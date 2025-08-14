/**
 * This is a API server with comprehensive security and validation
 */

import express, { type Request, type Response } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import helmet from 'helmet';
import compression from 'compression';
import binanceRoutes from './routes/binance.js';
import userRoutes from './routes/users.js';
import authMfaRoutes from './auth-mfa.js';
import {
  corsOptions,
  securityHeaders,
  sanitizeInput,
  requestLogger,
  errorHandler,
  healthCheck,
  generalRateLimit
} from './middleware/validation.js';

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

/**
 * API Routes
 */
app.use('/api/auth', (req, res) => {
  console.log('Auth route accessed');
  res.json({ message: 'Auth endpoint' });
});

app.use('/api/binance', binanceRoutes);
app.use('/api/users', userRoutes);
app.use('/api/auth-mfa', authMfaRoutes);

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