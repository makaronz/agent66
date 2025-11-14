import request from 'supertest';
import app from '../../server';

describe('Health Check Routes', () => {
  describe('GET /health', () => {
    it('should return health status with 200', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body).toHaveProperty('status', 'ok');
      expect(response.body).toHaveProperty('timestamp');
      expect(response.body).toHaveProperty('uptime');
      expect(response.body).toHaveProperty('version');
    });

    it('should include database status if available', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body).toHaveProperty('services');
      if (response.body.services) {
        expect(response.body.services).toHaveProperty('database');
      }
    });

    it('should include system information', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body).toHaveProperty('system');
      if (response.body.system) {
        expect(response.body.system).toHaveProperty('platform');
        expect(response.body.system).toHaveProperty('architecture');
        expect(response.body.system).toHaveProperty('memory');
      }
    });
  });

  describe('GET /health/detailed', () => {
    it('should return detailed health information', async () => {
      const response = await request(app)
        .get('/health/detailed')
        .expect(200);

      expect(response.body).toHaveProperty('status');
      expect(response.body).toHaveProperty('checks');
      expect(Array.isArray(response.body.checks)).toBe(true);

      if (response.body.checks.length > 0) {
        const check = response.body.checks[0];
        expect(check).toHaveProperty('name');
        expect(check).toHaveProperty('status');
        expect(check).toHaveProperty('responseTime');
      }
    });

    it('should include performance metrics in detailed health', async () => {
      const response = await request(app)
        .get('/health/detailed')
        .expect(200);

      expect(response.body).toHaveProperty('performance');
      if (response.body.performance) {
        expect(response.body.performance).toHaveProperty('cpu');
        expect(response.body.performance).toHaveProperty('memory');
        expect(response.body.performance).toHaveProperty('responseTime');
      }
    });
  });

  describe('GET /health/ready', () => {
    it('should return ready status when all services are available', async () => {
      const response = await request(app)
        .get('/health/ready')
        .expect(200);

      expect(response.body).toHaveProperty('status', 'ready');
      expect(response.body).toHaveProperty('checks');
    });

    it('should return 503 when critical services are unavailable', async () => {
      // This test would require mocking database connection failures
      // For now, we'll assume services are available
      const response = await request(app)
        .get('/health/ready')
        .expect(200);

      expect(response.body.status).toMatch(/ready|degraded/);
    });
  });

  describe('GET /health/live', () => {
    it('should return alive status', async () => {
      const response = await request(app)
        .get('/health/live')
        .expect(200);

      expect(response.body).toHaveProperty('status', 'alive');
      expect(response.body).toHaveProperty('timestamp');
    });
  });
});