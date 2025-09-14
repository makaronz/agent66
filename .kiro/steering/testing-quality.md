---
inclusion: fileMatch
fileMatchPattern: '**/*.{test,spec}.{ts,tsx,js,jsx}'
---

# Testing & Code Quality Standards for App_v2

## 🧪 Testing Strategy & Standards

### Test Pyramid Implementation

```typescript
// ✅ CORRECT: Comprehensive test pyramid
/*
    /\     E2E Tests (10%)
   /  \    - Critical user journeys
  /____\   - Cross-browser testing
 /      \  Integration Tests (20%)
/        \ - API endpoint testing
/__________\ Unit Tests (70%)
            - Component logic
            - Service functions
            - Utility functions
*/

// Test coverage targets
const COVERAGE_TARGETS = {
  statements: 80,
  branches: 75,
  functions: 80,
  lines: 80
} as const;
```

### Unit Testing Standards

#### Frontend Component Testing
```typescript
// ✅ CORRECT: Comprehensive component testing
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import LoginForm from '../LoginForm';

// Test utilities
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false }
  }
});

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe('LoginForm', () => {
  const mockOnSubmit = vi.fn();
  
  beforeEach(() => {
    mockOnSubmit.mockClear();
  });
  
  it('should render all form fields', () => {
    renderWithProviders(<LoginForm onSubmit={mockOnSubmit} />);
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });
  
  it('should show validation errors for invalid input', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginForm onSubmit={mockOnSubmit} />);
    
    const submitButton = screen.getByRole('button', { name: /login/i });
    await user.click(submitButton);
    
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });
  
  it('should submit form with valid data', async () => {
    const user = userEvent.setup();
    const validData = {
      email: 'test@example.com',
      password: 'ValidPassword123!'
    };
    
    renderWithProviders(<LoginForm onSubmit={mockOnSubmit} />);
    
    await user.type(screen.getByLabelText(/email/i), validData.email);
    await user.type(screen.getByLabelText(/password/i), validData.password);
    await user.click(screen.getByRole('button', { name: /login/i }));
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(validData);
    });
  });
  
  it('should handle loading state', () => {
    renderWithProviders(<LoginForm onSubmit={mockOnSubmit} loading={true} />);
    
    const submitButton = screen.getByRole('button', { name: /logging in/i });
    expect(submitButton).toBeDisabled();
  });
});

// ❌ INCORRECT: Shallow testing
describe('LoginForm - Bad Example', () => {
  it('should render', () => {
    render(<LoginForm />);
    expect(screen.getByText('Login')).toBeInTheDocument();
  });
});
```

#### Custom Hook Testing
```typescript
// ✅ CORRECT: Custom hook testing with renderHook
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { useAuth } from '../useAuth';
import * as authApi from '../../services/authApi';

// Mock API
vi.mock('../../services/authApi');
const mockAuthApi = vi.mocked(authApi);

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });
  
  it('should initialize with no user when no token exists', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper()
    });
    
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.loading).toBe(false);
  });
  
  it('should login user successfully', async () => {
    const mockUser = { id: '1', email: 'test@example.com', name: 'Test User' };
    const mockResponse = { user: mockUser, token: 'mock-token' };
    
    mockAuthApi.login.mockResolvedValueOnce(mockResponse);
    
    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper()
    });
    
    await result.current.login('test@example.com', 'password');
    
    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(localStorage.getItem('token')).toBe('mock-token');
    });
  });
  
  it('should handle login error', async () => {
    const mockError = new Error('Invalid credentials');
    mockAuthApi.login.mockRejectedValueOnce(mockError);
    
    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper()
    });
    
    await expect(
      result.current.login('test@example.com', 'wrong-password')
    ).rejects.toThrow('Invalid credentials');
    
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });
});
```

#### Backend Service Testing
```typescript
// ✅ CORRECT: Service layer testing with mocks
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { UserService } from '../UserService';
import { UserRepository } from '../repositories/UserRepository';
import { CacheService } from '../CacheService';
import { Logger } from '../utils/Logger';
import { createTestUser } from '../../test-utils/factories';

// Mock dependencies
vi.mock('../repositories/UserRepository');
vi.mock('../CacheService');
vi.mock('../utils/Logger');

const mockUserRepository = vi.mocked(UserRepository);
const mockCacheService = vi.mocked(CacheService);
const mockLogger = vi.mocked(Logger);

describe('UserService', () => {
  let userService: UserService;
  let mockRepository: jest.Mocked<UserRepository>;
  let mockCache: jest.Mocked<CacheService>;
  let mockLog: jest.Mocked<Logger>;
  
  beforeEach(() => {
    mockRepository = new mockUserRepository() as jest.Mocked<UserRepository>;
    mockCache = new mockCacheService() as jest.Mocked<CacheService>;
    mockLog = new mockLogger() as jest.Mocked<Logger>;
    
    userService = new UserService(mockRepository, mockLog, mockCache);
  });
  
  describe('findById', () => {
    it('should return user from cache if available', async () => {
      const testUser = createTestUser();
      mockCache.get.mockResolvedValueOnce(testUser);
      
      const result = await userService.findById(testUser.id);
      
      expect(result).toEqual(testUser);
      expect(mockCache.get).toHaveBeenCalledWith(`user:${testUser.id}`);
      expect(mockRepository.findById).not.toHaveBeenCalled();
      expect(mockLog.debug).toHaveBeenCalledWith(
        'User found in cache', 
        { userId: testUser.id }
      );
    });
    
    it('should fetch from repository and cache when not in cache', async () => {
      const testUser = createTestUser();
      mockCache.get.mockResolvedValueOnce(null);
      mockRepository.findById.mockResolvedValueOnce(testUser);
      
      const result = await userService.findById(testUser.id);
      
      expect(result).toEqual(testUser);
      expect(mockCache.get).toHaveBeenCalledWith(`user:${testUser.id}`);
      expect(mockRepository.findById).toHaveBeenCalledWith(testUser.id);
      expect(mockCache.set).toHaveBeenCalledWith(`user:${testUser.id}`, testUser, 3600);
    });
    
    it('should return null when user not found', async () => {
      mockCache.get.mockResolvedValueOnce(null);
      mockRepository.findById.mockResolvedValueOnce(null);
      
      const result = await userService.findById('non-existent-id');
      
      expect(result).toBeNull();
      expect(mockCache.set).not.toHaveBeenCalled();
    });
    
    it('should handle repository errors gracefully', async () => {
      const error = new Error('Database connection failed');
      mockCache.get.mockResolvedValueOnce(null);
      mockRepository.findById.mockRejectedValueOnce(error);
      
      await expect(userService.findById('test-id')).rejects.toThrow(error);
      expect(mockLog.error).toHaveBeenCalledWith(
        'Failed to find user by ID',
        { userId: 'test-id', error: error.message }
      );
    });
  });
});
```

### Integration Testing Standards

#### API Endpoint Testing
```typescript
// ✅ CORRECT: Comprehensive API testing
import request from 'supertest';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import app from '../server';
import { connectTestDB, clearTestDB, closeTestDB } from '../../test-utils/database';
import { createTestUser, createTestPost } from '../../test-utils/factories';
import { generateAuthToken } from '../../test-utils/auth';

describe('POST /api/posts', () => {
  beforeEach(async () => {
    await connectTestDB();
  });
  
  afterEach(async () => {
    await clearTestDB();
  });
  
  afterAll(async () => {
    await closeTestDB();
  });
  
  it('should create a new post with valid data', async () => {
    const user = await createTestUser();
    const token = generateAuthToken(user);
    const postData = {
      title: 'Test Post',
      content: 'This is a test post content'
    };
    
    const response = await request(app)
      .post('/api/posts')
      .set('Authorization', `Bearer ${token}`)
      .send(postData)
      .expect(201);
    
    expect(response.body).toMatchObject({
      success: true,
      data: {
        title: postData.title,
        content: postData.content,
        author: {
          id: user.id,
          name: user.name,
          email: user.email
        }
      }
    });
    
    expect(response.body.data.id).toBeDefined();
    expect(response.body.data.createdAt).toBeDefined();
  });
  
  it('should return 401 when no authentication token provided', async () => {
    const postData = {
      title: 'Test Post',
      content: 'This is a test post content'
    };
    
    const response = await request(app)
      .post('/api/posts')
      .send(postData)
      .expect(401);
    
    expect(response.body).toMatchObject({
      success: false,
      error: {
        code: 'UNAUTHORIZED',
        message: 'Authentication token required'
      }
    });
  });
  
  it('should return 400 for invalid post data', async () => {
    const user = await createTestUser();
    const token = generateAuthToken(user);
    const invalidData = {
      title: '', // Too short
      content: 'x' // Too short
    };
    
    const response = await request(app)
      .post('/api/posts')
      .set('Authorization', `Bearer ${token}`)
      .send(invalidData)
      .expect(400);
    
    expect(response.body).toMatchObject({
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Validation failed'
      }
    });
    
    expect(response.body.error.details).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          path: ['title'],
          message: expect.stringContaining('at least')
        }),
        expect.objectContaining({
          path: ['content'],
          message: expect.stringContaining('at least')
        })
      ])
    );
  });
  
  it('should handle database errors gracefully', async () => {
    const user = await createTestUser();
    const token = generateAuthToken(user);
    
    // Mock database error by closing connection
    await closeTestDB();
    
    const response = await request(app)
      .post('/api/posts')
      .set('Authorization', `Bearer ${token}`)
      .send({
        title: 'Test Post',
        content: 'This is a test post content'
      })
      .expect(500);
    
    expect(response.body).toMatchObject({
      success: false,
      error: {
        code: 'INTERNAL_SERVER_ERROR',
        message: 'An unexpected error occurred'
      }
    });
  });
});
```

### End-to-End Testing Standards

#### Critical User Journey Testing
```typescript
// ✅ CORRECT: E2E testing with Playwright
import { test, expect, Page } from '@playwright/test';

test.describe('User Authentication Flow', () => {
  let page: Page;
  
  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto('/');
  });
  
  test('should complete full login flow', async () => {
    // Navigate to login page
    await page.click('text=Login');
    await expect(page).toHaveURL('/login');
    
    // Fill login form
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'ValidPassword123!');
    
    // Submit form
    await page.click('[data-testid=login-button]');
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // Verify user is logged in
    await expect(page.locator('[data-testid=user-menu]')).toBeVisible();
    await expect(page.locator('text=Welcome back')).toBeVisible();
  });
  
  test('should show error for invalid credentials', async () => {
    await page.goto('/login');
    
    await page.fill('[data-testid=email-input]', 'invalid@example.com');
    await page.fill('[data-testid=password-input]', 'wrongpassword');
    await page.click('[data-testid=login-button]');
    
    // Should stay on login page and show error
    await expect(page).toHaveURL('/login');
    await expect(page.locator('[data-testid=error-message]')).toContainText('Invalid credentials');
  });
  
  test('should handle network errors gracefully', async () => {
    // Simulate network failure
    await page.route('**/api/auth/login', route => route.abort());
    
    await page.goto('/login');
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'ValidPassword123!');
    await page.click('[data-testid=login-button]');
    
    await expect(page.locator('[data-testid=error-message]')).toContainText('Network error');
  });
});

test.describe('Post Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'ValidPassword123!');
    await page.click('[data-testid=login-button]');
    await expect(page).toHaveURL('/dashboard');
  });
  
  test('should create, edit, and delete a post', async ({ page }) => {
    // Create post
    await page.click('[data-testid=add-post-button]');
    await expect(page).toHaveURL('/posts/new');
    
    await page.fill('[data-testid=post-title]', 'Test Post Title');
    await page.fill('[data-testid=post-content]', 'This is test post content');
    await page.click('[data-testid=save-post-button]');
    
    // Verify post was created
    await expect(page).toHaveURL('/posts');
    await expect(page.locator('[data-testid=post-item]')).toContainText('Test Post Title');
    
    // Edit post
    await page.click('[data-testid=edit-post-button]');
    await page.fill('[data-testid=post-title]', 'Updated Post Title');
    await page.click('[data-testid=save-post-button]');
    
    // Verify post was updated
    await expect(page.locator('[data-testid=post-item]')).toContainText('Updated Post Title');
    
    // Delete post
    await page.click('[data-testid=delete-post-button]');
    await page.click('[data-testid=confirm-delete-button]');
    
    // Verify post was deleted
    await expect(page.locator('[data-testid=post-item]')).not.toBeVisible();
  });
});
```

## 🔍 Code Quality Standards

### ESLint Configuration
```json
// ✅ CORRECT: Comprehensive ESLint configuration
{
  "extends": [
    "@typescript-eslint/recommended",
    "@typescript-eslint/recommended-requiring-type-checking",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
    "plugin:import/recommended",
    "plugin:import/typescript"
  ],
  "rules": {
    // TypeScript specific
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/explicit-function-return-type": "warn",
    "@typescript-eslint/no-non-null-assertion": "error",
    "@typescript-eslint/prefer-nullish-coalescing": "error",
    "@typescript-eslint/prefer-optional-chain": "error",
    
    // React specific
    "react/prop-types": "off", // Using TypeScript
    "react/react-in-jsx-scope": "off", // React 17+
    "react-hooks/exhaustive-deps": "error",
    
    // Import/Export
    "import/order": ["error", {
      "groups": [
        "builtin",
        "external",
        "internal",
        "parent",
        "sibling",
        "index"
      ],
      "newlines-between": "always",
      "alphabetize": { "order": "asc" }
    }],
    
    // General code quality
    "no-console": "warn",
    "no-debugger": "error",
    "prefer-const": "error",
    "no-var": "error",
    "eqeqeq": "error",
    "curly": "error"
  }
}
```

### Prettier Configuration
```json
// ✅ CORRECT: Prettier configuration
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "bracketSameLine": false,
  "arrowParens": "avoid",
  "endOfLine": "lf"
}
```

### Husky Pre-commit Hooks
```json
// ✅ CORRECT: Pre-commit quality gates
{
  "husky": {
    "hooks": {
      "pre-commit": "lint-staged",
      "commit-msg": "commitlint -E HUSKY_GIT_PARAMS",
      "pre-push": "npm run type-check && npm run test:unit"
    }
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write",
      "git add"
    ],
    "*.{js,jsx}": [
      "eslint --fix",
      "prettier --write",
      "git add"
    ],
    "*.{json,md,yml,yaml}": [
      "prettier --write",
      "git add"
    ]
  }
}
```

## 📊 Test Coverage & Reporting

### Coverage Configuration
```typescript
// ✅ CORRECT: Comprehensive coverage setup
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-utils/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/test-utils/',
        '**/*.d.ts',
        '**/*.config.{js,ts}',
        '**/index.ts',
        'src/main.tsx'
      ],
      thresholds: {
        global: {
          statements: 80,
          branches: 75,
          functions: 80,
          lines: 80
        },
        // Stricter thresholds for critical modules
        'src/services/': {
          statements: 90,
          branches: 85,
          functions: 90,
          lines: 90
        },
        'src/utils/': {
          statements: 95,
          branches: 90,
          functions: 95,
          lines: 95
        }
      }
    }
  }
});
```

### Test Utilities & Factories
```typescript
// ✅ CORRECT: Reusable test utilities
// test-utils/factories.ts
import { faker } from '@faker-js/faker';
import type { User, Post } from '../types';

export const createTestUser = (overrides: Partial<User> = {}): User => ({
  id: faker.string.uuid(),
  name: faker.person.fullName(),
  email: faker.internet.email(),
  role: 'user',
  isActive: true,
  createdAt: faker.date.past(),
  updatedAt: faker.date.recent(),
  ...overrides,
});

export const createTestPost = (overrides: Partial<Post> = {}): Post => ({
  id: faker.string.uuid(),
  title: faker.lorem.sentence(),
  content: faker.lorem.paragraphs(3),
  author: createTestUser(),
  createdAt: faker.date.past(),
  updatedAt: faker.date.recent(),
  ...overrides,
});

// test-utils/database.ts
import mongoose from 'mongoose';
import { MongoMemoryServer } from 'mongodb-memory-server';

let mongoServer: MongoMemoryServer;

export const connectTestDB = async (): Promise<void> => {
  mongoServer = await MongoMemoryServer.create();
  const mongoUri = mongoServer.getUri();
  
  await mongoose.connect(mongoUri);
};

export const clearTestDB = async (): Promise<void> => {
  const collections = mongoose.connection.collections;
  
  for (const key in collections) {
    await collections[key].deleteMany({});
  }
};

export const closeTestDB = async (): Promise<void> => {
  await mongoose.connection.dropDatabase();
  await mongoose.connection.close();
  await mongoServer.stop();
};

// test-utils/auth.ts
import jwt from 'jsonwebtoken';
import type { User } from '../types';

export const generateAuthToken = (user: User): string => {
  return jwt.sign(
    { userId: user.id, email: user.email },
    process.env.JWT_SECRET || 'test-secret',
    { expiresIn: '1h' }
  );
};

export const createAuthHeaders = (user: User) => ({
  Authorization: `Bearer ${generateAuthToken(user)}`,
});
```

## 🚀 Continuous Integration Testing

### GitHub Actions Workflow
```yaml
# ✅ CORRECT: Comprehensive CI pipeline
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:6.0
        ports:
          - 27017:27017
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: |
          npm ci
          cd app_v2/frontend && npm ci
          cd ../backend && npm ci
      
      - name: Lint code
        run: |
          npm run lint:frontend
          npm run lint:backend
      
      - name: Type check
        run: |
          npm run type-check:frontend
          npm run type-check:backend
      
      - name: Run unit tests
        run: |
          npm run test:unit:frontend
          npm run test:unit:backend
        env:
          NODE_ENV: test
          MONGO_URI: mongodb://localhost:27017/test
          REDIS_URL: redis://localhost:6379
      
      - name: Run integration tests
        run: npm run test:integration
        env:
          NODE_ENV: test
          MONGO_URI: mongodb://localhost:27017/test
          REDIS_URL: redis://localhost:6379
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
          flags: unittests
          name: codecov-umbrella
      
      - name: Build applications
        run: |
          npm run build:frontend
          npm run build:backend
      
      - name: Run E2E tests
        run: npm run test:e2e
        env:
          NODE_ENV: test
  
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run security audit
        run: |
          npm audit --audit-level=high
          cd app_v2/frontend && npm audit --audit-level=high
          cd ../backend && npm audit --audit-level=high
      
      - name: Run Semgrep security scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
```

## 📈 Quality Metrics & Monitoring

### Code Quality Dashboard
```typescript
// ✅ CORRECT: Quality metrics collection
export interface QualityMetrics {
  coverage: {
    statements: number;
    branches: number;
    functions: number;
    lines: number;
  };
  complexity: {
    cyclomatic: number;
    cognitive: number;
  };
  maintainability: {
    index: number;
    techDebt: string; // Time to fix
  };
  security: {
    vulnerabilities: number;
    securityHotspots: number;
  };
  duplications: {
    lines: number;
    blocks: number;
    percentage: number;
  };
}

// Quality gates configuration
export const QUALITY_GATES = {
  coverage: {
    statements: 80,
    branches: 75,
    functions: 80,
    lines: 80
  },
  complexity: {
    cyclomatic: 10, // Max per function
    cognitive: 15   // Max per function
  },
  maintainability: {
    index: 65, // Minimum maintainability index
  },
  security: {
    vulnerabilities: 0, // Zero tolerance for vulnerabilities
    securityHotspots: 5 // Max security hotspots
  },
  duplications: {
    percentage: 3 // Max 3% code duplication
  }
} as const;
```

### Performance Testing
```typescript
// ✅ CORRECT: Performance testing with k6
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 100 }, // Ramp up
    { duration: '5m', target: 100 }, // Stay at 100 users
    { duration: '2m', target: 200 }, // Ramp up to 200 users
    { duration: '5m', target: 200 }, // Stay at 200 users
    { duration: '2m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.1'],    // Error rate under 10%
    errors: ['rate<0.1'],             // Custom error rate under 10%
  },
};

export default function () {
  const BASE_URL = 'http://localhost:5000/api';
  
  // Login
  const loginResponse = http.post(`${BASE_URL}/auth/login`, {
    email: 'test@example.com',
    password: 'ValidPassword123!'
  });
  
  const loginSuccess = check(loginResponse, {
    'login status is 200': (r) => r.status === 200,
    'login response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  errorRate.add(!loginSuccess);
  
  if (loginSuccess) {
    const token = JSON.parse(loginResponse.body).token;
    
    // Get posts
    const postsResponse = http.get(`${BASE_URL}/posts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    
    const postsSuccess = check(postsResponse, {
      'posts status is 200': (r) => r.status === 200,
      'posts response time < 200ms': (r) => r.timings.duration < 200,
      'posts response has data': (r) => JSON.parse(r.body).data !== undefined,
    });
    
    errorRate.add(!postsSuccess);
  }
  
  sleep(1);
}
```

## 🎯 Testing Best Practices Checklist

### Before Writing Tests
- [ ] Understand the requirement and expected behavior
- [ ] Identify edge cases and error scenarios
- [ ] Plan test data and mocking strategy
- [ ] Consider performance implications

### Test Structure
- [ ] Use descriptive test names (should/when/given format)
- [ ] Follow AAA pattern (Arrange, Act, Assert)
- [ ] Keep tests focused and atomic
- [ ] Use proper setup and teardown

### Test Quality
- [ ] Test behavior, not implementation
- [ ] Cover happy path and edge cases
- [ ] Include error handling scenarios
- [ ] Verify all assertions are meaningful

### Maintenance
- [ ] Keep tests DRY with shared utilities
- [ ] Update tests when requirements change
- [ ] Remove obsolete tests
- [ ] Monitor test execution time

---

**Remember**: Testing is not just about coverage numbers - it's about confidence in your code. Write tests that catch real bugs and provide value to the development process. Quality over quantity always wins.