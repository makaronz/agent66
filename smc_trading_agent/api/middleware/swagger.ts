/**
 * Swagger UI middleware setup for API documentation
 * Provides interactive API documentation interface
 */

import swaggerUi from 'swagger-ui-express';
import { Request, Response, NextFunction } from 'express';
import { swaggerSpec, API_VERSION } from '../config/swagger.js';

// Custom CSS for Swagger UI styling
const customCss = `
  .swagger-ui .topbar { display: none; }
  .swagger-ui .info .title { color: #1f2937; }
  .swagger-ui .info .description { color: #4b5563; }
  .swagger-ui .scheme-container { background: #f9fafb; padding: 10px; border-radius: 4px; }
  .swagger-ui .btn.authorize { background-color: #3b82f6; border-color: #3b82f6; }
  .swagger-ui .btn.authorize:hover { background-color: #2563eb; border-color: #2563eb; }
  .swagger-ui .model-box { background-color: #f8fafc; }
  .swagger-ui .model .property { color: #1f2937; }
  .swagger-ui .response-col_status { color: #059669; }
  .swagger-ui .response-col_links { color: #3b82f6; }
`;

// Custom site title and favicon
const customSiteTitle = 'SMC Trading Agent API Documentation';

// Swagger UI options
const swaggerUiOptions: swaggerUi.SwaggerUiOptions = {
  customCss,
  customSiteTitle,
  customfavIcon: '/favicon.ico',
  swaggerOptions: {
    docExpansion: 'list',
    filter: true,
    showRequestDuration: true,
    tryItOutEnabled: true,
    requestInterceptor: (req: any) => {
      // Add API version header to all requests
      req.headers['X-API-Version'] = API_VERSION;
      return req;
    },
    responseInterceptor: (res: any) => {
      // Log response for debugging in development
      if (process.env.NODE_ENV === 'development') {
        console.log('Swagger UI Response:', res.status, res.url);
      }
      return res;
    },
    persistAuthorization: true,
    displayOperationId: false,
    displayRequestDuration: true,
    defaultModelsExpandDepth: 2,
    defaultModelExpandDepth: 2,
    showExtensions: true,
    showCommonExtensions: true,
    useUnsafeMarkdown: false
  }
};

// Security warning middleware for production
const securityWarningMiddleware = (req: Request, res: Response, next: NextFunction) => {
  if (process.env.NODE_ENV === 'production') {
    // Add security headers for documentation access
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    
    // Log documentation access in production
    console.log(`API Documentation accessed from IP: ${req.ip} at ${new Date().toISOString()}`);
  }
  next();
};

// Custom middleware to inject environment-specific information
const environmentInfoMiddleware = (req: Request, res: Response, next: NextFunction) => {
  // Add environment information to the spec
  const envSpec: any = { ...swaggerSpec };
  
  // Update server URLs based on environment
  if (process.env.NODE_ENV === 'production') {
    envSpec.servers = [
      {
        url: `https://api.smctradingagent.com/api/${API_VERSION}`,
        description: 'Production server'
      }
    ];
  } else if (process.env.NODE_ENV === 'staging') {
    envSpec.servers = [
      {
        url: `https://staging-api.smctradingagent.com/api/${API_VERSION}`,
        description: 'Staging server'
      }
    ];
  } else {
    envSpec.servers = [
      {
        url: `http://localhost:${process.env.PORT || 3000}/api/${API_VERSION}`,
        description: 'Development server'
      }
    ];
  }
  
  // Add environment badge to description
  const environmentBadge = process.env.NODE_ENV === 'production' 
    ? '🟢 **Production Environment**' 
    : process.env.NODE_ENV === 'staging'
    ? '🟡 **Staging Environment**'
    : '🔵 **Development Environment**';
  
  envSpec.info.description = `${environmentBadge}\n\n${envSpec.info.description}`;
  
  // Store the modified spec for this request
  (req as any).swaggerSpec = envSpec;
  next();
};

// Create Swagger UI middleware with custom spec
const createSwaggerMiddleware = () => {
  return [
    securityWarningMiddleware,
    environmentInfoMiddleware,
    (req: Request, res: Response, next: NextFunction) => {
      // Use the environment-specific spec
      const spec = (req as any).swaggerSpec || swaggerSpec;
      swaggerUi.setup(spec, swaggerUiOptions)(req, res, next);
    }
  ];
};

// Export middleware functions
export {
  swaggerUi,
  swaggerUiOptions,
  createSwaggerMiddleware,
  securityWarningMiddleware,
  environmentInfoMiddleware,
  customCss,
  customSiteTitle
};

// Default export for easy import
export default {
  serve: swaggerUi.serve,
  setup: createSwaggerMiddleware()
};