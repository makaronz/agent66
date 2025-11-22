"""
Position Manager for SMC Trading Agent.

This module provides comprehensive position management including:
- Position discovery across multiple exchanges
- Emergency position closure with market orders
- Concurrent closure across all connected exchanges
- Error handling and retry mechanisms
- Position validation and confirmation
- Integration with exchange connectors
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import aiohttp

from ..data_pipeline.exchange_connectors import ExchangeConnector, ExchangeConnectorError

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    """Position status enumeration."""
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"


@dataclass
class Position:
    """Position data structure."""
    exchange: str
    symbol: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    timestamp: float
    status: PositionStatus = PositionStatus.OPEN


@dataclass
class ClosureResult:
    """Position closure result."""
    exchange: str
    symbol: str
    success: bool
    closed_size: float
    closure_price: float
    timestamp: float
    error_message: str = ""
    retry_count: int = 0


class PositionManager:
    """
    Comprehensive position manager for emergency closure.
    
    Handles position discovery and closure across multiple exchanges
    with concurrent execution and error handling.
    """
    
    def __init__(self, config: Dict[str, Any], exchange_connectors: Dict[str, ExchangeConnector]):
        """
        Initialize position manager.
        
        Args:
            config: Configuration dictionary with position management parameters
            exchange_connectors: Dictionary of exchange connector instances
        """
        self.config = config
        self.exchange_connectors = exchange_connectors
        
        # Position management settings
        self.max_retry_attempts = config.get('max_retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 1.0)  # seconds
        self.closure_timeout = config.get('closure_timeout', 30.0)  # seconds
        self.concurrent_closures = config.get('concurrent_closures', 5)
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.closure_history: List[ClosureResult] = []
        
        logger.info(f"Initialized position manager with {len(exchange_connectors)} exchanges")
    
    async def discover_all_positions(self) -> Dict[str, Position]:
        """
        Discover all open positions across all connected exchanges.
        
        Returns:
            Dict[str, Position]: Dictionary of positions by position ID
        """
        try:
            logger.info("Starting position discovery across all exchanges")
            
            # Create tasks for concurrent position discovery
            discovery_tasks = []
            for exchange_name, connector in self.exchange_connectors.items():
                task = self._discover_exchange_positions(exchange_name, connector)
                discovery_tasks.append(task)
            
            # Execute all discovery tasks concurrently
            results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
            
            # Process results and collect positions
            all_positions = {}
            for i, result in enumerate(results):
                exchange_name = list(self.exchange_connectors.keys())[i]
                
                if isinstance(result, Exception):
                    logger.error(f"Position discovery failed for {exchange_name}: {result}")
                    continue
                
                if result:
                    for position in result:
                        position_id = f"{exchange_name}_{position.symbol}_{position.side}"
                        all_positions[position_id] = position
            
            # Update internal position tracking
            self.positions = all_positions
            
            logger.info(f"Discovered {len(all_positions)} positions across {len(self.exchange_connectors)} exchanges")
            return all_positions
            
        except Exception as e:
            logger.error(f"Position discovery failed: {e}")
            raise
    
    async def _discover_exchange_positions(self, exchange_name: str, 
                                         connector: ExchangeConnector) -> List[Position]:
        """Discover positions for a specific exchange."""
        try:
            logger.debug(f"Discovering positions for {exchange_name}")
            
            # Get account information (positions)
            if hasattr(connector, 'get_positions'):
                # Use connector-specific position discovery
                positions_data = await connector.get_positions()
            else:
                # Fallback to generic position discovery
                positions_data = await self._generic_position_discovery(connector)
            
            # Convert to Position objects
            positions = []
            for pos_data in positions_data:
                try:
                    position = Position(
                        exchange=exchange_name,
                        symbol=pos_data.get('symbol', ''),
                        side=pos_data.get('side', 'long'),
                        size=float(pos_data.get('size', 0)),
                        entry_price=float(pos_data.get('entry_price', 0)),
                        current_price=float(pos_data.get('current_price', 0)),
                        unrealized_pnl=float(pos_data.get('unrealized_pnl', 0)),
                        timestamp=time.time()
                    )
                    
                    # Only include positions with non-zero size
                    if position.size > 0:
                        positions.append(position)
                        
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse position data for {exchange_name}: {e}")
                    continue
            
            logger.debug(f"Discovered {len(positions)} positions for {exchange_name}")
            return positions
            
        except Exception as e:
            logger.error(f"Position discovery failed for {exchange_name}: {e}")
            return []
    
    async def _generic_position_discovery(self, connector: ExchangeConnector) -> List[Dict]:
        """Generic position discovery using REST API."""
        try:
            # Try common position endpoints
            endpoints = [
                '/api/v3/account',
                '/api/v3/positions',
                '/api/v3/balance',
                '/api/v3/positions/info'
            ]
            
            for endpoint in endpoints:
                try:
                    response = await connector.fetch_rest_data(endpoint)
                    
                    # Try to extract position data from response
                    positions = self._extract_positions_from_response(response)
                    if positions:
                        return positions
                        
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            # If no positions found, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Generic position discovery failed: {e}")
            return []
    
    def _extract_positions_from_response(self, response: Dict) -> List[Dict]:
        """Extract position data from API response."""
        try:
            positions = []
            
            # Try different response formats
            if 'positions' in response:
                positions = response['positions']
            elif 'balances' in response:
                # Convert balances to positions
                balances = response['balances']
                positions = [
                    {
                        'symbol': balance.get('asset', ''),
                        'side': 'long',
                        'size': float(balance.get('free', 0)),
                        'entry_price': 0,
                        'current_price': 0,
                        'unrealized_pnl': 0
                    }
                    for balance in balances
                    if float(balance.get('free', 0)) > 0
                ]
            elif 'data' in response and isinstance(response['data'], list):
                positions = response['data']
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to extract positions from response: {e}")
            return []
    
    async def close_all_positions(self, reason: str = "Circuit breaker triggered") -> List[ClosureResult]:
        """
        Close all open positions across all exchanges.
        
        Args:
            reason: Reason for position closure
            
        Returns:
            List[ClosureResult]: Results of position closure operations
        """
        try:
            logger.warning(f"Starting emergency position closure: {reason}")
            
            # Discover current positions
            positions = await self.discover_all_positions()
            
            if not positions:
                logger.info("No open positions found to close")
                return []
            
            logger.info(f"Closing {len(positions)} positions across {len(self.exchange_connectors)} exchanges")
            
            # Create closure tasks for all positions
            closure_tasks = []
            for position_id, position in positions.items():
                task = self._close_position_with_retry(position)
                closure_tasks.append(task)
            
            # Execute closures with concurrency limit
            semaphore = asyncio.Semaphore(self.concurrent_closures)
            
            async def limited_closure(task):
                async with semaphore:
                    return await task
            
            limited_tasks = [limited_closure(task) for task in closure_tasks]
            
            # Execute all closure tasks
            results = await asyncio.gather(*limited_tasks, return_exceptions=True)
            
            # Process results
            closure_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Position closure task failed: {result}")
                    continue
                if result:
                    closure_results.append(result)
            
            # Update closure history
            self.closure_history.extend(closure_results)
            
            # Log summary
            successful_closures = [r for r in closure_results if r.success]
            failed_closures = [r for r in closure_results if not r.success]
            
            logger.info(f"Position closure completed: {len(successful_closures)} successful, "
                       f"{len(failed_closures)} failed")
            
            if failed_closures:
                logger.error(f"Failed closures: {[f'{r.exchange}:{r.symbol}' for r in failed_closures]}")
            
            return closure_results
            
        except Exception as e:
            logger.error(f"Position closure failed: {e}")
            raise
    
    async def _close_position_with_retry(self, position: Position) -> ClosureResult:
        """Close a single position with retry logic."""
        try:
            logger.debug(f"Closing position: {position.exchange}:{position.symbol} {position.side} {position.size}")
            
            # Get exchange connector
            connector = self.exchange_connectors.get(position.exchange)
            if not connector:
                return ClosureResult(
                    exchange=position.exchange,
                    symbol=position.symbol,
                    success=False,
                    closed_size=0,
                    closure_price=0,
                    timestamp=time.time(),
                    error_message=f"Exchange connector not found: {position.exchange}"
                )
            
            # Try to close position with retries
            for attempt in range(self.max_retry_attempts):
                try:
                    result = await self._execute_position_closure(connector, position)
                    
                    if result.success:
                        logger.info(f"Successfully closed position: {position.exchange}:{position.symbol}")
                        return result
                    else:
                        logger.warning(f"Position closure failed (attempt {attempt + 1}): {result.error_message}")
                        
                        if attempt < self.max_retry_attempts - 1:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                        else:
                            return result
                            
                except Exception as e:
                    logger.error(f"Position closure error (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        return ClosureResult(
                            exchange=position.exchange,
                            symbol=position.symbol,
                            success=False,
                            closed_size=0,
                            closure_price=0,
                            timestamp=time.time(),
                            error_message=str(e),
                            retry_count=attempt + 1
                        )
            
            # Should not reach here
            return ClosureResult(
                exchange=position.exchange,
                symbol=position.symbol,
                success=False,
                closed_size=0,
                closure_price=0,
                timestamp=time.time(),
                error_message="Max retry attempts exceeded",
                retry_count=self.max_retry_attempts
            )
            
        except Exception as e:
            logger.error(f"Position closure with retry failed: {e}")
            return ClosureResult(
                exchange=position.exchange,
                symbol=position.symbol,
                success=False,
                closed_size=0,
                closure_price=0,
                timestamp=time.time(),
                error_message=str(e)
            )
    
    async def _execute_position_closure(self, connector: ExchangeConnector, 
                                      position: Position) -> ClosureResult:
        """Execute position closure on a specific exchange."""
        try:
            # Determine order side (opposite of position side)
            order_side = "SELL" if position.side == "long" else "BUY"
            
            # Create market order for immediate closure
            order_params = {
                'symbol': position.symbol,
                'side': order_side,
                'type': 'MARKET',
                'quantity': position.size,
                'timestamp': int(time.time() * 1000)
            }
            
            # Execute order
            if hasattr(connector, 'place_order'):
                # Use connector-specific order placement
                order_result = await connector.place_order(order_params)
            else:
                # Fallback to generic order placement
                order_result = await self._generic_order_placement(connector, order_params)
            
            # Process order result
            if order_result.get('status') == 'FILLED':
                return ClosureResult(
                    exchange=position.exchange,
                    symbol=position.symbol,
                    success=True,
                    closed_size=position.size,
                    closure_price=float(order_result.get('avgPrice', position.current_price)),
                    timestamp=time.time()
                )
            else:
                return ClosureResult(
                    exchange=position.exchange,
                    symbol=position.symbol,
                    success=False,
                    closed_size=0,
                    closure_price=0,
                    timestamp=time.time(),
                    error_message=f"Order not filled: {order_result.get('status', 'unknown')}"
                )
                
        except Exception as e:
            logger.error(f"Position closure execution failed: {e}")
            return ClosureResult(
                exchange=position.exchange,
                symbol=position.symbol,
                success=False,
                closed_size=0,
                closure_price=0,
                timestamp=time.time(),
                error_message=str(e)
            )
    
    async def _generic_order_placement(self, connector: ExchangeConnector, 
                                     order_params: Dict) -> Dict:
        """Generic order placement using REST API."""
        try:
            # Try common order endpoints
            endpoints = [
                '/api/v3/order',
                '/api/v3/order/place',
                '/api/v3/trade/order'
            ]
            
            for endpoint in endpoints:
                try:
                    response = await connector.fetch_rest_data(endpoint, order_params)
                    return response
                except Exception as e:
                    logger.debug(f"Order endpoint {endpoint} failed: {e}")
                    continue
            
            raise Exception("No order placement endpoint available")
            
        except Exception as e:
            logger.error(f"Generic order placement failed: {e}")
            raise
    
    async def validate_position_closure(self, closure_results: List[ClosureResult]) -> bool:
        """
        Validate that all positions were successfully closed.
        
        Args:
            closure_results: Results from position closure operations
            
        Returns:
            bool: True if all positions were successfully closed
        """
        try:
            if not closure_results:
                return True
            
            # Check if all closures were successful
            successful_closures = [r for r in closure_results if r.success]
            failed_closures = [r for r in closure_results if not r.success]
            
            if failed_closures:
                logger.error(f"Position closure validation failed: {len(failed_closures)} failed closures")
                for failed in failed_closures:
                    logger.error(f"Failed: {failed.exchange}:{failed.symbol} - {failed.error_message}")
                return False
            
            # Verify positions are actually closed
            remaining_positions = await self.discover_all_positions()
            
            if remaining_positions:
                logger.warning(f"Position closure validation failed: {len(remaining_positions)} positions still open")
                for pos_id, position in remaining_positions.items():
                    logger.warning(f"Still open: {position.exchange}:{position.symbol} {position.size}")
                return False
            
            logger.info("Position closure validation successful: all positions closed")
            return True
            
        except Exception as e:
            logger.error(f"Position closure validation failed: {e}")
            return False
    
    async def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of current positions and closure history."""
        try:
            # Get current positions
            current_positions = await self.discover_all_positions()
            
            # Calculate position statistics
            total_positions = len(current_positions)
            total_value = sum(abs(p.size * p.current_price) for p in current_positions.values())
            total_pnl = sum(p.unrealized_pnl for p in current_positions.values())
            
            # Get recent closure history
            recent_closures = [
                r for r in self.closure_history 
                if time.time() - r.timestamp < 3600  # Last hour
            ]
            
            successful_closures = [r for r in recent_closures if r.success]
            failed_closures = [r for r in recent_closures if not r.success]
            
            return {
                "timestamp": time.time(),
                "current_positions": {
                    "count": total_positions,
                    "total_value": total_value,
                    "total_pnl": total_pnl,
                    "positions": [
                        {
                            "exchange": p.exchange,
                            "symbol": p.symbol,
                            "side": p.side,
                            "size": p.size,
                            "current_price": p.current_price,
                            "unrealized_pnl": p.unrealized_pnl
                        }
                        for p in current_positions.values()
                    ]
                },
                "recent_closures": {
                    "total": len(recent_closures),
                    "successful": len(successful_closures),
                    "failed": len(failed_closures),
                    "success_rate": len(successful_closures) / len(recent_closures) if recent_closures else 1.0
                },
                "exchange_status": {
                    name: connector.connected if hasattr(connector, 'connected') else True
                    for name, connector in self.exchange_connectors.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get position summary: {e}")
            return {}
    
    async def clear_closure_history(self):
        """Clear closure history."""
        self.closure_history.clear()
        logger.info("Cleared position closure history")
    
    async def get_manager_status(self) -> Dict[str, Any]:
        """Get position manager status and statistics."""
        try:
            return {
                "exchange_connectors": len(self.exchange_connectors),
                "current_positions": len(self.positions),
                "closure_history_size": len(self.closure_history),
                "max_retry_attempts": self.max_retry_attempts,
                "retry_delay": self.retry_delay,
                "closure_timeout": self.closure_timeout,
                "concurrent_closures": self.concurrent_closures
            }
            
        except Exception as e:
            logger.error(f"Failed to get manager status: {e}")
            return {}
