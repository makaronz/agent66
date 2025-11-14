import { Router } from 'express';
import client from 'prom-client';
import { logger } from '../utils/logger';

const router = Router();

// Create a Registry to register the metrics
const register = new client.Registry();

// Add a default label which can be used to filter metrics
register.setDefaultLabels({
  app: 'film-time-tracker',
  version: process.env.APP_VERSION || '1.0.0',
  instance: process.env.INSTANCE_ID || 'unknown'
});

// Enable the collection of default metrics
client.collectDefaultMetrics({
  register,
  timeout: 5000,
  gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5]
});

// HTTP Request Metrics
const httpRequestDurationMicroseconds = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code', 'instance'],
  registers: [register],
  buckets: [0.1, 0.3, 0.5, 0.7, 1, 3, 5, 7, 10]
});

const httpRequestTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code', 'instance'],
  registers: [register]
});

const httpRequestSizeBytes = new client.Histogram({
  name: 'http_request_size_bytes',
  help: 'Size of HTTP requests in bytes',
  labelNames: ['method', 'route', 'instance'],
  registers: [register],
  buckets: [100, 1000, 10000, 100000, 1000000, 10000000]
});

const httpResponseSizeBytes = new client.Histogram({
  name: 'http_response_size_bytes',
  help: 'Size of HTTP responses in bytes',
  labelNames: ['method', 'route', 'status_code', 'instance'],
  registers: [register],
  buckets: [100, 1000, 10000, 100000, 1000000, 10000000]
});

// Application Business Metrics
const activeUsersGauge = new client.Gauge({
  name: 'active_users_total',
  help: 'Number of currently active users',
  labelNames: ['department', 'role'],
  registers: [register]
});

const timeEntriesTotal = new client.Counter({
  name: 'time_entries_total',
  help: 'Total number of time entries created',
  labelNames: ['status', 'department', 'project_type'],
  registers: [register]
});

const timeEntriesDuration = new client.Histogram({
  name: 'time_entry_duration_hours',
  help: 'Duration of time entries in hours',
  labelNames: ['department', 'role', 'project_type'],
  registers: [register],
  buckets: [1, 2, 4, 8, 12, 16, 24]
});

const projectsActive = new client.Gauge({
  name: 'projects_active_total',
  help: 'Number of currently active projects',
  labelNames: ['status', 'department'],
  registers: [register]
});

const crewMembersActive = new client.Gauge({
  name: 'crew_members_active_total',
  help: 'Number of currently active crew members',
  labelNames: ['department', 'role'],
  registers: [register]
});

const authenticationAttempts = new client.Counter({
  name: 'authentication_attempts_total',
  help: 'Total number of authentication attempts',
  labelNames: ['status', 'method', 'department'],
  registers: [register]
});

const dataProcessingQueue = new client.Gauge({
  name: 'data_processing_queue_size',
  help: 'Current size of data processing queue',
  labelNames: ['queue_type', 'priority'],
  registers: [register]
});

const databaseConnections = new client.Gauge({
  name: 'database_connections_active',
  help: 'Number of active database connections',
  labelNames: ['database_type', 'instance'],
  registers: [register]
});

const cacheHitRate = new client.Gauge({
  name: 'cache_hit_rate',
  help: 'Cache hit rate percentage',
  labelNames: ['cache_type', 'instance'],
  registers: [register]
});

// WebSocket Metrics
const websocketConnectionsActive = new client.Gauge({
  name: 'websocket_connections_active',
  help: 'Number of active WebSocket connections',
  labelNames: ['connection_type', 'department'],
  registers: [register]
});

const websocketMessagesTotal = new client.Counter({
  name: 'websocket_messages_total',
  help: 'Total number of WebSocket messages',
  labelNames: ['direction', 'message_type', 'department'],
  registers: [register]
});

// Error Metrics
const errorRate = new client.Gauge({
  name: 'error_rate_percentage',
  help: 'Current error rate percentage',
  labelNames: ['error_type', 'endpoint'],
  registers: [register]
});

const criticalErrorsTotal = new client.Counter({
  name: 'critical_errors_total',
  help: 'Total number of critical errors',
  labelNames: ['error_type', 'component', 'instance'],
  registers: [register]
});

// Performance Metrics
const cpuUsagePercent = new client.Gauge({
  name: 'cpu_usage_percent',
  help: 'Current CPU usage percentage',
  labelNames: ['instance', 'core'],
  registers: [register]
});

const memoryUsageBytes = new client.Gauge({
  name: 'memory_usage_bytes',
  help: 'Current memory usage in bytes',
  labelNames: ['type', 'instance'],
  registers: [register]
});

const diskUsageBytes = new client.Gauge({
  name: 'disk_usage_bytes',
  help: 'Current disk usage in bytes',
  labelNames: ['mount_point', 'instance'],
  registers: [register]
});

// Export metrics for use in other parts of the application
export {
  register,
  // HTTP Request Metrics
  httpRequestDurationMicroseconds,
  httpRequestTotal,
  httpRequestSizeBytes,
  httpResponseSizeBytes,
  // Business Metrics
  activeUsersGauge,
  timeEntriesTotal,
  timeEntriesDuration,
  projectsActive,
  crewMembersActive,
  authenticationAttempts,
  dataProcessingQueue,
  // Infrastructure Metrics
  databaseConnections,
  cacheHitRate,
  // WebSocket Metrics
  websocketConnectionsActive,
  websocketMessagesTotal,
  // Error & Performance Metrics
  errorRate,
  criticalErrorsTotal,
  cpuUsagePercent,
  memoryUsageBytes,
  diskUsageBytes
};

// Business metrics endpoint for dashboard monitoring
router.get('/business-metrics', async (req, res) => {
  try {
    // Update business metrics with current values
    await updateBusinessMetrics();

    const businessMetrics = await register.getMetricsAsJSON();
    const businessFiltered = businessMetrics.filter(metric =>
      metric.name.includes('active_users') ||
      metric.name.includes('time_entries') ||
      metric.name.includes('projects') ||
      metric.name.includes('crew_members') ||
      metric.name.includes('authentication')
    );

    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    logger.error('Failed to get business metrics:', error);
    res.status(500).json({ error: 'Failed to retrieve business metrics' });
  }
});

// WebSocket metrics endpoint
router.get('/websocket-metrics', async (req, res) => {
  try {
    // Update WebSocket metrics with current values
    await updateWebSocketMetrics();

    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    logger.error('Failed to get WebSocket metrics:', error);
    res.status(500).json({ error: 'Failed to retrieve WebSocket metrics' });
  }
});

// Main metrics endpoint
router.get('/', async (req, res) => {
  try {
    res.set('Content-Type', register.contentType);
    res.end(await register.metrics());
  } catch (error) {
    logger.error('Failed to get metrics:', error);
    res.status(500).end(error.message);
  }
});

// Helper functions to update metrics
async function updateBusinessMetrics() {
  try {
    // Get active users from database or cache
    // This is a placeholder - implement actual business logic
    activeUsersGauge.set({ department: 'production', role: 'crew' }, 25);
    activeUsersGauge.set({ department: 'post-production', role: 'editor' }, 15);
    activeUsersGauge.set({ department: 'vfx', role: 'artist' }, 12);

    projectsActive.set({ status: 'active', department: 'production' }, 8);
    projectsActive.set({ status: 'active', department: 'post-production' }, 5);

    crewMembersActive.set({ department: 'production', role: 'director' }, 3);
    crewMembersActive.set({ department: 'production', role: 'cameraman' }, 12);

    dataProcessingQueue.set({ queue_type: 'time_entries', priority: 'high' }, 5);
    dataProcessingQueue.set({ queue_type: 'time_entries', priority: 'normal' }, 23);

  } catch (error) {
    logger.error('Failed to update business metrics:', error);
  }
}

async function updateWebSocketMetrics() {
  try {
    // Get WebSocket connection counts
    // This is a placeholder - implement actual WebSocket monitoring
    websocketConnectionsActive.set({ connection_type: 'real_time_updates', department: 'production' }, 18);
    websocketConnectionsActive.set({ connection_type: 'notifications', department: 'all' }, 45);

  } catch (error) {
    logger.error('Failed to update WebSocket metrics:', error);
  }
}

export { router as metricsRouter };
// Enhanced Database Performance Metrics
import { getConnectionMetrics, checkDatabaseHealth } from '../database/connection';

const databaseConnectionPool = new client.Gauge({
  name: 'database_connection_pool_size',
  help: 'Current database connection pool size',
  labelNames: ['database_type', 'instance'],
  registers: [register]
});

const databaseQueriesTotal = new client.Counter({
  name: 'database_queries_total',
  help: 'Total number of database queries',
  labelNames: ['operation', 'table', 'status', 'instance'],
  registers: [register]
});

const databaseQueryDuration = new client.Histogram({
  name: 'database_query_duration_seconds',
  help: 'Duration of database queries in seconds',
  labelNames: ['operation', 'table', 'instance'],
  buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  registers: [register]
});

const databaseSlowQueries = new client.Counter({
  name: 'database_slow_queries_total',
  help: 'Total number of slow database queries (>1s)',
  labelNames: ['operation', 'table', 'instance'],
  registers: [register]
});

// Update database metrics periodically
const updateDatabaseMetrics = async () => {
  try {
    const metrics = getConnectionMetrics();
    const health = await checkDatabaseHealth();
    const instanceId = process.env.INSTANCE_ID || 'unknown';

    // Update connection pool metrics
    databaseConnectionPool.set({
      database_type: 'postgresql',
      instance: instanceId
    }, Number(process.env.DATABASE_POOL_SIZE) || 20);

    // Update query metrics
    databaseQueriesTotal.set({
      operation: 'total',
      table: 'all',
      status: 'executed',
      instance: instanceId
    }, metrics.totalQueries);

    databaseSlowQueries.set({
      operation: 'slow',
      table: 'all',
      instance: instanceId
    }, metrics.slowQueries);

    // Update average query time histogram
    if (metrics.averageQueryTime > 0) {
      databaseQueryDuration.observe(
        { operation: 'average', table: 'all', instance: instanceId },
        metrics.averageQueryTime / 1000 // Convert to seconds
      );
    }

  } catch (error) {
    console.error('Error updating database metrics:', error);
  }
};

// Update metrics every 30 seconds
setInterval(() => {
  updateDatabaseMetrics();
}, 30000);

// Initial metrics update
updateDatabaseMetrics();


