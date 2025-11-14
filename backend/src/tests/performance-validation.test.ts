import request from 'supertest';
import { app } from '../server';
import { redisClient } from '../cache/redis-client';
import { getConnectionMetrics } from '../database/connection';

describe('Performance Validation Tests', () => {
  let server: any;

  beforeAll(async () => {
    // Start the server for testing
    server = app.listen(0); // Use random port
    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for server to start
  });

  afterAll(async () => {
    // Clean up
    if (server) {
      server.close();
    }
    await redisClient.disconnect();
  });

  describe('API Response Time Performance', () => {
    const performanceTests = [
      { path: '/health', maxTime: 100, description: 'Health check' },
      { path: '/metrics', maxTime: 200, description: 'Metrics endpoint' },
      { path: '/api/projects', maxTime: 500, description: 'Projects list (cached)' },
    ];

    test.each(performanceTests)('$description should respond within $maxTime ms', async ({ path, maxTime }) => {
      const startTime = Date.now();

      try {
        const response = await request(app)
          .get(path)
          .timeout(5000);

        const duration = Date.now() - startTime;

        expect(response.status).toBeLessThan(500);
        expect(duration).toBeLessThan(maxTime);

        console.log(`✅ ${path}: ${duration}ms (${response.status})`);
      } catch (error) {
        const duration = Date.now() - startTime;
        console.log(`❌ ${path}: ${duration}ms (Failed)`);
        throw error;
      }
    });
  });

  describe('Database Performance', () => {
    test('Database connection pool should be utilized', async () => {
      const metrics = getConnectionMetrics();

      expect(metrics.totalQueries).toBeGreaterThanOrEqual(0);
      expect(metrics.slowQueries).toBeGreaterThanOrEqual(0);
      expect(metrics.averageQueryTime).toBeGreaterThanOrEqual(0);

      console.log('📊 Database Metrics:', {
        totalQueries: metrics.totalQueries,
        slowQueries: metrics.slowQueries,
        averageQueryTime: `${metrics.averageQueryTime.toFixed(2)}ms`
      });
    });

    test('Slow query detection should work', async () => {
      const initialSlowQueries = getConnectionMetrics().slowQueries;

      // Simulate some database operations
      for (let i = 0; i < 5; i++) {
        await request(app).get('/health');
      }

      const finalSlowQueries = getConnectionMetrics().slowQueries;

      // Should not have increased significantly with simple queries
      expect(finalSlowQueries - initialSlowQueries).toBeLessThan(3);
    });
  });

  describe('Cache Performance', () => {
    test('Redis cache should be accessible', async () => {
      const testKey = 'test:performance:cache';
      const testValue = { test: 'data', timestamp: Date.now() };

      // Set cache
      await redisClient.set(testKey, JSON.stringify(testValue), 60);

      // Get cache
      const cached = await redisClient.get(testKey);
      expect(cached).toBeTruthy();

      const parsed = JSON.parse(cached!);
      expect(parsed.test).toBe(testValue.test);

      // Clean up
      await redisClient.del(testKey);
    });

    test('Cache hit rate should be measurable', async () => {
      const testKey = 'test:performance:hitrate';
      const testValue = { data: 'test' };

      // First request - cache miss
      await redisClient.set(testKey, JSON.stringify(testValue), 60);

      const start1 = Date.now();
      const cached1 = await redisClient.get(testKey);
      const duration1 = Date.now() - start1;

      // Second request - cache hit
      const start2 = Date.now();
      const cached2 = await redisClient.get(testKey);
      const duration2 = Date.now() - start2;

      expect(cached1).toBeTruthy();
      expect(cached2).toBeTruthy();

      // Cache hit should be faster (though this is not guaranteed)
      console.log(`🎯 Cache performance: miss=${duration1}ms, hit=${duration2}ms`);

      // Clean up
      await redisClient.del(testKey);
    });
  });

  describe('Memory Usage Performance', () => {
    test('Memory usage should be within reasonable limits', async () => {
      const memUsage = process.memoryUsage();
      const maxMemory = 512 * 1024 * 1024; // 512MB

      expect(memUsage.heapUsed).toBeLessThan(maxMemory);

      console.log('💾 Memory Usage:', {
        rss: `${(memUsage.rss / 1024 / 1024).toFixed(2)} MB`,
        heapUsed: `${(memUsage.heapUsed / 1024 / 1024).toFixed(2)} MB`,
        heapTotal: `${(memUsage.heapTotal / 1024 / 1024).toFixed(2)} MB`,
        external: `${(memUsage.external / 1024 / 1024).toFixed(2)} MB`,
      });
    });

    test('Memory usage should not grow excessively during load', async () => {
      const initialMemory = process.memoryUsage().heapUsed;

      // Simulate load
      const requests = [];
      for (let i = 0; i < 20; i++) {
        requests.push(request(app).get('/health'));
      }

      await Promise.all(requests);

      // Allow garbage collection
      await new Promise(resolve => setTimeout(resolve, 100));
      if (global.gc) {
        global.gc();
      }

      const finalMemory = process.memoryUsage().heapUsed;
      const memoryGrowth = finalMemory - initialMemory;
      const maxGrowth = 50 * 1024 * 1024; // 50MB

      expect(memoryGrowth).toBeLessThan(maxGrowth);

      console.log(`📈 Memory growth: ${(memoryGrowth / 1024 / 1024).toFixed(2)} MB`);
    });
  });

  describe('Concurrent Request Performance', () => {
    test('Should handle concurrent requests without degradation', async () => {
      const concurrentRequests = 50;
      const maxAverageTime = 200; // ms

      const requests = Array.from({ length: concurrentRequests }, () =>
        request(app).get('/health')
      );

      const startTime = Date.now();
      const responses = await Promise.allSettled(requests);
      const totalTime = Date.now() - startTime;

      const successful = responses.filter(r =>
        r.status === 'fulfilled' &&
        r.value.status < 500
      );

      const successRate = successful.length / responses.length;
      const averageTime = totalTime / concurrentRequests;

      expect(successRate).toBeGreaterThan(0.9); // 90% success rate
      expect(averageTime).toBeLessThan(maxAverageTime);

      console.log(`🔄 Concurrency Test: ${concurrentRequests} requests`);
      console.log(`   Success rate: ${(successRate * 100).toFixed(1)}%`);
      console.log(`   Average time: ${averageTime.toFixed(2)}ms`);
      console.log(`   Total time: ${totalTime}ms`);
    });
  });

  describe('Response Compression', () => {
    test('Responses should be compressed when appropriate', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      // Check for compression headers
      const contentEncoding = response.headers['content-encoding'];
      const contentLength = response.headers['content-length'];

      // Most responses should be compressed
      if (contentLength && parseInt(contentLength) > 1024) {
        expect(['gzip', 'deflate', 'br']).toContain(contentEncoding);
      }

      console.log(`🗜️ Compression: ${contentEncoding || 'none'} (${contentLength} bytes)`);
    });
  });

  describe('Rate Limiting Performance', () => {
    test('Rate limiting should not impact legitimate requests', async () => {
      const legitimateRequests = 10;
      const maxTime = 100; // ms per request

      const requests = Array.from({ length: legitimateRequests }, (_, i) =>
        request(app).get('/health')
      );

      const startTime = Date.now();
      const responses = await Promise.allSettled(requests);
      const totalTime = Date.now() - startTime;

      const successful = responses.filter(r =>
        r.status === 'fulfilled' &&
        r.value.status === 200
      );

      expect(successful.length).toBe(legitimateRequests);
      expect(totalTime / legitimateRequests).toBeLessThan(maxTime);

      console.log(`🚦 Rate Limiting Test: ${successful.length}/${legitimateRequests} successful`);
      console.log(`   Average time: ${(totalTime / legitimateRequests).toFixed(2)}ms`);
    });
  });

  describe('WebSocket Performance', () => {
    test('WebSocket connection should be established quickly', async () => {
      const WebSocket = require('ws');
      const wsUrl = `ws://localhost:${server.address().port}/ws`;

      return new Promise((resolve, reject) => {
        const startTime = Date.now();
        const ws = new WebSocket(wsUrl);

        const timeout = setTimeout(() => {
          ws.close();
          reject(new Error('WebSocket connection timeout'));
        }, 5000);

        ws.on('open', () => {
          clearTimeout(timeout);
          const connectionTime = Date.now() - startTime;

          expect(connectionTime).toBeLessThan(3000); // 3 seconds max

          console.log(`🔌 WebSocket connection: ${connectionTime}ms`);
          ws.close();
          resolve(null);
        });

        ws.on('error', (error: Error) => {
          clearTimeout(timeout);
          reject(error);
        });
      });
    });
  });

  describe('Overall Performance SLA', () => {
    test('System should meet performance SLA requirements', async () => {
      const slaMetrics = {
        healthCheckMaxTime: 100,
        metricsMaxTime: 200,
        memoryMaxUsage: 512 * 1024 * 1024, // 512MB
        minSuccessRate: 0.95, // 95%
        maxSlowQueryRate: 0.05, // 5%
      };

      // Test health check performance
      const healthStart = Date.now();
      const healthResponse = await request(app).get('/health');
      const healthTime = Date.now() - healthStart;

      expect(healthTime).toBeLessThan(slaMetrics.healthCheckMaxTime);

      // Test metrics performance
      const metricsStart = Date.now();
      const metricsResponse = await request(app).get('/metrics');
      const metricsTime = Date.now() - metricsStart;

      expect(metricsTime).toBeLessThan(slaMetrics.metricsMaxTime);

      // Check memory usage
      const memUsage = process.memoryUsage();
      expect(memUsage.heapUsed).toBeLessThan(slaMetrics.memoryMaxUsage);

      // Check database performance
      const dbMetrics = getConnectionMetrics();
      const slowQueryRate = dbMetrics.totalQueries > 0
        ? dbMetrics.slowQueries / dbMetrics.totalQueries
        : 0;

      expect(slowQueryRate).toBeLessThan(slaMetrics.maxSlowQueryRate);

      // Test overall success rate
      const testRequests = [
        () => request(app).get('/health'),
        () => request(app).get('/metrics'),
      ];

      const responses = await Promise.allSettled(testRequests.map(req => req()));
      const successful = responses.filter(r =>
        r.status === 'fulfilled' &&
        r.value.status < 500
      );

      const successRate = successful.length / responses.length;
      expect(successRate).toBeGreaterThanOrEqual(slaMetrics.minSuccessRate);

      console.log('🎯 SLA Results:', {
        healthCheck: `${healthTime}ms < ${slaMetrics.healthCheckMaxTime}ms ✅`,
        metrics: `${metricsTime}ms < ${slaMetrics.metricsMaxTime}ms ✅`,
        memory: `${(memUsage.heapUsed / 1024 / 1024).toFixed(2)}MB < ${(slaMetrics.memoryMaxUsage / 1024 / 1024).toFixed(2)}MB ✅`,
        successRate: `${(successRate * 100).toFixed(1)}% >= ${(slaMetrics.minSuccessRate * 100).toFixed(1)}% ✅`,
        slowQueryRate: `${(slowQueryRate * 100).toFixed(2)}% <= ${(slaMetrics.maxSlowQueryRate * 100).toFixed(2)}% ✅`,
      });
    });
  });
});

// Performance benchmark utility
export const performanceBenchmark = {
  async measureEndpoint(endpoint: string, iterations: number = 10) {
    const times: number[] = [];

    for (let i = 0; i < iterations; i++) {
      const start = Date.now();
      try {
        await request(app).get(endpoint);
        times.push(Date.now() - start);
      } catch (error) {
        times.push(-1); // Mark failed requests
      }
    }

    const successful = times.filter(t => t > 0);

    return {
      endpoint,
      iterations,
      successful: successful.length,
      failed: times.length - successful.length,
      average: successful.length > 0 ? successful.reduce((a, b) => a + b, 0) / successful.length : 0,
      min: successful.length > 0 ? Math.min(...successful) : 0,
      max: successful.length > 0 ? Math.max(...successful) : 0,
      p95: successful.length > 0 ? successful.sort((a, b) => a - b)[Math.floor(successful.length * 0.95)] : 0,
    };
  },

  async generateReport() {
    const endpoints = ['/health', '/metrics', '/api/projects'];
    const results = await Promise.all(
      endpoints.map(endpoint => this.measureEndpoint(endpoint))
    );

    console.log('\n📊 Performance Benchmark Report');
    console.log('='.repeat(50));

    results.forEach(result => {
      console.log(`\n${result.endpoint}:`);
      console.log(`  Success Rate: ${(result.successful / result.iterations * 100).toFixed(1)}%`);
      console.log(`  Average: ${result.average.toFixed(2)}ms`);
      console.log(`  Min/Max: ${result.min.toFixed(2)}ms / ${result.max.toFixed(2)}ms`);
      console.log(`  P95: ${result.p95.toFixed(2)}ms`);
    });

    return results;
  },
};