import request from 'supertest';
import app from '../../server';
import { connectDB, closeDB, clearDB } from '../helpers/database';

describe('Authentication Flow Integration Tests', () => {
  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
  });

  describe('Complete Registration to Dashboard Flow', () => {
    it('should handle complete user registration and first login flow', async () => {
      const userData = {
        name: 'John Doe',
        email: 'john.doe@filmcrew.com',
        password: 'SecurePassword123!',
        department: 'Camera',
        phone: '+1234567890'
      };

      // Step 1: Register new user
      const registerResponse = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      expect(registerResponse.body).toHaveProperty('token');
      expect(registerResponse.body.user.email).toBe(userData.email);
      expect(registerResponse.body.user).not.toHaveProperty('password');

      const authToken = registerResponse.body.token;

      // Step 2: Verify user can access protected routes with token
      const profileResponse = await request(app)
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(profileResponse.body.email).toBe(userData.email);

      // Step 3: Login with new credentials (simulate new session)
      await request(app)
        .post('/api/auth/logout')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: userData.email,
          password: userData.password
        })
        .expect(200);

      expect(loginResponse.body).toHaveProperty('token');
      expect(loginResponse.body.user.email).toBe(userData.email);

      // Step 4: Verify user profile after login
      const newToken = loginResponse.body.token;
      const newProfileResponse = await request(app)
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${newToken}`)
        .expect(200);

      expect(newProfileResponse.body.email).toBe(userData.email);
      expect(newProfileResponse.body.department).toBe(userData.department);
    });

    it('should handle session expiration gracefully', async () => {
      const userData = {
        name: 'Jane Smith',
        email: 'jane.smith@filmcrew.com',
        password: 'AnotherSecurePassword123!'
      };

      // Register and login
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: userData.email,
          password: userData.password
        });

      const expiredToken = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2MzZmZmZmZmZmZmZmZmZmZiIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImlhdCI6MTY2NjY2NjY2NiwiZXhwIjoxNjY2NjY2NjY2fQ.invalid';

      // Try to access protected route with expired token
      const response = await request(app)
        .get('/api/user/profile')
        .set('Authorization', expiredToken)
        .expect(401);

      expect(response.body.message).toContain('Invalid or expired token');
    });
  });

  describe('Password Reset Flow', () => {
    it('should handle complete password reset flow', async () => {
      const userData = {
        name: 'Password Test User',
        email: 'password.test@filmcrew.com',
        password: 'OriginalPassword123!'
      };

      // Register user
      await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      // Request password reset
      const resetRequestResponse = await request(app)
        .post('/api/auth/forgot-password')
        .send({ email: userData.email })
        .expect(200);

      expect(resetRequestResponse.body.message).toContain('reset email sent');

      // In a real implementation, this would involve email verification
      // For testing, we'll simulate the reset token validation
      const resetToken = 'test-reset-token';

      // Reset password with token
      const newPassword = 'NewPassword456!';
      const resetResponse = await request(app)
        .post('/api/auth/reset-password')
        .send({
          token: resetToken,
          newPassword: newPassword
        });

      // Login with new password
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: userData.email,
          password: newPassword
        });

      expect(loginResponse.body).toHaveProperty('token');
    });
  });

  describe('Role-Based Access Control Integration', () => {
    let crewToken: string;
    let supervisorToken: string;
    let adminToken: string;

    beforeEach(async () => {
      // Create users with different roles
      const crewUser = {
        name: 'Crew Member',
        email: 'crew@filmcrew.com',
        password: 'Password123!',
        role: 'CREW'
      };

      const supervisorUser = {
        name: 'Supervisor',
        email: 'supervisor@filmcrew.com',
        password: 'Password123!',
        role: 'SUPERVISOR'
      };

      const adminUser = {
        name: 'Admin',
        email: 'admin@filmcrew.com',
        password: 'Password123!',
        role: 'ADMIN'
      };

      const crewResponse = await request(app)
        .post('/api/auth/register')
        .send(crewUser);

      const supervisorResponse = await request(app)
        .post('/api/auth/register')
        .send(supervisorUser);

      const adminResponse = await request(app)
        .post('/api/auth/register')
        .send(adminUser);

      crewToken = crewResponse.body.token;
      supervisorToken = supervisorResponse.body.token;
      adminToken = adminResponse.body.token;
    });

    it('should enforce role-based permissions correctly', async () => {
      // Test crew member access
      const crewProfileResponse = await request(app)
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${crewToken}`)
        .expect(200);

      expect(crewProfileResponse.body.role).toBe('CREW');

      // Test supervisor access to crew management
      const supervisorManagementResponse = await request(app)
        .get('/api/supervisor/crew')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .expect(200);

      // Test crew member denied access to supervisor endpoints
      const crewDeniedResponse = await request(app)
        .get('/api/supervisor/crew')
        .set('Authorization', `Bearer ${crewToken}`)
        .expect(403);

      expect(crewDeniedResponse.body.message).toContain('insufficient permissions');

      // Test admin access to system management
      const adminSystemResponse = await request(app)
        .get('/api/admin/system')
        .set('Authorization', `Bearer ${adminToken}`)
        .expect(200);

      // Test supervisor denied access to admin endpoints
      const supervisorDeniedResponse = await request(app)
        .get('/api/admin/system')
        .set('Authorization', `Bearer ${supervisorToken}`)
        .expect(403);

      expect(supervisorDeniedResponse.body.message).toContain('insufficient permissions');
    });
  });

  describe('Token Refresh Flow', () => {
    it('should handle token refresh correctly', async () => {
      const userData = {
        name: 'Refresh Test User',
        email: 'refresh.test@filmcrew.com',
        password: 'Password123!'
      };

      // Login to get initial token
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: userData.email,
          password: userData.password
        })
        .expect(200);

      const initialToken = loginResponse.body.token;

      // Use token to access protected route
      const profileResponse = await request(app)
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${initialToken}`)
        .expect(200);

      // Request token refresh
      const refreshResponse = await request(app)
        .post('/api/auth/refresh')
        .set('Authorization', `Bearer ${initialToken}`)
        .expect(200);

      expect(refreshResponse.body).toHaveProperty('token');
      expect(refreshResponse.body.token).not.toBe(initialToken);

      // Use new token to access protected route
      const newProfileResponse = await request(app)
        .get('/api/user/profile')
        .set('Authorization', `Bearer ${refreshResponse.body.token}`)
        .expect(200);

      expect(newProfileResponse.body.email).toBe(userData.email);
    });
  });
});