import { PrismaClient } from '@prisma/client';
import { logger } from '../utils/logger';

// Global prisma instance with optimized connection pooling
let prisma: PrismaClient;

// Connection pool configuration
const prismaConfig = {
  // Connection pool settings
  datasources: {
    db: {
      url: process.env.DATABASE_URL,
    },
  },
  // Connection pooling optimization
  log: process.env.NODE_ENV === 'development' ? [
    {
      emit: 'event',
      level: 'query',
    },
    {
      emit: 'event',
      level: 'error',
    },
    {
      emit: 'event',
      level: 'warn',
    },
  ] : [
    {
      emit: 'event',
      level: 'error',
    },
    {
      emit: 'event',
      level: 'warn',
    },
  ],
};

// Performance monitoring metrics
let connectionMetrics = {
  totalQueries: 0,
  slowQueries: 0,
  averageQueryTime: 0,
  connectionPoolSize: 0,
};

// Initialize database connection with enhanced pooling
export const initializeDatabase = async (): Promise<void> => {
  try {
    if (!prisma) {
      prisma = new PrismaClient({
        ...prismaConfig,
        // Enhanced connection pooling for performance
        __internal: {
          engine: {
            // Connection pool settings
            connectionLimit: Math.max(10, Number(process.env.DATABASE_POOL_SIZE) || 20),
            poolTimeout: 10000, // 10 seconds
            connectTimeout: 10000, // 10 seconds
            // Query optimization
            queryTimeout: 30000, // 30 seconds
            // Batch settings for better performance
            batchQueries: true,
            // Enable prepared statements for repeated queries
            preparedStatements: true,
          },
        },
      });

      // Log database events with performance monitoring
      prisma.$on('query', (e) => {
        connectionMetrics.totalQueries++;

        // Track slow queries (>1000ms)
        if (e.duration > 1000) {
          connectionMetrics.slowQueries++;
          logger.warn('🐌 Slow Query Detected:', {
            query: e.query,
            params: e.params,
            duration: `${e.duration}ms`,
            target: e.target,
          });
        } else if (process.env.NODE_ENV === 'development') {
          logger.debug('Database Query:', {
            query: e.query,
            params: e.params,
            duration: `${e.duration}ms`,
            target: e.target,
          });
        }

        // Update average query time
        connectionMetrics.averageQueryTime =
          (connectionMetrics.averageQueryTime * (connectionMetrics.totalQueries - 1) + e.duration) /
          connectionMetrics.totalQueries;
      });

      prisma.$on('error', (e) => {
        logger.error('❌ Database Error:', {
          message: e.message,
          target: e.target,
        });
      });

      prisma.$on('warn', (e) => {
        logger.warn('⚠️ Database Warning:', {
          message: e.message,
          target: e.target,
        });
      });

      // Test the connection with performance metrics
      const startTime = Date.now();
      await prisma.$connect();
      const connectionTime = Date.now() - startTime;

      logger.info('✅ Database connected successfully', {
        connectionTime: `${connectionTime}ms`,
        poolSize: process.env.DATABASE_POOL_SIZE || 20,
      });

      // Log connection metrics every 5 minutes in production
      if (process.env.NODE_ENV === 'production') {
        setInterval(() => {
          logger.info('📊 Database Performance Metrics:', connectionMetrics);
        }, 300000); // 5 minutes
      }
    }
  } catch (error) {
    logger.error('❌ Failed to connect to database:', error);
    throw error;
  }
};

// Get prisma client instance
export const getPrismaClient = (): PrismaClient => {
  if (!prisma) {
    throw new Error('Database not initialized. Call initializeDatabase() first.');
  }
  return prisma;
};

// Close database connection
export const closeDatabaseConnection = async (): Promise<void> => {
  try {
    if (prisma) {
      await prisma.$disconnect();
      logger.info('✅ Database connection closed');
    }
  } catch (error) {
    logger.error('❌ Error closing database connection:', error);
    throw error;
  }
};

// Export prisma client for use in modules
export { prisma };

// Enhanced health check for database with performance metrics
export const checkDatabaseHealth = async (): Promise<{
  status: string;
  responseTime: number;
  metrics: typeof connectionMetrics;
  poolInfo?: any;
}> => {
  const startTime = Date.now();

  try {
    // Simple connection test
    await prisma.$queryRaw`SELECT 1`;
    const responseTime = Date.now() - startTime;

    // Get connection pool information (if available)
    let poolInfo;
    try {
      // This query works for PostgreSQL
      poolInfo = await prisma.$queryRaw`
        SELECT
          count(*) as active_connections,
          count(*) FILTER (WHERE state = 'active') as active_queries
        FROM pg_stat_activity
        WHERE datname = current_database()
      `;
    } catch (e) {
      // Pool info not available, continue without it
    }

    return {
      status: responseTime < 100 ? 'healthy' : responseTime < 500 ? 'degraded' : 'unhealthy',
      responseTime,
      metrics: connectionMetrics,
      poolInfo,
    };
  } catch (error) {
    logger.error('❌ Database health check failed:', error);
    return {
      status: 'unhealthy',
      responseTime: Date.now() - startTime,
      metrics: connectionMetrics,
    };
  }
};

// Enhanced transaction helper with timeout and retry logic
export const withTransaction = async <T>(
  callback: (tx: PrismaClient) => Promise<T>,
  options: {
    timeout?: number;
    maxRetries?: number;
    isolationLevel?: any;
  } = {}
): Promise<T> => {
  const { timeout = 30000, maxRetries = 3 } = options;

  let lastError: Error;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await Promise.race([
        prisma.$transaction(callback),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Transaction timeout')), timeout)
        )
      ]);
    } catch (error) {
      lastError = error as Error;

      if (attempt === maxRetries) {
        logger.error('❌ Transaction failed after retries:', error);
        throw lastError;
      }

      // Exponential backoff
      const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
      logger.warn(`⚠️ Transaction attempt ${attempt + 1} failed, retrying in ${delay}ms:`, error);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError!;
};

// Get connection metrics for monitoring
export const getConnectionMetrics = () => connectionMetrics;

// Reset connection metrics (useful for testing)
export const resetConnectionMetrics = () => {
  connectionMetrics = {
    totalQueries: 0,
    slowQueries: 0,
    averageQueryTime: 0,
    connectionPoolSize: 0,
  };
};