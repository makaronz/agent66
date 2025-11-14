import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import {
  authMiddleware,
  requireRole,
  optionalAuth,
  authenticatedRateLimit,
  AuthenticatedRequest
} from '../../middleware/auth';
import { AuthenticationError, AuthorizationError } from '../../middleware/errorHandler';

// Mock dependencies
jest.mock('jsonwebtoken');
jest.mock('../../utils/logger', () => ({
  logger: {
    debug: jest.fn(),
    security: jest.fn(),
  }
}));

jest.mock('../../config/env-validation', () => ({
  config: {
    jwt: {
      secret: 'test-secret'
    }
  }
}));

describe('Authentication Middleware', () => {
  let mockRequest: Partial<AuthenticatedRequest>;
  let mockResponse: Partial<Response>;
  let mockNext: NextFunction;

  beforeEach(() => {
    mockRequest = {
      path: '/api/test',
      headers: {},
      ip: '127.0.0.1'
    };
    mockResponse = {};
    mockNext = jest.fn();
  });

  describe('authMiddleware', () => {
    it('should skip authentication for health check endpoints', async () => {
      mockRequest.path = '/health';

      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
      expect(mockNext).toHaveBeenCalledTimes(1);
    });

    it('should skip authentication for metrics endpoints', async () => {
      mockRequest.path = '/metrics';

      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should return AuthenticationError when no authorization header is provided', async () => {
      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith(
        expect.any(AuthenticationError)
      );
      expect(mockNext).toHaveBeenCalledTimes(1);
    });

    it('should return AuthenticationError when authorization header does not start with Bearer', async () => {
      mockRequest.headers = {
        authorization: 'Invalid token'
      };

      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith(
        expect.any(AuthenticationError)
      );
    });

    it('should successfully authenticate with valid token', async () => {
      const mockPayload = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        role: 'CREW',
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 3600
      };

      mockRequest.headers = {
        authorization: 'Bearer valid-token'
      };

      (jwt.verify as jest.Mock).mockReturnValue(mockPayload);

      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockRequest.user).toEqual(mockPayload);
      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should handle JsonWebTokenError and return AuthenticationError', async () => {
      mockRequest.headers = {
        authorization: 'Bearer invalid-token'
      };

      (jwt.verify as jest.Mock).mockImplementation(() => {
        throw new jwt.JsonWebTokenError('Invalid token');
      });

      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith(
        expect.any(AuthenticationError)
      );
    });

    it('should handle TokenExpiredError and return AuthenticationError', async () => {
      mockRequest.headers = {
        authorization: 'Bearer expired-token'
      };

      (jwt.verify as jest.Mock).mockImplementation(() => {
        throw new jwt.TokenExpiredError('Token expired', new Date());
      });

      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith(
        expect.any(AuthenticationError)
      );
    });

    it('should log successful authentication', async () => {
      const mockPayload = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        role: 'CREW'
      };

      mockRequest.headers = {
        authorization: 'Bearer valid-token'
      };

      (jwt.verify as jest.Mock).mockReturnValue(mockPayload);

      const { logger } = require('../../utils/logger');

      await authMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(logger.debug).toHaveBeenCalledWith('User authenticated', {
        userId: 'user123',
        email: 'test@example.com',
        ip: '127.0.0.1'
      });
    });
  });

  describe('requireRole', () => {
    it('should allow access when user has required role', () => {
      const roleMiddleware = requireRole(['ADMIN', 'SUPERVISOR']);
      mockRequest.user = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        role: 'ADMIN',
        iat: 1234567890,
        exp: 1234567890 + 3600
      };

      roleMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should allow access when user has one of multiple required roles', () => {
      const roleMiddleware = requireRole(['ADMIN', 'SUPERVISOR']);
      mockRequest.user = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        role: 'SUPERVISOR',
        iat: 1234567890,
        exp: 1234567890 + 3600
      };

      roleMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should allow access when user has required single role', () => {
      const roleMiddleware = requireRole('ADMIN');
      mockRequest.user = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        role: 'ADMIN',
        iat: 1234567890,
        exp: 1234567890 + 3600
      };

      roleMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should return AuthorizationError when user is not authenticated', () => {
      const roleMiddleware = requireRole('ADMIN');

      roleMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith(
        expect.any(AuthorizationError)
      );
    });

    it('should return AuthorizationError when user lacks required role', () => {
      const roleMiddleware = requireRole('ADMIN');
      mockRequest.user = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        role: 'CREW',
        iat: 1234567890,
        exp: 1234567890 + 3600
      };

      const { logger } = require('../../utils/logger');

      roleMiddleware(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith(
        expect.any(AuthorizationError)
      );
      expect(logger.security).toHaveBeenCalledWith(
        'Access denied - insufficient role',
        'user123',
        '127.0.0.1',
        expect.objectContaining({
          userRole: 'CREW',
          requiredRoles: ['ADMIN']
        })
      );
    });
  });

  describe('optionalAuth', () => {
    it('should continue without authentication when no token provided', async () => {
      await optionalAuth(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
      expect(mockRequest.user).toBeUndefined();
    });

    it('should authenticate when valid token provided', async () => {
      const mockPayload = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        role: 'CREW'
      };

      mockRequest.headers = {
        authorization: 'Bearer valid-token'
      };

      (jwt.verify as jest.Mock).mockReturnValue(mockPayload);

      await optionalAuth(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockRequest.user).toEqual(mockPayload);
      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should continue without authentication when token is invalid', async () => {
      mockRequest.headers = {
        authorization: 'Bearer invalid-token'
      };

      (jwt.verify as jest.Mock).mockImplementation(() => {
        throw new jwt.JsonWebTokenError('Invalid token');
      });

      const { logger } = require('../../utils/logger');

      await optionalAuth(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
      expect(mockRequest.user).toBeUndefined();
      expect(logger.debug).toHaveBeenCalledWith(
        'Optional authentication failed',
        expect.objectContaining({ error: expect.any(String) })
      );
    });
  });

  describe('authenticatedRateLimit', () => {
    it('should pass through to next middleware', () => {
      authenticatedRateLimit(
        mockRequest as AuthenticatedRequest,
        mockResponse as Response,
        mockNext
      );

      expect(mockNext).toHaveBeenCalledWith();
    });
  });
});