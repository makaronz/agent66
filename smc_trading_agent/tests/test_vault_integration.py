"""
Integration tests for Vault client functionality
Tests actual Vault integration with proper error handling
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from vault_client import (
    VaultClient, VaultClientError, get_vault_client,
    get_database_url, get_exchange_credentials, get_jwt_secret
)


class TestVaultClient:
    """Test Vault client functionality"""
    
    @pytest.fixture
    def mock_vault_client(self):
        """Create a mock Vault client for testing"""
        with patch('vault_client.hvac.Client') as mock_hvac:
            mock_client = Mock()
            mock_hvac.return_value = mock_client
            
            # Mock successful authentication
            mock_client.is_authenticated.return_value = True
            mock_client.lookup_token.return_value = {'data': {'ttl': 3600}}
            
            # Mock secret responses
            mock_client.secrets.kv.v2.read_secret_version.return_value = {
                'data': {
                    'data': {
                        'url': 'postgresql://test:test@localhost:5432/test',
                        'password': 'test_password',
                        'api_key': 'test_api_key',
                        'api_secret': 'test_api_secret',
                        'secret': 'test_jwt_secret',
                        'encryption_key': 'test_encryption_key'
                    }
                }
            }
            
            yield VaultClient()
    
    def test_vault_client_initialization(self, mock_vault_client):
        """Test Vault client initializes correctly"""
        assert mock_vault_client is not None
        assert mock_vault_client.vault_url == 'http://vault.vault.svc.cluster.local:8200'
        assert mock_vault_client.kubernetes_role == 'smc-trading-role'
    
    def test_get_database_config(self, mock_vault_client):
        """Test database configuration retrieval"""
        config = mock_vault_client.get_database_config()
        
        assert 'DATABASE_URL' in config
        assert 'DATABASE_PASSWORD' in config
        assert config['DATABASE_URL'] == 'postgresql://test:test@localhost:5432/test'
        assert config['DATABASE_PASSWORD'] == 'test_password'
    
    def test_get_exchange_config_binance(self, mock_vault_client):
        """Test Binance exchange configuration retrieval"""
        config = mock_vault_client.get_exchange_config('binance')
        
        assert 'BINANCE_API_KEY' in config
        assert 'BINANCE_API_SECRET' in config
        assert config['BINANCE_API_KEY'] == 'test_api_key'
        assert config['BINANCE_API_SECRET'] == 'test_api_secret'
    
    def test_get_exchange_config_invalid(self, mock_vault_client):
        """Test invalid exchange configuration raises error"""
        with pytest.raises(VaultClientError, match="Unsupported exchange"):
            mock_vault_client.get_exchange_config('invalid_exchange')
    
    def test_get_jwt_config(self, mock_vault_client):
        """Test JWT configuration retrieval"""
        config = mock_vault_client.get_jwt_config()
        
        assert 'JWT_SECRET' in config
        assert 'ENCRYPTION_KEY' in config
        assert config['JWT_SECRET'] == 'test_jwt_secret'
        assert config['ENCRYPTION_KEY'] == 'test_encryption_key'
    
    def test_secret_caching(self, mock_vault_client):
        """Test secret caching functionality"""
        # First call should hit Vault
        config1 = mock_vault_client.get_database_config()
        
        # Second call should use cache
        config2 = mock_vault_client.get_database_config()
        
        assert config1 == config2
        # Verify Vault was only called once
        mock_vault_client.client.secrets.kv.v2.read_secret_version.assert_called_once()
    
    def test_cache_invalidation(self, mock_vault_client):
        """Test cache invalidation"""
        # Get secret to populate cache
        mock_vault_client.get_database_config()
        
        # Invalidate cache
        mock_vault_client.invalidate_cache('secret/data/smc-trading/database')
        
        # Next call should hit Vault again
        mock_vault_client.get_database_config()
        
        # Verify Vault was called twice
        assert mock_vault_client.client.secrets.kv.v2.read_secret_version.call_count == 2
    
    def test_health_check(self, mock_vault_client):
        """Test health check functionality"""
        mock_vault_client.client.sys.read_health_status.return_value = {
            'sealed': False,
            'standby': False
        }
        
        health = mock_vault_client.health_check()
        
        assert health['authenticated'] is True
        assert health['sealed'] is False
        assert health['standby'] is False
        assert 'cache_size' in health
    
    def test_vault_error_handling(self, mock_vault_client):
        """Test Vault error handling"""
        from hvac.exceptions import InvalidPath
        
        # Mock Vault error
        mock_vault_client.client.secrets.kv.v2.read_secret_version.side_effect = InvalidPath()
        
        with pytest.raises(VaultClientError, match="Secret not found"):
            mock_vault_client.get_secret('secret/data/nonexistent')
    
    def test_retry_mechanism(self, mock_vault_client):
        """Test retry mechanism on failures"""
        from hvac.exceptions import VaultError
        
        # Mock first call fails, second succeeds
        mock_vault_client.client.secrets.kv.v2.read_secret_version.side_effect = [
            VaultError("Temporary failure"),
            {
                'data': {
                    'data': {'test': 'value'}
                }
            }
        ]
        
        result = mock_vault_client.get_secret('secret/data/test')
        assert result == {'test': 'value'}
        
        # Verify retry happened
        assert mock_vault_client.client.secrets.kv.v2.read_secret_version.call_count == 2


class TestVaultIntegration:
    """Test Vault integration with application components"""
    
    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables"""
        with patch.dict(os.environ, {
            'VAULT_ADDR': 'http://test-vault:8200',
            'VAULT_TOKEN': 'test-token',
            'DATABASE_URL': 'postgresql://fallback:fallback@localhost:5432/fallback'
        }):
            yield
    
    @patch('vault_client.VaultClient')
    def test_get_database_url_success(self, mock_vault_class, mock_environment):
        """Test successful database URL retrieval from Vault"""
        mock_client = Mock()
        mock_client.get_database_config.return_value = {
            'DATABASE_URL': 'postgresql://vault:vault@localhost:5432/vault'
        }
        mock_vault_class.return_value = mock_client
        
        url = get_database_url()
        assert url == 'postgresql://vault:vault@localhost:5432/vault'
    
    @patch('vault_client.VaultClient')
    def test_get_database_url_fallback(self, mock_vault_class, mock_environment):
        """Test database URL fallback to environment variable"""
        mock_client = Mock()
        mock_client.get_database_config.side_effect = VaultClientError("Vault unavailable")
        mock_vault_class.return_value = mock_client
        
        url = get_database_url()
        assert url == 'postgresql://fallback:fallback@localhost:5432/fallback'
    
    @patch('vault_client.VaultClient')
    def test_get_exchange_credentials_success(self, mock_vault_class, mock_environment):
        """Test successful exchange credentials retrieval"""
        mock_client = Mock()
        mock_client.get_exchange_config.return_value = {
            'BINANCE_API_KEY': 'vault_api_key',
            'BINANCE_API_SECRET': 'vault_api_secret'
        }
        mock_vault_class.return_value = mock_client
        
        creds = get_exchange_credentials('binance')
        assert creds['BINANCE_API_KEY'] == 'vault_api_key'
        assert creds['BINANCE_API_SECRET'] == 'vault_api_secret'
    
    @patch('vault_client.VaultClient')
    def test_get_exchange_credentials_fallback(self, mock_vault_class, mock_environment):
        """Test exchange credentials fallback to environment variables"""
        mock_client = Mock()
        mock_client.get_exchange_config.side_effect = VaultClientError("Vault unavailable")
        mock_vault_class.return_value = mock_client
        
        with patch.dict(os.environ, {
            'BINANCE_API_KEY': 'env_api_key',
            'BINANCE_API_SECRET': 'env_api_secret'
        }):
            creds = get_exchange_credentials('binance')
            assert creds['BINANCE_API_KEY'] == 'env_api_key'
            assert creds['BINANCE_API_SECRET'] == 'env_api_secret'
    
    @patch('vault_client.VaultClient')
    def test_get_jwt_secret_success(self, mock_vault_class, mock_environment):
        """Test successful JWT secret retrieval"""
        mock_client = Mock()
        mock_client.get_jwt_config.return_value = {
            'JWT_SECRET': 'vault_jwt_secret'
        }
        mock_vault_class.return_value = mock_client
        
        secret = get_jwt_secret()
        assert secret == 'vault_jwt_secret'
    
    @patch('vault_client.VaultClient')
    def test_get_jwt_secret_fallback(self, mock_vault_class, mock_environment):
        """Test JWT secret fallback to environment variable"""
        mock_client = Mock()
        mock_client.get_jwt_config.side_effect = VaultClientError("Vault unavailable")
        mock_vault_class.return_value = mock_client
        
        with patch.dict(os.environ, {'JWT_SECRET': 'env_jwt_secret'}):
            secret = get_jwt_secret()
            assert secret == 'env_jwt_secret'


class TestVaultAuthentication:
    """Test Vault authentication methods"""
    
    @patch('vault_client.hvac.Client')
    @patch('os.path.exists')
    def test_kubernetes_authentication(self, mock_exists, mock_hvac):
        """Test Kubernetes service account authentication"""
        mock_exists.return_value = True
        
        mock_client = Mock()
        mock_hvac.return_value = mock_client
        
        # Mock successful Kubernetes auth
        mock_client.auth.kubernetes.login.return_value = {
            'auth': {'client_token': 'k8s_token'}
        }
        
        with patch('builtins.open', mock_open(read_data='service_account_jwt')):
            vault_client = VaultClient()
            
        mock_client.auth.kubernetes.login.assert_called_once_with(
            role='smc-trading-role',
            jwt='service_account_jwt'
        )
        assert mock_client.token == 'k8s_token'
    
    @patch('vault_client.hvac.Client')
    @patch('os.path.exists')
    def test_token_file_authentication(self, mock_exists, mock_hvac):
        """Test token file authentication (Vault Agent)"""
        mock_exists.return_value = True
        
        mock_client = Mock()
        mock_hvac.return_value = mock_client
        
        with patch('builtins.open', mock_open(read_data='file_token')):
            vault_client = VaultClient(token_file_path='/vault/secrets/token')
            
        assert mock_client.token == 'file_token'
    
    @patch('vault_client.hvac.Client')
    def test_direct_token_authentication(self, mock_hvac):
        """Test direct token authentication"""
        mock_client = Mock()
        mock_hvac.return_value = mock_client
        
        vault_client = VaultClient(vault_token='direct_token')
        
        assert mock_client.token == 'direct_token'


def mock_open(read_data=''):
    """Helper function to mock file operations"""
    from unittest.mock import mock_open as _mock_open
    return _mock_open(read_data=read_data)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])