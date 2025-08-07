#!/usr/bin/env python3
"""
Simple validation script for SMC Indicators implementation.
This script tests the functionality without pytest dependencies.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from smc_detector.indicators import SMCIndicators


def create_test_data():
    """Create test data with known patterns."""
    dates = pd.date_range(start='2023-10-01', periods=50, freq='1H')
    
    # Create data with some volatility
    np.random.seed(42)
    base_price = 50000
    returns = np.random.normal(0, 0.02, 50)
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        volatility = price * 0.01
        open_price = price
        high_price = price + np.random.uniform(0, volatility)
        low_price = price - np.random.uniform(0, volatility)
        close_price = price + np.random.uniform(-volatility/2, volatility/2)
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data)


def test_smc_indicators():
    """Test SMC indicators functionality."""
    print("🧪 Testing SMC Indicators Implementation...")
    
    # Create indicators instance
    indicators = SMCIndicators()
    print("✅ SMCIndicators instantiated successfully")
    
    # Create test data
    test_data = create_test_data()
    print(f"✅ Test data created: {len(test_data)} candles")
    
    # Test 1: Order Blocks Detection
    print("\n📊 Testing Order Blocks Detection...")
    try:
        order_blocks = indicators.detect_order_blocks(test_data)
        print(f"✅ Order blocks detection: {len(order_blocks)} blocks found")
        if order_blocks:
            print(f"   Sample block: {order_blocks[0]}")
    except Exception as e:
        print(f"❌ Order blocks detection failed: {e}")
    
    # Test 2: COCH/BOS Detection
    print("\n📈 Testing COCH/BOS Detection...")
    try:
        coch_bos = indicators.identify_choch_bos(test_data)
        print(f"✅ COCH/BOS detection: {coch_bos['total_patterns']} patterns found")
        print(f"   COCH patterns: {len(coch_bos['coch_patterns'])}")
        print(f"   BOS patterns: {len(coch_bos['bos_patterns'])}")
        if coch_bos['coch_patterns']:
            print(f"   Sample COCH: {coch_bos['coch_patterns'][0]}")
        if coch_bos['bos_patterns']:
            print(f"   Sample BOS: {coch_bos['bos_patterns'][0]}")
    except Exception as e:
        print(f"❌ COCH/BOS detection failed: {e}")
    
    # Test 3: Liquidity Sweep Detection
    print("\n💧 Testing Liquidity Sweep Detection...")
    try:
        liquidity_sweeps = indicators.liquidity_sweep_detection(test_data)
        print(f"✅ Liquidity sweep detection: {liquidity_sweeps['total_sweeps']} sweeps found")
        print(f"   Bullish sweeps: {liquidity_sweeps['bullish_sweeps']}")
        print(f"   Bearish sweeps: {liquidity_sweeps['bearish_sweeps']}")
        if liquidity_sweeps['liquidity_sweeps']:
            print(f"   Sample sweep: {liquidity_sweeps['liquidity_sweeps'][0]}")
    except Exception as e:
        print(f"❌ Liquidity sweep detection failed: {e}")
    
    # Test 4: Performance Test
    print("\n⚡ Testing Performance...")
    import time
    
    start_time = time.time()
    indicators.identify_choch_bos(test_data)
    coch_time = time.time() - start_time
    
    start_time = time.time()
    indicators.liquidity_sweep_detection(test_data)
    sweep_time = time.time() - start_time
    
    print(f"✅ COCH/BOS processing time: {coch_time:.3f}s")
    print(f"✅ Liquidity sweep processing time: {sweep_time:.3f}s")
    
    # Test 5: Integration Test
    print("\n🔗 Testing Integration...")
    try:
        # Test all methods together
        order_blocks = indicators.detect_order_blocks(test_data)
        coch_bos = indicators.identify_choch_bos(test_data)
        liquidity_sweeps = indicators.liquidity_sweep_detection(test_data)
        
        print("✅ All methods work together successfully")
        print(f"   Total patterns detected: {len(order_blocks) + coch_bos['total_patterns'] + liquidity_sweeps['total_sweeps']}")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
    
    print("\n🎉 SMC Indicators Validation Complete!")
    return True


if __name__ == "__main__":
    test_smc_indicators()
