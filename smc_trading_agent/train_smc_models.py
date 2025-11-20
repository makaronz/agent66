#!/usr/bin/env python3
"""
SMC ML Models Training Script

This script trains the ML models for SMC pattern recognition.
It demonstrates the complete training pipeline from data collection to model deployment.

Usage:
    python train_smc_models.py [--symbols BTC/USDT] [--months 12] [--output-dir ./models]

Features:
- Historical data collection for SMC patterns
- Feature engineering and preprocessing
- Multi-model training (LSTM, Transformer, PPO)
- Performance evaluation and validation
- Model versioning and deployment package creation
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from decision_engine import get_smc_training_pipeline, SMCTrainingConfig
from decision_engine.smc_training_pipeline import SMCTrainingPipeline
from decision_engine.ml_config import get_ml_config, DeploymentStage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Train SMC ML Models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Train on default settings (BTC/USDT, 12 months)
    python train_smc_models.py

    # Train on multiple symbols with custom duration
    python train_smc_models.py --symbols BTC/USDT ETH/USDT --months 24

    # Custom model configuration
    python train_smc_models.py --epochs 200 --batch-size 128 --sequence-length 120
        """
    )

    # Data collection arguments
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['BTC/USDT'],
        help='Trading symbols to train on (default: BTC/USDT)'
    )

    parser.add_argument(
        '--months',
        type=int,
        default=12,
        help='Months of historical data to collect (default: 12)'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for training data (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for training data (YYYY-MM-DD format)'
    )

    # Training configuration arguments
    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help='Number of training epochs (default: 100)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=64,
        help='Training batch size (default: 64)'
    )

    parser.add_argument(
        '--sequence-length',
        type=int,
        default=60,
        help='Sequence length for time series models (default: 60)'
    )

    parser.add_argument(
        '--learning-rate',
        type=float,
        default=0.001,
        help='Learning rate for model training (default: 0.001)'
    )

    # Validation arguments
    parser.add_argument(
        '--validation-split',
        type=float,
        default=0.2,
        help='Validation data split ratio (default: 0.2)'
    )

    parser.add_argument(
        '--early-stopping-patience',
        type=int,
        default=10,
        help='Early stopping patience (default: 10)'
    )

    # Output arguments
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./models',
        help='Output directory for trained models (default: ./models)'
    )

    parser.add_argument(
        '--model-version',
        type=str,
        default=f'smc_v{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        help='Model version identifier (default: auto-generated)'
    )

    # Performance arguments
    parser.add_argument(
        '--min-accuracy',
        type=float,
        default=0.55,
        help='Minimum accuracy threshold for successful training (default: 0.55)'
    )

    parser.add_argument(
        '--max-drawdown',
        type=float,
        default=0.2,
        help='Maximum allowed drawdown for validation (default: 0.2)'
    )

    # System arguments
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers for data processing (default: 4)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


async def main():
    """Main training function."""
    args = parse_arguments()

    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 80)
    logger.info("SMC ML Models Training Pipeline")
    logger.info("=" * 80)

    try:
        # Parse date arguments
        end_date = datetime.now()
        if args.end_date:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

        start_date = None
        if args.start_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        else:
            start_date = end_date - timedelta(days=args.months * 30)

        logger.info(f"Training period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Symbols: {args.symbols}")
        logger.info(f"Output directory: {args.output_dir}")

        # Create training configuration
        training_config = SMCTrainingConfig(
            train_period_months=args.months,
            validation_split=args.validation_split,
            epochs_lstm=args.epochs,
            epochs_transformer=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            sequence_length=args.sequence_length,
            early_stopping_patience=args.early_stopping_patience,
            min_accuracy=args.min_accuracy,
            max_drawdown_threshold=args.max_drawdown
        )

        logger.info("Training Configuration:")
        logger.info(f"  - Training Period: {training_config.train_period_months} months")
        logger.info(f"  - Validation Split: {training_config.validation_split}")
        logger.info(f"  - LSTM Epochs: {training_config.epochs_lstm}")
        logger.info(f"  - Transformer Epochs: {training_config.epochs_transformer}")
        logger.info(f"  - Batch Size: {training_config.batch_size}")
        logger.info(f"  - Learning Rate: {training_config.learning_rate}")
        logger.info(f"  - Sequence Length: {training_config.sequence_length}")
        logger.info(f"  - Min Accuracy: {training_config.min_accuracy}")

        # Initialize training pipeline
        pipeline = SMCTrainingPipeline(config=training_config)

        logger.info("Starting training pipeline...")

        # Run the complete training pipeline
        results = await pipeline.run_full_training_pipeline(
            symbols=args.symbols,
            start_date=start_date,
            end_date=end_date
        )

        # Process results
        if results['status'] == 'completed':
            logger.info("✅ Training completed successfully!")

            # Extract key metrics
            data_collection = results.get('data_collection', {})
            training_results = results.get('training_results', {})

            logger.info("\n📊 Training Summary:")
            logger.info(f"  - Samples Collected: {data_collection.get('samples_collected', 0):,}")
            logger.info(f"  - Symbols Trained: {', '.join(data_collection.get('symbols_trained', []))}")

            # Model performance summary
            summary = training_results.get('summary', {})
            model_performance = summary.get('model_performance', {})

            for model_name, metrics in model_performance.items():
                logger.info(f"  - {model_name.upper()} Performance:")
                logger.info(f"    * Accuracy: {metrics.get('accuracy', 0):.3f}")
                logger.info(f"    * F1 Score: {metrics.get('f1_score', 0):.3f}")
                logger.info(f"    * Training Epochs: {metrics.get('training_epochs', 0)}")

            # Recommendations
            recommendations = summary.get('recommendations', [])
            if recommendations:
                logger.info("\n💡 Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    logger.info(f"  {i}. {rec}")

            # Update ML configuration for deployment
            if model_performance:
                logger.info("\n🚀 Updating ML configuration for deployment...")

                ml_config = get_ml_config()

                # Set deployment stage to shadow mode initially
                ml_config.set_deployment_stage(DeploymentStage.SHADOW)

                # Update model weights based on performance
                if 'lstm' in model_performance and 'transformer' in model_performance:
                    lstm_acc = model_performance['lstm'].get('accuracy', 0)
                    transformer_acc = model_performance['transformer'].get('accuracy', 0)

                    # Normalize weights based on performance
                    total_acc = lstm_acc + transformer_acc
                    if total_acc > 0:
                        lstm_weight = lstm_acc / total_acc
                        transformer_weight = transformer_acc / total_acc

                        ml_config.update_config({
                            'lstm_config': {
                                **ml_config.config.lstm_config.__dict__,
                                'weight': lstm_weight
                            },
                            'transformer_config': {
                                **ml_config.config.transformer_config.__dict__,
                                'weight': transformer_weight
                            }
                        })

                        logger.info(f"Updated model weights based on performance:")
                        logger.info(f"  - LSTM: {lstm_weight:.3f}")
                        logger.info(f"  - Transformer: {transformer_weight:.3f}")

                logger.info("✅ ML configuration updated successfully")

            # Create deployment report
            deployment_report = {
                'training_completed': datetime.now().isoformat(),
                'model_version': args.model_version,
                'training_results': results,
                'deployment_config': {
                    'stage': 'shadow',
                    'symbols': args.symbols,
                    'training_period_months': args.months
                }
            }

            report_path = Path(args.output_dir) / f"training_report_{args.model_version}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)

            import json
            with open(report_path, 'w') as f:
                json.dump(deployment_report, f, indent=2, default=str)

            logger.info(f"📄 Training report saved to: {report_path}")

            return 0

        else:
            logger.error("❌ Training failed!")
            error = results.get('error', 'Unknown error')
            logger.error(f"Error: {error}")

            return 1

    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error during training: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)