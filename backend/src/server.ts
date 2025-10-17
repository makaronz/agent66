import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { config } from './config';
import { logger } from './utils/logger';
import { errorHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/requestLogger';
import { authMiddleware } from './middleware/auth';
import { healthRouter } from './routes/health';
import { authRouter } from './routes/auth';
import { projectsRouter } from './routes/projects';
import { timeEntriesRouter } from './routes/time-entries';
import { crewRouter } from './routes/crew';
import { reportsRouter } from './routes/reports';
import { metricsRouter } from './routes/metrics';
import { setupSwagger } from './utils/swagger';
import { initializeDatabase } from './database/connection';
import { WebSocketServer } from './websocket/server';

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
    // Security middleware
    if (config.security.helmet.enabled) {
      this.app.use(helmet(config.security.helmet.contentSecurityPolicy));
    }

    // CORS middleware
    this.app.use(cors(config.cors));

    // Compression middleware
    this.app.use(compression());

    // Request logging
    this.app.use(requestLogger);

    // Body parsing middleware
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Rate limiting
    const limiter = rateLimit(config.rateLimit);
    this.app.use('/api/', limiter);

    // Health check endpoint (no rate limiting)
    this.app.use('/health', healthRouter);

    // Metrics endpoint (no rate limiting for monitoring)
    this.app.use('/metrics', metricsRouter);
  }

  private initializeRoutes(): void {
    // API routes
    this.app.use('/api/auth', authRouter);
    this.app.use('/api/projects', authMiddleware, projectsRouter);
    this.app.use('/api/time-entries', authMiddleware, timeEntriesRouter);
    this.app.use('/api/crew', authMiddleware, crewRouter);
    this.app.use('/api/reports', authMiddleware, reportsRouter);

    // API documentation
    if (config.app.environment !== 'production') {
      setupSwagger(this.app);
    }

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.originalUrl} not found`,
        timestamp: new Date().toISOString(),
      });
    });
  }

  private initializeErrorHandling(): void {
    // Error handling middleware (must be last)
    this.app.use(errorHandler);
  }

  public async start(): Promise<void> {
    try {
      // Initialize database connections
      await initializeDatabase();

      // Start the HTTP server
      this.server.listen(config.app.port, config.app.host, () => {
        logger.info(`🚀 Server started successfully`);
        logger.info(`📍 Environment: ${config.app.environment}`);
        logger.info(`🌐 Server: http://${config.app.host}:${config.app.port}`);
        logger.info(`📚 API Docs: http://${config.app.host}:${config.app.port}/api-docs`);
        logger.info(`📊 Metrics: http://${config.app.host}:${config.app.port}/metrics`);
        logger.info(`🔧 WebSocket: ws://${config.app.host}:${config.app.port}/ws`);
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

    } catch (error) {
      logger.error('Failed to start server:', error);
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

        // Close database connections
        await this.closeDatabaseConnections();
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

  private async closeDatabaseConnections(): Promise<void> {
    // Implementation for closing database connections
    // This would close PostgreSQL, MongoDB, and Redis connections
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