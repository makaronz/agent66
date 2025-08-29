"""
Database replica routing for read/write splitting.
Automatically routes read queries to replicas and write queries to primary.
"""

import asyncio
import logging
import random
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection_pool import ConnectionPoolManager, PoolType
from prometheus_client import Counter, Histogram, Gauge


class QueryIntent(Enum):
    """Intent of database query for routing decisions."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class ReplicaStatus:
    """Status information for a database replica."""
    host: str
    port: int
    is_healthy: bool
    lag_seconds: float
    last_check: float
    connection_count: int
    load_score: float


class ReplicaRouter:
    """
    Intelligent database replica router with automatic failover.
    Routes read queries to healthy replicas and write queries to primary.
    """
    
    def __init__(self, pool_manager: ConnectionPoolManager, config: Dict[str, Any]):
        self.pool_manager = pool_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.max_replica_lag = config.get('database', {}).get('max_replica_lag', 10.0)  # seconds
        self.health_check_interval = config.get('database', {}).get('replica_health_check_interval', 30)
        self.failover_threshold = config.get('database', {}).get('failover_threshold', 3)
        
        # Replica status tracking
        self.replica_status: Dict[str, ReplicaStatus] = {}
        self.primary_status: Optional[ReplicaStatus] = None
        
        # Routing statistics
        self.routing_stats = {
            'primary_queries': 0,
            'replica_queries': 0,
            'failover_events': 0,
            'routing_errors': 0
        }
        
        # Metrics
        self._setup_metrics()
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _setup_metrics(self):
        """Setup Prometheus metrics for replica routing."""
        self.metrics = {
            'query_routing_total': Counter(
                'db_query_routing_total',
                'Total queries routed by intent',
                ['intent', 'target', 'status']
            ),
            'replica_health_status': Gauge(
                'db_replica_health_status',
                'Replica health status (1=healthy, 0=unhealthy)',
                ['replica_host']
            ),
            'replica_lag_seconds': Gauge(
                'db_replica_lag_seconds',
                'Replica lag in seconds',
                ['replica_host']
            ),
            'replica_connection_count': Gauge(
                'db_replica_connection_count',
                'Number of active connections to replica',
                ['replica_host']
            ),
            'routing_decision_duration': Histogram(
                'db_routing_decision_duration_seconds',
                'Time spent making routing decisions',
                ['intent']
            ),
            'failover_events_total': Counter(
                'db_failover_events_total',
                'Total database failover events',
                ['from_target', 'to_target', 'reason']
            )
        }
    
    async def start_monitoring(self):
        """Start background health monitoring."""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Starting replica router monitoring")
        
        # Initialize replica status
        await self._initialize_replica_status()
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop_monitoring(self):
        """Stop background monitoring."""
        if not self._running:
            return
        
        self._running = False
        self.logger.info("Stopping replica router monitoring")
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
    
    async def _initialize_replica_status(self):
        """Initialize replica status tracking."""
        # This would typically discover replicas from Patroni or configuration
        replica_configs = self.config.get('database', {}).get('replicas', [])
        
        for replica_config in replica_configs:
            host = replica_config.get('host', 'postgresql-replica')
            port = replica_config.get('port', 5432)
            replica_key = f"{host}:{port}"
            
            self.replica_status[replica_key] = ReplicaStatus(
                host=host,
                port=port,
                is_healthy=False,
                lag_seconds=0.0,
                last_check=0.0,
                connection_count=0,
                load_score=0.0
            )
        
        # Initialize primary status
        primary_config = self.config.get('database', {})
        primary_host = primary_config.get('primary_host', 'postgresql-primary')
        primary_port = primary_config.get('primary_port', 5432)
        
        self.primary_status = ReplicaStatus(
            host=primary_host,
            port=primary_port,
            is_healthy=False,
            lag_seconds=0.0,
            last_check=0.0,
            connection_count=0,
            load_score=0.0
        )
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while self._running:
            try:
                await self._check_all_replicas()
                await self._check_primary()
                await self._update_metrics()
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}", exc_info=True)
            
            await asyncio.sleep(self.health_check_interval)
    
    async def _check_all_replicas(self):
        """Check health of all replicas."""
        check_tasks = []
        
        for replica_key, status in self.replica_status.items():
            task = asyncio.create_task(self._check_replica_health(replica_key, status))
            check_tasks.append(task)
        
        if check_tasks:
            await asyncio.gather(*check_tasks, return_exceptions=True)
    
    async def _check_replica_health(self, replica_key: str, status: ReplicaStatus):
        """Check health of a specific replica."""
        try:
            async with self.pool_manager.get_async_session(PoolType.READ_ONLY) as session:
                # Check if replica is accessible
                await session.execute(text("SELECT 1"))
                
                # Check replication lag
                lag_result = await session.execute(text("""
                    SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::float as lag
                """))
                
                lag_row = lag_result.fetchone()
                lag_seconds = lag_row.lag if lag_row and lag_row.lag else 0.0
                
                # Check connection count
                conn_result = await session.execute(text("""
                    SELECT count(*) as conn_count 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                
                conn_row = conn_result.fetchone()
                connection_count = conn_row.conn_count if conn_row else 0
                
                # Update status
                status.is_healthy = lag_seconds <= self.max_replica_lag
                status.lag_seconds = lag_seconds
                status.last_check = asyncio.get_event_loop().time()
                status.connection_count = connection_count
                status.load_score = self._calculate_load_score(status)
                
                if status.is_healthy:
                    self.logger.debug(f"Replica {replica_key} is healthy (lag: {lag_seconds:.2f}s)")
                else:
                    self.logger.warning(f"Replica {replica_key} is unhealthy (lag: {lag_seconds:.2f}s)")
                
        except Exception as e:
            status.is_healthy = False
            status.last_check = asyncio.get_event_loop().time()
            self.logger.error(f"Health check failed for replica {replica_key}: {e}")
    
    async def _check_primary(self):
        """Check health of primary database."""
        if not self.primary_status:
            return
        
        try:
            async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                # Check if primary is accessible
                await session.execute(text("SELECT 1"))
                
                # Check connection count
                conn_result = await session.execute(text("""
                    SELECT count(*) as conn_count 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                
                conn_row = conn_result.fetchone()
                connection_count = conn_row.conn_count if conn_row else 0
                
                # Update status
                self.primary_status.is_healthy = True
                self.primary_status.last_check = asyncio.get_event_loop().time()
                self.primary_status.connection_count = connection_count
                self.primary_status.load_score = self._calculate_load_score(self.primary_status)
                
                self.logger.debug("Primary database is healthy")
                
        except Exception as e:
            self.primary_status.is_healthy = False
            self.primary_status.last_check = asyncio.get_event_loop().time()
            self.logger.error(f"Primary health check failed: {e}")
    
    def _calculate_load_score(self, status: ReplicaStatus) -> float:
        """Calculate load score for replica selection."""
        # Simple load scoring based on connection count and lag
        base_score = 1.0
        
        # Penalize high connection count
        connection_penalty = status.connection_count * 0.01
        
        # Penalize high lag
        lag_penalty = status.lag_seconds * 0.1
        
        return max(0.1, base_score - connection_penalty - lag_penalty)
    
    def _update_metrics(self):
        """Update Prometheus metrics."""
        # Update replica metrics
        for replica_key, status in self.replica_status.items():
            self.metrics['replica_health_status'].labels(
                replica_host=replica_key
            ).set(1 if status.is_healthy else 0)
            
            self.metrics['replica_lag_seconds'].labels(
                replica_host=replica_key
            ).set(status.lag_seconds)
            
            self.metrics['replica_connection_count'].labels(
                replica_host=replica_key
            ).set(status.connection_count)
        
        # Update primary metrics
        if self.primary_status:
            self.metrics['replica_health_status'].labels(
                replica_host=f"{self.primary_status.host}:{self.primary_status.port}"
            ).set(1 if self.primary_status.is_healthy else 0)
            
            self.metrics['replica_connection_count'].labels(
                replica_host=f"{self.primary_status.host}:{self.primary_status.port}"
            ).set(self.primary_status.connection_count)
    
    def _detect_query_intent(self, query: str) -> QueryIntent:
        """Detect the intent of a SQL query."""
        query_lower = query.lower().strip()
        
        # Write operations
        if any(query_lower.startswith(op) for op in ['insert', 'update', 'delete', 'create', 'drop', 'alter', 'truncate']):
            return QueryIntent.WRITE
        
        # Administrative operations
        if any(op in query_lower for op in ['vacuum', 'analyze', 'reindex', 'cluster']):
            return QueryIntent.ADMIN
        
        # Functions that might modify data
        if any(func in query_lower for func in ['nextval', 'setval', 'pg_advisory_lock']):
            return QueryIntent.WRITE
        
        # Default to read for SELECT and other queries
        return QueryIntent.READ
    
    def _select_best_replica(self) -> Optional[str]:
        """Select the best available replica based on health and load."""
        healthy_replicas = [
            (key, status) for key, status in self.replica_status.items()
            if status.is_healthy
        ]
        
        if not healthy_replicas:
            return None
        
        # Sort by load score (higher is better)
        healthy_replicas.sort(key=lambda x: x[1].load_score, reverse=True)
        
        # Use weighted random selection among top replicas
        top_replicas = healthy_replicas[:min(3, len(healthy_replicas))]
        weights = [status.load_score for _, status in top_replicas]
        
        if sum(weights) == 0:
            return random.choice(top_replicas)[0]
        
        # Weighted random selection
        total_weight = sum(weights)
        r = random.uniform(0, total_weight)
        
        cumulative_weight = 0
        for (key, status), weight in zip(top_replicas, weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return key
        
        return top_replicas[0][0]  # Fallback
    
    @asynccontextmanager
    async def get_session(self, query: str, force_primary: bool = False):
        """
        Get an appropriate database session based on query intent.
        
        Args:
            query: SQL query to be executed
            force_primary: Force routing to primary regardless of query intent
        """
        start_time = asyncio.get_event_loop().time()
        
        # Detect query intent
        intent = QueryIntent.WRITE if force_primary else self._detect_query_intent(query)
        
        try:
            if intent == QueryIntent.WRITE or intent == QueryIntent.ADMIN or force_primary:
                # Route to primary
                if not self.primary_status or not self.primary_status.is_healthy:
                    self.logger.error("Primary database is not healthy")
                    self.metrics['query_routing_total'].labels(
                        intent=intent.value,
                        target='primary',
                        status='failed'
                    ).inc()
                    raise Exception("Primary database is not available")
                
                async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                    self.routing_stats['primary_queries'] += 1
                    self.metrics['query_routing_total'].labels(
                        intent=intent.value,
                        target='primary',
                        status='success'
                    ).inc()
                    yield session
                    
            else:
                # Route to replica for read queries
                best_replica = self._select_best_replica()
                
                if best_replica:
                    try:
                        async with self.pool_manager.get_async_session(PoolType.READ_ONLY) as session:
                            self.routing_stats['replica_queries'] += 1
                            self.metrics['query_routing_total'].labels(
                                intent=intent.value,
                                target='replica',
                                status='success'
                            ).inc()
                            yield session
                            
                    except Exception as e:
                        self.logger.warning(f"Replica query failed, falling back to primary: {e}")
                        
                        # Fallback to primary
                        self.routing_stats['failover_events'] += 1
                        self.metrics['failover_events_total'].labels(
                            from_target='replica',
                            to_target='primary',
                            reason='replica_error'
                        ).inc()
                        
                        async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                            self.routing_stats['primary_queries'] += 1
                            yield session
                else:
                    # No healthy replicas, use primary
                    self.logger.warning("No healthy replicas available, routing to primary")
                    
                    self.routing_stats['failover_events'] += 1
                    self.metrics['failover_events_total'].labels(
                        from_target='replica',
                        to_target='primary',
                        reason='no_healthy_replicas'
                    ).inc()
                    
                    async with self.pool_manager.get_async_session(PoolType.MAIN) as session:
                        self.routing_stats['primary_queries'] += 1
                        self.metrics['query_routing_total'].labels(
                            intent=intent.value,
                            target='primary',
                            status='fallback'
                        ).inc()
                        yield session
                        
        except Exception as e:
            self.routing_stats['routing_errors'] += 1
            self.metrics['query_routing_total'].labels(
                intent=intent.value,
                target='error',
                status='failed'
            ).inc()
            raise
        finally:
            duration = asyncio.get_event_loop().time() - start_time
            self.metrics['routing_decision_duration'].labels(
                intent=intent.value
            ).observe(duration)
    
    async def execute_query(self, query: str, params: Optional[Dict] = None, 
                          force_primary: bool = False):
        """Execute a query with automatic routing."""
        async with self.get_session(query, force_primary) as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return result
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        healthy_replicas = sum(1 for status in self.replica_status.values() if status.is_healthy)
        
        return {
            'routing_stats': self.routing_stats.copy(),
            'replica_status': {
                'total_replicas': len(self.replica_status),
                'healthy_replicas': healthy_replicas,
                'primary_healthy': self.primary_status.is_healthy if self.primary_status else False
            },
            'replica_details': {
                key: {
                    'host': status.host,
                    'port': status.port,
                    'is_healthy': status.is_healthy,
                    'lag_seconds': status.lag_seconds,
                    'connection_count': status.connection_count,
                    'load_score': status.load_score
                }
                for key, status in self.replica_status.items()
            }
        }
    
    async def force_failover(self, reason: str = "manual"):
        """Force a failover event for testing."""
        self.logger.warning(f"Forcing failover: {reason}")
        
        # Mark all replicas as unhealthy temporarily
        for status in self.replica_status.values():
            status.is_healthy = False
        
        self.routing_stats['failover_events'] += 1
        self.metrics['failover_events_total'].labels(
            from_target='replica',
            to_target='primary',
            reason=reason
        ).inc()
        
        # They will recover on next health check
        await asyncio.sleep(1)
        await self._check_all_replicas()