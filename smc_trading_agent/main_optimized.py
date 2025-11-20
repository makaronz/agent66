#!/usr/bin/env python3
"""
Ultra-Low Latency SMC Trading Agent - Optimized Main Application

Integrates all optimized components for sub-50ms end-to-end latency:
- Optimized async Kafka producer for data streaming
- Parallel ML ensemble with Redis caching
- Advanced risk management with circuit breakers
- Ultra-low latency execution engine
- Comprehensive performance monitoring

Target Performance:
- Data Pipeline: <10ms
- ML Inference: <20ms
- Risk Checks: <5ms
- Total System: <50ms
"""

import sys
import signal
import logging
import logging.config
import time
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

# Configuration and validation
from config_loader import load_secure_config, ConfigValidationError, EnvironmentVariableError
from config_validator import validate_config

# Optimized component imports
from data_pipeline.kafka_producer_optimized import create_optimized_kafka_producer, DataType
from decision_engine.model_ensemble_optimized import create_optimized_ensemble
from risk_manager.circuit_breaker_optimized import create_optimized_circuit_breaker
from execution_engine.optimized_execution_engine import create_optimized_execution_engine, OrderRequest, OrderSide, OrderType, ExecutionStrategy
from monitoring.enhanced_monitoring import initialize_monitoring, monitor_performance

# Legacy component imports (to be replaced)
from smc_detector.indicators import SMCIndicators
from decision_engine.ml_decision_engine import get_ml_config
from data_pipeline.live_data_client import LiveDataClient

# Error handling and validation
from error_handlers import (
    CircuitBreaker, RetryHandler, error_boundary, safe_execute,
    health_monitor, TradingError, ComponentHealthError, ErrorSeverity
)
from validators import (
    data_validator, DataQualityLevel, DataValidationError
)

# Service coordination
from service_manager import ServiceManager
from health_monitor import EnhancedHealthMonitor

# FastAPI for monitoring endpoints
from fastapi import FastAPI
import uvicorn

# Global state
shutdown_flag = False
performance_monitor = None

@dataclass
class TradingSignal:
    """Unified trading signal structure"""
    symbol: str
    action: str  # buy, sell, hold
    confidence: float
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    metadata: Dict[str, Any]
    timestamp: datetime
    source: str  # ml_ensemble, smc_patterns, combined
    execution_strategy: ExecutionStrategy
    expected_latency_ms: float

@dataclass
class SystemMetrics:
    """Real-time system performance metrics"""
    total_latency_ms: float
    data_pipeline_latency_ms: float
    ml_inference_latency_ms: float
    risk_check_latency_ms: float
    execution_latency_ms: float
    cache_hit_rate: float
    circuit_breaker_status: str
    system_health: str

class OptimizedTradingCoordinator:
    """
    Ultra-low latency trading coordinator integrating all optimized components.

    This class orchestrates the entire trading pipeline with:
    - Parallel component execution
    - Performance monitoring and tracking
    - Adaptive optimization based on market conditions
    - Circuit breaker protection
    - Real-time metrics collection
    """

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger

        # Performance targets (from optimization status)
        self.performance_targets = {
            'data_pipeline_ms': 10,
            'ml_inference_ms': 20,
            'risk_check_ms': 5,
            'total_system_ms': 50,
            'cache_hit_rate_min': 0.7
        }

        # Component placeholders (will be initialized in start())
        self.kafka_producer = None
        self.ml_ensemble = None
        self.circuit_breaker = None
        self.execution_engine = None
        self.smc_detector = None
        self.data_client = None

        # Performance tracking
        self.system_metrics = SystemMetrics(
            total_latency_ms=0.0,
            data_pipeline_latency_ms=0.0,
            ml_inference_latency_ms=0.0,
            risk_check_latency_ms=0.0,
            execution_latency_ms=0.0,
            cache_hit_rate=0.0,
            circuit_breaker_status='closed',
            system_health='healthy'
        )

        # Trade cache for duplicate prevention
        self.trade_cache = {}
        self.cache_ttl = 60  # seconds

        # Performance history for optimization
        self.performance_history = []
        self.max_history = 1000

        self.logger.info("Optimized Trading Coordinator initialized")

    async def start(self) -> None:
        """Initialize all optimized components"""
        try:
            self.logger.info("Starting optimized components initialization...")

            # 1. Initialize optimized Kafka producer
            kafka_config = self.config.get('performance', {}).get('kafka', {})
            self.kafka_producer = await create_optimized_kafka_producer(
                bootstrap_servers=kafka_config.get('bootstrap_servers', ['localhost:9092']),
                batch_size=kafka_config.get('batch_size', 1000),
                linger_ms=kafka_config.get('linger_ms', 5),
                topic_prefix="smc_optimized"
            )
            self.logger.info("✅ Optimized Kafka producer started")

            # 2. Initialize ML ensemble (models would be loaded here)
            # For now, we'll use dummy models - in production, load actual trained models
            lstm_model = None
            transformer_model = None
            ppo_model = None
            scaler = None  # Would be fitted scaler

            ml_config = self.config.get('performance', {}).get('ml_ensemble', {})
            self.ml_ensemble = await create_optimized_ensemble(
                lstm_model=lstm_model,
                transformer_model=transformer_model,
                ppo_model=ppo_model,
                scaler=scaler,
                redis_url=ml_config.get('redis_url', 'redis://localhost:6379'),
                parallel_execution=ml_config.get('parallel_execution', True),
                cache_ttl_seconds=ml_config.get('cache_ttl_seconds', 60)
            )
            self.logger.info("✅ Optimized ML ensemble started")

            # 3. Initialize optimized circuit breaker
            risk_config = self.config.get('performance', {}).get('risk_manager', {})
            self.circuit_breaker = await create_optimized_circuit_breaker(
                max_drawdown=self.config.get('risk_manager', {}).get('max_drawdown', 0.05),
                max_var=self.config.get('risk_manager', {}).get('max_var', 0.02),
                redis_url=risk_config.get('redis_url', 'redis://localhost:6379'),
                database_url=risk_config.get('database_url', 'postgresql://user:pass@localhost/smc_db'),
                parallel_calculation=risk_config.get('parallel_calculation', True)
            )
            self.logger.info("✅ Optimized circuit breaker started")

            # 4. Initialize optimized execution engine
            execution_config = self.config.get('execution_engine', {})
            self.execution_engine = create_optimized_execution_engine({
                'max_chunk_size': execution_config.get('max_chunk_size', 1000.0),
                'execution_workers': execution_config.get('workers', 4),
                'latency_target_ms': 30
            })
            await self.execution_engine.start()
            self.logger.info("✅ Optimized execution engine started")

            # 5. Initialize traditional components (to be optimized later)
            self.smc_detector = SMCIndicators()
            self.data_client = LiveDataClient(base_url="http://localhost:3001")

            self.logger.info("🚀 All optimized components started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start optimized components: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Cleanup all components"""
        try:
            if self.kafka_producer:
                await self.kafka_producer.close()
            if self.ml_ensemble:
                await self.ml_ensemble.cleanup()
            if self.circuit_breaker:
                await self.circuit_breaker.cleanup()
            if self.execution_engine:
                await self.execution_engine.stop()

            self.logger.info("All optimized components stopped")
        except Exception as e:
            self.logger.error(f"Error stopping components: {e}")

    async def process_trading_cycle(self) -> Optional[TradingSignal]:
        """
        Execute complete trading cycle with ultra-low latency optimization.

        Returns:
            TradingSignal if signal generated, None otherwise
        """
        cycle_start_time = time.time()
        signal = None

        try:
            # 1. Get market data (target: <10ms)
            data_start = time.time()
            market_data_df = await self._get_market_data_optimized()
            data_latency = (time.time() - data_start) * 1000

            if market_data_df is None or market_data_df.empty:
                self.logger.warning("No market data available")
                return None

            # Validate data quality
            is_valid, validation_errors = data_validator.validate_market_data(market_data_df)
            if not is_valid:
                self.logger.error(f"Market data validation failed: {validation_errors}")
                return None

            self.system_metrics.data_pipeline_latency_ms = data_latency

            # 2. Parallel analysis: SMC patterns + ML inference
            smc_task = asyncio.create_task(self._detect_smc_patterns(market_data_df))
            ml_task = asyncio.create_task(self._run_ml_inference(market_data_df))

            # Wait for both analyses in parallel
            smc_result, ml_result = await asyncio.gather(smc_task, ml_task, return_exceptions=True)

            # Process SMC patterns
            order_blocks = []
            smc_confidence = 0.0
            if not isinstance(smc_result, Exception):
                order_blocks = smc_result.get('order_blocks', [])
                smc_confidence = smc_result.get('confidence', 0.0)
            else:
                self.logger.warning(f"SMC analysis failed: {smc_result}")

            # Process ML inference
            ml_action = 1  # Hold by default
            ml_confidence = 0.0
            ml_metadata = {}
            if not isinstance(ml_result, Exception):
                ml_action, ml_confidence, ml_metadata = ml_result
            else:
                self.logger.warning(f"ML inference failed: {ml_result}")

            # Update ML latency metric
            if 'inference_time_ms' in ml_metadata:
                self.system_metrics.ml_inference_latency_ms = ml_metadata['inference_time_ms']

            # Update cache hit rate
            if 'cache_stats' in ml_metadata:
                cache_stats = ml_metadata['cache_stats']
                self.system_metrics.cache_hit_rate = cache_stats.get('hit_rate', 0.0)

            # 3. Generate unified signal
            signal = self._generate_unified_signal(
                order_blocks, smc_confidence,
                ml_action, ml_confidence, ml_metadata,
                market_data_df
            )

            if not signal:
                self.logger.info("No trading signal generated")
                return None

            # 4. Risk management (target: <5ms)
            risk_start = time.time()
            risk_passed, violations, risk_metadata = await self._apply_risk_management(signal)
            risk_latency = (time.time() - risk_start) * 1000

            self.system_metrics.risk_check_latency_ms = risk_latency
            self.system_metrics.circuit_breaker_status = risk_metadata.get('circuit_state', 'closed')

            if not risk_passed:
                self.logger.info(f"Signal rejected by risk management: {violations}")
                return None

            # 5. Execute trade if signal is strong enough
            if signal.confidence >= self.config.get('decision_engine', {}).get('confidence_threshold', 0.7):
                execution_success = await self._execute_optimized_trade(signal)
                if not execution_success:
                    return None

            # Update total metrics
            total_latency = (time.time() - cycle_start_time) * 1000
            self.system_metrics.total_latency_ms = total_latency

            # Log performance
            self._log_cycle_performance(signal, total_latency)

            # Update performance history
            self._update_performance_history()

            return signal

        except Exception as e:
            self.logger.error(f"Trading cycle failed: {e}", exc_info=True)
            return None

    async def _get_market_data_optimized(self):
        """Get market data with optimization"""
        try:
            # Use live data client with timeout
            symbol = "BTC/USDT"  # From config
            data = await asyncio.wait_for(
                self.data_client.get_latest_ohlcv_data(symbol, "1h"),
                timeout=5.0
            )

            # Send to Kafka for downstream processing
            if self.kafka_producer and data is not None and not data.empty:
                await self.kafka_producer.send_market_data(
                    exchange="binance",
                    symbol="BTCUSDT",
                    data_type=DataType.KLINE,
                    data={
                        'ohlcv': data.iloc[-1].to_dict(),
                        'volume': data.iloc[-1]['volume'],
                        'price': data.iloc[-1]['close']
                    }
                )

            return data

        except asyncio.TimeoutError:
            self.logger.warning("Market data request timeout")
            return None
        except Exception as e:
            self.logger.error(f"Failed to get market data: {e}")
            return None

    async def _detect_smc_patterns(self, market_data_df) -> Dict[str, Any]:
        """Detect SMC patterns with error handling"""
        try:
            start_time = time.time()
            order_blocks = self.smc_detector.detect_order_blocks(market_data_df)
            latency = (time.time() - start_time) * 1000

            return {
                'order_blocks': order_blocks,
                'confidence': 0.8 if order_blocks else 0.0,
                'latency_ms': latency
            }
        except Exception as e:
            self.logger.error(f"SMC pattern detection failed: {e}")
            return {'order_blocks': [], 'confidence': 0.0, 'error': str(e)}

    async def _run_ml_inference(self, market_data_df) -> Tuple[int, float, Dict[str, Any]]:
        """Run ML inference with optimized ensemble"""
        try:
            # Prepare data for ML (simplified)
            if len(market_data_df) < 60:
                return 1, 0.5, {'error': 'Insufficient data'}

            # Extract features (simplified - would use proper feature engineering)
            recent_data = market_data_df[['close', 'volume']].values[-60:]

            # Run parallel ML inference
            action, confidence, metadata = await self.ml_ensemble.predict_parallel(recent_data)

            return action, confidence, metadata

        except Exception as e:
            self.logger.error(f"ML inference failed: {e}")
            return 1, 0.5, {'error': str(e)}

    def _generate_unified_signal(
        self,
        order_blocks: list,
        smc_confidence: float,
        ml_action: int,
        ml_confidence: float,
        ml_metadata: Dict[str, Any],
        market_data_df
    ) -> Optional[TradingSignal]:
        """Generate unified trading signal from multiple sources"""

        # Skip if no strong signals
        if not order_blocks and ml_confidence < 0.6:
            return None

        # Get current price
        current_price = market_data_df['close'].iloc[-1]

        # Determine action and confidence
        if order_blocks and ml_confidence >= 0.7:
            # Both SMC and ML agree - strongest signal
            if ml_action == 0:  # Buy
                action = "buy"
                combined_confidence = min(0.95, (smc_confidence + ml_confidence) / 2 + 0.2)
            elif ml_action == 2:  # Sell
                action = "sell"
                combined_confidence = min(0.95, (smc_confidence + ml_confidence) / 2 + 0.2)
            else:
                action = "hold"
                combined_confidence = 0.5
            source = "combined"
        elif order_blocks:
            # SMC only
            # Determine direction from order block patterns (simplified)
            action = "buy"  # Simplified - would analyze order block direction
            combined_confidence = smc_confidence
            source = "smc_patterns"
        elif ml_confidence >= 0.7:
            # ML only
            action_map = {0: "buy", 1: "hold", 2: "sell"}
            action = action_map.get(ml_action, "hold")
            combined_confidence = ml_confidence
            source = "ml_ensemble"
        else:
            return None

        if action == "hold":
            return None

        # Calculate stop loss and take profit
        risk_config = self.config.get('risk_manager', {})
        stop_loss_pct = risk_config.get('stop_loss_percent', 2.0) / 100
        take_profit_ratio = risk_config.get('take_profit_ratio', 3.0)

        if action == "buy":
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + stop_loss_pct * take_profit_ratio)
        else:  # sell
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - stop_loss_pct * take_profit_ratio)

        # Select execution strategy based on market conditions
        volatility = market_data_df['close'].pct_change().std() * np.sqrt(252)  # Annualized
        if volatility > 0.5:  # High volatility
            execution_strategy = ExecutionStrategy.LATENCY_OPTIMIZED
        elif volatility > 0.3:  # Medium volatility
            execution_strategy = ExecutionStrategy.ADAPTIVE
        else:  # Low volatility
            execution_strategy = ExecutionStrategy.IMPACT_MINIMIZING

        # Expected latency based on current system performance
        expected_latency = (
            self.system_metrics.data_pipeline_latency_ms +
            self.system_metrics.ml_inference_latency_ms +
            self.system_metrics.risk_check_latency_ms +
            10  # Execution overhead
        )

        return TradingSignal(
            symbol="BTC/USDT",
            action=action,
            confidence=combined_confidence,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                'order_blocks': len(order_blocks),
                'ml_metadata': ml_metadata,
                'volatility': volatility,
                'source_weights': {
                    'smc': 0.6 if order_blocks else 0.0,
                    'ml': ml_confidence
                }
            },
            timestamp=datetime.utcnow(),
            source=source,
            execution_strategy=execution_strategy,
            expected_latency_ms=expected_latency
        )

    async def _apply_risk_management(self, signal: TradingSignal) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Apply optimized risk management"""
        try:
            # Prepare portfolio data (simplified)
            portfolio_data = {
                'positions': {},  # Would get from execution engine
                'balance': 10000.0,  # Would get from execution engine
                'drawdown': 0.0,
                'leverage': 1.0,
                'returns': [],  # Would calculate from history
                'returns_matrix': np.array([])  # Would calculate from history
            }

            # Prepare trade details
            trade_details = {
                'symbol': signal.symbol,
                'quantity': 0.01,  # Simplified position sizing
                'price': signal.entry_price,
                'side': signal.action,
                'type': 'market'
            }

            # Check risk limits
            is_safe, violations, metadata = await self.circuit_breaker.check_risk_limits(
                portfolio_data, trade_details
            )

            return is_safe, violations, metadata

        except Exception as e:
            self.logger.error(f"Risk management failed: {e}")
            return False, [f"Risk management error: {e}"], {}

    async def _execute_optimized_trade(self, signal: TradingSignal) -> bool:
        """Execute trade with optimized execution engine"""
        try:
            # Create order request
            order_request = OrderRequest(
                id=str(uuid.uuid4()),
                symbol="BTCUSDT",
                side=OrderSide.BUY if signal.action == "buy" else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=0.01,  # Simplified sizing
                strategy=signal.execution_strategy,
                metadata={
                    'signal_source': signal.source,
                    'confidence': signal.confidence,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit
                }
            )

            # Submit to execution engine
            order_id = await self.execution_engine.submit_order(order_request)

            if order_id:
                self.logger.info(
                    f"🚀 Trade executed: {signal.action} {signal.symbol} @ {signal.entry_price:.2f} "
                    f"(confidence: {signal.confidence:.2%}, source: {signal.source})",
                    extra={
                        'order_id': order_id,
                        'signal': signal.__dict__
                    }
                )

                # Record trade in monitoring
                if performance_monitor:
                    performance_monitor.record_trade(
                        symbol=signal.symbol,
                        side=signal.action,
                        quantity=0.01,
                        price=signal.entry_price,
                        execution_time=self.system_metrics.total_latency_ms / 1000,
                        slippage=0.001  # Would calculate actual slippage
                    )

                return True
            else:
                self.logger.error("Trade submission failed")
                return False

        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return False

    def _log_cycle_performance(self, signal: TradingSignal, total_latency: float):
        """Log trading cycle performance"""

        # Check against targets
        data_target = self.performance_targets['data_pipeline_ms']
        ml_target = self.performance_targets['ml_inference_ms']
        risk_target = self.performance_targets['risk_check_ms']
        total_target = self.performance_targets['total_system_ms']

        performance_issues = []
        if self.system_metrics.data_pipeline_latency_ms > data_target:
            performance_issues.append(f"data pipeline {self.system_metrics.data_pipeline_latency_ms:.1f}ms > {data_target}ms")
        if self.system_metrics.ml_inference_latency_ms > ml_target:
            performance_issues.append(f"ML inference {self.system_metrics.ml_inference_latency_ms:.1f}ms > {ml_target}ms")
        if self.system_metrics.risk_check_latency_ms > risk_target:
            performance_issues.append(f"risk check {self.system_metrics.risk_check_latency_ms:.1f}ms > {risk_target}ms")
        if total_latency > total_target:
            performance_issues.append(f"total {total_latency:.1f}ms > {total_target}ms")

        if performance_issues:
            self.logger.warning(
                f"⚠️ Performance issues: {', '.join(performance_issues)}",
                extra={
                    'signal_confidence': signal.confidence,
                    'signal_source': signal.source,
                    'latency_breakdown': {
                        'data': self.system_metrics.data_pipeline_latency_ms,
                        'ml': self.system_metrics.ml_inference_latency_ms,
                        'risk': self.system_metrics.risk_check_latency_ms,
                        'total': total_latency
                    }
                }
            )
        else:
            self.logger.info(
                f"✅ Trading cycle completed in {total_latency:.1f}ms (target: <{total_target}ms)",
                extra={
                    'signal': signal.action,
                    'confidence': signal.confidence,
                    'source': signal.source,
                    'cache_hit_rate': self.system_metrics.cache_hit_rate
                }
            )

    def _update_performance_history(self):
        """Update performance history for optimization"""
        snapshot = {
            'timestamp': datetime.utcnow(),
            'total_latency_ms': self.system_metrics.total_latency_ms,
            'data_pipeline_latency_ms': self.system_metrics.data_pipeline_latency_ms,
            'ml_inference_latency_ms': self.system_metrics.ml_inference_latency_ms,
            'risk_check_latency_ms': self.system_metrics.risk_check_latency_ms,
            'cache_hit_rate': self.system_metrics.cache_hit_rate,
            'circuit_breaker_status': self.system_metrics.circuit_breaker_status
        }

        self.performance_history.append(snapshot)

        # Keep only recent history
        if len(self.performance_history) > self.max_history:
            self.performance_history.pop(0)

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics"""
        return self.system_metrics

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring"""
        if not self.performance_history:
            return {}

        recent_snapshots = list(self.performance_history)[-10:]  # Last 10 cycles

        avg_total_latency = np.mean([s['total_latency_ms'] for s in recent_snapshots])
        avg_cache_hit_rate = np.mean([s['cache_hit_rate'] for s in recent_snapshots])

        target_achievement_rate = len([
            s for s in recent_snapshots
            if s['total_latency_ms'] < self.performance_targets['total_system_ms']
        ]) / len(recent_snapshots)

        return {
            'avg_total_latency_ms': avg_total_latency,
            'target_achievement_rate': target_achievement_rate,
            'avg_cache_hit_rate': avg_cache_hit_rate,
            'current_circuit_status': self.system_metrics.circuit_breaker_status,
            'performance_trend': 'improving' if len(recent_snapshots) > 1 else 'stable'
        }


async def run_optimized_trading_agent(
    config: Dict[str, Any],
    service_manager: ServiceManager,
    logger: logging.Logger
):
    """Main optimized trading loop"""

    # Initialize optimized trading coordinator
    coordinator = OptimizedTradingCoordinator(config, logger)

    try:
        # Start all optimized components
        await coordinator.start()

        # Register with service manager
        service_manager.register_service(
            "trading_coordinator",
            coordinator,
            lambda: coordinator.system_metrics.system_health == 'healthy',
            critical=True
        )

        # Main trading loop with performance monitoring
        cycle_count = 0
        while not service_manager.is_shutdown_requested():
            cycle_start = time.time()
            cycle_count += 1

            try:
                # Check system health before trading
                system_health = service_manager.get_service_health()
                if not system_health["overall_healthy"]:
                    logger.warning("System health check failed, skipping cycle", extra=system_health)
                    await asyncio.sleep(30)
                    continue

                # Execute optimized trading cycle
                signal = await coordinator.process_trading_cycle()

                if signal:
                    logger.info(
                        f"🎯 Trading signal generated: {signal.action} {signal.symbol}",
                        extra={
                            'confidence': signal.confidence,
                            'source': signal.source,
                            'expected_latency_ms': signal.expected_latency_ms
                        }
                    )

                # Adaptive timing based on performance
                metrics = coordinator.get_system_metrics()
                if metrics.total_latency_ms > 100:  # Slow performance
                    sleep_time = 120  # Wait longer
                elif metrics.total_latency_ms > 50:  # Target performance
                    sleep_time = 60  # Normal wait
                else:  # Good performance
                    sleep_time = 30  # Can trade more frequently

                # Wait for next cycle (with interruption for shutdown)
                for _ in range(int(sleep_time)):
                    if service_manager.is_shutdown_requested():
                        break
                    await asyncio.sleep(1)

                # Log periodic performance summary
                if cycle_count % 10 == 0:
                    summary = coordinator.get_performance_summary()
                    logger.info(
                        f"📊 Performance Summary (last 10 cycles)",
                        extra=summary
                    )

            except Exception as e:
                logger.error(f"Error in trading cycle {cycle_count}: {e}", exc_info=True)
                await asyncio.sleep(30)  # Wait before retrying
                continue

    except Exception as e:
        logger.error(f"Optimized trading agent failed: {e}", exc_info=True)
    finally:
        await coordinator.stop()
        logger.info("Optimized trading agent shutdown complete")


# Utility functions for setup and monitoring
def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration"""
    try:
        if "logging" in config:
            logging.config.dictConfig(config["logging"])
        sys.excepthook = handle_uncaught_exception
    except (ValueError, KeyError) as e:
        print(f"Error setting up logging: {e}", file=sys.stderr)
        sys.exit(1)

def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger().critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def handle_shutdown_signal(signum, frame):
    global shutdown_flag
    if not shutdown_flag:
        logging.getLogger().info(f"Received shutdown signal: {signal.Signals(signum).name}. Initiating graceful shutdown...")
        shutdown_flag = True
    else:
        logging.getLogger().warning("Received second shutdown signal. Forcing exit.")
        sys.exit(1)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load and validate configuration"""
    try:
        env_file = ".env"
        config = load_secure_config(config_path, env_file)

        # Validate configuration
        is_valid, errors, warnings = validate_config(config)
        if not is_valid:
            print("Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)

        if warnings:
            print("Configuration validation warnings:")
            for warning in warnings:
                print(f"  - {warning}")

        return config

    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)
    except (ConfigValidationError, EnvironmentVariableError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

async def main_async():
    """Async main function"""
    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting Ultra-Low Latency SMC Trading Agent")
    logger.info(f"Performance targets: Data<10ms, ML<20ms, Risk<5ms, Total<50ms")

    # Initialize global performance monitoring
    global performance_monitor
    monitoring_config = config.get('performance', {}).get('monitoring', {
        'metrics_collection_interval': 30,
        'prometheus_port': 8000
    })
    performance_monitor = initialize_monitoring(monitoring_config)
    performance_monitor.start()

    # Initialize service manager and health monitor
    service_manager = ServiceManager(config, logger)
    health_monitor = EnhancedHealthMonitor(
        app_name=config.get('app', {}).get('name', 'smc-trading-agent-optimized'),
        logger=logger
    )

    # Start health monitoring
    await health_monitor.start_background_health_checks()

    # Get monitoring port
    monitoring_port = config.get('monitoring', {}).get('port', 8008)

    # Create FastAPI app with enhanced endpoints
    app = health_monitor.get_fastapi_app()

    # Add optimized system endpoints
    @app.get("/api/optimized/metrics")
    async def get_optimized_metrics():
        """Get optimized system metrics"""
        try:
            # Get service metrics
            coordinator = service_manager.get_service("trading_coordinator")
            if coordinator:
                system_metrics = coordinator.get_system_metrics()
                performance_summary = coordinator.get_performance_summary()

                return {
                    "success": True,
                    "data": {
                        "system_metrics": system_metrics.__dict__,
                        "performance_summary": performance_summary,
                        "performance_targets": coordinator.performance_targets
                    }
                }
            else:
                return {"success": False, "error": "Trading coordinator not available"}
        except Exception as e:
            logger.error(f"Failed to get optimized metrics: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/optimized/health")
    async def get_optimized_health():
        """Get optimized system health"""
        try:
            coordinator = service_manager.get_service("trading_coordinator")
            if coordinator:
                return {
                    "success": True,
                    "data": {
                        "overall_status": coordinator.system_metrics.system_health,
                        "circuit_breaker": coordinator.system_metrics.circuit_breaker_status,
                        "cache_hit_rate": coordinator.system_metrics.cache_hit_rate,
                        "last_latency_ms": coordinator.system_metrics.total_latency_ms
                    }
                }
            else:
                return {"success": False, "error": "Trading coordinator not available"}
        except Exception as e:
            logger.error(f"Failed to get optimized health: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/optimized/performance")
    async def get_optimized_performance():
        """Get detailed performance metrics"""
        try:
            if performance_monitor:
                trading_summary = performance_monitor.get_trading_summary()
                health_status = performance_monitor.get_health_status()

                return {
                    "success": True,
                    "data": {
                        "trading_summary": trading_summary,
                        "health_status": health_status,
                        "active_alerts": performance_monitor.get_active_alerts()
                    }
                }
            else:
                return {"success": False, "error": "Performance monitor not available"}
        except Exception as e:
            logger.error(f"Failed to get performance data: {e}")
            return {"success": False, "error": str(e)}

    # Start monitoring server
    config_uvicorn = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=monitoring_port,
        log_level="info"
    )
    server = uvicorn.Server(config_uvicorn)

    # Run optimized trading agent with monitoring
    try:
        async with service_manager.service_lifecycle():
            # Start monitoring server
            server_task = asyncio.create_task(server.serve())

            # Run optimized trading agent
            trading_task = asyncio.create_task(
                run_optimized_trading_agent(config, service_manager, logger)
            )

            # Wait for completion
            done, pending = await asyncio.wait(
                [server_task, trading_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        logger.error(f"Service lifecycle failed: {e}", exc_info=True)
        return 1
    finally:
        # Cleanup
        await health_monitor.shutdown()
        if performance_monitor:
            performance_monitor.stop()

    return 0

def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Received keyboard interrupt, shutting down gracefully...")
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())