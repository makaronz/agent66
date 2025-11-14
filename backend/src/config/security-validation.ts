/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Security Configuration Validation
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE: Comprehensive security configuration validation
 * VALIDATES: Secret strength, environment security, SSL requirements
 * COMPLIANCE: OWASP security standards, industry best practices
 */

import { z } from 'zod';
import crypto from 'crypto';
import { logger } from '../utils/logger';

/**
 * Security configuration schema with validation
 */
export const securityConfigSchema = z.object({
  // JWT Configuration
  jwt: z.object({
    secret: z.string()
      .min(32, 'JWT secret must be at least 32 characters')
      .refine(val =>
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/.test(val),
        'JWT secret must contain uppercase, lowercase, numbers, and special characters'
      ),
    accessSecret: z.string().min(32),
    refreshSecret: z.string().min(32),
    expiration: z.number().min(300).max(3600), // 5min to 1hr
    refreshExpiration: z.number().min(86400).max(604800), // 1day to 7days
  }),

  // Encryption Configuration
  encryption: z.object({
    key: z.string()
      .length(32, 'Encryption key must be exactly 32 characters')
      .refine(val => /^[A-Za-z0-9+/=]+$/.test(val), 'Encryption key must be base64 encoded'),
    algorithm: z.string().default('AES-256-GCM'),
  }),

  // Session Configuration
  session: z.object({
    secret: z.string()
      .min(32, 'Session secret must be at least 32 characters')
      .refine(val =>
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/.test(val),
        'Session secret must contain uppercase, lowercase, numbers, and special characters'
      ),
    timeout: z.number().min(300000).max(3600000), // 5min to 1hr
  }),

  // Database Security
  database: z.object({
    ssl: z.boolean(),
    sslCert: z.string().optional(),
    sslKey: z.string().optional(),
    sslCA: z.string().optional(),
  }),

  // CORS Security
  cors: z.object({
    origin: z.union([
      z.string(),
      z.array(z.string()),
      z.boolean(),
    ]).default(false),
    credentials: z.boolean().default(false),
    maxAge: z.number().default(86400), // 24 hours
  }),

  // Rate Limiting
  rateLimit: z.object({
    windowMs: z.number().min(60000), // 1 minute minimum
    max: z.number().min(1).max(1000),
    skipSuccessfulRequests: z.boolean().default(false),
    skipFailedRequests: z.boolean().default(false),
  }),

  // SSL/TLS Configuration
  ssl: z.object({
    enabled: z.boolean(),
    certPath: z.string().optional(),
    keyPath: z.string().optional(),
    caPath: z.string().optional(),
    minVersion: z.string().default('TLSv1.2'),
  }),

  // Security Headers
  security: z.object({
    helmet: z.object({
      enabled: z.boolean().default(true),
      contentSecurityPolicy: z.object({
        directives: z.record(z.array(z.string())).optional(),
      }).optional(),
    }),
    hsts: z.object({
      enabled: z.boolean().default(true),
      maxAge: z.number().default(31536000),
      includeSubDomains: z.boolean().default(true),
      preload: z.boolean().default(true),
    }),
  }),

  // Password Security
  password: z.object({
    bcryptRounds: z.number().min(10).max(15).default(12),
    minLength: z.number().min(8).max(128).default(12),
    requireUppercase: z.boolean().default(true),
    requireLowercase: z.boolean().default(true),
    requireNumbers: z.boolean().default(true),
    requireSpecialChars: z.boolean().default(true),
  }),

  // API Security
  api: z.object({
    keyRotationInterval: z.number().min(86400).default(2592000), // 30 days
    maxRequestSize: z.number().min(1024).max(10485760).default(10485760), // 10MB
    timeout: z.number().min(5000).max(60000).default(30000), // 30 seconds
  }),

  // Monitoring and Logging
  monitoring: z.object({
    securityLogs: z.boolean().default(true),
    auditLogs: z.boolean().default(true),
    logLevel: z.enum(['error', 'warn', 'info', 'debug']).default('warn'),
    maxLogSize: z.string().default('10m'),
    logRetentionDays: z.number().min(1).max(365).default(30),
  }),
});

/**
 * Environment-specific security requirements
 */
const environmentSecurityRequirements = {
  development: {
    sslRequired: false,
    strictCORS: false,
    debugMode: true,
    auditLogging: false,
  },
  staging: {
    sslRequired: true,
    strictCORS: true,
    debugMode: false,
    auditLogging: true,
  },
  production: {
    sslRequired: true,
    strictCORS: true,
    debugMode: false,
    auditLogging: true,
  },
};

/**
 * Validate security configuration against requirements
 */
export function validateSecurityConfig(
  config: unknown,
  environment: string = 'development'
): { valid: boolean; errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];

  try {
    // Parse and validate configuration
    const parsedConfig = securityConfigSchema.parse(config);
    const requirements = environmentSecurityRequirements[environment as keyof typeof environmentSecurityRequirements];

    // SSL validation
    if (requirements.sslRequired && !parsedConfig.ssl.enabled) {
      errors.push('SSL/TLS is required in production environment');
    }

    // CORS validation
    if (requirements.strictCORS && parsedConfig.cors.origin === true) {
      errors.push('CORS must be specifically configured in production');
    }

    // Debug mode validation
    if (!requirements.debugMode && process.env.NODE_ENV === 'development') {
      warnings.push('Debug mode should be disabled in production');
    }

    // Secret strength validation
    validateSecretStrength(parsedConfig, errors, warnings);

    // Database security validation
    validateDatabaseSecurity(parsedConfig, errors, warnings);

    // Rate limiting validation
    validateRateLimiting(parsedConfig, errors, warnings);

    // Password policy validation
    validatePasswordPolicy(parsedConfig, errors, warnings);

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };

  } catch (error) {
    if (error instanceof z.ZodError) {
      errors.push(...error.errors.map(e => `${e.path.join('.')}: ${e.message}`));
    } else {
      errors.push('Invalid security configuration format');
    }

    return {
      valid: false,
      errors,
      warnings,
    };
  }
}

/**
 * Validate secret strength and entropy
 */
function validateSecretStrength(
  config: z.infer<typeof securityConfigSchema>,
  errors: string[],
  warnings: string[]
): void {
  const secrets = [
    { name: 'JWT Secret', value: config.jwt.secret },
    { name: 'JWT Access Secret', value: config.jwt.accessSecret },
    { name: 'JWT Refresh Secret', value: config.jwt.refreshSecret },
    { name: 'Session Secret', value: config.session.secret },
    { name: 'Encryption Key', value: config.encryption.key },
  ];

  for (const secret of secrets) {
    // Check for default/placeholder values
    if (secret.value.includes('CHANGE_ME') || secret.value.includes('your_')) {
      errors.push(`${secret.name} appears to be a placeholder value`);
    }

    // Calculate entropy
    const entropy = calculateEntropy(secret.value);
    if (entropy < 3.0) {
      warnings.push(`${secret.name} has low entropy (${entropy.toFixed(2)})`);
    }

    // Check for common patterns
    if (/password|secret|key/i.test(secret.value) && secret.value.length < 40) {
      warnings.push(`${secret.name} contains common words and may be weak`);
    }
  }
}

/**
 * Validate database security configuration
 */
function validateDatabaseSecurity(
  config: z.infer<typeof securityConfigSchema>,
  errors: string[],
  warnings: string[]
): void {
  if (process.env.NODE_ENV === 'production' && !config.database.ssl) {
    errors.push('Database SSL/TLS is required in production');
  }

  // Check for database URL in environment
  const databaseUrl = process.env.DATABASE_URL;
  if (databaseUrl) {
    // Check for credentials in URL (should use environment variables)
    if (databaseUrl.includes('postgres://postgres:postgres@')) {
      errors.push('Database contains default credentials');
    }

    // Check for SSL parameters
    if (!databaseUrl.includes('sslmode=')) {
      warnings.push('Database connection string should specify SSL mode');
    }
  }
}

/**
 * Validate rate limiting configuration
 */
function validateRateLimiting(
  config: z.infer<typeof securityConfigSchema>,
  errors: string[],
  warnings: string[]
): void {
  if (config.rateLimit.max > 1000) {
    warnings.push('High rate limit may be vulnerable to DoS attacks');
  }

  if (config.rateLimit.windowMs > 900000) { // 15 minutes
    warnings.push('Long rate limit window may allow sustained attacks');
  }
}

/**
 * Validate password policy
 */
function validatePasswordPolicy(
  config: z.infer<typeof securityConfigSchema>,
  errors: string[],
  warnings: string[]
): void {
  if (config.password.bcryptRounds < 12) {
    warnings.push('BCrypt rounds should be at least 12 for production');
  }

  if (config.password.minLength < 12) {
    warnings.push('Minimum password length should be at least 12 characters');
  }
}

/**
 * Calculate Shannon entropy of a string
 */
function calculateEntropy(str: string): number {
  const freq: { [key: string]: number } = {};
  let entropy = 0;

  // Calculate frequency of each character
  for (const char of str) {
    freq[char] = (freq[char] || 0) + 1;
  }

  // Calculate Shannon entropy
  for (const count of Object.values(freq)) {
    const probability = count / str.length;
    entropy -= probability * Math.log2(probability);
  }

  return entropy;
}

/**
 * Generate secure secrets
 */
export function generateSecureSecret(length: number = 32): string {
  return crypto.randomBytes(length).toString('base64').slice(0, length);
}

/**
 * Generate JWT secrets
 */
export function generateJWTSecrets() {
  return {
    secret: generateSecureSecret(32),
    accessSecret: generateSecureSecret(32),
    refreshSecret: generateSecureSecret(32),
  };
}

/**
 * Generate encryption key
 */
export function generateEncryptionKey(): string {
  return crypto.randomBytes(32).toString('base64');
}

/**
 * Check if environment is secure
 */
export function checkEnvironmentSecurity(): { secure: boolean; issues: string[] } {
  const issues: string[] = [];

  // Check Node.js version
  const nodeVersion = process.version;
  const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
  if (majorVersion < 18) {
    issues.push(`Node.js version ${nodeVersion} is outdated, upgrade to v18+`);
  }

  // Check for development mode in production
  if (process.env.NODE_ENV === 'production' && process.env.DEBUG) {
    issues.push('Debug mode should not be enabled in production');
  }

  // Check for insecure defaults
  if (process.env.JWT_SECRET === 'secret') {
    issues.push('JWT secret is using insecure default');
  }

  if (process.env.DATABASE_URL && process.env.DATABASE_URL.includes('localhost')) {
    issues.push('Production database should not be localhost');
  }

  return {
    secure: issues.length === 0,
    issues,
  };
}

/**
 * Security configuration validator
 */
export const validateSecurityConfiguration = (config: any) => {
  const result = validateSecurityConfig(config, config.app?.environment || 'development');

  // Log validation results
  if (!result.valid) {
    logger.error('Security configuration validation failed', { errors: result.errors });
  }

  if (result.warnings.length > 0) {
    logger.warn('Security configuration warnings', { warnings: result.warnings });
  }

  return result;
};