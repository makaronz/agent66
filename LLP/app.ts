/**
 * This is a API server with comprehensive security and validation
 */

import express, { type Request, type Response, type NextFunction } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import helmet from 'helmet';
import compression from 'compression';
import authRoutes from './routes/auth';
import binanceRoutes from './routes/binance';
import userRoutes from './routes/users';
import authMfaRoutes from './auth-mfa';
import {
  corsOptions,
  securityHeaders,
  sanitizeInput,
  requestLogger,
  errorHandler,
  healthCheck,
  generalRateLimit
} from './middleware/validation';
import swaggerMiddleware, { swaggerUi } from './middleware/swagger';
import { swaggerSpec, API_VERSION } from './config/swagger';
import versioning, { 
  versionDetectionMiddleware, 
  responseTransformMiddleware,
  getVersionInfoEndpoint,
  getMigrationGuideEndpoint,
  API_VERSIONS 
} from './config/versioning';

// load env
dotenv.config();

const app: express.Application = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: [
        "'self'", 
        "https://api.binance.com", 
        "https://api.bybit.com", 
        "https://api-fxtrade.oanda.com",
        "wss:"
      ],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"]
    }
  },
  crossOriginEmbedderPolicy: false
}));

// Compression middleware
app.use(compression());

// CORS with validation
app.use(cors(corsOptions));

// Security headers
app.use(securityHeaders);

// Request logging
app.use(requestLogger);

// Rate limiting
app.use(generalRateLimit);

// Body parsing with limits
app.use(express.json({ 
  limit: '1mb',
  verify: (req, res, buf) => {
    // Verify JSON payload
    try {
      JSON.parse(buf.toString());
    } catch (e) {
      throw new Error('Invalid JSON payload');
    }
  }
}));

app.use(express.urlencoded({ 
  extended: true, 
  limit: '1mb',
  parameterLimit: 100
}));

// Input sanitization
app.use(sanitizeInput);

// API versioning middleware
app.use('/api', versionDetectionMiddleware);
app.use('/api', responseTransformMiddleware);

/**
 * API Documentation Routes
 */
// Serve OpenAPI spec as JSON
app.get('/api/docs/openapi.json', (req: Request, res: Response): void => {
  res.setHeader('Content-Type', 'application/json');
  res.json(swaggerSpec);
});

// Serve Swagger UI documentation
app.use('/api/docs', swaggerUi.serve, ...swaggerMiddleware.setup);

// Redirect /docs to /api/docs for convenience
app.get('/docs', (req: Request, res: Response): void => {
  res.redirect('/api/docs');
});

/**
 * API Version Information Routes
 */
app.get('/api/version', getVersionInfoEndpoint);
app.get('/api/migration/:from/:to', getMigrationGuideEndpoint);

/**
 * API Routes (Versioned)
 */

// Create versioned routers
const v1Router = express.Router();
const v2Router = express.Router(); // Future version

// V1 Routes (Current)
v1Router.use('/auth', authRoutes);
v1Router.use('/binance', binanceRoutes);
v1Router.use('/users', userRoutes);
v1Router.use('/auth-mfa', authMfaRoutes);

// V2 Routes (Future - placeholder)
v2Router.use('/auth', (req: Request, res: Response) => {
  res.status(501).json({
    success: false,
    error: 'API v2 is not yet implemented',
    message: 'Please use API v1 for now',
    migration_guide: '/api/migration/v1/v2'
  });
});

// Mount versioned API routers
app.use('/api/v1', v1Router);
app.use('/api/v2', v2Router);

// Default version routing (no version specified)
app.use('/api', (req: Request, res: Response, next: NextFunction) => {
  // Check if request already has version in path
  if (req.path.match(/^\/v\d+/)) {
    return next();
  }
  
  // Redirect to default version with deprecation warning
  const originalUrl = req.originalUrl.replace('/api', `/api/${API_VERSION}`);
  
  res.setHeader('Warning', '299 - "Unversioned API access is deprecated. Please specify version in URL path."');
  res.setHeader('X-API-Version', API_VERSION);
  res.setHeader('X-Deprecated-Endpoint', req.originalUrl);
  res.setHeader('X-Recommended-Endpoint', originalUrl);
  
  // For GET requests, redirect
  if (req.method === 'GET') {
    return res.redirect(301, originalUrl);
  }
  
  // For other methods, forward to default version
  req.url = req.url.replace(/^\/api/, `/api/${API_VERSION}`);
  next();
});

// Legacy routes (for backward compatibility - will be removed in v2)
app.use('/api/binance', (req: Request, res: Response, next: NextFunction) => {
  res.setHeader('Warning', '299 - "Legacy endpoint. Use /api/v1/binance instead."');
  res.setHeader('X-API-Version', API_VERSION);
  res.setHeader('X-Deprecated-Endpoint', req.originalUrl);
  res.setHeader('X-Recommended-Endpoint', req.originalUrl.replace('/api/binance', '/api/v1/binance'));
  next();
}, binanceRoutes);

app.use('/api/users', (req: Request, res: Response, next: NextFunction) => {
  res.setHeader('Warning', '299 - "Legacy endpoint. Use /api/v1/users instead."');
  res.setHeader('X-API-Version', API_VERSION);
  res.setHeader('X-Deprecated-Endpoint', req.originalUrl);
  res.setHeader('X-Recommended-Endpoint', req.originalUrl.replace('/api/users', '/api/v1/users'));
  next();
}, userRoutes);

app.use('/api/auth-mfa', (req: Request, res: Response, next: NextFunction) => {
  res.setHeader('Warning', '299 - "Legacy endpoint. Use /api/v1/auth-mfa instead."');
  res.setHeader('X-API-Version', API_VERSION);
  res.setHeader('X-Deprecated-Endpoint', req.originalUrl);
  res.setHeader('X-Recommended-Endpoint', req.originalUrl.replace('/api/auth-mfa', '/api/v1/auth-mfa'));
  next();
}, authMfaRoutes);

/**
 * Health check endpoint
 */
app.get('/api/health', healthCheck);

/**
 * API status endpoint
 */
app.get('/api/status', (req: Request, res: Response): void => {
  res.status(200).json({
    success: true,
    message: 'SMC Trading Agent API is running',
    version: process.env.npm_package_version || '1.0.0',
    environment: process.env.NODE_ENV || 'development',
    timestamp: new Date().toISOString()
  });
});

/**
 * Error handler middleware
 */
app.use(errorHandler);

/**
 * 404 handler
 */
app.use((req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: 'API endpoint not found',
    path: req.path,
    method: req.method,
    timestamp: new Date().toISOString()
  });
});

export default app;