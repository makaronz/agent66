import Redis from 'ioredis';
import { logger } from '../utils/logger';

// Redis client with connection pooling and performance optimization
class RedisClient {
  private client: Redis;
  private isConnected: boolean = false;

  constructor() {
    this.client = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD,
      db: parseInt(process.env.REDIS_DB || '0'),

      // Connection pooling settings
      maxRetriesPerRequest: 3,
      retryDelayOnFailover: 100,
      enableOfflineQueue: false,

      // Performance optimizations
      lazyConnect: true,
      keepAlive: 30000,
      connectTimeout: 10000,
      commandTimeout: 5000,

      // Connection pool settings
      family: 4,

      // Connection monitoring
      reconnectOnError: (err) => {
        const targetError = 'READONLY';
        return err.message.includes(targetError);
      },
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.client.on('connect', () => {
      logger.info('🔗 Redis connected successfully');
      this.isConnected = true;
    });

    this.client.on('ready', () => {
      logger.info('✅ Redis ready for commands');
    });

    this.client.on('error', (error) => {
      logger.error('❌ Redis connection error:', error);
      this.isConnected = false;
    });

    this.client.on('close', () => {
      logger.warn('⚠️ Redis connection closed');
      this.isConnected = false;
    });

    this.client.on('reconnecting', () => {
      logger.info('🔄 Redis reconnecting...');
    });

    this.client.on('end', () => {
      logger.info('🔌 Redis connection ended');
      this.isConnected = false;
    });
  }

  async connect(): Promise<void> {
    try {
      if (!this.isConnected) {
        await this.client.connect();
      }
    } catch (error) {
      logger.error('❌ Failed to connect to Redis:', error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    try {
      if (this.isConnected) {
        await this.client.quit();
      }
    } catch (error) {
      logger.error('❌ Error disconnecting from Redis:', error);
      throw error;
    }
  }

  // Cache operations with performance monitoring
  async get(key: string): Promise<string | null> {
    const startTime = Date.now();
    try {
      if (!this.isConnected) {
        logger.warn('Redis not connected, skipping get operation');
        return null;
      }

      const result = await this.client.get(key);
      const duration = Date.now() - startTime;

      if (duration > 100) {
        logger.warn(`⚠️ Slow Redis GET operation: ${duration}ms for key: ${key}`);
      }

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error(`❌ Redis GET error after ${duration}ms:`, error);
      return null;
    }
  }

  async set(key: string, value: string, ttl?: number): Promise<void> {
    const startTime = Date.now();
    try {
      if (!this.isConnected) {
        logger.warn('Redis not connected, skipping set operation');
        return;
      }

      if (ttl) {
        await this.client.setex(key, ttl, value);
      } else {
        await this.client.set(key, value);
      }

      const duration = Date.now() - startTime;
      if (duration > 100) {
        logger.warn(`⚠️ Slow Redis SET operation: ${duration}ms for key: ${key}`);
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error(`❌ Redis SET error after ${duration}ms:`, error);
    }
  }

  async del(key: string): Promise<void> {
    const startTime = Date.now();
    try {
      if (!this.isConnected) {
        return;
      }

      await this.client.del(key);
      const duration = Date.now() - startTime;
      if (duration > 100) {
        logger.warn(`⚠️ Slow Redis DEL operation: ${duration}ms for key: ${key}`);
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error(`❌ Redis DEL error after ${duration}ms:`, error);
    }
  }

  async exists(key: string): Promise<boolean> {
    try {
      if (!this.isConnected) {
        return false;
      }

      const result = await this.client.exists(key);
      return result === 1;
    } catch (error) {
      logger.error('❌ Redis EXISTS error:', error);
      return false;
    }
  }

  async expire(key: string, ttl: number): Promise<void> {
    try {
      if (!this.isConnected) {
        return;
      }

      await this.client.expire(key, ttl);
    } catch (error) {
      logger.error('❌ Redis EXPIRE error:', error);
    }
  }

  // Advanced cache operations
  async mget(keys: string[]): Promise<(string | null)[]> {
    const startTime = Date.now();
    try {
      if (!this.isConnected) {
        return keys.map(() => null);
      }

      const result = await this.client.mget(...keys);
      const duration = Date.now() - startTime;

      if (duration > 200) {
        logger.warn(`⚠️ Slow Redis MGET operation: ${duration}ms for ${keys.length} keys`);
      }

      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error(`❌ Redis MGET error after ${duration}ms:`, error);
      return keys.map(() => null);
    }
  }

  async mset(keyValuePairs: Record<string, string>, ttl?: number): Promise<void> {
    const startTime = Date.now();
    try {
      if (!this.isConnected) {
        return;
      }

      const keys = Object.keys(keyValuePairs);
      const values = Object.values(keyValuePairs);

      if (ttl) {
        // For MSET with TTL, we need to use a pipeline
        const pipeline = this.client.pipeline();
        for (let i = 0; i < keys.length; i++) {
          pipeline.setex(keys[i], ttl, values[i]);
        }
        await pipeline.exec();
      } else {
        await this.client.mset(...keys.flatMap((key, i) => [key, values[i]]));
      }

      const duration = Date.now() - startTime;
      if (duration > 200) {
        logger.warn(`⚠️ Slow Redis MSET operation: ${duration}ms for ${keys.length} keys`);
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.error(`❌ Redis MSET error after ${duration}ms:`, error);
    }
  }

  // Cache pattern operations
  async getPattern(pattern: string): Promise<string[]> {
    try {
      if (!this.isConnected) {
        return [];
      }

      const keys = await this.client.keys(pattern);
      return keys;
    } catch (error) {
      logger.error('❌ Redis KEYS error:', error);
      return [];
    }
  }

  async deletePattern(pattern: string): Promise<number> {
    try {
      if (!this.isConnected) {
        return 0;
      }

      const keys = await this.client.keys(pattern);
      if (keys.length === 0) {
        return 0;
      }

      const result = await this.client.del(...keys);
      return result;
    } catch (error) {
      logger.error('❌ Redis delete pattern error:', error);
      return 0;
    }
  }

  // Cache statistics and health monitoring
  async getStats(): Promise<any> {
    try {
      if (!this.isConnected) {
        return null;
      }

      const info = await this.client.info('memory');
      const keyspace = await this.client.info('keyspace');
      const stats = await this.client.info('stats');

      return {
        memory: info,
        keyspace,
        stats,
        connected: this.isConnected,
      };
    } catch (error) {
      logger.error('❌ Redis stats error:', error);
      return null;
    }
  }

  async ping(): Promise<boolean> {
    try {
      if (!this.isConnected) {
        return false;
      }

      const result = await this.client.ping();
      return result === 'PONG';
    } catch (error) {
      logger.error('❌ Redis PING error:', error);
      return false;
    }
  }

  getClient(): Redis {
    return this.client;
  }

  isRedisConnected(): boolean {
    return this.isConnected;
  }
}

// Singleton Redis instance
const redisClient = new RedisClient();

export { redisClient };

// Cache helper functions
export const cacheHelpers = {
  // Cache API responses
  async cacheApiResponse(key: string, data: any, ttl: number = 300): Promise<void> {
    await redisClient.set(key, JSON.stringify(data), ttl);
  },

  // Get cached API response
  async getCachedApiResponse(key: string): Promise<any | null> {
    const cached = await redisClient.get(key);
    if (cached) {
      try {
        return JSON.parse(cached);
      } catch (error) {
        logger.error('Error parsing cached JSON:', error);
        return null;
      }
    }
    return null;
  },

  // Cache database query results
  async cacheQueryResult(queryKey: string, result: any, ttl: number = 600): Promise<void> {
    await redisClient.set(`query:${queryKey}`, JSON.stringify(result), ttl);
  },

  // Get cached query result
  async getCachedQueryResult(queryKey: string): Promise<any | null> {
    const cached = await redisClient.get(`query:${queryKey}`);
    if (cached) {
      try {
        return JSON.parse(cached);
      } catch (error) {
        logger.error('Error parsing cached query result:', error);
        return null;
      }
    }
    return null;
  },

  // Invalidate cache patterns
  async invalidateCachePattern(pattern: string): Promise<void> {
    const deletedCount = await redisClient.deletePattern(pattern);
    if (deletedCount > 0) {
      logger.info(`🗑️ Invalidated ${deletedCount} cache keys matching pattern: ${pattern}`);
    }
  },

  // Cache warming for frequently accessed data
  async warmCache(cacheData: Record<string, { data: any; ttl: number }>): Promise<void> {
    const entries = Object.entries(cacheData);
    if (entries.length === 0) return;

    await redisClient.mset(
      Object.fromEntries(
        entries.map(([key, { data }]) => [key, JSON.stringify(data)])
      )
    );

    // Set TTL for each key
    const ttlPromises = entries.map(([key, { ttl }]) =>
      redisClient.expire(key, ttl)
    );

    await Promise.all(ttlPromises);

    logger.info(`🔥 Warmed cache with ${entries.length} entries`);
  },
};

export default redisClient;