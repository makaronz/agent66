import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { config } from './config/env-validation';
import { logger } from './utils/logger';
import { errorHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/requestLogger';
import { authMiddleware } from './middleware/auth';
import healthRouter from './routes/health';
// import authRouter from './routes/auth';
import projectsRouter from './routes/projects';
import timeEntriesRouter from './routes/time-entries';
import crewRouter from './routes/crew';
import reportsRouter from './routes/reports';
import { metricsRouter, metricsMiddleware } from './routes/metrics';
import { setupSwagger } from './utils/swagger';
import { initializeDatabase, closeDatabaseConnection } from './database/connection';
import { WebSocketServer } from './websocket/server';
import { redisClient } from './cache/redis-client';
import {
  performanceMiddleware,
  cacheMiddleware,
  memoryMonitoringMiddleware,
  performanceRateLimit,
  invalidateCache
} from './middleware/performance';

class Server {
  private app: express.Application;
  private server: any;
  private wsServer: WebSocketServer;

  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.wsServer = new WebSocketServer(this.server);
    this.initializeMiddlewares();
    this.initializeRoutes();
    this.initializeErrorHandling();
  }

  private initializeMiddlewares(): void {
    // Performance monitoring middleware (should be first)
    this.app.use(performanceMiddleware);

    // Memory monitoring middleware
    this.app.use(memoryMonitoringMiddleware);

    // Prometheus metrics collection
    this.app.use(metricsMiddleware);

    // Security middleware
    if (config.security.helmet.enabled) {
      this.app.use(helmet({
        ...config.security.helmet.contentSecurityPolicy,
        // Performance optimizations
        hsts: {
          maxAge: 31536000,
          includeSubDomains: true,
          preload: true
        },
        // Enable compression for security headers
        crossOriginEmbedderPolicy: false,
      }));
    }

    // CORS middleware
    this.app.use(cors({
      ...config.cors,
      // Performance optimizations
      maxAge: 86400, // Cache preflight requests for 24 hours
      credentials: true,
    }));

    // Enhanced compression middleware with performance settings
    this.app.use(compression({
      level: 6,
      threshold: 1024,
      filter: (req, res) => {
        if (req.headers['x-no-compression']) {
          return false;
        }
        return compression.filter(req, res);
      },
    }));

    // Request logging
    this.app.use(requestLogger);

    // Body parsing middleware with size limits for performance
    this.app.use(express.json({
      limit: '10mb',
      verify: (req, res, buf) => {
        // Verify request size for performance monitoring
        if (buf.length > 1024 * 1024) { // 1MB
          logger.warn(`⚠️ Large request body detected: ${buf.length} bytes`);
        }
      }
    }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Enhanced rate limiting with performance tracking
    const limiter = rateLimit({
      ...config.rateLimit,
      // Performance optimizations
      skip: (req) => {
        // Skip rate limiting for health checks and metrics
        return req.path.startsWith('/health') || req.path.startsWith('/metrics');
      },
      onLimitReached: (req, res, options) => {
        logger.warn(`🚫 Rate limit exceeded for IP: ${req.ip}`, {
          path: req.path,
          method: req.method,
          userAgent: req.get('User-Agent'),
        });
      },
    });
    this.app.use('/api/', limiter);

    // Custom performance-based rate limiting for sensitive endpoints
    this.app.use('/api/projects', performanceRateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 200, // More restrictive for projects
      message: 'Too many project requests, please try again later.',
    }));

    this.app.use('/api/reports', performanceRateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 50, // Very restrictive for reports
      message: 'Too many report requests, please try again later.',
    }));

    // Health check endpoint (no rate limiting, with caching)
    this.app.use('/health',
      cacheMiddleware({ ttl: 30 }), // Cache health checks for 30 seconds
      healthRouter
    );

    // Metrics endpoint (no rate limiting for monitoring)
    this.app.use('/metrics', metricsRouter);
  }

  private initializeRoutes(): void {
    // API routes with performance optimizations

    // Cache GET routes for better performance
    this.app.use('/api/projects',
      authMiddleware,
      cacheMiddleware({ ttl: 300 }), // Cache project data for 5 minutes
      invalidateCache('api:*'), // Clear cache on modifications
      projectsRouter
    );

    this.app.use('/api/time-entries',
      authMiddleware,
      cacheMiddleware({ ttl: 60 }), // Cache time entries for 1 minute
      invalidateCache('api:time-entries:*'),
      timeEntriesRouter
    );

    this.app.use('/api/crew',
      authMiddleware,
      cacheMiddleware({ ttl: 600 }), // Cache crew data for 10 minutes
      invalidateCache('api:crew:*'),
      crewRouter
    );

    this.app.use('/api/reports',
      authMiddleware,
      cacheMiddleware({
        ttl: 1800, // Cache reports for 30 minutes
        keyGenerator: (req) => `reports:${req.path}:${JSON.stringify(req.query)}:${req.user?.id}`
      }),
      reportsRouter
    );

    // API documentation (development only)
    if (config.app.environment !== 'production') {
      setupSwagger(this.app);
    }

    // 404 handler with performance tracking
    this.app.use('*', (req, res) => {
      logger.warn(`404 - Route not found: ${req.method} ${req.originalUrl}`, {
        ip: req.ip,
        userAgent: req.get('User-Agent'),
      });

      res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.originalUrl} not found`,
        timestamp: new Date().toISOString(),
        requestId: req.headers['x-request-id'],
      });
    });
  }

  private initializeErrorHandling(): void {
    // Enhanced error handling middleware with performance tracking
    this.app.use((error: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
      const startTime = Date.now();

      // Log error with performance context
      logger.error('❌ Unhandled error:', {
        error: error.message,
        stack: error.stack,
        path: req.path,
        method: req.method,
        ip: req.ip,
        requestId: req.headers['x-request-id'],
        memoryUsage: process.memoryUsage(),
      });

      // Handle specific error types
      if (error.name === 'ValidationError') {
        return res.status(400).json({
          error: 'Validation Error',
          message: error.message,
          timestamp: new Date().toISOString(),
          requestId: req.headers['x-request-id'],
        });
      }

      if (error.name === 'UnauthorizedError') {
        return res.status(401).json({
          error: 'Unauthorized',
          message: 'Authentication required',
          timestamp: new Date().toISOString(),
          requestId: req.headers['x-request-id'],
        });
      }

      // Default error response
      const statusCode = error.statusCode || 500;
      const message = config.app.environment === 'production'
        ? 'Internal Server Error'
        : error.message;

      res.status(statusCode).json({
        error: 'Internal Server Error',
        message,
        timestamp: new Date().toISOString(),
        requestId: req.headers['x-request-id'],
        ...(config.app.environment !== 'production' && { stack: error.stack }),
      });

      // Track error handling performance
      const duration = Date.now() - startTime;
      logger.info(`🔧 Error handled in ${duration}ms`);
    });

    // Global error handler
    this.app.use(errorHandler);
  }

  public async start(): Promise<void> {
    try {
      // Initialize Redis connection for caching
      logger.info('🔗 Initializing Redis connection...');
      await redisClient.connect();
      logger.info('✅ Redis connected successfully');

      // Initialize database connections with performance monitoring
      logger.info('🗄️ Initializing database connections...');
      await initializeDatabase();
      logger.info('✅ Database connections established');

      // Start the HTTP server
      this.server.listen(config.app.port, config.app.host, () => {
        logger.info(`🚀 Server started successfully`);
        logger.info(`📍 Environment: ${config.app.environment}`);
        logger.info(`🌐 Server: http://${config.app.host}:${config.app.port}`);
        logger.info(`📚 API Docs: http://${config.app.host}:${config.app.port}/api-docs`);
        logger.info(`📊 Metrics: http://${config.app.host}:${config.app.port}/metrics`);
        logger.info(`🔧 WebSocket: ws://${config.app.host}:${config.app.port}/ws`);
        logger.info(`🔗 Redis: ${process.env.REDIS_HOST || 'localhost'}:${process.env.REDIS_PORT || 6379}`);

        // Log performance configuration
        logger.info(`⚡ Performance optimizations enabled:`, {
          compression: true,
          caching: true,
          connectionPool: process.env.DATABASE_POOL_SIZE || 20,
          metricsCollection: true,
          memoryMonitoring: true,
        });
      });

      // Handle server errors
      this.server.on('error', (error: NodeJS.ErrnoException) => {
        if (error.syscall !== 'listen') {
          throw error;
        }

        const bind = typeof config.app.port === 'string'
          ? 'Pipe ' + config.app.port
          : 'Port ' + config.app.port;

        switch (error.code) {
          case 'EACCES':
            logger.error(`${bind} requires elevated privileges`);
            process.exit(1);
            break;
          case 'EADDRINUSE':
            logger.error(`${bind} is already in use`);
            process.exit(1);
            break;
          default:
            throw error;
        }
      });

      // Handle graceful shutdown
      process.on('SIGTERM', () => this.gracefulShutdown('SIGTERM'));
      process.on('SIGINT', () => this.gracefulShutdown('SIGINT'));

      // Handle uncaught exceptions
      process.on('uncaughtException', (error) => {
        logger.error('💥 Uncaught Exception:', error);
        this.gracefulShutdown('uncaughtException');
      });

      process.on('unhandledRejection', (reason, promise) => {
        logger.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
        this.gracefulShutdown('unhandledRejection');
      });

    } catch (error) {
      logger.error('❌ Failed to start server:', error);
      process.exit(1);
    }
  }

  private async gracefulShutdown(signal: string): Promise<void> {
    logger.info(`🛑 Received ${signal}. Starting graceful shutdown...`);

    // Stop accepting new connections
    this.server.close(async () => {
      logger.info('📡 HTTP server closed');

      try {
        // Close WebSocket connections
        await this.wsServer.close();
        logger.info('🔌 WebSocket server closed');

        // Close Redis connection
        await redisClient.disconnect();
        logger.info('🔗 Redis connection closed');

        // Close database connections
        await closeDatabaseConnection();
        logger.info('🗄️ Database connections closed');

        logger.info('✅ Graceful shutdown completed');
        process.exit(0);
      } catch (error) {
        logger.error('❌ Error during graceful shutdown:', error);
        process.exit(1);
      }
    });

    // Force shutdown after 30 seconds
    setTimeout(() => {
      logger.error('❌ Graceful shutdown timeout. Forcing exit.');
      process.exit(1);
    }, 30000);
  }

  public getApp(): express.Application {
    return this.app;
  }

  public getServer(): any {
    return this.server;
  }

  public getWebSocketServer(): WebSocketServer {
    return this.wsServer;
  }
}

// Create and start server
const server = new Server();

// Start server if this file is run directly
if (require.main === module) {
  server.start().catch((error) => {
    logger.error('Failed to start server:', error);
    process.exit(1);
  });
}

export default server;