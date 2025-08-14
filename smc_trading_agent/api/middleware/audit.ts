/**
 * Comprehensive audit logging system
 * Tracks all security-relevant events and user actions
 */

import { Request, Response, NextFunction } from 'express';
import { createHash } from 'crypto';
import fs from 'fs/promises';
import path from 'path';

// Audit event types
export enum AuditEventType {
  // Authentication events
  LOGIN_SUCCESS = 'LOGIN_SUCCESS',
  LOGIN_FAILURE = 'LOGIN_FAILURE',
  LOGOUT = 'LOGOUT',
  PASSWORD_CHANGE = 'PASSWORD_CHANGE',
  PASSWORD_RESET_REQUEST = 'PASSWORD_RESET_REQUEST',
  PASSWORD_RESET_SUCCESS = 'PASSWORD_RESET_SUCCESS',
  
  // MFA events
  MFA_SETUP = 'MFA_SETUP',
  MFA_VERIFY_SUCCESS = 'MFA_VERIFY_SUCCESS',
  MFA_VERIFY_FAILURE = 'MFA_VERIFY_FAILURE',
  MFA_DISABLE = 'MFA_DISABLE',
  
  // API key events
  API_KEY_CREATE = 'API_KEY_CREATE',
  API_KEY_UPDATE = 'API_KEY_UPDATE',
  API_KEY_DELETE = 'API_KEY_DELETE',
  API_KEY_VIEW = 'API_KEY_VIEW',
  
  // Trading events
  ORDER_PLACE = 'ORDER_PLACE',
  ORDER_CANCEL = 'ORDER_CANCEL',
  ORDER_MODIFY = 'ORDER_MODIFY',
  BALANCE_VIEW = 'BALANCE_VIEW',
  
  // Configuration events
  CONFIG_CREATE = 'CONFIG_CREATE',
  CONFIG_UPDATE = 'CONFIG_UPDATE',
  CONFIG_DELETE = 'CONFIG_DELETE',
  CONFIG_VIEW = 'CONFIG_VIEW',
  
  // Security events
  UNAUTHORIZED_ACCESS = 'UNAUTHORIZED_ACCESS',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  SUSPICIOUS_ACTIVITY = 'SUSPICIOUS_ACTIVITY',
  DATA_EXPORT = 'DATA_EXPORT',
  DATA_DELETE = 'DATA_DELETE',
  
  // System events
  SYSTEM_ERROR = 'SYSTEM_ERROR',
  SYSTEM_WARNING = 'SYSTEM_WARNING',
  MAINTENANCE_START = 'MAINTENANCE_START',
  MAINTENANCE_END = 'MAINTENANCE_END'
}

// Audit log entry interface
export interface AuditLogEntry {
  id: string;
  timestamp: string;
  event_type: AuditEventType;
  user_id?: string;
  user_email?: string;
  ip_address: string;
  user_agent: string;
  endpoint: string;
  method: string;
  status_code?: number;
  resource_id?: string;
  resource_type?: string;
  details: Record<string, any>;
  risk_score: number;
  session_id?: string;
  request_id: string;
  geolocation?: {
    country?: string;
    city?: string;
    latitude?: number;
    longitude?: number;
  };
}

// Risk scoring for events
const RISK_SCORES: Record<AuditEventType, number> = {
  [AuditEventType.LOGIN_SUCCESS]: 1,
  [AuditEventType.LOGIN_FAILURE]: 5,
  [AuditEventType.LOGOUT]: 1,
  [AuditEventType.PASSWORD_CHANGE]: 3,
  [AuditEventType.PASSWORD_RESET_REQUEST]: 4,
  [AuditEventType.PASSWORD_RESET_SUCCESS]: 5,
  
  [AuditEventType.MFA_SETUP]: 3,
  [AuditEventType.MFA_VERIFY_SUCCESS]: 1,
  [AuditEventType.MFA_VERIFY_FAILURE]: 6,
  [AuditEventType.MFA_DISABLE]: 7,
  
  [AuditEventType.API_KEY_CREATE]: 6,
  [AuditEventType.API_KEY_UPDATE]: 5,
  [AuditEventType.API_KEY_DELETE]: 7,
  [AuditEventType.API_KEY_VIEW]: 2,
  
  [AuditEventType.ORDER_PLACE]: 4,
  [AuditEventType.ORDER_CANCEL]: 3,
  [AuditEventType.ORDER_MODIFY]: 4,
  [AuditEventType.BALANCE_VIEW]: 2,
  
  [AuditEventType.CONFIG_CREATE]: 3,
  [AuditEventType.CONFIG_UPDATE]: 3,
  [AuditEventType.CONFIG_DELETE]: 5,
  [AuditEventType.CONFIG_VIEW]: 1,
  
  [AuditEventType.UNAUTHORIZED_ACCESS]: 9,
  [AuditEventType.RATE_LIMIT_EXCEEDED]: 6,
  [AuditEventType.SUSPICIOUS_ACTIVITY]: 8,
  [AuditEventType.DATA_EXPORT]: 5,
  [AuditEventType.DATA_DELETE]: 8,
  
  [AuditEventType.SYSTEM_ERROR]: 4,
  [AuditEventType.SYSTEM_WARNING]: 2,
  [AuditEventType.MAINTENANCE_START]: 1,
  [AuditEventType.MAINTENANCE_END]: 1
};

// Audit logger class
class AuditLogger {
  private logDirectory: string;
  private maxLogSize: number;
  private retentionDays: number;

  constructor() {
    this.logDirectory = process.env.AUDIT_LOG_DIR || './logs/audit';
    this.maxLogSize = parseInt(process.env.MAX_LOG_SIZE || '100') * 1024 * 1024; // 100MB default
    this.retentionDays = parseInt(process.env.LOG_RETENTION_DAYS || '2555'); // 7 years default
    this.ensureLogDirectory();
  }

  private async ensureLogDirectory(): Promise<void> {
    try {
      await fs.mkdir(this.logDirectory, { recursive: true });
    } catch (error) {
      console.error('Failed to create audit log directory:', error);
    }
  }

  private generateRequestId(): string {
    return createHash('sha256')
      .update(`${Date.now()}-${Math.random()}`)
      .digest('hex')
      .substring(0, 16);
  }

  private getLogFileName(): string {
    const date = new Date().toISOString().split('T')[0];
    return path.join(this.logDirectory, `audit-${date}.jsonl`);
  }

  private sanitizeForLogging(data: any): any {
    if (typeof data !== 'object' || data === null) {
      return data;
    }

    const sensitiveFields = [
      'password', 'secret', 'token', 'key', 'authorization',
      'api_key', 'api_secret', 'private_key', 'access_token',
      'refresh_token', 'session_token', 'csrf_token'
    ];

    const sanitized = { ...data };
    
    for (const [key, value] of Object.entries(sanitized)) {
      const lowerKey = key.toLowerCase();
      
      if (sensitiveFields.some(field => lowerKey.includes(field))) {
        sanitized[key] = '[REDACTED]';
      } else if (typeof value === 'object' && value !== null) {
        sanitized[key] = this.sanitizeForLogging(value);
      }
    }

    return sanitized;
  }

  async logEvent(
    eventType: AuditEventType,
    req: Request,
    details: Record<string, any> = {},
    statusCode?: number,
    resourceId?: string,
    resourceType?: string
  ): Promise<void> {
    try {
      const entry: AuditLogEntry = {
        id: this.generateRequestId(),
        timestamp: new Date().toISOString(),
        event_type: eventType,
        user_id: req.user?.id,
        user_email: req.user?.email,
        ip_address: this.getClientIP(req),
        user_agent: req.get('User-Agent') || 'Unknown',
        endpoint: req.originalUrl || req.url,
        method: req.method,
        status_code: statusCode,
        resource_id: resourceId,
        resource_type: resourceType,
        details: this.sanitizeForLogging(details),
        risk_score: RISK_SCORES[eventType] || 5,
        session_id: req.sessionID,
        request_id: req.headers['x-request-id'] as string || this.generateRequestId(),
        geolocation: await this.getGeolocation(this.getClientIP(req))
      };

      await this.writeLogEntry(entry);
      
      // Alert on high-risk events
      if (entry.risk_score >= 7) {
        await this.sendSecurityAlert(entry);
      }

    } catch (error) {
      console.error('Failed to write audit log:', error);
      // Don't throw - logging failures shouldn't break the application
    }
  }

  private getClientIP(req: Request): string {
    return (
      req.headers['x-forwarded-for'] as string ||
      req.headers['x-real-ip'] as string ||
      req.connection.remoteAddress ||
      req.socket.remoteAddress ||
      'unknown'
    ).split(',')[0].trim();
  }

  private async getGeolocation(ip: string): Promise<AuditLogEntry['geolocation']> {
    // In production, integrate with a geolocation service like MaxMind
    // For now, return undefined to avoid external dependencies
    return undefined;
  }

  private async writeLogEntry(entry: AuditLogEntry): Promise<void> {
    const logFile = this.getLogFileName();
    const logLine = JSON.stringify(entry) + '\n';

    try {
      // Check file size and rotate if necessary
      try {
        const stats = await fs.stat(logFile);
        if (stats.size > this.maxLogSize) {
          await this.rotateLogFile(logFile);
        }
      } catch (error) {
        // File doesn't exist yet, which is fine
      }

      await fs.appendFile(logFile, logLine, 'utf8');
    } catch (error) {
      console.error('Failed to write audit log entry:', error);
    }
  }

  private async rotateLogFile(logFile: string): Promise<void> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const rotatedFile = logFile.replace('.jsonl', `-${timestamp}.jsonl`);
    
    try {
      await fs.rename(logFile, rotatedFile);
    } catch (error) {
      console.error('Failed to rotate log file:', error);
    }
  }

  private async sendSecurityAlert(entry: AuditLogEntry): Promise<void> {
    // In production, integrate with alerting systems like Slack, PagerDuty, etc.
    console.warn('🚨 HIGH RISK SECURITY EVENT:', {
      event_type: entry.event_type,
      user_email: entry.user_email,
      ip_address: entry.ip_address,
      risk_score: entry.risk_score,
      timestamp: entry.timestamp
    });

    // TODO: Implement actual alerting
    // - Send to Slack webhook
    // - Send to PagerDuty
    // - Send email to security team
    // - Store in security incident database
  }

  async cleanupOldLogs(): Promise<void> {
    try {
      const files = await fs.readdir(this.logDirectory);
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - this.retentionDays);

      for (const file of files) {
        if (file.startsWith('audit-') && file.endsWith('.jsonl')) {
          const filePath = path.join(this.logDirectory, file);
          const stats = await fs.stat(filePath);
          
          if (stats.mtime < cutoffDate) {
            await fs.unlink(filePath);
            console.log(`Deleted old audit log: ${file}`);
          }
        }
      }
    } catch (error) {
      console.error('Failed to cleanup old audit logs:', error);
    }
  }

  async searchLogs(
    startDate: Date,
    endDate: Date,
    eventTypes?: AuditEventType[],
    userId?: string,
    ipAddress?: string
  ): Promise<AuditLogEntry[]> {
    const results: AuditLogEntry[] = [];
    
    try {
      const files = await fs.readdir(this.logDirectory);
      
      for (const file of files) {
        if (file.startsWith('audit-') && file.endsWith('.jsonl')) {
          const filePath = path.join(this.logDirectory, file);
          const content = await fs.readFile(filePath, 'utf8');
          const lines = content.split('\n').filter(line => line.trim());
          
          for (const line of lines) {
            try {
              const entry: AuditLogEntry = JSON.parse(line);
              const entryDate = new Date(entry.timestamp);
              
              // Date filter
              if (entryDate < startDate || entryDate > endDate) {
                continue;
              }
              
              // Event type filter
              if (eventTypes && !eventTypes.includes(entry.event_type)) {
                continue;
              }
              
              // User ID filter
              if (userId && entry.user_id !== userId) {
                continue;
              }
              
              // IP address filter
              if (ipAddress && entry.ip_address !== ipAddress) {
                continue;
              }
              
              results.push(entry);
            } catch (parseError) {
              console.error('Failed to parse audit log line:', parseError);
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to search audit logs:', error);
    }
    
    return results.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }
}

// Global audit logger instance
export const auditLogger = new AuditLogger();

// Audit middleware
export const auditMiddleware = (eventType: AuditEventType, options: {
  resourceType?: string;
  captureBody?: boolean;
  captureResponse?: boolean;
} = {}) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    const originalSend = res.send;
    let responseBody: any;

    // Capture response if requested
    if (options.captureResponse) {
      res.send = function(body: any) {
        responseBody = body;
        return originalSend.call(this, body);
      };
    }

    // Continue with request processing
    res.on('finish', async () => {
      const details: Record<string, any> = {};
      
      if (options.captureBody && req.body) {
        details.request_body = req.body;
      }
      
      if (options.captureResponse && responseBody) {
        details.response_body = responseBody;
      }
      
      if (req.params && Object.keys(req.params).length > 0) {
        details.params = req.params;
      }
      
      if (req.query && Object.keys(req.query).length > 0) {
        details.query = req.query;
      }

      await auditLogger.logEvent(
        eventType,
        req,
        details,
        res.statusCode,
        req.params.id || req.body?.id,
        options.resourceType
      );
    });

    next();
  };
};

// Convenience functions for common audit events
export const auditAuth = {
  loginSuccess: (req: Request) => auditLogger.logEvent(AuditEventType.LOGIN_SUCCESS, req),
  loginFailure: (req: Request, reason: string) => auditLogger.logEvent(
    AuditEventType.LOGIN_FAILURE, 
    req, 
    { failure_reason: reason }
  ),
  logout: (req: Request) => auditLogger.logEvent(AuditEventType.LOGOUT, req),
  passwordChange: (req: Request) => auditLogger.logEvent(AuditEventType.PASSWORD_CHANGE, req),
  mfaSetup: (req: Request, method: string) => auditLogger.logEvent(
    AuditEventType.MFA_SETUP, 
    req, 
    { mfa_method: method }
  ),
  mfaVerifySuccess: (req: Request, method: string) => auditLogger.logEvent(
    AuditEventType.MFA_VERIFY_SUCCESS, 
    req, 
    { mfa_method: method }
  ),
  mfaVerifyFailure: (req: Request, method: string, reason: string) => auditLogger.logEvent(
    AuditEventType.MFA_VERIFY_FAILURE, 
    req, 
    { mfa_method: method, failure_reason: reason }
  )
};

export const auditTrading = {
  orderPlace: (req: Request, orderData: any) => auditLogger.logEvent(
    AuditEventType.ORDER_PLACE,
    req,
    { order_data: orderData },
    undefined,
    orderData.id,
    'order'
  ),
  orderCancel: (req: Request, orderId: string) => auditLogger.logEvent(
    AuditEventType.ORDER_CANCEL,
    req,
    {},
    undefined,
    orderId,
    'order'
  ),
  balanceView: (req: Request, exchange: string) => auditLogger.logEvent(
    AuditEventType.BALANCE_VIEW,
    req,
    { exchange }
  )
};

export const auditSecurity = {
  unauthorizedAccess: (req: Request, reason: string) => auditLogger.logEvent(
    AuditEventType.UNAUTHORIZED_ACCESS,
    req,
    { reason }
  ),
  rateLimitExceeded: (req: Request, limit: number) => auditLogger.logEvent(
    AuditEventType.RATE_LIMIT_EXCEEDED,
    req,
    { rate_limit: limit }
  ),
  suspiciousActivity: (req: Request, activity: string, details: any) => auditLogger.logEvent(
    AuditEventType.SUSPICIOUS_ACTIVITY,
    req,
    { activity, ...details }
  )
};

// Schedule log cleanup (run daily)
setInterval(() => {
  auditLogger.cleanupOldLogs();
}, 24 * 60 * 60 * 1000); // 24 hours