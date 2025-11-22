#!/usr/bin/env python3
"""
Configuration setup utility for SMC Trading Agent

This script helps initialize and validate configuration for different environments.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.enhanced_config_manager import (
    EnhancedConfigManager,
    ConfigEnvironment,
    ConfigurationError,
    ConfigValidationError
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConfigSetup:
    """Configuration setup and validation utility"""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize config setup"""
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config_manager = None

    def initialize_environment(self, environment: str) -> bool:
        """
        Initialize configuration for a specific environment.

        Args:
            environment: Target environment (development, testing, staging, production)

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Initializing configuration for environment: {environment}")

            # Validate environment
            try:
                ConfigEnvironment(environment.lower())
                environment = environment.lower()
            except ValueError:
                logger.error(f"Invalid environment: {environment}")
                return False

            # Check required config files exist
            required_files = [
                self.config_dir / "base.yaml",
                self.config_dir / f"{environment}.yaml"
            ]

            missing_files = [f for f in required_files if not f.exists()]
            if missing_files:
                logger.error(f"Missing required config files: {missing_files}")
                return False

            # Initialize config manager
            self.config_manager = EnhancedConfigManager(
                config_dir=self.config_dir,
                environment=environment,
                auto_reload=False
            )

            # Load configuration
            config = self.config_manager.load_config()
            logger.info(f"Configuration loaded successfully for {environment}")

            # Validate configuration
            issues = self.config_manager.validate_config()
            if issues:
                logger.warning("Configuration validation issues found:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("Configuration validation passed")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            return False

    def create_env_file(self, environment: str, template: bool = True) -> bool:
        """
        Create .env file for the specified environment.

        Args:
            environment: Target environment
            template: Create as template (with placeholder values)

        Returns:
            True if successful, False otherwise
        """
        try:
            env_file = self.config_dir / f".env.{environment}"

            if env_file.exists() and not template:
                logger.warning(f"Environment file already exists: {env_file}")
                response = input("Overwrite? (y/N): ")
                if response.lower() != 'y':
                    return False

            # Environment-specific variables
            env_vars = self._get_environment_variables(environment, template)

            # Write .env file
            with open(env_file, 'w') as f:
                f.write(f"# Environment variables for {environment.upper()}\n")
                f.write(f"# Generated automatically - customize as needed\n\n")

                for key, value in env_vars.items():
                    if template and "password" in key.lower() or "secret" in key.lower() or "key" in key.lower():
                        f.write(f"{key}=\n")
                    else:
                        f.write(f"{key}={value}\n")

            logger.info(f"Created environment file: {env_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to create environment file: {e}")
            return False

    def _get_environment_variables(self, environment: str, template: bool) -> Dict[str, str]:
        """Get environment variables for the specified environment"""
        env_vars = {
            # Core settings
            "ENVIRONMENT": environment,
            "LOG_LEVEL": "DEBUG" if environment in ["development", "testing"] else "INFO",
            "DEBUG": "true" if environment == "development" else "false",

            # Database settings
            "DATABASE_HOST": "localhost" if environment != "production" else "your_prod_db_host",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": f"smc_trading_{environment}",
            "DATABASE_USERNAME": f"{environment}_trader",
            "DATABASE_PASSWORD": "your_password_here" if template else "",

            # Redis settings
            "REDIS_HOST": "localhost" if environment != "production" else "your_prod_redis_host",
            "REDIS_PORT": "6379",
            "REDIS_DB": {"development": "1", "testing": "15", "staging": "2", "production": "0"}.get(environment, "0"),

            # Exchange settings
            "BINANCE_SANDBOX": "true" if environment != "production" else "false",
            "BINANCE_TESTNET": "true" if environment != "production" else "false",
            "BYBIT_SANDBOX": "true" if environment != "production" else "false",
            "BYBIT_TESTNET": "true" if environment != "production" else "false",
            "OANDA_SANDBOX": "true" if environment != "production" else "false",
            "OANDA_TESTNET": "true" if environment != "production" else "false",

            # Trading settings
            "TRADING_SYMBOLS": '["BTC/USDT"]' if environment == "development" else '["BTC/USDT", "ETH/USDT"]',
            "TRADING_TIMEFRAME": "5m" if environment == "development" else "1h",
            "MAX_CONCURRENT_POSITIONS": "1" if environment == "development" else "5",

            # Risk settings
            "MAX_POSITION_SIZE": "100.0" if environment == "development" else "1000.0",
            "MAX_PORTFOLIO_RISK": "0.01" if environment in ["development", "testing"] else "0.02",
            "MAX_DAILY_LOSS": "50.0" if environment == "development" else "500.0",

            # Feature flags
            "ENHANCED_SMC_DETECTION": "true",
            "ADVANCED_RISK_MANAGEMENT": "true",
            "ULTRA_LOW_LATENCY_EXECUTION": "false" if environment == "development" else "true",
            "CIRCUIT_BREAKER_PROTECTION": "true",
            "DISTRIBUTED_TRACING": "true",
            "AUTO_SCALING": "false" if environment in ["development", "testing"] else "true",
        }

        return env_vars

    def validate_configuration(self, config_file: Optional[str] = None) -> bool:
        """
        Validate configuration without loading it.

        Args:
            config_file: Specific config file to validate (validates current if None)

        Returns:
            True if valid, False otherwise
        """
        try:
            if config_file:
                # Validate specific file
                config_path = Path(config_file)
                if not config_path.exists():
                    logger.error(f"Config file not found: {config_file}")
                    return False

                # Create temporary config manager to validate
                temp_manager = EnhancedConfigManager(config_dir=config_path.parent)
                temp_manager._config_sources = [
                    type(temp_manager._config_sources[0])(
                        name="validation",
                        path=config_path,
                        format=ConfigFormat.YAML,
                        required=True,
                        priority=100
                    )
                ]

                temp_manager.load_config()
                logger.info(f"Configuration file {config_file} is valid")
            else:
                # Validate current configuration
                if not self.config_manager:
                    logger.error("No configuration loaded to validate")
                    return False

                issues = self.config_manager.validate_config()
                if issues:
                    logger.error("Configuration validation failed:")
                    for issue in issues:
                        logger.error(f"  - {issue}")
                    return False
                else:
                    logger.info("Current configuration is valid")

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def export_configuration(self, output_file: str, format: str = "yaml",
                           include_secrets: bool = False) -> bool:
        """
        Export current configuration to file.

        Args:
            output_file: Output file path
            format: Export format (yaml, json)
            include_secrets: Include sensitive information

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.config_manager:
                logger.error("No configuration loaded to export")
                return False

            exported_config = self.config_manager.export_config(
                format=format,
                include_secrets=include_secrets
            )

            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                f.write(exported_config)

            logger.info(f"Configuration exported to: {output_path}")
            if not include_secrets:
                logger.info("Sensitive information has been redacted")

            return True

        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False

    def show_configuration(self, section: Optional[str] = None,
                          show_secrets: bool = False) -> bool:
        """
        Display current configuration.

        Args:
            section: Specific section to show (shows all if None)
            show_secrets: Include sensitive information

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.config_manager:
                logger.error("No configuration loaded to display")
                return False

            if section:
                config_section = self.config_manager.get_section(section)
                if config_section is None:
                    logger.error(f"Configuration section not found: {section}")
                    return False

                print(f"\n=== Configuration Section: {section.upper()} ===")
                print(config_section)
            else:
                config = self.config_manager.get_config()
                if not show_secrets:
                    # Export and redact secrets
                    config_str = self.config_manager.export_config(
                        format="yaml",
                        include_secrets=False
                    )
                    print(config_str)
                else:
                    print(config)

            return True

        except Exception as e:
            logger.error(f"Failed to display configuration: {e}")
            return False


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="SMC Trading Agent Configuration Setup")
    parser.add_argument("action", choices=[
        "init", "validate", "export", "show", "create-env"
    ], help="Action to perform")

    parser.add_argument("--environment", "-e",
                       choices=["development", "testing", "staging", "production"],
                       help="Target environment")
    parser.add_argument("--config-dir", "-c",
                       help="Configuration directory path")
    parser.add_argument("--output", "-o",
                       help="Output file for export")
    parser.add_argument("--format", "-f", choices=["yaml", "json"], default="yaml",
                       help="Export format")
    parser.add_argument("--section", "-s",
                       help="Configuration section to show/export")
    parser.add_argument("--include-secrets", action="store_true",
                       help="Include sensitive information")
    parser.add_argument("--template", action="store_true",
                       help="Create template files")

    args = parser.parse_args()

    # Initialize config setup
    setup = ConfigSetup(args.config_dir)

    success = False

    if args.action == "init":
        if not args.environment:
            logger.error("Environment required for initialization")
            return 1

        success = setup.initialize_environment(args.environment)

        if success:
            # Also create .env file
            setup.create_env_file(args.environment, template=True)

    elif args.action == "validate":
        success = setup.validate_configuration()

    elif args.action == "export":
        if not args.output:
            logger.error("Output file required for export")
            return 1

        if not setup.config_manager:
            # Load configuration first
            if args.environment:
                setup.initialize_environment(args.environment)
            else:
                setup.initialize_environment("development")

        success = setup.export_configuration(
            args.output,
            args.format,
            args.include_secrets
        )

    elif args.action == "show":
        if not setup.config_manager:
            # Load configuration first
            if args.environment:
                setup.initialize_environment(args.environment)
            else:
                setup.initialize_environment("development")

        success = setup.show_configuration(
            args.section,
            args.include_secrets
        )

    elif args.action == "create-env":
        if not args.environment:
            logger.error("Environment required for .env creation")
            return 1

        success = setup.create_env_file(args.environment, args.template)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())