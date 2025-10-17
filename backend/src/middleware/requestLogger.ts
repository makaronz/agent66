import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';

export const requestLogger = (req: Request, res: Response, next: NextFunction): void => {
  const startTime = Date.now();

  // Store start time on request for later use
  (req as any).startTime = startTime;

  // Log request
  logger.debug(`${req.method} ${req.url}`, {
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    contentType: req.get('Content-Type'),
    contentLength: req.get('Content-Length'),
  });

  // Override res.end to log response
  const originalEnd = res.end;
  res.end = function (chunk?: any, encoding?: any) {
    const endTime = Date.now();
    const responseTime = endTime - startTime;

    // Log response
    logger.http(req.method, req.url, res.statusCode, responseTime, req.get('User-Agent'));

    // Call original end
    originalEnd.call(this, chunk, encoding);
  };

  next();
};