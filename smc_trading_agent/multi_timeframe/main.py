"""
Multi-Timeframe Confluence Analysis Main Module

Integration point for the complete multi-timeframe confluence analysis system.
Provides a unified interface for data management, confluence analysis,
signal generation, and caching.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import asdict

from .data_manager import MultiTimeframeDataManager, MarketDataUpdate
from .confluence_engine import ConfluenceAnalysisEngine, ConfluenceScore
from .signal_generator import MultiTimeframeSignalGenerator, TradingSignal
from .cache_manager import ConfluenceCacheManager

logger = logging.getLogger(__name__)

class MultiTimeframeConfluenceSystem:
    """
    Main integration system for multi-timeframe confluence analysis.

    Provides a unified interface for:
    - Real-time multi-timeframe data management
    - Confluence analysis across timeframes
    - Intelligent signal generation
    - High-performance caching
    - Risk-adjusted position sizing
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbols = config.get('symbols', ['BTCUSDT'])
        self.timeframes = config.get('timeframes', ['M5', 'M15', 'H1', 'H4', 'D1'])

        # Initialize components
        self.data_manager = MultiTimeframeDataManager(config.get('data_manager', {}))
        self.confluence_engine = ConfluenceAnalysisEngine(config.get('confluence_engine', {}))
        self.signal_generator = MultiTimeframeSignalGenerator(config.get('signal_generator', {}))
        self.cache_manager = ConfluenceCacheManager(config.get('cache_manager', {}))

        # System state
        self.running = False
        self.last_analysis_time: Dict[str, datetime] = {}
        self.analysis_interval_minutes = config.get('analysis_interval_minutes', 5)

        # Performance tracking
        self.metrics = {
            'total_analyses': 0,
            'total_signals': 0,
            'successful_signals': 0,
            'avg_analysis_time_ms': 0,
            'cache_hit_rate': 0.0
        }

        logger.info("Multi-timeframe confluence system initialized")

    async def initialize(self):
        """Initialize the multi-timeframe confluence system."""
        try:
            logger.info("Initializing multi-timeframe confluence system...")

            # Initialize all components
            await self.data_manager.initialize()
            await self.cache_manager.initialize()

            logger.info("Multi-timeframe confluence system initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing system: {e}")
            raise

    async def start(self):
        """Start the multi-timeframe confluence system."""
        try:
            logger.info("Starting multi-timeframe confluence system...")

            # Start background tasks
            asyncio.create_task(self._periodic_analysis())
            asyncio.create_task(self._performance_monitoring())

            self.running = True
            logger.info("Multi-timeframe confluence system started successfully")

        except Exception as e:
            logger.error(f"Error starting system: {e}")
            raise

    async def stop(self):
        """Stop the multi-timeframe confluence system."""
        try:
            logger.info("Stopping multi-timeframe confluence system...")

            self.running = False
            await self.cache_manager.shutdown()

            logger.info("Multi-timeframe confluence system stopped")

        except Exception as e:
            logger.error(f"Error stopping system: {e}")

    def add_market_data(self, symbol: str, price: float, volume: float,
                       timestamp: Optional[datetime] = None):
        """
        Add real-time market data to the system.

        Args:
            symbol: Trading symbol
            price: Current price
            volume: Trade volume
            timestamp: Optional timestamp
        """
        try:
            self.data_manager.add_market_data(symbol, price, volume, timestamp)
        except Exception as e:
            logger.error(f"Error adding market data: {e}")

    def analyze_symbol(self, symbol: str, force_analysis: bool = False) -> Dict[str, Any]:
        """
        Perform complete multi-timeframe analysis for a symbol.

        Args:
            symbol: Trading symbol
            force_analysis: Force analysis even if recently analyzed

        Returns:
            Complete analysis results including confluence and signals
        """
        try:
            start_time = datetime.utcnow()

            # Check if analysis is needed
            if not force_analysis and self._should_skip_analysis(symbol):
                return self._get_cached_analysis(symbol)

            logger.info(f"Starting multi-timeframe analysis for {symbol}")

            # Get data for all timeframes
            timeframe_data = self.data_manager.get_all_timeframes_data(symbol)

            if not any(df.empty for df in timeframe_data.values()):
                # Get current price from most recent data
                current_price = self._get_current_price(timeframe_data)

                # Check cache first
                cache_key = self._generate_cache_key(symbol, timeframe_data)
                cached_confluence = self.cache_manager.get_cached_confluence(
                    symbol, list(timeframe_data.keys()), cache_key
                )

                if cached_confluence:
                    confluence_scores = cached_confluence
                    logger.info(f"Using cached confluence analysis for {symbol}")
                else:
                    # Perform confluence analysis
                    confluence_scores = self.confluence_engine.analyze_multi_timeframe_confluence(
                        symbol, timeframe_data, current_price
                    )

                    # Cache the results
                    self.cache_manager.cache_confluence_result(
                        symbol, list(timeframe_data.keys()), confluence_scores
                    )

                # Generate signals
                market_data = {
                    'account_balance': 10000,  # Should be updated from actual
                    'volatility': self._calculate_volatility(timeframe_data),
                    'volume_ratio': self._calculate_volume_ratio(timeframe_data),
                    'spread': 0.001  # Should be updated from actual
                }

                signals = self.signal_generator.generate_signals(
                    symbol, confluence_scores, current_price, market_data
                )

                # Compile results
                analysis_results = {
                    'symbol': symbol,
                    'timestamp': datetime.utcnow(),
                    'current_price': current_price,
                    'timeframe_data_status': {
                        tf: len(df) if not df.empty else 0
                        for tf, df in timeframe_data.items()
                    },
                    'confluence_scores': [asdict(score) for score in confluence_scores],
                    'signals': [self._signal_to_dict(signal) for signal in signals],
                    'analysis_time_ms': (datetime.utcnow() - start_time).total_seconds() * 1000,
                    'data_quality': self._assess_data_quality(timeframe_data)
                }

                # Update metrics
                self._update_metrics(len(confluence_scores), len(signals),
                                   analysis_results['analysis_time_ms'])

                # Store analysis timestamp
                self.last_analysis_time[symbol] = datetime.utcnow()

                return analysis_results

            else:
                logger.warning(f"Insufficient data for {symbol} analysis")
                return {'error': 'Insufficient data', 'symbol': symbol}

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}

    def get_signal_for_symbol(self, symbol: str) -> Optional[TradingSignal]:
        """
        Get the best trading signal for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Best trading signal or None if no valid signals
        """
        try:
            # Perform analysis
            analysis = self.analyze_symbol(symbol)

            if 'error' in analysis:
                return None

            # Get signals from analysis
            signals_data = analysis.get('signals', [])
            if not signals_data:
                return None

            # Convert back to signal objects and find the best one
            signals = [self._dict_to_signal(signal_data) for signal_data in signals_data]
            valid_signals = [s for s in signals if s.confidence >= 0.7]

            if not valid_signals:
                return None

            # Return the signal with highest confidence
            best_signal = max(valid_signals, key=lambda s: s.confidence)
            return best_signal

        except Exception as e:
            logger.error(f"Error getting signal for {symbol}: {e}")
            return None

    def get_all_signals(self) -> Dict[str, Optional[TradingSignal]]:
        """Get best signals for all configured symbols."""
        signals = {}
        for symbol in self.symbols:
            signals[symbol] = self.get_signal_for_symbol(symbol)
        return signals

    def update_signal_performance(self, signal: TradingSignal, outcome: Dict[str, Any]):
        """Update performance tracking for a signal."""
        try:
            self.signal_generator.update_signal_performance(signal, outcome)
        except Exception as e:
            logger.error(f"Error updating signal performance: {e}")

    def _should_skip_analysis(self, symbol: str) -> bool:
        """Check if analysis should be skipped for this symbol."""
        last_analysis = self.last_analysis_time.get(symbol)
        if not last_analysis:
            return False

        time_since_analysis = (datetime.utcnow() - last_analysis).total_seconds()
        return time_since_analysis < (self.analysis_interval_minutes * 60)

    def _get_cached_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get cached analysis if available."""
        try:
            # Try to get cached confluence
            timeframe_data = self.data_manager.get_all_timeframes_data(symbol)
            cache_key = self._generate_cache_key(symbol, timeframe_data)

            cached_confluence = self.cache_manager.get_cached_confluence(
                symbol, list(timeframe_data.keys()), cache_key
            )

            if cached_confluence:
                current_price = self._get_current_price(timeframe_data)

                return {
                    'symbol': symbol,
                    'timestamp': datetime.utcnow(),
                    'current_price': current_price,
                    'confluence_scores': [asdict(score) for score in cached_confluence],
                    'signals': [],  # Don't generate signals from cache
                    'cached': True
                }

        except Exception as e:
            logger.error(f"Error getting cached analysis: {e}")

        return {'error': 'No cached data available', 'symbol': symbol}

    def _get_current_price(self, timeframe_data: Dict[str, pd.DataFrame]) -> float:
        """Get current price from the most recent data."""
        try:
            # Prefer M1 or M5 data for current price
            for tf in ['M5', 'M15', 'H1']:
                if tf in timeframe_data and not timeframe_data[tf].empty:
                    return float(timeframe_data[tf].iloc[-1]['close'])

            # Fallback to any available timeframe
            for df in timeframe_data.values():
                if not df.empty:
                    return float(df.iloc[-1]['close'])

            raise ValueError("No price data available")

        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return 0.0

    def _calculate_volatility(self, timeframe_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate overall volatility from timeframe data."""
        try:
            volatilities = []

            for df in timeframe_data.values():
                if len(df) >= 20:
                    returns = df['close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252)  # Annualized
                    volatilities.append(volatility)

            return np.mean(volatilities) if volatilities else 0.02

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.02

    def _calculate_volume_ratio(self, timeframe_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate volume ratio (current vs average)."""
        try:
            ratios = []

            for df in timeframe_data.values():
                if len(df) >= 20:
                    current_volume = df.iloc[-1]['volume']
                    avg_volume = df['volume'].tail(20).mean()
                    ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                    ratios.append(ratio)

            return np.mean(ratios) if ratios else 1.0

        except Exception as e:
            logger.error(f"Error calculating volume ratio: {e}")
            return 1.0

    def _generate_cache_key(self, symbol: str, timeframe_data: Dict[str, pd.DataFrame]) -> str:
        """Generate cache key based on data state."""
        try:
            # Create hash based on latest timestamps and data counts
            key_data = {
                'symbol': symbol,
                'timeframes': {
                    tf: {
                        'count': len(df) if not df.empty else 0,
                        'latest_timestamp': df.iloc[-1]['timestamp'].isoformat() if not df.empty else None
                    }
                    for tf, df in timeframe_data.items()
                }
            }

            import hashlib
            import json
            key_string = json.dumps(key_data, sort_keys=True)
            return hashlib.md5(key_string.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            return f"{symbol}_fallback"

    def _assess_data_quality(self, timeframe_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Assess quality of data across timeframes."""
        try:
            quality_scores = {}
            total_candles = 0
            complete_timeframes = 0

            for tf, df in timeframe_data.items():
                if df.empty:
                    quality_scores[tf] = 0.0
                    continue

                # Check data completeness
                expected_candles = self._get_expected_candles(tf)
                actual_candles = len(df)
                completeness = min(1.0, actual_candles / expected_candles)

                # Check data consistency
                has_nulls = df.isnull().any().any()
                consistency = 0.0 if has_nulls else 1.0

                # Overall quality score
                quality_score = (completeness * 0.7 + consistency * 0.3)
                quality_scores[tf] = quality_score

                total_candles += actual_candles
                if completeness > 0.8:
                    complete_timeframes += 1

            overall_quality = np.mean(list(quality_scores.values())) if quality_scores else 0.0

            return {
                'timeframe_scores': quality_scores,
                'overall_score': overall_quality,
                'total_candles': total_candles,
                'complete_timeframes': complete_timeframes,
                'total_timeframes': len(timeframe_data)
            }

        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return {'error': str(e), 'overall_score': 0.0}

    def _get_expected_candles(self, timeframe: str) -> int:
        """Get expected number of candles for a timeframe."""
        # Expected candles per day
        candles_per_day = {
            'M5': 24 * 12,      # 288
            'M15': 24 * 4,      # 96
            'H1': 24,           # 24
            'H4': 6,            # 6
            'D1': 1             # 1
        }
        return candles_per_day.get(timeframe, 24)

    def _signal_to_dict(self, signal: TradingSignal) -> Dict[str, Any]:
        """Convert signal to dictionary for serialization."""
        from dataclasses import asdict

        signal_dict = asdict(signal)
        signal_dict['signal_type'] = signal.signal_type.value
        signal_dict['strength'] = signal.strength.value
        signal_dict['timestamp'] = signal.timestamp.isoformat()
        if signal.expiry_time:
            signal_dict['expiry_time'] = signal.expiry_time.isoformat()

        return signal_dict

    def _dict_to_signal(self, signal_dict: Dict[str, Any]) -> TradingSignal:
        """Convert dictionary back to signal object."""
        from .signal_generator import SignalType, SignalStrength

        signal_dict['signal_type'] = SignalType(signal_dict['signal_type'])
        signal_dict['strength'] = SignalStrength(signal_dict['strength'])
        signal_dict['timestamp'] = datetime.fromisoformat(signal_dict['timestamp'])
        if signal_dict.get('expiry_time'):
            signal_dict['expiry_time'] = datetime.fromisoformat(signal_dict['expiry_time'])

        return TradingSignal(**signal_dict)

    def _update_metrics(self, confluence_count: int, signal_count: int, analysis_time_ms: float):
        """Update system performance metrics."""
        try:
            self.metrics['total_analyses'] += 1
            self.metrics['total_signals'] += signal_count
            if signal_count > 0:
                self.metrics['successful_signals'] += 1

            # Update average analysis time
            current_avg = self.metrics['avg_analysis_time_ms']
            total_analyses = self.metrics['total_analyses']
            self.metrics['avg_analysis_time_ms'] = (
                (current_avg * (total_analyses - 1) + analysis_time_ms) / total_analyses
            )

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def _periodic_analysis(self):
        """Background task for periodic analysis of all symbols."""
        while self.running:
            try:
                # Analyze all symbols
                for symbol in self.symbols:
                    try:
                        self.analyze_symbol(symbol)
                    except Exception as e:
                        logger.error(f"Error in periodic analysis for {symbol}: {e}")

                # Update cache hit rate
                cache_metrics = self.cache_manager.get_performance_metrics()
                self.metrics['cache_hit_rate'] = cache_metrics.get('hit_rate', 0.0)

                # Wait for next analysis cycle
                await asyncio.sleep(self.analysis_interval_minutes * 60)

            except Exception as e:
                logger.error(f"Error in periodic analysis: {e}")
                await asyncio.sleep(60)

    async def _performance_monitoring(self):
        """Background task for performance monitoring."""
        while self.running:
            try:
                # Log performance metrics every 5 minutes
                await asyncio.sleep(300)

                if self.running:
                    metrics = self.get_performance_metrics()
                    logger.info(f"Multi-TF System Metrics - "
                               f"Analyses: {metrics['total_analyses']}, "
                               f"Signals: {metrics['total_signals']}, "
                               f"Success Rate: {metrics['success_rate']:.1%}, "
                               f"Avg Time: {metrics['avg_analysis_time_ms']:.1f}ms, "
                               f"Cache Hit Rate: {metrics['cache_hit_rate']:.1%}")

            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(60)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system performance metrics."""
        try:
            # System metrics
            system_metrics = self.metrics.copy()
            total_signals = system_metrics['total_signals']
            system_metrics['success_rate'] = (
                system_metrics['successful_signals'] / max(1, total_signals)
            )

            # Data manager metrics
            data_metrics = self.data_manager.get_metrics()

            # Cache metrics
            cache_metrics = self.cache_manager.get_performance_metrics()

            # Signal generator metrics
            signal_metrics = self.signal_generator.get_signal_statistics()

            return {
                'system': system_metrics,
                'data_manager': data_metrics,
                'cache': cache_metrics,
                'signal_generator': signal_metrics,
                'last_update': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}

# Convenience function for creating system instance
def create_confluence_system(config: Dict[str, Any]) -> MultiTimeframeConfluenceSystem:
    """
    Create and configure a multi-timeframe confluence system.

    Args:
        config: Configuration dictionary

    Returns:
        Configured MultiTimeframeConfluenceSystem instance
    """
    return MultiTimeframeConfluenceSystem(config)