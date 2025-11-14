"""
Mock Vault client for testing.
"""

class MockVaultClient:
    """Mock Vault client that doesn't require actual Vault connection."""
    
    def __init__(self):
        self.is_authenticated = True
    
    def get_database_config(self):
        return {
            'DATABASE_URL': 'postgresql://test:test@localhost/test_db',
            'DATABASE_PASSWORD': 'test_password'
        }
    
    def get_exchange_config(self, exchange):
        return {
            'api_key': f'test_{exchange}_key',
            'api_secret': f'test_{exchange}_secret'
        }
    
    def get_jwt_config(self):
        return {
            'jwt_secret': 'test_jwt_secret'
        }
    
    def get_redis_config(self):
        return {
            'redis_url': 'redis://localhost:6379'
        }


class VaultClientError(Exception):
    """Mock Vault client error."""
    pass


def get_vault_client():
    """Mock function to get vault client."""
    return MockVaultClient()


def get_database_url():
    """Mock function to get database URL."""
    return 'postgresql://test:test@localhost/test_db'


def get_exchange_credentials(exchange):
    """Mock function to get exchange credentials."""
    return {
        'api_key': f'test_{exchange}_key',
        'api_secret': f'test_{exchange}_secret'
    }