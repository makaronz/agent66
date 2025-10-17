import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { config } from '../config';
import { logger } from '../utils/logger';
import { AuthenticationError, AuthorizationError } from './errorHandler';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    username: string;
    role: string;
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

    // Get token from header
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new AuthenticationError('No token provided');
    }

    const token = authHeader.substring(7); // Remove 'Bearer ' prefix

    // Verify token
    const decoded = jwt.verify(token, config.jwt.secret) as any;

    // Add user info to request
    req.user = {
      id: decoded.id,
      email: decoded.email,
      username: decoded.username,
      role: decoded.role,
      iat: decoded.iat,
      exp: decoded.exp,
    };

    // Log successful authentication
    logger.debug('User authenticated', {
      userId: req.user.id,
      email: req.user.email,
      ip: req.ip,
    });

    next();
  } catch (error) {
    if (error instanceof jwt.JsonWebTokenError) {
      logger.security('Invalid token used', undefined, req.ip, { error: error.message });
      throw new AuthenticationError('Invalid token');
    } else if (error instanceof jwt.TokenExpiredError) {
      logger.security('Expired token used', undefined, req.ip, { error: error.message });
      throw new AuthenticationError('Token expired');
    } else {
      logger.security('Authentication error', undefined, req.ip, { error: error.message });
      throw new AuthenticationError('Authentication failed');
    }
  }
};

export const requireRole = (roles: string | string[]) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      throw new AuthenticationError('User not authenticated');
    }

    const allowedRoles = Array.isArray(roles) ? roles : [roles];
    if (!allowedRoles.includes(req.user.role)) {
      logger.security('Access denied - insufficient role', req.user.id, req.ip, {
        userRole: req.user.role,
        requiredRoles: allowedRoles,
      });
      throw new AuthorizationError('Insufficient permissions');
    }

    next();
  };
};

export const optionalAuth = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    // Get token from header
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return next(); // No token, continue without authentication
    }

    const token = authHeader.substring(7); // Remove 'Bearer ' prefix

    // Verify token
    const decoded = jwt.verify(token, config.jwt.secret) as any;

    // Add user info to request
    req.user = {
      id: decoded.id,
      email: decoded.email,
      username: decoded.username,
      role: decoded.role,
      iat: decoded.iat,
      exp: decoded.exp,
    };

    next();
  } catch (error) {
    // Log error but don't block request
    logger.debug('Optional authentication failed', { error: error.message });
    next();
  }
};

// Rate limiting middleware for authenticated users
export const authenticatedRateLimit = (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void => {
  // Add user-specific rate limiting logic here
  // For now, just pass through to the main rate limiter
  next();
};

// Legacy authGuard for backward compatibility
export const authGuard = authMiddleware;

export default authMiddleware;