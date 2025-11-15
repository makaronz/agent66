/**
 * Rate Limiter for Exchange API Calls
 * Prevents API rate limit violations and optimizes request timing
 */

export interface RateLimitConfig {
  requestsPerSecond: number;
  requestsPerMinute: number;
  requestsPerHour: number;
  burstLimit: number;
  strategy: 'token-bucket' | 'sliding-window' | 'fixed-window';
}

export interface RateLimitStatus {
  allowed: boolean;
  waitTime: number;
  requestsRemaining: number;
  resetTime: number;
  limitExceeded: boolean;
}

interface TokenBucket {
  tokens: number;
  lastRefill: number;
}

export class RateLimiter {
  private tokenBucket: Map<string, TokenBucket> = new Map();
  private slidingWindow: Map<string, number[]> = new Map();
  private fixedWindowCounters: Map<string, { count: number; windowStart: number }> = new Map();

  constructor(private config: RateLimitConfig) {}

  // Check if request is allowed under rate limits
  async checkLimit(identifier: string = 'default'): Promise<RateLimitStatus> {
    switch (this.config.strategy) {
      case 'token-bucket':
        return this.checkTokenBucket(identifier);
      case 'sliding-window':
        return this.checkSlidingWindow(identifier);
      case 'fixed-window':
        return this.checkFixedWindow(identifier);
      default:
        throw new Error(`Unknown rate limiting strategy: ${this.config.strategy}`);
    }
  }

  // Wait until request is allowed (blocking)
  async waitForSlot(identifier: string = 'default'): Promise<void> {
    const status = await this.checkLimit(identifier);
    if (!status.allowed) {
      if (status.waitTime > 0) {
        await new Promise(resolve => setTimeout(resolve, status.waitTime));
      }
      return this.waitForSlot(identifier);
    }
  }

  private checkTokenBucket(identifier: string): RateLimitStatus {
    const now = Date.now();
    const bucket = this.tokenBucket.get(identifier) || {
      tokens: this.config.burstLimit,
      lastRefill: now
    };

    // Refill tokens based on time elapsed
    const timeElapsed = now - bucket.lastRefill;
    const tokensToAdd = (timeElapsed / 1000) * this.config.requestsPerSecond;
    bucket.tokens = Math.min(this.config.burstLimit, bucket.tokens + tokensToAdd);
    bucket.lastRefill = now;

    // Check if we have enough tokens
    const allowed = bucket.tokens >= 1;
    const requestsRemaining = Math.floor(bucket.tokens);

    if (allowed) {
      bucket.tokens -= 1;
    }

    this.tokenBucket.set(identifier, bucket);

    return {
      allowed,
      waitTime: allowed ? 0 : Math.ceil(1000 / this.config.requestsPerSecond),
      requestsRemaining,
      resetTime: now + 60000, // 1 minute from now
      limitExceeded: !allowed
    };
  }

  private checkSlidingWindow(identifier: string): RateLimitStatus {
    const now = Date.now();
    const windowMs = 60000; // 1 minute window
    const requests = this.slidingWindow.get(identifier) || [];

    // Remove requests outside the sliding window
    const validRequests = requests.filter(timestamp => now - timestamp < windowMs);
    this.slidingWindow.set(identifier, validRequests);

    const requestsInWindow = validRequests.length;
    const allowed = requestsInWindow < this.config.requestsPerMinute;

    return {
      allowed,
      waitTime: allowed ? 0 : Math.max(0, validRequests[0] + windowMs - now),
      requestsRemaining: Math.max(0, this.config.requestsPerMinute - requestsInWindow),
      resetTime: now + windowMs,
      limitExceeded: !allowed
    };
  }

  private checkFixedWindow(identifier: string): RateLimitStatus {
    const now = Date.now();
    const windowMs = 60000; // 1 minute window
    const counter = this.fixedWindowCounters.get(identifier);

    if (!counter || now - counter.windowStart >= windowMs) {
      // New window
      this.fixedWindowCounters.set(identifier, {
        count: 1,
        windowStart: now
      });

      return {
        allowed: true,
        waitTime: 0,
        requestsRemaining: this.config.requestsPerMinute - 1,
        resetTime: now + windowMs,
        limitExceeded: false
      };
    }

    // Same window
    const allowed = counter.count < this.config.requestsPerMinute;
    if (allowed) {
      counter.count++;
    }

    this.fixedWindowCounters.set(identifier, counter);

    return {
      allowed,
      waitTime: allowed ? 0 : windowMs - (now - counter.windowStart),
      requestsRemaining: Math.max(0, this.config.requestsPerMinute - counter.count),
      resetTime: counter.windowStart + windowMs,
      limitExceeded: !allowed
    };
  }

  // Get current status for all rate limiters
  getAllStatuses(): Record<string, RateLimitStatus> {
    const statuses: Record<string, RateLimitStatus> = {};
    const allIdentifiers = new Set([
      ...this.tokenBucket.keys(),
      ...this.slidingWindow.keys(),
      ...this.fixedWindowCounters.keys()
    ]);

    for (const identifier of allIdentifiers) {
      statuses[identifier] = this.checkLimit(identifier);
    }

    return statuses;
  }

  // Reset rate limiter for specific identifier
  reset(identifier: string): void {
    this.tokenBucket.delete(identifier);
    this.slidingWindow.delete(identifier);
    this.fixedWindowCounters.delete(identifier);
  }

  // Reset all rate limiters
  resetAll(): void {
    this.tokenBucket.clear();
    this.slidingWindow.clear();
    this.fixedWindowCounters.clear();
  }
}

// Exchange-specific rate limit configurations
export const EXCHANGE_RATE_LIMITS = {
  BYBIT: {
    WEBSOCKET: {
      requestsPerSecond: 5,
      requestsPerMinute: 100,
      requestsPerHour: 6000,
      burstLimit: 10,
      strategy: 'token-bucket' as const
    },
    REST_API: {
      requestsPerSecond: 10,
      requestsPerMinute: 600,
      requestsPerHour: 30000,
      burstLimit: 20,
      strategy: 'sliding-window' as const
    }
  },
  BINANCE: {
    WEBSOCKET: {
      requestsPerSecond: 10,
      requestsPerMinute: 300,
      requestsPerHour: 12000,
      burstLimit: 20,
      strategy: 'token-bucket' as const
    },
    REST_API: {
      requestsPerSecond: 20,
      requestsPerMinute: 1200,
      requestsPerHour: 100000,
      burstLimit: 50,
      strategy: 'sliding-window' as const
    }
  }
} as const;

// Rate limiter manager for multiple exchanges
export class RateLimiterManager {
  private static instance: RateLimiterManager;
  private limiters: Map<string, RateLimiter> = new Map();

  static getInstance(): RateLimiterManager {
    if (!RateLimiterManager.instance) {
      RateLimiterManager.instance = new RateLimiterManager();
    }
    return RateLimiterManager.instance;
  }

  createLimiter(name: string, config: RateLimitConfig): RateLimiter {
    const limiter = new RateLimiter(config);
    this.limiters.set(name, limiter);
    return limiter;
  }

  getLimiter(name: string): RateLimiter | undefined {
    return this.limiters.get(name);
  }

  // Initialize with exchange-specific configurations
  initializeExchangeLimiters(): void {
    for (const [exchange, configs] of Object.entries(EXCHANGE_RATE_LIMITS)) {
      for (const [type, config] of Object.entries(configs)) {
        const name = `${exchange}_${type}`;
        this.createLimiter(name, config);
      }
    }
  }

  // Get all rate limiter statuses
  getAllStatuses(): Record<string, Record<string, RateLimitStatus>> {
    const statuses: Record<string, Record<string, RateLimitStatus>> = {};

    for (const [name, limiter] of this.limiters) {
      statuses[name] = limiter.getAllStatuses();
    }

    return statuses;
  }

  // Health check for all rate limiters
  getHealthStatus(): { healthy: string[]; warnings: string[] } {
    const healthy: string[] = [];
    const warnings: string[] = [];

    for (const [name, limiter] of this.limiters) {
      const statuses = limiter.getAllStatuses();
      let hasIssues = false;

      for (const status of Object.values(statuses)) {
        if (status.limitExceeded || status.requestsRemaining === 0) {
          hasIssues = true;
          break;
        }
      }

      if (hasIssues) {
        warnings.push(name);
      } else {
        healthy.push(name);
      }
    }

    return { healthy, warnings };
  }
}

// Enhanced retry handler with rate limiting
export class RateLimitedRetryHandler {
  static async executeWithRetryAndRateLimit<T>(
    operation: () => Promise<T>,
    rateLimiterName: string,
    identifier: string = 'default',
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<T> {
    const manager = RateLimiterManager.getInstance();
    const rateLimiter = manager.getLimiter(rateLimiterName);

    if (!rateLimiter) {
      throw new Error(`Rate limiter not found: ${rateLimiterName}`);
    }

    let lastError: Error;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // Wait for rate limit slot
        await rateLimiter.waitForSlot(identifier);

        // Execute operation
        return await operation();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        if (attempt === maxRetries) {
          console.error(`Operation failed after ${maxRetries + 1} attempts:`, lastError.message);
          throw lastError;
        }

        const delay = baseDelay * Math.pow(2, attempt);
        console.warn(`Attempt ${attempt + 1} failed, retrying in ${delay}ms:`, lastError.message);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError!;
  }
}