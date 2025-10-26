# Agent66 Security Remediation Implementation Guide

**Purpose:** Step-by-step implementation guide for addressing security vulnerabilities identified in the security audit report.

---

## 🚨 CRITICAL PRIORITY: Immediate Fixes (24-48 hours)

### 1. Secure Secret Management

**Issue:** Default/placeholder secrets in production configuration

**Files to Update:**
- `.env.production` (create if doesn't exist)
- `/backend/src/config/env-validation.ts`
- `/backend/src/config/index.ts`

**Step 1: Generate Secure Secrets**
```bash
# Generate new secure secrets
JWT_SECRET=$(openssl rand -base64 32)
JWT_ACCESS_SECRET=$(openssl rand -base64 32)
JWT_REFRESH_SECRET=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -hex 16) # 32 hex chars = 16 bytes = 128 bits
SESSION_SECRET=$(openssl rand -base64 32)

echo "Generated secrets (save these securely):"
echo "JWT_SECRET=$JWT_SECRET"
echo "JWT_ACCESS_SECRET=$JWT_ACCESS_SECRET"
echo "JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET"
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"
echo "SESSION_SECRET=$SESSION_SECRET"
```

**Step 2: Update Environment Validation**
```typescript
// /backend/src/config/env-validation.ts
const validateProductionSecrets = (env: any) => {
  if (env.NODE_ENV === 'production') {
    const weakPatterns = [
      'CHANGE_ME', 'DEFAULT', 'EXAMPLE', 'TEST', 'DEMO',
      'SAMPLE', 'your-', 'replace-', 'your-project'
    ];

    const criticalSecrets = [
      'JWT_SECRET', 'JWT_ACCESS_SECRET', 'JWT_REFRESH_SECRET',
      'ENCRYPTION_KEY', 'SESSION_SECRET'
    ];

    criticalSecrets.forEach(secretName => {
      const value = env[secretName];
      if (!value) {
        throw new Error(`${secretName} is required in production`);
      }

      if (weakPatterns.some(pattern => value.toLowerCase().includes(pattern.toLowerCase()))) {
        throw new Error(`${secretName} contains default/placeholder value in production`);
      }

      // Validate minimum entropy
      const entropy = calculateEntropy(value);
      if (entropy < 4.0) { // Minimum 4 bits of entropy per character
        throw new Error(`${secretName} has insufficient entropy for production`);
      }
    });
  }
};

function calculateEntropy(str: string): number {
  const chars = str.split('');
  const charCounts: { [key: string]: number } = {};

  chars.forEach(char => {
    charCounts[char] = (charCounts[char] || 0) + 1;
  });

  const entropy = Object.values(charCounts)
    .map(count => count / str.length)
    .reduce((sum, prob) => {
      return sum - prob * Math.log2(prob);
    }, 0);

  return entropy;
}
```

**Step 3: Create Secure Production Environment**
```bash
# .env.production
NODE_ENV=production
PORT=5000
HOST=0.0.0.0
APP_DEBUG=false

# Secure secrets (replace with generated values)
JWT_SECRET=<PASTE_GENERATED_SECRET_HERE>
JWT_ACCESS_SECRET=<PASTE_GENERATED_ACCESS_SECRET_HERE>
JWT_REFRESH_SECRET=<PASTE_GENERATED_REFRESH_SECRET_HERE>
ENCRYPTION_KEY=<PASTE_GENERATED_ENCRYPTION_KEY_HERE>
SESSION_SECRET=<PASTE_GENERATED_SESSION_SECRET_HERE>

# Other secure production settings
BCRYPT_ROUNDS=12
JWT_EXPIRATION=3600
JWT_REFRESH_EXPIRATION=604800
SESSION_TIMEOUT=3600000

# Database security
DATABASE_URL=postgresql://username:password@localhost:5432/smc_trading_prod
DB_SSL=true
DB_POOL_SIZE=20

# Enhanced security settings
HELMET_ENABLED=true
CSRF_PROTECTION=true
DDOS_PROTECTION=true
RATE_LIMIT_MAX_REQUESTS=50
LOG_LEVEL=warn
```

### 2. Token Security Enhancement

**Issue:** JWT tokens stored in localStorage, missing blacklisting

**Step 1: Secure Token Storage Implementation**
```typescript
// /backend/src/middleware/tokenManager.ts
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { config } from '../config';

export interface TokenBlacklist {
  [jti: string]: {
    reason: string;
    blacklistedAt: Date;
    expiresAt: Date;
  };
}

class TokenManager {
  private tokenBlacklist: TokenBlacklist = {};
  private userSessions: Map<string, Set<string>> = new Map();

  // Generate secure token with additional claims
  generateTokens(payload: any) {
    const jti = crypto.randomBytes(16).toString('hex');
    const now = Math.floor(Date.now() / 1000);

    const accessToken = jwt.sign(
      {
        ...payload,
        jti,
        type: 'access',
        sessionId: crypto.randomBytes(8).toString('hex'),
        deviceFingerprint: this.generateDeviceFingerprint(payload.deviceInfo)
      },
      config.jwt.accessSecret,
      {
        expiresIn: config.jwt.expiresIn,
        issuer: 'agent66',
        audience: 'agent66-users',
        algorithm: 'HS256'
      }
    );

    const refreshToken = jwt.sign(
      {
        userId: payload.userId,
        jti,
        type: 'refresh',
        version: payload.tokenVersion || 0
      },
      config.jwt.refreshSecret,
      {
        expiresIn: config.jwt.refreshExpiresIn,
        issuer: 'agent66',
        audience: 'agent66-refresh'
      }
    );

    // Track user sessions
    if (!this.userSessions.has(payload.userId)) {
      this.userSessions.set(payload.userId, new Set());
    }
    this.userSessions.get(payload.userId)!.add(jti);

    return { accessToken, refreshToken, jti };
  }

  // Blacklist token (for logout/session invalidation)
  blacklistToken(jti: string, reason: string = 'Logout'): void {
    this.tokenBlacklist[jti] = {
      reason,
      blacklistedAt: new Date(),
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours
    };
  }

  // Check if token is blacklisted
  isTokenBlacklisted(jti: string): boolean {
    const blacklisted = this.tokenBlacklist[jti];
    if (!blacklisted) return false;

    // Clean up expired blacklist entries
    if (blacklisted.expiresAt < new Date()) {
      delete this.tokenBlacklist[jti];
      return false;
    }

    return true;
  }

  // Invalidate all user sessions
  invalidateUserSessions(userId: string, reason: string = 'Security logout'): void {
    const sessions = this.userSessions.get(userId);
    if (sessions) {
      sessions.forEach(jti => {
        this.blacklistToken(jti, reason);
      });
      this.userSessions.delete(userId);
    }
  }

  // Verify token with blacklist check
  verifyToken(token: string, secret: string): any {
    try {
      const decoded = jwt.verify(token, secret, {
        issuer: 'agent66',
        algorithms: ['HS256']
      });

      // Check if token is blacklisted
      if (decoded.jti && this.isTokenBlacklisted(decoded.jti)) {
        throw new Error('Token has been blacklisted');
      }

      return decoded;
    } catch (error) {
      throw new Error(`Token verification failed: ${error.message}`);
    }
  }

  private generateDeviceFingerprint(deviceInfo: any): string {
    return crypto.createHash('sha256')
      .update(JSON.stringify(deviceInfo || {}))
      .digest('hex');
  }

  // Cleanup expired blacklist entries
  cleanupBlacklist(): void {
    const now = new Date();
    Object.keys(this.tokenBlacklist).forEach(jti => {
      if (this.tokenBlacklist[jti].expiresAt < now) {
        delete this.tokenBlacklist[jti];
      }
    });
  }
}

export const tokenManager = new TokenManager();

// Schedule cleanup every hour
setInterval(() => tokenManager.cleanupBlacklist(), 60 * 60 * 1000);
```

**Step 2: Update Authentication Middleware**
```typescript
// /backend/src/middleware/auth.ts (revised)
import { Request, Response, NextFunction } from 'express';
import { cookie } from 'express-validator';
import { tokenManager } from './tokenManager';
import { config } from '../config';
import { logger } from '../utils/logger';
import { AuthenticationError, AuthorizationError } from './errorHandler';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    username: string;
    role: string;
    jti: string;
    sessionId: string;
    deviceFingerprint: string;
    iat: number;
    exp: number;
  };
}

export const authMiddleware = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    // Skip authentication for health check and metrics endpoints
    if (req.path.startsWith('/health') || req.path.startsWith('/metrics')) {
      return next();
    }

    // Get token from secure httpOnly cookie
    const token = req.cookies?.auth_token;

    if (!token) {
      // Fallback to Authorization header for API compatibility
      const authHeader = req.headers.authorization;
      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        throw new AuthenticationError('No token provided');
      }
      req.token = authHeader.substring(7);
    }

    // Verify token with enhanced security
    const decoded = tokenManager.verifyToken(token || req.token, config.jwt.accessSecret);

    // Validate token structure
    if (!decoded.userId || !decoded.jti || !decoded.sessionId) {
      throw new AuthenticationError('Invalid token structure');
    }

    // Check session binding
    const currentDeviceFingerprint = generateDeviceFingerprint(req);
    if (decoded.deviceFingerprint && decoded.deviceFingerprint !== currentDeviceFingerprint) {
      logger.security('Device fingerprint mismatch', decoded.userId, req.ip, {
        expected: decoded.deviceFingerprint,
        received: currentDeviceFingerprint
      });
      throw new AuthenticationError('Device verification failed');
    }

    // Add user info to request
    req.user = {
      id: decoded.userId,
      email: decoded.email,
      username: decoded.username,
      role: decoded.role,
      jti: decoded.jti,
      sessionId: decoded.sessionId,
      deviceFingerprint: decoded.deviceFingerprint,
      iat: decoded.iat,
      exp: decoded.exp,
    };

    // Log successful authentication
    logger.debug('User authenticated', {
      userId: req.user.id,
      email: req.user.email,
      ip: req.ip,
      sessionId: req.user.sessionId
    });

    next();
  } catch (error) {
    if (error instanceof jwt.JsonWebTokenError) {
      logger.security('Invalid token used', undefined, req.ip, {
        error: error.message,
        userAgent: req.get('User-Agent')
      });
      throw new AuthenticationError('Invalid token');
    } else if (error instanceof jwt.TokenExpiredError) {
      logger.security('Expired token used', undefined, req.ip, {
        error: error.message,
        userAgent: req.get('User-Agent')
      });
      throw new AuthenticationError('Token expired');
    } else {
      logger.security('Authentication error', undefined, req.ip, {
        error: error.message,
        userAgent: req.get('User-Agent')
      });
      throw new AuthenticationError('Authentication failed');
    }
  }
};

function generateDeviceFingerprint(req: Request): string {
  const fingerprint = {
    userAgent: req.get('User-Agent'),
    accept: req.get('Accept'),
    acceptLanguage: req.get('Accept-Language'),
    acceptEncoding: req.get('Accept-Encoding'),
    ip: req.ip
  };

  return crypto.createHash('sha256')
    .update(JSON.stringify(fingerprint))
    .digest('hex');
}
```

**Step 3: Secure Token Storage (Frontend)**
```typescript
// /frontend/src/utils/tokenManager.ts
import axios from 'axios';

export class SecureTokenManager {
  private static instance: SecureTokenManager;

  static getInstance(): SecureTokenManager {
    if (!SecureTokenManager.instance) {
      SecureTokenManager.instance = new SecureTokenManager();
    }
    return SecureTokenManager.instance;
  }

  // Set token using secure httpOnly cookie
  async setToken(token: string): Promise<void> {
    try {
      await axios.post('/api/auth/set-token', { token }, {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    } catch (error) {
      console.error('Failed to set secure token:', error);
      throw error;
    }
  }

  // Remove token via secure endpoint
  async removeToken(): Promise<void> {
    try {
      await axios.post('/api/auth/remove-token', {}, {
        withCredentials: true
      });
    } catch (error) {
      console.error('Failed to remove token:', error);
      throw error;
    }
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return document.cookie.includes('auth_token=');
  }

  // Refresh token if needed
  async refreshToken(): Promise<void> {
    try {
      const response = await axios.post('/api/auth/refresh', {}, {
        withCredentials: true
      });

      // New token will be set via httpOnly cookie
      return response.data;
    } catch (error) {
      console.error('Token refresh failed:', error);
      await this.removeToken();
      throw error;
    }
  }
}

// Updated authentication slice
// /frontend/src/store/slices/authSlice.ts
import { SecureTokenManager } from '../utils/tokenManager';

export const loginUser = createAsyncThunk(
  'auth/login',
  async (userData: any, { rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_URL}/auth/login`, userData, {
        withCredentials: true
      });

      // Token is automatically set via httpOnly cookie
      SecureTokenManager.getInstance().setToken(response.data.token);

      toast.success('Login successful!');
      return {
        user: response.data.user,
        isAuthenticated: true
      };
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Login failed');
      return rejectWithValue(error.response?.data);
    }
  }
);

// Updated logout action
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: async (state) => {
      state.isAuthenticated = false;
      state.user = null;

      // Remove secure token
      try {
        await SecureTokenManager.getInstance().removeToken();
      } catch (error) {
        console.error('Logout token removal failed:', error);
      }
    },
  },
});
```

---

## 🟠 HIGH PRIORITY: Critical Security Improvements (7 days)

### 3. Input Validation and Sanitization

**Step 1: Comprehensive Input Validation**
```typescript
// /backend/src/middleware/inputValidation.ts
import { body, param, query, validationResult } from 'express-validator';
import DOMPurify from 'dompurify';
import validator from 'validator';

export const validateRegistration = [
  body('name')
    .trim()
    .isLength({ min: 2, max: 100 })
    .withMessage('Name must be between 2 and 100 characters')
    .matches(/^[a-zA-Z\s'-]+$/)
    .withMessage('Name can only contain letters, spaces, hyphens, and apostrophes')
    .customSanitizer(value => DOMPurify.sanitize(value, { ALLOWED_TAGS: [] })),

  body('email')
    .trim()
    .isEmail()
    .withMessage('Invalid email format')
    .normalizeEmail()
    .isLength({ max: 255 })
    .withMessage('Email too long')
    .custom(value => {
      // Check for suspicious email patterns
      const suspiciousPatterns = [
        /<script/i,
        /javascript:/i,
        /data:/i,
        /vbscript:/i,
        /onload=/i,
        /onerror=/i
      ];

      if (suspiciousPatterns.some(pattern => pattern.test(value))) {
        throw new Error('Email contains suspicious content');
      }
      return true;
    }),

  body('password')
    .isLength({ min: 8, max: 128 })
    .withMessage('Password must be between 8 and 128 characters')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
    .withMessage('Password must contain uppercase, lowercase, number, and special character')
    .not()
    .matches(/^(.)\1{2,}$/) // Prevent sequences like "aaa", "111"
    .withMessage('Password cannot contain repeating characters')
    .not()
    .matches(/(012|123|234|345|456|567|678|789|890)/)
    .withMessage('Password cannot contain sequential numbers')
];

export const validateLogin = [
  body('email')
    .trim()
    .isEmail()
    .withMessage('Invalid email format')
    .normalizeEmail(),

  body('password')
    .isLength({ min: 1 })
    .withMessage('Password is required')
    .escape()
];

export const validateUserUpdate = [
  body('name')
    .optional()
    .trim()
    .isLength({ min: 2, max: 100 })
    .matches(/^[a-zA-Z\s'-]+$/)
    .customSanitizer(value => DOMPurify.sanitize(value, { ALLOWED_TAGS: [] })),

  body('email')
    .optional()
    .trim()
    .isEmail()
    .normalizeEmail()
    .isLength({ max: 255 })
];

export const handleValidationErrors = (req: Request, res: Response, next: NextFunction) => {
  const errors = validationResult(req);

  if (!errors.isEmpty()) {
    const validationErrors = errors.array().map(error => ({
      field: error.param,
      message: error.msg,
      value: error.value
    }));

    logger.security('Input validation failed', undefined, req.ip, {
      errors: validationErrors,
      body: req.body,
      userAgent: req.get('User-Agent')
    });

    return res.status(400).json({
      message: 'Validation failed',
      errors: validationErrors
    });
  }

  next();
};
```

**Step 2: Update Authentication Routes**
```typescript
// /backend/src/routes/auth.ts (revised)
import express, { Request, Response, NextFunction } from 'express';
import bcrypt from 'bcryptjs';
import { validateRegistration, validateLogin, handleValidationErrors } from '../middleware/inputValidation';
import { rateLimiter } from '../middleware/rateLimiter';
import { tokenManager } from '../middleware/tokenManager';

const router = express.Router();

// Apply rate limiting to all auth routes
router.use(rateLimiter.auth);

// Enhanced registration with comprehensive validation
router.post('/register',
  validateRegistration,
  handleValidationErrors,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { name, email, password } = req.body;

      // Check if user already exists with timing attack protection
      const existingUser = await User.findOne({ email }).select('_id').lean();
      if (existingUser) {
        // Use consistent response time to prevent enumeration
        await bcrypt.compare(password, '$2b$12$dummy.hash.for.timing');
        return res.status(400).json({ message: 'User already exists' });
      }

      // Hash password with additional security
      const saltRounds = 12; // High strength
      const hashedPassword = await bcrypt.hash(password, saltRounds);

      // Create user with additional security fields
      const user = new User({
        name,
        email,
        password: hashedPassword,
        emailVerified: false,
        tokenVersion: 0,
        loginAttempts: 0,
        lockUntil: null,
        createdAt: new Date(),
        lastModified: new Date()
      });

      await user.save();

      // Generate verification token
      const verificationToken = crypto.randomBytes(32).toString('hex');
      await sendVerificationEmail(email, verificationToken);

      // Generate secure tokens
      const tokens = tokenManager.generateTokens({
        userId: user._id,
        email: user.email,
        role: user.role,
        tokenVersion: user.tokenVersion,
        deviceInfo: extractDeviceInfo(req)
      });

      logger.info('User registered successfully', {
        userId: user._id,
        email: user.email,
        ip: req.ip
      });

      res.status(201).json({
        message: 'Registration successful. Please verify your email.',
        tokens: {
          accessToken: tokens.accessToken,
          refreshToken: tokens.refreshToken
        },
        user: {
          id: user._id,
          name: user.name,
          email: user.email,
          role: user.role,
          emailVerified: user.emailVerified
        }
      });
    } catch (error) {
      logger.error('Registration error', { error: error.message, body: req.body });
      next(error);
    }
  }
);

// Enhanced login with brute force protection
router.post('/login',
  validateLogin,
  handleValidationErrors,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { email, password } = req.body;

      // Find user and check account lock
      const user = await User.findOne({ email }).select('+password +loginAttempts +lockUntil');

      if (!user) {
        // Use consistent timing to prevent enumeration
        await bcrypt.compare(password, '$2b$12$dummy.hash.for.timing');
        return res.status(400).json({ message: 'Invalid credentials' });
      }

      // Check if account is locked
      if (user.lockUntil && user.lockUntil > new Date()) {
        const remainingTime = Math.ceil((user.lockUntil.getTime() - Date.now()) / 60000);
        return res.status(423).json({
          message: `Account temporarily locked. Try again in ${remainingTime} minutes.`
        });
      }

      // Verify password
      const isMatch = await bcrypt.compare(password, user.password);
      if (!isMatch) {
        await handleFailedLogin(user);
        return res.status(400).json({ message: 'Invalid credentials' });
      }

      // Check if email is verified
      if (!user.emailVerified) {
        return res.status(403).json({
          message: 'Please verify your email address before logging in.'
        });
      }

      // Reset login attempts on successful login
      if (user.loginAttempts > 0) {
        await User.updateOne(
          { _id: user._id },
          { $set: { loginAttempts: 0, lockUntil: null } }
        );
      }

      // Generate secure tokens
      const tokens = tokenManager.generateTokens({
        userId: user._id,
        email: user.email,
        role: user.role,
        tokenVersion: user.tokenVersion,
        deviceInfo: extractDeviceInfo(req)
      });

      // Set secure httpOnly cookie
      res.cookie('auth_token', tokens.accessToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 3600 * 1000, // 1 hour
        path: '/'
      });

      logger.info('User logged in successfully', {
        userId: user._id,
        email: user.email,
        ip: req.ip,
        userAgent: req.get('User-Agent')
      });

      res.json({
        message: 'Login successful',
        user: {
          id: user._id,
          name: user.name,
          email: user.email,
          role: user.role
        },
        refreshToken: tokens.refreshToken // Only return refresh token
      });
    } catch (error) {
      logger.error('Login error', { error: error.message, email: req.body.email });
      next(error);
    }
  }
);

// Helper function to handle failed login attempts
async function handleFailedLogin(user: any) {
  const maxAttempts = 5;
  const lockTime = 30 * 60 * 1000; // 30 minutes

  const updateData: any = {
    $inc: { loginAttempts: 1 }
  };

  // Lock account if max attempts reached
  if (user.loginAttempts + 1 >= maxAttempts) {
    updateData.$set = {
      lockUntil: new Date(Date.now() + lockTime)
    };

    logger.security('Account locked due to too many failed attempts', user._id, undefined, {
      attempts: user.loginAttempts + 1,
      lockTime
    });
  }

  await User.updateOne({ _id: user._id }, updateData);
}

function extractDeviceInfo(req: Request) {
  return {
    userAgent: req.get('User-Agent'),
    ip: req.ip,
    accept: req.get('Accept'),
    acceptLanguage: req.get('Accept-Language')
  };
}
```

### 4. Enhanced Security Headers

**Step 1: Update Security Configuration**
```typescript
// /backend/src/config/security.ts (new file)
export const securityConfig = {
  helmet: {
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "'nonce-{nonce}'"],
        styleSrc: ["'self'", "https://fonts.googleapis.com"],
        styleSrcAttr: ["'none'"], // Remove unsafe-inline
        imgSrc: ["'self'", "data:", "https:"],
        fontSrc: ["'self'", "https://fonts.gstatic.com"],
        connectSrc: ["'self'", "wss:", "https:"],
        frameSrc: ["'none'"],
        frameAncestors: ["'none'"],
        objectSrc: ["'none'"],
        baseUri: ["'self'"],
        formAction: ["'self'"],
        manifestSrc: ["'self'"],
        workerSrc: ["'none'"],
        mediaSrc: ["'self'"],
        prefetchSrc: ["'self'"]
      }
    },
    crossOriginEmbedderPolicy: false,
    crossOriginResourcePolicy: { policy: "cross-origin" },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true
    }
  },

  cors: {
    origin: (origin: string, callback: Function) => {
      const allowedOrigins = process.env.CORS_ORIGIN?.split(',') || [];
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(new Error('Not allowed by CORS'), false);
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: [
      'Origin',
      'X-Requested-With',
      'Content-Type',
      'Accept',
      'Authorization',
      'X-API-Key',
      'X-Client-Version',
      'X-CSRF-Token'
    ],
    exposedHeaders: [
      'X-RateLimit-Limit',
      'X-RateLimit-Remaining',
      'X-RateLimit-Reset'
    ],
    maxAge: 86400 // 24 hours
  }
};

export const csrfProtection = {
  cookieOptions: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict'
  }
};
```

**Step 2: Apply Security Headers in Server**
```typescript
// /backend/src/server.ts (enhanced)
import helmet from 'helmet';
import cors from 'cors';
import csrf from 'csurf';
import { securityConfig, csrfProtection } from './config/security';

// Apply security headers
app.use(helmet(securityConfig.helmet));

// Apply CORS with strict policy
app.use(cors(securityConfig.cors));

// CSRF protection
const csrfProtection = csrf(csrfProtection.cookieOptions);
app.use(csrfProtection);

// Provide CSRF token to frontend
app.get('/api/csrf-token', csrfProtection, (req, res) => {
  res.json({ csrfToken: req.csrfToken() });
});

// Additional security headers
app.use((req, res, next) => {
  // Prevent MIME type sniffing
  res.set('X-Content-Type-Options', 'nosniff');

  // Prevent clickjacking
  res.set('X-Frame-Options', 'DENY');

  // Control referrer information
  res.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  // Disable browser features
  res.set('Permissions-Policy', 'geolocation=(), microphone=(), camera=(), payment=()');

  // Server information
  res.removeHeader('X-Powered-By');

  // Content type protection
  res.set('X-Content-Type-Options', 'nosniff');

  next();
});
```

---

## 🟡 MEDIUM PRIORITY: Security Hardening (30 days)

### 5. Enhanced Logging and Monitoring

**Step 1: Security Event Logging System**
```typescript
// /backend/src/utils/securityLogger.ts
import { logger } from './logger';

export interface SecurityEvent {
  type: 'authentication' | 'authorization' | 'data_access' | 'system_change';
  severity: 'low' | 'medium' | 'high' | 'critical';
  userId?: string;
  ip: string;
  userAgent?: string;
  sessionId?: string;
  description: string;
  metadata?: any;
  timestamp: Date;
}

export class SecurityLogger {
  private securityEvents: SecurityEvent[] = [];
  private alertThresholds = {
    failedLogins: 5,
    suspiciousIP: 10,
    rapidRequests: 100
  };

  logSecurityEvent(event: Omit<SecurityEvent, 'timestamp'>): void {
    const securityEvent: SecurityEvent = {
      ...event,
      timestamp: new Date()
    };

    // Store in memory (should be moved to database in production)
    this.securityEvents.push(securityEvent);

    // Log to main logger
    logger.security(event.description, event.userId, event.ip, {
      type: event.type,
      severity: event.severity,
      metadata: event.metadata
    });

    // Check for alert conditions
    this.checkForAlerts(securityEvent);

    // Clean old events (keep last 10000)
    if (this.securityEvents.length > 10000) {
      this.securityEvents = this.securityEvents.slice(-10000);
    }
  }

  private checkForAlerts(event: SecurityEvent): void {
    // Check for brute force attacks
    const recentFailedLogins = this.securityEvents.filter(e =>
      e.type === 'authentication' &&
      e.description.includes('failed') &&
      e.ip === event.ip &&
      (event.timestamp.getTime() - e.timestamp.getTime()) < 300000 // 5 minutes
    );

    if (recentFailedLogins.length >= this.alertThresholds.failedLogins) {
      this.sendAlert({
        type: 'BRUTE_FORCE_ATTACK',
        severity: 'high',
        ip: event.ip,
        attempts: recentFailedLogins.length,
        timeWindow: '5 minutes'
      });
    }

    // Check for suspicious IP activity
    const ipActivity = this.securityEvents.filter(e =>
      e.ip === event.ip &&
      (event.timestamp.getTime() - e.timestamp.getTime()) < 3600000 // 1 hour
    );

    if (ipActivity.length >= this.alertThresholds.suspiciousIP) {
      this.sendAlert({
        type: 'SUSPICIOUS_IP_ACTIVITY',
        severity: 'medium',
        ip: event.ip,
        events: ipActivity.length,
        timeWindow: '1 hour'
      });
    }
  }

  private sendAlert(alert: any): void {
    // Log critical alert
    logger.error('SECURITY ALERT', alert);

    // In production, send to external monitoring service
    if (process.env.NODE_ENV === 'production') {
      this.sendToExternalService(alert);
      this.sendEmailNotification(alert);
      this.sendSlackNotification(alert);
    }
  }

  private async sendToExternalService(alert: any): Promise<void> {
    // Integration with SIEM, Datadog, or other monitoring service
    try {
      const response = await fetch(process.env.SECURITY_WEBHOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.SECURITY_API_KEY}`
        },
        body: JSON.stringify({
          service: 'agent66-auth',
          alert: alert,
          timestamp: new Date().toISOString()
        })
      });

      if (!response.ok) {
        logger.error('Failed to send security alert to external service', {
          status: response.status,
          alert
        });
      }
    } catch (error) {
      logger.error('Error sending security alert to external service', {
        error: error.message,
        alert
      });
    }
  }

  getSecurityReport(timeframe: 'hour' | 'day' | 'week' = 'day'): SecurityReport {
    const now = new Date();
    const timeframes = {
      hour: 60 * 60 * 1000,
      day: 24 * 60 * 60 * 1000,
      week: 7 * 24 * 60 * 60 * 1000
    };

    const cutoffTime = new Date(now.getTime() - timeframes[timeframe]);
    const events = this.securityEvents.filter(e => e.timestamp >= cutoffTime);

    return {
      timeframe,
      totalEvents: events.length,
      eventsByType: this.groupByType(events),
      eventsBySeverity: this.groupBySeverity(events),
      topIPs: this.getTopIPs(events),
      criticalEvents: events.filter(e => e.severity === 'critical')
    };
  }

  private groupByType(events: SecurityEvent[]): Record<string, number> {
    return events.reduce((acc, event) => {
      acc[event.type] = (acc[event.type] || 0) + 1;
      return acc;
    }, {});
  }

  private groupBySeverity(events: SecurityEvent[]): Record<string, number> {
    return events.reduce((acc, event) => {
      acc[event.severity] = (acc[event.severity] || 0) + 1;
      return acc;
    }, {});
  }

  private getTopIPs(events: SecurityEvent[]): Array<{ip: string, count: number}> {
    const ipCounts = events.reduce((acc, event) => {
      acc[event.ip] = (acc[event.ip] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(ipCounts)
      .map(([ip, count]) => ({ ip, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }

  // Additional notification methods
  private async sendEmailNotification(alert: any): Promise<void> {
    // Implementation for email notifications
  }

  private async sendSlackNotification(alert: any): Promise<void> {
    // Implementation for Slack notifications
  }
}

interface SecurityReport {
  timeframe: string;
  totalEvents: number;
  eventsByType: Record<string, number>;
  eventsBySeverity: Record<string, number>;
  topIPs: Array<{ip: string, count: number}>;
  criticalEvents: SecurityEvent[];
}

export const securityLogger = new SecurityLogger();
```

### 6. Rate Limiting Enhancement

**Step 1: Advanced Rate Limiting**
```typescript
// /backend/src/middleware/advancedRateLimiter.ts
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import Redis from 'ioredis';
import { config } from '../config';
import { securityLogger } from '../utils/securityLogger';

const redis = new Redis(config.redis.url);

export const advancedRateLimiter = {
  // General API rate limiting
  general: rateLimit({
    store: new RedisStore({
      sendCommand: (...args: string[]) => redis.call(...args),
    }),
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 1000, // 1000 requests per window
    message: {
      error: 'Too many requests from this IP, please try again later.',
      retryAfter: '15 minutes'
    },
    standardHeaders: true,
    legacyHeaders: false,
    handler: (req, res) => {
      securityLogger.logSecurityEvent({
        type: 'data_access',
        severity: 'medium',
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        description: 'Rate limit exceeded',
        metadata: {
          path: req.path,
          method: req.method,
          limit: 1000
        }
      });

      res.status(429).json({
        error: 'Too many requests',
        message: 'Rate limit exceeded. Please try again later.',
        retryAfter: '15 minutes'
      });
    }
  }),

  // Authentication rate limiting
  auth: rateLimit({
    store: new RedisStore({
      sendCommand: (...args: string[]) => redis.call(...args),
    }),
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 20, // 20 auth requests per window
    message: {
      error: 'Too many authentication attempts, please try again later.',
      retryAfter: '15 minutes'
    },
    keyGenerator: (req) => {
      // Use both IP and email for login attempts
      const email = req.body?.email || 'unknown';
      return `auth:${req.ip}:${email}`;
    },
    handler: (req, res) => {
      securityLogger.logSecurityEvent({
        type: 'authentication',
        severity: 'high',
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        description: 'Authentication rate limit exceeded',
        metadata: {
          email: req.body?.email,
          path: req.path
        }
      });

      res.status(429).json({
        error: 'Too many authentication attempts',
        message: 'Authentication rate limit exceeded. Please try again later.',
        retryAfter: '15 minutes'
      });
    }
  }),

  // Password reset rate limiting
  passwordReset: rateLimit({
    store: new RedisStore({
      sendCommand: (...args: string[]) => redis.call(...args),
    }),
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 3, // 3 password reset attempts per hour
    message: {
      error: 'Too many password reset attempts, please try again later.',
      retryAfter: '1 hour'
    },
    keyGenerator: (req) => {
      const email = req.body?.email || 'unknown';
      return `password-reset:${email}`;
    },
    handler: (req, res) => {
      securityLogger.logSecurityEvent({
        type: 'authentication',
        severity: 'high',
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        description: 'Password reset rate limit exceeded',
        metadata: {
          email: req.body?.email
        }
      });

      res.status(429).json({
        error: 'Too many password reset attempts',
        message: 'Password reset rate limit exceeded. Please try again later.',
        retryAfter: '1 hour'
      });
    }
  }),

  // Registration rate limiting
  registration: rateLimit({
    store: new RedisStore({
      sendCommand: (...args: string[]) => redis.call(...args),
    }),
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 5, // 5 registrations per hour per IP
    message: {
      error: 'Too many registration attempts from this IP, please try again later.',
      retryAfter: '1 hour'
    },
    keyGenerator: (req) => `registration:${req.ip}`,
    handler: (req, res) => {
      securityLogger.logSecurityEvent({
        type: 'authentication',
        severity: 'medium',
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        description: 'Registration rate limit exceeded',
        metadata: {
          userAgent: req.get('User-Agent')
        }
      });

      res.status(429).json({
        error: 'Too many registration attempts',
        message: 'Registration rate limit exceeded. Please try again later.',
        retryAfter: '1 hour'
      });
    }
  })
};
```

---

## 🟢 LOW PRIORITY: Additional Security Features (90 days)

### 7. Dependency Security Management

**Step 1: Automated Security Scanning Setup**
```json
// package.json additions
{
  "scripts": {
    "security:audit": "npm audit --audit-level=high",
    "security:scan": "npx snyk test",
    "security:patch": "npm audit fix",
    "security:monitor": "npm install --save-dev snyk && npx snyk monitor"
  },
  "devDependencies": {
    "snyk": "^1.1000.0",
    "npm-audit-resolver": "^3.0.1",
    "audit-ci": "^6.6.1"
  }
}
```

**Step 2: GitHub Actions Security Workflow**
```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 1' # Weekly on Monday 2AM

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci

    - name: Run npm audit
      run: npm audit --audit-level=high

    - name: Run Snyk to check for vulnerabilities
      uses: snyk/actions/node@master
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
      with:
        args: --severity-threshold=high

    - name: Run CodeQL Analysis
      uses: github/codeql-action/analyze@v2
      with:
        languages: javascript
```

### 8. Database Security

**Step 1: Database Connection Security**
```typescript
// /backend/src/config/secureDatabase.ts
import { Pool } from 'pg';
import { config } from './index';

export const secureDatabaseConfig = {
  // PostgreSQL secure connection
  postgres: {
    ...config.database.postgres,
    ssl: {
      rejectUnauthorized: true,
      cert: process.env.DB_SSL_CERT,
      key: process.env.DB_SSL_KEY,
      ca: process.env.DB_SSL_CA
    },
    connectionTimeoutMillis: 10000,
    query_timeout: 30000,
    statement_timeout: 30000,
    idleTimeoutMillis: 30000,
    // Enable query logging in development
    log: (messages: string[]) => {
      if (process.env.NODE_ENV === 'development') {
        console.log('Database Query:', messages);
      }
    }
  },

  // Database query security
  queryDefaults: {
    rowMode: 'array',
    types: {
      getTypeParser: (oid: number, format: string) => {
        // Secure type parsing to prevent injection
        return (value: string) => {
          if (format === 'text') {
            return value; // Raw text, handle carefully
          }
          return JSON.parse(value); // For JSON types
        };
      }
    }
  }
};

// Secure database pool
export const dbPool = new Pool(secureDatabaseConfig.postgres);

// Query validation middleware
export const validateDatabaseQuery = (query: string, params: any[]): boolean => {
  // Check for dangerous SQL patterns
  const dangerousPatterns = [
    /drop\s+table/i,
    /delete\s+from/i,
    /truncate\s+table/i,
    /exec\s*\(/i,
    /eval\s*\(/i,
    /system\s*\(/i,
    /xp_cmdshell/i,
    /sp_oacreate/i,
    /bulk\s+insert/i,
    /openrowset/i,
    /opendatasource/i
  ];

  if (dangerousPatterns.some(pattern => pattern.test(query))) {
    throw new Error('Potentially dangerous SQL query detected');
  }

  // Validate parameters
  if (params.some(param =>
    typeof param === 'string' &&
    (param.includes(';') || param.includes('--') || param.includes('/*'))
  )) {
    throw new Error('Potentially dangerous query parameters detected');
  }

  return true;
};
```

---

## Implementation Checklist

### Phase 1: Critical Fixes (24-48 hours)
- [ ] Generate and update all secrets
- [ ] Implement token blacklisting
- [ ] Fix CSP configuration
- [ ] Add input validation for auth endpoints
- [ ] Implement secure token storage
- [ ] Add comprehensive error handling

### Phase 2: High Priority (7 days)
- [ ] Implement rate limiting
- [ ] Add CSRF protection
- [ ] Enhance security headers
- [ ] Add device fingerprinting
- [ ] Implement account lockout
- [ ] Add security monitoring
- [ ] Update frontend token management

### Phase 3: Medium Priority (30 days)
- [ ] Implement comprehensive audit logging
- [ ] Add real-time security monitoring
- [ ] Set up automated vulnerability scanning
- [ ] Implement database security
- [ ] Add session management enhancements

### Phase 4: Low Priority (90 days)
- [ ] Complete dependency security setup
- [ ] Implement compliance features
- [ ] Add security documentation
- [ ] Set up regular security assessments
- [ ] Implement security training program

---

## Testing and Validation

### Security Testing Checklist
- [ ] Penetration testing of authentication endpoints
- [ ] OWASP ZAP automated scanning
- [ ] Load testing with security scenarios
- [ ] Token security validation
- [ ] Rate limiting effectiveness testing
- [ ] CSRF protection testing
- [ ] XSS prevention testing
- [ ] SQL injection prevention testing

### Monitoring and Alerting Setup
- [ ] Configure security event alerts
- [ ] Set up SIEM integration
- [ ] Configure automated incident response
- [ ] Implement log analysis tools
- [ ] Set up security dashboard

---

**Note:** This remediation guide should be implemented by experienced security professionals. Each change should be tested in a staging environment before production deployment.