# Agent66 Security - Immediate Fixes Implementation

**Purpose:** Critical security fixes that can be implemented immediately to address the most severe vulnerabilities identified in the security audit.

---

## 🚨 CRITICAL FIXES - Implement Now (These take < 1 hour each)

### 1. Replace Default Secrets - IMMEDIATE

**Problem:** Default placeholder secrets in configuration files

**Quick Fix:** Generate new secrets and update environment files

```bash
# Run this command immediately to generate secure secrets
#!/bin/bash

echo "Generating secure secrets..."

JWT_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
JWT_ACCESS_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
JWT_REFRESH_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
ENCRYPTION_KEY=$(openssl rand -hex 16)
SESSION_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create production environment file
cat > .env.production << EOF
NODE_ENV=production
PORT=5000
HOST=0.0.0.0
APP_DEBUG=false

# Critical Security - Replace these values immediately
JWT_SECRET=$JWT_SECRET
JWT_ACCESS_SECRET=$JWT_ACCESS_SECRET
JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
SESSION_SECRET=$SESSION_SECRET

# Secure settings
BCRYPT_ROUNDS=12
JWT_EXPIRATION=3600
JWT_REFRESH_EXPIRATION=604800
SESSION_TIMEOUT=3600000
EOF

echo "✅ Production environment created with secure secrets"
echo "🚨 IMPORTANT: Save these secrets in your password manager:"
echo "JWT_SECRET=$JWT_SECRET"
echo "JWT_ACCESS_SECRET=$JWT_ACCESS_SECRET"
echo "JWT_REFRESH_SECRET=$JWT_REFRESH_SECRET"
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"
echo "SESSION_SECRET=$SESSION_SECRET"
```

### 2. Fix Content Security Policy - IMMEDIATE

**Problem:** CSP allows 'unsafe-inline' and 'unsafe-eval'

**Quick Fix:** Update security configuration

```typescript
// File: /backend/src/config/index.ts
// Replace lines 118-125 with:

contentSecurityPolicy: {
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'nonce-{nonce}'"], // Remove unsafe-inline and unsafe-eval
    styleSrc: ["'self'", "https://fonts.googleapis.com"], // Remove unsafe-inline
    styleSrcAttr: ["'none'"], // Block inline styles
    imgSrc: ["'self'", "data:", "https:"],
    fontSrc: ["'self'", "https://fonts.gstatic.com"],
    connectSrc: ["'self'", "wss:", "https:"],
    frameSrc: ["'none'"], // Block all frames
    objectSrc: ["'none'"], // Block objects
    baseUri: ["'self'"], // Restrict base URI
    formAction: ["'self'"], // Restrict form actions
    manifestSrc: ["'self'"], // Restrict manifest
    workerSrc: ["'none'"], // Disable workers
    mediaSrc: ["'self'"], // Restrict media
    prefetchSrc: ["'self'"] // Restrict prefetch
  }
}
```

### 3. Add Input Validation - IMMEDIATE

**Problem:** No input validation on authentication endpoints

**Quick Fix:** Add express-validator middleware

```typescript
// File: /backend/src/middleware/validation.ts (NEW FILE)
import { body, validationResult } from 'express-validator';

export const validateRegistration = [
  body('name')
    .trim()
    .isLength({ min: 2, max: 100 })
    .withMessage('Name must be between 2 and 100 characters')
    .matches(/^[a-zA-Z\s'-]+$/)
    .withMessage('Name can only contain letters, spaces, hyphens, and apostrophes'),

  body('email')
    .trim()
    .isEmail()
    .withMessage('Invalid email format')
    .normalizeEmail(),

  body('password')
    .isLength({ min: 8, max: 128 })
    .withMessage('Password must be between 8 and 128 characters')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
    .withMessage('Password must contain uppercase, lowercase, number, and special character')
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
];

export const handleValidationErrors = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      message: 'Validation failed',
      errors: errors.array()
    });
  }
  next();
};
```

```typescript
// File: /backend/src/routes/auth.ts (UPDATE)
// Add these lines after import statements:
import { validateRegistration, validateLogin, handleValidationErrors } from '../middleware/validation';

// Update registration route:
router.post('/register', validateRegistration, handleValidationErrors, async (req, res, next) => {
  // Existing code continues here...
});

// Update login route:
router.post('/login', validateLogin, handleValidationErrors, async (req, res, next) => {
  // Existing code continues here...
});
```

### 4. Secure Token Storage - IMMEDIATE

**Problem:** JWT tokens stored in localStorage (XSS vulnerable)

**Quick Fix:** Add httpOnly cookie middleware

```typescript
// File: /backend/src/middleware/cookieAuth.ts (NEW FILE)
export const setAuthCookie = (res, token) => {
  res.cookie('auth_token', token, {
    httpOnly: true, // Prevent XSS access
    secure: process.env.NODE_ENV === 'production', // HTTPS only in production
    sameSite: 'strict', // Prevent CSRF
    maxAge: 3600 * 1000, // 1 hour
    path: '/'
  });
};

export const clearAuthCookie = (res) => {
  res.clearCookie('auth_token', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/'
  });
};

// Middleware to read token from cookie
export const tokenFromCookie = (req) => {
  return req.cookies?.auth_token;
};
```

```typescript
// File: /backend/src/routes/auth.ts (UPDATE)
// Update login route success response:
const token = jwt.sign(payload, secret, { expiresIn: process.env.JWT_EXPIRES_IN || '1d' });

// Set secure cookie instead of returning token
setAuthCookie(res, token);

res.json({
  message: 'Login successful',
  user: {
    id: user._id,
    email: user.email,
    name: user.name,
    role: user.role
  }
  // Don't return token
});

// Update logout route:
router.post('/logout', (req, res) => {
  clearAuthCookie(res);
  res.json({ message: 'Logout successful' });
});
```

### 5. Add Basic Rate Limiting - IMMEDIATE

**Problem:** No rate limiting on authentication endpoints

**Quick Fix:** Add express-rate-limit

```bash
# Install rate limiting package
npm install express-rate-limit
```

```typescript
// File: /backend/src/middleware/rateLimit.ts (NEW FILE)
import rateLimit from 'express-rate-limit';

export const authRateLimit = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 20, // 20 attempts per window
  message: {
    error: 'Too many authentication attempts',
    message: 'Please try again later.',
    retryAfter: '15 minutes'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

export const loginRateLimit = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 login attempts per window
  message: {
    error: 'Too many login attempts',
    message: 'Account temporarily locked. Please try again later.',
    retryAfter: '15 minutes'
  },
  skipSuccessfulRequests: true,
});
```

```typescript
// File: /backend/src/routes/auth.ts (UPDATE)
// Add at top:
import { authRateLimit, loginRateLimit } from '../middleware/rateLimit';

// Add middleware to routes:
router.use(authRateLimit); // Apply to all auth routes
router.post('/login', loginRateLimit, validateLogin, handleValidationErrors, async (req, res, next) => {
  // Existing login code...
});
```

### 6. Add Security Headers - IMMEDIATE

**Problem:** Missing security headers

**Quick Fix:** Add helmet middleware

```bash
# Install helmet
npm install helmet
```

```typescript
// File: /backend/src/server.ts (UPDATE)
// Add near top:
import helmet from 'helmet';

// Add after app creation:
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'nonce-{nonce}'"],
      styleSrc: ["'self'", "https://fonts.googleapis.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'"],
      frameSrc: ["'none'"],
      objectSrc: ["'none'"]
    }
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));

// Additional headers
app.use((req, res, next) => {
  res.header('X-Content-Type-Options', 'nosniff');
  res.header('X-Frame-Options', 'DENY');
  res.header('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.header('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  next();
});
```

---

## 🔧 HIGH PRIORITY FIXES - Implement Today (2-4 hours)

### 7. Add Account Lockout

```typescript
// File: /backend/src/middleware/accountLockout.ts (NEW FILE)
const loginAttempts = new Map(); // In production, use Redis

export const checkAccountLockout = async (req, res, next) => {
  const { email } = req.body;
  const ip = req.ip;
  const key = `${email}_${ip}`;

  const attempts = loginAttempts.get(key) || { count: 0, lastAttempt: null };

  // Lock account after 5 failed attempts for 30 minutes
  if (attempts.count >= 5 && attempts.lastAttempt &&
      (Date.now() - attempts.lastAttempt) < 30 * 60 * 1000) {
    return res.status(423).json({
      error: 'Account locked',
      message: 'Too many failed attempts. Try again in 30 minutes.'
    });
  }

  // Reset attempts after 30 minutes of inactivity
  if (attempts.lastAttempt &&
      (Date.now() - attempts.lastAttempt) > 30 * 60 * 1000) {
    loginAttempts.set(key, { count: 0, lastAttempt: null });
  }

  next();
};

export const recordFailedAttempt = (email, ip) => {
  const key = `${email}_${ip}`;
  const attempts = loginAttempts.get(key) || { count: 0, lastAttempt: null };

  attempts.count++;
  attempts.lastAttempt = Date.now();
  loginAttempts.set(key, attempts);
};

export const recordSuccessfulLogin = (email, ip) => {
  const key = `${email}_${ip}`;
  loginAttempts.delete(key); // Clear failed attempts on success
};
```

### 8. Add Token Blacklisting

```typescript
// File: /backend/src/middleware/tokenBlacklist.ts (NEW FILE)
const blacklistedTokens = new Set(); // In production, use Redis

export const blacklistToken = (token) => {
  blacklistedTokens.add(token);
  // Auto-cleanup after 24 hours
  setTimeout(() => blacklistedTokens.delete(token), 24 * 60 * 60 * 1000);
};

export const isTokenBlacklisted = (token) => {
  return blacklistedTokens.has(token);
};
```

```typescript
// File: /backend/src/middleware/auth.ts (UPDATE)
// Update JWT verification:
const decoded = jwt.verify(token, config.jwt.secret);

// Add blacklist check:
if (isTokenBlacklisted(token)) {
  throw new AuthenticationError('Token has been revoked');
}
```

### 9. Add Error Handling Security

```typescript
// File: /backend/src/middleware/secureErrorHandler.ts (NEW FILE)
export const secureErrorHandler = (error, req, res, next) => {
  // Log full error for debugging (development only)
  if (process.env.NODE_ENV === 'development') {
    console.error(error);
  }

  // Always return generic error messages to clients
  let statusCode = 500;
  let message = 'An error occurred';

  if (error.name === 'ValidationError') {
    statusCode = 400;
    message = 'Invalid input provided';
  } else if (error.name === 'AuthenticationError') {
    statusCode = 401;
    message = 'Authentication failed';
  } else if (error.name === 'AuthorizationError') {
    statusCode = 403;
    message = 'Access denied';
  } else if (error.name === 'JsonWebTokenError') {
    statusCode = 401;
    message = 'Invalid token';
  } else if (error.name === 'TokenExpiredError') {
    statusCode = 401;
    message = 'Token expired';
  }

  // Never expose stack traces or internal details
  res.status(statusCode).json({
    message,
    timestamp: new Date().toISOString(),
    path: req.path
  });
};
```

### 10. Add Database Security

```typescript
// File: /backend/src/config/databaseSecurity.ts (NEW FILE)
export const secureDatabaseConfig = {
  // Force SSL in production
  ssl: process.env.NODE_ENV === 'production' ? {
    rejectUnauthorized: true
  } : false,

  // Connection limits
  connectionLimit: 20,
  queueLimit: 0,

  // Query timeout
  acquireTimeout: 60000,
  timeout: 60000,

  // Enable query logging in development
  debug: process.env.NODE_ENV === 'development'
};

// Database query validator
export const validateQuery = (sql) => {
  const dangerousPatterns = [
    /drop\s+table/i,
    /delete\s+from/i,
    /truncate\s+table/i,
    /exec\s*\(/i,
    /eval\s*\(/i,
    /system\s*\(/i
  ];

  return !dangerousPatterns.some(pattern => pattern.test(sql));
};
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (30 minutes)
- [ ] Run the secret generation script
- [ ] Update .env.production with new secrets
- [ ] Install security packages: `npm install helmet express-rate-limit express-validator`
- [ ] Add CSP configuration fix
- [ ] Add basic input validation
- [ ] Implement secure cookie storage
- [ ] Add basic rate limiting
- [ ] Add security headers

### Phase 2: High Priority (2 hours)
- [ ] Implement account lockout mechanism
- [ ] Add token blacklisting
- [ ] Implement secure error handling
- [ ] Add database security configuration
- [ ] Update authentication middleware
- [ ] Test all authentication flows

### Phase 3: Testing (1 hour)
- [ ] Test authentication with secure cookies
- [ ] Verify rate limiting works
- [ ] Test account lockout functionality
- [ ] Verify CSP headers are correct
- [ ] Test error handling doesn't leak information
- [ ] Run security tests

---

## 🔍 QUICK SECURITY TESTS

Run these commands after implementing fixes:

```bash
# Test security headers
curl -I http://localhost:5000/api/auth/login

# Should see:
# content-security-policy: default-src 'self'...
# x-frame-options: DENY
# x-content-type-options: nosniff
# strict-transport-security: max-age=31536000...

# Test rate limiting
for i in {1..25}; do
  curl -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"test"}' \
    -w "%{http_code}\n"
done

# Should see 429 (Too Many Requests) after 20 attempts

# Test input validation
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"<script>alert(1)</script>","email":"test@test.com","password":"password"}' \
  -w "%{http_code}\n"

# Should see 400 (Bad Request)
```

---

## 🚨 POST-IMPLEMENTATION VERIFICATION

After implementing these fixes, verify:

1. **Secrets are secure:**
   ```bash
   grep -r "CHANGE_ME\|DEFAULT\|TEST" .env.*
   # Should return no results
   ```

2. **CSP is working:**
   ```bash
   curl -I http://localhost:5000 | grep content-security-policy
   # Should not contain 'unsafe-inline' or 'unsafe-eval'
   ```

3. **Rate limiting works:**
   ```bash
   # Run 25 curl requests quickly, should get 429
   ```

4. **Input validation works:**
   ```bash
   # Try XSS payload, should get 400
   ```

5. **Security headers present:**
   ```bash
   curl -I http://localhost:5000
   # Should include all security headers
   ```

---

## 📞 EMERGENCY CONTACT INFORMATION

If any security issue occurs during implementation:

1. **Immediate Actions:**
   - Stop the application: `pkill -f "node.*server"`
   - Check logs: `tail -f logs/smc_trading.log`
   - Review recent changes: `git diff HEAD~5`

2. **Rollback Plan:**
   ```bash
   git checkout HEAD~1
   npm install
   npm run build
   npm start
   ```

3. **Security Team Notification:**
   - Email: security@yourcompany.com
   - Slack: #security-alerts
   - Phone: [Security Team Phone]

---

**⚠️ IMPORTANT:** These fixes address the most critical vulnerabilities. A complete security implementation requires all items from the full remediation guide. Schedule additional time to implement medium and low priority fixes.