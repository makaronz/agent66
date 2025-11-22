"""
Multi-Timeframe Integration Module

Integrates the new multi-timeframe confluence analysis system with existing
SMC components including the data pipeline, decision engine, and risk manager.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

from .main import MultiTimeframeConfluenceSystem, create_confluence_system
from ..data_pipeline.ingestion import DataIngestion
from ..decision_engine.model_ensemble import ModelEnsemble
from ..risk_manager.smc_risk_manager import SMCRiskManager
from ..smc_detector.indicators import SMCIndicators
from .signal_generator import TradingSignal, SignalType

logger = logging.getLogger(__name__)

@dataclass
class IntegratedSignal:
    """Integrated signal combining multi-timeframe analysis with existing components."""
    symbol: str
    multi_tf_signal: TradingSignal
    ml_ensemble_signal: Dict[str, Any]
    smc_indicator_signal: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    final_decision: str
    combined_confidence: float
    recommended_action: str
    position_size_adjusted: float
    timestamp: datetime

class MultiTimeframeIntegration:
    """
    Integration layer for multi-timeframe confluence analysis.

    Bridges the new multi-timeframe system with existing SMC components to provide
    unified trading decisions with enhanced confidence and risk management.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbols = config.get('symbols', ['BTCUSDT'])

        # Initialize multi-timeframe system
        mt_config = config.get('multi_timeframe', {})
        self.mt_system = create_confluence_system(mt_config)

        # Initialize existing components (if available)
        self.data_ingestion = None
        self.model_ensemble = None
        self.risk_manager = None
        self.smc_indicators = None

        # Integration weights
        self.weights = config.get('integration_weights', {
            'multi_timeframe': 0.4,
            'ml_ensemble': 0.3,
            'smc_indicators': 0.2,
            'risk_management': 0.1
        })

        # Signal history for performance tracking
        self.signal_history = []
        self.performance_metrics = {}

        logger.info("Multi-timeframe integration initialized")

    async def initialize(self):
        """Initialize all components and establish connections."""
        try:
            logger.info("Initializing multi-timeframe integration...")

            # Start multi-timeframe system
            await self.mt_system.start()

            # Initialize existing components based on configuration
            await self._initialize_existing_components()

            # Set up data flow integration
            await self._setup_data_flow()

            logger.info("Multi-timeframe integration initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing integration: {e}")
            raise

    async def _initialize_existing_components(self):
        """Initialize existing SMC components based on configuration."""
        try:
            # Initialize data ingestion if enabled
            if self.config.get('data_ingestion_enabled', True):
                self.data_ingestion = DataIngestion(self.config.get('exchanges', {}))
                await self.data_ingestion.start()

            # Initialize ML ensemble if enabled
            if self.config.get('ml_ensemble_enabled', True):
                self.model_ensemble = ModelEnsemble(self.config.get('ml_models', {}))

            # Initialize risk manager if enabled
            if self.config.get('risk_manager_enabled', True):
                self.risk_manager = SMCRiskManager(self.config.get('risk_management', {}))

            # Initialize SMC indicators if enabled
            if self.config.get('smc_indicators_enabled', True):
                self.smc_indicators = SMCIndicators()

        except Exception as e:
            logger.error(f"Error initializing existing components: {e}")
            # Continue without failed components

    async def _setup_data_flow(self):
        """Set up data flow between components."""
        try:
            if self.data_ingestion:
                # Set up callback for processing market data
                async def market_data_callback(data: Dict[str, Any]):
                    await self._process_market_data(data)

                # This would require modifying the data ingestion to support callbacks
                # For now, we'll simulate data flow
                pass

        except Exception as e:
            logger.error(f"Error setting up data flow: {e}")

    async def process_market_data(self, symbol: str, price: float, volume: float,
                                timestamp: Optional[datetime] = None):
        """
        Process market data through all components.

        Args:
            symbol: Trading symbol
            price: Current price
            volume: Trade volume
            timestamp: Optional timestamp
        """
        try:
            # Add to multi-timeframe system
            self.mt_system.add_market_data(symbol, price, volume, timestamp)

            # Process through other components if available
            if self.data_ingestion:
                # Data would flow through the existing pipeline
                pass

        except Exception as e:
            logger.error(f"Error processing market data: {e}")

    async def generate_integrated_signal(self, symbol: str) -> Optional[IntegratedSignal]:
        """
        Generate integrated trading signal using all available components.

        Args:
            symbol: Trading symbol

        Returns:
            Integrated signal with comprehensive analysis
        """
        try:
            logger.info(f"Generating integrated signal for {symbol}")

            # Get multi-timeframe signal
            mt_signal = self.mt_system.get_signal_for_symbol(symbol)

            # Get ML ensemble signal
            ml_signal = await self._get_ml_ensemble_signal(symbol) if self.model_ensemble else None

            # Get SMC indicators signal
            smc_signal = await self._get_smc_indicator_signal(symbol) if self.smc_indicators else None

            # Get risk assessment
            risk_assessment = await self._get_risk_assessment(symbol) if self.risk_manager else None

            # Combine signals
            integrated_signal = self._combine_signals(
                symbol, mt_signal, ml_signal, smc_signal, risk_assessment
            )

            # Store signal history
            self.signal_history.append(integrated_signal)

            # Keep history manageable
            if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-1000:]

            return integrated_signal

        except Exception as e:
            logger.error(f"Error generating integrated signal for {symbol}: {e}")
            return None

    async def _get_ml_ensemble_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get signal from ML ensemble component."""
        try:
            if not self.model_ensemble:
                return None

            # This would integrate with the existing ML ensemble
            # For now, return a placeholder
            return {
                'signal': 'hold',
                'confidence': 0.5,
                'prediction': 0.0,
                'volatility_adjusted': True,
                'model_weights': {
                    'lstm': 0.4,
                    'transformer': 0.4,
                    'ppo': 0.2
                }
            }

        except Exception as e:
            logger.error(f"Error getting ML ensemble signal: {e}")
            return None

    async def _get_smc_indicator_signal(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get signal from SMC indicators component."""
        try:
            if not self.smc_indicators:
                return None

            # Get data for analysis
            timeframe_data = self.mt_system.data_manager.get_timeframe_data(symbol, 'H1', limit=100)
            if timeframe_data.empty:
                return None

            # Use existing SMC indicators
            order_blocks = self.smc_indicators.detect_order_blocks(timeframe_data)
            coch_bos = self.smc_indicators.identify_choch_bos(timeframe_data)

            # Generate signal from SMC indicators
            signal = 'hold'
            confidence = 0.5

            # Simple logic based on detected patterns
            if order_blocks:
                bullish_ob = [ob for ob in order_blocks if ob['type'] == 'bullish']
                bearish_ob = [ob for ob in order_blocks if ob['type'] == 'bearish']

                if len(bullish_ob) > len(bearish_ob):
                    signal = 'buy'
                    confidence = min(0.8, 0.5 + len(bullish_ob) * 0.1)
                elif len(bearish_ob) > len(bullish_ob):
                    signal = 'sell'
                    confidence = min(0.8, 0.5 + len(bearish_ob) * 0.1)

            return {
                'signal': signal,
                'confidence': confidence,
                'order_blocks': order_blocks,
                'coch_bos': coch_bos,
                'pattern_count': len(order_blocks) + len(coch_bos.get('total_patterns', 0))
            }

        except Exception as e:
            logger.error(f"Error getting SMC indicator signal: {e}")
            return None

    async def _get_risk_assessment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get risk assessment from risk manager."""
        try:
            if not self.risk_manager:
                return None

            # This would integrate with the existing risk manager
            # For now, return a placeholder
            return {
                'risk_level': 'medium',
                'max_position_size': 0.05,
                'recommended_stop_loss': 0.02,
                'portfolio_risk': 0.15,
                'correlation_risk': 0.3,
                'market_regime': 'normal'
            }

        except Exception as e:
            logger.error(f"Error getting risk assessment: {e}")
            return None

    def _combine_signals(self, symbol: str, mt_signal: Optional[TradingSignal],
                        ml_signal: Optional[Dict[str, Any]],
                        smc_signal: Optional[Dict[str, Any]],
                        risk_assessment: Optional[Dict[str, Any]]) -> IntegratedSignal:
        """
        Combine signals from all components into integrated decision.

        Args:
            symbol: Trading symbol
            mt_signal: Multi-timeframe signal
            ml_signal: ML ensemble signal
            smc_signal: SMC indicator signal
            risk_assessment: Risk assessment

        Returns:
            Integrated signal with combined analysis
        """
        try:
            # Initialize signal scores
            buy_score = 0.0
            sell_score = 0.0
            hold_score = 0.0

            # Process multi-timeframe signal
            if mt_signal:
                weight = self.weights.get('multi_timeframe', 0.4)
                confidence = mt_signal.confidence

                if mt_signal.signal_type == SignalType.BUY:
                    buy_score += confidence * weight
                elif mt_signal.signal_type == SignalType.SELL:
                    sell_score += confidence * weight
                else:
                    hold_score += confidence * weight

            # Process ML ensemble signal
            if ml_signal:
                weight = self.weights.get('ml_ensemble', 0.3)
                confidence = ml_signal.get('confidence', 0.5)
                signal = ml_signal.get('signal', 'hold')

                if signal == 'buy':
                    buy_score += confidence * weight
                elif signal == 'sell':
                    sell_score += confidence * weight
                else:
                    hold_score += confidence * weight

            # Process SMC indicators signal
            if smc_signal:
                weight = self.weights.get('smc_indicators', 0.2)
                confidence = smc_signal.get('confidence', 0.5)
                signal = smc_signal.get('signal', 'hold')

                if signal == 'buy':
                    buy_score += confidence * weight
                elif signal == 'sell':
                    sell_score += confidence * weight
                else:
                    hold_score += confidence * weight

            # Process risk assessment
            if risk_assessment:
                risk_weight = self.weights.get('risk_management', 0.1)
                risk_level = risk_assessment.get('risk_level', 'medium')

                # Adjust based on risk level
                if risk_level == 'high':
                    # Reduce confidence in extreme positions
                    buy_score *= 0.8
                    sell_score *= 0.8
                    hold_score += 0.2 * risk_weight

            # Determine final decision
            max_score = max(buy_score, sell_score, hold_score)
            combined_confidence = max_score

            if buy_score == max_score and buy_score > 0.6:
                final_decision = 'buy'
                recommended_action = 'BUY'
            elif sell_score == max_score and sell_score > 0.6:
                final_decision = 'sell'
                recommended_action = 'SELL'
            else:
                final_decision = 'hold'
                recommended_action = 'HOLD'

            # Adjust position size based on risk assessment and confidence
            base_position = 0.02  # 2% base position
            adjusted_position = base_position * combined_confidence

            if risk_assessment:
                max_position = risk_assessment.get('max_position_size', 0.05)
                adjusted_position = min(adjusted_position, max_position)

            return IntegratedSignal(
                symbol=symbol,
                multi_tf_signal=mt_signal,
                ml_ensemble_signal=ml_signal or {},
                smc_indicator_signal=smc_signal or {},
                risk_assessment=risk_assessment or {},
                final_decision=final_decision,
                combined_confidence=combined_confidence,
                recommended_action=recommended_action,
                position_size_adjusted=adjusted_position,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error combining signals: {e}")

            # Return safe default signal
            return IntegratedSignal(
                symbol=symbol,
                multi_tf_signal=None,
                ml_ensemble_signal={},
                smc_indicator_signal={},
                risk_assessment={},
                final_decision='hold',
                combined_confidence=0.0,
                recommended_action='HOLD',
                position_size_adjusted=0.0,
                timestamp=datetime.utcnow()
            )

    def get_signals_for_all_symbols(self) -> List[IntegratedSignal]:
        """Get integrated signals for all configured symbols."""
        signals = []
        for symbol in self.symbols:
            try:
                # Use synchronous version for simplicity
                signal = asyncio.run(self.generate_integrated_signal(symbol))
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error getting signal for {symbol}: {e}")

        return signals

    def update_signal_outcome(self, signal: IntegratedSignal, outcome: Dict[str, Any]):
        """Update signal performance tracking."""
        try:
            # Update multi-timeframe signal performance
            if signal.multi_tf_signal:
                self.mt_system.update_signal_performance(signal.multi_tf_signal, outcome)

            # Store outcome in signal history
            signal_entry = {
                'signal': signal,
                'outcome': outcome,
                'timestamp': datetime.utcnow()
            }

            # This would be used for performance analysis and model improvement

        except Exception as e:
            logger.error(f"Error updating signal outcome: {e}")

    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get comprehensive integration performance metrics."""
        try:
            # Multi-timeframe system metrics
            mt_metrics = self.mt_system.get_performance_metrics()

            # Signal history analysis
            total_signals = len(self.signal_history)
            if total_signals > 0:
                buy_signals = len([s for s in self.signal_history if s.final_decision == 'buy'])
                sell_signals = len([s for s in self.signal_history if s.final_decision == 'sell'])
                hold_signals = total_signals - buy_signals - sell_signals

                avg_confidence = np.mean([s.combined_confidence for s in self.signal_history])
            else:
                buy_signals = sell_signals = hold_signals = 0
                avg_confidence = 0.0

            return {
                'integration': {
                    'total_signals': total_signals,
                    'buy_signals': buy_signals,
                    'sell_signals': sell_signals,
                    'hold_signals': hold_signals,
                    'average_confidence': avg_confidence,
                    'integration_weights': self.weights
                },
                'multi_timeframe_system': mt_metrics,
                'component_status': {
                    'data_ingestion': self.data_ingestion is not None,
                    'ml_ensemble': self.model_ensemble is not None,
                    'risk_manager': self.risk_manager is not None,
                    'smc_indicators': self.smc_indicators is not None
                }
            }

        except Exception as e:
            logger.error(f"Error getting integration metrics: {e}")
            return {'error': str(e)}

    def configure_integration_weights(self, weights: Dict[str, float]):
        """Update integration weights for signal combination."""
        try:
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"Weights sum to {total_weight}, normalizing...")
                weights = {k: v / total_weight for k, v in weights.items()}

            self.weights.update(weights)
            logger.info(f"Updated integration weights: {self.weights}")

        except Exception as e:
            logger.error(f"Error configuring integration weights: {e}")

    async def shutdown(self):
        """Shutdown the integration system."""
        try:
            logger.info("Shutting down multi-timeframe integration...")

            # Stop multi-timeframe system
            await self.mt_system.stop()

            # Stop other components
            if self.data_ingestion:
                await self.data_ingestion.stop()

            logger.info("Multi-timeframe integration shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Factory function for creating integration system
def create_integration_system(config: Dict[str, Any]) -> MultiTimeframeIntegration:
    """
    Create and configure a multi-timeframe integration system.

    Args:
        config: Configuration dictionary

    Returns:
        Configured MultiTimeframeIntegration instance
    """
    return MultiTimeframeIntegration(config)