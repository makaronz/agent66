import request from 'supertest';
import app from '../server';
import User from '../models/User';
import { connectDB, closeDB, clearDB } from './helpers/database';

describe('Authentication API Tests', () => {
  beforeAll(async () => {
    await connectDB();
  });

  afterAll(async () => {
    await closeDB();
  });

  beforeEach(async () => {
    await clearDB();
  });

  describe('POST /api/auth/register', () => {
    const validUser = {
      name: 'John Doe',
      email: 'john.doe@filmcrew.com',
      password: 'password123',
      role: 'crew_member'
    };

    it('should register a new crew member successfully', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send(validUser)
        .expect(201);

      expect(response.body).toHaveProperty('token');
      expect(response.body.user).toHaveProperty('email', validUser.email);
      expect(response.body.user).not.toHaveProperty('password');
    });

    it('should return 400 for invalid email format', async () => {
      const invalidUser = { ...validUser, email: 'invalid-email' };

      const response = await request(app)
        .post('/api/auth/register')
        .send(invalidUser)
        .expect(400);

      expect(response.body).toHaveProperty('message');
    });

    it('should return 400 for duplicate email', async () => {
      // First registration
      await request(app)
        .post('/api/auth/register')
        .send(validUser)
        .expect(201);

      // Duplicate registration
      const response = await request(app)
        .post('/api/auth/register')
        .send(validUser)
        .expect(400);

      expect(response.body.message).toContain('already exists');
    });

    it('should hash password before saving', async () => {
      await request(app)
        .post('/api/auth/register')
        .send(validUser)
        .expect(201);

      const user = await User.findOne({ email: validUser.email }).select('+password');
      expect(user?.password).not.toBe(validUser.password);
      expect(user?.password).toMatch(/^\$2[aby]\$\d+\$/); // bcrypt hash pattern
    });
  });

  describe('POST /api/auth/login', () => {
    const testUser = {
      name: 'Jane Smith',
      email: 'jane.smith@filmcrew.com',
      password: 'password123'
    };

    beforeEach(async () => {
      await request(app)
        .post('/api/auth/register')
        .send(testUser);
    });

    it('should login with valid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: testUser.password
        })
        .expect(200);

      expect(response.body).toHaveProperty('token');
      expect(response.body.user).toHaveProperty('email', testUser.email);
    });

    it('should return 400 for invalid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          password: 'wrongpassword'
        })
        .expect(400);

      expect(response.body.message).toContain('Invalid credentials');
    });

    it('should return 400 for non-existent user', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@filmcrew.com',
          password: 'password123'
        })
        .expect(400);

      expect(response.body.message).toContain('Invalid credentials');
    });
  });
});