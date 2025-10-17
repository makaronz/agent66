import { config } from '../config';

export enum LogLevel {
  ERROR = 0,
  WARN = 1,
  INFO = 2,
  DEBUG = 3,
}

class Logger {
  private level: LogLevel;

  constructor() {
    this.level = this.getLogLevel(config.logging.level);
  }

  private getLogLevel(level: string): LogLevel {
    switch (level.toLowerCase()) {
      case 'error': return LogLevel.ERROR;
      case 'warn': return LogLevel.WARN;
      case 'info': return LogLevel.INFO;
      case 'debug': return LogLevel.DEBUG;
      default: return LogLevel.INFO;
    }
  }

  private formatMessage(level: string, message: string, ...args: any[]): string {
    const timestamp = new Date().toISOString();
    const formattedArgs = args.length > 0 ? ' ' + args.map(arg =>
      typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
    ).join(' ') : '';

    return `[${timestamp}] [${level}] ${message}${formattedArgs}`;
  }

  private log(level: LogLevel, levelName: string, message: string, ...args: any[]): void {
    if (level <= this.level) {
      const formattedMessage = this.formatMessage(levelName, message, ...args);

      if (config.logging.colorize && process.stdout.isTTY) {
        const colors = {
          ERROR: '\x1b[31m', // Red
          WARN: '\x1b[33m',  // Yellow
          INFO: '\x1b[36m',  // Cyan
          DEBUG: '\x1b[37m', // White
          RESET: '\x1b[0m',
        };
        console.log(`${colors[levelName]}${formattedMessage}${colors.RESET}`);
      } else {
        console.log(formattedMessage);
      }
    }
  }

  error(message: string, ...args: any[]): void {
    this.log(LogLevel.ERROR, 'ERROR', message, ...args);
  }

  warn(message: string, ...args: any[]): void {
    this.log(LogLevel.WARN, 'WARN', message, ...args);
  }

  info(message: string, ...args: any[]): void {
    this.log(LogLevel.INFO, 'INFO', message, ...args);
  }

  debug(message: string, ...args: any[]): void {
    this.log(LogLevel.DEBUG, 'DEBUG', message, ...args);
  }

  // HTTP request logging
  http(method: string, url: string, statusCode: number, responseTime: number, userAgent?: string): void {
    const message = `${method} ${url} ${statusCode} - ${responseTime}ms`;
    if (userAgent) {
      this.info(message, { userAgent });
    } else {
      this.info(message);
    }
  }

  // Database operation logging
  db(operation: string, table: string, duration: number, affected?: number): void {
    const message = `DB ${operation} on ${table} - ${duration}ms`;
    if (affected !== undefined) {
      this.info(message, { affected });
    } else {
      this.info(message);
    }
  }

  // Trading operation logging
  trading(operation: string, symbol: string, status: string, details?: any): void {
    const message = `Trading ${operation} - ${symbol} - ${status}`;
    if (details) {
      this.info(message, { details });
    } else {
      this.info(message);
    }
  }

  // Security event logging
  security(event: string, userId?: string, ip?: string, details?: any): void {
    const message = `Security: ${event}`;
    const context: any = {};

    if (userId) context.userId = userId;
    if (ip) context.ip = ip;
    if (details) context.details = details;

    if (Object.keys(context).length > 0) {
      this.warn(message, context);
    } else {
      this.warn(message);
    }
  }

  // Performance logging
  performance(operation: string, duration: number, memory?: number): void {
    const message = `Performance: ${operation} - ${duration}ms`;
    const context: any = {};

    if (memory) context.memory = `${(memory / 1024 / 1024).toFixed(2)}MB`;

    if (Object.keys(context).length > 0) {
      this.debug(message, context);
    } else {
      this.debug(message);
    }
  }
}

// Create singleton logger instance
export const logger = new Logger();

// Export convenience functions
export const logError = (message: string, ...args: any[]) => logger.error(message, ...args);
export const logWarn = (message: string, ...args: any[]) => logger.warn(message, ...args);
export const logInfo = (message: string, ...args: any[]) => logger.info(message, ...args);
export const logDebug = (message: string, ...args: any[]) => logger.debug(message, ...args);

export default logger;