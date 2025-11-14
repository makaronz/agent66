import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';
import { redisClient, cacheHelpers } from '../cache/redis-client';
import {
  httpRequestDurationMicroseconds,
  httpRequestTotal,
  databaseSlowQueries,
  performanceSlaCompliance,
  apiResponseTimeP95
} from '../routes/metrics';

// Performance monitoring middleware
export const performanceMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const startTime = Date.now();
  const startMemory = process.memoryUsage();

  // Generate unique request ID for tracking
  const requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  req.headers['x-request-id'] = requestId;

  // Log request start
  logger.info(`🚀 [${requestId}] ${req.method} ${req.path}`, {
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    contentLength: req.get('Content-Length') || '0',
  });

  // Override res.end to capture response metrics
  const originalEnd = res.end;
  res.end = function (this: Response, ...args: any[]) {
    const endTime = Date.now();
    const endMemory = process.memoryUsage();
    const duration = endTime - startTime;
    const route = req.route ? req.route.path : req.path;

    // Calculate memory delta
    const memoryDelta = {
      rss: endMemory.rss - startMemory.rss,
      heapUsed: endMemory.heapUsed - startMemory.heapUsed,
      heapTotal: endMemory.heapTotal - startMemory.heapTotal,
    };

    // Update Prometheus metrics
    httpRequestDurationMicroseconds
      .labels(req.method, route, res.statusCode.toString(), process.env.INSTANCE_ID || 'unknown')
      .observe(duration / 1000);

    httpRequestTotal
      .labels(req.method, route, res.statusCode.toString(), process.env.INSTANCE_ID || 'unknown')
      .inc();

    // Track P95 response times
    apiResponseTimeP95
      .labels(route, req.method)
      .observe(duration / 1000);

    // Performance SLA tracking
    if (duration < 200) {
      performanceSlaCompliance.set({
        metric_type: 'api_response_time',
        sla_target: '<200ms'
      }, 100);
    } else if (duration < 1000) {
      performanceSlaCompliance.set({
        metric_type: 'api_response_time',
        sla_target: '<200ms'
      }, 80);
    } else {
      performanceSlaCompliance.set({
        metric_type: 'api_response_time',
        sla_target: '<200ms'
      }, 50);
    }

    // Log request completion with performance metrics
    const logLevel = duration > 1000 ? 'warn' : duration > 500 ? 'info' : 'debug';
    logger[logLevel](`✅ [${requestId}] ${req.method} ${req.path} - ${res.statusCode} - ${duration}ms`, {
      responseSize: res.get('Content-Length') || '0',
      memoryDelta: {
        rss: `${(memoryDelta.rss / 1024 / 1024).toFixed(2)}MB`,
        heapUsed: `${(memoryDelta.heapUsed / 1024 / 1024).toFixed(2)}MB`,
      },
    });

    // Log slow requests
    if (duration > 1000) {
      logger.warn(`🐌 Slow request detected: [${requestId}] ${req.method} ${req.path} - ${duration}ms`, {
        query: req.query,
        params: req.params,
        body: req.method !== 'GET' ? '[REDACTED]' : undefined,
      });
    }

    // Call original end
    return originalEnd.apply(this, args);
  };

  next();
};

// API response caching middleware
export const cacheMiddleware = (options: {
  ttl?: number;
  keyGenerator?: (req: Request) => string;
  condition?: (req: Request, res: Response) => boolean;
} = {}) => {
  const {
    ttl = 300, // 5 minutes default
    keyGenerator = (req) => `api:${req.method}:${req.path}:${JSON.stringify(req.query)}`,
    condition = (req, res) => req.method === 'GET' && res.statusCode === 200,
  } = options;

  return async (req: Request, res: Response, next: NextFunction) => {
    // Skip caching for non-GET requests
    if (req.method !== 'GET') {
      return next();
    }

    const cacheKey = keyGenerator(req);

    try {
      // Try to get from cache
      const cached = await cacheHelpers.getCachedApiResponse(cacheKey);

      if (cached) {
        logger.debug(`🎯 Cache hit for: ${cacheKey}`);
        res.set({
          'X-Cache': 'HIT',
          'X-Cache-Key': cacheKey,
          'X-Cache-TTL': ttl.toString(),
        });
        return res.json(cached);
      }

      logger.debug(`❌ Cache miss for: ${cacheKey}`);

      // Override res.json to cache successful responses
      const originalJson = res.json;
      res.json = function (this: Response, data: any) {
        // Only cache successful responses
        if (condition(req, res)) {
          cacheHelpers.cacheApiResponse(cacheKey, data, ttl).catch((error) => {
            logger.error('Error caching response:', error);
          });

          res.set({
            'X-Cache': 'MISS',
            'X-Cache-Key': cacheKey,
            'X-Cache-TTL': ttl.toString(),
          });
        }

        return originalJson.call(this, data);
      };

      next();
    } catch (error) {
      logger.error('Cache middleware error:', error);
      next(); // Continue without caching if there's an error
    }
  };
};

// Memory usage monitoring middleware
export const memoryMonitoringMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const memUsage = process.memoryUsage();

  // Log memory usage if it's getting high
  const memoryThreshold = 512 * 1024 * 1024; // 512MB
  if (memUsage.heapUsed > memoryThreshold) {
    logger.warn(`⚠️ High memory usage detected: ${(memUsage.heapUsed / 1024 / 1024).toFixed(2)}MB`, {
      route: req.path,
      method: req.method,
      memoryUsage: {
        rss: `${(memUsage.rss / 1024 / 1024).toFixed(2)}MB`,
        heapUsed: `${(memUsage.heapUsed / 1024 / 1024).toFixed(2)}MB`,
        heapTotal: `${(memUsage.heapTotal / 1024 / 1024).toFixed(2)}MB`,
        external: `${(memUsage.external / 1024 / 1024).toFixed(2)}MB`,
      },
    });

    // Force garbage collection if available
    if (global.gc) {
      global.gc();
      logger.info('🗑️ Forced garbage collection due to high memory usage');
    }
  }

  next();
};

// Rate limiting with performance tracking
export const performanceRateLimit = (options: {
  windowMs?: number;
  max?: number;
  message?: string;
}) => {
  const {
    windowMs = 15 * 60 * 1000, // 15 minutes
    max = 100, // limit each IP to 100 requests per windowMs
    message = 'Too many requests from this IP, please try again later.',
  } = options;

  const requests = new Map<string, { count: number; resetTime: number }>();

  return (req: Request, res: Response, next: NextFunction) => {
    const ip = req.ip || req.connection.remoteAddress || 'unknown';
    const now = Date.now();

    // Clean up expired entries
    for (const [key, value] of requests.entries()) {
      if (now > value.resetTime) {
        requests.delete(key);
      }
    }

    const requestData = requests.get(ip);

    if (!requestData) {
      // First request from this IP
      requests.set(ip, {
        count: 1,
        resetTime: now + windowMs,
      });
      return next();
    }

    if (requestData.count >= max) {
      const resetTime = Math.ceil((requestData.resetTime - now) / 1000);
      logger.warn(`🚫 Rate limit exceeded for IP: ${ip}`, {
        requests: requestData.count,
        limit: max,
        resetTime: `${resetTime}s`,
        path: req.path,
      });

      return res.status(429).json({
        error: message,
        retryAfter: resetTime,
        limit: max,
        windowMs,
      });
    }

    requestData.count++;
    next();
  };
};

// Database query performance monitoring
export const dbPerformanceMiddleware = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    const originalQuery = res.locals.query || ((() => next()) as any);

    // This would be integrated with your database client
    // For now, it's a placeholder for the concept
    res.locals.onQueryComplete = (query: string, duration: number) => {
      if (duration > 1000) {
        logger.warn(`🐌 Slow database query: ${duration}ms`, {
          query: query.substring(0, 200) + '...',
          path: req.path,
          method: req.method,
        });

        databaseSlowQueries.inc({
          operation: 'select',
          table: 'unknown',
          instance: process.env.INSTANCE_ID || 'unknown'
        });
      }
    };

    next();
  };
};

// Performance metrics collector
export const collectPerformanceMetrics = () => {
  return {
    async getMetrics() {
      try {
        const redisStats = await redisClient.getStats();
        const memUsage = process.memoryUsage();
        const cpuUsage = process.cpuUsage();

        return {
          timestamp: new Date().toISOString(),
          memory: {
            rss: memUsage.rss,
            heapUsed: memUsage.heapUsed,
            heapTotal: memUsage.heapTotal,
            external: memUsage.external,
          },
          cpu: {
            user: cpuUsage.user,
            system: cpuUsage.system,
          },
          uptime: process.uptime(),
          redis: redisStats,
        };
      } catch (error) {
        logger.error('Error collecting performance metrics:', error);
        return null;
      }
    },
  };
};

// Cache invalidation helper
export const invalidateCache = (pattern: string) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      await cacheHelpers.invalidateCachePattern(pattern);
      logger.info(`🗑️ Cache invalidated for pattern: ${pattern}`);
    } catch (error) {
      logger.error('Error invalidating cache:', error);
    }
    next();
  };
};