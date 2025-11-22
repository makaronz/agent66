"""
Multi-Timeframe Confluence Analysis System - Example Usage

This example demonstrates how to use the multi-timeframe confluence analysis system
for real-world trading scenarios.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml

# Import the multi-timeframe system
from multi_timeframe.main import create_confluence_system
from multi_timeframe.integration import create_integration_system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def basic_multi_timeframe_example():
    """Basic example of multi-timeframe confluence analysis."""
    print("\n=== Basic Multi-Timeframe Example ===")

    # Load configuration
    config = {
        'symbols': ['BTCUSDT'],
        'timeframes': ['M5', 'M15', 'H1', 'H4'],
        'analysis_interval_minutes': 2,
        'data_manager': {
            'symbols': ['BTCUSDT']
        },
        'confluence_engine': {
            'min_confluence_score': 0.6
        },
        'signal_generator': {
            'validation': {
                'min_confidence': 0.7,
                'min_risk_reward': 1.5
            }
        },
        'cache_manager': {
            'cache': {
                'max_memory_mb': 256
            }
        }
    }

    # Create and initialize the system
    system = create_confluence_system(config)
    await system.initialize()

    try:
        # Simulate real-time market data
        print("Simulating market data...")
        base_price = 50000

        for i in range(50):  # Add 50 data points
            # Create realistic price movement
            trend = i * 2  # Upward trend
            volatility = np.random.normal(0, 50)  # Random volatility
            price = base_price + trend + volatility
            volume = 100 + np.random.randint(-20, 50)

            timestamp = datetime.utcnow() + timedelta(minutes=i)
            system.add_market_data('BTCUSDT', price, volume, timestamp)

            if i % 10 == 0:
                print(f"Added data point {i+1}: Price=${price:.2f}, Volume={volume}")

        print("\nAnalyzing symbol...")

        # Perform analysis
        analysis = system.analyze_symbol('BTCUSDT', force_analysis=True)

        if 'error' in analysis:
            print(f"Analysis error: {analysis['error']}")
            return

        # Display analysis results
        print(f"\nAnalysis Results for {analysis['symbol']}:")
        print(f"Current Price: ${analysis['current_price']:.2f}")
        print(f"Analysis Time: {analysis['analysis_time_ms']:.1f}ms")
        print(f"Data Quality Score: {analysis['data_quality']['overall_score']:.2f}")

        # Display confluence scores
        confluence_scores = analysis['confluence_scores']
        print(f"\nFound {len(confluence_scores)} confluence zones:")

        for i, score in enumerate(confluence_scores[:5]):  # Top 5 zones
            print(f"  Zone {i+1}:")
            print(f"    Price Level: ${score['price_level']:.2f}")
            print(f"    Overall Score: {score['overall_score']:.3f}")
            print(f"    Trend Alignment: {score['trend_alignment']:.3f}")
            print(f"    Timeframe Agreement: {score['timeframe_agreement']:.3f}")
            print(f"    Risk/Reward Ratio: {score['risk_reward_ratio']:.2f}")

        # Display trading signals
        signals = analysis['signals']
        print(f"\nGenerated {len(signals)} trading signals:")

        for i, signal in enumerate(signals):
            print(f"  Signal {i+1}:")
            print(f"    Action: {signal['signal_type']}")
            print(f"    Entry: ${signal['entry_price']:.2f}")
            print(f"    Stop Loss: ${signal['stop_loss']:.2f}")
            print(f"    Take Profit: ${signal['take_profit']:.2f}")
            print(f"    Confidence: {signal['confidence']:.2f}")
            print(f"    Position Size: {signal['position_size']:.1%}")
            print(f"    R/R Ratio: {signal['risk_reward_ratio']:.2f}")

        # Get best signal
        best_signal = system.get_signal_for_symbol('BTCUSDT')
        if best_signal:
            print(f"\nBest Signal: {best_signal.signal_type.value}")
            print(f"Confidence: {best_signal.confidence:.2f}")
            print(f"Entry: ${best_signal.entry_price:.2f}")
            print(f"Position Size: {best_signal.position_size:.1%}")

        # Display performance metrics
        metrics = system.get_performance_metrics()
        print(f"\nSystem Performance:")
        print(f"Total Analyses: {metrics['system']['total_analyses']}")
        print(f"Total Signals: {metrics['system']['total_signals']}")
        print(f"Cache Hit Rate: {metrics['cache']['hit_rate']:.1%}")
        print(f"Average Analysis Time: {metrics['system']['avg_analysis_time_ms']:.1f}ms")

    finally:
        await system.stop()

async def integration_example():
    """Example using the integration system with existing SMC components."""
    print("\n=== Integration Example ===")

    # Configuration for integration
    config = {
        'symbols': ['BTCUSDT', 'ETHUSDT'],
        'multi_timeframe': {
            'symbols': ['BTCUSDT', 'ETHUSDT'],
            'timeframes': ['M5', 'M15', 'H1']
        },
        'integration_weights': {
            'multi_timeframe': 0.4,
            'ml_ensemble': 0.3,
            'smc_indicators': 0.2,
            'risk_management': 0.1
        },
        # Enable existing components
        'data_ingestion_enabled': False,  # Disabled for example
        'ml_ensemble_enabled': False,     # Disabled for example
        'risk_manager_enabled': True,
        'smc_indicators_enabled': True
    }

    # Create integration system
    integration = create_integration_system(config)
    await integration.initialize()

    try:
        # Add market data for multiple symbols
        symbols = config['symbols']
        prices = {'BTCUSDT': 50000, 'ETHUSDT': 3000}

        for i in range(30):
            for symbol in symbols:
                base_price = prices[symbol]
                price = base_price + np.random.normal(0, base_price * 0.001)
                volume = 100 + np.random.randint(-50, 50)

                integration.process_market_data(symbol, price, volume)

        # Generate integrated signals
        print("Generating integrated signals...")

        for symbol in symbols:
            integrated_signal = await integration.generate_integrated_signal(symbol)

            if integrated_signal:
                print(f"\nIntegrated Signal for {symbol}:")
                print(f"Final Decision: {integrated_signal.final_decision}")
                print(f"Recommended Action: {integrated_signal.recommended_action}")
                print(f"Combined Confidence: {integrated_signal.combined_confidence:.2f}")
                print(f"Adjusted Position Size: {integrated_signal.position_size_adjusted:.1%}")

                # Component contributions
                if integrated_signal.multi_tf_signal:
                    print(f"Multi-TF Signal: {integrated_signal.multi_tf_signal.signal_type.value}")
                    print(f"  Confidence: {integrated_signal.multi_tf_signal.confidence:.2f}")

                if integrated_signal.smc_indicator_signal:
                    print(f"SMC Indicators: {integrated_signal.smc_indicator_signal['signal']}")
                    print(f"  Confidence: {integrated_signal.smc_indicator_signal['confidence']:.2f}")

                if integrated_signal.risk_assessment:
                    print(f"Risk Level: {integrated_signal.risk_assessment['risk_level']}")
                    print(f"  Max Position: {integrated_signal.risk_assessment['max_position_size']:.1%}")

        # Get integration metrics
        metrics = integration.get_integration_metrics()
        print(f"\nIntegration Metrics:")
        print(f"Total Signals: {metrics['integration']['total_signals']}")
        print(f"Average Confidence: {metrics['integration']['average_confidence']:.2f}")
        print(f"Component Status: {metrics['component_status']}")

    finally:
        await integration.shutdown()

async def real_time_simulation():
    """Simulate real-time trading scenario."""
    print("\n=== Real-Time Simulation ===")

    config = {
        'symbols': ['BTCUSDT'],
        'timeframes': ['M5', 'M15', 'H1'],
        'analysis_interval_minutes': 1,
        'data_manager': {'symbols': ['BTCUSDT']},
        'signal_generator': {
            'validation': {'min_confidence': 0.6}
        }
    }

    system = create_confluence_system(config)
    await system.initialize()

    try:
        print("Starting real-time simulation...")
        print("Press Ctrl+C to stop")

        # Simulate real-time data stream
        base_price = 50000
        trend_direction = 1  # 1 for up, -1 for down
        trend_strength = 2

        signal_count = 0

        for i in range(100):  # Simulate 100 time periods
            # Create price movement with trend
            if i % 20 == 0:  # Change trend every 20 periods
                trend_direction *= -1
                trend_strength = np.random.uniform(1, 3)

            trend = i * trend_direction * trend_strength
            volatility = np.random.normal(0, 100)
            price = base_price + trend + volatility
            volume = 100 + np.random.randint(-30, 70)

            timestamp = datetime.utcnow() + timedelta(minutes=i)
            system.add_market_data('BTCUSDT', price, volume, timestamp)

            # Perform analysis every 5 periods
            if i % 5 == 0:
                analysis = system.analyze_symbol('BTCUSDT', force_analysis=True)

                if 'error' not in analysis:
                    current_price = analysis['current_price']
                    signals = analysis['signals']

                    print(f"\nTime {i}: Price=${current_price:.2f}")

                    if signals:
                        signal_count += len(signals)
                        best_signal = max(signals, key=lambda s: s['confidence'])
                        print(f"  Signal: {best_signal['signal_type']}")
                        print(f"  Confidence: {best_signal['confidence']:.2f}")
                        print(f"  Entry: ${best_signal['entry_price']:.2f}")
                        print(f"  R/R: {best_signal['risk_reward_ratio']:.2f}")
                    else:
                        print("  No trading signals generated")

            # Small delay to simulate real-time
            await asyncio.sleep(0.1)

        print(f"\nSimulation completed. Generated {signal_count} signals.")

        # Final performance metrics
        metrics = system.get_performance_metrics()
        print(f"\nFinal Performance:")
        print(f"Total Analyses: {metrics['system']['total_analyses']}")
        print(f"Success Rate: {metrics['system']['success_rate']:.1%}")
        print(f"Cache Hit Rate: {metrics['cache']['hit_rate']:.1%}")

    finally:
        await system.stop()

async def performance_benchmark():
    """Benchmark system performance."""
    print("\n=== Performance Benchmark ===")

    config = {
        'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'],
        'timeframes': ['M5', 'M15', 'H1'],
        'data_manager': {'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']},
        'cache_manager': {
            'cache': {'max_memory_mb': 512}
        }
    }

    system = create_confluence_system(config)
    await system.initialize()

    try:
        print("Running performance benchmark...")

        # Generate test data for all symbols
        symbols = config['symbols']
        base_prices = {s: (50000 if 'BTC' in s else 3000 if 'ETH' in s else 1000) for s in symbols}

        start_time = datetime.utcnow()

        # Add data points
        for i in range(100):  # 100 data points per symbol
            for symbol in symbols:
                base_price = base_prices[symbol]
                price = base_price + np.random.normal(0, base_price * 0.002)
                volume = 100 + np.random.randint(-50, 50)

                system.add_market_data(symbol, price, volume)

        data_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"Data generation: {data_time:.2f}s")

        # Analyze all symbols
        start_time = datetime.utcnow()

        analysis_results = []
        for symbol in symbols:
            analysis = system.analyze_symbol(symbol, force_analysis=True)
            analysis_results.append(analysis)

        analysis_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"Analysis time: {analysis_time:.2f}s")
        print(f"Analysis per symbol: {analysis_time/len(symbols):.3f}s")

        # Test signal generation
        start_time = datetime.utcnow()

        signals = []
        for symbol in symbols:
            signal = system.get_signal_for_symbol(symbol)
            if signal:
                signals.append(signal)

        signal_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"Signal generation: {signal_time:.3f}s")
        print(f"Signals generated: {len(signals)}")

        # Test cache performance
        print("\nTesting cache performance...")
        start_time = datetime.utcnow()

        # Run same analysis again (should use cache)
        for symbol in symbols:
            system.analyze_symbol(symbol, force_analysis=True)

        cache_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"Cached analysis: {cache_time:.2f}s")

        # Get final metrics
        metrics = system.get_performance_metrics()
        cache_hit_rate = metrics['cache']['hit_rate']

        print(f"\nBenchmark Results:")
        print(f"Total symbols: {len(symbols)}")
        print(f"Data per symbol: 100 points")
        print(f"Analysis time: {analysis_time:.2f}s total, {analysis_time/len(symbols):.3f}s per symbol")
        print(f"Cache hit rate: {cache_hit_rate:.1%}")
        print(f"Memory usage: {metrics['cache'].get('total_memory_mb', 0):.1f}MB")

    finally:
        await system.stop()

async def main():
    """Run all examples."""
    print("Multi-Timeframe Confluence Analysis System Examples")
    print("=" * 60)

    try:
        # Basic example
        await basic_multi_timeframe_example()

        # Integration example
        await integration_example()

        # Real-time simulation
        await real_time_simulation()

        # Performance benchmark
        await performance_benchmark()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")

    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())