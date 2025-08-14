/**
 * Comprehensive input validation schemas using Zod
 * Provides type-safe validation for all API endpoints
 */

import { z } from 'zod';

// Common validation patterns
const emailSchema = z.string().email('Invalid email format').max(255);
const passwordSchema = z.string()
  .min(8, 'Password must be at least 8 characters')
  .max(128, 'Password must not exceed 128 characters')
  .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/, 
    'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character');

const apiKeySchema = z.string()
  .min(10, 'API key must be at least 10 characters')
  .max(256, 'API key must not exceed 256 characters')
  .regex(/^[A-Za-z0-9_-]+$/, 'API key contains invalid characters');

const secretKeySchema = z.string()
  .min(10, 'Secret key must be at least 10 characters')
  .max(512, 'Secret key must not exceed 512 characters')
  .regex(/^[A-Za-z0-9+/=_-]+$/, 'Secret key contains invalid characters');

// Trading symbol validation
const symbolSchema = z.string()
  .min(3, 'Symbol must be at least 3 characters')
  .max(20, 'Symbol must not exceed 20 characters')
  .regex(/^[A-Z0-9/_-]+$/, 'Symbol must contain only uppercase letters, numbers, and allowed separators')
  .transform(s => s.toUpperCase());

// Numeric validations
const positiveNumberSchema = z.number().positive('Value must be positive');
const priceSchema = z.number().positive('Price must be positive').max(1000000, 'Price too high');
const quantitySchema = z.number().positive('Quantity must be positive').max(1000000, 'Quantity too high');
const percentageSchema = z.number().min(0, 'Percentage cannot be negative').max(100, 'Percentage cannot exceed 100');

// Exchange validation
const exchangeSchema = z.enum(['binance', 'bybit', 'oanda']);

// Order side and type validation
const orderSideSchema = z.enum(['buy', 'sell']);

const orderTypeSchema = z.enum(['market', 'limit', 'stop_loss', 'take_profit']);

// Authentication schemas
export const registerSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  full_name: z.string()
    .min(2, 'Full name must be at least 2 characters')
    .max(100, 'Full name must not exceed 100 characters')
    .regex(/^[a-zA-Z\s'-]+$/, 'Full name contains invalid characters')
    .optional(),
  terms_accepted: z.boolean().refine(val => val === true, 'Terms and conditions must be accepted')
});

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required').max(128)
});

export const changePasswordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: passwordSchema,
  confirm_password: z.string()
}).refine(data => data.new_password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"]
});

// User profile schemas
export const updateProfileSchema = z.object({
  full_name: z.string()
    .min(2, 'Full name must be at least 2 characters')
    .max(100, 'Full name must not exceed 100 characters')
    .regex(/^[a-zA-Z\s'-]+$/, 'Full name contains invalid characters')
    .optional(),
  avatar_url: z.string().url('Invalid avatar URL').optional(),
  timezone: z.string().max(50, 'Timezone must not exceed 50 characters').optional(),
  notification_preferences: z.object({
    email_alerts: z.boolean().optional(),
    push_notifications: z.boolean().optional(),
    trading_alerts: z.boolean().optional()
  }).optional()
});

// API key management schemas
export const storeApiKeysSchema = z.object({
  exchange: exchangeSchema,
  apiKey: apiKeySchema,
  secret: secretKeySchema,
  isTestnet: z.boolean().default(true),
  label: z.string()
    .min(1, 'Label is required')
    .max(50, 'Label must not exceed 50 characters')
    .regex(/^[a-zA-Z0-9\s_-]+$/, 'Label contains invalid characters')
    .optional()
});

export const testConnectionSchema = z.object({
  apiKey: apiKeySchema,
  secret: secretKeySchema,
  sandbox: z.boolean().default(true),
  saveKeys: z.boolean().default(false),
  exchange: exchangeSchema.optional()
});

// Trading schemas
export const placeOrderSchema = z.object({
  symbol: symbolSchema,
  side: orderSideSchema,
  type: orderTypeSchema,
  quantity: quantitySchema,
  price: priceSchema.optional(),
  stopLoss: priceSchema.optional(),
  takeProfit: priceSchema.optional(),
  timeInForce: z.enum(['GTC', 'IOC', 'FOK']).default('GTC').optional(),
  clientOrderId: z.string()
    .max(36, 'Client order ID must not exceed 36 characters')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Client order ID contains invalid characters')
    .optional()
}).refine(data => {
  // Require price for limit orders
  if (data.type === 'limit' && !data.price) {
    return false;
  }
  return true;
}, {
  message: 'Price is required for limit orders',
  path: ['price']
}).refine(data => {
  // Validate stop loss and take profit logic
  if (data.stopLoss && data.price) {
    if (data.side === 'buy' && data.stopLoss >= data.price) {
      return false;
    }
    if (data.side === 'sell' && data.stopLoss <= data.price) {
      return false;
    }
  }
  return true;
}, {
  message: 'Stop loss price must be below entry price for buy orders and above entry price for sell orders',
  path: ['stopLoss']
});

export const cancelOrderSchema = z.object({
  orderId: z.string().min(1, 'Order ID is required'),
  symbol: symbolSchema,
  clientOrderId: z.string().optional()
});

export const getOrderHistorySchema = z.object({
  symbol: symbolSchema.optional(),
  startTime: z.number().int().positive().optional(),
  endTime: z.number().int().positive().optional(),
  limit: z.number().int().min(1).max(1000).default(100),
  offset: z.number().int().min(0).default(0)
}).refine(data => {
  if (data.startTime && data.endTime && data.startTime >= data.endTime) {
    return false;
  }
  return true;
}, {
  message: 'Start time must be before end time',
  path: ['endTime']
});

// Market data schemas
export const getMarketDataSchema = z.object({
  symbol: symbolSchema,
  interval: z.enum(['1m', '5m', '15m', '30m', '1h', '4h', '1d']).default('1h'),
  limit: z.number().int().min(1).max(1000).default(100),
  startTime: z.number().int().positive().optional(),
  endTime: z.number().int().positive().optional()
});

export const getTickerSchema = z.object({
  symbol: symbolSchema.optional()
});

// Configuration schemas
export const saveConfigurationSchema = z.object({
  configName: z.string()
    .min(1, 'Configuration name is required')
    .max(50, 'Configuration name must not exceed 50 characters')
    .regex(/^[a-zA-Z0-9\s_-]+$/, 'Configuration name contains invalid characters'),
  config: z.object({
    risk_management: z.object({
      max_position_size: positiveNumberSchema,
      max_daily_loss: positiveNumberSchema,
      max_drawdown: percentageSchema,
      stop_loss_percentage: percentageSchema.optional(),
      take_profit_percentage: percentageSchema.optional()
    }).optional(),
    trading_parameters: z.object({
      symbols: z.array(symbolSchema).min(1, 'At least one symbol is required'),
      timeframes: z.array(z.enum(['1m', '5m', '15m', '30m', '1h', '4h', '1d'])).min(1),
      max_concurrent_trades: z.number().int().min(1).max(100),
      min_confidence_threshold: percentageSchema
    }).optional(),
    smc_settings: z.object({
      detect_order_blocks: z.boolean().default(true),
      detect_liquidity_zones: z.boolean().default(true),
      detect_fair_value_gaps: z.boolean().default(true),
      min_volume_threshold: positiveNumberSchema.optional(),
      confidence_threshold: percentageSchema.default(70)
    }).optional()
  })
});

// MFA schemas
export const setupTOTPSchema = z.object({
  secret: z.string().min(16, 'TOTP secret must be at least 16 characters'),
  token: z.string().length(6, 'TOTP token must be exactly 6 digits').regex(/^\d{6}$/, 'TOTP token must contain only digits')
});

export const verifyTOTPSchema = z.object({
  token: z.string().length(6, 'TOTP token must be exactly 6 digits').regex(/^\d{6}$/, 'TOTP token must contain only digits')
});

export const setupSMSSchema = z.object({
  phone_number: z.string()
    .regex(/^\+[1-9]\d{1,14}$/, 'Phone number must be in international format (+1234567890)')
    .min(10, 'Phone number must be at least 10 digits')
    .max(15, 'Phone number must not exceed 15 digits')
});

export const verifySMSSchema = z.object({
  phone_number: z.string().regex(/^\+[1-9]\d{1,14}$/, 'Invalid phone number format'),
  code: z.string().length(6, 'SMS code must be exactly 6 digits').regex(/^\d{6}$/, 'SMS code must contain only digits')
});

// WebAuthn schemas
export const webAuthnRegistrationSchema = z.object({
  credential: z.object({
    id: z.string().min(1, 'Credential ID is required'),
    rawId: z.string().min(1, 'Raw credential ID is required'),
    response: z.object({
      attestationObject: z.string().min(1, 'Attestation object is required'),
      clientDataJSON: z.string().min(1, 'Client data JSON is required')
    }),
    type: z.literal('public-key')
  }),
  name: z.string()
    .min(1, 'Authenticator name is required')
    .max(50, 'Authenticator name must not exceed 50 characters')
});

export const webAuthnAuthenticationSchema = z.object({
  credential: z.object({
    id: z.string().min(1, 'Credential ID is required'),
    rawId: z.string().min(1, 'Raw credential ID is required'),
    response: z.object({
      authenticatorData: z.string().min(1, 'Authenticator data is required'),
      clientDataJSON: z.string().min(1, 'Client data JSON is required'),
      signature: z.string().min(1, 'Signature is required'),
      userHandle: z.string().optional()
    }),
    type: z.literal('public-key')
  })
});

// Query parameter schemas
export const paginationSchema = z.object({
  page: z.string().regex(/^\d+$/, 'Page must be a number').transform(Number).refine(n => n >= 1, 'Page must be at least 1').default(() => 1),
  limit: z.string().regex(/^\d+$/, 'Limit must be a number').transform(Number).refine(n => n >= 1 && n <= 100, 'Limit must be between 1 and 100').default(() => 20),
  sort: z.string().max(50, 'Sort parameter too long').optional(),
  order: z.enum(['asc', 'desc']).default('desc')
});

// File upload schemas
export const fileUploadSchema = z.object({
  file: z.object({
    originalname: z.string().max(255, 'Filename too long'),
    mimetype: z.enum(['image/jpeg', 'image/png', 'image/gif', 'image/webp']),
    size: z.number().max(5 * 1024 * 1024, 'File size must not exceed 5MB')
  })
});

// Export type definitions for TypeScript
export type RegisterInput = z.infer<typeof registerSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type UpdateProfileInput = z.infer<typeof updateProfileSchema>;
export type StoreApiKeysInput = z.infer<typeof storeApiKeysSchema>;
export type PlaceOrderInput = z.infer<typeof placeOrderSchema>;
export type SaveConfigurationInput = z.infer<typeof saveConfigurationSchema>;
export type GetMarketDataInput = z.infer<typeof getMarketDataSchema>;
export type PaginationInput = z.infer<typeof paginationSchema>;