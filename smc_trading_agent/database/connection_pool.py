"""
Database connection pool management with PgBouncer integration.
Provides optimized connection pooling for different workload types.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, AsyncContextManager
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

import asyncpg
import psycopg2
from psycopg2 import pool
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

from prometheus_client import Counter, Histogram, Gauge


class PoolType(Enum):
    """Database pool types for different workloads."""
    MAIN = "main"           # Main application OLTP workload
    READ_ONLY = "read_only" # Read-only queries and analytics
    HFT = "hft"            # High-frequency trading data
    JOBS = "jobs"          # Background jobs and data processing


@dataclass
class PoolConfig:
    """Configuration for database connection pools."""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    pool_pre_ping: bool = True


class DatabaseMetrics:
    """Prometheus metrics for database connections."""
    
    def __init__(self):
        self.connection_requests = Counter(
            'db_connection_requests_total',
            'Total database connection requests',
            ['pool_type', 'status']
        )
        
        self.connection_duration = Histogram(
            'db_connection_duration_seconds',
            'Time spent acquiring database connections',
            ['pool_type']
        )
        
        self.active_connections = Gauge(
            'db_active_connections',
            'Number of active database connections',
            ['pool_type']
        )
        
        self.pool_size = Gauge(
            'db_pool_size',
            'Database connection pool size',
            ['pool_type']
        )
        
        self.query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query execution time',
            ['pool_type', 'query_type']
        )


class ConnectionPoolManager:
    """
    Manages multiple database connection pools for different workload types.
    Integrates with PgBouncer for optimal connection management.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics = DatabaseMetrics()
        
        # Connection pools
        self._async_engines: Dict[PoolType, Any] = {}
        self._sync_engines: Dict[PoolType, Any] = {}
        self._async_session_makers: Dict[PoolType, Any] = {}
        self._sync_session_makers: Dict[PoolType, Any] = {}
        
        # Pool configurations
        self._pool_configs = self._create_pool_configs()
        
        # Health check status
        self._health_status: Dict[PoolType, bool] = {}
        
    def _create_pool_configs(self) -> Dict[PoolType, PoolConfig]:
        """Create pool configurations for different workload types."""
        base_config = self.config.get('database', {})
        
        # PgBouncer connection details
        pgbouncer_host = base_config.get('pgbouncer_host', 'pgbouncer')
        pgbouncer_port = base_config.get('pgbouncer_port', 6432)
        
        configs = {
            PoolType.MAIN: PoolConfig(
                host=pgbouncer_host,
                port=pgbouncer_port,
                database='smc_trading_agent',
                username=base_config.get('username', 'smc_app_user'),
                password=base_config.get('password', ''),
                pool_size=20,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
            ),
            PoolType.READ_ONLY: PoolConfig(
                host=pgbouncer_host,
                port=pgbouncer_port,
                database='smc_trading_agent_read',
                username=base_config.get('read_username', 'smc_read_user'),
                password=base_config.get('read_password', ''),
                pool_size=15,
                max_overflow=5,
                pool_timeout=30,
                pool_recycle=3600,
            ),
            PoolType.HFT: PoolConfig(
                host=pgbouncer_host,
                port=pgbouncer_port,
                database='smc_trading_hft',
                username=base_config.get('username', 'smc_app_user'),
                password=base_config.get('password', ''),
                pool_size=30,
                max_overflow=20,
                pool_timeout=10,
                pool_recycle=1800,
            ),
            PoolType.JOBS: PoolConfig(
                host=pgbouncer_host,
                port=pgbouncer_port,
                database='smc_trading_jobs',
                username=base_config.get('username', 'smc_app_user'),
                password=base_config.get('password', ''),
                pool_size=10,
                max_overflow=5,
                pool_timeout=60,
                pool_recycle=7200,
            ),
        }
        
        return configs
    
    async def initialize(self):
        """Initialize all connection pools."""
        self.logger.info("Initializing database connection pools...")
        
        for pool_type in PoolType:
            try:
                await self._create_pool(pool_type)
                self._health_status[pool_type] = True
                self.logger.info(f"Initialized {pool_type.value} pool successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize {pool_type.value} pool: {e}")
                self._health_status[pool_type] = False
                raise
        
        # Start health monitoring
        asyncio.create_task(self._health_monitor())
        
        self.logger.info("All database connection pools initialized successfully")
    
    async def _create_pool(self, pool_type: PoolType):
        """Create async and sync connection pools for a specific type."""
        config = self._pool_configs[pool_type]
        
        # Create connection URLs
        async_url = (
            f"postgresql+asyncpg://{config.username}:{config.password}@"
            f"{config.host}:{config.port}/{config.database}"
        )
        
        sync_url = (
            f"postgresql+psycopg2://{config.username}:{config.password}@"
            f"{config.host}:{config.port}/{config.database}"
        )
        
        # Create async engine
        self._async_engines[pool_type] = create_async_engine(
            async_url,
            poolclass=QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=config.pool_pre_ping,
            echo=self.config.get('database', {}).get('echo', False),
        )
        
        # Create sync engine
        self._sync_engines[pool_type] = create_engine(
            sync_url,
            poolclass=QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=config.pool_pre_ping,
            echo=self.config.get('database', {}).get('echo', False),
        )
        
        # Create session makers
        self._async_session_makers[pool_type] = async_sessionmaker(
            self._async_engines[pool_type],
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self._sync_session_makers[pool_type] = sessionmaker(
            self._sync_engines[pool_type],
            expire_on_commit=False
        )
        
        # Update metrics
        self.metrics.pool_size.labels(pool_type=pool_type.value).set(config.pool_size)
    
    @asynccontextmanager
    async def get_async_session(self, pool_type: PoolType = PoolType.MAIN) -> AsyncContextManager[AsyncSession]:
        """Get an async database session with automatic cleanup."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.metrics.connection_requests.labels(
                pool_type=pool_type.value, 
                status='requested'
            ).inc()
            
            session_maker = self._async_session_makers.get(pool_type)
            if not session_maker:
                raise ValueError(f"Pool {pool_type.value} not initialized")
            
            async with session_maker() as session:
                self.metrics.connection_requests.labels(
                    pool_type=pool_type.value, 
                    status='acquired'
                ).inc()
                
                self.metrics.active_connections.labels(
                    pool_type=pool_type.value
                ).inc()
                
                yield session
                
        except Exception as e:
            self.metrics.connection_requests.labels(
                pool_type=pool_type.value, 
                status='failed'
            ).inc()
            self.logger.error(f"Database session error for {pool_type.value}: {e}")
            raise
        finally:
            duration = asyncio.get_event_loop().time() - start_time
            self.metrics.connection_duration.labels(
                pool_type=pool_type.value
            ).observe(duration)
            
            self.metrics.active_connections.labels(
                pool_type=pool_type.value
            ).dec()
    
    @asynccontextmanager
    async def get_sync_session(self, pool_type: PoolType = PoolType.MAIN):
        """Get a sync database session with automatic cleanup."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.metrics.connection_requests.labels(
                pool_type=pool_type.value, 
                status='requested'
            ).inc()
            
            session_maker = self._sync_session_makers.get(pool_type)
            if not session_maker:
                raise ValueError(f"Pool {pool_type.value} not initialized")
            
            with session_maker() as session:
                self.metrics.connection_requests.labels(
                    pool_type=pool_type.value, 
                    status='acquired'
                ).inc()
                
                self.metrics.active_connections.labels(
                    pool_type=pool_type.value
                ).inc()
                
                yield session
                
        except Exception as e:
            self.metrics.connection_requests.labels(
                pool_type=pool_type.value, 
                status='failed'
            ).inc()
            self.logger.error(f"Database session error for {pool_type.value}: {e}")
            raise
        finally:
            duration = asyncio.get_event_loop().time() - start_time
            self.metrics.connection_duration.labels(
                pool_type=pool_type.value
            ).observe(duration)
            
            self.metrics.active_connections.labels(
                pool_type=pool_type.value
            ).dec()
    
    async def execute_query(self, query: str, params: Optional[Dict] = None, 
                          pool_type: PoolType = PoolType.MAIN, query_type: str = "select"):
        """Execute a query with metrics tracking."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.get_async_session(pool_type) as session:
                result = await session.execute(text(query), params or {})
                await session.commit()
                return result
        finally:
            duration = asyncio.get_event_loop().time() - start_time
            self.metrics.query_duration.labels(
                pool_type=pool_type.value,
                query_type=query_type
            ).observe(duration)
    
    async def health_check(self, pool_type: Optional[PoolType] = None) -> Dict[str, Any]:
        """Perform health check on connection pools."""
        if pool_type:
            pools_to_check = [pool_type]
        else:
            pools_to_check = list(PoolType)
        
        health_status = {}
        
        for pool in pools_to_check:
            try:
                async with self.get_async_session(pool) as session:
                    await session.execute(text("SELECT 1"))
                    health_status[pool.value] = {
                        "status": "healthy",
                        "pool_size": self._pool_configs[pool].pool_size,
                        "active_connections": self._get_active_connections(pool)
                    }
            except Exception as e:
                health_status[pool.value] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                self._health_status[pool] = False
        
        return health_status
    
    def _get_active_connections(self, pool_type: PoolType) -> int:
        """Get the number of active connections for a pool."""
        engine = self._async_engines.get(pool_type)
        if engine and hasattr(engine.pool, 'size'):
            return engine.pool.size()
        return 0
    
    async def _health_monitor(self):
        """Background task to monitor pool health."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for pool_type in PoolType:
                    try:
                        async with self.get_async_session(pool_type) as session:
                            await session.execute(text("SELECT 1"))
                        
                        if not self._health_status.get(pool_type, False):
                            self.logger.info(f"Pool {pool_type.value} recovered")
                            self._health_status[pool_type] = True
                            
                    except Exception as e:
                        if self._health_status.get(pool_type, True):
                            self.logger.error(f"Pool {pool_type.value} health check failed: {e}")
                            self._health_status[pool_type] = False
                            
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
    
    async def close(self):
        """Close all connection pools."""
        self.logger.info("Closing database connection pools...")
        
        for pool_type, engine in self._async_engines.items():
            try:
                await engine.dispose()
                self.logger.info(f"Closed async engine for {pool_type.value}")
            except Exception as e:
                self.logger.error(f"Error closing async engine for {pool_type.value}: {e}")
        
        for pool_type, engine in self._sync_engines.items():
            try:
                engine.dispose()
                self.logger.info(f"Closed sync engine for {pool_type.value}")
            except Exception as e:
                self.logger.error(f"Error closing sync engine for {pool_type.value}: {e}")
        
        self.logger.info("All database connection pools closed")


# Global connection pool manager instance
_pool_manager: Optional[ConnectionPoolManager] = None


async def get_pool_manager() -> ConnectionPoolManager:
    """Get the global connection pool manager instance."""
    global _pool_manager
    if _pool_manager is None:
        raise RuntimeError("Connection pool manager not initialized")
    return _pool_manager


async def initialize_pools(config: Dict[str, Any]) -> ConnectionPoolManager:
    """Initialize the global connection pool manager."""
    global _pool_manager
    _pool_manager = ConnectionPoolManager(config)
    await _pool_manager.initialize()
    return _pool_manager


async def close_pools():
    """Close the global connection pool manager."""
    global _pool_manager
    if _pool_manager:
        await _pool_manager.close()
        _pool_manager = None