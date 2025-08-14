"""
Production-ready HashiCorp Vault client for SMC Trading Agent
Handles secret retrieval, caching, and automatic token renewal
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
import hvac
from hvac.exceptions import VaultError, InvalidPath
import threading
from datetime import datetime, timedelta
import requests
from functools import wraps

logger = logging.getLogger(__name__)


class VaultClientError(Exception):
    """Custom exception for Vault client errors"""
    pass


class VaultClient:
    """Production Vault client with automatic token renewal and caching"""
    
    def __init__(
        self,
        vault_url: str = None,
        vault_token: str = None,
        kubernetes_role: str = None,
        token_file_path: str = "/vault/secrets/token",
        cache_ttl: int = 300,  # 5 minutes
        max_retries: int = 3
    ):
        self.vault_url = vault_url or os.getenv('VAULT_ADDR', 'http://vault.vault.svc.cluster.local:8200')
        self.vault_token = vault_token
        self.kubernetes_role = kubernetes_role or os.getenv('VAULT_ROLE', 'smc-trading-role')
        self.token_file_path = token_file_path
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        
        # Initialize client
        self.client = hvac.Client(url=self.vault_url)
        self._secret_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._token_renewal_thread = None
        self._stop_renewal = threading.Event()
        
        # Authenticate
        self._authenticate()
        
        # Start token renewal thread
        self._start_token_renewal()
    
    def _authenticate(self):
        """Authenticate with Vault using available methods"""
        try:
            # Try token from file (Vault Agent)
            if os.path.exists(self.token_file_path):
                with open(self.token_file_path, 'r') as f:
                    token = f.read().strip()
                self.client.token = token
                logger.info("Authenticated with Vault using token from file")
                return
            
            # Try direct token
            if self.vault_token:
                self.client.token = self.vault_token
                logger.info("Authenticated with Vault using provided token")
                return
            
            # Try Kubernetes authentication
            if self._authenticate_kubernetes():
                logger.info("Authenticated with Vault using Kubernetes service account")
                return
            
            # Try environment token as fallback
            env_token = os.getenv('VAULT_TOKEN')
            if env_token:
                self.client.token = env_token
                logger.info("Authenticated with Vault using environment token")
                return
            
            raise VaultClientError("No valid authentication method found")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Vault: {e}")
            raise VaultClientError(f"Authentication failed: {e}")
    
    def _authenticate_kubernetes(self) -> bool:
        """Authenticate using Kubernetes service account"""
        try:
            jwt_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
            if not os.path.exists(jwt_path):
                return False
            
            with open(jwt_path, 'r') as f:
                jwt_token = f.read().strip()
            
            # Authenticate with Kubernetes auth method
            auth_response = self.client.auth.kubernetes.login(
                role=self.kubernetes_role,
                jwt=jwt_token
            )
            
            self.client.token = auth_response['auth']['client_token']
            return True
            
        except Exception as e:
            logger.warning(f"Kubernetes authentication failed: {e}")
            return False
    
    def _start_token_renewal(self):
        """Start background thread for token renewal"""
        if self._token_renewal_thread and self._token_renewal_thread.is_alive():
            return
        
        self._token_renewal_thread = threading.Thread(
            target=self._token_renewal_loop,
            daemon=True
        )
        self._token_renewal_thread.start()
    
    def _token_renewal_loop(self):
        """Background loop for token renewal"""
        while not self._stop_renewal.is_set():
            try:
                # Check token validity
                if self.client.is_authenticated():
                    # Renew token if it expires within 5 minutes
                    token_info = self.client.lookup_token()
                    ttl = token_info.get('data', {}).get('ttl', 0)
                    
                    if ttl < 300:  # Less than 5 minutes
                        self.client.renew_token()
                        logger.info("Vault token renewed successfully")
                else:
                    # Re-authenticate if token is invalid
                    logger.warning("Vault token invalid, re-authenticating")
                    self._authenticate()
                
            except Exception as e:
                logger.error(f"Token renewal failed: {e}")
            
            # Wait 60 seconds before next check
            self._stop_renewal.wait(60)
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached secret is still valid"""
        if key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[key]
        return datetime.now() - cache_time < timedelta(seconds=self.cache_ttl)
    
    def _retry_on_failure(self, func):
        """Decorator for retrying Vault operations"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except (VaultError, requests.RequestException) as e:
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Vault operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                        
                        # Try to re-authenticate on auth errors
                        if "permission denied" in str(e).lower():
                            self._authenticate()
                    else:
                        logger.error(f"Vault operation failed after {self.max_retries} attempts: {e}")
            
            raise VaultClientError(f"Operation failed after {self.max_retries} attempts: {last_exception}")
        
        return wrapper
    
    @_retry_on_failure
    def get_secret(self, path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Retrieve secret from Vault with caching
        
        Args:
            path: Vault secret path (e.g., 'secret/data/smc-trading/database')
            use_cache: Whether to use cached values
            
        Returns:
            Dictionary containing secret data
        """
        # Check cache first
        if use_cache and self._is_cache_valid(path):
            logger.debug(f"Returning cached secret for path: {path}")
            return self._secret_cache[path]
        
        try:
            # Retrieve from Vault
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            secret_data = response['data']['data']
            
            # Cache the result
            self._secret_cache[path] = secret_data
            self._cache_timestamps[path] = datetime.now()
            
            logger.debug(f"Retrieved secret from Vault: {path}")
            return secret_data
            
        except InvalidPath:
            logger.error(f"Secret not found at path: {path}")
            raise VaultClientError(f"Secret not found: {path}")
        except Exception as e:
            logger.error(f"Failed to retrieve secret from {path}: {e}")
            raise VaultClientError(f"Failed to retrieve secret: {e}")
    
    def get_database_config(self) -> Dict[str, str]:
        """Get database configuration from Vault"""
        try:
            secret = self.get_secret('secret/data/smc-trading/database')
            return {
                'DATABASE_URL': secret['url'],
                'DATABASE_PASSWORD': secret['password']
            }
        except Exception as e:
            logger.error(f"Failed to get database config: {e}")
            raise
    
    def get_exchange_config(self, exchange: str) -> Dict[str, str]:
        """Get exchange API configuration from Vault"""
        try:
            secret = self.get_secret(f'secret/data/smc-trading/exchanges/{exchange}')
            
            if exchange == 'binance':
                return {
                    'BINANCE_API_KEY': secret['api_key'],
                    'BINANCE_API_SECRET': secret['api_secret']
                }
            elif exchange == 'bybit':
                return {
                    'BYBIT_API_KEY': secret['api_key'],
                    'BYBIT_API_SECRET': secret['api_secret']
                }
            elif exchange == 'oanda':
                return {
                    'OANDA_API_KEY': secret['api_key'],
                    'OANDA_ACCOUNT_ID': secret['account_id']
                }
            else:
                raise VaultClientError(f"Unsupported exchange: {exchange}")
                
        except Exception as e:
            logger.error(f"Failed to get {exchange} config: {e}")
            raise
    
    def get_jwt_config(self) -> Dict[str, str]:
        """Get JWT configuration from Vault"""
        try:
            secret = self.get_secret('secret/data/smc-trading/jwt')
            return {
                'JWT_SECRET': secret['secret'],
                'ENCRYPTION_KEY': secret['encryption_key']
            }
        except Exception as e:
            logger.error(f"Failed to get JWT config: {e}")
            raise
    
    def get_redis_config(self) -> Dict[str, str]:
        """Get Redis configuration from Vault"""
        try:
            secret = self.get_secret('secret/data/smc-trading/redis')
            return {
                'REDIS_PASSWORD': secret['password']
            }
        except Exception as e:
            logger.error(f"Failed to get Redis config: {e}")
            raise
    
    def get_supabase_config(self) -> Dict[str, str]:
        """Get Supabase configuration from Vault"""
        try:
            secret = self.get_secret('secret/data/smc-trading/supabase')
            return {
                'SUPABASE_URL': secret['url'],
                'SUPABASE_SERVICE_ROLE_KEY': secret['service_role_key'],
                'SUPABASE_ANON_KEY': secret['anon_key']
            }
        except Exception as e:
            logger.error(f"Failed to get Supabase config: {e}")
            raise
    
    @_retry_on_failure
    def encrypt_data(self, plaintext: str, key_name: str = 'smc-trading') -> str:
        """Encrypt data using Vault transit engine"""
        try:
            response = self.client.secrets.transit.encrypt_data(
                name=key_name,
                plaintext=plaintext
            )
            return response['data']['ciphertext']
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise VaultClientError(f"Encryption failed: {e}")
    
    @_retry_on_failure
    def decrypt_data(self, ciphertext: str, key_name: str = 'smc-trading') -> str:
        """Decrypt data using Vault transit engine"""
        try:
            response = self.client.secrets.transit.decrypt_data(
                name=key_name,
                ciphertext=ciphertext
            )
            return response['data']['plaintext']
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise VaultClientError(f"Decryption failed: {e}")
    
    def invalidate_cache(self, path: str = None):
        """Invalidate secret cache"""
        if path:
            self._secret_cache.pop(path, None)
            self._cache_timestamps.pop(path, None)
            logger.debug(f"Invalidated cache for path: {path}")
        else:
            self._secret_cache.clear()
            self._cache_timestamps.clear()
            logger.debug("Invalidated entire secret cache")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Vault health and authentication status"""
        try:
            health = self.client.sys.read_health_status()
            authenticated = self.client.is_authenticated()
            
            return {
                'vault_url': self.vault_url,
                'authenticated': authenticated,
                'sealed': health.get('sealed', True),
                'standby': health.get('standby', True),
                'cache_size': len(self._secret_cache),
                'last_auth_method': 'kubernetes' if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token') else 'token'
            }
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return {
                'vault_url': self.vault_url,
                'authenticated': False,
                'error': str(e)
            }
    
    def close(self):
        """Clean shutdown of Vault client"""
        self._stop_renewal.set()
        if self._token_renewal_thread and self._token_renewal_thread.is_alive():
            self._token_renewal_thread.join(timeout=5)
        
        self.invalidate_cache()
        logger.info("Vault client closed")


# Global Vault client instance
_vault_client: Optional[VaultClient] = None


def get_vault_client() -> VaultClient:
    """Get or create global Vault client instance"""
    global _vault_client
    
    if _vault_client is None:
        _vault_client = VaultClient()
    
    return _vault_client


def get_secret_from_vault(path: str) -> Dict[str, Any]:
    """Convenience function to get secret from Vault"""
    client = get_vault_client()
    return client.get_secret(path)


def get_config_value(key: str, default: Any = None, vault_path: str = None) -> Any:
    """
    Get configuration value with Vault fallback
    
    Priority:
    1. Environment variable
    2. Vault secret (if vault_path provided)
    3. Default value
    """
    # Try environment variable first
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value
    
    # Try Vault if path provided
    if vault_path:
        try:
            client = get_vault_client()
            secret = client.get_secret(vault_path)
            return secret.get(key.lower(), default)
        except Exception as e:
            logger.warning(f"Failed to get {key} from Vault: {e}")
    
    return default


# Configuration helpers using Vault
def get_database_url() -> str:
    """Get database URL from Vault or environment"""
    try:
        client = get_vault_client()
        config = client.get_database_config()
        return config['DATABASE_URL']
    except Exception:
        return os.getenv('DATABASE_URL', 'postgresql://localhost:5432/smc_trading_agent')


def get_exchange_credentials(exchange: str) -> Dict[str, str]:
    """Get exchange credentials from Vault or environment"""
    try:
        client = get_vault_client()
        return client.get_exchange_config(exchange)
    except Exception as e:
        logger.warning(f"Failed to get {exchange} credentials from Vault: {e}")
        
        # Fallback to environment variables
        if exchange == 'binance':
            return {
                'BINANCE_API_KEY': os.getenv('BINANCE_API_KEY', ''),
                'BINANCE_API_SECRET': os.getenv('BINANCE_API_SECRET', '')
            }
        elif exchange == 'bybit':
            return {
                'BYBIT_API_KEY': os.getenv('BYBIT_API_KEY', ''),
                'BYBIT_API_SECRET': os.getenv('BYBIT_API_SECRET', '')
            }
        elif exchange == 'oanda':
            return {
                'OANDA_API_KEY': os.getenv('OANDA_API_KEY', ''),
                'OANDA_ACCOUNT_ID': os.getenv('OANDA_ACCOUNT_ID', '')
            }
        
        return {}


def get_jwt_secret() -> str:
    """Get JWT secret from Vault or environment"""
    try:
        client = get_vault_client()
        config = client.get_jwt_config()
        return config['JWT_SECRET']
    except Exception:
        return os.getenv('JWT_SECRET', 'fallback-secret-change-in-production')


def get_encryption_key() -> str:
    """Get encryption key from Vault or environment"""
    try:
        client = get_vault_client()
        config = client.get_jwt_config()
        return config['ENCRYPTION_KEY']
    except Exception:
        return os.getenv('ENCRYPTION_KEY', 'fallback-key-change-in-production')


# Cleanup on module exit
import atexit

def cleanup_vault_client():
    global _vault_client
    if _vault_client:
        _vault_client.close()

atexit.register(cleanup_vault_client)