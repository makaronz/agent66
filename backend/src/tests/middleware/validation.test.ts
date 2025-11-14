import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { validateRequest } from '../../middleware/validation';

describe('Validation Middleware', () => {
  let mockRequest: Partial<Request>;
  let mockResponse: Partial<Response>;
  let mockNext: NextFunction;

  beforeEach(() => {
    mockRequest = {
      body: {},
      params: {},
      query: {}
    };
    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis()
    };
    mockNext = jest.fn();
  });

  describe('validateRequest', () => {
    it('should pass validation when request body is valid', () => {
      const schema = z.object({
        body: z.object({
          email: z.string().email(),
          password: z.string().min(6)
        })
      });

      mockRequest.body = {
        email: 'test@example.com',
        password: 'password123'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
      expect(mockNext).toHaveBeenCalledTimes(1);
    });

    it('should return 400 when request body is invalid', () => {
      const schema = z.object({
        body: z.object({
          email: z.string().email(),
          password: z.string().min(6)
        })
      });

      mockRequest.body = {
        email: 'invalid-email',
        password: '123'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          timestamp: expect.any(String),
          details: expect.objectContaining({
            body: expect.any(Array)
          })
        }
      });
      expect(mockNext).not.toHaveBeenCalled();
    });

    it('should validate request params', () => {
      const schema = z.object({
        params: z.object({
          id: z.string().uuid()
        })
      });

      mockRequest.params = {
        id: '550e8400-e29b-41d4-a716-446655440000'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should return 400 when request params are invalid', () => {
      const schema = z.object({
        params: z.object({
          id: z.string().uuid()
        })
      });

      mockRequest.params = {
        id: 'invalid-uuid'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          timestamp: expect.any(String),
          details: expect.objectContaining({
            params: expect.any(Array)
          })
        }
      });
    });

    it('should validate request query', () => {
      const schema = z.object({
        query: z.object({
          page: z.string().transform(Number).pipe(z.number().min(1)),
          limit: z.string().transform(Number).pipe(z.number().max(100))
        })
      });

      mockRequest.query = {
        page: '1',
        limit: '10'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should validate combined body, params, and query', () => {
      const schema = z.object({
        body: z.object({
          title: z.string().min(1),
          content: z.string().min(1)
        }),
        params: z.object({
          userId: z.string().uuid()
        }),
        query: z.object({
          draft: z.string().transform(Boolean).pipe(z.boolean())
        })
      });

      mockRequest.body = {
        title: 'Test Post',
        content: 'Test content'
      };
      mockRequest.params = {
        userId: '550e8400-e29b-41d4-a716-446655440000'
      };
      mockRequest.query = {
        draft: 'true'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should handle partial validation with optional fields', () => {
      const schema = z.object({
        body: z.object({
          title: z.string().min(1),
          content: z.string().optional(),
          published: z.boolean().optional().default(false)
        })
      });

      mockRequest.body = {
        title: 'Test Post'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
      expect(mockRequest.body.published).toBe(false);
    });

    it('should provide detailed validation error messages', () => {
      const schema = z.object({
        body: z.object({
          email: z.string().email('Must be a valid email address'),
          age: z.number().min(18, 'Must be at least 18 years old')
        })
      });

      mockRequest.body = {
        email: 'invalid-email',
        age: 16
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          timestamp: expect.any(String),
          details: expect.objectContaining({
            body: expect.arrayContaining([
              expect.objectContaining({
                message: 'Must be a valid email address'
              }),
              expect.objectContaining({
                message: 'Must be at least 18 years old'
              })
            ])
          })
        }
      });
    });

    it('should handle nested object validation', () => {
      const schema = z.object({
        body: z.object({
          user: z.object({
            name: z.string().min(1),
            contact: z.object({
              email: z.string().email(),
              phone: z.string().optional()
            })
          })
        })
      });

      mockRequest.body = {
        user: {
          name: 'John Doe',
          contact: {
            email: 'john@example.com',
            phone: '1234567890'
          }
        }
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should handle array validation', () => {
      const schema = z.object({
        body: z.object({
          tags: z.array(z.string()).min(1),
          scores: z.array(z.number().min(0).max(100))
        })
      });

      mockRequest.body = {
        tags: ['javascript', 'testing'],
        scores: [85, 92, 78]
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
    });

    it('should transform data during validation', () => {
      const schema = z.object({
        body: z.object({
          email: z.string().email().transform(val => val.toLowerCase()),
          age: z.string().transform(Number),
          active: z.string().transform(val => val === 'true')
        })
      });

      mockRequest.body = {
        email: 'Test@Example.COM',
        age: '25',
        active: 'true'
      };

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockNext).toHaveBeenCalledWith();
      expect(mockRequest.body.email).toBe('test@example.com');
      expect(mockRequest.body.age).toBe(25);
      expect(mockRequest.body.active).toBe(true);
    });

    it('should handle validation errors gracefully with missing fields', () => {
      const schema = z.object({
        body: z.object({
          required: z.string(),
          optional: z.string().optional()
        })
      });

      mockRequest.body = {};

      const middleware = validateRequest(schema);
      middleware(mockRequest as Request, mockResponse as Response, mockNext);

      expect(mockResponse.status).toHaveBeenCalledWith(400);
      expect(mockResponse.json).toHaveBeenCalledWith({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Validation failed',
          timestamp: expect.any(String),
          details: expect.objectContaining({
            body: expect.any(Array)
          })
        }
      });
    });
  });
});