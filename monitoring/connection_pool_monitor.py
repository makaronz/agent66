"""
Connection pool monitoring and health checks.
Provides real-time monitoring of database connection pools and PgBouncer.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import psycopg2
from prometheus_client import Counter, Histogram, Gauge, Info
from database.connection_pool import ConnectionPoolManager, PoolType


@dataclass
class PoolStats:
    """Statistics for a connection pool."""
    pool_name: str
    total_connections: int
    active_connections: int
    idle_connections: int
    waiting_connections: int
    max_connections: int
    pool_utilization: float
    avg_wait_time: float
    total_queries: int
    queries_per_second: float
    error_rate: float
    last_updated: datetime


@dataclass
class PgBouncerStats:
    """PgBouncer statistics."""
    database: str
    user: str
    cl_active: int
    cl_waiting: int
    sv_active: int
    sv_idle: int
    sv_used: int
    sv_tested: int
    sv_login: int
    maxwait: int
    maxwait_us: int
    pool_mode: str


class ConnectionPoolMonitor:
    """
    Monitors database connection pools and PgBouncer statistics.
    Provides health checks, metrics collection, and alerting.
    """
    
    def __init__(self, pool_manager: ConnectionPoolManager, config: Dict[str, Any]):
        self.pool_manager = pool_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Monitoring configuration
        self.monitoring_interval = config.get('monitoring', {}).get('pool_check_interval', 30)
        self.alert_thresholds = config.get('monitoring', {}).get('alert_thresholds', {})
        
        # Metrics
        self._setup_metrics()
        
        # Statistics storage
        self.pool_stats: Dict[str, PoolStats] = {}
        self.pgbouncer_stats: List[PgBouncerStats] = []
        
        # Health status
        self.is_healthy = True
        self.last_health_check = datetime.now()
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _setup_metrics(self):
        """Setup Prometheus metrics for connection pool monitoring."""
        self.metrics = {
            'pool_connections_total': Gauge(
                'pgbouncer_pool_connections_total',
                'Total connections in pool',
                ['database', 'pool_type', 'state']
            ),
            'pool_utilization': Gauge(
                'pgbouncer_pool_utilization_ratio',
                'Pool utilization ratio (0-1)',
                ['database', 'pool_type']
            ),
            'pool_wait_time': Histogram(
                'pgbouncer_pool_wait_time_seconds',
                'Time spent waiting for connections',
                ['database', 'pool_type']
            ),
            'pool_queries_total': Counter(
                'pgbouncer_pool_queries_total',
                'Total queries processed by pool',
                ['database', 'pool_type']
            ),
            'pool_errors_total': Counter(
                'pgbouncer_pool_errors_total',
                'Total pool errors',
                ['database', 'pool_type', 'error_type']
            ),
            'pool_health_status': Gauge(
                'pgbouncer_pool_health_status',
                'Pool health status (1=healthy, 0=unhealthy)',
                ['database', 'pool_type']
            ),
            'pgbouncer_info': Info(
                'pgbouncer_info',
                'PgBouncer version and configuration info'
            )
        }
    
    async def start_monitoring(self):
        """Start background monitoring tasks."""
        if self._running:
            self.logger.warning("Monitoring already running")
            return
        
        self._running = True
        self.logger.info("Starting connection pool monitoring")
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Initialize PgBouncer info
        await self._collect_pgbouncer_info()
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks."""
        if not self._running:
            return
        
        self._running = False
        self.logger.info("Stopping connection pool monitoring")
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect pool statistics
                await self._collect_pool_stats()
                
                # Collect PgBouncer statistics
                await self._collect_pgbouncer_stats()
                
                # Update metrics
                self._update_metrics()
                
                # Check health and alerts
                await self._check_health_and_alerts()
                
                # Update last health check time
                self.last_health_check = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                self.is_healthy = False
            
            # Wait for next iteration
            await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_pool_stats(self):
        """Collect statistics from connection pools."""
        for pool_type in PoolType:
            try:
                # Get pool health status
                health_status = await self.pool_manager.health_check(pool_type)
                pool_info = health_status.get(pool_type.value, {})
                
                if pool_info.get('status') == 'healthy':
                    stats = PoolStats(
                        pool_name=pool_type.value,
                        total_connections=pool_info.get('pool_size', 0),
                        active_connections=pool_info.get('active_connections', 0),
                        idle_connections=pool_info.get('pool_size', 0) - pool_info.get('active_connections', 0),
                        waiting_connections=0,  # Would need to get from engine internals
                        max_connections=pool_info.get('pool_size', 0),
                        pool_utilization=pool_info.get('active_connections', 0) / max(pool_info.get('pool_size', 1), 1),
                        avg_wait_time=0.0,  # Would need to track this
                        total_queries=0,  # Would need to track this
                        queries_per_second=0.0,  # Would need to track this
                        error_rate=0.0,  # Would need to track this
                        last_updated=datetime.now()
                    )
                    
                    self.pool_stats[pool_type.value] = stats
                    
                else:
                    self.logger.warning(f"Pool {pool_type.value} is unhealthy: {pool_info.get('error')}")
                    
            except Exception as e:
                self.logger.error(f"Error collecting stats for pool {pool_type.value}: {e}")
    
    async def _collect_pgbouncer_stats(self):
        """Collect statistics from PgBouncer."""
        try:
            # Connect to PgBouncer admin interface
            pgbouncer_config = self.config.get('database', {})
            pgbouncer_host = pgbouncer_config.get('pgbouncer_host', 'pgbouncer')
            pgbouncer_port = pgbouncer_config.get('pgbouncer_port', 6432)
            
            conn = psycopg2.connect(
                host=pgbouncer_host,
                port=pgbouncer_port,
                database='pgbouncer',
                user='postgres',
                password=pgbouncer_config.get('password', ''),
                connect_timeout=10
            )
            
            with conn.cursor() as cursor:
                # Get pool statistics
                cursor.execute("SHOW POOLS;")
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                self.pgbouncer_stats = []
                for row in rows:
                    stats_dict = dict(zip(columns, row))
                    stats = PgBouncerStats(
                        database=stats_dict.get('database', ''),
                        user=stats_dict.get('user', ''),
                        cl_active=stats_dict.get('cl_active', 0),
                        cl_waiting=stats_dict.get('cl_waiting', 0),
                        sv_active=stats_dict.get('sv_active', 0),
                        sv_idle=stats_dict.get('sv_idle', 0),
                        sv_used=stats_dict.get('sv_used', 0),
                        sv_tested=stats_dict.get('sv_tested', 0),
                        sv_login=stats_dict.get('sv_login', 0),
                        maxwait=stats_dict.get('maxwait', 0),
                        maxwait_us=stats_dict.get('maxwait_us', 0),
                        pool_mode=stats_dict.get('pool_mode', 'unknown')
                    )
                    self.pgbouncer_stats.append(stats)
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error collecting PgBouncer stats: {e}")
            self.pgbouncer_stats = []
    
    async def _collect_pgbouncer_info(self):
        """Collect PgBouncer version and configuration info."""
        try:
            pgbouncer_config = self.config.get('database', {})
            pgbouncer_host = pgbouncer_config.get('pgbouncer_host', 'pgbouncer')
            pgbouncer_port = pgbouncer_config.get('pgbouncer_port', 6432)
            
            conn = psycopg2.connect(
                host=pgbouncer_host,
                port=pgbouncer_port,
                database='pgbouncer',
                user='postgres',
                password=pgbouncer_config.get('password', ''),
                connect_timeout=10
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SHOW VERSION;")
                version_info = cursor.fetchone()
                
                cursor.execute("SHOW CONFIG;")
                config_rows = cursor.fetchall()
                config_dict = {row[0]: row[1] for row in config_rows}
                
                # Update Prometheus info metric
                self.metrics['pgbouncer_info'].info({
                    'version': version_info[0] if version_info else 'unknown',
                    'pool_mode': config_dict.get('pool_mode', 'unknown'),
                    'max_client_conn': config_dict.get('max_client_conn', 'unknown'),
                    'default_pool_size': config_dict.get('default_pool_size', 'unknown')
                })
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error collecting PgBouncer info: {e}")
    
    def _update_metrics(self):
        """Update Prometheus metrics with collected statistics."""
        # Update pool metrics
        for pool_name, stats in self.pool_stats.items():
            labels = {'database': 'smc_trading_agent', 'pool_type': pool_name}
            
            self.metrics['pool_connections_total'].labels(
                **labels, state='active'
            ).set(stats.active_connections)
            
            self.metrics['pool_connections_total'].labels(
                **labels, state='idle'
            ).set(stats.idle_connections)
            
            self.metrics['pool_connections_total'].labels(
                **labels, state='waiting'
            ).set(stats.waiting_connections)
            
            self.metrics['pool_utilization'].labels(**labels).set(stats.pool_utilization)
            
            self.metrics['pool_health_status'].labels(**labels).set(1 if stats.pool_utilization < 0.9 else 0)
        
        # Update PgBouncer metrics
        for stats in self.pgbouncer_stats:
            if stats.database and stats.database != 'pgbouncer':
                labels = {'database': stats.database, 'pool_type': 'pgbouncer'}
                
                self.metrics['pool_connections_total'].labels(
                    **labels, state='client_active'
                ).set(stats.cl_active)
                
                self.metrics['pool_connections_total'].labels(
                    **labels, state='client_waiting'
                ).set(stats.cl_waiting)
                
                self.metrics['pool_connections_total'].labels(
                    **labels, state='server_active'
                ).set(stats.sv_active)
                
                self.metrics['pool_connections_total'].labels(
                    **labels, state='server_idle'
                ).set(stats.sv_idle)
    
    async def _check_health_and_alerts(self):
        """Check health status and trigger alerts if needed."""
        overall_healthy = True
        alerts = []
        
        # Check pool utilization
        for pool_name, stats in self.pool_stats.items():
            utilization_threshold = self.alert_thresholds.get('pool_utilization', 0.8)
            
            if stats.pool_utilization > utilization_threshold:
                overall_healthy = False
                alerts.append(f"High pool utilization for {pool_name}: {stats.pool_utilization:.2%}")
        
        # Check PgBouncer waiting connections
        for stats in self.pgbouncer_stats:
            if stats.cl_waiting > self.alert_thresholds.get('max_waiting_connections', 10):
                overall_healthy = False
                alerts.append(f"High waiting connections for {stats.database}: {stats.cl_waiting}")
        
        # Check if monitoring is stale
        time_since_check = datetime.now() - self.last_health_check
        if time_since_check > timedelta(minutes=5):
            overall_healthy = False
            alerts.append("Connection pool monitoring is stale")
        
        self.is_healthy = overall_healthy
        
        # Log alerts
        for alert in alerts:
            self.logger.warning(f"Connection pool alert: {alert}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            'healthy': self.is_healthy,
            'last_check': self.last_health_check.isoformat(),
            'pool_stats': {name: asdict(stats) for name, stats in self.pool_stats.items()},
            'pgbouncer_stats': [asdict(stats) for stats in self.pgbouncer_stats],
            'monitoring_running': self._running
        }
    
    def get_pool_summary(self) -> Dict[str, Any]:
        """Get a summary of all pool statistics."""
        total_connections = sum(stats.active_connections for stats in self.pool_stats.values())
        total_capacity = sum(stats.max_connections for stats in self.pool_stats.values())
        avg_utilization = sum(stats.pool_utilization for stats in self.pool_stats.values()) / max(len(self.pool_stats), 1)
        
        return {
            'total_active_connections': total_connections,
            'total_capacity': total_capacity,
            'average_utilization': avg_utilization,
            'healthy_pools': sum(1 for stats in self.pool_stats.values() if stats.pool_utilization < 0.9),
            'total_pools': len(self.pool_stats),
            'pgbouncer_databases': len(self.pgbouncer_stats)
        }