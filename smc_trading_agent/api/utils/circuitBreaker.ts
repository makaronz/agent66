/**
 * Enhanced Circuit Breaker Implementation for Trading Data Reliability
 * Provides fault tolerance with automatic recovery and monitoring
 */

export enum CircuitState {
  CLOSED = 'CLOSED',
  OPEN = 'OPEN',
  HALF_OPEN = 'HALF_OPEN'
}

export interface CircuitBreakerConfig {
  failureThreshold: number;
  resetTimeout: number;
  monitoringPeriod: number;
  halfOpenMaxCalls: number;
  name: string;
}

export interface CircuitMetrics {
  failures: number;
  successes: number;
  timeouts: number;
  lastFailureTime?: number;
  lastSuccessTime?: number;
  consecutiveFailures: number;
  state: CircuitState;
  responseTime: number[];
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failures = 0;
  private successes = 0;
  private timeouts = 0;
  private consecutiveFailures = 0;
  private lastFailureTime?: number;
  private lastSuccessTime?: number;
  private responseTime: number[] = [];
  private nextAttempt?: number;
  private halfOpenCalls = 0;

  constructor(private config: CircuitBreakerConfig) {}

  async execute<T>(operation: () => Promise<T>, timeoutMs: number = 5000): Promise<T> {
    const startTime = Date.now();

    // Check if circuit is open and should refuse execution
    if (this.state === CircuitState.OPEN && this.nextAttempt && Date.now() < this.nextAttempt) {
      throw new Error(`Circuit breaker '${this.config.name}' is OPEN. Refusing execution.`);
    }

    // Handle half-open state
    if (this.state === CircuitState.HALF_OPEN) {
      if (this.halfOpenCalls >= this.config.halfOpenMaxCalls) {
        throw new Error(`Circuit breaker '${this.config.name}' is HALF_OPEN with max calls reached.`);
      }
      this.halfOpenCalls++;
    }

    try {
      // Execute with timeout
      const result = await Promise.race([
        operation(),
        new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('Operation timeout')), timeoutMs);
        })
      ]);

      const responseTime = Date.now() - startTime;
      this.onSuccess(responseTime);
      return result;

    } catch (error) {
      const responseTime = Date.now() - startTime;
      this.onFailure(error instanceof Error ? error : new Error(String(error)), responseTime);
      throw error;
    }
  }

  private onSuccess(responseTime: number): void {
    this.successes++;
    this.lastSuccessTime = Date.now();
    this.responseTime.push(responseTime);

    // Keep only last 100 response times for memory efficiency
    if (this.responseTime.length > 100) {
      this.responseTime = this.responseTime.slice(-100);
    }

    // Reset on first success in half-open state
    if (this.state === CircuitState.HALF_OPEN) {
      this.reset();
    }
  }

  private onFailure(error: Error, responseTime: number): void {
    this.failures++;
    this.consecutiveFailures++;
    this.lastFailureTime = Date.now();

    // Track timeouts separately
    if (error.message.includes('timeout')) {
      this.timeouts++;
    }

    // Open circuit if threshold exceeded
    if (this.state === CircuitState.CLOSED &&
        this.consecutiveFailures >= this.config.failureThreshold) {
      this.open();
    } else if (this.state === CircuitState.HALF_OPEN) {
      // Reopen if failure in half-open state
      this.open();
    }
  }

  private open(): void {
    this.state = CircuitState.OPEN;
    this.nextAttempt = Date.now() + this.config.resetTimeout;
    console.warn(`Circuit breaker '${this.config.name}' opened due to ${this.consecutiveFailures} consecutive failures`);
  }

  private reset(): void {
    this.state = CircuitState.CLOSED;
    this.consecutiveFailures = 0;
    this.halfOpenCalls = 0;
    this.nextAttempt = undefined;
    console.info(`Circuit breaker '${this.config.name}' reset to CLOSED state`);
  }

  // Force circuit to half-open for testing
  forceHalfOpen(): void {
    this.state = CircuitState.HALF_OPEN;
    this.halfOpenCalls = 0;
  }

  getMetrics(): CircuitMetrics {
    return {
      failures: this.failures,
      successes: this.successes,
      timeouts: this.timeouts,
      lastFailureTime: this.lastFailureTime,
      lastSuccessTime: this.lastSuccessTime,
      consecutiveFailures: this.consecutiveFailures,
      state: this.state,
      responseTime: [...this.responseTime]
    };
  }

  getState(): CircuitState {
    return this.state;
  }

  getName(): string {
    return this.config.name;
  }

  // Calculate success rate
  getSuccessRate(): number {
    const total = this.successes + this.failures;
    return total > 0 ? (this.successes / total) * 100 : 100;
  }

  // Calculate average response time
  getAverageResponseTime(): number {
    if (this.responseTime.length === 0) return 0;
    return this.responseTime.reduce((a, b) => a + b, 0) / this.responseTime.length;
  }

  // Get time until next attempt (when circuit is open)
  getTimeToNextAttempt(): number | null {
    if (!this.nextAttempt) return null;
    const now = Date.now();
    return Math.max(0, this.nextAttempt - now);
  }
}

// Circuit breaker registry for managing multiple breakers
export class CircuitBreakerRegistry {
  private static instance: CircuitBreakerRegistry;
  private breakers: Map<string, CircuitBreaker> = new Map();

  static getInstance(): CircuitBreakerRegistry {
    if (!CircuitBreakerRegistry.instance) {
      CircuitBreakerRegistry.instance = new CircuitBreakerRegistry();
    }
    return CircuitBreakerRegistry.instance;
  }

  create(name: string, config: Partial<CircuitBreakerConfig> = {}): CircuitBreaker {
    const defaultConfig: CircuitBreakerConfig = {
      failureThreshold: 5,
      resetTimeout: 60000, // 1 minute
      monitoringPeriod: 10000, // 10 seconds
      halfOpenMaxCalls: 3,
      name,
      ...config
    };

    const breaker = new CircuitBreaker(defaultConfig);
    this.breakers.set(name, breaker);
    return breaker;
  }

  get(name: string): CircuitBreaker | undefined {
    return this.breakers.get(name);
  }

  getAll(): Map<string, CircuitBreaker> {
    return new Map(this.breakers);
  }

  getMetrics(): Record<string, CircuitMetrics> {
    const metrics: Record<string, CircuitMetrics> = {};
    for (const [name, breaker] of this.breakers) {
      metrics[name] = breaker.getMetrics();
    }
    return metrics;
  }

  // Health check for all breakers
  getHealthStatus(): { healthy: string[]; unhealthy: string[]; warnings: string[] } {
    const healthy: string[] = [];
    const unhealthy: string[] = [];
    const warnings: string[] = [];

    for (const [name, breaker] of this.breakers) {
      const metrics = breaker.getMetrics();
      const successRate = breaker.getSuccessRate();

      if (metrics.state === CircuitState.OPEN) {
        unhealthy.push(name);
      } else if (successRate < 80) {
        warnings.push(name);
      } else {
        healthy.push(name);
      }
    }

    return { healthy, unhealthy, warnings };
  }
}

// Enhanced retry handler with exponential backoff
export class RetryHandler {
  static async executeWithRetry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000,
    backoffFactor: number = 2,
    circuitBreaker?: CircuitBreaker
  ): Promise<T> {
    let lastError: Error;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        if (circuitBreaker) {
          return await circuitBreaker.execute(operation);
        }
        return await operation();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        if (attempt === maxRetries) {
          console.error(`Operation failed after ${maxRetries + 1} attempts:`, lastError.message);
          throw lastError;
        }

        const delay = baseDelay * Math.pow(backoffFactor, attempt);
        console.warn(`Attempt ${attempt + 1} failed, retrying in ${delay}ms:`, lastError.message);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError!;
  }
}

// Default circuit breaker configurations for different operations
export const DEFAULT_CIRCUIT_CONFIGS = {
  WEBSOCKET_CONNECTION: {
    failureThreshold: 3,
    resetTimeout: 30000, // 30 seconds
    monitoringPeriod: 5000,
    halfOpenMaxCalls: 2,
  },
  API_REQUEST: {
    failureThreshold: 5,
    resetTimeout: 60000, // 1 minute
    monitoringPeriod: 10000,
    halfOpenMaxCalls: 3,
  },
  DATA_VALIDATION: {
    failureThreshold: 10,
    resetTimeout: 120000, // 2 minutes
    monitoringPeriod: 15000,
    halfOpenMaxCalls: 5,
  }
} as const;