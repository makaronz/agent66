#!/usr/bin/env python3
"""
SMC ML Training Quick Start Script

This script provides a quick way to train SMC ML models for trading.
It demonstrates the complete workflow from data collection to model deployment.

Usage:
    python quick_start_training.py [--demo] [--symbols BTC/USDT] [--days 30]

Features:
- One-command training of complete SMC ML pipeline
- Demo mode with synthetic data for quick testing
- Configurable symbols, exchanges, and timeframes
- Automatic model saving and deployment setup
- Real-time progress tracking and logging
"""

import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from training.smc_training_pipeline import create_training_config, SMCTrainingPipeline
try:
    from training.deploy_models import ModelDeployer
except ImportError:
    from training.deploy_models import ModelDeployer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('training.log')
    ]
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Quick Start SMC ML Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run demo training with synthetic data
    python quick_start_training.py --demo

    # Train on specific symbols for 30 days
    python quick_start_training.py --symbols BTC/USDT ETH/USDT --days 30

    # Full training pipeline with 3 months of data
    python quick_start_training.py --months 3 --epochs 100

    # Custom configuration
    python quick_start_training.py --config custom_config.json
        """
    )

    # Data collection arguments
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo mode with synthetic data (default: real data collection)'
    )

    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['BTCUSDT'],
        help='Trading symbols (default: BTCUSDT)'
    )

    parser.add_argument(
        '--exchanges',
        nargs='+',
        default=['binance', 'bybit'],
        help='Exchanges to collect from (default: binance bybit)'
    )

    parser.add_argument(
        '--timeframes',
        nargs='+',
        default=['5m', '15m', '1h', '4h'],
        help='Timeframes to collect (default: 5m 15m 1h 4h)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days of historical data (default: 30)'
    )

    parser.add_argument(
        '--months',
        type=int,
        default=None,
        help='Number of months of historical data (overrides --days)'
    )

    # Training arguments
    parser.add_argument(
        '--epochs',
        type=int,
        default=50,
        help='Number of training epochs (default: 50)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=256,
        help='Training batch size (default: 256)'
    )

    parser.add_argument(
        '--learning-rate',
        type=float,
        default=0.001,
        help='Learning rate (default: 0.001)'
    )

    parser.add_argument(
        '--min-accuracy',
        type=float,
        default=0.55,
        help='Minimum accuracy threshold (default: 0.55)'
    )

    # Output arguments
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./smc_models',
        help='Output directory for models (default: ./smc_models)'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration JSON file'
    )

    parser.add_argument(
        '--deploy',
        action='store_true',
        help='Deploy models after training'
    )

    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip model validation (faster execution)'
    )

    # System arguments
    parser.add_argument(
        '--device',
        type=str,
        default='auto',
        choices=['auto', 'cpu', 'cuda'],
        help='Device for training (default: auto)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )

    return parser.parse_args()


def create_demo_config(args):
    """Create configuration for demo mode."""
    config = create_training_config(
        symbols=['BTCUSDT'],
        exchanges=['binance'],
        timeframes=['5m', '15m'],
        start_date=datetime.now() - timedelta(days=args.days),
        end_date=datetime.now(),
        data_dir='./demo_data',
        test_size=0.2,
        validation_size=0.2,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        epochs=min(args.epochs, 20),  # Reduce epochs for demo
        early_stopping_patience=5,
        min_accuracy=max(args.min_accuracy, 0.4),  # Lower threshold for demo
        device=args.device,
        model_dir=args.output_dir,
        random_seed=42,
        num_workers=args.workers
    )

    return config


def create_real_config(args):
    """Create configuration for real training."""
    # Calculate date range
    if args.months:
        start_date = datetime.now() - timedelta(days=args.months * 30)
    else:
        start_date = datetime.now() - timedelta(days=args.days)

    # Clean symbol names
    symbols = [s.replace('/', '') for s in args.symbols]

    config = create_training_config(
        symbols=symbols,
        exchanges=args.exchanges,
        timeframes=args.timeframes,
        start_date=start_date,
        end_date=datetime.now(),
        data_dir='./historical_data',
        test_size=0.2,
        validation_size=0.2,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        epochs=args.epochs,
        early_stopping_patience=15,
        min_accuracy=args.min_accuracy,
        device=args.device,
        model_dir=args.output_dir,
        random_seed=42,
        num_workers=args.workers
    )

    return config


def load_custom_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        # Convert ISO date strings to datetime objects if present
        if 'start_date' in config_dict and isinstance(config_dict['start_date'], str):
            config_dict['start_date'] = datetime.fromisoformat(config_dict['start_date'].replace('Z', '+00:00'))
        if 'end_date' in config_dict and isinstance(config_dict['end_date'], str):
            config_dict['end_date'] = datetime.fromisoformat(config_dict['end_date'].replace('Z', '+00:00'))
        
        # Create TrainingConfig object
        config = create_training_config(**config_dict)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config file {config_path}: {str(e)}")
        return None


def create_training_pipeline(args):
    """Create and initialize the training pipeline."""
    try:
        # Get configuration
        if args.config:
            config = load_custom_config(args.config)
            if config is None:
                logger.error("Failed to load configuration file")
                return None
        elif args.demo:
            config = create_demo_config(args)
            logger.info("Using demo configuration")
        else:
            config = create_real_config(args)

        # Set logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        logger.info(f"Training configuration:")
        logger.info(f"  Symbols: {config.symbols}")
        logger.info(f"  Exchanges: {config.exchanges}")
        logger.info(f"  Timeframes: {config.timeframes}")
        logger.info(f"  Data period: {config.start_date} to {config.end_date}")
        logger.info(f"  Epochs: {config.epochs}")
        logger.info(f"  Batch size: {config.batch_size}")
        logger.info(f"  Device: {config.device}")
        logger.info(f"  Output dir: {config.model_dir}")

        # Create pipeline
        pipeline = SMCTrainingPipeline(config)

        return pipeline

    except Exception as e:
        logger.error(f"Failed to create training pipeline: {str(e)}")
        return None


def format_results(results):
    """Format training results for display."""
    if results.get('status') == 'completed':
        perf_summary = results.get('performance_summary', {})
        model_perf = perf_summary.get('model_performance', {})
        ensemble_perf = perf_summary.get('ensemble_performance', {})

        print("\n" + "="*80)
        print("🎯 TRAINING COMPLETED SUCCESSFULLY!")
        print("="*80)

        print(f"\n📊 MODEL PERFORMANCE:")
        if 'lstm' in model_perf:
            lstm = model_perf['lstm']
            print(f"  🧠 LSTM Model:")
            print(f"    • Test Accuracy: {lstm.get('test_accuracy', 0):.4f}")
            print(f"    • Validation Loss: {lstm.get('best_val_loss', 0):.4f}")
            print(f"    • Epochs Trained: {lstm.get('epochs_trained', 0)}")
            print(f"    • Parameters: {lstm.get('parameters', 0):,}")

        if 'transformer' in model_perf:
            transformer = model_perf['transformer']
            print(f"  🔮 Transformer Model:")
            print(f"    • Test Accuracy: {transformer.get('test_accuracy', 0):.4f}")
            print(f"    • Validation Loss: {transformer.get('best_val_loss', 0):.4f}")
            print(f"    • Epochs Trained: {transformer.get('epochs_trained', 0)}")
            print(f"    • Parameters: {transformer.get('parameters', 0):,}")

        if 'ppo' in model_perf:
            ppo = model_perf['ppo']
            print(f"  🤖 PPO Agent:")
            print(f"    • Average Reward: {ppo.get('average_reward', 0):.4f}")
            print(f"    • Episodes Trained: {ppo.get('episodes_trained', 0)}")

        if ensemble_perf:
            print(f"\n🎯 ENSEMBLE PERFORMANCE:")
            print(f"  • Overall Accuracy: {ensemble_perf.get('ensemble_accuracy', 0):.4f}")
            print(f"  • Win Rate: {ensemble_perf.get('win_rate', 0):.4f}")
            print(f"  • Profit Factor: {ensemble_perf.get('profit_factor', 0):.2f}")
            print(f"  • Max Drawdown: {ensemble_perf.get('max_drawdown', 0):.4f}")
            print(f"  • Sharpe Ratio: {ensemble_perf.get('sharpe_ratio', 0):.4f}")

        targets = perf_summary.get('targets_met', {})
        print(f"\n✅ PERFORMANCE TARGETS:")
        print(f"  • Min Accuracy Met: {'✓' if targets.get('min_accuracy_met') else '✗'}")
        print(f"  • Max Latency Met: {'✓' if targets.get('max_latency_met') else '✗'}")
        print(f"  • Min Profit Factor Met: {'✓' if targets.get('min_profit_factor_met') else '✗'}")

        # Model paths
        model_paths = results.get('model_paths', {})
        if model_paths:
            print(f"\n💾 SAVED MODELS:")
            for model_name, path in model_paths.items():
                print(f"  • {model_name.title()}: {path}")

    else:
        print("\n❌ TRAINING FAILED!")
        if 'error' in results:
            print(f"  Error: {results['error']}")
        print(f"  Time: {results.get('total_time_seconds', 0):.2f}s")

    print("="*80)


async def main():
    """Main function."""
    start_time = time.time()

    # Parse arguments
    args = parse_arguments()

    logger.info("🚀 Starting SMC ML Training")
    logger.info(f"Mode: {'Demo' if args.demo else 'Real'}")
    logger.info(f"Arguments: {vars(args)}")

    try:
        # Create training pipeline
        pipeline = create_training_pipeline(args)
        if pipeline is None:
            return 1

        # Run training
        logger.info("\n🔄 Starting training pipeline...")
        results = await pipeline.run_complete_pipeline()

        # Format and display results
        format_results(results)

        # Deploy models if requested
        if args.deploy and results.get('status') == 'completed':
            logger.info("\n🚀 Deploying models...")
            deployer = ModelDeployer(
                model_dir=args.output_dir,
                config_file="deployment_config.json"
            )

            # Load models for deployment
            load_results = await deployer.load_models()

            # Perform health check
            health = deployer.health_check()

            print(f"\n🏥 DEPLOYMENT STATUS: {health.get('status', 'unknown').upper()}")
            if health.get('status') == 'healthy':
                print("  ✓ All models loaded successfully")
                print(f"  ✓ Scaler loaded: {health['checks']['scaler']['loaded']}")
                print(f"  ✓ Device: {health['checks']['device']['device']}")
            else:
                print("  ✗ Deployment failed - check logs for details")

        # Save results
        results_file = Path(args.output_dir) / 'training_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"💾 Results saved to {results_file}")

        # Total time
        total_time = time.time() - start_time
        logger.info(f"⏱️  Total execution time: {total_time:.2f} seconds")

        return 0 if results.get('status') == 'completed' else 1

    except KeyboardInterrupt:
        logger.info("\n🛑 Training interrupted by user")
        return 1

    except Exception as e:
        logger.error(f"\n💥 Unexpected error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)