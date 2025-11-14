import { config } from '../config/env-validation';

// Set test environment variables before tests run
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-key-for-testing-only';
process.env.JWT_EXPIRES_IN = '1h';
process.env.MONGODB_URI = 'mongodb://localhost:27017/agent66-test';
process.env.REDIS_URL = 'redis://localhost:6379/1';

// Mock console methods to reduce noise in test output
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Increase timeout for async operations
jest.setTimeout(30000);

// Global test helpers
global.testHelpers = {
  generateTestUser: (overrides = {}) => ({
    email: 'test@example.com',
    firstName: 'Test',
    lastName: 'User',
    role: 'CREW',
    ...overrides
  }),

  generateTestProject: (overrides = {}) => ({
    name: 'Test Project',
    description: 'A test project for unit testing',
    status: 'ACTIVE',
    startDate: new Date(),
    ...overrides
  }),

  generateTimeEntry: (overrides = {}) => ({
    date: new Date(),
    startTime: '09:00',
    endTime: '17:00',
    breakDuration: 60,
    description: 'Test work entry',
    ...overrides
  })
};

// Mock external services
jest.mock('../utils/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
    security: jest.fn(),
  }
}));

// Clear all mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
});