import swaggerUi from 'swagger-ui-express';
import swaggerSpec from '../config/swagger';
import { logger } from './logger';
import { Express } from 'express';

export function setupSwagger(app: Express): void {
  try {
    // Serve API documentation
    app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
      explorer: true,
      customCss: '.swagger-ui .topbar { display: none }',
      customSiteTitle: 'Film Industry Time Tracking API Documentation'
    }));

    // Serve JSON spec
    app.get('/api-docs.json', (req, res) => {
      res.setHeader('Content-Type', 'application/json');
      res.send(swaggerSpec);
    });

    logger.info('📚 Swagger documentation initialized at /api-docs');
  } catch (error) {
    logger.error('Failed to initialize Swagger:', error);
  }
}