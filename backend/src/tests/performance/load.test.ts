import request from 'supertest';
import app from '../../server';
import { connectDB, closeDB, clearDB, createTestUser } from '../helpers/database';

describe('Performance and Load Testing', () => {
  let authToken: string;

  beforeAll(async () => {
    await connectDB();
    const { token } = await createTestUser({
      email: 'perf@example.com',
      firstName: 'Performance',
      lastName: 'Test'
    });
    authToken = token;
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
  });

  describe('Response Time Benchmarks', () => {
    it('should respond to health checks within 50ms', async () => {
      const startTime = Date.now();

      await request(app)
        .get('/health')
        .expect(200);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
    });

    it('should handle authentication within 200ms', async () => {
      const userData = {
        email: 'perftest@example.com',
        name: 'Performance Test User',
        password: 'password123'
      };

      // Register
      const registerStart = Date.now();
      await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);
      const registerTime = Date.now() - registerStart;

      expect(registerTime).toBeLessThan(200);

      // Login
      const loginStart = Date.now();
      await request(app)
        .post('/api/auth/login')
        .send({
          email: userData.email,
          password: userData.password
        })
        .expect(200);
      const loginTime = Date.now() - loginStart;

      expect(loginTime).toBeLessThan(200);
    });

    it('should serve metrics within 100ms', async () => {
      const startTime = Date.now();

      await request(app)
        .get('/metrics')
        .expect(200);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(100);
    });
  });

  describe('Concurrent Request Handling', () => {
    it('should handle 50 concurrent health check requests', async () => {
      const concurrentRequests = 50;
      const promises = Array(concurrentRequests).fill(null).map(() =>
        request(app).get('/health')
      );

      const startTime = Date.now();
      const responses = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      // All requests should succeed
      responses.forEach(response => {
        expect(response.status).toBe(200);
      });

      // Average response time should be reasonable
      const avgResponseTime = totalTime / concurrentRequests;
      expect(avgResponseTime).toBeLessThan(100);
    });

    it('should handle 20 concurrent authentication requests', async () => {
      const concurrentRequests = 20;
      const promises = Array(concurrentRequests).fill(null).map((_, index) =>
        request(app)
          .post('/api/auth/register')
          .send({
            email: `concurrent${index}@example.com`,
            name: `Concurrent User ${index}`,
            password: 'password123'
          })
      );

      const startTime = Date.now();
      const responses = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      // Most requests should succeed (allowing for some rate limiting)
      const successfulResponses = responses.filter(res => res.status === 201);
      expect(successfulResponses.length).toBeGreaterThan(concurrentRequests * 0.8);

      // Average response time should be reasonable
      const avgResponseTime = totalTime / concurrentRequests;
      expect(avgResponseTime).toBeLessThan(500);
    });
  });

  describe('Memory Usage', () => {
    it('should not leak memory during repeated requests', async () => {
      const initialMemory = process.memoryUsage().heapUsed;

      // Make many requests
      for (let i = 0; i < 100; i++) {
        await request(app).get('/health');
        await request(app)
          .get('/api/projects')
          .set('Authorization', `Bearer ${authToken}`);
      }

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;

      // Memory increase should be minimal (less than 10MB)
      expect(memoryIncrease).toBeLessThan(10 * 1024 * 1024);
    });

    it('should handle large payloads efficiently', async () => {
      const largePayload = {
        title: 'Large Project',
        description: 'A'.repeat(10000), // 10KB description
        metadata: {
          tags: Array(100).fill(null).map((_, i) => `tag-${i}`),
          categories: Array(50).fill(null).map((_, i) => `category-${i}`)
        }
      };

      const startTime = Date.now();

      const response = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .send(largePayload);

      const responseTime = Date.now() - startTime;

      // Should handle large payloads efficiently
      expect(responseTime).toBeLessThan(1000);
      expect(response.status).toBeLessThan(500);
    });
  });

  describe('Database Performance', () => {
    it('should handle rapid database operations', async () => {
      const operationCount = 50;
      const promises = [];

      const startTime = Date.now();

      // Create multiple projects concurrently
      for (let i = 0; i < operationCount; i++) {
        promises.push(
          request(app)
            .post('/api/projects')
            .set('Authorization', `Bearer ${authToken}`)
            .send({
              title: `Project ${i}`,
              description: `Description for project ${i}`
            })
        );
      }

      const responses = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      // Most operations should succeed
      const successfulResponses = responses.filter(res => res.status === 201);
      expect(successfulResponses.length).toBeGreaterThan(operationCount * 0.9);

      // Average time per operation should be reasonable
      const avgTime = totalTime / operationCount;
      expect(avgTime).toBeLessThan(200);
    });

    it('should efficiently query large datasets', async () => {
      // Create many projects first
      const projectCount = 100;
      const createPromises = [];

      for (let i = 0; i < projectCount; i++) {
        createPromises.push(
          request(app)
            .post('/api/projects')
            .set('Authorization', `Bearer ${authToken}`)
            .send({
              title: `Query Test Project ${i}`,
              description: `Description ${i}`,
              status: i % 2 === 0 ? 'ACTIVE' : 'COMPLETED'
            })
        );
      }

      await Promise.all(createPromises);

      // Test query performance
      const startTime = Date.now();

      const response = await request(app)
        .get('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .query({ page: 1, limit: 50 });

      const queryTime = Date.now() - startTime;

      expect(response.status).toBe(200);
      expect(queryTime).toBeLessThan(500);
      expect(response.body.length).toBeLessThanOrEqual(50);
    });
  });

  describe('Rate Limiting Performance', () => {
    it('should implement efficient rate limiting', async () => {
      const burstRequestCount = 30;
      const promises = Array(burstRequestCount).fill(null).map(() =>
        request(app).get('/health')
      );

      const startTime = Date.now();
      const responses = await Promise.all(promises);
      const totalTime = Date.now() - startTime;

      // Should handle burst requests efficiently
      const successCount = responses.filter(res => res.status === 200).length;
      const rateLimitedCount = responses.filter(res => res.status === 429).length;

      expect(successCount + rateLimitedCount).toBe(burstRequestCount);
      expect(totalTime).toBeLessThan(1000);
    });
  });

  describe('Stress Testing', () => {
    it('should maintain performance under sustained load', async () => {
      const rounds = 5;
      const requestsPerRound = 20;
      const performanceMetrics: number[] = [];

      for (let round = 0; round < rounds; round++) {
        const promises = Array(requestsPerRound).fill(null).map((_, index) =>
          request(app)
            .get('/health')
            .query({ round, request: index })
        );

        const startTime = Date.now();
        await Promise.all(promises);
        const roundTime = Date.now() - startTime;

        performanceMetrics.push(roundTime / requestsPerRound);

        // Brief pause between rounds
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Performance should be consistent across rounds
      const avgResponseTime = performanceMetrics.reduce((a, b) => a + b, 0) / performanceMetrics.length;
      const maxResponseTime = Math.max(...performanceMetrics);
      const minResponseTime = Math.min(...performanceMetrics);

      // Response times should be consistent (within 2x variation)
      expect(maxResponseTime / minResponseTime).toBeLessThan(2);
      expect(avgResponseTime).toBeLessThan(100);
    });

    it('should recover from temporary load spikes', async () => {
      // Create load spike
      const spikeRequests = 100;
      const spikePromises = Array(spikeRequests).fill(null).map(() =>
        request(app).get('/health')
      );

      await Promise.all(spikePromises);

      // Wait for recovery
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Test normal performance after spike
      const normalRequests = 10;
      const normalPromises = Array(normalRequests).fill(null).map(() =>
        request(app).get('/health')
      );

      const startTime = Date.now();
      const responses = await Promise.all(normalPromises);
      const recoveryTime = Date.now() - startTime;

      // Should recover and maintain normal performance
      const successCount = responses.filter(res => res.status === 200).length;
      expect(successCount).toBe(normalRequests);
      expect(recoveryTime / normalRequests).toBeLessThan(100);
    });
  });
});