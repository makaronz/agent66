#!/usr/bin/env python3
"""
Comprehensive test suite for Enhanced Configuration Manager

Tests configuration loading, validation, environment variable substitution,
and advanced features like hot reloading and export functionality.
"""

import pytest
import os
import yaml
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

# Import configuration management components
from config.enhanced_config_manager import (
    EnhancedConfigManager,
    EnhancedConfig,
    ConfigEnvironment,
    ConfigFormat,
    ConfigurationError,
    ConfigValidationError,
    ConfigFileNotFoundError,
    EnvironmentVariableSubstitutor,
    ConfigurationValidator,
    get_config_manager,
    load_config,
    get_config,
    get_value
)


class TestEnvironmentVariableSubstitutor:
    """Test environment variable substitution functionality"""

    def test_simple_substitution(self):
        """Test simple variable substitution"""
        os.environ['TEST_VAR'] = 'test_value'
        result = EnvironmentVariableSubstitutor.substitute('${TEST_VAR}')
        assert result == 'test_value'
        del os.environ['TEST_VAR']

    def test_substitution_with_default(self):
        """Test variable substitution with default value"""
        result = EnvironmentVariableSubstitutor.substitute('${MISSING_VAR:default_value}')
        assert result == 'default_value'

    def test_required_variable_with_error(self):
        """Test required variable with error message"""
        with pytest.raises(ConfigValidationError):
            EnvironmentVariableSubstitutor.substitute('${MISSING_VAR:?This variable is required}')

    def test_numeric_conversion(self):
        """Test automatic numeric conversion"""
        os.environ['TEST_INT'] = '42'
        os.environ['TEST_FLOAT'] = '3.14'
        os.environ['TEST_BOOL'] = 'true'

        assert EnvironmentVariableSubstitutor.substitute('${TEST_INT}') == 42
        assert EnvironmentVariableSubstitutor.substitute('${TEST_FLOAT}') == 3.14
        assert EnvironmentVariableSubstitutor.substitute('${TEST_BOOL}') is True

        del os.environ['TEST_INT'], os.environ['TEST_FLOAT'], os.environ['TEST_BOOL']

    def test_recursive_substitution(self):
        """Test recursive substitution in nested structures"""
        config = {
            'database': {
                'host': '${DB_HOST:localhost}',
                'port': '${DB_PORT:5432}',
                'credentials': {
                    'username': '${DB_USER:admin}',
                    'password': '${DB_PASS:?Database password required}'
                }
            },
            'servers': ['${SERVER_1:server1}', '${SERVER_2:server2}']
        }

        os.environ['DB_HOST'] = 'test-host'
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_USER'] = 'testuser'
        os.environ['DB_PASS'] = 'testpass'
        os.environ['SERVER_1'] = 'prod-server-1'

        result = EnvironmentVariableSubstitutor.substitute(config)

        assert result['database']['host'] == 'test-host'
        assert result['database']['port'] == 3306
        assert result['database']['credentials']['username'] == 'testuser'
        assert result['database']['credentials']['password'] == 'testpass'
        assert result['servers'][0] == 'prod-server-1'
        assert result['servers'][1] == 'server2'

        # Clean up
        del (os.environ['DB_HOST'], os.environ['DB_PORT'], os.environ['DB_USER'],
             os.environ['DB_PASS'], os.environ['SERVER_1'])


class TestEnhancedConfigManager:
    """Test enhanced configuration manager functionality"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary configuration directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            yield config_dir

    @pytest.fixture
    def sample_base_config(self, temp_config_dir):
        """Create sample base configuration"""
        base_config = {
            'environment': 'development',
            'debug': False,
            'log_level': 'INFO',
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'test_db',
                'username': 'test_user',
                'password': 'test_pass'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'exchanges': {
                'binance': {
                    'api_key': '${BINANCE_API_KEY}',
                    'api_secret': '${BINANCE_API_SECRET}',
                    'sandbox': True
                }
            },
            'risk': {
                'max_position_size': 1000.0,
                'max_portfolio_risk': 0.02
            },
            'monitoring': {
                'enabled': True,
                'prometheus_port': 8000
            },
            'trading': {
                'symbols': ['BTC/USDT'],
                'timeframe': '1h'
            }
        }

        base_file = temp_config_dir / 'base.yaml'
        with open(base_file, 'w') as f:
            yaml.dump(base_config, f)

        return base_file

    @pytest.fixture
    def sample_env_config(self, temp_config_dir):
        """Create sample environment-specific configuration"""
        env_config = {
            'environment': 'testing',
            'debug': True,
            'database': {
                'pool_size': 5,
                'timeout': 10
            },
            'risk': {
                'max_position_size': 500.0  # Override base config
            }
        }

        env_file = temp_config_dir / 'testing.yaml'
        with open(env_file, 'w') as f:
            yaml.dump(env_config, f)

        return env_file

    def test_config_initialization(self, temp_config_dir, sample_base_config):
        """Test basic configuration manager initialization"""
        manager = EnhancedConfigManager(config_dir=temp_config_dir)
        assert manager.config_dir == temp_config_dir
        assert manager.environment == 'development'  # Default environment
        assert len(manager._config_sources) > 0

    def test_environment_detection(self):
        """Test automatic environment detection"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            manager = EnhancedConfigManager()
            assert manager.environment == 'production'

        with patch.dict(os.environ, {'ENV': 'staging'}, clear=True):
            manager = EnhancedConfigManager()
            assert manager.environment == 'staging'

        # Test fallback to development
        with patch.dict(os.environ, {}, clear=True):
            manager = EnhancedConfigManager()
            assert manager.environment == 'development'

    def test_config_loading(self, temp_config_dir, sample_base_config, sample_env_config):
        """Test configuration loading and merging"""
        os.environ['BINANCE_API_KEY'] = 'test_api_key'
        os.environ['BINANCE_API_SECRET'] = 'test_api_secret'

        manager = EnhancedConfigManager(
            config_dir=temp_config_dir,
            environment='testing'
        )

        config = manager.load_config()

        # Test base configuration loaded
        assert config.database.host == 'localhost'
        assert config.database.port == 5432
        assert config.trading.symbols == ['BTC/USDT']

        # Test environment-specific overrides
        assert config.environment == 'testing'
        assert config.debug is True
        assert config.database.pool_size == 5
        assert config.risk.max_position_size == 500.0  # Should be overridden

        # Test environment variable substitution
        assert config.exchanges['binance'].api_key == 'test_api_key'
        assert config.exchanges['binance'].api_secret == 'test_api_secret'

        del os.environ['BINANCE_API_KEY'], os.environ['BINANCE_API_SECRET']

    def test_config_validation(self, temp_config_dir, sample_base_config):
        """Test configuration validation"""
        manager = EnhancedConfigManager(config_dir=temp_config_dir)
        config = manager.load_config()

        # Valid configuration should not raise exceptions
        assert config is not None
        assert isinstance(config, EnhancedConfig)

    def test_invalid_config_validation(self, temp_config_dir):
        """Test invalid configuration validation"""
        # Create invalid configuration
        invalid_config = {
            'environment': 'invalid_env',
            'database': {
                'port': 99999  # Invalid port
            },
            'trading': {
                'symbols': []  # Empty symbols list
            }
        }

        invalid_file = temp_config_dir / 'invalid.yaml'
        with open(invalid_file, 'w') as f:
            yaml.dump(invalid_config, f)

        manager = EnhancedConfigManager(config_dir=temp_config_dir)

        with pytest.raises(ConfigValidationError):
            manager.load_config()

    def test_missing_required_file(self, temp_config_dir):
        """Test handling of missing required configuration file"""
        # No configuration files exist
        manager = EnhancedConfigManager(config_dir=temp_config_dir)

        with pytest.raises(ConfigFileNotFoundError):
            manager.load_config()

    def test_optional_file_handling(self, temp_config_dir, sample_base_config):
        """Test handling of optional configuration files"""
        # Only base config exists, optional files are missing
        manager = EnhancedConfigManager(config_dir=temp_config_dir)

        # Should load successfully with just base config
        config = manager.load_config()
        assert config is not None

    def test_get_value_dot_notation(self, temp_config_dir, sample_base_config):
        """Test getting configuration values using dot notation"""
        manager = EnhancedConfigManager(config_dir=temp_config_dir)
        config = manager.load_config()

        # Test nested value access
        assert manager.get_value('database.host') == 'localhost'
        assert manager.get_value('database.port') == 5432
        assert manager.get_value('exchanges.binance.sandbox') is True

        # Test default values
        assert manager.get_value('nonexistent.key', 'default') == 'default'
        assert manager.get_value('database.nonexistent', None) is None

    def test_set_value_runtime(self, temp_config_dir, sample_base_config):
        """Test setting configuration values at runtime"""
        manager = EnhancedConfigManager(config_dir=temp_config_dir)
        config = manager.load_config()

        # Set new value
        manager.set_value('database.timeout', 30)
        assert manager.get_value('database.timeout') == 30

        # Override existing value
        manager.set_value('database.port', 3306)
        assert manager.get_value('database.port') == 3306

    def test_export_configuration(self, temp_config_dir, sample_base_config):
        """Test configuration export functionality"""
        manager = EnhancedConfigManager(config_dir=temp_config_dir)
        config = manager.load_config()

        # Test YAML export
        yaml_export = manager.export_config(format='yaml', include_secrets=False)
        assert 'database:' in yaml_export
        assert '***REDACTED***' in yaml_export  # Secrets should be redacted

        # Test JSON export
        json_export = manager.export_config(format='json', include_secrets=False)
        json_data = json.loads(json_export)
        assert 'database' in json_data

    def test_config_validation_issues(self, temp_config_dir):
        """Test configuration validation issue detection"""
        # Create config with validation issues
        problematic_config = {
            'environment': 'development',
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'test_db',
                'username': 'test_user',
                'password': 'test_pass'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'exchanges': {
                'binance': {
                    'api_key': '',  # Empty API key
                    'api_secret': '',  # Empty API secret
                    'sandbox': True
                }
            },
            'risk': {
                'max_position_size': -100.0,  # Negative position size
                'max_portfolio_risk': 0.02
            },
            'monitoring': {
                'enabled': True,
                'prometheus_port': 8000
            },
            'trading': {
                'symbols': [],  # Empty symbols list
                'timeframe': '1h',
                'order_timeout': -5  # Negative timeout
            }
        }

        config_file = temp_config_dir / 'problematic.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(problematic_config, f)

        manager = EnhancedConfigManager(config_dir=temp_config_dir)
        config = manager.load_config()

        issues = manager.validate_config()
        assert len(issues) > 0

        # Check for specific issues
        issue_messages = ' '.join(issues)
        assert 'API' in issue_messages or 'api' in issue_messages.lower()
        assert 'symbols' in issue_messages.lower()

    def test_auto_reload_functionality(self, temp_config_dir, sample_base_config):
        """Test configuration auto-reload functionality"""
        manager = EnhancedConfigManager(
            config_dir=temp_config_dir,
            auto_reload=False  # Disable for testing
        )

        initial_config = manager.load_config()
        initial_port = initial_config.database.port

        # Modify configuration file
        time.sleep(0.1)  # Ensure different timestamp
        modified_config = yaml.safe_load(sample_base_config.read_text())
        modified_config['database']['port'] = 3306

        with open(sample_base_config, 'w') as f:
            yaml.dump(modified_config, f)

        # Check if reload detects changes
        changed = manager.reload_config()
        assert changed is True

        # Verify the change
        updated_config = manager.get_config()
        assert updated_config.database.port == 3306

    def test_context_manager(self, temp_config_dir, sample_base_config):
        """Test configuration manager as context manager"""
        with EnhancedConfigManager(config_dir=temp_config_dir) as manager:
            config = manager.load_config()
            assert config is not None

        # Manager should be properly closed after context exit
        # (This is mainly to test that no exceptions are raised)

    def test_global_config_functions(self, temp_config_dir, sample_base_config):
        """Test global configuration utility functions"""
        # Patch global config manager
        with patch('config.enhanced_config_manager._config_manager') as mock_manager:
            mock_config = Mock()
            mock_config.database.host = 'test-host'
            mock_manager.get_config.return_value = mock_config

            # Test get_config
            config = get_config()
            assert config.database.host == 'test-host'

            # Test get_value
            value = get_value('database.host', 'default')
            assert value == 'test-host'


class TestConfigurationSetupUtility:
    """Test configuration setup utility"""

    def test_environment_validation(self):
        """Test environment validation in setup utility"""
        # Import here to avoid circular imports in test setup
        sys.path.append(str(Path(__file__).parent.parent / 'config'))
        from config_setup import ConfigSetup

        setup = ConfigSetup()

        # Test valid environments
        assert setup.initialize_environment('development') is False  # No config files

        # Test invalid environment
        try:
            setup.initialize_environment('invalid_env')
            assert False, "Should have raised an exception"
        except:
            pass  # Expected


class TestConfigurationIntegration:
    """Integration tests for configuration management"""

    def test_end_to_end_config_flow(self):
        """Test complete configuration management workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create base configuration
            base_config = {
                'environment': '${ENVIRONMENT:development}',
                'database': {
                    'host': '${DATABASE_HOST:localhost}',
                    'port': '${DATABASE_PORT:5432}',
                    'name': '${DATABASE_NAME:test_db}',
                    'username': '${DATABASE_USER:test_user}',
                    'password': '${DATABASE_PASS:?Database password required}'
                },
                'trading': {
                    'symbols': '${TRADING_SYMBOLS:["BTC/USDT"]}',
                    'max_concurrent_positions': '${MAX_POSITIONS:5}'
                },
                'risk': {
                    'max_position_size': '${MAX_POS_SIZE:1000.0}',
                    'max_portfolio_risk': '${MAX_RISK:0.02}'
                }
            }

            base_file = config_dir / 'base.yaml'
            with open(base_file, 'w') as f:
                yaml.dump(base_config, f)

            # Set environment variables
            env_vars = {
                'ENVIRONMENT': 'testing',
                'DATABASE_HOST': 'test-db-host',
                'DATABASE_PORT': '3306',
                'DATABASE_NAME': 'integration_test_db',
                'DATABASE_USER': 'integration_user',
                'DATABASE_PASS': 'integration_pass',
                'TRADING_SYMBOLS': '["BTC/USDT", "ETH/USDT"]',
                'MAX_POSITIONS': '3',
                'MAX_POS_SIZE': '500.0',
                'MAX_RISK': '0.01'
            }

            with patch.dict(os.environ, env_vars):
                # Initialize configuration manager
                manager = EnhancedConfigManager(
                    config_dir=config_dir,
                    environment='testing'
                )

                # Load configuration
                config = manager.load_config()

                # Verify environment variable substitution
                assert config.environment == 'testing'
                assert config.database.host == 'test-db-host'
                assert config.database.port == 3306
                assert config.database.name == 'integration_test_db'
                assert config.database.username == 'integration_user'
                assert config.database.password == 'integration_pass'
                assert config.trading.symbols == ['BTC/USDT', 'ETH/USDT']
                assert config.trading.max_concurrent_positions == 3
                assert config.risk.max_position_size == 500.0
                assert config.risk.max_portfolio_risk == 0.01

                # Test configuration validation
                issues = manager.validate_config()
                assert len(issues) == 0

                # Test export functionality
                exported_yaml = manager.export_config(format='yaml', include_secrets=True)
                exported_data = yaml.safe_load(exported_yaml)
                assert exported_data['database']['host'] == 'test-db-host'

                # Test export with secrets redacted
                exported_redacted = manager.export_config(format='yaml', include_secrets=False)
                assert '***REDACTED***' in exported_redacted

                # Test dot notation access
                assert manager.get_value('database.host') == 'test-db-host'
                assert manager.get_value('trading.symbols') == ['BTC/USDT', 'ETH/USDT']

                # Test runtime configuration changes
                manager.set_value('database.timeout', 30)
                assert manager.get_value('database.timeout') == 30

    def test_multi_source_priority(self):
        """Test configuration priority from multiple sources"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create base configuration
            base_config = {
                'environment': 'development',
                'database': {
                    'host': 'base-host',
                    'port': 5432,
                    'timeout': 30
                },
                'risk': {
                    'max_position_size': 1000.0,
                    'max_portfolio_risk': 0.02
                }
            }

            base_file = config_dir / 'base.yaml'
            with open(base_file, 'w') as f:
                yaml.dump(base_config, f)

            # Create environment override
            env_config = {
                'database': {
                    'host': 'env-host',
                    'pool_size': 10  # New field
                },
                'risk': {
                    'max_position_size': 500.0  # Override
                }
            }

            env_file = config_dir / 'development.yaml'
            with open(env_file, 'w') as f:
                yaml.dump(env_config, f)

            # Create local override
            local_config = {
                'database': {
                    'port': 3306  # Override base
                },
                'debug': True  # New field
            }

            local_file = config_dir / 'local.yaml'
            with open(local_file, 'w') as f:
                yaml.dump(local_config, f)

            manager = EnhancedConfigManager(config_dir=config_dir)
            config = manager.load_config()

            # Verify priority merging
            assert config.database.host == 'env-host'  # From env config
            assert config.database.port == 3306  # From local config
            assert config.database.timeout == 30  # From base config
            assert config.database.pool_size == 10  # From env config
            assert config.risk.max_position_size == 500.0  # From env config
            assert config.risk.max_portfolio_risk == 0.02  # From base config
            assert config.debug is True  # From local config


if __name__ == '__main__':
    pytest.main([__file__, '-v'])