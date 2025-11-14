/**
 * OpenAPI/Swagger configuration for SMC Trading Agent API
 * Provides comprehensive API documentation with examples and schemas
 */

import swaggerJSDoc from 'swagger-jsdoc';
import { SwaggerDefinition } from 'swagger-jsdoc';

// API versioning configuration
export const API_VERSION = 'v1';
export const API_BASE_PATH = `/api/${API_VERSION}`;

// OpenAPI specification definition
const swaggerDefinition: SwaggerDefinition = {
  openapi: '3.0.3',
  info: {
    title: 'SMC Trading Agent API',
    version: '1.0.0',
    description: `
      A sophisticated algorithmic trading system API that implements Smart Money Concepts (SMC) 
      for automated cryptocurrency and forex trading.
      
      ## Features
      - **Multi-exchange support**: Binance, Bybit, Oanda integration
      - **SMC pattern detection**: Advanced institutional trading pattern analysis
      - **Real-time processing**: Live market data with sub-second latency
      - **Risk management**: Comprehensive position sizing and risk controls
      - **Authentication & Security**: JWT, MFA, API key management
      
      ## Getting Started
      
      1. **Register**: Create an account via \`/auth/register\`
      2. **Login**: Authenticate via \`/auth/login\` to get JWT token
      3. **Configure**: Add exchange API keys via \`/users/api-keys\`
      4. **Trade**: Start placing orders and monitoring positions
      
      ## Authentication
      Most endpoints require JWT authentication. Include the token in the Authorization header:
      \`\`\`
      Authorization: Bearer <your-jwt-token>
      \`\`\`
      
      ## API Versioning
      This API uses URL path versioning:
      - Current version: **v1**
      - Base URL: \`/api/v1\`
      - Version header: \`X-API-Version: v1\`
      
      ## Rate Limiting
      API endpoints are rate-limited to ensure fair usage and system stability:
      - General endpoints: 100 requests per 15 minutes
      - Authentication: 5 attempts per 15 minutes
      - Trading operations: 10 requests per minute
      - Market data: 60 requests per minute
      
      Rate limit headers are included in responses:
      - \`X-RateLimit-Limit\`: Request limit per window
      - \`X-RateLimit-Remaining\`: Remaining requests
      - \`X-RateLimit-Reset\`: Reset time (Unix timestamp)
      
      ## Error Handling
      All endpoints return consistent error responses:
      
      **Success Response:**
      \`\`\`json
      {
        "success": true,
        "data": { ... },
        "message": "Operation successful"
      }
      \`\`\`
      
      **Error Response:**
      \`\`\`json
      {
        "success": false,
        "error": "Error message",
        "details": "Additional details",
        "code": "ERROR_CODE",
        "timestamp": "2024-01-15T10:30:00.000Z"
      }
      \`\`\`
      
      ## Status Codes
      - \`200\`: Success
      - \`400\`: Bad Request (validation errors)
      - \`401\`: Unauthorized (authentication required)
      - \`403\`: Forbidden (insufficient permissions)
      - \`404\`: Not Found
      - \`429\`: Too Many Requests (rate limited)
      - \`500\`: Internal Server Error
      
      ## Examples
      
      ### Authentication
      \`\`\`bash
      curl -X POST "https://api.smctradingagent.com/api/v1/auth/login" \\
        -H "Content-Type: application/json" \\
        -d '{"email": "trader@example.com", "password": "password"}'
      \`\`\`
      
      ### Test Exchange Connection
      \`\`\`bash
      curl -X POST "https://api.smctradingagent.com/api/v1/binance/test-connection" \\
        -H "Content-Type: application/json" \\
        -H "Authorization: Bearer your-jwt-token" \\
        -d '{"apiKey": "your-api-key", "secret": "your-secret", "sandbox": true}'
      \`\`\`
      
      ### Get Market Data
      \`\`\`bash
      curl -X GET "https://api.smctradingagent.com/api/v1/binance/market-data/BTC/USDT?sandbox=true"
      \`\`\`
    `,
    contact: {
      name: 'SMC Trading Agent Support',
      email: 'support@smctradingagent.com',
      url: 'https://github.com/smc-trading-agent'
    },
    license: {
      name: 'MIT',
      url: 'https://opensource.org/licenses/MIT'
    },
    termsOfService: 'https://smctradingagent.com/terms'
  },
  servers: [
    {
      url: `http://localhost:3000${API_BASE_PATH}`,
      description: 'Development server'
    },
    {
      url: `https://api.smctradingagent.com${API_BASE_PATH}`,
      description: 'Production server'
    },
    {
      url: `https://staging-api.smctradingagent.com${API_BASE_PATH}`,
      description: 'Staging server'
    }
  ],
  components: {
    securitySchemes: {
      BearerAuth: {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
        description: 'JWT token for authentication'
      },
      ApiKeyAuth: {
        type: 'apiKey',
        in: 'header',
        name: 'X-API-Key',
        description: 'API key for service-to-service authentication'
      }
    },
    schemas: {
      // Common response schemas
      SuccessResponse: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: true
          },
          message: {
            type: 'string',
            example: 'Operation completed successfully'
          },
          timestamp: {
            type: 'string',
            format: 'date-time',
            example: '2024-01-15T10:30:00.000Z'
          }
        },
        required: ['success']
      },
      ErrorResponse: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: false
          },
          error: {
            type: 'string',
            example: 'Invalid request parameters'
          },
          details: {
            type: 'string',
            example: 'Additional error details'
          },
          code: {
            type: 'string',
            example: 'VALIDATION_ERROR'
          },
          timestamp: {
            type: 'string',
            format: 'date-time',
            example: '2024-01-15T10:30:00.000Z'
          }
        },
        required: ['success', 'error']
      },
      
      // User schemas
      User: {
        type: 'object',
        properties: {
          id: {
            type: 'string',
            format: 'uuid',
            example: '123e4567-e89b-12d3-a456-426614174000'
          },
          email: {
            type: 'string',
            format: 'email',
            example: 'trader@example.com'
          },
          full_name: {
            type: 'string',
            example: 'John Doe'
          },
          avatar_url: {
            type: 'string',
            format: 'uri',
            example: 'https://example.com/avatar.jpg'
          },
          created_at: {
            type: 'string',
            format: 'date-time',
            example: '2024-01-15T10:30:00.000Z'
          },
          updated_at: {
            type: 'string',
            format: 'date-time',
            example: '2024-01-15T10:30:00.000Z'
          }
        },
        required: ['id', 'email']
      },
      
      // Authentication schemas
      LoginRequest: {
        type: 'object',
        properties: {
          email: {
            type: 'string',
            format: 'email',
            example: 'trader@example.com'
          },
          password: {
            type: 'string',
            format: 'password',
            example: 'SecurePassword123!'
          }
        },
        required: ['email', 'password']
      },
      LoginResponse: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: true
          },
          token: {
            type: 'string',
            example: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
          },
          user: {
            $ref: '#/components/schemas/User'
          },
          expires_in: {
            type: 'integer',
            example: 3600,
            description: 'Token expiration time in seconds'
          }
        },
        required: ['success', 'token', 'user']
      },
      RegisterRequest: {
        type: 'object',
        properties: {
          email: {
            type: 'string',
            format: 'email',
            example: 'newuser@example.com'
          },
          password: {
            type: 'string',
            format: 'password',
            example: 'SecurePassword123!'
          },
          full_name: {
            type: 'string',
            example: 'Jane Smith'
          }
        },
        required: ['email', 'password']
      },
      
      // Trading schemas
      ExchangeCredentials: {
        type: 'object',
        properties: {
          apiKey: {
            type: 'string',
            example: 'your-api-key'
          },
          secret: {
            type: 'string',
            example: 'your-api-secret'
          },
          sandbox: {
            type: 'boolean',
            example: true,
            description: 'Whether to use testnet/sandbox environment'
          }
        },
        required: ['apiKey', 'secret']
      },
      ConnectionTestResponse: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: true
          },
          message: {
            type: 'string',
            example: 'Connection successful'
          },
          data: {
            type: 'object',
            properties: {
              exchange: {
                type: 'string',
                example: 'Binance'
              },
              status: {
                type: 'string',
                example: 'ok'
              },
              updated: {
                type: 'string',
                format: 'date-time',
                example: '2024-01-15T10:30:00.000Z'
              },
              sandbox: {
                type: 'boolean',
                example: true
              }
            }
          }
        }
      },
      AccountInfo: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: true
          },
          data: {
            type: 'object',
            properties: {
              balances: {
                type: 'object',
                additionalProperties: {
                  type: 'object',
                  properties: {
                    total: {
                      type: 'number',
                      example: 1000.50
                    },
                    free: {
                      type: 'number',
                      example: 950.25
                    },
                    used: {
                      type: 'number',
                      example: 50.25
                    }
                  }
                },
                example: {
                  'USDT': {
                    total: 1000.50,
                    free: 950.25,
                    used: 50.25
                  },
                  'BTC': {
                    total: 0.05,
                    free: 0.04,
                    used: 0.01
                  }
                }
              },
              tradingFees: {
                type: 'object',
                properties: {
                  maker: {
                    type: 'number',
                    example: 0.001
                  },
                  taker: {
                    type: 'number',
                    example: 0.001
                  }
                }
              },
              accountType: {
                type: 'string',
                example: 'Testnet'
              },
              timestamp: {
                type: 'integer',
                example: 1705312200000
              }
            }
          }
        }
      },
      MarketData: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: true
          },
          data: {
            type: 'object',
            properties: {
              symbol: {
                type: 'string',
                example: 'BTC/USDT'
              },
              price: {
                type: 'number',
                example: 45000.50
              },
              bid: {
                type: 'number',
                example: 44999.75
              },
              ask: {
                type: 'number',
                example: 45001.25
              },
              volume: {
                type: 'number',
                example: 1234.56
              },
              change: {
                type: 'number',
                example: 500.25
              },
              percentage: {
                type: 'number',
                example: 1.12
              },
              high: {
                type: 'number',
                example: 45500.00
              },
              low: {
                type: 'number',
                example: 44000.00
              },
              recentTrades: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    price: {
                      type: 'number',
                      example: 45000.50
                    },
                    amount: {
                      type: 'number',
                      example: 0.1
                    },
                    side: {
                      type: 'string',
                      enum: ['buy', 'sell'],
                      example: 'buy'
                    },
                    timestamp: {
                      type: 'integer',
                      example: 1705312200000
                    }
                  }
                }
              }
            }
          }
        }
      },
      PlaceOrderRequest: {
        type: 'object',
        properties: {
          symbol: {
            type: 'string',
            example: 'BTC/USDT'
          },
          side: {
            type: 'string',
            enum: ['buy', 'sell'],
            example: 'buy'
          },
          type: {
            type: 'string',
            enum: ['market', 'limit'],
            example: 'limit'
          },
          quantity: {
            type: 'number',
            example: 0.1,
            minimum: 0
          },
          price: {
            type: 'number',
            example: 45000.00,
            minimum: 0,
            description: 'Required for limit orders'
          },
          stopLoss: {
            type: 'number',
            example: 44000.00,
            minimum: 0,
            description: 'Optional stop loss price'
          },
          takeProfit: {
            type: 'number',
            example: 46000.00,
            minimum: 0,
            description: 'Optional take profit price'
          }
        },
        required: ['symbol', 'side', 'type', 'quantity']
      },
      PlaceOrderResponse: {
        type: 'object',
        properties: {
          success: {
            type: 'boolean',
            example: true
          },
          data: {
            type: 'object',
            properties: {
              orderId: {
                type: 'string',
                example: '12345678'
              },
              symbol: {
                type: 'string',
                example: 'BTC/USDT'
              },
              side: {
                type: 'string',
                example: 'buy'
              },
              type: {
                type: 'string',
                example: 'limit'
              },
              quantity: {
                type: 'number',
                example: 0.1
              },
              price: {
                type: 'number',
                example: 45000.00
              },
              fillPrice: {
                type: 'number',
                example: 45000.50
              },
              status: {
                type: 'string',
                example: 'filled'
              },
              timestamp: {
                type: 'integer',
                example: 1705312200000
              },
              stopLossOrderId: {
                type: 'string',
                example: '12345679'
              },
              takeProfitOrderId: {
                type: 'string',
                example: '12345680'
              }
            }
          }
        }
      },
      
      // API Key management schemas
      ApiKeyRequest: {
        type: 'object',
        properties: {
          exchange: {
            type: 'string',
            enum: ['binance', 'bybit', 'oanda'],
            example: 'binance'
          },
          apiKey: {
            type: 'string',
            example: 'your-api-key'
          },
          secret: {
            type: 'string',
            example: 'your-api-secret'
          },
          isTestnet: {
            type: 'boolean',
            example: true
          }
        },
        required: ['exchange', 'apiKey', 'secret']
      },
      ApiKeyInfo: {
        type: 'object',
        properties: {
          id: {
            type: 'string',
            format: 'uuid',
            example: '123e4567-e89b-12d3-a456-426614174000'
          },
          exchange: {
            type: 'string',
            example: 'binance'
          },
          is_testnet: {
            type: 'boolean',
            example: true
          },
          is_active: {
            type: 'boolean',
            example: true
          },
          has_api_key: {
            type: 'boolean',
            example: true
          },
          has_secret: {
            type: 'boolean',
            example: true
          },
          created_at: {
            type: 'string',
            format: 'date-time',
            example: '2024-01-15T10:30:00.000Z'
          }
        }
      }
    },
    responses: {
      UnauthorizedError: {
        description: 'Authentication required',
        content: {
          'application/json': {
            schema: {
              $ref: '#/components/schemas/ErrorResponse'
            },
            examples: {
              missing_token: {
                summary: 'Missing authentication token',
                value: {
                  success: false,
                  error: 'Authentication required',
                  details: 'Authorization header with Bearer token is required',
                  code: 'UNAUTHORIZED',
                  timestamp: '2024-01-15T10:30:00.000Z'
                }
              },
              invalid_token: {
                summary: 'Invalid or expired token',
                value: {
                  success: false,
                  error: 'Invalid or expired token',
                  details: 'Please login again to get a new token',
                  code: 'TOKEN_INVALID',
                  timestamp: '2024-01-15T10:30:00.000Z'
                }
              }
            }
          }
        }
      },
      ForbiddenError: {
        description: 'Insufficient permissions',
        content: {
          'application/json': {
            schema: {
              $ref: '#/components/schemas/ErrorResponse'
            },
            example: {
              success: false,
              error: 'Insufficient permissions',
              code: 'FORBIDDEN',
              timestamp: '2024-01-15T10:30:00.000Z'
            }
          }
        }
      },
      ValidationError: {
        description: 'Invalid request data',
        content: {
          'application/json': {
            schema: {
              $ref: '#/components/schemas/ErrorResponse'
            },
            example: {
              success: false,
              error: 'Validation failed',
              details: 'Missing required field: email',
              code: 'VALIDATION_ERROR',
              timestamp: '2024-01-15T10:30:00.000Z'
            }
          }
        }
      },
      NotFoundError: {
        description: 'Resource not found',
        content: {
          'application/json': {
            schema: {
              $ref: '#/components/schemas/ErrorResponse'
            },
            example: {
              success: false,
              error: 'Resource not found',
              code: 'NOT_FOUND',
              timestamp: '2024-01-15T10:30:00.000Z'
            }
          }
        }
      },
      InternalServerError: {
        description: 'Internal server error',
        content: {
          'application/json': {
            schema: {
              $ref: '#/components/schemas/ErrorResponse'
            },
            example: {
              success: false,
              error: 'Internal server error',
              code: 'INTERNAL_ERROR',
              timestamp: '2024-01-15T10:30:00.000Z'
            }
          }
        }
      },
      RateLimitError: {
        description: 'Rate limit exceeded',
        content: {
          'application/json': {
            schema: {
              $ref: '#/components/schemas/ErrorResponse'
            },
            examples: {
              general_rate_limit: {
                summary: 'General rate limit exceeded',
                value: {
                  success: false,
                  error: 'Rate limit exceeded',
                  details: 'Too many requests from this IP, please try again later',
                  code: 'RATE_LIMIT_EXCEEDED',
                  retryAfter: 900,
                  timestamp: '2024-01-15T10:30:00.000Z'
                }
              },
              auth_rate_limit: {
                summary: 'Authentication rate limit exceeded',
                value: {
                  success: false,
                  error: 'Too many authentication attempts',
                  details: 'Please wait before trying to login again',
                  code: 'AUTH_RATE_LIMIT_EXCEEDED',
                  retryAfter: 900,
                  timestamp: '2024-01-15T10:30:00.000Z'
                }
              },
              trading_rate_limit: {
                summary: 'Trading rate limit exceeded',
                value: {
                  success: false,
                  error: 'Too many trading requests',
                  details: 'Please slow down your trading operations',
                  code: 'TRADING_RATE_LIMIT_EXCEEDED',
                  retryAfter: 60,
                  timestamp: '2024-01-15T10:30:00.000Z'
                }
              }
            }
          }
        },
        headers: {
          'X-RateLimit-Limit': {
            description: 'Request limit per time window',
            schema: {
              type: 'integer',
              example: 100
            }
          },
          'X-RateLimit-Remaining': {
            description: 'Remaining requests in current window',
            schema: {
              type: 'integer',
              example: 0
            }
          },
          'X-RateLimit-Reset': {
            description: 'Time when rate limit resets (Unix timestamp)',
            schema: {
              type: 'integer',
              example: 1705312800
            }
          },
          'Retry-After': {
            description: 'Seconds to wait before retrying',
            schema: {
              type: 'integer',
              example: 900
            }
          }
        }
      }
    },
    parameters: {
      LimitParam: {
        name: 'limit',
        in: 'query',
        description: 'Maximum number of items to return',
        required: false,
        schema: {
          type: 'integer',
          minimum: 1,
          maximum: 100,
          default: 20
        }
      },
      OffsetParam: {
        name: 'offset',
        in: 'query',
        description: 'Number of items to skip',
        required: false,
        schema: {
          type: 'integer',
          minimum: 0,
          default: 0
        }
      },
      ExchangeParam: {
        name: 'exchange',
        in: 'query',
        description: 'Filter by exchange',
        required: false,
        schema: {
          type: 'string',
          enum: ['binance', 'bybit', 'oanda']
        }
      }
    }
  },
  security: [
    {
      BearerAuth: []
    }
  ],
  tags: [
    {
      name: 'Authentication',
      description: 'User authentication and authorization endpoints'
    },
    {
      name: 'Users',
      description: 'User profile and settings management'
    },
    {
      name: 'Trading',
      description: 'Trading operations and exchange integrations'
    },
    {
      name: 'Market Data',
      description: 'Real-time and historical market data'
    },
    {
      name: 'Risk Management',
      description: 'Risk management and position sizing'
    },
    {
      name: 'System',
      description: 'System health and monitoring endpoints'
    }
  ]
};

// Swagger JSDoc options
const swaggerOptions = {
  definition: swaggerDefinition,
  apis: [
    './api/routes/*.ts',
    './api/routes/*.js',
    './api/*.ts',
    './api/*.js'
  ]
};

// Generate OpenAPI specification
export const swaggerSpec = swaggerJSDoc(swaggerOptions);

// Export configuration for use in other modules
export default {
  swaggerDefinition,
  swaggerOptions,
  swaggerSpec,
  API_VERSION,
  API_BASE_PATH
};