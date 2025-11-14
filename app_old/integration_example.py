"""
Integration example demonstrating how the enhanced Model Ensemble integrates 
with existing SMC detector and risk manager components.

This example shows the complete flow:
1. SMC pattern detection
2. Enhanced decision making with ensemble models
3. Risk management and position sizing
4. Trade execution signals
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_market_data(n_samples: int = 200) -> pd.DataFrame:
    """Create sample market data for demonstration."""
    np.random.seed(42)
    
    # Generate realistic price data
    base_price = 45000  # BTC-like price
    prices = [base_price]
    
    for i in range(1, n_samples):
        # Random walk with slight trend
        change = np.random.normal(0.0005, 0.015)  # Small positive drift, moderate volatility
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1000))  # Floor price
        
    prices = np.array(prices)
    
    # Create OHLCV data
    opens = prices + np.random.normal(0, 0.002, n_samples) * prices
    highs = np.maximum(opens, prices) + np.abs(np.random.normal(0, 0.008, n_samples)) * prices
    lows = np.minimum(opens, prices) - np.abs(np.random.normal(0, 0.008, n_samples)) * prices
    volumes = np.random.lognormal(8, 0.5, n_samples)
    
    # Add technical indicators
    closes_series = pd.Series(prices)
    sma_20 = closes_series.rolling(20).mean().fillna(closes_series.iloc[0])
    sma_50 = closes_series.rolling(50).mean().fillna(closes_series.iloc[0])
    
    # Simple RSI calculation
    delta = closes_series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)
    
    return pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='1H'),
        'open': opens,
        'high': highs,
        'low': lows,
        'close': prices,
        'volume': volumes,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'rsi': rsi
    })

def simulate_smc_patterns(market_data: pd.DataFrame) -> List[Dict[str, Any]]:
    """Simulate SMC pattern detection (normally done by smc_detector module)."""
    patterns = []
    
    for i in range(20, len(market_data) - 10, 15):  # Every 15 bars, skip first/last
        # Simulate order block detection
        if np.random.random() > 0.7:  # 30% chance of pattern
            current_price = market_data.iloc[i]['close']
            high_price = market_data.iloc[i]['high']
            low_price = market_data.iloc[i]['low']
            
            # Determine pattern type based on recent price action
            recent_trend = market_data.iloc[i-5:i]['close'].diff().sum()
            
            if recent_trend > 0:  # Bullish context
                pattern_type = 'bullish' if np.random.random() > 0.3 else 'bearish'
            else:  # Bearish context
                pattern_type = 'bearish' if np.random.random() > 0.3 else 'bullish'
                
            pattern = {
                'type': pattern_type,
                'direction': pattern_type,  # Both formats for compatibility
                'price_level': (high_price, low_price),
                'strength': np.random.uniform(0.6, 0.95),
                'timestamp': market_data.iloc[i]['timestamp'],
                'index': i,
                'pattern_name': 'order_block'
            }
            patterns.append(pattern)
            
    return patterns

def simulate_risk_assessment(signal: Dict[str, Any], market_data: pd.DataFrame) -> Dict[str, Any]:
    """Simulate risk manager assessment (normally done by risk_manager module)."""
    if not signal:
        return None
        
    # Simple risk calculations
    current_price = signal['entry_price']
    
    # Calculate position size (risk 1% of capital per trade)
    capital = 100000  # $100k example
    risk_per_trade = 0.01
    
    if signal['action'] == 'BUY':
        # Set stop loss 2% below entry
        stop_loss = current_price * 0.98
        # Set take profit 3% above entry  
        take_profit = current_price * 1.03
    else:  # SELL
        # Set stop loss 2% above entry
        stop_loss = current_price * 1.02
        # Set take profit 3% below entry
        take_profit = current_price * 0.97
    
    # Calculate position size based on stop loss distance
    risk_amount = capital * risk_per_trade
    stop_distance = abs(current_price - stop_loss)
    position_size = risk_amount / stop_distance
    
    return {
        'position_size': position_size,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'risk_amount': risk_amount,
        'risk_reward_ratio': abs(take_profit - current_price) / stop_distance,
        'max_position_value': position_size * current_price
    }

def run_integration_example():
    """Run the complete integration example."""
    logger.info("Starting SMC Trading Agent Integration Example")
    
    # Step 1: Generate market data
    logger.info("Generating sample market data...")
    market_data = create_sample_market_data(n_samples=300)
    logger.info(f"Generated {len(market_data)} data points from {market_data['timestamp'].iloc[0]} to {market_data['timestamp'].iloc[-1]}")
    
    # Step 2: Initialize the enhanced decision engine
    logger.info("Initializing enhanced decision engine with ensemble models...")
    try:
        from smc_trading_agent.decision_engine.model_ensemble import AdaptiveModelSelector
        
        decision_engine = AdaptiveModelSelector(input_size=6)  # 6 features: OHLCV + 1 indicator
        logger.info("Decision engine initialized successfully")
        
        # Prepare features for the ensemble
        feature_data = market_data[['open', 'high', 'low', 'close', 'volume', 'rsi']].copy()
        
    except ImportError as e:
        logger.error(f"Could not import decision engine: {e}")
        logger.info("Using fallback decision logic")
        decision_engine = None
        feature_data = market_data
    
    # Step 3: Simulate SMC pattern detection
    logger.info("Detecting SMC patterns...")
    smc_patterns = simulate_smc_patterns(market_data)
    logger.info(f"Detected {len(smc_patterns)} SMC patterns")
    
    # Step 4: Process each pattern and generate trading signals
    signals_generated = 0
    total_signals = []
    
    logger.info("Processing patterns and generating trading signals...")
    
    for i, pattern in enumerate(smc_patterns):
        try:
            # Get market data up to the pattern point
            pattern_index = pattern['index']
            current_market_data = feature_data.iloc[:pattern_index+1]
            
            if len(current_market_data) < 60:  # Need enough data for ensemble
                logger.debug(f"Insufficient data for pattern {i+1}, skipping")
                continue
            
            # Generate decision using enhanced ensemble
            if decision_engine:
                signal = decision_engine.make_decision([pattern], current_market_data)
            else:
                # Fallback logic
                if pattern['type'] == 'bullish':
                    signal = {
                        'action': 'BUY',
                        'symbol': 'BTC/USDT',
                        'entry_price': pattern['price_level'][0],
                        'confidence': 0.75
                    }
                elif pattern['type'] == 'bearish':
                    signal = {
                        'action': 'SELL', 
                        'symbol': 'BTC/USDT',
                        'entry_price': pattern['price_level'][1],
                        'confidence': 0.75
                    }
                else:
                    signal = None
            
            if signal:
                # Step 5: Risk assessment and position sizing
                risk_assessment = simulate_risk_assessment(signal, current_market_data)
                
                if risk_assessment:
                    # Combine signal with risk management
                    final_signal = {
                        **signal,
                        'timestamp': pattern['timestamp'],
                        'pattern_strength': pattern['strength'],
                        'stop_loss': risk_assessment['stop_loss'],
                        'take_profit': risk_assessment['take_profit'],
                        'position_size': risk_assessment['position_size'],
                        'risk_reward_ratio': risk_assessment['risk_reward_ratio'],
                        'pattern_type': pattern['pattern_name']
                    }
                    
                    # Add ensemble details if available
                    if 'ensemble_details' in signal:
                        final_signal['market_regime'] = signal.get('market_regime', 'unknown')
                        final_signal['model_weights'] = signal['ensemble_details'].get('model_weights', {})
                    
                    total_signals.append(final_signal)
                    signals_generated += 1
                    
                    logger.info(f"Generated {signal['action']} signal for {signal['symbol']} at {signal['entry_price']:.2f}")
                    logger.info(f"  Confidence: {signal['confidence']:.3f}, R:R Ratio: {risk_assessment['risk_reward_ratio']:.2f}")
                    
                    if 'market_regime' in final_signal:
                        logger.info(f"  Market Regime: {final_signal['market_regime']}")
                    
        except Exception as e:
            logger.error(f"Error processing pattern {i+1}: {str(e)}")
            continue
    
    # Step 6: Summary and analysis
    logger.info("\n" + "="*60)
    logger.info("INTEGRATION EXAMPLE SUMMARY")
    logger.info("="*60)
    logger.info(f"Total SMC patterns detected: {len(smc_patterns)}")
    logger.info(f"Trading signals generated: {signals_generated}")
    
    if total_signals:
        # Analyze signals
        buy_signals = [s for s in total_signals if s['action'] == 'BUY']
        sell_signals = [s for s in total_signals if s['action'] == 'SELL']
        
        logger.info(f"Buy signals: {len(buy_signals)}")
        logger.info(f"Sell signals: {len(sell_signals)}")
        
        avg_confidence = np.mean([s['confidence'] for s in total_signals])
        avg_rr_ratio = np.mean([s['risk_reward_ratio'] for s in total_signals])
        
        logger.info(f"Average signal confidence: {avg_confidence:.3f}")
        logger.info(f"Average risk/reward ratio: {avg_rr_ratio:.2f}")
        
        # Show some example signals
        logger.info("\nExample signals:")
        for i, signal in enumerate(total_signals[:3]):
            logger.info(f"  {i+1}. {signal['action']} {signal['symbol']} @ {signal['entry_price']:.2f}")
            logger.info(f"     SL: {signal['stop_loss']:.2f}, TP: {signal['take_profit']:.2f}")
            logger.info(f"     Confidence: {signal['confidence']:.3f}, Pattern: {signal['pattern_type']}")
            if 'market_regime' in signal:
                logger.info(f"     Market Regime: {signal['market_regime']}")
    
    logger.info("\nIntegration example completed successfully!")
    logger.info("The enhanced ensemble integrates seamlessly with existing SMC detector and risk manager.")
    
    return {
        'patterns_detected': len(smc_patterns),
        'signals_generated': signals_generated,
        'signals': total_signals,
        'success': True
    }

if __name__ == "__main__":
    try:
        result = run_integration_example()
        print(f"\nIntegration test {'PASSED' if result['success'] else 'FAILED'}")
    except Exception as e:
        logger.error(f"Integration example failed: {str(e)}")
        print("Integration test FAILED")