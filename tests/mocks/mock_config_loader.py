"""
Mock configuration loader for testing.
"""

def load_secure_config(config_path, env_file=None):
    """Mock secure config loader."""
    return {
        'app': {
            'name': 'smc-trading-agent-test',
            'version': '1.0.0'
        },
        'logging': {
            'version': 1,
            'formatters': {
                'default': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'default'
                }
            },
            'root': {
                'level': 'INFO',
                'handlers': ['console']
            }
        },
        'database': {
            'url': 'postgresql://test:test@localhost/test_db'
        },
        'exchanges': {
            'binance': {'api_key': 'test_key', 'api_secret': 'test_secret'},
            'bybit': {'api_key': 'test_key', 'api_secret': 'test_secret'}
        },
        'decision_engine': {
            'confidence_threshold': 0.7
        },
        'monitoring': {
            'port': 8008
        }
    }


class ConfigValidationError(Exception):
    """Mock config validation error."""
    pass


class EnvironmentVariableError(Exception):
    """Mock environment variable error."""
    pass