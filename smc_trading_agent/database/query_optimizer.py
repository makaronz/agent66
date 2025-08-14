"""
Database query optimization and analysis module.
Provides slow query analysis, index recommendations, and query result caching.
"""

import asyncio
import logging
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

import redis
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from database.connection_pool import ConnectionPoolManager, PoolType
from prometheus_client import Counter, Histogram, Gauge


class QueryType(Enum):
    """Types of database queries."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    UNKNOWN = "unknown"


@dataclass
class SlowQuery:
    """Represents a slow query with analysis."""
    query_hash: str
    query_text: str
    query_type: QueryType
    avg_duration: float
    max_duration: float
    call_count: int
    total_time: float
    first_seen: datetime
    last_seen: datetime
    database: str
    user: str
    suggested_indexes: List[str]
    optimization_suggestions: List[str]


@dataclass
class IndexRecommendation:
    """Database index recommendation."""
    table_name: str
    columns: List[str]
    index_type: str  # btree, hash, gin, gist
    reason: str
    estimated_benefit: float
    create_statement: str


@dataclass
class QueryStats:
    """Query execution statistics."""
    query_hash: str
    execution_count: int
    total_duration: float
    avg_duration: float
    min_duration: float
    max_duration: float
    cache_hits: int
    cache_misses: int
    last_executed: datetime


class QueryOptimizer:
    """
    Database query optimizer with slow query analysis and caching.
    Integrates with pg_stat_statements for query performance monitoring.
    """
    
    def __init__(self, pool_manager: ConnectionPoolManager, redis_client: redis.Redis, config: Dict[str, Any]):
        self.pool_manager = pool_manager
        self.redis_client = redis_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.slow_query_threshold = config.get('database', {}).get('slow_query_threshold', 1.0)  # seconds
        self.cache_ttl = config.get('database', {}).get('cache_ttl', 3600)  # 1 hour
        self.max_cache_size = config.get('database', {}).get('max_cache_size', 1000)
        
        # Metrics
        self._setup_metrics()
        
        # Query statistics
        self.query_stats: Dict[str, QueryStats] = {}
        self.slow_queries: Dict[str, SlowQuery] = {}
        self.index_recommendations: List[IndexRecommendation] = []
        
        # Cache statistics
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _setup_metrics(self):
        """Setup Prometheus metrics for query optimization."""
        self.metrics = {
            'query_duration': Histogram(
                'db_query_duration_seconds',
                'Database query execution time',
                ['query_type', 'cached', 'pool_type']
            ),
            'query_cache_hits': Counter(
                'db_query_cache_hits_total',
                'Total query cache hits',
                ['query_type']
            ),
            'query_cache_misses': Counter(
                'db_query_cache_misses_total',
                'Total query cache misses',
                ['query_type']
            ),
            'slow_queries_total': Counter(
                'db_slow_queries_total',
                'Total slow queries detected',
                ['query_type', 'database']
            ),
            'query_optimization_suggestions': Gauge(
                'db_query_optimization_suggestions',
                'Number of query optimization suggestions',
                ['suggestion_type']
            ),
            'index_recommendations': Gauge(
                'db_index_recommendations_total',
                'Total number of index recommendations'
            )
        }
    
    async def analyze_slow_queries(self) -> List[SlowQuery]:
        """Analyze slow queries using pg_stat_statements."""
        slow_queries = []
        
        try:
            async with self.pool_manager.get_async_session(PoolType.READ_ONLY) as session:
                # Query pg_stat_statements for slow queries
                query = text("""
                    SELECT 
                        md5(query) as query_hash,
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time,
                        min_exec_time,
                        stddev_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements 
                    WHERE mean_exec_time > :threshold
                    ORDER BY total_exec_time DESC
                    LIMIT 50
                """)
                
                result = await session.execute(query, {'threshold': self.slow_query_threshold * 1000})  # Convert to ms
                rows = result.fetchall()
                
                for row in rows:
                    query_hash = row.query_hash
                    query_text = row.query.strip()
                    query_type = self._detect_query_type(query_text)
                    
                    # Generate optimization suggestions
                    suggestions = self._generate_optimization_suggestions(query_text, row)
                    index_suggestions = self._suggest_indexes(query_text)
                    
                    slow_query = SlowQuery(
                        query_hash=query_hash,
                        query_text=query_text,
                        query_type=query_type,
                        avg_duration=row.mean_exec_time / 1000.0,  # Convert to seconds
                        max_duration=row.max_exec_time / 1000.0,
                        call_count=row.calls,
                        total_time=row.total_exec_time / 1000.0,
                        first_seen=datetime.now() - timedelta(hours=1),  # Approximate
                        last_seen=datetime.now(),
                        database='smc_trading_agent',
                        user='smc_app_user',
                        suggested_indexes=index_suggestions,
                        optimization_suggestions=suggestions
                    )
                    
                    slow_queries.append(slow_query)
                    self.slow_queries[query_hash] = slow_query
                    
                    # Update metrics
                    self.metrics['slow_queries_total'].labels(
                        query_type=query_type.value,
                        database='smc_trading_agent'
                    ).inc()
                
                self.logger.info(f"Analyzed {len(slow_queries)} slow queries")
                
        except Exception as e:
            self.logger.error(f"Error analyzing slow queries: {e}", exc_info=True)
        
        return slow_queries
    
    def _detect_query_type(self, query: str) -> QueryType:
        """Detect the type of SQL query."""
        query_lower = query.lower().strip()
        
        if query_lower.startswith('select'):
            return QueryType.SELECT
        elif query_lower.startswith('insert'):
            return QueryType.INSERT
        elif query_lower.startswith('update'):
            return QueryType.UPDATE
        elif query_lower.startswith('delete'):
            return QueryType.DELETE
        else:
            return QueryType.UNKNOWN
    
    def _generate_optimization_suggestions(self, query: str, stats: Any) -> List[str]:
        """Generate optimization suggestions for a query."""
        suggestions = []
        query_lower = query.lower()
        
        # Check for common anti-patterns
        if 'select *' in query_lower:
            suggestions.append("Avoid SELECT * - specify only needed columns")
        
        if 'order by' in query_lower and 'limit' not in query_lower:
            suggestions.append("Consider adding LIMIT to ORDER BY queries")
        
        if 'like' in query_lower and query_lower.count('%') > 0:
            if query_lower.find("like '%") != -1:
                suggestions.append("Leading wildcard in LIKE prevents index usage - consider full-text search")
        
        if 'or' in query_lower:
            suggestions.append("OR conditions can prevent index usage - consider UNION or restructuring")
        
        if 'function(' in query_lower.replace(' ', ''):
            suggestions.append("Functions in WHERE clause prevent index usage - consider functional indexes")
        
        # Check for missing indexes based on WHERE clauses
        if 'where' in query_lower:
            suggestions.append("Ensure indexes exist for WHERE clause columns")
        
        # Check for JOIN performance
        if 'join' in query_lower and not any(word in query_lower for word in ['inner join', 'left join', 'right join']):
            suggestions.append("Use explicit JOIN syntax instead of implicit joins")
        
        # Check hit ratio
        if hasattr(stats, 'hit_percent') and stats.hit_percent and stats.hit_percent < 95:
            suggestions.append(f"Low buffer hit ratio ({stats.hit_percent:.1f}%) - consider increasing shared_buffers")
        
        return suggestions
    
    def _suggest_indexes(self, query: str) -> List[str]:
        """Suggest indexes based on query analysis."""
        suggestions = []
        query_lower = query.lower()
        
        # Simple pattern matching for index suggestions
        # In production, this would be more sophisticated
        
        # Extract table names and WHERE conditions
        import re
        
        # Find WHERE clauses
        where_matches = re.findall(r'where\s+(\w+\.\w+|\w+)\s*[=<>]', query_lower)
        for match in where_matches:
            if '.' in match:
                table, column = match.split('.')
                suggestions.append(f"CREATE INDEX idx_{table}_{column} ON {table} ({column});")
            else:
                # Need to infer table from context - simplified approach
                table_matches = re.findall(r'from\s+(\w+)', query_lower)
                if table_matches:
                    table = table_matches[0]
                    suggestions.append(f"CREATE INDEX idx_{table}_{match} ON {table} ({match});")
        
        # Find ORDER BY clauses
        order_matches = re.findall(r'order\s+by\s+(\w+\.\w+|\w+)', query_lower)
        for match in order_matches:
            if '.' in match:
                table, column = match.split('.')
                suggestions.append(f"CREATE INDEX idx_{table}_{column}_order ON {table} ({column});")
        
        return suggestions
    
    async def generate_index_recommendations(self) -> List[IndexRecommendation]:
        """Generate comprehensive index recommendations."""
        recommendations = []
        
        try:
            async with self.pool_manager.get_async_session(PoolType.READ_ONLY) as session:
                # Get table statistics
                table_stats_query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del,
                        n_live_tup,
                        n_dead_tup,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        idx_tup_fetch
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY seq_scan DESC, n_live_tup DESC
                """)
                
                result = await session.execute(table_stats_query)
                table_stats = result.fetchall()
                
                for stats in table_stats:
                    table_name = stats.tablename
                    
                    # High sequential scan ratio suggests missing indexes
                    if stats.seq_scan > 0 and stats.idx_scan > 0:
                        seq_ratio = stats.seq_scan / (stats.seq_scan + stats.idx_scan)
                        if seq_ratio > 0.1 and stats.n_live_tup > 1000:  # More than 10% seq scans on large table
                            
                            # Get column usage statistics
                            column_usage = await self._get_column_usage_stats(session, table_name)
                            
                            for column_info in column_usage:
                                recommendation = IndexRecommendation(
                                    table_name=table_name,
                                    columns=[column_info['column_name']],
                                    index_type='btree',
                                    reason=f"High sequential scan ratio ({seq_ratio:.2%}) on frequently queried column",
                                    estimated_benefit=seq_ratio * 100,
                                    create_statement=f"CREATE INDEX CONCURRENTLY idx_{table_name}_{column_info['column_name']} ON {table_name} ({column_info['column_name']});"
                                )
                                recommendations.append(recommendation)
                
                # Analyze missing indexes from slow queries
                for slow_query in self.slow_queries.values():
                    if slow_query.query_type == QueryType.SELECT:
                        query_recommendations = self._analyze_query_for_indexes(slow_query.query_text)
                        recommendations.extend(query_recommendations)
                
                self.index_recommendations = recommendations
                
                # Update metrics
                self.metrics['index_recommendations'].set(len(recommendations))
                
                self.logger.info(f"Generated {len(recommendations)} index recommendations")
                
        except Exception as e:
            self.logger.error(f"Error generating index recommendations: {e}", exc_info=True)
        
        return recommendations
    
    async def _get_column_usage_stats(self, session, table_name: str) -> List[Dict[str, Any]]:
        """Get column usage statistics for a table."""
        try:
            # This is a simplified approach - in production you'd analyze pg_stat_statements
            # to see which columns are most frequently used in WHERE clauses
            
            column_query = text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :table_name
                ORDER BY ordinal_position
            """)
            
            result = await session.execute(column_query, {'table_name': table_name})
            columns = result.fetchall()
            
            # Return columns that are likely to benefit from indexes
            # This is simplified - real implementation would analyze query patterns
            return [
                {
                    'column_name': col.column_name,
                    'data_type': col.data_type,
                    'usage_frequency': 1.0  # Placeholder
                }
                for col in columns
                if col.column_name in ['id', 'user_id', 'created_at', 'updated_at', 'status', 'symbol']
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting column usage stats for {table_name}: {e}")
            return []
    
    def _analyze_query_for_indexes(self, query: str) -> List[IndexRecommendation]:
        """Analyze a specific query for index recommendations."""
        recommendations = []
        
        # This is a simplified implementation
        # In production, you'd use a proper SQL parser
        
        query_lower = query.lower()
        
        # Look for WHERE clauses with equality conditions
        import re
        where_patterns = re.findall(r'where\s+(\w+)\s*=', query_lower)
        
        for column in where_patterns:
            # Try to extract table name
            table_matches = re.findall(r'from\s+(\w+)', query_lower)
            if table_matches:
                table_name = table_matches[0]
                
                recommendation = IndexRecommendation(
                    table_name=table_name,
                    columns=[column],
                    index_type='btree',
                    reason="Equality condition in WHERE clause",
                    estimated_benefit=50.0,
                    create_statement=f"CREATE INDEX CONCURRENTLY idx_{table_name}_{column} ON {table_name} ({column});"
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    async def execute_with_cache(self, query: str, params: Optional[Dict] = None, 
                                pool_type: PoolType = PoolType.MAIN, 
                                cache_ttl: Optional[int] = None) -> Any:
        """Execute a query with result caching."""
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(query, params)
        query_type = self._detect_query_type(query)
        
        # Only cache SELECT queries
        if query_type == QueryType.SELECT:
            # Try to get from cache first
            try:
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    self.cache_stats['hits'] += 1
                    self.metrics['query_cache_hits'].labels(query_type=query_type.value).inc()
                    
                    duration = time.time() - start_time
                    self.metrics['query_duration'].labels(
                        query_type=query_type.value,
                        cached='true',
                        pool_type=pool_type.value
                    ).observe(duration)
                    
                    return json.loads(cached_result)
                    
            except Exception as e:
                self.logger.warning(f"Cache read error: {e}")
        
        # Cache miss or non-cacheable query - execute normally
        self.cache_stats['misses'] += 1
        self.metrics['query_cache_misses'].labels(query_type=query_type.value).inc()
        
        try:
            result = await self.pool_manager.execute_query(
                query, params, pool_type, query_type.value
            )
            
            # Cache the result if it's a SELECT query
            if query_type == QueryType.SELECT and result:
                try:
                    # Convert result to JSON-serializable format
                    if hasattr(result, 'fetchall'):
                        rows = result.fetchall()
                        serializable_result = [dict(row._mapping) for row in rows]
                    else:
                        serializable_result = result
                    
                    ttl = cache_ttl or self.cache_ttl
                    self.redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(serializable_result, default=str)
                    )
                    
                except Exception as e:
                    self.logger.warning(f"Cache write error: {e}")
            
            duration = time.time() - start_time
            self.metrics['query_duration'].labels(
                query_type=query_type.value,
                cached='false',
                pool_type=pool_type.value
            ).observe(duration)
            
            # Update query statistics
            self._update_query_stats(cache_key, duration)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Query execution error: {e}")
            raise
    
    def _generate_cache_key(self, query: str, params: Optional[Dict] = None) -> str:
        """Generate a cache key for a query and parameters."""
        query_normalized = ' '.join(query.split())  # Normalize whitespace
        
        if params:
            params_str = json.dumps(params, sort_keys=True)
            cache_input = f"{query_normalized}:{params_str}"
        else:
            cache_input = query_normalized
        
        return f"query_cache:{hashlib.md5(cache_input.encode()).hexdigest()}"
    
    def _update_query_stats(self, query_hash: str, duration: float):
        """Update query execution statistics."""
        if query_hash in self.query_stats:
            stats = self.query_stats[query_hash]
            stats.execution_count += 1
            stats.total_duration += duration
            stats.avg_duration = stats.total_duration / stats.execution_count
            stats.min_duration = min(stats.min_duration, duration)
            stats.max_duration = max(stats.max_duration, duration)
            stats.last_executed = datetime.now()
        else:
            self.query_stats[query_hash] = QueryStats(
                query_hash=query_hash,
                execution_count=1,
                total_duration=duration,
                avg_duration=duration,
                min_duration=duration,
                max_duration=duration,
                cache_hits=0,
                cache_misses=1,
                last_executed=datetime.now()
            )
    
    async def optimize_table_statistics(self):
        """Update table statistics for better query planning."""
        try:
            async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                # Get all user tables
                tables_query = text("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                
                result = await session.execute(tables_query)
                tables = result.fetchall()
                
                for table in tables:
                    table_name = table.tablename
                    
                    # Analyze table to update statistics
                    analyze_query = text(f"ANALYZE {table_name}")
                    await session.execute(analyze_query)
                    
                    self.logger.info(f"Updated statistics for table {table_name}")
                
                await session.commit()
                
        except Exception as e:
            self.logger.error(f"Error updating table statistics: {e}", exc_info=True)
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get a comprehensive optimization report."""
        return {
            'slow_queries': {
                'count': len(self.slow_queries),
                'queries': [asdict(query) for query in self.slow_queries.values()]
            },
            'index_recommendations': {
                'count': len(self.index_recommendations),
                'recommendations': [asdict(rec) for rec in self.index_recommendations]
            },
            'cache_statistics': self.cache_stats,
            'query_statistics': {
                'total_queries': len(self.query_stats),
                'avg_duration': sum(stats.avg_duration for stats in self.query_stats.values()) / max(len(self.query_stats), 1)
            }
        }
    
    async def clear_cache(self, pattern: Optional[str] = None):
        """Clear query cache."""
        try:
            if pattern:
                keys = self.redis_client.keys(f"query_cache:{pattern}*")
            else:
                keys = self.redis_client.keys("query_cache:*")
            
            if keys:
                self.redis_client.delete(*keys)
                self.cache_stats['evictions'] += len(keys)
                self.logger.info(f"Cleared {len(keys)} cache entries")
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")