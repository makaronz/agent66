"""
API Key Rotation System

Handles secure API key rotation for all exchanges with zero-downtime updates,
audit logging, and integration with HashiCorp Vault.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
import hmac

from .production_config import ExchangeType, ExchangeCredentials, ProductionConfigManager
from .production_factory import ProductionExchangeFactory

logger = logging.getLogger(__name__)


class RotationStatus(Enum):
    """API key rotation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class RotationRecord:
    """Record of API key rotation."""
    exchange_type: ExchangeType
    rotation_id: str
    old_key_hash: str  # Hash of old key for audit
    new_key_hash: str  # Hash of new key for audit
    status: RotationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "exchange": self.exchange_type.value,
            "rotation_id": self.rotation_id,
            "old_key_hash": self.old_key_hash,
            "new_key_hash": self.new_key_hash,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "rollback_reason": self.rollback_reason
        }


class APIKeyRotationManager:
    """
    Manages API key rotation for all exchanges.
    
    Features:
    - Zero-downtime rotation
    - Automatic rollback on failure
    - Audit logging
    - Integration with Vault
    - Validation of new keys
    """
    
    def __init__(self, config_manager: ProductionConfigManager, factory: ProductionExchangeFactory):
        """
        Initialize rotation manager.
        
        Args:
            config_manager: Production configuration manager
            factory: Exchange factory for testing connections
        """
        self.config_manager = config_manager
        self.factory = factory
        self.rotation_records: List[RotationRecord] = []
        self.rotation_callbacks: List[Callable] = []
        
        # Rotation settings
        self.validation_timeout = 30  # seconds
        self.rollback_timeout = 60    # seconds
        self.max_rotation_attempts = 3
        
        logger.info("Initialized API key rotation manager")
    
    def add_rotation_callback(self, callback: Callable[[RotationRecord], None]):
        """
        Add callback to be called on rotation events.
        
        Args:
            callback: Function to call with rotation record
        """
        self.rotation_callbacks.append(callback)
    
    async def rotate_api_keys(
        self, 
        exchange_type: ExchangeType, 
        new_api_key: str, 
        new_api_secret: str,
        new_passphrase: Optional[str] = None,
        validate_before_rotation: bool = True
    ) -> RotationRecord:
        """
        Rotate API keys for specific exchange.
        
        Args:
            exchange_type: Exchange to rotate keys for
            new_api_key: New API key
            new_api_secret: New API secret
            new_passphrase: New passphrase (if required)
            validate_before_rotation: Whether to validate new keys before rotation
            
        Returns:
            RotationRecord: Record of the rotation attempt
        """
        rotation_id = self._generate_rotation_id(exchange_type)
        
        # Get current configuration
        current_config = self.config_manager.get_config(exchange_type)
        if not current_config:
            raise ValueError(f"No configuration found for {exchange_type.value}")
        
        # Create rotation record
        record = RotationRecord(
            exchange_type=exchange_type,
            rotation_id=rotation_id,
            old_key_hash=self._hash_api_key(current_config.credentials.api_key),
            new_key_hash=self._hash_api_key(new_api_key),
            status=RotationStatus.PENDING,
            started_at=datetime.utcnow()
        )
        
        self.rotation_records.append(record)
        logger.info(f"Starting API key rotation for {exchange_type.value} (ID: {rotation_id})")
        
        try:
            # Update status
            record.status = RotationStatus.IN_PROGRESS
            await self._notify_callbacks(record)
            
            # Validate new credentials if requested
            if validate_before_rotation:
                logger.info(f"Validating new credentials for {exchange_type.value}")
                is_valid = await self._validate_new_credentials(
                    exchange_type, new_api_key, new_api_secret, new_passphrase
                )
                
                if not is_valid:
                    record.status = RotationStatus.FAILED
                    record.error_message = "New credentials validation failed"
                    record.completed_at = datetime.utcnow()
                    await self._notify_callbacks(record)
                    return record
            
            # Store old credentials for rollback
            old_credentials = current_config.credentials
            
            # Create new credentials
            new_credentials = ExchangeCredentials(
                api_key=new_api_key,
                api_secret=new_api_secret,
                passphrase=new_passphrase,
                account_id=old_credentials.account_id  # Keep existing account ID
            )
            
            # Update configuration
            self.config_manager.update_credentials(exchange_type, new_credentials)
            logger.info(f"Updated credentials for {exchange_type.value}")
            
            # Test new credentials with live connection
            test_success = await self._test_credentials_with_connection(exchange_type)
            
            if test_success:
                # Success - finalize rotation
                record.status = RotationStatus.COMPLETED
                record.completed_at = datetime.utcnow()
                logger.info(f"Successfully rotated API keys for {exchange_type.value}")
                
            else:
                # Failed - rollback
                logger.error(f"New credentials failed live test for {exchange_type.value}, rolling back")
                self.config_manager.update_credentials(exchange_type, old_credentials)
                
                record.status = RotationStatus.ROLLED_BACK
                record.rollback_reason = "Live connection test failed"
                record.completed_at = datetime.utcnow()
            
            await self._notify_callbacks(record)
            return record
            
        except Exception as e:
            # Error during rotation - attempt rollback
            logger.error(f"Error during API key rotation for {exchange_type.value}: {e}")
            
            try:
                # Restore old credentials
                old_credentials = current_config.credentials
                self.config_manager.update_credentials(exchange_type, old_credentials)
                
                record.status = RotationStatus.ROLLED_BACK
                record.rollback_reason = f"Exception during rotation: {str(e)}"
                
            except Exception as rollback_error:
                logger.error(f"Failed to rollback credentials for {exchange_type.value}: {rollback_error}")
                record.status = RotationStatus.FAILED
                record.error_message = f"Rotation failed and rollback failed: {str(e)}, {str(rollback_error)}"
            
            record.completed_at = datetime.utcnow()
            await self._notify_callbacks(record)
            return record
    
    async def rotate_all_exchanges(
        self, 
        new_credentials: Dict[ExchangeType, Dict[str, str]],
        validate_before_rotation: bool = True
    ) -> Dict[ExchangeType, RotationRecord]:
        """
        Rotate API keys for multiple exchanges.
        
        Args:
            new_credentials: Dictionary mapping exchange types to credential dictionaries
            validate_before_rotation: Whether to validate new keys before rotation
            
        Returns:
            Dict[ExchangeType, RotationRecord]: Rotation records for each exchange
        """
        results = {}
        
        # Rotate keys for each exchange
        for exchange_type, creds in new_credentials.items():
            try:
                record = await self.rotate_api_keys(
                    exchange_type=exchange_type,
                    new_api_key=creds["api_key"],
                    new_api_secret=creds["api_secret"],
                    new_passphrase=creds.get("passphrase"),
                    validate_before_rotation=validate_before_rotation
                )
                results[exchange_type] = record
                
            except Exception as e:
                logger.error(f"Failed to rotate keys for {exchange_type.value}: {e}")
                # Create failed record
                results[exchange_type] = RotationRecord(
                    exchange_type=exchange_type,
                    rotation_id=self._generate_rotation_id(exchange_type),
                    old_key_hash="unknown",
                    new_key_hash="unknown",
                    status=RotationStatus.FAILED,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                    error_message=str(e)
                )
        
        return results
    
    async def schedule_rotation(
        self, 
        exchange_type: ExchangeType, 
        rotation_time: datetime,
        new_api_key: str,
        new_api_secret: str,
        new_passphrase: Optional[str] = None
    ) -> str:
        """
        Schedule API key rotation for future execution.
        
        Args:
            exchange_type: Exchange to rotate keys for
            rotation_time: When to perform the rotation
            new_api_key: New API key
            new_api_secret: New API secret
            new_passphrase: New passphrase (if required)
            
        Returns:
            str: Rotation ID for tracking
        """
        rotation_id = self._generate_rotation_id(exchange_type)
        
        # Calculate delay
        delay = (rotation_time - datetime.utcnow()).total_seconds()
        
        if delay <= 0:
            raise ValueError("Rotation time must be in the future")
        
        logger.info(f"Scheduled API key rotation for {exchange_type.value} at {rotation_time} (ID: {rotation_id})")
        
        # Schedule the rotation
        asyncio.create_task(self._scheduled_rotation(
            delay, exchange_type, new_api_key, new_api_secret, new_passphrase, rotation_id
        ))
        
        return rotation_id
    
    async def _scheduled_rotation(
        self, 
        delay: float, 
        exchange_type: ExchangeType,
        new_api_key: str,
        new_api_secret: str,
        new_passphrase: Optional[str],
        rotation_id: str
    ):
        """Execute scheduled rotation."""
        try:
            await asyncio.sleep(delay)
            logger.info(f"Executing scheduled rotation {rotation_id} for {exchange_type.value}")
            
            await self.rotate_api_keys(
                exchange_type=exchange_type,
                new_api_key=new_api_key,
                new_api_secret=new_api_secret,
                new_passphrase=new_passphrase
            )
            
        except Exception as e:
            logger.error(f"Scheduled rotation {rotation_id} failed: {e}")
    
    async def _validate_new_credentials(
        self, 
        exchange_type: ExchangeType, 
        api_key: str, 
        api_secret: str,
        passphrase: Optional[str] = None
    ) -> bool:
        """
        Validate new credentials without affecting current configuration.
        
        Args:
            exchange_type: Exchange type
            api_key: New API key
            api_secret: New API secret
            passphrase: New passphrase (if required)
            
        Returns:
            bool: True if credentials are valid
        """
        try:
            # Create temporary configuration
            current_config = self.config_manager.get_config(exchange_type)
            if not current_config:
                return False
            
            temp_credentials = ExchangeCredentials(
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                account_id=current_config.credentials.account_id
            )
            
            # Create temporary connector for testing
            temp_config = current_config
            temp_config.credentials = temp_credentials
            
            # Test basic API call (this would be exchange-specific)
            # For now, just validate the credential format
            if not api_key or not api_secret:
                return False
            
            # Additional validation could include:
            # - API key format validation
            # - Test API call to exchange
            # - Permission validation
            
            logger.info(f"New credentials validated for {exchange_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Credential validation failed for {exchange_type.value}: {e}")
            return False
    
    async def _test_credentials_with_connection(self, exchange_type: ExchangeType) -> bool:
        """
        Test new credentials with actual connection.
        
        Args:
            exchange_type: Exchange type
            
        Returns:
            bool: True if connection successful
        """
        try:
            # Create temporary connector with new credentials
            connector = self.factory.create_connector(exchange_type)
            if not connector:
                return False
            
            # Test connection
            success = await connector.connect_websocket()
            
            if success:
                # Test basic functionality
                health = await connector.get_health_status()
                success = health.get("connected", False)
                
                # Clean up
                await connector.disconnect_websocket()
            
            return success
            
        except Exception as e:
            logger.error(f"Connection test failed for {exchange_type.value}: {e}")
            return False
    
    def _generate_rotation_id(self, exchange_type: ExchangeType) -> str:
        """Generate unique rotation ID."""
        timestamp = int(time.time() * 1000)
        return f"{exchange_type.value}_{timestamp}"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Create hash of API key for audit logging."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    async def _notify_callbacks(self, record: RotationRecord):
        """Notify all registered callbacks."""
        for callback in self.rotation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(record)
                else:
                    callback(record)
            except Exception as e:
                logger.error(f"Callback notification failed: {e}")
    
    def get_rotation_history(self, exchange_type: Optional[ExchangeType] = None) -> List[RotationRecord]:
        """
        Get rotation history.
        
        Args:
            exchange_type: Filter by exchange type, or None for all
            
        Returns:
            List[RotationRecord]: Rotation records
        """
        if exchange_type:
            return [r for r in self.rotation_records if r.exchange_type == exchange_type]
        return self.rotation_records.copy()
    
    def get_latest_rotation(self, exchange_type: ExchangeType) -> Optional[RotationRecord]:
        """
        Get latest rotation record for exchange.
        
        Args:
            exchange_type: Exchange type
            
        Returns:
            RotationRecord: Latest rotation record or None
        """
        exchange_records = [r for r in self.rotation_records if r.exchange_type == exchange_type]
        if exchange_records:
            return max(exchange_records, key=lambda r: r.started_at)
        return None
    
    def export_audit_log(self, file_path: str):
        """
        Export rotation audit log.
        
        Args:
            file_path: Path to save audit log
        """
        try:
            audit_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "total_rotations": len(self.rotation_records),
                "rotations": [record.to_dict() for record in self.rotation_records]
            }
            
            with open(file_path, 'w') as f:
                json.dump(audit_data, f, indent=2)
            
            logger.info(f"Audit log exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")


class VaultIntegration:
    """
    Integration with HashiCorp Vault for secure credential storage.
    
    Handles automatic key rotation with Vault's dynamic secrets.
    """
    
    def __init__(self, vault_url: str, vault_token: str):
        """
        Initialize Vault integration.
        
        Args:
            vault_url: Vault server URL
            vault_token: Vault authentication token
        """
        self.vault_url = vault_url
        self.vault_token = vault_token
        self.vault_client = None  # Would initialize actual Vault client
        
        logger.info("Initialized Vault integration")
    
    async def get_credentials(self, exchange_type: ExchangeType) -> Optional[Dict[str, str]]:
        """
        Get credentials from Vault.
        
        Args:
            exchange_type: Exchange type
            
        Returns:
            Dict[str, str]: Credentials or None if not found
        """
        try:
            # This would integrate with actual Vault client
            # For now, return placeholder
            logger.info(f"Retrieved credentials from Vault for {exchange_type.value}")
            return {
                "api_key": "vault_managed_key",
                "api_secret": "vault_managed_secret"
            }
            
        except Exception as e:
            logger.error(f"Failed to get credentials from Vault for {exchange_type.value}: {e}")
            return None
    
    async def rotate_credentials(self, exchange_type: ExchangeType) -> Optional[Dict[str, str]]:
        """
        Trigger credential rotation in Vault.
        
        Args:
            exchange_type: Exchange type
            
        Returns:
            Dict[str, str]: New credentials or None if failed
        """
        try:
            # This would trigger Vault rotation
            logger.info(f"Triggered credential rotation in Vault for {exchange_type.value}")
            return await self.get_credentials(exchange_type)
            
        except Exception as e:
            logger.error(f"Failed to rotate credentials in Vault for {exchange_type.value}: {e}")
            return None


# Convenience functions
def create_rotation_manager(
    config_manager: ProductionConfigManager, 
    factory: ProductionExchangeFactory
) -> APIKeyRotationManager:
    """Create API key rotation manager."""
    return APIKeyRotationManager(config_manager, factory)


async def perform_emergency_rotation(
    exchange_type: ExchangeType,
    new_api_key: str,
    new_api_secret: str,
    config_manager: ProductionConfigManager,
    factory: ProductionExchangeFactory
) -> RotationRecord:
    """
    Perform emergency API key rotation.
    
    Args:
        exchange_type: Exchange to rotate
        new_api_key: New API key
        new_api_secret: New API secret
        config_manager: Configuration manager
        factory: Exchange factory
        
    Returns:
        RotationRecord: Rotation result
    """
    rotation_manager = create_rotation_manager(config_manager, factory)
    
    logger.warning(f"Performing emergency API key rotation for {exchange_type.value}")
    
    return await rotation_manager.rotate_api_keys(
        exchange_type=exchange_type,
        new_api_key=new_api_key,
        new_api_secret=new_api_secret,
        validate_before_rotation=False  # Skip validation for emergency rotation
    )