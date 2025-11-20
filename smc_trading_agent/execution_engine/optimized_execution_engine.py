"""
Ultra-Low Latency Execution Engine with Advanced Performance Optimization

This module implements a high-performance trading execution engine with sub-50ms latency,
advanced order routing, intelligent order splitting, and real-time market microstructure analysis.

Key Features:
- Ultra-low latency order execution (<50ms target)
- Intelligent order routing and market impact minimization
- Advanced order splitting algorithms for large positions
- Real-time market microstructure analysis
- Adaptive execution strategies based on market conditions
- Comprehensive execution analytics and performance metrics
- Smart order routing with latency optimization
- Advanced slippage control and execution quality monitoring
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import deque, defaultdict
import json
import aioredis
from aiohttp import ClientSession, ClientTimeout
import uvloop

# Set uvloop for better performance
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types supported by the execution engine"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    TWAP = "twap"  # Time-Weighted Average Price
    VWAP = "vwap"  # Volume-Weighted Average Price

class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order status tracking"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ExecutionStrategy(Enum):
    """Execution strategies for different market conditions"""
    AGGRESSIVE = "aggressive"  # Prioritize speed over price
    PASSIVE = "passive"  # Prioritize price over speed
    ADAPTIVE = "adaptive"  # Balance speed and price based on conditions
    IMPACT_MINIMIZING = "impact_minimizing"  # Minimize market impact
    LATENCY_OPTIMIZED = "latency_optimized"  # Ultra-low latency execution

@dataclass
class MarketData:
    """Real-time market data structure"""
    symbol: str
    bid: float
    ask: float
    bid_size: float
    ask_size: float
    last_price: float
    last_size: float
    timestamp: datetime
    spread: float = field(init=False)
    mid_price: float = field(init=False)

    def __post_init__(self):
        self.spread = self.ask - self.bid
        self.mid_price = (self.bid + self.ask) / 2

@dataclass
class OrderRequest:
    """Order request structure"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionReport:
    """Execution report for filled orders"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    execution_time: datetime
    latency_ms: float
    venue: str
    fee: float
    slippage: float
    market_impact: float
    strategy_used: str

@dataclass
class Order:
    """Order tracking structure"""
    request: OrderRequest
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    execution_reports: List[ExecutionReport] = field(default_factory=list)
    error_message: Optional[str] = None

    def __post_init__(self):
        self.remaining_quantity = self.request.quantity

class LatencyTracker:
    """Track and analyze execution latency"""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.latencies = deque(maxlen=window_size)
        self.lock = threading.Lock()

    def record_latency(self, latency_ms: float):
        """Record execution latency"""
        with self.lock:
            self.latencies.append(latency_ms)

    def get_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        with self.lock:
            if not self.latencies:
                return {
                    'count': 0,
                    'mean_ms': 0.0,
                    'median_ms': 0.0,
                    'p95_ms': 0.0,
                    'p99_ms': 0.0,
                    'max_ms': 0.0
                }

            latencies_array = np.array(self.latencies)
            return {
                'count': len(latencies_array),
                'mean_ms': float(np.mean(latencies_array)),
                'median_ms': float(np.median(latencies_array)),
                'p95_ms': float(np.percentile(latencies_array, 95)),
                'p99_ms': float(np.percentile(latencies_array, 99)),
                'max_ms': float(np.max(latencies_array))
            }

class MarketMicrostructureAnalyzer:
    """Analyze market microstructure for optimal execution"""

    def __init__(self):
        self.order_books = defaultdict(dict)
        self.trade_flows = defaultdict(list)
        self.volatility_cache = {}
        self.last_update = {}

    def update_order_book(self, symbol: str, market_data: MarketData):
        """Update order book data"""
        self.order_books[symbol] = {
            'bid': market_data.bid,
            'ask': market_data.ask,
            'bid_size': market_data.bid_size,
            'ask_size': market_data.ask_size,
            'spread': market_data.spread,
            'mid_price': market_data.mid_price,
            'timestamp': market_data.timestamp
        }
        self.last_update[symbol] = datetime.utcnow()

    def calculate_market_impact(self, symbol: str, quantity: float,
                              side: OrderSide) -> Dict[str, float]:
        """
        Calculate estimated market impact for a trade

        Args:
            symbol: Trading symbol
            quantity: Trade quantity
            side: Order side

        Returns:
            Market impact estimates
        """
        if symbol not in self.order_books:
            return {'impact_bps': 0.0, 'price_slippage': 0.0, 'confidence': 0.0}

        book = self.order_books[symbol]
        mid_price = book['mid_price']
        available_liquidity = book['bid_size'] if side == OrderSide.BUY else book['ask_size']

        # Simple impact model (would be enhanced with historical data)
        impact_ratio = min(quantity / available_liquidity, 1.0)
        impact_bps = impact_ratio * 50  # 50 bps max impact

        price_slippage = mid_price * (impact_bps / 10000)
        confidence = min(available_liquidity / quantity, 1.0)

        return {
            'impact_bps': impact_bps,
            'price_slippage': price_slippage,
            'confidence': confidence,
            'available_liquidity': available_liquidity,
            'spread_bps': book['spread'] / mid_price * 10000
        }

    def get_optimal_execution_venue(self, symbol: str) -> str:
        """Get optimal execution venue based on current market conditions"""
        # Simplified venue selection - would be enhanced with multi-exchange analysis
        return "primary"

class OrderSplitter:
    """Advanced order splitting algorithms for large positions"""

    def __init__(self, max_chunk_size: float = 1000.0, min_chunk_size: float = 10.0):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def split_order(self, order_request: OrderRequest,
                   market_conditions: Dict[str, Any]) -> List[OrderRequest]:
        """
        Split large order into optimal chunks

        Args:
            order_request: Original order request
            market_conditions: Current market conditions

        Returns:
            List of chunked order requests
        """
        if order_request.quantity <= self.max_chunk_size:
            return [order_request]

        # Calculate optimal chunk size based on market conditions
        volatility = market_conditions.get('volatility', 0.02)
        liquidity = market_conditions.get('liquidity_score', 0.5)

        # Adjust chunk size based on conditions
        if volatility > 0.03:  # High volatility
            chunk_multiplier = 0.5
        elif volatility > 0.015:  # Medium volatility
            chunk_multiplier = 0.75
        else:  # Low volatility
            chunk_multiplier = 1.0

        # Adjust for liquidity
        chunk_multiplier *= liquidity

        optimal_chunk_size = min(
            self.max_chunk_size * chunk_multiplier,
            order_request.quantity * 0.1,  # Max 10% per chunk
            order_request.quantity / 10   # Minimum 10 chunks
        )

        optimal_chunk_size = max(optimal_chunk_size, self.min_chunk_size)

        # Create chunks
        chunks = []
        remaining_quantity = order_request.quantity
        chunk_count = 0

        while remaining_quantity > 0:
            chunk_quantity = min(optimal_chunk_size, remaining_quantity)
            remaining_quantity -= chunk_quantity

            chunk_request = OrderRequest(
                id=f"{order_request.id}_chunk_{chunk_count}",
                symbol=order_request.symbol,
                side=order_request.side,
                order_type=order_request.order_type,
                quantity=chunk_quantity,
                price=order_request.price,
                stop_price=order_request.stop_price,
                time_in_force=order_request.time_in_force,
                strategy=order_request.strategy,
                metadata={
                    **order_request.metadata,
                    'parent_order_id': order_request.id,
                    'chunk_number': chunk_count,
                    'total_chunks': int(np.ceil(order_request.quantity / optimal_chunk_size))
                }
            )

            chunks.append(chunk_request)
            chunk_count += 1

        return chunks

class ExecutionEngine:
    """
    Ultra-low latency execution engine with advanced optimization
    Target latency: <50ms for market orders, <100ms for limit orders
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Performance tracking
        self.latency_tracker = LatencyTracker()
        self.execution_stats = defaultdict(int)

        # Order management
        self.orders: Dict[str, Order] = {}
        self.order_lock = threading.Lock()

        # Market data
        self.market_data: Dict[str, MarketData] = {}
        self.market_analyzer = MarketMicrostructureAnalyzer()

        # Order splitting
        self.order_splitter = OrderSplitter(
            max_chunk_size=self.config.get('max_chunk_size', 1000.0),
            min_chunk_size=self.config.get('min_chunk_size', 10.0)
        )

        # Connection pool for HTTP requests
        self.session: Optional[ClientSession] = None
        self.redis_pool: Optional[aioredis.ConnectionPool] = None

        # Execution queue with priority
        self.execution_queue = asyncio.PriorityQueue()
        self.is_running = False

        # Performance optimization
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.config.get('max_workers', 8),
            thread_name_prefix="execution_engine"
        )

        # Circuit breaker for execution failures
        self.circuit_breaker = {
            'failure_count': 0,
            'last_failure': None,
            'state': 'closed',  # closed, open, half-open
            'threshold': 5,
            'timeout': 60  # seconds
        }

        # Market regime detection
        self.current_regime = 'normal'
        self.regime_adjustments = {
            'normal': {'latency_target_ms': 50, 'slippage_tolerance_bps': 5},
            'volatile': {'latency_target_ms': 30, 'slippage_tolerance_bps': 10},
            'illiquid': {'latency_target_ms': 100, 'slippage_tolerance_bps': 15}
        }

        self.logger.info("Optimized Execution Engine initialized for ultra-low latency")

    async def start(self):
        """Start the execution engine"""
        if self.is_running:
            return

        self.is_running = True

        # Initialize HTTP session
        timeout = ClientTimeout(total=5.0, connect=1.0)
        self.session = ClientSession(timeout=timeout)

        # Initialize Redis connection for caching
        try:
            self.redis_pool = aioredis.ConnectionPool.from_url(
                "redis://localhost:6379",
                max_connections=20,
                retry_on_timeout=True
            )
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}")

        # Start execution workers
        for i in range(self.config.get('execution_workers', 4)):
            asyncio.create_task(self._execution_worker(f"worker_{i}"))

        # Start market data processor
        asyncio.create_task(self._market_data_processor())

        # Start performance monitor
        asyncio.create_task(self._performance_monitor())

        self.logger.info("Execution engine started successfully")

    async def stop(self):
        """Stop the execution engine"""
        self.is_running = False

        if self.session:
            await self.session.close()

        self.thread_pool.shutdown(wait=True)
        self.logger.info("Execution engine stopped")

    async def submit_order(self, order_request: OrderRequest) -> str:
        """
        Submit order for execution

        Args:
            order_request: Order to be executed

        Returns:
            Order ID
        """
        start_time = time.time()

        try:
            # Validate order
            validation_result = self._validate_order(order_request)
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])

            # Create order object
            order = Order(request=order_request)

            with self.order_lock:
                self.orders[order_request.id] = order

            # Check if order needs splitting
            market_conditions = self._get_market_conditions(order_request.symbol)
            if order_request.quantity > self.order_splitter.max_chunk_size:
                chunks = self.order_splitter.split_order(order_request, market_conditions)

                # Submit chunks to execution queue
                for chunk in chunks:
                    priority = self._calculate_order_priority(chunk, market_conditions)
                    await self.execution_queue.put((priority, chunk))

                    self.logger.info(
                        f"Order chunk submitted: {chunk.id}",
                        extra={
                            'order_id': chunk.id,
                            'parent_id': order_request.id,
                            'quantity': chunk.quantity,
                            'priority': priority
                        }
                    )
            else:
                # Submit single order
                priority = self._calculate_order_priority(order_request, market_conditions)
                await self.execution_queue.put((priority, order_request))

            # Update order status
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.utcnow()

            latency_ms = (time.time() - start_time) * 1000
            self.latency_tracker.record_latency(latency_ms)

            self.execution_stats['orders_submitted'] += 1

            self.logger.info(
                f"Order submitted: {order_request.id}",
                extra={
                    'order_id': order_request.id,
                    'symbol': order_request.symbol,
                    'side': order_request.side.value,
                    'quantity': order_request.quantity,
                    'latency_ms': latency_ms
                }
            )

            return order_request.id

        except Exception as e:
            self.logger.error(f"Order submission failed: {str(e)}", exc_info=True)
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order

        Args:
            order_id: Order ID to cancel

        Returns:
            Success status
        """
        with self.order_lock:
            order = self.orders.get(order_id)

        if not order:
            return False

        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False

        # Update order status
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()

        self.execution_stats['orders_cancelled'] += 1

        self.logger.info(f"Order cancelled: {order_id}")
        return True

    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status and details"""
        with self.order_lock:
            order = self.orders.get(order_id)

        if not order:
            return None

        return {
            'order_id': order_id,
            'status': order.status.value,
            'filled_quantity': order.filled_quantity,
            'remaining_quantity': order.remaining_quantity,
            'average_fill_price': order.average_fill_price,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'execution_reports': [report.__dict__ for report in order.execution_reports]
        }

    async def _execution_worker(self, worker_name: str):
        """Worker thread for order execution"""
        self.logger.info(f"Execution worker {worker_name} started")

        while self.is_running:
            try:
                # Get next order from queue
                priority, order_request = await asyncio.wait_for(
                    self.execution_queue.get(),
                    timeout=1.0
                )

                # Execute order
                await self._execute_order(order_request)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Execution worker {worker_name} error: {str(e)}", exc_info=True)

        self.logger.info(f"Execution worker {worker_name} stopped")

    async def _execute_order(self, order_request: OrderRequest):
        """Execute individual order with ultra-low latency"""
        start_time = time.time()

        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                await self._handle_execution_failure(order_request.id, "Circuit breaker open")
                return

            # Get current market data
            market_data = self.market_data.get(order_request.symbol)
            if not market_data:
                await self._handle_execution_failure(order_request.id, "No market data")
                return

            # Select execution strategy
            strategy = self._select_execution_strategy(order_request, market_data)

            # Execute based on order type and strategy
            execution_result = await self._execute_with_strategy(
                order_request, market_data, strategy
            )

            if execution_result['success']:
                await self._handle_execution_success(order_request.id, execution_result)
                self._reset_circuit_breaker()
            else:
                await self._handle_execution_failure(order_request.id, execution_result['error'])
                self._increment_circuit_breaker()

            # Record latency
            latency_ms = (time.time() - start_time) * 1000
            self.latency_tracker.record_latency(latency_ms)

            self.execution_stats['orders_executed'] += 1

        except Exception as e:
            self.logger.error(f"Order execution failed for {order_request.id}: {str(e)}", exc_info=True)
            await self._handle_execution_failure(order_request.id, str(e))
            self._increment_circuit_breaker()

    async def _execute_with_strategy(self, order_request: OrderRequest,
                                   market_data: MarketData, strategy: ExecutionStrategy) -> Dict[str, Any]:
        """Execute order using selected strategy"""

        if order_request.order_type == OrderType.MARKET:
            return await self._execute_market_order(order_request, market_data, strategy)
        elif order_request.order_type == OrderType.LIMIT:
            return await self._execute_limit_order(order_request, market_data, strategy)
        else:
            return await self._execute_advanced_order(order_request, market_data, strategy)

    async def _execute_market_order(self, order_request: OrderRequest,
                                   market_data: MarketData, strategy: ExecutionStrategy) -> Dict[str, Any]:
        """Execute market order with ultra-low latency"""

        execution_price = market_data.ask if order_request.side == OrderSide.BUY else market_data.bid

        # Calculate slippage
        if order_request.side == OrderSide.BUY:
            slippage = max(0, execution_price - market_data.mid_price)
        else:
            slippage = max(0, market_data.mid_price - execution_price)

        # Simulate execution (would be actual exchange API call)
        await asyncio.sleep(0.001)  # 1ms processing time

        return {
            'success': True,
            'execution_price': execution_price,
            'executed_quantity': order_request.quantity,
            'slippage': slippage,
            'venue': 'primary',
            'strategy_used': strategy.value,
            'timestamp': datetime.utcnow()
        }

    async def _execute_limit_order(self, order_request: OrderRequest,
                                   market_data: MarketData, strategy: ExecutionStrategy) -> Dict[str, Any]:
        """Execute limit order with intelligent placement"""

        # For limit orders, we would place the order and wait for fill
        # This is a simplified implementation

        if not order_request.price:
            # Set limit price if not provided
            if order_request.side == OrderSide.BUY:
                order_request.price = market_data.mid_price * 0.999  # 0.1% below mid
            else:
                order_request.price = market_data.mid_price * 1.001  # 0.1% above mid

        # Check if order can be filled immediately
        can_fill_immediately = (
            (order_request.side == OrderSide.BUY and order_request.price >= market_data.ask) or
            (order_request.side == OrderSide.SELL and order_request.price <= market_data.bid)
        )

        if can_fill_immediately:
            execution_price = market_data.ask if order_request.side == OrderSide.BUY else market_data.bid
        else:
            # Would place limit order and wait for fill (simplified)
            execution_price = order_request.price

        return {
            'success': True,
            'execution_price': execution_price,
            'executed_quantity': order_request.quantity if can_fill_immediately else 0.0,
            'slippage': 0.0,  # Limit orders have controlled slippage
            'venue': 'primary',
            'strategy_used': strategy.value,
            'timestamp': datetime.utcnow(),
            'immediate_fill': can_fill_immediately
        }

    async def _execute_advanced_order(self, order_request: OrderRequest,
                                     market_data: MarketData, strategy: ExecutionStrategy) -> Dict[str, Any]:
        """Execute advanced order types (TWAP, VWAP, Iceberg)"""

        # Simplified implementation for advanced orders
        if order_request.order_type == OrderType.TWAP:
            return await self._execute_twap_order(order_request, market_data, strategy)
        elif order_request.order_type == OrderType.VWAP:
            return await self._execute_vwap_order(order_request, market_data, strategy)
        elif order_request.order_type == OrderType.ICEBERG:
            return await self._execute_iceberg_order(order_request, market_data, strategy)
        else:
            return {'success': False, 'error': f'Unsupported order type: {order_request.order_type}'}

    async def _execute_twap_order(self, order_request: OrderRequest,
                                  market_data: MarketData, strategy: ExecutionStrategy) -> Dict[str, Any]:
        """Execute Time-Weighted Average Price order"""

        # Split order over time (simplified)
        num_slices = 5
        slice_quantity = order_request.quantity / num_slices

        total_executed = 0.0
        total_cost = 0.0

        for i in range(num_slices):
            # Execute slice
            slice_price = market_data.ask if order_request.side == OrderSide.BUY else market_data.bid
            total_executed += slice_quantity
            total_cost += slice_quantity * slice_price

            # Wait between slices (would be configurable)
            await asyncio.sleep(0.1)

        average_price = total_cost / total_executed if total_executed > 0 else 0.0

        return {
            'success': True,
            'execution_price': average_price,
            'executed_quantity': total_executed,
            'slippage': abs(average_price - market_data.mid_price),
            'venue': 'primary',
            'strategy_used': f'{strategy.value}_twap',
            'timestamp': datetime.utcnow(),
            'num_slices': num_slices
        }

    async def _execute_vwap_order(self, order_request: OrderRequest,
                                  market_data: MarketData, strategy: ExecutionStrategy) -> Dict[str, Any]:
        """Execute Volume-Weighted Average Price order"""

        # Simplified VWAP execution
        # In production, would track actual volume and execute accordingly

        # Predict volume for the time window
        predicted_volume = 1000.0  # Simplified
        participation_rate = min(order_request.quantity / predicted_volume, 0.2)

        # Execute with participation rate constraints
        execution_price = market_data.mid_price

        return {
            'success': True,
            'execution_price': execution_price,
            'executed_quantity': order_request.quantity,
            'slippage': 0.0,
            'venue': 'primary',
            'strategy_used': f'{strategy.value}_vwap',
            'participation_rate': participation_rate,
            'timestamp': datetime.utcnow()
        }

    async def _execute_iceberg_order(self, order_request: OrderRequest,
                                     market_data: MarketData, strategy: ExecutionStrategy) -> Dict[str, Any]:
        """Execute Iceberg order (hidden quantity)"""

        # Split visible and hidden quantities
        visible_quantity = min(order_request.quantity * 0.2, 100.0)  # 20% visible, max 100
        hidden_quantity = order_request.quantity - visible_quantity

        # Execute visible quantity first
        visible_price = market_data.ask if order_request.side == OrderSide.BUY else market_data.bid

        return {
            'success': True,
            'execution_price': visible_price,
            'executed_quantity': visible_quantity,
            'slippage': 0.0,
            'venue': 'primary',
            'strategy_used': f'{strategy.value}_iceberg',
            'visible_quantity': visible_quantity,
            'hidden_quantity': hidden_quantity,
            'timestamp': datetime.utcnow()
        }

    async def _handle_execution_success(self, order_id: str, execution_result: Dict[str, Any]):
        """Handle successful order execution"""
        with self.order_lock:
            order = self.orders.get(order_id)

        if not order:
            return

        # Create execution report
        execution_report = ExecutionReport(
            order_id=order_id,
            symbol=order.request.symbol,
            side=order.request.side,
            quantity=execution_result['executed_quantity'],
            price=execution_result['execution_price'],
            execution_time=execution_result['timestamp'],
            latency_ms=0.0,  # Would be calculated
            venue=execution_result['venue'],
            fee=0.0,  # Would be calculated
            slippage=execution_result['slippage'],
            market_impact=0.0,  # Would be calculated
            strategy_used=execution_result['strategy_used']
        )

        # Update order
        order.execution_reports.append(execution_report)
        order.filled_quantity += execution_result['executed_quantity']
        order.remaining_quantity -= execution_result['executed_quantity']

        # Calculate average fill price
        if order.filled_quantity > 0:
            total_cost = sum([r.quantity * r.price for r in order.execution_reports])
            order.average_fill_price = total_cost / order.filled_quantity

        # Update status
        if order.remaining_quantity <= 0:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIAL_FILLED

        order.updated_at = datetime.utcnow()

        self.logger.info(
            f"Order execution success: {order_id}",
            extra={
                'order_id': order_id,
                'executed_quantity': execution_result['executed_quantity'],
                'execution_price': execution_result['execution_price'],
                'status': order.status.value
            }
        )

    async def _handle_execution_failure(self, order_id: str, error_message: str):
        """Handle failed order execution"""
        with self.order_lock:
            order = self.orders.get(order_id)

        if not order:
            return

        order.status = OrderStatus.REJECTED
        order.error_message = error_message
        order.updated_at = datetime.utcnow()

        self.logger.error(
            f"Order execution failed: {order_id}",
            extra={
                'order_id': order_id,
                'error': error_message,
                'status': order.status.value
            }
        )

    def _validate_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Validate order request"""
        if order_request.quantity <= 0:
            return {'valid': False, 'error': 'Invalid quantity'}

        if order_request.order_type == OrderType.LIMIT and not order_request.price:
            return {'valid': False, 'error': 'Limit orders require price'}

        if order_request.order_type == OrderType.STOP and not order_request.stop_price:
            return {'valid': False, 'error': 'Stop orders require stop price'}

        return {'valid': True}

    def _calculate_order_priority(self, order_request: OrderRequest,
                                market_conditions: Dict[str, Any]) -> int:
        """Calculate priority for order queue"""
        base_priority = 1000

        # Adjust based on strategy
        if order_request.strategy == ExecutionStrategy.AGGRESSIVE:
            base_priority -= 500
        elif order_request.strategy == ExecutionStrategy.LATENCY_OPTIMIZED:
            base_priority -= 800

        # Adjust based on market conditions
        if market_conditions.get('volatility', 0) > 0.03:
            base_priority -= 200  # Higher priority in volatile markets

        # Adjust based on order size
        if order_request.quantity > 1000:
            base_priority -= 100

        return int(base_priority)

    def _select_execution_strategy(self, order_request: OrderRequest,
                                 market_data: MarketData) -> ExecutionStrategy:
        """Select optimal execution strategy"""

        # Use requested strategy if specified
        if order_request.strategy != ExecutionStrategy.ADAPTIVE:
            return order_request.strategy

        # Adaptive strategy selection
        spread_bps = (market_data.spread / market_data.mid_price) * 10000

        if spread_bps > 10:  # Wide spread
            return ExecutionStrategy.PASSIVE
        elif spread_bps < 2:  # Tight spread
            return ExecutionStrategy.AGGRESSIVE
        else:
            return ExecutionStrategy.IMPACT_MINIMIZING

    def _get_market_conditions(self, symbol: str) -> Dict[str, Any]:
        """Get current market conditions for symbol"""
        market_data = self.market_data.get(symbol)
        if not market_data:
            return {'volatility': 0.02, 'liquidity_score': 0.5, 'regime': 'normal'}

        # Simplified market conditions
        spread_bps = (market_data.spread / market_data.mid_price) * 10000

        if spread_bps > 10:
            regime = 'illiquid'
            liquidity_score = 0.3
        elif spread_bps > 5:
            regime = 'volatile'
            liquidity_score = 0.6
        else:
            regime = 'normal'
            liquidity_score = 0.8

        return {
            'volatility': 0.02,  # Would be calculated from historical data
            'liquidity_score': liquidity_score,
            'regime': regime,
            'spread_bps': spread_bps
        }

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        cb = self.circuit_breaker

        if cb['state'] == 'open':
            if time.time() - cb['last_failure'] > cb['timeout']:
                cb['state'] = 'half-open'
                return False
            return True

        return False

    def _increment_circuit_breaker(self):
        """Increment circuit breaker failure count"""
        cb = self.circuit_breaker
        cb['failure_count'] += 1
        cb['last_failure'] = time.time()

        if cb['failure_count'] >= cb['threshold']:
            cb['state'] = 'open'
            self.logger.warning("Circuit breaker opened due to repeated failures")

    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful execution"""
        cb = self.circuit_breaker
        cb['failure_count'] = 0
        cb['state'] = 'closed'

    async def _market_data_processor(self):
        """Process market data updates"""
        while self.is_running:
            try:
                # Update market data (would subscribe to real-time feeds)
                for symbol in self.market_data.keys():
                    # Simulate market data updates
                    await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Market data processor error: {str(e)}")
                await asyncio.sleep(1)

    async def _performance_monitor(self):
        """Monitor execution performance"""
        while self.is_running:
            try:
                # Get latency stats
                latency_stats = self.latency_tracker.get_stats()

                # Log performance metrics
                self.logger.info(
                    "Execution engine performance metrics",
                    extra={
                        'latency_mean_ms': latency_stats['mean_ms'],
                        'latency_p95_ms': latency_stats['p95_ms'],
                        'latency_p99_ms': latency_stats['p99_ms'],
                        'orders_submitted': self.execution_stats['orders_submitted'],
                        'orders_executed': self.execution_stats['orders_executed'],
                        'orders_cancelled': self.execution_stats['orders_cancelled']
                    }
                )

                # Check if latency targets are being met
                target_latency = self.regime_adjustments.get(self.current_regime, {}).get('latency_target_ms', 50)
                if latency_stats['mean_ms'] > target_latency * 1.5:
                    self.logger.warning(
                        f"Latency target exceeded: {latency_stats['mean_ms']:.2f}ms > {target_latency}ms"
                    )

                await asyncio.sleep(60)  # Monitor every minute

            except Exception as e:
                self.logger.error(f"Performance monitor error: {str(e)}")
                await asyncio.sleep(60)

    async def update_market_data(self, market_data: MarketData):
        """Update market data for a symbol"""
        self.market_data[market_data.symbol] = market_data
        self.market_analyzer.update_order_book(market_data.symbol, market_data)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        latency_stats = self.latency_tracker.get_stats()

        return {
            'latency_stats': latency_stats,
            'execution_stats': dict(self.execution_stats),
            'circuit_breaker': {
                'state': self.circuit_breaker['state'],
                'failure_count': self.circuit_breaker['failure_count']
            },
            'market_regime': self.current_regime,
            'active_orders': len([o for o in self.orders.values() if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]])
        }

# Factory function for easy instantiation
def create_optimized_execution_engine(config: Optional[Dict[str, Any]] = None) -> ExecutionEngine:
    """Create optimized execution engine instance"""
    return ExecutionEngine(config)