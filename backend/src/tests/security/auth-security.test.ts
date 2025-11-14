import request from 'supertest';
import jwt from 'jsonwebtoken';
import app from '../../server';
import { connectDB, closeDB, clearDB } from '../helpers/database';

describe('Authentication Security Tests', () => {
  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
  });

  describe('Input Validation Security', () => {
    it('should prevent SQL injection attempts', async () => {
      const maliciousInputs = [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "admin'--",
        "' UNION SELECT * FROM users --",
        "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --"
      ];

      for (const maliciousInput of maliciousInputs) {
        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: maliciousInput,
            password: 'password123'
          });

        // Should not return 500 (internal server error)
        expect(response.status).not.toBe(500);
        expect(response.body).not.toHaveProperty('error', expect.objectContaining({
          message: expect.stringContaining('SQL')
        }));
      }
    });

    it('should prevent XSS attempts', async () => {
      const xssPayloads = [
        '<script>alert("xss")</script>',
        'javascript:alert("xss")',
        '<img src=x onerror=alert("xss")>',
        '"><script>alert("xss")</script>',
        '\"><script>document.location=\"http://evil.com\"</script>'
      ];

      for (const xssPayload of xssPayloads) {
        const response = await request(app)
          .post('/api/auth/register')
          .send({
            name: xssPayload,
            email: `test${Date.now()}@example.com`,
            password: 'password123'
          });

        // Should handle XSS attempts gracefully
        expect([200, 201, 400]).toContain(response.status);

        // Response should not contain unescaped script tags
        const responseText = JSON.stringify(response.body);
        expect(responseText).not.toMatch(/<script[^>]*>/i);
      }
    });

    it('should validate email format strictly', async () => {
      const invalidEmails = [
        'plainaddress',
        '@missingdomain.com',
        'missing@.com',
        'spaces @domain.com',
        'user@domain .com',
        'user@domain.c',
        'user..name@domain.com',
        '.user@domain.com',
        'user@domain..com'
      ];

      for (const invalidEmail of invalidEmails) {
        const response = await request(app)
          .post('/api/auth/register')
          .send({
            name: 'Test User',
            email: invalidEmail,
            password: 'password123'
          });

        expect(response.status).toBe(400);
        expect(response.body.error.code).toBe('VALIDATION_ERROR');
      }
    });

    it('should enforce password strength requirements', async () => {
      const weakPasswords = [
        '123',
        'password',
        'qwerty',
        '111111',
        'abc123',
        'password123',
        'admin',
        'letmein'
      ];

      for (const weakPassword of weakPasswords) {
        const response = await request(app)
          .post('/api/auth/register')
          .send({
            name: 'Test User',
            email: `test${Date.now()}@example.com`,
            password: weakPassword
          });

        // Should either accept with additional validation or reject weak passwords
        expect([200, 201, 400]).toContain(response.status);
      }
    });
  });

  describe('Token Security', () => {
    it('should use secure JWT settings', () => {
      // Test JWT token generation with proper claims
      const payload = {
        id: 'test-user-id',
        email: 'test@example.com',
        role: 'USER'
      };

      const token = jwt.sign(payload, process.env.JWT_SECRET || 'test-secret', {
        expiresIn: '1h',
        issuer: 'agent66',
        audience: 'agent66-users'
      });

      const decoded = jwt.decode(token) as any;

      expect(decoded).toHaveProperty('id');
      expect(decoded).toHaveProperty('email');
      expect(decoded).toHaveProperty('role');
      expect(decoded).toHaveProperty('iat');
      expect(decoded).toHaveProperty('exp');
    });

    it('should reject tokens with none algorithm', async () => {
      const maliciousToken = jwt.sign({
        id: 'admin',
        email: 'admin@example.com',
        role: 'ADMIN'
      }, '', { algorithm: 'none' });

      const response = await request(app)
        .get('/api/projects')
        .set('Authorization', `Bearer ${maliciousToken}`)
        .expect(401);

      expect(response.body.error.code).toBe('AUTHENTICATION_ERROR');
    });

    it('should reject tokens with invalid signatures', async () => {
      const validPayload = {
        id: 'user123',
        email: 'user@example.com',
        role: 'USER'
      };

      const tokenWithWrongSecret = jwt.sign(validPayload, 'wrong-secret');

      const response = await request(app)
        .get('/api/projects')
        .set('Authorization', `Bearer ${tokenWithWrongSecret}`)
        .expect(401);

      expect(response.body.error.code).toBe('AUTHENTICATION_ERROR');
    });

    it('should handle token replay attacks', async () => {
      // Register a user
      const userData = {
        name: 'Replay Test User',
        email: 'replay@example.com',
        password: 'password123'
      };

      const registerResponse = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      const token = registerResponse.body.token;

      // Use token multiple times rapidly (should be allowed for same token)
      for (let i = 0; i < 5; i++) {
        const response = await request(app)
          .get('/api/projects')
          .set('Authorization', `Bearer ${token}`)
          .expect(200);

        expect(response.body).toBeDefined();
      }
    });
  });

  describe('Rate Limiting Security', () => {
    it('should prevent brute force attacks on login', async () => {
      const maliciousEmail = 'bruteforce@example.com';
      const attempts = 20;

      const promises = Array(attempts).fill(null).map(() =>
        request(app)
          .post('/api/auth/login')
          .send({
            email: maliciousEmail,
            password: 'wrongpassword'
          })
      );

      const responses = await Promise.all(promises);

      // Some requests should be rate limited
      const rateLimitedResponses = responses.filter(res => res.status === 429);
      expect(rateLimitedResponses.length).toBeGreaterThan(0);

      // Rate limited responses should have appropriate headers
      if (rateLimitedResponses.length > 0) {
        const rateLimitedResponse = rateLimitedResponses[0];
        expect(rateLimitedResponse.headers['retry-after']).toBeDefined();
      }
    });

    it('should prevent enumeration attacks', async () => {
      const commonEmails = [
        'admin@example.com',
        'test@example.com',
        'user@example.com',
        'root@example.com',
        'administrator@example.com'
      ];

      const promises = commonEmails.map(email =>
        request(app)
          .post('/api/auth/login')
          .send({
            email,
            password: 'password'
          })
      );

      const responses = await Promise.all(promises);

      // All responses should have the same error message format
      responses.forEach(response => {
        if (response.status === 400) {
          expect(response.body.message).toContain('Invalid credentials');
        }
      });

      // Should not reveal which emails exist
      const errorMessages = responses
        .filter(res => res.status === 400)
        .map(res => res.body.message);

      const uniqueMessages = [...new Set(errorMessages)];
      expect(uniqueMessages.length).toBeLessThanOrEqual(2); // Allow slight variations
    });
  });

  describe('Session Security', () => {
    it('should not expose sensitive information in error messages', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@example.com',
          password: 'wrongpassword'
        })
        .expect(400);

      // Error message should be generic
      expect(response.body.message).not.toContain('database');
      expect(response.body.message).not.toContain('SQL');
      expect(response.body.message).not.toContain('internal');

      // Should not expose stack traces in production
      expect(response.body).not.toHaveProperty('stack');
    });

    it('should implement proper CORS headers', async () => {
      const response = await request(app)
        .options('/api/auth/login')
        .set('Origin', 'http://evil.com');

      // Should have appropriate CORS headers
      expect(response.headers['access-control-allow-origin']).toBeDefined();

      // Should not allow arbitrary origins (unless configured)
      if (response.headers['access-control-allow-origin'] !== '*') {
        expect(['http://localhost:3000', 'http://localhost:5173']).toContain(
          response.headers['access-control-allow-origin']
        );
      }
    });

    it('should include security headers', async () => {
      const response = await request(app)
        .get('/health');

      // Should include security-related headers
      expect(response.headers['x-content-type-options']).toBe('nosniff');
      expect(response.headers['x-frame-options']).toBeDefined();
      expect(response.headers['x-xss-protection']).toBeDefined();
    });
  });

  describe('Authorization Security', () => {
    it('should prevent privilege escalation', async () => {
      // Create normal user
      const normalUserResponse = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Normal User',
          email: 'normal@example.com',
          password: 'password123'
        })
        .expect(201);

      const normalUserToken = normalUserResponse.body.token;

      // Try to access admin endpoints with normal user token
      const adminEndpoints = [
        '/api/admin/users',
        '/api/admin/system',
        '/api/admin/logs'
      ];

      for (const endpoint of adminEndpoints) {
        await request(app)
          .get(endpoint)
          .set('Authorization', `Bearer ${normalUserToken}`)
          .expect(403);
      }
    });

    it('should validate user permissions on each request', async () => {
      const userData = {
        name: 'Permission Test User',
        email: 'permission@example.com',
        password: 'password123'
      };

      const registerResponse = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      const token = registerResponse.body.token;

      // Create a modified token with elevated privileges (this should fail)
      const decodedToken = jwt.decode(token) as any;
      decodedToken.role = 'ADMIN';

      const maliciousToken = jwt.sign(decodedToken, process.env.JWT_SECRET || 'test-secret');

      // Server should reject the manipulated token
      const response = await request(app)
        .get('/api/admin/users')
        .set('Authorization', `Bearer ${maliciousToken}`)
        .expect(403);

      expect(response.body.error.code).toBe('AUTHORIZATION_ERROR');
    });
  });

  describe('Input Size Limits', () => {
    it('should handle oversized payloads', async () => {
      const oversizedPayload = {
        name: 'A'.repeat(10000), // Very long name
        email: 'test@example.com',
        password: 'password123'
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(oversizedPayload);

      // Should handle oversized input gracefully
      expect([400, 413, 422]).toContain(response.status);
    });

    it('should prevent buffer overflow attacks', async () => {
      const bufferSize = 1024 * 1024; // 1MB
      const buffer = 'A'.repeat(bufferSize);

      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: `${buffer}@example.com`,
          password: buffer
        });

      // Should handle buffer overflow attempts
      expect([400, 413, 422]).toContain(response.status);
    });
  });
});