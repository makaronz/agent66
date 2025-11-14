/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Enhanced Security Middleware Suite
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * SECURITY ENHANCEMENTS:
 * ✅ Comprehensive security headers
 * ✅ Advanced rate limiting with user-specific throttling
 * ✅ Input validation and sanitization
 * ✅ CSRF protection
 * ✅ IP blocking for malicious actors
 * ✅ Request size limits
 * ✅ HTTP parameter pollution prevention
 * ✅ Security logging and monitoring
 */

import { Request, Response, NextFunction } from 'express';
import rateLimit from 'express-rate-limit';
import helmet from 'helmet';
import { logger } from '../utils/logger';
import { config } from '../config/env-validation';

// Malicious IP store (in production, use Redis or database)
const maliciousIPs = new Set<string>();
const suspiciousRequests = new Map<string, number>();

/**
 * Enhanced Security Headers Configuration
 */
export const enhancedSecurityHeaders = helmet({
  // Content Security Policy
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      fontSrc: ["'self'", "https://fonts.gstatic.com"],
      imgSrc: ["'self'", "data:", "https:"],
      scriptSrc: ["'self'"],
      connectSrc: ["'self'", "https://api.supabase.co"],
      frameSrc: ["'none'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      manifestSrc: ["'self'"],
      workerSrc: ["'self'"],
      upgradeInsecureRequests: config.app.environment === 'production' ? [] : null,
    },
  },

  // HTTP Strict Transport Security
  hsts: {
    maxAge: 31536000, // 1 year
    includeSubDomains: true,
    preload: true,
  },

  // X-Frame-Options
  frameguard: {
    action: 'deny',
  },

  // X-Content-Type-Options
  noSniff: true,

  // Referrer Policy
  referrerPolicy: {
    policy: 'strict-origin-when-cross-origin',
  },

  // X-XSS Protection (legacy but still useful)
  xssFilter: true,

  // X-Permitted-Cross-Domain-Policies
  permittedCrossDomainPolicies: false,

  // Hide X-Powered-By header
  hidePoweredBy: true,

  // Expect-CT
  expectCt: {
    maxAge: 86400,
    enforce: true,
  },
});

/**
 * Advanced Rate Limiting Configuration
 */
export const createAdvancedRateLimiter = (options: {
  windowMs: number;
  max: number;
  message?: string;
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
}) => {
  return rateLimit({
    windowMs: options.windowMs,
    max: options.max,
    message: options.message || {
      error: 'Too Many Requests',
      message: `Rate limit exceeded. Please try again later.`,
      retryAfter: Math.ceil(options.windowMs / 1000),
    },
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: options.skipSuccessfulRequests || false,
    skipFailedRequests: options.skipFailedRequests || false,

    // Custom key generator for user-specific rate limiting
    keyGenerator: (req: Request) => {
      const userId = (req as any).user?.id;
      const ip = req.ip || req.connection.remoteAddress;
      return userId ? `user:${userId}` : `ip:${ip}`;
    },

    // Custom skip function for admin bypass
    skip: (req: Request) => {
      const user = (req as any).user;
      return user?.role === 'admin';
    },

    // Custom handler with security logging
    handler: (req: Request, res: Response) => {
      const keyGenerator = (req: Request) => {
        const userId = (req as any).user?.id;
        const ip = req.ip || req.connection.remoteAddress;
        return userId ? `user:${userId}` : `ip:${ip}`;
      };

      const key = keyGenerator(req);
      const ip = req.ip || req.connection.remoteAddress;

      // Log rate limit violation
      logger.security('Rate limit exceeded', (req as any).user?.id, ip, {
        endpoint: req.path,
        method: req.method,
        userAgent: req.get('User-Agent'),
        key,
      });

      // Add IP to suspicious list
      const currentCount = suspiciousRequests.get(ip) || 0;
      suspiciousRequests.set(ip, currentCount + 1);

      // Auto-block after multiple violations
      if (currentCount > 10) {
        maliciousIPs.add(ip);
        logger.security('IP auto-blocked for repeated violations', (req as any).user?.id, ip);
      }

      res.status(429).json({
        error: 'Too Many Requests',
        message: 'Rate limit exceeded. Please try again later.',
        retryAfter: Math.ceil(options.windowMs / 1000),
      });
    },
  });
};

// Rate limiters for different endpoint types
export const authRateLimiter = createAdvancedRateLimiter({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 attempts per 15 minutes for auth
  message: {
    error: 'Authentication Rate Limit',
    message: 'Too many authentication attempts. Please try again later.',
  },
});

export const apiRateLimiter = createAdvancedRateLimiter({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // 100 requests per 15 minutes
  skipSuccessfulRequests: true,
});

export const uploadRateLimiter = createAdvancedRateLimiter({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 10, // 10 uploads per hour
});

/**
 * Input Validation Middleware
 */
export const validateInput = (req: Request, res: Response, next: NextFunction) => {
  // Check for HTTP parameter pollution
  if (req.query && typeof req.query === 'object') {
    for (const [key, value] of Object.entries(req.query)) {
      if (Array.isArray(value) && value.length > 1) {
        logger.security('HTTP parameter pollution detected', (req as any).user?.id, req.ip, {
          parameter: key,
          values: value,
        });
        return res.status(400).json({
          error: 'Bad Request',
          message: 'Invalid parameter format detected.',
        });
      }
    }
  }

  // Check request size
  const contentLength = parseInt(req.get('Content-Length') || '0');
  const maxSize = 10 * 1024 * 1024; // 10MB

  if (contentLength > maxSize) {
    logger.security('Request size exceeded', (req as any).user?.id, req.ip, {
      contentLength,
      maxSize,
    });
    return res.status(413).json({
      error: 'Request Too Large',
      message: `Request size exceeds maximum allowed size of ${maxSize / 1024 / 1024}MB.`,
    });
  }

  // Check for suspicious patterns in URL
  const suspiciousPatterns = [
    /\.\./,  // Directory traversal
    /[<>]/,  // HTML tags
    /javascript:/i,  // JavaScript protocol
    /data:.*base64/i,  // Base64 data URLs
  ];

  const url = req.originalUrl || req.url;
  for (const pattern of suspiciousPatterns) {
    if (pattern.test(url)) {
      logger.security('Suspicious URL pattern detected', (req as any).user?.id, req.ip, {
        url,
        pattern: pattern.source,
      });
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Invalid request format.',
      });
    }
  }

  next();
};

/**
 * IP Blocking Middleware
 */
export const ipBlocker = (req: Request, res: Response, next: NextFunction) => {
  const ip = req.ip || req.connection.remoteAddress;

  if (maliciousIPs.has(ip)) {
    logger.security('Blocked IP attempted access', (req as any).user?.id, ip);
    return res.status(403).json({
      error: 'Forbidden',
      message: 'Access denied.',
    });
  }

  next();
};

/**
 * CSRF Protection Middleware
 */
export const csrfProtection = (req: Request, res: Response, next: NextFunction) => {
  // Skip CSRF for GET, HEAD, OPTIONS requests
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
    return next();
  }

  // Check for CSRF token (simplified implementation)
  const csrfToken = req.get('X-CSRF-Token') || req.body._csrf;
  const sessionToken = req.session?.csrfToken;

  if (!csrfToken || csrfToken !== sessionToken) {
    logger.security('CSRF attack detected', (req as any).user?.id, req.ip, {
      method: req.method,
      path: req.path,
      csrfToken: csrfToken ? 'present' : 'missing',
    });

    return res.status(403).json({
      error: 'Forbidden',
      message: 'Invalid CSRF token.',
    });
  }

  next();
};

/**
 * Request Size Limiter
 */
export const requestSizeLimiter = (maxSize: number = 10 * 1024 * 1024) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const contentLength = parseInt(req.get('Content-Length') || '0');

    if (contentLength > maxSize) {
      logger.security('Request size limit exceeded', (req as any).user?.id, req.ip, {
        contentLength,
        maxSize,
        path: req.path,
      });

      return res.status(413).json({
        error: 'Request Too Large',
        message: `Request size exceeds maximum allowed size of ${maxSize / 1024 / 1024}MB.`,
      });
    }

    next();
  };
};

/**
 * Security Monitoring Middleware
 */
export const securityMonitor = (req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();

  // Monitor response time
  res.on('finish', () => {
    const duration = Date.now() - start;
    const ip = req.ip || req.connection.remoteAddress;

    // Log slow requests (potential DoS)
    if (duration > 5000) { // 5 seconds
      logger.security('Slow request detected', (req as any).user?.id, ip, {
        method: req.method,
        path: req.path,
        duration,
        statusCode: res.statusCode,
      });
    }

    // Monitor error rates
    if (res.statusCode >= 400) {
      const key = `${ip}:${req.path}`;
      const currentCount = suspiciousRequests.get(key) || 0;
      suspiciousRequests.set(key, currentCount + 1);

      if (currentCount > 20) { // 20 errors in short time
        logger.security('High error rate detected', (req as any).user?.id, ip, {
          path: req.path,
          errorCount: currentCount,
        });
      }
    }
  });

  next();
};

/**
 * Clean up old suspicious request records
 */
setInterval(() => {
  suspiciousRequests.clear();
}, 60 * 60 * 1000); // Clear every hour

export default {
  enhancedSecurityHeaders,
  createAdvancedRateLimiter,
  authRateLimiter,
  apiRateLimiter,
  uploadRateLimiter,
  validateInput,
  ipBlocker,
  csrfProtection,
  requestSizeLimiter,
  securityMonitor,
};