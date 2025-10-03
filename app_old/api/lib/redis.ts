/**
 * Redis client configuration with development mode support
 * Handles graceful degradation when Redis is unavailable
 */

import Redis from 'ioredis';

// Redis client instance
export const redis = process.env.REDIS_ENABLED === 'false'
  ? null
  : new Redis(process.env.REDIS_URL ?? 'redis://127.0.0.1:6379', {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD,
      lazyConnect: true,
      enableOfflineQueue: false,
      maxRetriesPerRequest: null,
      retryStrategy: (times) => {
        // Exponential backoff with max 5 seconds
        return Math.min(1000 * times, 5000);
      },
      connectTimeout: 10000,
      commandTimeout: 5000,
    });

// Handle Redis connection errors gracefully in development
if (redis) {
  redis.on('error', (e) => {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('[redis] dev connection problem:', e.message);
    } else {
      console.error('[redis] connection error:', e.message);
    }
  });

  redis.on('connect', () => {
    console.log('[redis] connected successfully');
  });

  redis.on('ready', () => {
    console.log('[redis] ready for commands');
  });

  redis.on('close', () => {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('[redis] connection closed');
    }
  });

  // Attempt connection but don't crash the process if it fails
  redis.connect().catch((error) => {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('[redis] Failed to connect in development mode - continuing without Redis:', error.message);
    } else {
      console.error('[redis] Failed to connect:', error.message);
    }
  });
} else {
  console.warn('[redis] Redis is disabled in development mode');
}

/**
 * Safe Redis operations that handle null redis client
 */
export const safeRedisGet = async (key: string): Promise<string | null> => {
  if (!redis) {
    console.warn('[redis] GET operation skipped - Redis disabled');
    return null;
  }
  
  try {
    return await redis.get(key);
  } catch (error) {
    console.warn('[redis] GET operation failed:', error);
    return null;
  }
};

export const safeRedisSet = async (key: string, value: string, ttl?: number): Promise<boolean> => {
  if (!redis) {
    console.warn('[redis] SET operation skipped - Redis disabled');
    return false;
  }
  
  try {
    if (ttl) {
      await redis.setex(key, ttl, value);
    } else {
      await redis.set(key, value);
    }
    return true;
  } catch (error) {
    console.warn('[redis] SET operation failed:', error);
    return false;
  }
};

export const safeRedisDel = async (key: string): Promise<boolean> => {
  if (!redis) {
    console.warn('[redis] DEL operation skipped - Redis disabled');
    return false;
  }
  
  try {
    await redis.del(key);
    return true;
  } catch (error) {
    console.warn('[redis] DEL operation failed:', error);
    return false;
  }
};

/**
 * Check if Redis is available and connected
 */
export const isRedisAvailable = (): boolean => {
  return redis !== null && redis.status === 'ready';
};

/**
 * Gracefully close Redis connection
 */
export const closeRedis = async (): Promise<void> => {
  if (redis) {
    try {
      await redis.quit();
      console.log('[redis] connection closed gracefully');
    } catch (error) {
      console.warn('[redis] error during graceful shutdown:', error);
    }
  }
};

export default redis;