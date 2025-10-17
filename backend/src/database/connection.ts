import { PrismaClient } from '@prisma/client';
import { logger } from '../utils/logger';

// Global prisma instance
let prisma: PrismaClient;

// Initialize database connection
export const initializeDatabase = async (): Promise<void> => {
  try {
    if (!prisma) {
      prisma = new PrismaClient({
        log: [
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
            level: 'info',
          },
          {
            emit: 'event',
            level: 'warn',
          },
        ],
      });

      // Log database events
      prisma.$on('query', (e) => {
        logger.debug('Database Query:', {
          query: e.query,
          params: e.params,
          duration: `${e.duration}ms`,
        });
      });

      prisma.$on('error', (e) => {
        logger.error('Database Error:', e);
      });

      prisma.$on('info', (e) => {
        logger.info('Database Info:', e.message);
      });

      prisma.$on('warn', (e) => {
        logger.warn('Database Warning:', e.message);
      });

      // Test the connection
      await prisma.$connect();
      logger.info('✅ Database connected successfully');
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

// Health check for database
export const checkDatabaseHealth = async (): Promise<{ status: string; responseTime: number }> => {
  const startTime = Date.now();

  try {
    await prisma.$queryRaw`SELECT 1`;
    const responseTime = Date.now() - startTime;

    return {
      status: 'healthy',
      responseTime,
    };
  } catch (error) {
    logger.error('Database health check failed:', error);
    return {
      status: 'unhealthy',
      responseTime: Date.now() - startTime,
    };
  }
};

// Database transaction helper
export const withTransaction = async <T>(
  callback: (tx: PrismaClient) => Promise<T>
): Promise<T> => {
  return await prisma.$transaction(callback);
};