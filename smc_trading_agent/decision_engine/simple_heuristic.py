"""
Simple SMC Heuristic Decision Engine

Lightweight decision maker based on Smart Money Concepts patterns.
No ML models required - fast startup, no training needed.
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd


logger = logging.getLogger(__name__)


class SimpleSMCHeuristic:
    """
    Simple heuristic decision engine based on SMC patterns.
    
    Decision Logic:
    - Bullish order block → BUY signal
    - Bearish order block → SELL signal
    - Confidence based on pattern strength
    """
    
    def __init__(self, min_confidence: float = 0.70):
        """
        Initialize simple heuristic engine.
        
        Args:
            min_confidence: Minimum confidence to generate signal
        """
        self.min_confidence = min_confidence
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Simple SMC Heuristic initialized (min confidence: {min_confidence:.1%})")
    
    def make_decision(
        self,
        order_blocks: List[Dict[str, Any]],
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make trading decision based on detected SMC patterns.
        
        Args:
            order_blocks: List of detected order blocks
            market_data: Optional market data (not used in simple heuristic)
        
        Returns:
            Trading signal dict or None
        """
        if not order_blocks:
            self.logger.debug("No order blocks provided")
            return None
        
        try:
            # Use the most recent (first) order block
            latest_ob = order_blocks[0]
            
            # Extract pattern information
            ob_direction = latest_ob.get('direction') or latest_ob.get('type')
            ob_strength = latest_ob.get('strength', 0.75)
            price_level = latest_ob.get('price_level')
            
            if not ob_direction or not price_level:
                self.logger.warning("Order block missing required fields")
                return None
            
            # Calculate confidence
            # Base confidence 0.75, adjusted by strength
            confidence = min(0.75 + (ob_strength * 0.2), 0.95)
            
            # Generate signal based on direction
            if ob_direction.lower() in ['bullish', 'bull', 'buy']:
                # Extract entry price
                if isinstance(price_level, tuple) or isinstance(price_level, list):
                    entry_price = price_level[0]  # Low of bullish OB
                else:
                    entry_price = price_level
                
                signal = {
                    "action": "BUY",
                    "symbol": "BTC/USDT",
                    "entry_price": entry_price,
                    "confidence": confidence,
                    "pattern_type": "bullish_order_block",
                    "pattern_strength": ob_strength
                }
                
                self.logger.info(
                    f"🎯 BUY signal generated (confidence: {confidence:.1%}, "
                    f"entry: ${entry_price:.2f}, strength: {ob_strength:.2f})"
                )
                
                return signal
                
            elif ob_direction.lower() in ['bearish', 'bear', 'sell']:
                # Extract entry price
                if isinstance(price_level, tuple) or isinstance(price_level, list):
                    entry_price = price_level[1]  # High of bearish OB
                else:
                    entry_price = price_level
                
                signal = {
                    "action": "SELL",
                    "symbol": "BTC/USDT",
                    "entry_price": entry_price,
                    "confidence": confidence,
                    "pattern_type": "bearish_order_block",
                    "pattern_strength": ob_strength
                }
                
                self.logger.info(
                    f"🎯 SELL signal generated (confidence: {confidence:.1%}, "
                    f"entry: ${entry_price:.2f}, strength: {ob_strength:.2f})"
                )
                
                return signal
            
            else:
                self.logger.warning(f"Unknown order block direction: {ob_direction}")
                return None
        
        except Exception as e:
            self.logger.error(f"Decision making failed: {str(e)}", exc_info=True)
            return None
    
    def get_market_regime(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Simple market regime analysis (optional, for logging).
        
        Args:
            market_data: DataFrame with OHLCV data
        
        Returns:
            Dictionary with regime information
        """
        if market_data is None or market_data.empty or 'close' not in market_data.columns:
            return {"regime": "unknown", "volatility": 0.0}
        
        try:
            # Calculate simple volatility
            prices = market_data['close']
            returns = prices.pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5) if len(returns) > 1 else 0.0
            
            # Simple trend detection
            sma_short = prices.tail(10).mean()
            sma_long = prices.tail(30).mean()
            
            if sma_short > sma_long * 1.02:
                trend = "uptrend"
            elif sma_short < sma_long * 0.98:
                trend = "downtrend"
            else:
                trend = "sideways"
            
            regime = f"{trend}_{('high_vol' if volatility > 0.25 else 'low_vol')}"
            
            return {
                "regime": regime,
                "volatility": volatility,
                "trend": trend
            }
            
        except Exception as e:
            self.logger.warning(f"Market regime analysis failed: {str(e)}")
            return {"regime": "unknown", "volatility": 0.0}


# Alias for backward compatibility
AdaptiveModelSelector = SimpleSMCHeuristic

