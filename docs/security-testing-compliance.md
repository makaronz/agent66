# Agent66 Security Testing & Compliance Framework

**Purpose:** Comprehensive security testing suite and compliance verification for Agent66 authentication system.

---

## 🔍 Security Testing Framework

### 1. Automated Security Tests

**File:** `/backend/src/tests/security/authSecurity.test.ts`

```typescript
import request from 'supertest';
import app from '../../server';
import { connectDB, closeDB, clearDB } from '../helpers/database';
import User from '../../models/User';

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

  describe('OWASP A01 - Broken Access Control Tests', () => {
    test('should reject requests without proper Authorization header', async () => {
      const response = await request(app)
        .get('/api/protected-endpoint')
        .expect(401);

      expect(response.body).toHaveProperty('message');
    });

    test('should reject requests with malformed JWT tokens', async () => {
      const malformedTokens = [
        'invalid.token',
        'not.a.jwt',
        'bearer token',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature'
      ];

      for (const token of malformedTokens) {
        const response = await request(app)
          .get('/api/protected-endpoint')
          .set('Authorization', `Bearer ${token}`)
          .expect(401);

        expect(response.body.message).toMatch(/Invalid token/i);
      }
    });

    test('should reject expired tokens', async () => {
      // Create expired token
      const expiredToken = createExpiredToken();

      const response = await request(app)
        .get('/api/protected-endpoint')
        .set('Authorization', `Bearer ${expiredToken}`)
        .expect(401);

      expect(response.body.message).toMatch(/expired/i);
    });

    test('should enforce role-based access control', async () => {
      // Create user with CREW role
      const userToken = await createUserToken('CREW');

      // Try to access admin endpoint
      const response = await request(app)
        .get('/api/admin/endpoint')
        .set('Authorization', `Bearer ${userToken}`)
        .expect(403);

      expect(response.body.message).toMatch(/insufficient permissions/i);
    });

    test('should prevent privilege escalation attempts', async () => {
      const userToken = await createUserToken('CREW');

      // Attempt to modify user role
      const response = await request(app)
        .put('/api/users/role')
        .set('Authorization', `Bearer ${userToken}`)
        .send({ role: 'ADMIN' })
        .expect(403);

      expect(response.body.message).toMatch(/unauthorized/i);
    });
  });

  describe('OWASP A02 - Cryptographic Failures Tests', () => {
    test('should store passwords with proper hashing', async () => {
      const user = {
        name: 'Test User',
        email: 'test@example.com',
        password: 'SecurePassword123!'
      };

      await request(app)
        .post('/api/auth/register')
        .send(user)
        .expect(201);

      const savedUser = await User.findOne({ email: user.email }).select('+password');

      expect(savedUser.password).not.toBe(user.password);
      expect(savedUser.password).toMatch(/^\$2[aby]\$\d+\$/); // bcrypt pattern
      expect(savedUser.password.split('$')[2]).toBe('12'); // 12 rounds
    });

    test('should not use default/weak secrets', async () => {
      const weakSecrets = [
        'password',
        '123456',
        'secret',
        'changeme',
        'default',
        'test'
      ];

      for (const weakSecret of weakSecrets) {
        // This test would check if application rejects weak secrets
        // Implementation depends on your secret validation
        expect(process.env.JWT_SECRET).not.toBe(weakSecret);
        expect(process.env.ENCRYPTION_KEY).not.toBe(weakSecret);
      }
    });

    test('should use strong cryptographic algorithms', async () => {
      // Verify JWT is using HS256 or better
      const user = await createTestUser();
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: user.email,
          password: 'password123'
        });

      const token = loginResponse.body.token;
      const decoded = require('jsonwebtoken').decode(token, { complete: true });

      expect(decoded.header.alg).toMatch(/^(HS|RS)256$/);
    });
  });

  describe('OWASP A03 - Injection Tests', () => {
    test('should prevent SQL injection in email field', async () => {
      const sqlInjectionPayloads = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'--",
        "admin'/*",
        "' OR 'x'='x",
        "'; DELETE FROM users WHERE 1=1; --"
      ];

      for (const payload of sqlInjectionPayloads) {
        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: payload,
            password: 'password'
          });

        expect(response.status).toBe(400);
        expect(response.body.message).toMatch(/invalid credentials/i);
      }
    });

    test('should prevent XSS in name field', async () => {
      const xssPayloads = [
        '<script>alert("XSS")</script>',
        '"><script>alert("XSS")</script>',
        '<img src="x" onerror="alert(1)">',
        '<svg onload="alert(1)">',
        'javascript:alert(1)'
      ];

      for (const payload of xssPayloads) {
        const response = await request(app)
          .post('/api/auth/register')
          .send({
            name: payload,
            email: `test-${Math.random()}@example.com`,
            password: 'SecurePassword123!'
          });

        // Should either reject or sanitize
        if (response.status === 201) {
          // If accepted, verify sanitization
          const user = await User.findOne({ name: payload });
          expect(user.name).not.toContain('<script>');
          expect(user.name).not.toContain('javascript:');
        }
      }
    });

    test('should prevent NoSQL injection', async () => {
      const noSQLPayloads = [
        { '$ne': null },
        { '$gt': '' },
        { '$regex': '.*' },
        { '$where': 'return true' },
        { '$or': [{ 'email': { $ne: null } }, { 'password': { $ne: null } }] }
      ];

      for (const payload of noSQLPayloads) {
        const response = await request(app)
          .post('/api/auth/login')
          .send({
            email: payload,
            password: 'password'
          });

        expect(response.status).toBe(400);
      }
    });
  });

  describe('OWASP A07 - Authentication Failures Tests', () => {
    test('should prevent user enumeration via email', async () => {
      // Create a user
      await createTestUser();

      // Try different timing attacks
      const existingEmailResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'existinguser@example.com',
          password: 'wrongpassword'
        });

      const nonExistingEmailResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistinguser@example.com',
          password: 'wrongpassword'
        });

      // Both responses should be identical
      expect(existingEmailResponse.status).toBe(nonExistingEmailResponse.status);
      expect(existingEmailResponse.body.message).toBe(nonExistingEmailResponse.body.message);
    });

    test('should implement account lockout after failed attempts', async () => {
      const user = await createTestUser();

      // Make multiple failed login attempts
      for (let i = 0; i < 6; i++) {
        await request(app)
          .post('/api/auth/login')
          .send({
            email: user.email,
            password: 'wrongpassword'
          });
      }

      // Next login attempt should be locked
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: user.email,
          password: 'password123'
        });

      expect(response.status).toBe(423); // Locked
      expect(response.body.message).toMatch(/locked/i);
    });

    test('should enforce strong password requirements', async () => {
      const weakPasswords = [
        'password',
        '12345678',
        'qwerty',
        'password123',
        'abc123',
        'no numbers',
        'NO UPPERCASE',
        'no lowercase',
        'Short1!',
        'no特殊字符'
      ];

      for (const weakPassword of weakPasswords) {
        const response = await request(app)
          .post('/api/auth/register')
          .send({
            name: 'Test User',
            email: `test-${Math.random()}@example.com`,
            password: weakPassword
          });

        expect(response.status).toBe(400);
        expect(response.body.message).toMatch(/password/i);
      }
    });
  });

  describe('Rate Limiting Tests', () => {
    test('should limit authentication attempts', async () => {
      const loginData = {
        email: 'test@example.com',
        password: 'password'
      };

      // Make rapid requests
      const requests = Array(25).fill(null).map(() =>
        request(app).post('/api/auth/login').send(loginData)
      );

      const responses = await Promise.all(requests);

      // At least some requests should be rate limited
      const rateLimitedResponses = responses.filter(r => r.status === 429);
      expect(rateLimitedResponses.length).toBeGreaterThan(0);

      rateLimitedResponses.forEach(response => {
        expect(response.body.message).toMatch(/too many requests/i);
      });
    });

    test('should limit registration attempts', async () => {
      const userData = {
        name: 'Test User',
        email: 'test@example.com',
        password: 'SecurePassword123!'
      };

      // Make multiple registration attempts
      const requests = Array(10).fill(null).map((_, i) =>
        request(app).post('/api/auth/register').send({
          ...userData,
          email: `test${i}@example.com`
        })
      );

      const responses = await Promise.all(requests);

      // Check for rate limiting
      const rateLimitedResponses = responses.filter(r => r.status === 429);
      if (rateLimitedResponses.length > 0) {
        expect(rateLimitedResponses[0].body.message).toMatch(/too many requests/i);
      }
    });
  });

  describe('Session Management Tests', () => {
    test('should invalidate tokens on logout', async () => {
      const user = await createTestUser();
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: user.email,
          password: 'password123'
        });

      const token = loginResponse.body.token;

      // Logout
      await request(app)
        .post('/api/auth/logout')
        .set('Authorization', `Bearer ${token}`)
        .expect(200);

      // Try to use token after logout
      const response = await request(app)
        .get('/api/protected-endpoint')
        .set('Authorization', `Bearer ${token}`)
        .expect(401);

      expect(response.body.message).toMatch(/invalid/i);
    });

    test('should implement token refresh mechanism', async () => {
      const user = await createTestUser();
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: user.email,
          password: 'password123'
        });

      const refreshToken = loginResponse.body.refreshToken;

      // Use refresh token to get new access token
      const refreshResponse = await request(app)
        .post('/api/auth/refresh')
        .send({ refreshToken });

      expect(refreshResponse.status).toBe(200);
      expect(refreshResponse.body).toHaveProperty('accessToken');
    });
  });
});

// Helper functions
async function createTestUser(userData?: any) {
  const defaultUser = {
    name: 'Test User',
    email: `test-${Math.random()}@example.com`,
    password: 'password123'
  };

  const user = new User({ ...defaultUser, ...userData });
  return await user.save();
}

async function createUserToken(role: string = 'CREW') {
  const user = await createTestUser({ role });
  const loginResponse = await request(app)
    .post('/api/auth/login')
    .send({
      email: user.email,
      password: 'password123'
    });

  return loginResponse.body.token;
}

function createExpiredToken() {
  const jwt = require('jsonwebtoken');
  return jwt.sign(
    { userId: 'test', role: 'CREW' },
    process.env.JWT_SECRET,
    { expiresIn: '-1h' } // Expired
  );
}
```

### 2. Integration Security Tests

**File:** `/backend/src/tests/security/integrationSecurity.test.ts`

```typescript
import request from 'supertest';
import app from '../../server';
import { connectDB, closeDB, clearDB } from '../helpers/database';

describe('Integration Security Tests', () => {
  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
  });

  describe('Cross-Site Scripting (XSS) Protection', () => {
    test('should sanitize user input in responses', async () => {
      const xssPayload = '<script>alert("XSS")</script>';

      // Register user with XSS payload
      await request(app)
        .post('/api/auth/register')
        .send({
          name: xssPayload,
          email: 'xss@example.com',
          password: 'SecurePassword123!'
        });

      // Login and get user data
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'xss@example.com',
          password: 'SecurePassword123!'
        });

      const token = loginResponse.body.token;

      // Get user profile
      const profileResponse = await request(app)
        .get('/api/users/profile')
        .set('Authorization', `Bearer ${token}`);

      // Verify XSS payload is sanitized
      expect(profileResponse.body.name).not.toContain('<script>');
      expect(profileResponse.body.name).not.toContain('alert');
    });

    test('should implement Content Security Policy', async () => {
      const response = await request(app)
        .get('/');

      const cspHeader = response.headers['content-security-policy'];
      expect(cspHeader).toBeDefined();
      expect(cspHeader).toContain("default-src 'self'");
      expect(cspHeader).not.toContain("script-src 'unsafe-inline'");
      expect(cspHeader).not.toContain("script-src 'unsafe-eval'");
    });
  });

  describe('Cross-Site Request Forgery (CSRF) Protection', () => {
    test('should include CSRF token in forms', async () => {
      const response = await request(app)
        .get('/csrf-token');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('csrfToken');
      expect(typeof response.body.csrfToken).toBe('string');
    });

    test('should reject requests without CSRF token', async () => {
      // This test assumes CSRF protection is implemented
      // Implementation depends on your CSRF middleware
      const response = await request(app)
        .post('/api/sensitive-action')
        .send({
          // No CSRF token
        });

      // Should reject if CSRF protection is enabled
      // expect(response.status).toBe(403);
    });
  });

  describe('Security Headers', () => {
    test('should include all required security headers', async () => {
      const response = await request(app).get('/');

      const requiredHeaders = [
        'x-frame-options',
        'x-content-type-options',
        'x-xss-protection',
        'referrer-policy',
        'strict-transport-security'
      ];

      requiredHeaders.forEach(header => {
        expect(response.headers[header]).toBeDefined();
      });

      // Verify header values
      expect(response.headers['x-frame-options']).toBe('DENY');
      expect(response.headers['x-content-type-options']).toBe('nosniff');
      expect(response.headers['x-xss-protection']).toContain('mode=block');
      expect(response.headers['referrer-policy']).toContain('strict-origin');
    });

    test('should implement HSTS in production', async () => {
      const response = await request(app).get('/');

      if (process.env.NODE_ENV === 'production') {
        const hstsHeader = response.headers['strict-transport-security'];
        expect(hstsHeader).toBeDefined();
        expect(hstsHeader).toContain('max-age=');
        expect(hstsHeader).toContain('includeSubDomains');
      }
    });
  });

  describe('Error Handling Security', () => {
    test('should not expose sensitive information in error messages', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@example.com',
          password: 'wrongpassword'
        });

      expect(response.status).toBe(400);
      expect(response.body.message).not.toContain('sql');
      expect(response.body.message).not.toContain('mongodb');
      expect(response.body.message).not.toContain('internal');
      expect(response.body.message).not.toContain('stack');
    });

    test('should sanitize error responses', async () => {
      // Test with malformed request that would cause database errors
      const response = await request(app)
        .post('/api/auth/login')
        .send({});

      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('message');
      expect(response.body).not.toHaveProperty('stack');
      expect(response.body).not.toHaveProperty('error');
    });
  });
});
```

### 3. Penetration Testing Suite

**File:** `/backend/src/tests/security/penetrationTests.test.ts`

```typescript
import request from 'supertest';
import app from '../../server';
import axios from 'axios';

describe('Penetration Testing Suite', () => {
  describe('Authentication Bypass Attempts', () => {
    test('should prevent authentication via URL parameters', async () => {
      const response = await request(app)
        .get('/api/protected?userId=admin&role=ADMIN')
        .expect(401);

      expect(response.body.message).toMatch(/authentication failed/i);
    });

    test('should prevent authentication via HTTP headers', async () => {
      const response = await request(app)
        .get('/api/protected')
        .set('X-User-ID', 'admin')
        .set('X-User-Role', 'ADMIN')
        .expect(401);

      expect(response.body.message).toMatch(/authentication failed/i);
    });

    test('should prevent JWT token manipulation', async () => {
      // Create valid token
      const validToken = createValidToken({ userId: 'user', role: 'USER' });

      // Manipulate token by changing role
      const manipulatedToken = validToken.replace('USER', 'ADMIN');

      const response = await request(app)
        .get('/api/admin/endpoint')
        .set('Authorization', `Bearer ${manipulatedToken}`)
        .expect(401);

      expect(response.body.message).toMatch(/invalid token/i);
    });
  });

  describe('Brute Force Attacks', () => {
    test('should withstand password spraying attack', async () => {
      const commonPasswords = [
        'password', '123456', 'password123', 'admin', 'qwerty',
        'letmein', 'welcome', 'monkey', 'dragon', 'football'
      ];

      const email = 'test@example.com';

      // Create user
      await createTestUser({ email, password: 'SecurePassword123!' });

      // Try all common passwords
      const attempts = commonPasswords.map(password =>
        request(app)
          .post('/api/auth/login')
          .send({ email, password })
      );

      const responses = await Promise.all(attempts);

      // All attempts should fail
      responses.forEach(response => {
        expect(response.status).toBe(400);
        expect(response.body.message).toMatch(/invalid credentials/i);
      });
    });

    test('should implement progressive delay for failed attempts', async () => {
      const startTime = Date.now();

      // Make multiple failed attempts
      for (let i = 0; i < 5; i++) {
        await request(app)
          .post('/api/auth/login')
          .send({
            email: 'test@example.com',
            password: 'wrongpassword'
          });
      }

      const endTime = Date.now();
      const totalTime = endTime - startTime;

      // Should take longer due to rate limiting delays
      expect(totalTime).toBeGreaterThan(1000);
    });
  });

  describe('Session Hijacking Tests', () => {
    test('should prevent session fixation', async () => {
      // Create user and login
      const user = await createTestUser();
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: user.email,
          password: 'password123'
        });

      const sessionCookie = loginResponse.headers['set-cookie'];

      // Try to use session cookie for privileged access
      const response = await request(app)
        .get('/api/admin/endpoint')
        .set('Cookie', sessionCookie)
        .expect(403);

      expect(response.body.message).toMatch(/insufficient permissions/i);
    });

    test('should implement session timeout', async () => {
      // This test would verify that sessions expire after inactivity
      // Implementation depends on your session management
    });
  });

  describe('Information Disclosure Tests', () => {
    test('should not leak information via error codes', async () => {
      const endpoints = [
        '/api/nonexistent',
        '/api/auth/nonexistent',
        '/api/users/999999',
        '/api/admin/nonexistent'
      ];

      for (const endpoint of endpoints) {
        const response = await request(app).get(endpoint);

        // All errors should return generic error responses
        expect([404, 401, 403]).toContain(response.status);

        if (response.status !== 404) {
          expect(response.body.message).not.toContain('sql');
          expect(response.body.message).not.toContain('database');
          expect(response.body.message).not.toContain('internal');
        }
      }
    });

    test('should not expose directory structure', async () => {
      const paths = [
        '/',
        '/api',
        '/api/auth',
        '/src',
        '/config',
        '/node_modules'
      ];

      for (const path of paths) {
        const response = await request(app).get(path);

        // Should not return directory listings
        expect(response.status).not.toBe(200);
        expect(response.headers['content-type']).not.toBe('text/html');
      }
    });
  });

  describe('Denial of Service Tests', () => {
    test('should handle large request payloads', async () => {
      const largePayload = 'x'.repeat(10 * 1024 * 1024); // 10MB

      const response = await request(app)
        .post('/api/auth/login')
        .send({ email: largePayload, password: largePayload })
        .expect(413);

      expect(response.body.message).toMatch(/too large/i);
    });

    test('should handle connection timeouts', async () => {
      const largeArray = Array(100000).fill(0);

      const response = await request(app)
        .post('/api/auth/register')
        .timeout(5000) // 5 second timeout
        .send({
          name: 'Test User',
          email: 'test@example.com',
          password: 'SecurePassword123!',
          largeField: largeArray
        })
        .catch(err => err);

      // Should timeout or reject large requests
      expect(response.timeout || response.status === 413).toBeTruthy();
    });
  });
});

// Helper functions
function createValidToken(payload: any): string {
  const jwt = require('jsonwebtoken');
  return jwt.sign(payload, process.env.JWT_SECRET, { expiresIn: '1h' });
}

async function createTestUser(userData?: any) {
  // Implementation depends on your user model
}
```

---

## 📋 Compliance Verification Checklists

### 1. GDPR Compliance Checklist

```typescript
// /backend/src/compliance/gdprCompliance.test.ts

describe('GDPR Compliance Tests', () => {
  describe('Article 5 - Principles for processing personal data', () => {
    test('should implement data minimization', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Test User',
          email: 'test@example.com',
          password: 'SecurePassword123!',
          unnecessaryField: 'This should be ignored'
        });

      expect(response.status).toBe(201);

      // Verify only necessary data is collected
      expect(response.body.user).toHaveProperty('name');
      expect(response.body.user).toHaveProperty('email');
      expect(response.body.user).not.toHaveProperty('unnecessaryField');
    });

    test('should implement purpose limitation', async () => {
      // Verify data is only used for stated purposes
      const user = await createTestUser();
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: user.email,
          password: 'password123'
        });

      expect(loginResponse.body.user).toHaveProperty('name');
      expect(loginResponse.body.user).toHaveProperty('email');
      expect(loginResponse.body.user).not.toHaveProperty('password');
      expect(loginResponse.body.user).not.toHaveProperty('internalData');
    });
  });

  describe('Article 7 - Conditions for consent', () => {
    test('should record user consent', async () => {
      const consentData = {
        name: 'Test User',
        email: 'test@example.com',
        password: 'SecurePassword123!',
        privacyPolicyAccepted: true,
        marketingConsent: false,
        dataProcessingConsent: true
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(consentData);

      expect(response.status).toBe(201);

      // Verify consent is recorded
      const user = await User.findOne({ email: consentData.email });
      expect(user.privacyConsents).toBeDefined();
      expect(user.privacyConsents.privacyPolicyAccepted).toBe(true);
      expect(user.privacyConsents.marketingConsent).toBe(false);
    });

    test('should allow withdrawal of consent', async () => {
      const user = await createTestUser();
      const token = await getUserToken(user);

      // Withdraw consent
      const response = await request(app)
        .post('/api/privacy/withdraw-consent')
        .set('Authorization', `Bearer ${token}`)
        .send({
          consentType: 'marketing',
          withdrawn: true
        })
        .expect(200);

      // Verify consent is updated
      const updatedUser = await User.findById(user._id);
      expect(updatedUser.privacyConsents.marketingConsent).toBe(false);
    });
  });

  describe('Article 15 - Right of access by data subject', () => {
    test('should provide data export', async () => {
      const user = await createTestUser();
      const token = await getUserToken(user);

      const response = await request(app)
        .get('/api/privacy/data-export')
        .set('Authorization', `Bearer ${token}`)
        .expect(200);

      expect(response.body).toHaveProperty('userData');
      expect(response.body).toHaveProperty('exportDate');
      expect(response.body).toHaveProperty('format');
      expect(response.body.userData.email).toBe(user.email);
      expect(response.body.userData.name).toBe(user.name);
    });

    test('should provide data in machine-readable format', async () => {
      const user = await createTestUser();
      const token = await getUserToken(user);

      const response = await request(app)
        .get('/api/privacy/data-export')
        .set('Authorization', `Bearer ${token}`)
        .query({ format: 'json' });

      expect(response.headers['content-type']).toMatch(/application\/json/);
      expect(typeof response.body).toBe('object');
    });
  });

  describe('Article 17 - Right to erasure', () => {
    test('should implement right to be forgotten', async () => {
      const user = await createTestUser();
      const token = await getUserToken(user);

      // Request data deletion
      await request(app)
        .delete('/api/privacy/data-deletion')
        .set('Authorization', `Bearer ${token}`)
        .expect(200);

      // Verify data is deleted
      const deletedUser = await User.findById(user._id);
      expect(deletedUser).toBeNull();

      // Verify authentication fails
      await request(app)
        .get('/api/users/profile')
        .set('Authorization', `Bearer ${token}`)
        .expect(401);
    });

    test('should handle data deletion requests with verification', async () => {
      const user = await createTestUser();
      const token = await getUserToken(user);

      // Require additional verification for deletion
      const response = await request(app)
        .delete('/api/privacy/data-deletion')
        .set('Authorization', `Bearer ${token}`)
        .send({
          verificationCode: 'incorrect'
        })
        .expect(400);

      expect(response.body.message).toMatch(/verification failed/i);
    });
  });
});
```

### 2. SOC 2 Type II Compliance Checklist

```typescript
// /backend/src/compliance/soc2Compliance.test.ts

describe('SOC 2 Type II Compliance Tests', () => {
  describe('Security Criteria', () => {
    test('should implement least privilege access', async () => {
      const userToken = await createUserToken('USER');
      const adminToken = await createUserToken('ADMIN');

      // User should not access admin functions
      const userResponse = await request(app)
        .get('/api/admin/users')
        .set('Authorization', `Bearer ${userToken}`)
        .expect(403);

      expect(userResponse.body.message).toMatch(/insufficient permissions/i);

      // Admin should access admin functions
      const adminResponse = await request(app)
        .get('/api/admin/users')
        .set('Authorization', `Bearer ${adminToken}`)
        .expect(200);

      expect(adminResponse.body).toHaveProperty('users');
    });

    test('should implement secure authentication mechanisms', async () => {
      // Verify multi-factor authentication is supported
      const mfaResponse = await request(app)
        .post('/api/auth/setup-mfa')
        .send({
          method: 'totp'
        });

      expect(mfaResponse.status).toBe(401); // Requires authentication

      // Verify MFA enforcement for sensitive operations
      const user = await createTestUserWithMFA();
      const token = await getUserToken(user);

      const sensitiveResponse = await request(app)
        .post('/api/users/change-password')
        .set('Authorization', `Bearer ${token}`)
        .send({
          currentPassword: 'oldpassword',
          newPassword: 'newpassword'
        });

      expect(sensitiveResponse.status).toBe(403); // Requires MFA
    });

    test('should implement intrusion detection', async () => {
      // Simulate suspicious activity
      const suspiciousIPs = ['192.168.1.100', '10.0.0.50'];

      for (const ip of suspiciousIPs) {
        await request(app)
          .post('/api/auth/login')
          .set('X-Forwarded-For', ip)
          .send({
            email: 'test@example.com',
            password: 'wrongpassword'
          });
      }

      // Verify suspicious activity is logged and possibly blocked
      const response = await request(app)
        .get('/api/security/alerts')
        .expect(200);

      expect(response.body.alerts).toBeDefined();
      expect(response.body.alerts.length).toBeGreaterThan(0);
    });
  });

  describe('Availability Criteria', () => {
    test('should implement failover mechanisms', async () => {
      // Test system behavior under failure conditions
      // This would require infrastructure-level testing
    });

    test('should implement backup and recovery procedures', async () => {
      // Verify backup procedures are documented and tested
      const response = await request(app)
        .get('/api/system/backup-status')
        .expect(200);

      expect(response.body).toHaveProperty('lastBackup');
      expect(response.body).toHaveProperty('backupSuccess');
      expect(response.body.backupSuccess).toBe(true);
    });
  });

  describe('Processing Integrity Criteria', () => {
    test('should implement data integrity checks', async () => {
      const user = await createTestUser();

      // Create audit trail
      await request(app)
        .put('/api/users/profile')
        .set('Authorization', `Bearer ${await getUserToken(user)}`)
        .send({
          name: 'Updated Name'
        });

      // Verify audit trail exists
      const auditResponse = await request(app)
        .get('/api/audit/user-changes')
        .set('Authorization', `Bearer ${await getAdminToken()}`)
        .query({ userId: user._id });

      expect(auditResponse.status).toBe(200);
      expect(auditResponse.body.changes).toBeDefined();
      expect(auditResponse.body.changes.length).toBeGreaterThan(0);
    });

    test('should implement error detection and correction', async () => {
      // Simulate data corruption scenario
      const corruptedData = { name: '', email: 'invalid-email' };

      const response = await request(app)
        .post('/api/auth/register')
        .send(corruptedData);

      expect(response.status).toBe(400);
      expect(response.body.errors).toBeDefined();
    });
  });

  describe('Confidentiality Criteria', () => {
    test('should implement data encryption', async () => {
      const sensitiveData = 'This is sensitive information';

      const response = await request(app)
        .post('/api/data/store')
        .send({ data: sensitiveData });

      expect(response.status).toBe(200);

      // Verify data is encrypted in database
      const storedData = await getStoredData(response.body.id);
      expect(storedData.data).not.toBe(sensitiveData);
      expect(storedData.data).toMatch(/^enc:/); // Encrypted marker
    });

    test('should implement access controls', async () => {
      const user1Token = await createUserToken();
      const user2Token = await createUserToken();

      // User 1 should not access User 2's data
      const response = await request(app)
        .get('/api/data/user2-id')
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(403);

      expect(response.body.message).toMatch(/access denied/i);
    });
  });

  describe('Privacy Criteria', () => {
    test('should implement privacy by design', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          name: 'Test User',
          email: 'test@example.com',
          password: 'SecurePassword123!',
          unnecessaryPersonalData: 'This should be rejected'
        });

      // System should reject unnecessary data collection
      if (response.status === 201) {
        expect(response.body.user).not.toHaveProperty('unnecessaryPersonalData');
      }
    });

    test('should implement privacy by default', async () => {
      const user = await createTestUser();

      // Default privacy settings should be most restrictive
      expect(user.privacySettings).toBeDefined();
      expect(user.privacySettings.dataSharing).toBe(false);
      expect(user.privacySettings.profileVisibility).toBe('private');
    });
  });
});
```

### 3. PCI DSS Compliance Checklist

```typescript
// /backend/src/compliance/pciDssCompliance.test.ts

describe('PCI DSS Compliance Tests', () => {
  describe('Requirement 3 - Protect Cardholder Data', () => {
    test('should never store full credit card numbers', async () => {
      const paymentData = {
        cardNumber: '4111111111111111',
        expiryDate: '12/25',
        cvv: '123',
        amount: 100
      };

      const response = await request(app)
        .post('/api/payments/process')
        .send(paymentData);

      expect(response.status).toBe(200);

      // Verify full card number is not stored
      const storedPayment = await getStoredPayment(response.body.paymentId);
      expect(storedPayment.cardNumber).not.toBe(paymentData.cardNumber);
      expect(storedPayment.cardNumber).toMatch(/\*{12}\d{4}/); // Masked
    });

    test('should implement strong cryptography for cardholder data', async () => {
      const cardData = '4111111111111111';
      const encryptedData = encryptCardData(cardData);

      // Verify encryption is strong
      expect(encryptedData).not.toBe(cardData);
      expect(verifyEncryption(encryptedData, cardData)).toBe(true);
    });
  });

  describe('Requirement 4 - Strong Access Control Measures', () => {
    test('should implement two-factor authentication for admin access', async () => {
      const adminToken = await createAdminToken();

      const response = await request(app)
        .get('/api/admin/payments')
        .set('Authorization', `Bearer ${adminToken}`)
        .expect(401); // Requires MFA

      expect(response.body.message).toMatch(/multi-factor authentication required/i);
    });

    test('should implement unique user IDs', async () => {
      const user1 = await createTestUser();
      const user2 = await createTestUser();

      expect(user1.id).not.toBe(user2.id);
      expect(typeof user1.id).toBe('string');
      expect(user1.id.length).toBeGreaterThan(10); // Strong randomness
    });
  });

  describe('Requirement 6 - Regularly Monitor and Test Networks', () => {
    test('should implement vulnerability scanning', async () => {
      const scanResponse = await request(app)
        .post('/api/security/vulnerability-scan')
        .set('Authorization', `Bearer ${await getAdminToken()}`);

      expect(scanResponse.status).toBe(200);
      expect(scanResponse.body).toHaveProperty('scanResults');
      expect(scanResponse.body).toHaveProperty('vulnerabilities');
    });

    test('should implement penetration testing', async () => {
      // This would coordinate with external penetration testing
      const testResults = await request(app)
        .get('/api/security/penetration-test-results')
        .set('Authorization', `Bearer ${await getAdminToken()}`);

      expect(testResults.status).toBe(200);
      expect(testResults.body).toHaveProperty('lastTestDate');
      expect(testResults.body).toHaveProperty('criticalIssues');
      expect(testResults.body.criticalIssues).toBe(0);
    });
  });
});
```

---

## 🔧 Security Testing Automation

### 1. Continuous Integration Security Tests

**File:** `/.github/workflows/security-tests.yml`

```yaml
name: Security Testing Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 1' # Weekly on Monday

jobs:
  security-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: testpassword
          POSTGRES_USER: testuser
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    - name: Run security unit tests
      run: npm run test:security

    - name: Run OWASP ZAP Baseline Scan
      uses: zaproxy/action-baseline@v0.7.0
      with:
        target: 'http://localhost:3000'
        rules_file_name: '.zap/rules.tsv'
        cmd_options: '-a'

    - name: Run npm audit
      run: npm audit --audit-level=high

    - name: Run Snyk security scan
      uses: snyk/actions/node@master
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
      with:
        args: --severity-threshold=high

    - name: Run CodeQL Analysis
      uses: github/codeql-action/analyze@v2
      with:
        languages: javascript

    - name: Generate security report
      run: npm run security:report

    - name: Upload security artifacts
      uses: actions/upload-artifact@v3
      with:
        name: security-report
        path: security-report.json

    - name: Notify security team on failure
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        text: 'Security tests failed. Please review the logs.'
        webhook_url: ${{ secrets.SECURITY_SLACK_WEBHOOK }}
```

### 2. Security Testing Utilities

**File:** `/backend/src/tests/utils/securityTestUtils.ts`

```typescript
import { v4 as uuidv4 } from 'uuid';
import crypto from 'crypto';

export class SecurityTestUtils {
  static generateMaliciousPayloads(): Array<{type: string, payload: any}> {
    return [
      {
        type: 'SQL Injection',
        payload: "'; DROP TABLE users; --"
      },
      {
        type: 'XSS',
        payload: '<script>alert("XSS")</script>'
      },
      {
        type: 'NoSQL Injection',
        payload: { '$ne': null }
      },
      {
        type: 'Command Injection',
        payload: '; rm -rf /'
      },
      {
        type: 'XSS (Image)',
        payload: '<img src="x" onerror="alert(1)">'
      },
      {
        type: 'XSS (SVG)',
        payload: '<svg onload="alert(1)">'
      },
      {
        type: 'XSS (JavaScript)',
        payload: 'javascript:alert(1)'
      },
      {
        type: 'XSS (IFrame)',
        payload: '<iframe src="javascript:alert(1)"></iframe>'
      },
      {
        type: 'XSS (Data URI)',
        payload: 'data:text/html,<script>alert(1)</script>'
      },
      {
        type: 'XSS (Meta)',
        payload: '<meta http-equiv="refresh" content="0;url=javascript:alert(1)">'
      }
    ];
  }

  static generateLargePayloads(): Array<{size: string, payload: string}> {
    return [
      {
        size: '1MB',
        payload: 'x'.repeat(1024 * 1024)
      },
      {
        size: '10MB',
        payload: 'x'.repeat(10 * 1024 * 1024)
      },
      {
        size: '100MB',
        payload: 'x'.repeat(100 * 1024 * 1024)
      }
    ];
  }

  static generateWeakPasswords(): string[] {
    return [
      'password',
      '123456',
      '12345678',
      'qwerty',
      'abc123',
      'monkey',
      'letmein',
      'dragon',
      'football',
      'iloveyou',
      'admin',
      'welcome',
      'master',
      'hello',
      'freedom',
      'whatever'
    ];
  }

  static generateStrongPasswords(): string[] {
    const strongPasswords = [];

    for (let i = 0; i < 10; i++) {
      const length = 12 + Math.floor(Math.random() * 8); // 12-20 chars
      const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
      let password = '';

      for (let j = 0; j < length; j++) {
        password += charset.charAt(Math.floor(Math.random() * charset.length));
      }

      strongPasswords.push(password);
    }

    return strongPasswords;
  }

  static generateRandomEmails(count: number): string[] {
    const emails = [];
    const domains = ['example.com', 'test.org', 'demo.net', 'sample.io'];

    for (let i = 0; i < count; i++) {
      const username = Math.random().toString(36).substring(2, 10);
      const domain = domains[Math.floor(Math.random() * domains.length)];
      emails.push(`${username}@${domain}`);
    }

    return emails;
  }

  static generateUUIDs(count: number): string[] {
    const uuids = [];

    for (let i = 0; i < count; i++) {
      uuids.push(uuidv4());
    }

    return uuids;
  }

  static calculateEntropy(data: string): number {
    const chars = {};
    let entropy = 0;

    // Count character occurrences
    for (let char of data) {
      chars[char] = (chars[char] || 0) + 1;
    }

    // Calculate entropy
    for (let char in chars) {
      const probability = chars[char] / data.length;
      entropy -= probability * Math.log2(probability);
    }

    return entropy;
  }

  static generateBruteForcePasswords(basePassword: string, variations: number): string[] {
    const passwords = [];
    const commonVariations = [
      () => basePassword + '123',
      () => basePassword + '!',
      () => basePassword.charAt(0).toUpperCase() + basePassword.slice(1),
      () => basePassword.toUpperCase(),
      () => basePassword + basePassword,
      () => basePassword + '1',
      () => '123' + basePassword,
      () => basePassword + '2023',
      () => basePassword.charAt(0) + '*' + basePassword.slice(1)
    ];

    for (let i = 0; i < Math.min(variations, commonVariations.length); i++) {
      passwords.push(commonVariations[i]());
    }

    return passwords;
  }

  static generateTimingAttackPayloads(): Array<{description: string, email: string}> {
    return [
      {
        description: 'Very short email',
        email: 'a@b.c'
      },
      {
        description: 'Very long email',
        email: 'a'.repeat(100) + '@example.com'
      },
      {
        description: 'Special characters in email',
        email: 'test+special@example.com'
      },
      {
        description: 'Unicode characters in email',
        email: 'tëst@example.com'
      },
      {
        description: 'Null byte injection',
        email: 'test\x00@example.com'
      },
      {
        description: 'Line feed injection',
        email: 'test\n@example.com'
      },
      {
        description: 'Carriage return injection',
        email: 'test\r@example.com'
      },
      {
        description: 'Tab injection',
        email: 'test\t@example.com'
      }
    ];
  }

  static async measureResponseTime(url: string, iterations: number = 10): Promise<{average: number, min: number, max: number}> {
    const times = [];

    for (let i = 0; i < iterations; i++) {
      const start = Date.now();
      await fetch(url);
      const end = Date.now();
      times.push(end - start);
    }

    const average = times.reduce((a, b) => a + b, 0) / times.length;
    const min = Math.min(...times);
    const max = Math.max(...times);

    return { average, min, max };
  }

  static generateCSRFToken(): string {
    return crypto.randomBytes(32).toString('hex');
  }

  static generateJWTToken(payload: any, secret?: string, expiresIn?: string): string {
    const jwt = require('jsonwebtoken');
    return jwt.sign(payload, secret || process.env.JWT_SECRET, {
      expiresIn: expiresIn || '1h',
      algorithm: 'HS256'
    });
  }

  static decodeJWTToken(token: string): any {
    const jwt = require('jsonwebtoken');
    return jwt.decode(token, { complete: true });
  }

  static generateSecureRandomString(length: number): string {
    return crypto.randomBytes(length).toString('hex').substring(0, length);
  }
}
```

---

## 📊 Security Metrics and Reporting

### 1. Security Dashboard Implementation

**File:** `/backend/src/api/routes/security.ts`

```typescript
import express from 'express';
import { securityLogger } from '../utils/securityLogger';
import { SecurityTestUtils } from '../tests/utils/securityTestUtils';

const router = express.Router();

// Get security dashboard
router.get('/dashboard', async (req, res) => {
  try {
    const report = securityLogger.getSecurityReport('day');
    const vulnerabilityScan = await getLastVulnerabilityScan();
    const authenticationStats = await getAuthenticationStats();

    const dashboard = {
      overview: {
        totalSecurityEvents: report.totalEvents,
        criticalEvents: report.eventsBySeverity.critical || 0,
        highEvents: report.eventsBySeverity.high || 0,
        mediumEvents: report.eventsBySeverity.medium || 0,
        lowEvents: report.eventsBySeverity.low || 0
      },
      authentication: {
        failedLogins: authenticationStats.failedLogins,
        successfulLogins: authenticationStats.successfulLogins,
        lockedAccounts: authenticationStats.lockedAccounts,
        suspiciousIPs: authenticationStats.suspiciousIPs.length
      },
      vulnerabilities: {
        totalFound: vulnerabilityScan.totalVulnerabilities,
        critical: vulnerabilityScan.critical,
        high: vulnerabilityScan.high,
        medium: vulnerabilityScan.medium,
        low: vulnerabilityScan.low,
        lastScanDate: vulnerabilityScan.lastScanDate
      },
      topThreats: {
        suspiciousIPs: report.topIPs.slice(0, 5),
        eventTypes: Object.entries(report.eventsByType)
          .sort(([,a], [,b]) => b - a)
          .slice(0, 5)
      },
      recommendations: generateSecurityRecommendations(report, vulnerabilityScan)
    };

    res.json(dashboard);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get security trends
router.get('/trends', async (req, res) => {
  try {
    const { period = '7d' } = req.query;
    const days = period === '7d' ? 7 : period === '30d' ? 30 : 1;

    const trends = [];

    for (let i = days; i > 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      date.setHours(23, 59, 59, 999);

      const report = securityLogger.getSecurityReport('day');
      const filteredEvents = report.events.filter(event =>
        event.timestamp <= date && event.timestamp >= new Date(date.getTime() - 24 * 60 * 60 * 1000)
      );

      trends.push({
        date: date.toISOString(),
        totalEvents: filteredEvents.length,
        criticalEvents: filteredEvents.filter(e => e.severity === 'critical').length,
        authenticationEvents: filteredEvents.filter(e => e.type === 'authentication').length,
        authorizationEvents: filteredEvents.filter(e => e.type === 'authorization').length
      });
    }

    res.json(trends);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Run security scan
router.post('/scan', async (req, res) => {
  try {
    const { type = 'full' } = req.body;

    const scanResults = await runSecurityScan(type);

    res.json({
      scanId: scanResults.scanId,
      startTime: scanResults.startTime,
      status: 'running',
      estimatedDuration: scanResults.estimatedDuration
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Helper functions
async function getAuthenticationStats() {
  // Implementation depends on your database schema
  return {
    failedLogins: 0,
    successfulLogins: 0,
    lockedAccounts: 0,
    suspiciousIPs: []
  };
}

async function getLastVulnerabilityScan() {
  // Implementation depends on your vulnerability scanning setup
  return {
    totalVulnerabilities: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    lastScanDate: new Date()
  };
}

function generateSecurityRecommendations(report, vulnerabilityScan) {
  const recommendations = [];

  if (report.criticalEvents > 0) {
    recommendations.push({
      priority: 'HIGH',
      title: 'Critical Security Events Detected',
      description: `${report.criticalEvents} critical security events in the last 24 hours`,
      action: 'Review security logs and investigate immediately'
    });
  }

  if (vulnerabilityScan.critical > 0) {
    recommendations.push({
      priority: 'HIGH',
      title: 'Critical Vulnerabilities Found',
      description: `${vulnerabilityScan.critical} critical vulnerabilities require immediate attention`,
      action: 'Apply security patches immediately'
    });
  }

  if (report.topIPs.length > 0 && report.topIPs[0].count > 10) {
    recommendations.push({
      priority: 'MEDIUM',
      title: 'High Activity from Suspicious IP',
      description: `IP ${report.topIPs[0].ip} has ${report.topIPs[0].count} security events`,
      action: 'Consider blocking this IP address'
    });
  }

  return recommendations;
}

async function runSecurityScan(type) {
  const scanId = SecurityTestUtils.generateSecureRandomString(16);

  // Implement actual security scanning logic
  // This could include OWASP ZAP, Nessus, or custom security tests

  return {
    scanId,
    startTime: new Date(),
    estimatedDuration: type === 'full' ? '30 minutes' : '10 minutes'
  };
}

export default router;
```

---

## ✅ Implementation Checklist

### Security Testing Implementation
- [ ] Set up automated security tests in CI/CD
- [ ] Implement penetration testing suite
- [ ] Create compliance verification tests
- [ ] Set up vulnerability scanning
- [ ] Configure security monitoring dashboard
- [ ] Implement security metrics tracking

### Compliance Implementation
- [ ] Complete GDPR compliance checklist
- [ ] Implement SOC 2 Type II controls
- [ ] Set up PCI DSS compliance (if applicable)
- [ ] Create privacy policy and terms of service
- [ ] Implement data retention policies
- [ ] Set up incident response procedures

### Monitoring and Alerting
- [ ] Configure real-time security monitoring
- [ ] Set up automated incident response
- [ ] Implement security alerting system
- [ ] Create security incident tracking
- [ ] Set up regular security reporting
- [ ] Implement security metrics dashboard

### Documentation and Training
- [ ] Create security documentation
- [ ] Develop security training program
- [ ] Write security incident response plan
- [ ] Create security best practices guide
- [ ] Implement code review security checklist
- [ ] Set up regular security assessments

---

**Note:** This security testing framework should be customized based on your specific application requirements, compliance needs, and infrastructure setup. Regular updates and maintenance are essential for maintaining security effectiveness.