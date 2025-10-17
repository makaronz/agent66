import { Router, Request, Response } from 'express';
import { config } from '../config';
import { logger } from '../utils/logger';

const router = Router();

// Basic health check
router.get('/', (req: Request, res: Response) => {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: config.app.environment,
    version: config.app.version,
  });
});

// Detailed health check with service status
router.get('/detailed', async (req: Request, res: Response) => {
  try {
    const healthStatus = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      environment: config.app.environment,
      version: config.app.version,
      services: {
        database: await checkDatabaseHealth(),
        mongodb: await checkMongoDBHealth(),
        redis: await checkRedisHealth(),
        external: await checkExternalServices(),
      },
      system: {
        memory: getMemoryUsage(),
        cpu: getCpuUsage(),
        disk: getDiskUsage(),
      },
    };

    // Determine overall status
    const allServicesHealthy = Object.values(healthStatus.services).every(
      (service: any) => service.status === 'healthy'
    );

    if (!allServicesHealthy) {
      healthStatus.status = 'degraded';
      return res.status(503).json(healthStatus);
    }

    res.status(200).json(healthStatus);
  } catch (error) {
    logger.error('Health check failed:', error);
    res.status(500).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: 'Health check failed',
    });
  }
});

// Readiness probe
router.get('/ready', async (req: Request, res: Response) => {
  try {
    // Check if all critical services are ready
    const dbHealthy = await checkDatabaseHealth();
    const mongoHealthy = await checkMongoDBHealth();

    if (dbHealthy.status === 'healthy' && mongoHealthy.status === 'healthy') {
      res.status(200).json({
        status: 'ready',
        timestamp: new Date().toISOString(),
      });
    } else {
      res.status(503).json({
        status: 'not ready',
        timestamp: new Date().toISOString(),
        services: {
          database: dbHealthy,
          mongodb: mongoHealthy,
        },
      });
    }
  } catch (error) {
    logger.error('Readiness check failed:', error);
    res.status(503).json({
      status: 'not ready',
      timestamp: new Date().toISOString(),
      error: 'Readiness check failed',
    });
  }
});

// Liveness probe
router.get('/live', (req: Request, res: Response) => {
  res.status(200).json({
    status: 'alive',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// Service-specific health checks
async function checkDatabaseHealth() {
  try {
    // Implementation would check PostgreSQL connection
    return {
      status: 'healthy',
      latency: Date.now(), // Would be actual measurement
      lastCheck: new Date().toISOString(),
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error.message,
      lastCheck: new Date().toISOString(),
    };
  }
}

async function checkMongoDBHealth() {
  try {
    // Implementation would check MongoDB connection
    return {
      status: 'healthy',
      latency: Date.now(), // Would be actual measurement
      lastCheck: new Date().toISOString(),
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error.message,
      lastCheck: new Date().toISOString(),
    };
  }
}

async function checkRedisHealth() {
  try {
    // Implementation would check Redis connection
    return {
      status: 'healthy',
      latency: Date.now(), // Would be actual measurement
      lastCheck: new Date().toISOString(),
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error.message,
      lastCheck: new Date().toISOString(),
    };
  }
}

async function checkExternalServices() {
  const services = {};

  // Check Binance API
  try {
    // Implementation would ping Binance API
    services.binance = {
      status: 'healthy',
      lastCheck: new Date().toISOString(),
    };
  } catch (error) {
    services.binance = {
      status: 'unhealthy',
      error: error.message,
      lastCheck: new Date().toISOString(),
    };
  }

  // Check other services as needed
  return services;
}

function getMemoryUsage() {
  const usage = process.memoryUsage();
  return {
    rss: Math.round(usage.rss / 1024 / 1024 * 100) / 100, // MB
    heapTotal: Math.round(usage.heapTotal / 1024 / 1024 * 100) / 100, // MB
    heapUsed: Math.round(usage.heapUsed / 1024 / 1024 * 100) / 100, // MB
    external: Math.round(usage.external / 1024 / 1024 * 100) / 100, // MB
  };
}

function getCpuUsage() {
  // Implementation would get actual CPU usage
  return {
    usage: process.cpuUsage(),
    loadAverage: require('os').loadavg(),
  };
}

function getDiskUsage() {
  // Implementation would get actual disk usage
  return {
    total: 'unknown',
    used: 'unknown',
    free: 'unknown',
  };
}

export default router;