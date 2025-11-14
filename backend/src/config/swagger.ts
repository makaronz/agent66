import swaggerJsdoc from 'swagger-jsdoc';

const options: swaggerJsdoc.Options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Film Industry Time Tracking API',
      version: '2.0.0',
      description: `## Film Industry Time Tracking System API

This comprehensive API provides endpoints for managing time tracking, projects, crew members, and authentication in the film industry.

### Features
- **Authentication & Authorization**: JWT-based secure authentication
- **Time Entry Management**: Create, read, update, and delete time entries
- **Project Management**: Manage film productions and post-production projects
- **Crew Management**: Handle cast and crew member information
- **Real-time Updates**: WebSocket support for live collaboration
- **Advanced Analytics**: Comprehensive metrics and reporting

### Authentication
Most endpoints require JWT authentication. Include the token in the Authorization header:
\`Authorization: Bearer <your-jwt-token>\`

### Rate Limiting
API requests are rate-limited to prevent abuse:
- **Standard endpoints**: 100 requests per minute
- **Upload endpoints**: 10 requests per minute
- **Analytics endpoints**: 50 requests per minute

### Error Handling
The API uses standard HTTP status codes:
- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **429**: Too Many Requests
- **500**: Internal Server Error`,
      contact: {
        name: 'API Support',
        email: 'support@filmtracker.com',
        url: 'https://docs.filmtracker.com'
      },
      license: {
        name: 'MIT',
        url: 'https://opensource.org/licenses/MIT'
      }
    },
    servers: [
      {
        url: 'https://api.filmtracker.com/v2',
        description: 'Production server'
      },
      {
        url: 'https://staging-api.filmtracker.com/v2',
        description: 'Staging server'
      },
      {
        url: 'http://localhost:3002/v2',
        description: 'Development server'
      }
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
          description: 'JWT authentication token'
        }
      },
      schemas: {
        User: {
          type: 'object',
          required: ['id', 'email', 'firstName', 'lastName', 'role'],
          properties: {
            id: {
              type: 'string',
              format: 'uuid',
              description: 'Unique user identifier'
            },
            email: {
              type: 'string',
              format: 'email',
              description: 'User email address'
            },
            firstName: {
              type: 'string',
              description: 'User first name'
            },
            lastName: {
              type: 'string',
              description: 'User last name'
            },
            role: {
              type: 'string',
              enum: ['admin', 'producer', 'director', 'crew', 'viewer'],
              description: 'User role in the system'
            },
            department: {
              type: 'string',
              enum: ['production', 'post-production', 'vfx', 'sound', 'camera', 'art'],
              description: 'Department affiliation'
            },
            isActive: {
              type: 'boolean',
              description: 'Whether the user account is active'
            },
            createdAt: {
              type: 'string',
              format: 'date-time',
              description: 'Account creation timestamp'
            },
            updatedAt: {
              type: 'string',
              format: 'date-time',
              description: 'Last update timestamp'
            }
          }
        },
        Project: {
          type: 'object',
          required: ['id', 'name', 'status', 'startDate'],
          properties: {
            id: {
              type: 'string',
              format: 'uuid',
              description: 'Unique project identifier'
            },
            name: {
              type: 'string',
              description: 'Project name'
            },
            description: {
              type: 'string',
              description: 'Project description'
            },
            status: {
              type: 'string',
              enum: ['pre-production', 'active', 'post-production', 'completed', 'cancelled'],
              description: 'Current project status'
            },
            projectType: {
              type: 'string',
              enum: ['feature', 'short', 'documentary', 'commercial', 'music_video', 'tv_series'],
              description: 'Type of production'
            },
            department: {
              type: 'string',
              enum: ['production', 'post-production', 'vfx', 'sound', 'camera', 'art'],
              description: 'Primary department responsible'
            },
            startDate: {
              type: 'string',
              format: 'date',
              description: 'Project start date'
            },
            endDate: {
              type: 'string',
              format: 'date',
              description: 'Expected project end date'
            },
            budget: {
              type: 'number',
              description: 'Project budget in USD'
            },
            createdAt: {
              type: 'string',
              format: 'date-time',
              description: 'Project creation timestamp'
            },
            updatedAt: {
              type: 'string',
              format: 'date-time',
              description: 'Last update timestamp'
            }
          }
        },
        TimeEntry: {
          type: 'object',
          required: ['id', 'userId', 'projectId', 'startTime', 'endTime'],
          properties: {
            id: {
              type: 'string',
              format: 'uuid',
              description: 'Unique time entry identifier'
            },
            userId: {
              type: 'string',
              format: 'uuid',
              description: 'User ID who created the entry'
            },
            projectId: {
              type: 'string',
              format: 'uuid',
              description: 'Project ID for the time entry'
            },
            activityType: {
              type: 'string',
              enum: ['filming', 'editing', 'vfx', 'sound', 'meeting', 'prep', 'wrap', 'other'],
              description: 'Type of activity performed'
            },
            description: {
              type: 'string',
              description: 'Description of the work performed'
            },
            startTime: {
              type: 'string',
              format: 'date-time',
              description: 'Work start time'
            },
            endTime: {
              type: 'string',
              format: 'date-time',
              description: 'Work end time'
            },
            duration: {
              type: 'number',
              description: 'Duration in hours'
            },
            location: {
              type: 'string',
              description: 'Location where work was performed'
            },
            equipment: {
              type: 'array',
              items: {
                type: 'string'
              },
              description: 'Equipment used during the work'
            },
            overtime: {
              type: 'boolean',
              description: 'Whether this entry counts as overtime'
            },
            approved: {
              type: 'boolean',
              description: 'Whether the entry has been approved'
            },
            approvedBy: {
              type: 'string',
              format: 'uuid',
              description: 'User ID who approved the entry'
            },
            createdAt: {
              type: 'string',
              format: 'date-time',
              description: 'Entry creation timestamp'
            },
            updatedAt: {
              type: 'string',
              format: 'date-time',
              description: 'Last update timestamp'
            }
          }
        },
        ErrorResponse: {
          type: 'object',
          required: ['error'],
          properties: {
            error: {
              type: 'string',
              description: 'Error message'
            },
            code: {
              type: 'string',
              description: 'Error code for programmatic handling'
            },
            details: {
              type: 'object',
              description: 'Additional error details'
            },
            timestamp: {
              type: 'string',
              format: 'date-time',
              description: 'Error timestamp'
            },
            requestId: {
              type: 'string',
              description: 'Request ID for tracking'
            }
          }
        },
        MetricsResponse: {
          type: 'object',
          properties: {
            totalUsers: {
              type: 'number',
              description: 'Total number of users'
            },
            activeUsers: {
              type: 'number',
              description: 'Currently active users'
            },
            totalProjects: {
              type: 'number',
              description: 'Total number of projects'
            },
            activeProjects: {
              type: 'number',
              description: 'Currently active projects'
            },
            totalTimeEntries: {
              type: 'number',
              description: 'Total time entries'
            },
            averageWorkHours: {
              type: 'number',
              description: 'Average work hours per user'
            },
            departmentBreakdown: {
              type: 'object',
              description: 'User breakdown by department'
            }
          }
        }
      }
    }
  },
  apis: [
    './src/routes/*.ts',
    './src/models/*.ts',
    './src/middleware/*.ts'
  ]
};

const swaggerSpec = swaggerJsdoc(options);

export default swaggerSpec;