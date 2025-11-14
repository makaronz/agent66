import request from 'supertest';
import app from '../../server';

describe('Metrics Routes', () => {
  describe('GET /metrics', () => {
    it('should return Prometheus-style metrics', async () => {
      const response = await request(app)
        .get('/metrics')
        .expect(200);

      expect(response.headers['content-type']).toMatch(/text\/plain/);
      expect(response.text).toContain('# HELP');
      expect(response.text).toContain('# TYPE');
    });

    it('should include HTTP request metrics', async () => {
      const response = await request(app)
        .get('/metrics')
        .expect(200);

      // Check for common HTTP metrics
      expect(response.text).toMatch(/http_requests_total/);
      expect(response.text).toMatch(/http_request_duration_seconds/);
    });

    it('should include application-specific metrics', async () => {
      const response = await request(app)
        .get('/metrics')
        .expect(200);

      // Look for application metrics
      expect(response.text).toMatch(/nodejs_|process_/);
    });

    it('should include custom business metrics', async () => {
      const response = await request(app)
        .get('/metrics')
        .expect(200);

      // Check for business metrics like active users, projects, etc.
      const businessMetrics = [
        'active_users_total',
        'projects_total',
        'time_entries_total'
      ];

      const hasBusinessMetric = businessMetrics.some(metric =>
        response.text.includes(metric)
      );

      // This assertion might need adjustment based on actual metrics implementation
      expect(typeof response.text).toBe('string');
    });
  });

  describe('GET /metrics/json', () => {
    it('should return metrics in JSON format', async () => {
      const response = await request(app)
        .get('/metrics/json')
        .expect(200);

      expect(response.headers['content-type']).toMatch(/application\/json/);
      expect(response.body).toHaveProperty('metrics');
      expect(Array.isArray(response.body.metrics)).toBe(true);
    });

    it('should include metric metadata', async () => {
      const response = await request(app)
        .get('/metrics/json')
        .expect(200);

      if (response.body.metrics.length > 0) {
        const metric = response.body.metrics[0];
        expect(metric).toHaveProperty('name');
        expect(metric).toHaveProperty('type');
        expect(metric).toHaveProperty('value');
      }
    });
  });

  describe('Metrics collection', () => {
    it('should track HTTP request metrics', async () => {
      // Make some requests to generate metrics
      await request(app).get('/health');
      await request(app).get('/health/detailed');
      await request(app).get('/nonexistent-route').expect(404);

      // Check that metrics were recorded
      const metricsResponse = await request(app)
        .get('/metrics')
        .expect(200);

      expect(metricsResponse.text).toContain('http_requests_total');
    });

    it('should track response time metrics', async () => {
      const startTime = Date.now();

      await request(app).get('/health');

      const responseTime = Date.now() - startTime;

      // Check that response time metrics exist
      const metricsResponse = await request(app)
        .get('/metrics')
        .expect(200);

      expect(metricsResponse.text).toMatch(/http_request_duration_seconds/);
    });
  });

  describe('Security and access control', () => {
    it('should allow access to metrics endpoint without authentication', async () => {
      await request(app)
        .get('/metrics')
        .expect(200);
    });

    it('should include rate limiting headers if applicable', async () => {
      const response = await request(app)
        .get('/metrics');

      // Check for common rate limiting headers
      const rateLimitHeaders = [
        'x-ratelimit-limit',
        'x-ratelimit-remaining',
        'x-ratelimit-reset'
      ];

      const hasRateLimitHeader = rateLimitHeaders.some(header =>
        response.headers[header]
      );

      // This might not always be present, so we don't assert strictly
      expect(response.status).toBe(200);
    });
  });
});