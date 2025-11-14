import { Request, Response, NextFunction } from 'express';
import {
  errorHandler,
  asyncHandler,
  notFoundHandler,
  CustomError,
  ValidationError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  ConflictError,
  RateLimitError,
  DatabaseError,
  ExternalServiceError
} from '../../middleware/errorHandler';

// Mock dependencies
jest.mock('../../utils/logger', () => ({
  logger: {
    error: jest.fn(),
  }
}));

jest.mock('../../config/env-validation', () => ({
  config: {
    app: {
      debug: false,
      environment: 'production'
    },
    rateLimit: {
      windowMs: 900000
    }
  }
}));

describe('Error Handler Middleware', () => {
  let mockRequest: Partial<Request>;
  let mockResponse: Partial<Response>;
  let mockNext: NextFunction;

  beforeEach(() => {
    mockRequest = {
      url: '/api/test',
      method: 'GET',
      ip: '127.0.0.1',
      get: jest.fn()
    };
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis(),
      set: jest.fn().mockReturnThis()
    };
    mockNext = jest.fn();
  });

  describe('CustomError Classes', () => {
    it('should create CustomError with correct properties', () => {
      const details = { field: 'email', message: 'Invalid format' };
      const error = new CustomError('Test error', 400, 'TEST_ERROR', details);

      expect(error.message).toBe('Test error');
      expect(error.statusCode).toBe(400);
      expect(error.code).toBe('TEST_ERROR');
      expect(error.details).toEqual(details);
      expect(error.isOperational).toBe(true);
      expect(error.name).toBe('CustomError');
    });

    it('should create ValidationError with correct properties', () => {
      const error = new ValidationError('Validation failed');

      expect(error.message).toBe('Validation failed');
      expect(error.statusCode).toBe(400);
      expect(error.code).toBe('VALIDATION_ERROR');
    });

    it('should create AuthenticationError with correct properties', () => {
      const error = new AuthenticationError('Auth failed');

      expect(error.message).toBe('Auth failed');
      expect(error.statusCode).toBe(401);
      expect(error.code).toBe('AUTHENTICATION_ERROR');
    });

    it('should create AuthorizationError with correct properties', () => {
      const error = new AuthorizationError();

      expect(error.message).toBe('Access denied');
      expect(error.statusCode).toBe(403);
      expect(error.code).toBe('AUTHORIZATION_ERROR');
    });

    it('should create NotFoundError with correct properties', () => {
      const error = new NotFoundError('User not found');

      expect(error.message).toBe('User not found');
      expect(error.statusCode).toBe(404);
      expect(error.code).toBe('NOT_FOUND');
    });

    it('should create ConflictError with correct properties', () => {
      const error = new ConflictError('Email exists');

      expect(error.message).toBe('Email exists');
      expect(error.statusCode).toBe(409);
      expect(error.code).toBe('CONFLICT_ERROR');
    });

    it('should create RateLimitError with correct properties', () => {
      const error = new RateLimitError();

      expect(error.message).toBe('Rate limit exceeded');
      expect(error.statusCode).toBe(429);
      expect(error.code).toBe('RATE_LIMIT_EXCEEDED');
    });

    it('should create DatabaseError with correct properties', () => {
      const error = new DatabaseError('Connection failed');

      expect(error.message).toBe('Connection failed');
      expect(error.statusCode).toBe(500);
      expect(error.code).toBe('DATABASE_ERROR');
    });

    it('should create ExternalServiceError with correct properties', () => {
      const error = new ExternalServiceError('Service down', 'payment-api');

      expect(error.message).toBe('Service down');
      expect(error.statusCode).toBe(502);
      expect(error.code).toBe('EXTERNAL_SERVICE_ERROR');
      expect(error.details).toEqual({ service: 'payment-api' });
    });
  });

  describe('errorHandler', () => {
    it('should handle CustomError correctly', () => {
      const error = new ValidationError('Invalid email format', {
        field: 'email',
        value: 'invalid-email'
      });

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Invalid email format',
          timestamp: expect.any(String)
        }
      });
    });

    it('should handle ValidationError (from validation library)', () => {
      const error = new Error('Validation failed');
      error.name = 'ValidationError';

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          timestamp: expect.any(String)
        }
      });
    });

    it('should handle CastError (invalid ID format)', () => {
      const error = new Error('Cast to ObjectId failed');
      error.name = 'CastError';

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'INVALID_ID',
          message: 'Invalid ID format',
          timestamp: expect.any(String)
        }
      });
    });

    it('should handle MongoDB errors', () => {
      const error = new Error('Connection timeout');
      error.name = 'MongoError';

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.status).toHaveBeenCalledWith(500);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'DATABASE_ERROR',
          message: 'Database operation failed',
          timestamp: expect.any(String)
        }
      });
    });

    it('should handle JsonWebTokenError', () => {
      const error = new Error('Invalid token');
      error.name = 'JsonWebTokenError';

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.status).toHaveBeenCalledWith(401);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'INVALID_TOKEN',
          message: 'Invalid authentication token',
          timestamp: expect.any(String)
        }
      });
    });

    it('should handle TokenExpiredError', () => {
      const error = new Error('Token expired');
      error.name = 'TokenExpiredError';

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.status).toHaveBeenCalledWith(401);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'TOKEN_EXPIRED',
          message: 'Authentication token expired',
          timestamp: expect.any(String)
        }
      });
    });

    it('should handle JSON syntax errors', () => {
      const error = new Error('Unexpected token');
      error.name = 'SyntaxError';
      (error as any).body = true;

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'INVALID_JSON',
          message: 'Invalid JSON in request body',
          timestamp: expect.any(String)
        }
      });
    });

    it('should handle rate limit errors with retry-after header', () => {
      const error = new RateLimitError();

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.set).toHaveBeenCalledWith('Retry-After', '900');
      expect(mockResponse.status).toHaveBeenCalledWith(429);
    });

    it('should include details in development mode', () => {
      // Mock development config
      jest.doMock('../../config/env-validation', () => ({
        config: {
          app: {
            debug: true,
            environment: 'development'
          },
          rateLimit: {
            windowMs: 900000
          }
        }
      }));

      const error = new ValidationError('Validation failed', {
        field: 'email',
        value: 'invalid'
      });

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          timestamp: expect.any(String),
          details: {
            field: 'email',
            value: 'invalid'
          },
          stack: expect.any(String),
          request: {
            method: 'GET',
            url: '/api/test',
            ip: '127.0.0.1',
            userAgent: undefined
          }
        }
      });
    });

    it('should log error information', () => {
      const { logger } = require('../../utils/logger');
      const error = new Error('Test error');

      errorHandler(
        error,
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(logger.error).toHaveBeenCalledWith('API Error:', {
        message: 'Test error',
        statusCode: undefined,
        code: undefined,
        stack: expect.any(String),
        url: '/api/test',
        method: 'GET',
        ip: '127.0.0.1',
        userAgent: undefined
      });
    });
  });

  describe('asyncHandler', () => {
    it('should catch errors from async functions and pass to next', async () => {
      const asyncFunction = jest.fn().mockRejectedValue(new Error('Async error'));
      const wrappedHandler = asyncHandler(asyncFunction);

      await wrappedHandler(
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith(new Error('Async error'));
    });

    it('should resolve successfully when async function completes', async () => {
      const asyncFunction = jest.fn().mockResolvedValue({ success: true });
      const wrappedHandler = asyncHandler(asyncFunction);

      await wrappedHandler(
        mockRequest as Request,
        mockResponse as Response,
        mockNext
      );

      expect(asyncFunction).toHaveBeenCalledWith(
        mockRequest,
        mockResponse,
        mockNext
      );
      expect(mockNext).not.toHaveBeenCalled();
    });
  });

  describe('notFoundHandler', () => {
    it('should return 404 for undefined routes', () => {
      mockRequest = {
        originalUrl: '/api/nonexistent-route'
      };

      notFoundHandler(
        mockRequest as Request,
        mockResponse as Response
      );

      expect(mockResponse.status).toHaveBeenCalledWith(404);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'NOT_FOUND',
          message: 'Route /api/nonexistent-route not found',
          timestamp: expect.any(String)
        }
      });
    });
  });
});