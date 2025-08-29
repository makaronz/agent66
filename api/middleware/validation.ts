/**
 * Input validation middleware using Zod schemas
 * Provides comprehensive request validation and sanitization
 */

import { Request, Response, NextFunction } from 'express';
import { z, ZodError } from 'zod';
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import Redis from 'ioredis';

// Redis client for rate limiting
const redis = process.env.REDIS_ENABLED === 'false' 
  ? null 
  : new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD,
      maxRetriesPerRequest: null,
      lazyConnect: true,
      enableOfflineQueue: false,
      retryStrategy: (times) => Math.min(1000 * times, 5000)
    });

// Handle Redis connection errors gracefully in development
if (redis) {
  redis.on('error', (e) => {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('[redis] dev connection problem:', e.message);
    }
  });
  
  redis.connect().catch(() => {
    if (process.env.NODE_ENV !== 'production') {
      console.warn('[redis] Failed to connect in development mode - continuing without Redis');
    }
  });
}

// Generic validation middleware factory
export const validateRequest = (schema: {
  body?: z.ZodSchema;
  query?: z.ZodSchema;
  params?: z.ZodSchema;
}) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Validate request body
      if (schema.body) {
        req.body = await schema.body.parseAsync(req.body);
      }

      // Validate query parameters
      if (schema.query) {
        req.query = await schema.query.parseAsync(req.query) as any;
      }

      // Validate URL parameters
      if (schema.params) {
        req.params = await schema.params.parseAsync(req.params) as any;
      }

      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const validationErrors = (error as any).errors.map((err: any) => ({
          field: err.path.join('.'),
          message: err.message,
          code: err.code,
          received: err.received
        }));

        return res.status(400).json({
          success: false,
          error: 'Validation failed',
          details: validationErrors,
          timestamp: new Date().toISOString()
        });
      }

      // Handle other validation errors
      console.error('Validation middleware error:', error);
      return res.status(500).json({
        success: false,
        error: 'Internal validation error',
        timestamp: new Date().toISOString()
      });
    }
  };
};

// Sanitization middleware
export const sanitizeInput = (req: Request, res: Response, next: NextFunction) => {
  // Recursively sanitize object properties
  const sanitizeObject = (obj: any): any => {
    if (typeof obj === 'string') {
      // Remove potentially dangerous characters
      return obj
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
        .replace(/javascript:/gi, '') // Remove javascript: protocol
        .replace(/on\w+\s*=/gi, '') // Remove event handlers
        .trim();
    }
    
    if (Array.isArray(obj)) {
      return obj.map(sanitizeObject);
    }
    
    if (obj && typeof obj === 'object') {
      const sanitized: any = {};
      for (const [key, value] of Object.entries(obj)) {
        // Sanitize key names
        const sanitizedKey = key.replace(/[^\w.-]/g, '');
        if (sanitizedKey) {
          sanitized[sanitizedKey] = sanitizeObject(value);
        }
      }
      return sanitized;
    }
    
    return obj;
  };

  // Sanitize request body
  if (req.body) {
    req.body = sanitizeObject(req.body);
  }

  // Sanitize query parameters
  if (req.query) {
    req.query = sanitizeObject(req.query);
  }

  next();
};

// Rate limiting configurations
export const createRateLimit = (options: {
  windowMs: number;
  max: number;
  message?: string;
  skipSuccessfulRequests?: boolean;
  keyGenerator?: (req: Request) => string;
}) => {
  const rateLimitConfig: any = {
    windowMs: options.windowMs,
    max: options.max,
    message: {
      success: false,
      error: options.message || 'Too many requests, please try again later',
      retryAfter: Math.ceil(options.windowMs / 1000),
      timestamp: new Date().toISOString()
    },
    standardHeaders: true,
    legacyHeaders: false,
    skipSuccessfulRequests: options.skipSuccessfulRequests || false,
    keyGenerator: options.keyGenerator || ((req: Request) => {
      // Use user ID if authenticated, otherwise IP address
      return req.user?.id || req.ip;
    }),
    handler: (req: Request, res: Response) => {
      res.status(429).json({
        success: false,
        error: options.message || 'Too many requests, please try again later',
        retryAfter: Math.ceil(options.windowMs / 1000),
        timestamp: new Date().toISOString()
      });
    }
  };

  // Add Redis store only if Redis is available
  if (redis) {
    rateLimitConfig.store = new RedisStore({
      sendCommand: (...args: string[]) => redis.call(args[0], ...args.slice(1)) as any,
    });
  } else if (process.env.NODE_ENV !== 'production') {
    console.warn('[redis] Rate limiting using memory store - Redis disabled in development');
  }

  return rateLimit(rateLimitConfig);
};

// Predefined rate limiters - lazy initialization to respect environment variables
let _generalRateLimit: any;
let _authRateLimit: any;
let _tradingRateLimit: any;
let _apiKeyRateLimit: any;
let _marketDataRateLimit: any;

export const generalRateLimit = (req: any, res: any, next: any) => {
  if (!_generalRateLimit) {
    _generalRateLimit = createRateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100, // 100 requests per window
      message: 'Too many requests from this IP, please try again later'
    });
  }
  return _generalRateLimit(req, res, next);
};

export const authRateLimit = (req: any, res: any, next: any) => {
  if (!_authRateLimit) {
    _authRateLimit = createRateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 5, // 5 login attempts per window
      message: 'Too many authentication attempts, please try again later',
      skipSuccessfulRequests: true
    });
  }
  return _authRateLimit(req, res, next);
};

export const tradingRateLimit = (req: any, res: any, next: any) => {
  if (!_tradingRateLimit) {
    _tradingRateLimit = createRateLimit({
      windowMs: 60 * 1000, // 1 minute
      max: 10, // 10 trading requests per minute
      message: 'Too many trading requests, please slow down'
    });
  }
  return _tradingRateLimit(req, res, next);
};

export const apiKeyRateLimit = (req: any, res: any, next: any) => {
  if (!_apiKeyRateLimit) {
    _apiKeyRateLimit = createRateLimit({
      windowMs: 60 * 60 * 1000, // 1 hour
      max: 5, // 5 API key operations per hour
      message: 'Too many API key operations, please try again later'
    });
  }
  return _apiKeyRateLimit(req, res, next);
};

export const marketDataRateLimit = (req: any, res: any, next: any) => {
  if (!_marketDataRateLimit) {
    _marketDataRateLimit = createRateLimit({
      windowMs: 60 * 1000, // 1 minute
      max: 60, // 60 market data requests per minute
      message: 'Too many market data requests, please slow down'
    });
  }
  return _marketDataRateLimit(req, res, next);
};

// CORS configuration with validation
export const corsOptions = {
  origin: (origin: string | undefined, callback: (err: Error | null, allow?: boolean) => void) => {
    const allowedOrigins = [
      'http://localhost:3000',
      'http://localhost:5173',
      'http://localhost:8080',
      'https://smc-trading-agent.vercel.app',
      process.env.FRONTEND_URL
    ].filter(Boolean);

    // Allow requests with no origin (mobile apps, etc.)
    if (!origin) return callback(null, true);

    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS policy'), false);
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
    'X-Client-Version'
  ],
  exposedHeaders: [
    'X-RateLimit-Limit',
    'X-RateLimit-Remaining',
    'X-RateLimit-Reset'
  ],
  maxAge: 86400 // 24 hours
};

// Security headers middleware
export const securityHeaders = (req: Request, res: Response, next: NextFunction) => {
  // Set security headers
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  
  // Content Security Policy
  res.setHeader('Content-Security-Policy', [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "connect-src 'self' https://api.binance.com https://api.bybit.com https://api-fxtrade.oanda.com wss:",
    "font-src 'self'",
    "object-src 'none'",
    "media-src 'self'",
    "frame-src 'none'"
  ].join('; '));

  next();
};

// Request logging middleware
export const requestLogger = (req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();
  const originalSend = res.send;

  // Override res.send to capture response
  res.send = function(body: any) {
    const duration = Date.now() - start;
    
    // Log request details (excluding sensitive data)
    const logData = {
      timestamp: new Date().toISOString(),
      method: req.method,
      url: req.url,
      ip: req.ip,
      userAgent: req.get('User-Agent'),
      userId: req.user?.id,
      statusCode: res.statusCode,
      duration: `${duration}ms`,
      contentLength: body ? Buffer.byteLength(body) : 0
    };

    // Don't log sensitive endpoints in detail
    const sensitiveEndpoints = ['/api/auth/login', '/api/users/api-keys'];
    const isSensitive = sensitiveEndpoints.some(endpoint => req.url.includes(endpoint));
    
    if (!isSensitive || res.statusCode >= 400) {
      console.log('API Request:', JSON.stringify(logData));
    }

    // Call original send
    return originalSend.call(this, body);
  };

  next();
};

// Error handling middleware
export const errorHandler = (error: Error, req: Request, res: Response, next: NextFunction) => {
  console.error('API Error:', {
    timestamp: new Date().toISOString(),
    error: error.message,
    stack: error.stack,
    url: req.url,
    method: req.method,
    ip: req.ip,
    userId: req.user?.id
  });

  // Don't leak error details in production
  const isDevelopment = process.env.NODE_ENV === 'development';
  
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    ...(isDevelopment && { details: error.message, stack: error.stack }),
    timestamp: new Date().toISOString()
  });
};

// Health check with validation
export const healthCheck = (req: Request, res: Response) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    version: process.env.npm_package_version || '1.0.0',
    environment: process.env.NODE_ENV || 'development'
  };

  res.status(200).json(health);
};