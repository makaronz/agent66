"""
Bulk database operations to prevent N+1 queries and improve performance.
Provides efficient batch processing for common database operations.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy import text, insert, update, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection_pool import ConnectionPoolManager, PoolType
from prometheus_client import Counter, Histogram


@dataclass
class BulkOperationResult:
    """Result of a bulk database operation."""
    success: bool
    affected_rows: int
    errors: List[str]
    execution_time: float
    operation_type: str


class BulkOperations:
    """
    Efficient bulk database operations to prevent N+1 queries.
    Provides batch processing for inserts, updates, and complex queries.
    """
    
    def __init__(self, pool_manager: ConnectionPoolManager):
        self.pool_manager = pool_manager
        self.logger = logging.getLogger(__name__)
        
        # Metrics
        self.metrics = {
            'bulk_operations_total': Counter(
                'db_bulk_operations_total',
                'Total bulk database operations',
                ['operation_type', 'status']
            ),
            'bulk_operation_duration': Histogram(
                'db_bulk_operation_duration_seconds',
                'Bulk operation execution time',
                ['operation_type']
            ),
            'bulk_operation_rows': Histogram(
                'db_bulk_operation_rows',
                'Number of rows affected by bulk operations',
                ['operation_type']
            )
        }
    
    async def bulk_insert_trades(self, trades_data: List[Dict[str, Any]], 
                                batch_size: int = 1000) -> BulkOperationResult:
        """
        Bulk insert trades with efficient batching.
        Handles large volumes of trade data efficiently.
        """
        start_time = asyncio.get_event_loop().time()
        total_affected = 0
        errors = []
        
        try:
            async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                # Process in batches to avoid memory issues
                for i in range(0, len(trades_data), batch_size):
                    batch = trades_data[i:i + batch_size]
                    
                    try:
                        # Use PostgreSQL's efficient bulk insert
                        insert_stmt = pg_insert(text('trades')).values(batch)
                        
                        # Handle conflicts with ON CONFLICT DO UPDATE
                        upsert_stmt = insert_stmt.on_conflict_do_update(
                            index_elements=['id'],
                            set_={
                                'executed_price': insert_stmt.excluded.executed_price,
                                'executed_quantity': insert_stmt.excluded.executed_quantity,
                                'status': insert_stmt.excluded.status,
                                'execution_time': insert_stmt.excluded.execution_time,
                                'pnl': insert_stmt.excluded.pnl,
                                'metadata': insert_stmt.excluded.metadata
                            }
                        )
                        
                        result = await session.execute(upsert_stmt)
                        total_affected += result.rowcount
                        
                    except Exception as e:
                        error_msg = f"Batch {i//batch_size + 1} failed: {str(e)}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                
                await session.commit()
                
        except Exception as e:
            errors.append(f"Bulk insert failed: {str(e)}")
            self.logger.error(f"Bulk insert trades failed: {e}", exc_info=True)
        
        execution_time = asyncio.get_event_loop().time() - start_time
        success = len(errors) == 0
        
        # Update metrics
        self.metrics['bulk_operations_total'].labels(
            operation_type='insert_trades',
            status='success' if success else 'error'
        ).inc()
        
        self.metrics['bulk_operation_duration'].labels(
            operation_type='insert_trades'
        ).observe(execution_time)
        
        self.metrics['bulk_operation_rows'].labels(
            operation_type='insert_trades'
        ).observe(total_affected)
        
        return BulkOperationResult(
            success=success,
            affected_rows=total_affected,
            errors=errors,
            execution_time=execution_time,
            operation_type='insert_trades'
        )
    
    async def bulk_insert_smc_signals(self, signals_data: List[Dict[str, Any]], 
                                     batch_size: int = 500) -> BulkOperationResult:
        """
        Bulk insert SMC signals with deduplication.
        Efficiently handles high-frequency signal generation.
        """
        start_time = asyncio.get_event_loop().time()
        total_affected = 0
        errors = []
        
        try:
            async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                for i in range(0, len(signals_data), batch_size):
                    batch = signals_data[i:i + batch_size]
                    
                    try:
                        # Use raw SQL for better performance with large batches
                        values_list = []
                        params = {}
                        
                        for idx, signal in enumerate(batch):
                            param_prefix = f"s{idx}_"
                            values_list.append(f"""(
                                :{param_prefix}user_id,
                                :{param_prefix}symbol,
                                :{param_prefix}timeframe,
                                :{param_prefix}signal_type,
                                :{param_prefix}direction,
                                :{param_prefix}confidence,
                                :{param_prefix}price_level,
                                :{param_prefix}stop_loss,
                                :{param_prefix}take_profit,
                                :{param_prefix}risk_reward_ratio,
                                :{param_prefix}expires_at,
                                :{param_prefix}metadata,
                                NOW()
                            )""")
                            
                            # Add parameters
                            for key, value in signal.items():
                                params[f"{param_prefix}{key}"] = value
                        
                        insert_query = text(f"""
                            INSERT INTO smc_signals (
                                user_id, symbol, timeframe, signal_type, direction,
                                confidence, price_level, stop_loss, take_profit,
                                risk_reward_ratio, expires_at, metadata, created_at
                            ) VALUES {', '.join(values_list)}
                            ON CONFLICT (user_id, symbol, signal_type, created_at) 
                            DO UPDATE SET
                                confidence = EXCLUDED.confidence,
                                price_level = EXCLUDED.price_level,
                                metadata = EXCLUDED.metadata
                        """)
                        
                        result = await session.execute(insert_query, params)
                        total_affected += result.rowcount
                        
                    except Exception as e:
                        error_msg = f"Signal batch {i//batch_size + 1} failed: {str(e)}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                
                await session.commit()
                
        except Exception as e:
            errors.append(f"Bulk insert signals failed: {str(e)}")
            self.logger.error(f"Bulk insert SMC signals failed: {e}", exc_info=True)
        
        execution_time = asyncio.get_event_loop().time() - start_time
        success = len(errors) == 0
        
        # Update metrics
        self.metrics['bulk_operations_total'].labels(
            operation_type='insert_signals',
            status='success' if success else 'error'
        ).inc()
        
        self.metrics['bulk_operation_duration'].labels(
            operation_type='insert_signals'
        ).observe(execution_time)
        
        self.metrics['bulk_operation_rows'].labels(
            operation_type='insert_signals'
        ).observe(total_affected)
        
        return BulkOperationResult(
            success=success,
            affected_rows=total_affected,
            errors=errors,
            execution_time=execution_time,
            operation_type='insert_signals'
        )
    
    async def bulk_update_trade_status(self, trade_updates: List[Dict[str, Any]]) -> BulkOperationResult:
        """
        Bulk update trade statuses efficiently.
        Prevents N+1 queries when updating multiple trades.
        """
        start_time = asyncio.get_event_loop().time()
        total_affected = 0
        errors = []
        
        try:
            async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                # Group updates by status for efficiency
                status_groups = {}
                for update in trade_updates:
                    status = update.get('status')
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(update)
                
                for status, updates in status_groups.items():
                    try:
                        # Extract trade IDs and common fields
                        trade_ids = [update['id'] for update in updates]
                        
                        # Build dynamic update query
                        update_query = text("""
                            UPDATE trades 
                            SET 
                                status = :status,
                                executed_price = CASE 
                                    WHEN :executed_price IS NOT NULL THEN :executed_price 
                                    ELSE executed_price 
                                END,
                                executed_quantity = CASE 
                                    WHEN :executed_quantity IS NOT NULL THEN :executed_quantity 
                                    ELSE executed_quantity 
                                END,
                                execution_time = CASE 
                                    WHEN :execution_time IS NOT NULL THEN :execution_time 
                                    ELSE execution_time 
                                END,
                                pnl = CASE 
                                    WHEN :pnl IS NOT NULL THEN :pnl 
                                    ELSE pnl 
                                END
                            WHERE id = ANY(:trade_ids)
                        """)
                        
                        # Use the first update as template for common values
                        template = updates[0]
                        result = await session.execute(update_query, {
                            'status': status,
                            'executed_price': template.get('executed_price'),
                            'executed_quantity': template.get('executed_quantity'),
                            'execution_time': template.get('execution_time'),
                            'pnl': template.get('pnl'),
                            'trade_ids': trade_ids
                        })
                        
                        total_affected += result.rowcount
                        
                    except Exception as e:
                        error_msg = f"Status group {status} update failed: {str(e)}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                
                await session.commit()
                
        except Exception as e:
            errors.append(f"Bulk update trade status failed: {str(e)}")
            self.logger.error(f"Bulk update trade status failed: {e}", exc_info=True)
        
        execution_time = asyncio.get_event_loop().time() - start_time
        success = len(errors) == 0
        
        # Update metrics
        self.metrics['bulk_operations_total'].labels(
            operation_type='update_trades',
            status='success' if success else 'error'
        ).inc()
        
        self.metrics['bulk_operation_duration'].labels(
            operation_type='update_trades'
        ).observe(execution_time)
        
        return BulkOperationResult(
            success=success,
            affected_rows=total_affected,
            errors=errors,
            execution_time=execution_time,
            operation_type='update_trades'
        )
    
    async def get_user_trading_data_bulk(self, user_ids: List[str], 
                                        days_back: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Efficiently fetch trading data for multiple users.
        Prevents N+1 queries when loading user dashboards.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.pool_manager.get_async_session(PoolType.READ_ONLY) as session:
                # Single query to get all user trading data
                query = text("""
                    WITH user_stats AS (
                        SELECT 
                            t.user_id,
                            COUNT(*) as total_trades,
                            SUM(CASE WHEN t.pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                            SUM(CASE WHEN t.pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                            SUM(t.pnl) as total_pnl,
                            AVG(t.pnl) as avg_pnl,
                            MAX(t.pnl) as best_trade,
                            MIN(t.pnl) as worst_trade,
                            COUNT(DISTINCT t.symbol) as symbols_traded,
                            MAX(t.timestamp) as last_trade_time
                        FROM trades t
                        WHERE t.user_id = ANY(:user_ids)
                            AND t.timestamp >= NOW() - INTERVAL ':days_back days'
                            AND t.status = 'filled'
                            AND t.pnl IS NOT NULL
                        GROUP BY t.user_id
                    ),
                    session_stats AS (
                        SELECT 
                            ts.user_id,
                            COUNT(*) as total_sessions,
                            COUNT(CASE WHEN ts.status = 'active' THEN 1 END) as active_sessions,
                            AVG(ts.total_pnl) as avg_session_pnl
                        FROM trading_sessions ts
                        WHERE ts.user_id = ANY(:user_ids)
                            AND ts.created_at >= NOW() - INTERVAL ':days_back days'
                        GROUP BY ts.user_id
                    ),
                    signal_stats AS (
                        SELECT 
                            s.user_id,
                            COUNT(*) as total_signals,
                            COUNT(CASE WHEN s.is_processed THEN 1 END) as processed_signals,
                            AVG(s.confidence) as avg_confidence
                        FROM smc_signals s
                        WHERE s.user_id = ANY(:user_ids)
                            AND s.created_at >= NOW() - INTERVAL ':days_back days'
                        GROUP BY s.user_id
                    )
                    SELECT 
                        u.id as user_id,
                        u.email,
                        u.full_name,
                        u.subscription_tier,
                        COALESCE(us.total_trades, 0) as total_trades,
                        COALESCE(us.winning_trades, 0) as winning_trades,
                        COALESCE(us.losing_trades, 0) as losing_trades,
                        COALESCE(us.total_pnl, 0) as total_pnl,
                        COALESCE(us.avg_pnl, 0) as avg_pnl,
                        COALESCE(us.best_trade, 0) as best_trade,
                        COALESCE(us.worst_trade, 0) as worst_trade,
                        COALESCE(us.symbols_traded, 0) as symbols_traded,
                        us.last_trade_time,
                        COALESCE(ss.total_sessions, 0) as total_sessions,
                        COALESCE(ss.active_sessions, 0) as active_sessions,
                        COALESCE(ss.avg_session_pnl, 0) as avg_session_pnl,
                        COALESCE(sig.total_signals, 0) as total_signals,
                        COALESCE(sig.processed_signals, 0) as processed_signals,
                        COALESCE(sig.avg_confidence, 0) as avg_confidence,
                        CASE 
                            WHEN us.total_trades > 0 
                            THEN ROUND(us.winning_trades::numeric / us.total_trades * 100, 2)
                            ELSE 0 
                        END as win_rate
                    FROM users u
                    LEFT JOIN user_stats us ON u.id = us.user_id
                    LEFT JOIN session_stats ss ON u.id = ss.user_id
                    LEFT JOIN signal_stats sig ON u.id = sig.user_id
                    WHERE u.id = ANY(:user_ids)
                """)
                
                result = await session.execute(query, {
                    'user_ids': user_ids,
                    'days_back': days_back
                })
                
                rows = result.fetchall()
                
                # Convert to dictionary format
                user_data = {}
                for row in rows:
                    user_data[row.user_id] = {
                        'user_info': {
                            'email': row.email,
                            'full_name': row.full_name,
                            'subscription_tier': row.subscription_tier
                        },
                        'trading_stats': {
                            'total_trades': row.total_trades,
                            'winning_trades': row.winning_trades,
                            'losing_trades': row.losing_trades,
                            'win_rate': float(row.win_rate),
                            'total_pnl': float(row.total_pnl),
                            'avg_pnl': float(row.avg_pnl),
                            'best_trade': float(row.best_trade),
                            'worst_trade': float(row.worst_trade),
                            'symbols_traded': row.symbols_traded,
                            'last_trade_time': row.last_trade_time
                        },
                        'session_stats': {
                            'total_sessions': row.total_sessions,
                            'active_sessions': row.active_sessions,
                            'avg_session_pnl': float(row.avg_session_pnl)
                        },
                        'signal_stats': {
                            'total_signals': row.total_signals,
                            'processed_signals': row.processed_signals,
                            'avg_confidence': float(row.avg_confidence)
                        }
                    }
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                # Update metrics
                self.metrics['bulk_operation_duration'].labels(
                    operation_type='bulk_user_data'
                ).observe(execution_time)
                
                self.logger.info(f"Loaded trading data for {len(user_data)} users in {execution_time:.3f}s")
                
                return user_data
                
        except Exception as e:
            self.logger.error(f"Bulk user data fetch failed: {e}", exc_info=True)
            return {}
    
    async def get_symbol_analytics_bulk(self, symbols: List[str], 
                                       timeframe: str = '1h') -> Dict[str, Dict[str, Any]]:
        """
        Efficiently fetch analytics data for multiple symbols.
        Prevents N+1 queries when loading market overview.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.pool_manager.get_async_session(PoolType.READ_ONLY) as session:
                # Get trading statistics for symbols
                trading_query = text("""
                    SELECT 
                        symbol,
                        COUNT(*) as total_trades,
                        SUM(quantity) as total_volume,
                        AVG(executed_price) as avg_price,
                        MIN(executed_price) as min_price,
                        MAX(executed_price) as max_price,
                        SUM(CASE WHEN side = 'buy' THEN quantity ELSE 0 END) as buy_volume,
                        SUM(CASE WHEN side = 'sell' THEN quantity ELSE 0 END) as sell_volume,
                        COUNT(DISTINCT user_id) as unique_traders,
                        MAX(timestamp) as last_trade_time
                    FROM trades
                    WHERE symbol = ANY(:symbols)
                        AND timestamp >= NOW() - INTERVAL '24 hours'
                        AND status = 'filled'
                    GROUP BY symbol
                """)
                
                # Get SMC signal statistics
                signals_query = text("""
                    SELECT 
                        symbol,
                        signal_type,
                        direction,
                        COUNT(*) as signal_count,
                        AVG(confidence) as avg_confidence,
                        COUNT(CASE WHEN is_processed THEN 1 END) as processed_count
                    FROM smc_signals
                    WHERE symbol = ANY(:symbols)
                        AND created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY symbol, signal_type, direction
                """)
                
                # Execute queries concurrently
                trading_result, signals_result = await asyncio.gather(
                    session.execute(trading_query, {'symbols': symbols}),
                    session.execute(signals_query, {'symbols': symbols})
                )
                
                # Process trading data
                symbol_data = {}
                for row in trading_result.fetchall():
                    symbol_data[row.symbol] = {
                        'trading_stats': {
                            'total_trades': row.total_trades,
                            'total_volume': float(row.total_volume or 0),
                            'avg_price': float(row.avg_price or 0),
                            'min_price': float(row.min_price or 0),
                            'max_price': float(row.max_price or 0),
                            'buy_volume': float(row.buy_volume or 0),
                            'sell_volume': float(row.sell_volume or 0),
                            'unique_traders': row.unique_traders,
                            'last_trade_time': row.last_trade_time
                        },
                        'smc_signals': {}
                    }
                
                # Process signal data
                for row in signals_result.fetchall():
                    symbol = row.symbol
                    if symbol not in symbol_data:
                        symbol_data[symbol] = {'trading_stats': {}, 'smc_signals': {}}
                    
                    signal_key = f"{row.signal_type}_{row.direction}"
                    symbol_data[symbol]['smc_signals'][signal_key] = {
                        'signal_count': row.signal_count,
                        'avg_confidence': float(row.avg_confidence or 0),
                        'processed_count': row.processed_count
                    }
                
                execution_time = asyncio.get_event_loop().time() - start_time
                
                # Update metrics
                self.metrics['bulk_operation_duration'].labels(
                    operation_type='bulk_symbol_analytics'
                ).observe(execution_time)
                
                self.logger.info(f"Loaded analytics for {len(symbol_data)} symbols in {execution_time:.3f}s")
                
                return symbol_data
                
        except Exception as e:
            self.logger.error(f"Bulk symbol analytics fetch failed: {e}", exc_info=True)
            return {}
    
    async def cleanup_expired_data(self, batch_size: int = 1000) -> BulkOperationResult:
        """
        Efficiently clean up expired data in batches.
        Prevents long-running transactions and locks.
        """
        start_time = asyncio.get_event_loop().time()
        total_affected = 0
        errors = []
        
        try:
            async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                # Clean up expired market data cache
                cache_query = text("""
                    DELETE FROM market_data_cache 
                    WHERE expires_at < NOW()
                    AND id IN (
                        SELECT id FROM market_data_cache 
                        WHERE expires_at < NOW()
                        LIMIT :batch_size
                    )
                """)
                
                # Clean up expired SMC signals
                signals_query = text("""
                    DELETE FROM smc_signals 
                    WHERE expires_at < NOW()
                    AND id IN (
                        SELECT id FROM smc_signals 
                        WHERE expires_at < NOW()
                        LIMIT :batch_size
                    )
                """)
                
                # Execute cleanup queries
                cache_result = await session.execute(cache_query, {'batch_size': batch_size})
                signals_result = await session.execute(signals_query, {'batch_size': batch_size})
                
                total_affected = cache_result.rowcount + signals_result.rowcount
                
                await session.commit()
                
        except Exception as e:
            errors.append(f"Cleanup failed: {str(e)}")
            self.logger.error(f"Data cleanup failed: {e}", exc_info=True)
        
        execution_time = asyncio.get_event_loop().time() - start_time
        success = len(errors) == 0
        
        # Update metrics
        self.metrics['bulk_operations_total'].labels(
            operation_type='cleanup',
            status='success' if success else 'error'
        ).inc()
        
        self.metrics['bulk_operation_duration'].labels(
            operation_type='cleanup'
        ).observe(execution_time)
        
        return BulkOperationResult(
            success=success,
            affected_rows=total_affected,
            errors=errors,
            execution_time=execution_time,
            operation_type='cleanup'
        )