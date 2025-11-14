import { z } from 'zod';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Environment validation schema
const envSchema = z.object({
  // Application Configuration
  NODE_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  PORT: z.coerce.number().default(5000),
  HOST: z.string().default('0.0.0.0'),
  APP_NAME: z.string().default('SMC_Trading_Agent'),
  APP_VERSION: z.string().default('1.0.0'),
  APP_DEBUG: z.coerce.boolean().default(false),

  // Security Configuration
  JWT_SECRET: z.string().min(32, 'JWT secret must be at least 32 characters'),
  JWT_ACCESS_SECRET: z.string().min(32, 'JWT access secret must be at least 32 characters'),
  JWT_REFRESH_SECRET: z.string().min(32, 'JWT refresh secret must be at least 32 characters'),
  JWT_EXPIRATION: z.coerce.number().default(3600),
  JWT_REFRESH_EXPIRATION: z.coerce.number().default(604800),
  ENCRYPTION_KEY: z.string().length(32, 'Encryption key must be exactly 32 characters'),
  BCRYPT_ROUNDS: z.coerce.number().min(10).max(15).default(12),
  SESSION_SECRET: z.string().min(32, 'Session secret must be at least 32 characters'),
  SESSION_TIMEOUT: z.coerce.number().default(3600000),

  // Database Configuration
  DATABASE_URL: z.string().url().optional(),
  DB_HOST: z.string().default('localhost'),
  DB_PORT: z.coerce.number().default(5432),
  DB_NAME: z.string().default('smc_trading'),
  DB_USER: z.string().default('postgres'),
  DB_PASSWORD: z.string().optional(),
  DB_SSL: z.coerce.boolean().default(false),
  DB_POOL_SIZE: z.coerce.number().default(10),

  // MongoDB Configuration
  MONGO_URI: z.string().url().optional(),
  MONGO_HOST: z.string().default('localhost'),
  MONGO_PORT: z.coerce.number().default(27017),
  MONGO_DB_NAME: z.string().default('smc_trading'),
  MONGO_USER: z.string().optional(),
  MONGO_PASSWORD: z.string().optional(),

  // Redis Configuration
  REDIS_URL: z.string().url().optional(),
  REDIS_HOST: z.string().default('localhost'),
  REDIS_PORT: z.coerce.number().default(6379),
  REDIS_DB: z.coerce.number().default(0),
  REDIS_PASSWORD: z.string().optional(),
  REDIS_MAX_CONNECTIONS: z.coerce.number().default(20),

  // Supabase Configuration
  SUPABASE_URL: z.string().url().optional(),
  SUPABASE_ANON_KEY: z.string().min(1, 'Supabase anonymous key is required').optional(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1, 'Supabase service role key is required').optional(),

  // Trading API Configuration
  BINANCE_API_KEY: z.string().optional(),
  BINANCE_API_SECRET: z.string().optional(),
  BINANCE_TESTNET: z.coerce.boolean().default(true),
  BYBIT_API_KEY: z.string().optional(),
  BYBIT_API_SECRET: z.string().optional(),
  BYBIT_TESTNET: z.coerce.boolean().default(true),
  OANDA_API_KEY: z.string().optional(),
  OANDA_ACCOUNT_ID: z.string().optional(),
  OANDA_ENVIRONMENT: z.enum(['practice', 'live']).default('practice'),

  // Trading Configuration
  TRADING_MODE: z.enum(['paper', 'live']).default('paper'),
  MAX_CONCURRENT_TRADES: z.coerce.number().default(3),
  DEFAULT_RISK_PERCENTAGE: z.coerce.number().default(1),
  DEFAULT_STOP_LOSS_PERCENTAGE: z.coerce.number().default(0.5),
  DEFAULT_TAKE_PROFIT_PERCENTAGE: z.coerce.number().default(2),

  // Security & Rate Limiting
  RATE_LIMIT_WINDOW_MS: z.coerce.number().default(900000),
  RATE_LIMIT_MAX_REQUESTS: z.coerce.number().default(100),
  HELMET_ENABLED: z.coerce.boolean().default(true),
  CORS_ENABLED: z.coerce.boolean().default(true),
  CORS_ORIGIN: z.string().default('http://localhost:5173'),
  CSRF_PROTECTION: z.coerce.boolean().default(true),
  DDOS_PROTECTION: z.coerce.boolean().default(true),
  DDOS_THRESHOLD: z.coerce.number().default(100),
  DDOS_WINDOW_MS: z.coerce.number().default(60000),

  // Logging & Monitoring
  LOG_LEVEL: z.enum(['error', 'warn', 'info', 'debug']).default('info'),
  LOG_FILE: z.string().default('logs/smc_trading.log'),
  PROMETHEUS_ENABLED: z.coerce.boolean().default(true),
  PROMETHEUS_PORT: z.coerce.number().default(9090),
  GRAFANA_ENABLED: z.coerce.boolean().default(true),
  GRAFANA_PORT: z.coerce.number().default(3001),
  HEALTH_CHECK_INTERVAL: z.coerce.number().default(30000),
  HEALTH_CHECK_TIMEOUT: z.coerce.number().default(5000),

  // Backup & Alerting
  BACKUP_ENABLED: z.coerce.boolean().default(true),
  BACKUP_INTERVAL: z.coerce.number().default(3600000),
  BACKUP_RETENTION_HOURS: z.coerce.number().default(168),
  BACKUP_PATH: z.string().default('backups'),
  ALERT_EMAIL_ENABLED: z.coerce.boolean().default(false),
  ALERT_EMAIL_SMTP_HOST: z.string().optional(),
  ALERT_EMAIL_SMTP_PORT: z.coerce.number().optional(),
  ALERT_EMAIL_USER: z.string().optional(),
  ALERT_EMAIL_PASSWORD: z.string().optional(),
  ALERT_EMAIL_TO: z.string().email().optional(),

  // External Services
  VAULT_ENABLED: z.coerce.boolean().default(false),
  VAULT_ADDR: z.string().url().optional(),
  VAULT_TOKEN: z.string().optional(),
  OPENWEATHER_API_KEY: z.string().optional(),

  // SSL Configuration
  SSL_ENABLED: z.coerce.boolean().default(false),
  SSL_CERT_PATH: z.string().optional(),
  SSL_KEY_PATH: z.string().optional(),

  // Testing Configuration
  TEST_MODE: z.coerce.boolean().default(false),
  MOCK_EXCHANGES: z.coerce.boolean().default(true),
  MOCK_DATA: z.coerce.boolean().default(false),
  MOCK_ORDERS: z.coerce.boolean().default(true),
});

// Validate environment variables
function validateEnv() {
  try {
    const env = envSchema.parse(process.env);
    return { success: true, env };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const formattedErrors = error.errors.map(err => ({
        field: err.path.join('.'),
        message: err.message,
        expected: err.expected,
        received: err.received,
      }));

      console.error('❌ Environment Variable Validation Failed:');
      console.error('Please fix the following configuration errors:');
      formattedErrors.forEach(err => {
        console.error(`  • ${err.field}: ${err.message}`);
        if (err.expected !== undefined) {
          console.error(`    Expected: ${JSON.stringify(err.expected)}`);
        }
        if (err.received !== undefined) {
          console.error(`    Received: ${JSON.stringify(err.received)}`);
        }
      });

      console.error('\n📋 Next Steps:');
      console.error('1. Copy .env.template to .env.local');
      console.error('2. Update .env.local with proper values');
      console.error('3. Restart the application');

      process.exit(1);
    }
    throw error;
  }
}

// Security validation
function validateSecurityConfig(env: any) {
  const warnings = [];
  const errors = [];

  // Check for default/weak secrets
  const weakSecrets = [
    'CHANGE_ME',
    'DEFAULT',
    'EXAMPLE',
    'TEST',
    'DEMO',
    'SAMPLE',
    'your-',
    'replace-',
  ];

  const checkWeakSecret = (value: string, fieldName: string) => {
    if (value && weakSecrets.some(weak => value.toLowerCase().includes(weak.toLowerCase()))) {
      if (env.NODE_ENV === 'production') {
        errors.push(`❌ ${fieldName}: Using default/weak secret in production`);
      } else {
        warnings.push(`⚠️  ${fieldName}: Using default/weak secret in development`);
      }
    }
  };

  checkWeakSecret(env.JWT_SECRET, 'JWT_SECRET');
  checkWeakSecret(env.JWT_ACCESS_SECRET, 'JWT_ACCESS_SECRET');
  checkWeakSecret(env.JWT_REFRESH_SECRET, 'JWT_REFRESH_SECRET');
  checkWeakSecret(env.ENCRYPTION_KEY, 'ENCRYPTION_KEY');
  checkWeakSecret(env.SESSION_SECRET, 'SESSION_SECRET');

  // Check for exposed secrets in production
  if (env.NODE_ENV === 'production') {
    if (env.TEST_MODE === true) {
      errors.push('❌ TEST_MODE cannot be enabled in production');
    }

    if (env.MOCK_EXCHANGES === true) {
      errors.push('❌ MOCK_EXCHANGES cannot be enabled in production');
    }

    if (env.TRADING_MODE === 'paper') {
      warnings.push('⚠️  TRADING_MODE is set to paper in production');
    }

    if (env.APP_DEBUG === true) {
      errors.push('❌ APP_DEBUG cannot be enabled in production');
    }
  }

  // Check database security
  if (env.DATABASE_URL && env.DATABASE_URL.includes('password')) {
    warnings.push('⚠️  DATABASE_URL contains password in plain text');
  }

  if (env.MONGO_URI && env.MONGO_URI.includes('password')) {
    warnings.push('⚠️  MONGO_URI contains password in plain text');
  }

  return { warnings, errors };
}

// Configuration validation and loading
export function loadConfig() {
  console.log('🔧 Loading application configuration...');

  // Validate environment variables
  const { success, env } = validateEnv();
  if (!success) {
    throw new Error('Environment validation failed');
  }

  // Security validation
  const { warnings, errors } = validateSecurityConfig(env);

  if (errors.length > 0) {
    console.error('❌ Security Configuration Errors:');
    errors.forEach(error => console.error(`  ${error}`));
    process.exit(1);
  }

  if (warnings.length > 0) {
    console.warn('⚠️  Security Configuration Warnings:');
    warnings.forEach(warning => console.warn(`  ${warning}`));
  }

  // Log successful validation
  console.log('✅ Environment validation successful');
  console.log(`📍 Environment: ${env.NODE_ENV}`);
  console.log(`🌐 Server: ${env.HOST}:${env.PORT}`);
  console.log(`🔐 Security: ${env.HELMET_ENABLED ? 'Enabled' : 'Disabled'}`);
  console.log(`📊 Monitoring: ${env.PROMETHEUS_ENABLED ? 'Enabled' : 'Disabled'}`);
  console.log(`💰 Trading: ${env.TRADING_MODE} mode`);

  return env;
}

// Export validated configuration
export const config = loadConfig();

// Export types
export type Config = z.infer<typeof envSchema>;