# Backend Testing Suite

This comprehensive testing suite provides complete coverage for the Agent66 backend application, ensuring reliability, security, and performance.

## Test Structure

```
src/tests/
├── middleware/           # Middleware testing
│   ├── auth.test.ts     # Authentication middleware
│   ├── errorHandler.test.ts # Error handling
│   └── validation.test.ts # Request validation
├── models/              # Database model testing
│   └── User.test.ts     # User model tests
├── routes/              # API endpoint testing
│   ├── health.test.ts   # Health check endpoints
│   └── metrics.test.ts  # Metrics endpoints
├── integration/         # Integration testing
│   └── auth-flow.test.ts # Complete auth flows
├── websocket/           # WebSocket testing
│   └── server.test.ts   # WebSocket server functionality
├── security/            # Security testing
│   └── auth-security.test.ts # Authentication security
├── performance/         # Performance testing
│   └── load.test.ts     # Load and stress tests
├── helpers/             # Test utilities
│   ├── database.ts      # Database setup/teardown
│   └── auth.ts          # Authentication helpers
├── fixtures/            # Test data
│   ├── film-industry-data.ts
│   └── test-database.ts
├── setup.ts            # Global test setup
└── README.md           # This file
```

## Running Tests

### Basic Test Commands

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test categories
npm run test:unit         # Unit tests only
npm run test:integration  # Integration tests only
npm run test:security     # Security tests only
npm run test:performance  # Performance tests only

# CI mode (no watch, coverage enabled)
npm run test:ci

# Debug mode
npm run test:debug
```

### Test Categories

#### 1. Unit Tests (`test:unit`)
- **Middleware Testing**: Individual middleware functions
- **Model Testing**: Database model validation and methods
- **Route Testing**: Individual API endpoints
- **Utility Testing**: Helper functions and utilities

#### 2. Integration Tests (`test:integration`)
- **Authentication Flows**: Complete register/login workflows
- **Multi-step Operations**: End-to-end user journeys
- **Cross-service Integration**: Database and external service interactions

#### 3. Security Tests (`test:security`)
- **Input Validation**: SQL injection, XSS prevention
- **Authentication Security**: JWT token handling, rate limiting
- **Authorization Testing**: Role-based access control
- **Data Exposure**: Sensitive information protection

#### 4. Performance Tests (`test:performance`)
- **Load Testing**: Concurrent request handling
- **Response Time Benchmarks**: Performance SLA verification
- **Memory Usage**: Resource consumption monitoring
- **Stress Testing**: System behavior under extreme load

## Test Configuration

### Jest Configuration (`jest.config.js`)

- **Preset**: TypeScript support with `ts-jest`
- **Environment**: Node.js for backend testing
- **Coverage**: 80% minimum threshold
- **Timeout**: 30 seconds for async operations
- **Workers**: 50% of available CPUs for parallel execution

### Test Environment

- **Database**: In-memory MongoDB using `mongodb-memory-server`
- **Authentication**: Test JWT tokens with dedicated secret
- **Logging**: Mocked logger to reduce test noise
- **Timeouts**: Extended for database operations

## Key Features

### 1. Database Isolation

Each test runs with a fresh in-memory database:

```typescript
beforeAll(async () => await connectDB());
afterAll(async () => await closeDB());
beforeEach(async () => await clearDB());
```

### 2. Authentication Helpers

Simplified user creation and authentication:

```typescript
const { user, token } = await createTestUser({
  email: 'test@example.com',
  role: 'ADMIN'
});
```

### 3. Mock External Services

All external dependencies are mocked:

```typescript
jest.mock('../utils/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    // ...
  }
}));
```

### 4. Coverage Reporting

Comprehensive coverage with:
- Line, branch, function, and statement coverage
- HTML report generation
- JSON summary for CI integration
- Minimum 80% threshold enforcement

## Test Data Management

### Fixtures

Test data is managed through fixtures in `src/tests/fixtures/`:

- **Film Industry Data**: Realistic film production scenarios
- **Test Database**: Pre-configured test users and projects
- **Authentication Scenarios**: Various user roles and permissions

### Data Factory Pattern

Test data is generated using factory functions:

```typescript
global.testHelpers.generateTestUser(overrides);
global.testHelpers.generateTestProject(overrides);
global.testHelpers.generateTimeEntry(overrides);
```

## Security Testing

### Input Validation

- **SQL Injection**: Malicious input attempts
- **XSS Prevention**: Script injection testing
- **Buffer Overflow**: Oversized payload handling
- **Email Validation**: Strict email format checking

### Authentication Security

- **JWT Token Validation**: Algorithm, signature, expiration
- **Rate Limiting**: Brute force prevention
- **Session Management**: Token replay attacks
- **Privilege Escalation**: Role-based access enforcement

## Performance Testing

### Load Testing

- **Concurrent Requests**: 50+ simultaneous requests
- **Response Time SLAs**: Sub-100ms for critical paths
- **Memory Usage**: Leak detection and monitoring
- **Database Performance**: Query optimization validation

### Stress Testing

- **Sustained Load**: Performance under continuous load
- **Load Spikes**: Recovery from traffic bursts
- **Resource Limits**: System boundary testing
- **Error Recovery**: Graceful degradation

## CI/CD Integration

### Quality Gates

- **Coverage Threshold**: Minimum 80% code coverage
- **All Tests Pass**: Zero tolerance for test failures
- **Security Tests**: All security validations must pass
- **Performance Benchmarks**: Response time SLAs enforced

### Test Reports

- **Coverage Reports**: HTML and JSON formats
- **Test Results**: Detailed test execution logs
- **Performance Metrics**: Response time and resource usage
- **Security Scan**: Vulnerability assessment results

## Best Practices

### 1. Test Organization

- **Descriptive Names**: Clear, comprehensive test descriptions
- **Logical Grouping**: Related tests grouped in `describe` blocks
- **Setup/Teardown**: Proper resource management
- **Isolation**: Tests independent of each other

### 2. Assertion Quality

- **Specific Expectations**: Test exact behavior, not just success
- **Error Handling**: Verify proper error responses
- **Edge Cases**: Test boundary conditions
- **Negative Testing**: Invalid input handling

### 3. Mock Management

- **Consistent Mocks**: Same mocks across related tests
- **Mock Cleanup**: Reset mocks between tests
- **Realistic Data**: Use representative test data
- **External Services**: Mock all external dependencies

### 4. Performance Considerations

- **Efficient Setup**: Minimal test preparation time
- **Parallel Execution**: Leverage Jest's parallel capabilities
- **Resource Cleanup**: Proper teardown to prevent memory leaks
- **Test Isolation**: No shared state between tests

## Debugging Tests

### Common Issues

1. **Database Connection**: Ensure in-memory MongoDB is properly configured
2. **Async Operations**: Use proper `async/await` and error handling
3. **Mock Failures**: Verify mock setup and expectations
4. **Timeout Issues**: Increase timeout for complex operations

### Debug Mode

Run tests with Node.js debugger:

```bash
npm run test:debug
```

This allows you to:
- Set breakpoints in test files
- Inspect variables during execution
- Step through test logic
- Analyze failure conditions

## Continuous Monitoring

### Metrics to Track

- **Test Execution Time**: Identify slow tests
- **Coverage Trends**: Monitor coverage changes
- **Flaky Tests**: Detect inconsistent test behavior
- **Performance Regression**: Catch performance degradation

### Alerts and Notifications

- **Test Failures**: Immediate notification on CI failures
- **Coverage Drops**: Alert when coverage falls below threshold
- **Performance Issues**: Notify when benchmarks are missed
- **Security Vulnerabilities**: Alert on security test failures

This comprehensive testing foundation ensures the Agent66 backend maintains high quality, security, and performance standards throughout development and deployment.