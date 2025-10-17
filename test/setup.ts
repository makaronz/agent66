import { beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { config } from 'dotenv';

// Load test environment variables
config({ path: '.env.test' });

// Set test environment
process.env.NODE_ENV = 'test';
process.env.TEST_MODE = 'true';
process.env.MOCK_EXCHANGES = 'true';
process.env.MOCK_DATA = 'true';
process.env.MOCK_ORDERS = 'true';

// Test database configuration
process.env.TEST_DATABASE_URL = process.env.TEST_DATABASE_URL || 'postgresql://test:test@localhost:5432/smc_trading_test';
process.env.TEST_REDIS_URL = process.env.TEST_REDIS_URL || 'redis://localhost:6379/1';

// Global test setup
beforeAll(async () => {
  console.log('🧪 Setting up test environment...');

  // Initialize test databases
  await setupTestDatabases();

  // Initialize test services
  await setupTestServices();

  console.log('✅ Test environment setup complete');
});

beforeEach(async () => {
  // Reset test data before each test
  await resetTestData();
});

afterEach(async () => {
  // Clean up test data after each test
  await cleanupTestData();
});

afterAll(async () => {
  console.log('🧹 Cleaning up test environment...');

  // Clean up test databases
  await cleanupTestDatabases();

  // Clean up test services
  await cleanupTestServices();

  console.log('✅ Test environment cleanup complete');
});

// Database setup functions
async function setupTestDatabases() {
  // Implementation for setting up test databases
  // This would connect to test databases and create schemas
}

async function cleanupTestDatabases() {
  // Implementation for cleaning up test databases
  // This would drop test data and close connections
}

// Service setup functions
async function setupTestServices() {
  // Implementation for setting up test services
  // This would initialize mock services and dependencies
}

async function cleanupTestServices() {
  // Implementation for cleaning up test services
  // This would stop mock services and clean up resources
}

// Data management functions
async function resetTestData() {
  // Implementation for resetting test data
  // This would clear test data to ensure test isolation
}

async function cleanupTestData() {
  // Implementation for cleaning up test data
  // This would clean up any remaining test data
}

// Export test utilities
export const testUtils = {
  setupTestDatabases,
  cleanupTestDatabases,
  setupTestServices,
  cleanupTestServices,
  resetTestData,
  cleanupTestData,
};

// Global test mocks
export const mockData = {
  user: {
    id: 'test-user-id',
    email: 'test@example.com',
    username: 'testuser',
  },
  tradingAccount: {
    id: 'test-account-id',
    userId: 'test-user-id',
    balance: 10000,
    currency: 'USD',
  },
  trade: {
    id: 'test-trade-id',
    symbol: 'BTCUSDT',
    side: 'buy',
    quantity: 0.1,
    price: 50000,
    status: 'filled',
  },
};

// Test configuration
export const testConfig = {
  timeout: 30000,
  retries: 3,
  parallel: true,
  verbose: true,
};