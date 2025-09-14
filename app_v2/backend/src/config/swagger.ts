import swaggerJsdoc from 'swagger-jsdoc';

const options: swaggerJsdoc.Options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Trading App API',
      version: '1.0.0',
      description: 'API documentation for the Trading App',
    },
    servers: [
      {
        url: 'http://localhost:5000/api',
        description: 'Development server',
      },
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        },
      },
    },
    // Remove global security to fix initialization error
    // security: [
    //   {
    //     bearerAuth: [],
    //   },
    // ],
  },
  apis: ['./src/**/*.ts'], // Change to recursive pattern to find all route files
};

const swaggerSpec = swaggerJsdoc(options);

export default swaggerSpec;