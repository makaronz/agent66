---
inclusion: fileMatch
fileMatchPattern: 'app_v2/**/*'
---

# App_v2 Development Best Practices & Standards

## 🎯 Project Context
This steering document applies to the app_v2 full-stack trading application modernization project. It provides specific guidance for maintaining code quality, security, and performance standards during development.

## 📋 Architecture Guidelines

### Frontend (React + TypeScript)
- **Always use TypeScript 5.3.3** - maintain version consistency across the project
- **No `any` types** - use proper interfaces and type definitions
- **Remove unnecessary React imports** - leverage JSX transform for React 17+
- **Use functional components with hooks** - avoid class components
- **Implement custom hooks** for reusable logic (useAuth, useApi, useLocalStorage)
- **Code splitting** - use React.lazy() for route-based splitting
- **Error boundaries** - wrap components with proper error handling

### Backend (Node.js + Express + TypeScript)
- **Service layer pattern** - separate business logic from controllers
- **Dependency injection** - use constructor injection for services
- **Async/await** - prefer over promises and callbacks
- **Proper error handling** - use custom error classes with status codes
- **Input validation** - use Zod schemas for all API endpoints
- **Security middleware** - implement comprehensive security headers

## 🔒 Security Standards (OWASP 2025 Compliance)

### Authentication & Authorization
```typescript
// ✅ CORRECT: Secure JWT configuration
const JWT_CONFIG = {
  accessToken: {
    secret: process.env.JWT_ACCESS_SECRET,
    expiresIn: '15m',
    algorithm: 'HS256'
  },
  refreshToken: {
    secret: process.env.JWT_REFRESH_SECRET,
    expiresIn: '7d',
    algorithm: 'HS256'
  }
};

// ❌ INCORRECT: Long-lived tokens
const token = jwt.sign(payload, secret, { expiresIn: '30d' });
```

### Input Validation & Sanitization
```typescript
// ✅ CORRECT: Comprehensive validation
const userSchema = z.object({
  name: z.string().min(2).max(100).trim(),
  email: z.string().email().toLowerCase(),
  password: z.string().min(8).regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/)
});

// ❌ INCORRECT: No validation
app.post('/users', (req, res) => {
  const user = new User(req.body); // Direct assignment without validation
});
```

### Security Headers
```typescript
// ✅ CORRECT: Comprehensive security headers
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));
```

## ⚡ Performance Guidelines

### Frontend Performance
```typescript
// ✅ CORRECT: Code splitting with Suspense
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Posts = lazy(() => import('./pages/Posts'));

<Suspense fallback={<LoadingSpinner />}>
  <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/posts" element={<Posts />} />
  </Routes>
</Suspense>

// ❌ INCORRECT: Loading all components upfront
import Dashboard from './pages/Dashboard';
import Posts from './pages/Posts';
```

### Backend Performance
```typescript
// ✅ CORRECT: Optimized database queries with caching
async getPosts(page: number = 1, limit: number = 10) {
  const cacheKey = `posts:${page}:${limit}`;
  const cached = await redis.get(cacheKey);
  
  if (cached) return JSON.parse(cached);
  
  const posts = await Post.find()
    .populate('author', 'name email')
    .sort({ createdAt: -1 })
    .skip((page - 1) * limit)
    .limit(limit)
    .lean(); // Use lean() for read-only operations
    
  await redis.setex(cacheKey, 3600, JSON.stringify(posts));
  return posts;
}

// ❌ INCORRECT: Unoptimized queries
const posts = await Post.find().populate('author'); // No pagination, no caching
```

## 🧪 Testing Standards

### Unit Testing
```typescript
// ✅ CORRECT: Comprehensive test coverage
describe('AuthService', () => {
  let authService: AuthService;
  
  beforeEach(() => {
    authService = new AuthService();
  });
  
  it('should generate valid JWT tokens', async () => {
    const user = { id: '123', email: 'test@example.com' };
    const tokens = await authService.generateTokens(user);
    
    expect(tokens.accessToken).toBeDefined();
    expect(tokens.refreshToken).toBeDefined();
    
    const decoded = jwt.verify(tokens.accessToken, JWT_SECRET);
    expect(decoded.userId).toBe(user.id);
  });
});
```

### Integration Testing
```typescript
// ✅ CORRECT: API endpoint testing
describe('POST /api/auth/login', () => {
  it('should return tokens for valid credentials', async () => {
    const response = await request(app)
      .post('/api/auth/login')
      .send({
        email: 'test@example.com',
        password: 'ValidPassword123!'
      })
      .expect(200);
      
    expect(response.body.accessToken).toBeDefined();
    expect(response.headers['set-cookie']).toBeDefined();
  });
});
```

## 📝 Code Style & Formatting

### TypeScript Conventions
```typescript
// ✅ CORRECT: Proper interface definitions
interface User {
  id: string;
  name: string;
  email: string;
  role: 'user' | 'admin';
  createdAt: Date;
  updatedAt: Date;
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  pagination?: {
    page: number;
    limit: number;
    total: number;
  };
}

// ❌ INCORRECT: Using any types
interface User {
  id: any;
  data: any;
}
```

### Error Handling Patterns
```typescript
// ✅ CORRECT: Custom error classes
export class AppError extends Error {
  public statusCode: number;
  public isOperational: boolean;
  
  constructor(message: string, statusCode: number) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

// Usage
throw new AppError('User not found', 404);

// ❌ INCORRECT: Generic error throwing
throw new Error('Something went wrong');
```

## 🗄️ Database Best Practices

### MongoDB Schema Design
```typescript
// ✅ CORRECT: Optimized schema with indexes
const UserSchema = new Schema({
  name: { type: String, required: true, trim: true, maxlength: 100 },
  email: { 
    type: String, 
    required: true, 
    unique: true, 
    lowercase: true,
    index: true,
    validate: [validator.isEmail, 'Invalid email']
  },
  role: { 
    type: String, 
    enum: ['user', 'admin'], 
    default: 'user',
    index: true 
  }
}, {
  timestamps: true,
  toJSON: { virtuals: true }
});

// Compound indexes for common queries
UserSchema.index({ email: 1, isActive: 1 });
UserSchema.index({ role: 1, createdAt: -1 });
```

### Query Optimization
```typescript
// ✅ CORRECT: Efficient queries with pagination
async function getUsers(filters: any, page: number = 1, limit: number = 10) {
  const skip = (page - 1) * limit;
  
  const [users, total] = await Promise.all([
    User.find(filters)
      .select('name email role createdAt')
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit)
      .lean(),
    User.countDocuments(filters)
  ]);
  
  return { users, total, page, pages: Math.ceil(total / limit) };
}
```

## 🔧 Environment & Configuration

### Environment Variables Validation
```typescript
// ✅ CORRECT: Zod schema validation
const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'staging', 'production']),
  PORT: z.string().transform(Number).default('5000'),
  MONGO_URI: z.string().url(),
  JWT_ACCESS_SECRET: z.string().min(32),
  JWT_REFRESH_SECRET: z.string().min(32),
  REDIS_URL: z.string().url(),
  ALLOWED_ORIGINS: z.string().transform(s => s.split(',')),
});

export const env = envSchema.parse(process.env);

// ❌ INCORRECT: No validation
const mongoUri = process.env.MONGO_URI; // Could be undefined
```

## 📊 Monitoring & Logging

### Structured Logging
```typescript
// ✅ CORRECT: Structured logging with context
import winston from 'winston';

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'app-v2-api' }
});

// Usage with context
logger.info('User login attempt', {
  userId: user.id,
  email: user.email,
  ip: req.ip,
  userAgent: req.get('User-Agent')
});
```

### Health Checks
```typescript
// ✅ CORRECT: Comprehensive health checks
export const healthCheck = async (req: Request, res: Response) => {
  const health = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    checks: {
      database: await checkDatabase(),
      redis: await checkRedis(),
      memory: checkMemory()
    }
  };
  
  const isHealthy = Object.values(health.checks)
    .every(check => check.status === 'OK');
  
  res.status(isHealthy ? 200 : 503).json(health);
};
```

## 🚀 Deployment Guidelines

### Docker Best Practices
```dockerfile
# ✅ CORRECT: Multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS production
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
USER nextjs
EXPOSE 5000
CMD ["npm", "start"]
```

### CI/CD Pipeline
```yaml
# ✅ CORRECT: Comprehensive pipeline
name: CI/CD Pipeline
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check
      - run: npm test
      - run: npm run security-audit
      
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker build -t app-v2 .
      - run: docker run --rm app-v2 npm test
```

## 🎯 Performance Targets

### Frontend Metrics
- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Cumulative Layout Shift**: < 0.1
- **Bundle Size**: < 1MB gzipped
- **Lighthouse Performance Score**: > 90

### Backend Metrics
- **API Response Time**: < 500ms (95th percentile)
- **Database Query Time**: < 100ms (average)
- **Memory Usage**: < 512MB
- **CPU Usage**: < 70%
- **Cache Hit Ratio**: > 80%

## 🔍 Code Review Checklist

### Before Submitting PR
- [ ] All tests pass locally
- [ ] TypeScript compilation without errors
- [ ] ESLint and Prettier checks pass
- [ ] Security scan shows no critical issues
- [ ] Performance impact assessed
- [ ] Documentation updated if needed

### Review Criteria
- [ ] Code follows established patterns
- [ ] Proper error handling implemented
- [ ] Security considerations addressed
- [ ] Performance implications considered
- [ ] Test coverage adequate
- [ ] Breaking changes documented

## 🚨 Common Anti-Patterns to Avoid

### Frontend Anti-Patterns
```typescript
// ❌ AVOID: Prop drilling
function App() {
  const [user, setUser] = useState(null);
  return <Dashboard user={user} setUser={setUser} />;
}

// ✅ USE: Context or state management
const AuthContext = createContext();
function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
}
```

### Backend Anti-Patterns
```typescript
// ❌ AVOID: Fat controllers
app.post('/users', async (req, res) => {
  // 50+ lines of business logic
  const hashedPassword = await bcrypt.hash(req.body.password, 10);
  const user = new User({ ...req.body, password: hashedPassword });
  await user.save();
  const token = jwt.sign({ userId: user.id }, JWT_SECRET);
  res.json({ user, token });
});

// ✅ USE: Service layer
app.post('/users', validateRequest(userSchema), async (req, res) => {
  const result = await authService.registerUser(req.body);
  res.status(201).json(result);
});
```

## 📚 Reference Documentation

### Key Files to Reference
- `#[[file:app_v2_comprehensive_review.md]]` - Complete architecture analysis
- `#[[file:.kiro/specs/app-v2-modernization/requirements.md]]` - Project requirements
- `#[[file:.kiro/specs/app-v2-modernization/design.md]]` - Technical design
- `#[[file:.kiro/specs/app-v2-modernization/tasks.md]]` - Implementation tasks

### External Resources
- [React Best Practices 2025](https://react.dev/learn)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)
- [OWASP Top 10 2025](https://owasp.org/www-project-top-ten/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Remember**: These guidelines ensure consistency, security, and maintainability across the app_v2 modernization project. Always prioritize security and performance while maintaining clean, readable code.