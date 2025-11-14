---
inclusion: fileMatch
fileMatchPattern: 'app_v2/**/*'
---

# Security & Performance Standards for App_v2

## 🔒 Security-First Development

### OWASP 2025 Compliance Checklist

#### A01: Broken Access Control
```typescript
// ✅ CORRECT: Role-based access control
interface AuthContext {
  user: User;
  permissions: Permission[];
  hasPermission: (permission: string) => boolean;
}

const requirePermission = (permission: string) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user.hasPermission(permission)) {
      return res.status(403).json({
        error: 'Insufficient permissions',
        required: permission
      });
    }
    next();
  };
};

// Usage
app.delete('/api/users/:id', 
  authGuard, 
  requirePermission('users:delete'), 
  deleteUser
);

// ❌ INCORRECT: No authorization checks
app.delete('/api/users/:id', deleteUser);
```

#### A02: Cryptographic Failures
```typescript
// ✅ CORRECT: Secure password hashing
import bcrypt from 'bcryptjs';
import crypto from 'crypto';

const SALT_ROUNDS = 12; // Minimum for 2025

export class PasswordService {
  static async hash(password: string): Promise<string> {
    return bcrypt.hash(password, SALT_ROUNDS);
  }
  
  static async verify(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
  }
  
  static generateSecureToken(): string {
    return crypto.randomBytes(32).toString('hex');
  }
}

// ✅ CORRECT: Secure JWT configuration
const JWT_CONFIG = {
  accessToken: {
    secret: process.env.JWT_ACCESS_SECRET!, // Min 256 bits
    expiresIn: '15m',
    algorithm: 'HS256' as const,
    issuer: 'app-v2',
    audience: 'app-v2-users'
  },
  refreshToken: {
    secret: process.env.JWT_REFRESH_SECRET!, // Different secret
    expiresIn: '7d',
    algorithm: 'HS256' as const
  }
};

// ❌ INCORRECT: Weak hashing
const hash = crypto.createHash('md5').update(password).digest('hex');
```

#### A03: Injection Attacks
```typescript
// ✅ CORRECT: Comprehensive input validation
import { z } from 'zod';
import mongoSanitize from 'express-mongo-sanitize';
import xss from 'xss';

const sanitizeInput = (input: string): string => {
  return xss(input.trim());
};

const userSearchSchema = z.object({
  query: z.string()
    .min(1)
    .max(100)
    .regex(/^[a-zA-Z0-9\s\-_.@]+$/, 'Invalid characters')
    .transform(sanitizeInput),
  page: z.coerce.number().min(1).max(1000).default(1),
  limit: z.coerce.number().min(1).max(100).default(10)
});

// MongoDB injection prevention
app.use(mongoSanitize({
  replaceWith: '_',
  onSanitize: ({ req, key }) => {
    logger.warn('Potential injection attempt', {
      ip: req.ip,
      key,
      userAgent: req.get('User-Agent')
    });
  }
}));

// ❌ INCORRECT: Direct query construction
const users = await User.find({ name: req.query.name }); // Vulnerable
```

#### A04: Insecure Design
```typescript
// ✅ CORRECT: Secure session management
interface SessionData {
  userId: string;
  role: UserRole;
  permissions: string[];
  createdAt: Date;
  lastActivity: Date;
  ipAddress: string;
  userAgent: string;
}

export class SessionService {
  private readonly redis: Redis;
  private readonly SESSION_TTL = 15 * 60; // 15 minutes
  
  async createSession(user: User, req: Request): Promise<string> {
    const sessionId = crypto.randomUUID();
    const sessionData: SessionData = {
      userId: user.id,
      role: user.role,
      permissions: user.permissions,
      createdAt: new Date(),
      lastActivity: new Date(),
      ipAddress: req.ip,
      userAgent: req.get('User-Agent') || 'unknown'
    };
    
    await this.redis.setex(
      `session:${sessionId}`, 
      this.SESSION_TTL, 
      JSON.stringify(sessionData)
    );
    
    return sessionId;
  }
  
  async validateSession(sessionId: string, req: Request): Promise<SessionData | null> {
    const data = await this.redis.get(`session:${sessionId}`);
    if (!data) return null;
    
    const session: SessionData = JSON.parse(data);
    
    // Validate IP and User-Agent for session hijacking prevention
    if (session.ipAddress !== req.ip || 
        session.userAgent !== req.get('User-Agent')) {
      await this.invalidateSession(sessionId);
      logger.warn('Session hijacking attempt detected', {
        sessionId,
        originalIp: session.ipAddress,
        currentIp: req.ip
      });
      return null;
    }
    
    // Update last activity
    session.lastActivity = new Date();
    await this.redis.setex(
      `session:${sessionId}`, 
      this.SESSION_TTL, 
      JSON.stringify(session)
    );
    
    return session;
  }
}
```

#### A05: Security Misconfiguration
```typescript
// ✅ CORRECT: Comprehensive security headers
import helmet from 'helmet';

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: [
        "'self'", 
        "'unsafe-inline'", // Only for Tailwind CSS
        "https://fonts.googleapis.com"
      ],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", process.env.API_URL!],
      frameSrc: ["'none'"],
      objectSrc: ["'none'"],
      baseUri: ["'self'"],
      formAction: ["'self'"],
      upgradeInsecureRequests: []
    },
  },
  hsts: {
    maxAge: 31536000, // 1 year
    includeSubDomains: true,
    preload: true
  },
  noSniff: true,
  frameguard: { action: 'deny' },
  xssFilter: true,
  referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
  permissionsPolicy: {
    features: {
      camera: [],
      microphone: [],
      geolocation: [],
      payment: []
    }
  }
}));

// CORS configuration
app.use(cors({
  origin: (origin, callback) => {
    const allowedOrigins = env.ALLOWED_ORIGINS;
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  maxAge: 86400 // 24 hours
}));
```

### Rate Limiting & DDoS Protection
```typescript
// ✅ CORRECT: Sophisticated rate limiting
import rateLimit from 'express-rate-limit';
import slowDown from 'express-slow-down';

// General API rate limiting
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // requests per window
  message: {
    error: 'Too many requests',
    retryAfter: '15 minutes'
  },
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => {
    return req.ip + ':' + (req.user?.id || 'anonymous');
  }
});

// Strict rate limiting for auth endpoints
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5, // Only 5 login attempts per 15 minutes
  skipSuccessfulRequests: true,
  message: {
    error: 'Too many authentication attempts',
    retryAfter: '15 minutes'
  }
});

// Progressive delay for repeated requests
const speedLimiter = slowDown({
  windowMs: 15 * 60 * 1000,
  delayAfter: 50,
  delayMs: 500,
  maxDelayMs: 20000
});

app.use('/api', speedLimiter, apiLimiter);
app.use('/api/auth', authLimiter);
```

## ⚡ Performance Optimization Standards

### Frontend Performance Patterns

#### Code Splitting & Lazy Loading
```typescript
// ✅ CORRECT: Strategic code splitting
import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

// Route-based splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Posts = lazy(() => import('./pages/Posts'));
const Profile = lazy(() => import('./pages/Profile'));

// Component-based splitting for heavy components
const DataVisualization = lazy(() => import('./components/DataVisualization'));

// Loading component with skeleton
const LoadingFallback = ({ type }: { type: 'page' | 'component' }) => (
  <div className={`animate-pulse ${type === 'page' ? 'min-h-screen' : 'min-h-32'}`}>
    <div className="bg-gray-200 rounded h-full"></div>
  </div>
);

export const AppRoutes = () => (
  <Suspense fallback={<LoadingFallback type="page" />}>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/posts" element={<Posts />} />
      <Route path="/profile" element={<Profile />} />
    </Routes>
  </Suspense>
);

// ❌ INCORRECT: Loading everything upfront
import Dashboard from './pages/Dashboard';
import Posts from './pages/Posts';
import Profile from './pages/Profile';
```

#### Optimized State Management
```typescript
// ✅ CORRECT: Optimized React Query usage
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const QUERY_KEYS = {
  users: ['users'] as const,
  user: (id: string) => ['users', id] as const,
  posts: (filters?: PostFilters) => ['posts', filters] as const,
} as const;

// Optimized data fetching with caching
export const useUsers = (filters?: UserFilters) => {
  return useQuery({
    queryKey: QUERY_KEYS.users,
    queryFn: () => userApi.getUsers(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
    retry: (failureCount, error) => {
      if (error.status === 404) return false;
      return failureCount < 3;
    }
  });
};

// Optimistic updates
export const useUpdateUser = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: userApi.updateUser,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.user(variables.id) });
      
      const previousUser = queryClient.getQueryData(QUERY_KEYS.user(variables.id));
      
      queryClient.setQueryData(QUERY_KEYS.user(variables.id), {
        ...previousUser,
        ...variables.updates
      });
      
      return { previousUser };
    },
    onError: (err, variables, context) => {
      if (context?.previousUser) {
        queryClient.setQueryData(
          QUERY_KEYS.user(variables.id), 
          context.previousUser
        );
      }
    },
    onSettled: (data, error, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.user(variables.id) 
      });
    }
  });
};
```

#### Bundle Optimization
```typescript
// ✅ CORRECT: Tree-shaking friendly imports
import { debounce } from 'lodash-es/debounce';
import { format } from 'date-fns/format';

// ✅ CORRECT: Dynamic imports for heavy libraries
const loadChartLibrary = async () => {
  const { Chart } = await import('chart.js');
  return Chart;
};

// ✅ CORRECT: Webpack bundle analysis
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
  plugins: [
    process.env.ANALYZE && new BundleAnalyzerPlugin({
      analyzerMode: 'static',
      openAnalyzer: false,
      reportFilename: 'bundle-report.html'
    })
  ].filter(Boolean),
  
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
          priority: 10
        },
        common: {
          name: 'common',
          minChunks: 2,
          chunks: 'all',
          priority: 5,
          enforce: true
        }
      }
    },
    usedExports: true,
    sideEffects: false
  }
};

// ❌ INCORRECT: Importing entire libraries
import _ from 'lodash';
import * as dateFns from 'date-fns';
```

### Backend Performance Patterns

#### Database Query Optimization
```typescript
// ✅ CORRECT: Optimized MongoDB queries
export class PostService {
  async getPosts(options: GetPostsOptions): Promise<PaginatedResult<Post>> {
    const { page = 1, limit = 10, userId, sortBy = 'createdAt', sortOrder = 'desc' } = options;
    const skip = (page - 1) * limit;
    
    // Build query with proper indexing
    const query: any = {};
    if (userId) query.author = userId;
    
    // Use aggregation for complex queries
    const pipeline = [
      { $match: query },
      { $sort: { [sortBy]: sortOrder === 'desc' ? -1 : 1 } },
      {
        $facet: {
          posts: [
            { $skip: skip },
            { $limit: limit },
            {
              $lookup: {
                from: 'users',
                localField: 'author',
                foreignField: '_id',
                as: 'author',
                pipeline: [{ $project: { name: 1, email: 1 } }] // Only needed fields
              }
            },
            { $unwind: '$author' }
          ],
          totalCount: [{ $count: 'count' }]
        }
      }
    ];
    
    const [result] = await Post.aggregate(pipeline);
    const posts = result.posts;
    const total = result.totalCount[0]?.count || 0;
    
    return {
      items: posts,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit)
      }
    };
  }
  
  // ❌ INCORRECT: Inefficient queries
  async getPostsInefficient() {
    const posts = await Post.find()
      .populate('author') // Loads all user fields
      .sort({ createdAt: -1 }); // No pagination
    
    return posts; // No pagination info
  }
}
```

#### Caching Strategy Implementation
```typescript
// ✅ CORRECT: Multi-layer caching
import Redis from 'ioredis';

export class CacheService {
  private redis: Redis;
  private memoryCache = new Map<string, { data: any; expires: number }>();
  
  constructor() {
    this.redis = new Redis(env.REDIS_URL, {
      retryDelayOnFailover: 100,
      maxRetriesPerRequest: 3,
      lazyConnect: true
    });
  }
  
  async get<T>(key: string): Promise<T | null> {
    // L1: Memory cache (fastest)
    const memCached = this.memoryCache.get(key);
    if (memCached && memCached.expires > Date.now()) {
      return memCached.data;
    }
    
    // L2: Redis cache
    try {
      const cached = await this.redis.get(key);
      if (cached) {
        const data = JSON.parse(cached);
        // Store in memory cache for faster access
        this.memoryCache.set(key, {
          data,
          expires: Date.now() + 60000 // 1 minute in memory
        });
        return data;
      }
    } catch (error) {
      logger.warn('Redis cache miss', { key, error: error.message });
    }
    
    return null;
  }
  
  async set(key: string, value: any, ttl: number = 3600): Promise<void> {
    const serialized = JSON.stringify(value);
    
    // Store in both layers
    this.memoryCache.set(key, {
      data: value,
      expires: Date.now() + Math.min(ttl * 1000, 60000)
    });
    
    try {
      await this.redis.setex(key, ttl, serialized);
    } catch (error) {
      logger.error('Redis cache set failed', { key, error: error.message });
    }
  }
  
  async invalidate(pattern: string): Promise<void> {
    // Clear memory cache
    for (const key of this.memoryCache.keys()) {
      if (key.includes(pattern)) {
        this.memoryCache.delete(key);
      }
    }
    
    // Clear Redis cache
    try {
      const keys = await this.redis.keys(`*${pattern}*`);
      if (keys.length > 0) {
        await this.redis.del(...keys);
      }
    } catch (error) {
      logger.error('Redis cache invalidation failed', { pattern, error: error.message });
    }
  }
}

// Cache middleware with smart invalidation
export const cacheMiddleware = (
  keyGenerator: (req: Request) => string,
  ttl: number = 3600,
  invalidateOn: string[] = []
) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    const cacheKey = keyGenerator(req);
    
    // Try to get from cache
    const cached = await cacheService.get(cacheKey);
    if (cached) {
      return res.json(cached);
    }
    
    // Intercept response to cache it
    const originalSend = res.json;
    res.json = function(data) {
      // Only cache successful responses
      if (res.statusCode >= 200 && res.statusCode < 300) {
        cacheService.set(cacheKey, data, ttl);
      }
      return originalSend.call(this, data);
    };
    
    next();
  };
};
```

#### Connection Pooling & Resource Management
```typescript
// ✅ CORRECT: Optimized database connections
import mongoose from 'mongoose';

const connectDB = async () => {
  try {
    await mongoose.connect(env.MONGO_URI, {
      // Connection pool settings
      maxPoolSize: 10, // Maximum connections
      minPoolSize: 2,  // Minimum connections
      maxIdleTimeMS: 30000, // Close connections after 30s of inactivity
      serverSelectionTimeoutMS: 5000, // How long to try selecting a server
      socketTimeoutMS: 45000, // How long a send or receive on a socket can take
      
      // Buffering settings
      bufferCommands: false, // Disable mongoose buffering
      bufferMaxEntries: 0, // Disable mongoose buffering
      
      // Monitoring
      heartbeatFrequencyMS: 10000,
      
      // Compression
      compressors: ['zlib'],
      zlibCompressionLevel: 6
    });
    
    // Connection event handlers
    mongoose.connection.on('connected', () => {
      logger.info('MongoDB connected successfully');
    });
    
    mongoose.connection.on('error', (err) => {
      logger.error('MongoDB connection error:', err);
    });
    
    mongoose.connection.on('disconnected', () => {
      logger.warn('MongoDB disconnected');
    });
    
    // Graceful shutdown
    process.on('SIGINT', async () => {
      await mongoose.connection.close();
      logger.info('MongoDB connection closed through app termination');
      process.exit(0);
    });
    
  } catch (error) {
    logger.error('Database connection failed:', error);
    process.exit(1);
  }
};
```

## 📊 Performance Monitoring

### Application Performance Monitoring
```typescript
// ✅ CORRECT: Comprehensive performance monitoring
import { performance } from 'perf_hooks';

export class PerformanceMonitor {
  private static metrics = new Map<string, number[]>();
  
  static startTimer(label: string): () => number {
    const start = performance.now();
    return () => {
      const duration = performance.now() - start;
      this.recordMetric(label, duration);
      return duration;
    };
  }
  
  static recordMetric(label: string, value: number): void {
    if (!this.metrics.has(label)) {
      this.metrics.set(label, []);
    }
    
    const values = this.metrics.get(label)!;
    values.push(value);
    
    // Keep only last 1000 measurements
    if (values.length > 1000) {
      values.shift();
    }
  }
  
  static getStats(label: string) {
    const values = this.metrics.get(label) || [];
    if (values.length === 0) return null;
    
    const sorted = [...values].sort((a, b) => a - b);
    return {
      count: values.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      avg: values.reduce((a, b) => a + b, 0) / values.length,
      p50: sorted[Math.floor(sorted.length * 0.5)],
      p95: sorted[Math.floor(sorted.length * 0.95)],
      p99: sorted[Math.floor(sorted.length * 0.99)]
    };
  }
}

// Performance middleware
export const performanceMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const timer = PerformanceMonitor.startTimer(`api:${req.method}:${req.route?.path || req.path}`);
  
  res.on('finish', () => {
    const duration = timer();
    
    // Log slow requests
    if (duration > 1000) {
      logger.warn('Slow request detected', {
        method: req.method,
        path: req.path,
        duration,
        statusCode: res.statusCode
      });
    }
  });
  
  next();
};
```

### Health Check Implementation
```typescript
// ✅ CORRECT: Comprehensive health checks
export const healthCheck = async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  const checks = {
    database: await checkDatabase(),
    redis: await checkRedis(),
    memory: checkMemory(),
    disk: await checkDisk(),
    external: await checkExternalServices()
  };
  
  const isHealthy = Object.values(checks).every(check => check.status === 'OK');
  const responseTime = Date.now() - startTime;
  
  const health = {
    status: isHealthy ? 'OK' : 'ERROR',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    responseTime,
    version: process.env.npm_package_version,
    environment: env.NODE_ENV,
    checks
  };
  
  res.status(isHealthy ? 200 : 503).json(health);
};

async function checkDatabase(): Promise<HealthCheck> {
  try {
    const start = Date.now();
    await mongoose.connection.db.admin().ping();
    const responseTime = Date.now() - start;
    
    return {
      status: 'OK',
      responseTime,
      details: {
        readyState: mongoose.connection.readyState,
        host: mongoose.connection.host,
        port: mongoose.connection.port
      }
    };
  } catch (error) {
    return {
      status: 'ERROR',
      error: error.message,
      details: { readyState: mongoose.connection.readyState }
    };
  }
}

interface HealthCheck {
  status: 'OK' | 'ERROR' | 'WARNING';
  responseTime?: number;
  error?: string;
  details?: Record<string, any>;
}
```

## 🎯 Performance Targets & SLAs

### Frontend Performance Targets
```typescript
// Performance budget configuration
const PERFORMANCE_BUDGET = {
  // Core Web Vitals
  LCP: 2500, // Largest Contentful Paint (ms)
  FID: 100,  // First Input Delay (ms)
  CLS: 0.1,  // Cumulative Layout Shift
  
  // Loading Performance
  FCP: 1500, // First Contentful Paint (ms)
  TTI: 3000, // Time to Interactive (ms)
  
  // Bundle Size
  initialJS: 1024 * 1024, // 1MB gzipped
  totalJS: 2 * 1024 * 1024, // 2MB gzipped
  
  // Network
  requests: 50, // Maximum requests per page
  
  // Lighthouse Scores
  performance: 90,
  accessibility: 95,
  bestPractices: 90,
  seo: 90
} as const;

// Performance monitoring in production
if (typeof window !== 'undefined' && 'performance' in window) {
  window.addEventListener('load', () => {
    setTimeout(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      const paint = performance.getEntriesByType('paint');
      
      const metrics = {
        FCP: paint.find(p => p.name === 'first-contentful-paint')?.startTime,
        LCP: navigation.loadEventEnd - navigation.loadEventStart,
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.fetchStart
      };
      
      // Send to analytics
      if (metrics.FCP && metrics.FCP > PERFORMANCE_BUDGET.FCP) {
        console.warn('FCP budget exceeded', metrics);
      }
    }, 0);
  });
}
```

### Backend Performance Targets
```typescript
// SLA definitions
const SLA_TARGETS = {
  // Response Times (95th percentile)
  api: {
    read: 200,   // GET requests
    write: 500,  // POST/PUT/DELETE requests
    search: 1000 // Complex queries
  },
  
  // Database Performance
  database: {
    query: 100,     // Average query time
    connection: 50  // Connection establishment
  },
  
  // Cache Performance
  cache: {
    hit_ratio: 0.8, // 80% cache hit ratio
    response: 10    // Cache response time
  },
  
  // System Resources
  system: {
    cpu: 70,        // Max CPU usage %
    memory: 80,     // Max memory usage %
    disk: 85        // Max disk usage %
  },
  
  // Availability
  uptime: 99.9 // 99.9% uptime SLA
} as const;

// SLA monitoring middleware
export const slaMonitoringMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    const method = req.method.toLowerCase();
    
    let target: number;
    if (method === 'get') {
      target = SLA_TARGETS.api.read;
    } else if (['post', 'put', 'delete'].includes(method)) {
      target = SLA_TARGETS.api.write;
    } else {
      target = SLA_TARGETS.api.search;
    }
    
    if (duration > target) {
      logger.warn('SLA violation detected', {
        method: req.method,
        path: req.path,
        duration,
        target,
        statusCode: res.statusCode
      });
    }
    
    // Record metrics for monitoring
    PerformanceMonitor.recordMetric(`sla:${method}`, duration);
  });
  
  next();
};
```

---

**Remember**: Security and performance are not optional features - they are fundamental requirements. Always implement security measures from the start and continuously monitor performance metrics to ensure optimal user experience.