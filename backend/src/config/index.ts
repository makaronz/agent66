import { config } from './env-validation';

// Database configuration
export const databaseConfig = {
  postgres: {
    url: config.DATABASE_URL || `postgresql://${config.DB_USER}:${config.DB_PASSWORD || ''}@${config.DB_HOST}:${config.DB_PORT}/${config.DB_NAME}`,
    host: config.DB_HOST,
    port: config.DB_PORT,
    database: config.DB_NAME,
    username: config.DB_USER,
    password: config.DB_PASSWORD,
    ssl: config.DB_SSL,
    pool: {
      min: 2,
      max: config.DB_POOL_SIZE,
      acquire: 30000,
      idle: 10000,
    },
  },
  mongodb: {
    uri: config.MONGO_URI || `mongodb://${config.MONGO_HOST}:${config.MONGO_PORT}/${config.MONGO_DB_NAME}`,
    host: config.MONGO_HOST,
    port: config.MONGO_PORT,
    database: config.MONGO_DB_NAME,
    username: config.MONGO_USER,
    password: config.MONGO_PASSWORD,
    options: {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    },
  },
  redis: {
    url: config.REDIS_URL || `redis://${config.REDIS_HOST}:${config.REDIS_PORT}/${config.REDIS_DB}`,
    host: config.REDIS_HOST,
    port: config.REDIS_PORT,
    db: config.REDIS_DB,
    password: config.REDIS_PASSWORD,
    maxRetriesPerRequest: 3,
    retryDelayOnFailover: 100,
    lazyConnect: true,
    maxConnections: config.REDIS_MAX_CONNECTIONS,
  },
};

// Supabase configuration
export const supabaseConfig = {
  url: config.SUPABASE_URL,
  anonKey: config.SUPABASE_ANON_KEY,
  serviceRoleKey: config.SUPABASE_SERVICE_ROLE_KEY,
  options: {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  },
};

// JWT configuration
export const jwtConfig = {
  secret: config.JWT_SECRET,
  accessSecret: config.JWT_ACCESS_SECRET,
  refreshSecret: config.JWT_REFRESH_SECRET,
  expiresIn: config.JWT_EXPIRATION,
  refreshExpiresIn: config.JWT_REFRESH_EXPIRATION,
  issuer: config.APP_NAME,
  audience: 'smc-trading-agent',
};

// Encryption configuration
export const encryptionConfig = {
  key: config.ENCRYPTION_KEY,
  algorithm: 'aes-256-cbc',
  ivLength: 16,
  tagLength: 16,
};

// Session configuration
export const sessionConfig = {
  secret: config.SESSION_SECRET,
  timeout: config.SESSION_TIMEOUT,
  name: 'smc-session',
  secure: config.NODE_ENV === 'production',
  httpOnly: true,
  maxAge: config.SESSION_TIMEOUT,
  sameSite: 'strict' as const,
};

// Rate limiting configuration
export const rateLimitConfig = {
  windowMs: config.RATE_LIMIT_WINDOW_MS,
  max: config.RATE_LIMIT_MAX_REQUESTS,
  message: {
    error: 'Too many requests from this IP, please try again later.',
    retryAfter: Math.ceil(config.RATE_LIMIT_WINDOW_MS / 1000),
  },
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: false,
};

// CORS configuration
export const corsConfig = {
  origin: config.CORS_ORIGIN.split(',').map(origin => origin.trim()),
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  exposedHeaders: ['X-Total-Count', 'X-Rate-Limit-Limit', 'X-Rate-Limit-Remaining'],
  maxAge: 86400, // 24 hours
};

// Security configuration
export const securityConfig = {
  helmet: {
    enabled: config.HELMET_ENABLED,
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        fontSrc: ["'self'", "https://fonts.gstatic.com"],
        imgSrc: ["'self'", "data:", "https:"],
        scriptSrc: ["'self'"],
        connectSrc: ["'self'", "ws:", "wss:"],
      },
    },
  },
  csrf: {
    enabled: config.CSRF_PROTECTION,
    cookieOptions: {
      httpOnly: true,
      secure: config.NODE_ENV === 'production',
      sameSite: 'strict',
    },
  },
  ddos: {
    enabled: config.DDOS_PROTECTION,
    threshold: config.DDOS_THRESHOLD,
    windowMs: config.DDOS_WINDOW_MS,
  },
};

// Trading configuration
export const tradingConfig = {
  mode: config.TRADING_MODE,
  maxConcurrentTrades: config.MAX_CONCURRENT_TRADES,
  defaultRiskPercentage: config.DEFAULT_RISK_PERCENTAGE,
  defaultStopLossPercentage: config.DEFAULT_STOP_LOSS_PERCENTAGE,
  defaultTakeProfitPercentage: config.DEFAULT_TAKE_PROFIT_PERCENTAGE,
  exchanges: {
    binance: {
      apiKey: config.BINANCE_API_KEY,
      apiSecret: config.BINANCE_API_SECRET,
      testnet: config.BINANCE_TESTNET,
      baseUrl: config.BINANCE_TESTNET
        ? 'https://testnet.binance.vision'
        : 'https://api.binance.com',
      wsUrl: config.BINANCE_TESTNET
        ? 'wss://testnet.binance.vision/ws'
        : 'wss://stream.binance.com:9443/ws',
      rateLimit: 1200,
    },
    bybit: {
      apiKey: config.BYBIT_API_KEY,
      apiSecret: config.BYBIT_API_SECRET,
      testnet: config.BYBIT_TESTNET,
      baseUrl: config.BYBIT_TESTNET
        ? 'https://api-testnet.bybit.com'
        : 'https://api.bybit.com',
      wsUrl: config.BYBIT_TESTNET
        ? 'wss://stream-testnet.bybit.com/v5/public'
        : 'wss://stream.bybit.com/v5/public',
      rateLimit: 120,
    },
    oanda: {
      apiKey: config.OANDA_API_KEY,
      accountId: config.OANDA_ACCOUNT_ID,
      environment: config.OANDA_ENVIRONMENT,
      baseUrl: config.OANDA_ENVIRONMENT === 'live'
        ? 'https://api-fxtrade.oanda.com/v3'
        : 'https://api-fxpractice.oanda.com/v3',
      wsUrl: config.OANDA_ENVIRONMENT === 'live'
        ? 'wss://stream-fxtrade.oanda.com/v3'
        : 'wss://stream-fxpractice.oanda.com/v3',
      rateLimit: 120,
    },
  },
};

// Logging configuration
export const loggingConfig = {
  level: config.LOG_LEVEL,
  file: config.LOG_FILE,
  maxSize: '10m',
  maxFiles: 5,
  format: 'combined',
  colorize: config.NODE_ENV !== 'production',
};

// Monitoring configuration
export const monitoringConfig = {
  prometheus: {
    enabled: config.PROMETHEUS_ENABLED,
    port: config.PROMETHEUS_PORT,
    endpoint: '/metrics',
    collectDefaultMetrics: true,
    collectInterval: 10000,
  },
  grafana: {
    enabled: config.GRAFANA_ENABLED,
    port: config.GRAFANA_PORT,
    dashboardUrl: config.GRAFANA_DASHBOARD_URL,
  },
  healthCheck: {
    interval: config.HEALTH_CHECK_INTERVAL,
    timeout: config.HEALTH_CHECK_TIMEOUT,
    endpoint: '/health',
  },
};

// Backup configuration
export const backupConfig = {
  enabled: config.BACKUP_ENABLED,
  interval: config.BACKUP_INTERVAL,
  retentionHours: config.BACKUP_RETENTION_HOURS,
  path: config.BACKUP_PATH,
  compression: true,
  encryption: true,
};

// Alerting configuration
export const alertingConfig = {
  email: {
    enabled: config.ALERT_EMAIL_ENABLED,
    smtp: {
      host: config.ALERT_EMAIL_SMTP_HOST,
      port: config.ALERT_EMAIL_SMTP_PORT,
      secure: config.ALERT_EMAIL_SMTP_PORT === 465,
      auth: {
        user: config.ALERT_EMAIL_USER,
        pass: config.ALERT_EMAIL_PASSWORD,
      },
    },
    to: config.ALERT_EMAIL_TO,
  },
  webhooks: {
    slack: process.env.SLACK_WEBHOOK_URL,
    discord: process.env.DISCORD_WEBHOOK_URL,
    telegram: {
      botToken: process.env.TELEGRAM_BOT_TOKEN,
      chatId: process.env.TELEGRAM_CHAT_ID,
    },
  },
};

// SSL configuration
export const sslConfig = {
  enabled: config.SSL_ENABLED,
  certPath: config.SSL_CERT_PATH,
  keyPath: config.SSL_KEY_PATH,
  caPath: process.env.SSL_CA_PATH,
  passphrase: process.env.SSL_PASSPHRASE,
};

// Development configuration
export const developmentConfig = {
  testMode: config.TEST_MODE,
  mockExchanges: config.MOCK_EXCHANGES,
  mockData: config.MOCK_DATA,
  mockOrders: config.MOCK_ORDERS,
  hotReload: config.NODE_ENV === 'development',
  sourceMaps: config.NODE_ENV === 'development',
};

// Export all configurations
export const appConfig = {
  app: {
    name: config.APP_NAME,
    version: config.APP_VERSION,
    environment: config.NODE_ENV,
    debug: config.APP_DEBUG,
    port: config.PORT,
    host: config.HOST,
  },
  database: databaseConfig,
  supabase: supabaseConfig,
  jwt: jwtConfig,
  encryption: encryptionConfig,
  session: sessionConfig,
  rateLimit: rateLimitConfig,
  cors: corsConfig,
  security: securityConfig,
  trading: tradingConfig,
  logging: loggingConfig,
  monitoring: monitoringConfig,
  backup: backupConfig,
  alerting: alertingConfig,
  ssl: sslConfig,
  development: developmentConfig,
};

// Export default
export default appConfig;