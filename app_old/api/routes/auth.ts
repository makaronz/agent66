/**
 * @swagger
 * components:
 *   schemas:
 *     AuthUser:
 *       type: object
 *       properties:
 *         id:
 *           type: integer
 *           example: 1
 *         email:
 *           type: string
 *           format: email
 *           example: trader@example.com
 *         name:
 *           type: string
 *           example: SMC Trader
 */

/**
 * User authentication API routes
 * Handle user registration, login, token management, etc.
 */
import { Router, type Request, type Response } from 'express';


const router = Router();

/**
 * @swagger
 * /auth/register:
 *   post:
 *     summary: Register a new user
 *     description: Create a new user account with email and password
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/RegisterRequest'
 *           examples:
 *             newUser:
 *               summary: New user registration
 *               value:
 *                 email: newuser@example.com
 *                 password: SecurePassword123!
 *                 full_name: Jane Smith
 *     responses:
 *       200:
 *         description: User registered successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 message:
 *                   type: string
 *                   example: User registered successfully
 *                 user:
 *                   $ref: '#/components/schemas/AuthUser'
 *             examples:
 *               success:
 *                 summary: Successful registration
 *                 value:
 *                   success: true
 *                   message: User registered successfully
 *                   user:
 *                     id: 2
 *                     email: newuser@example.com
 *       400:
 *         $ref: '#/components/responses/ValidationError'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/register', async (req: Request, res: Response): Promise<void> => {
  try {
    // Mock register logic
    res.json({
      success: true,
      message: 'User registered successfully',
      user: { id: 2, email: req.body.email || 'newuser@example.com' }
    });
  } catch {
    res.status(500).json({ error: 'Registration failed' });
  }
});

/**
 * @swagger
 * /auth/login:
 *   post:
 *     summary: User login
 *     description: Authenticate user with email and password, returns JWT token
 *     tags: [Authentication]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/LoginRequest'
 *           examples:
 *             trader:
 *               summary: Trader login
 *               value:
 *                 email: trader@example.com
 *                 password: SecurePassword123!
 *     responses:
 *       200:
 *         description: Login successful
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/LoginResponse'
 *             examples:
 *               success:
 *                 summary: Successful login
 *                 value:
 *                   success: true
 *                   token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
 *                   user:
 *                     id: 1
 *                     email: trader@example.com
 *                   expires_in: 3600
 *       400:
 *         $ref: '#/components/responses/ValidationError'
 *       401:
 *         description: Invalid credentials
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ErrorResponse'
 *             example:
 *               success: false
 *               error: Invalid email or password
 *               code: INVALID_CREDENTIALS
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/login', async (req: Request, res: Response): Promise<void> => {
  try {
    // Mock login logic
    res.json({
      success: true,
      token: 'mock-jwt-token',
      user: { id: 1, email: 'trader@example.com' }
    });
  } catch {
    res.status(500).json({ error: 'Login failed' });
  }
});

/**
 * @swagger
 * /auth/logout:
 *   post:
 *     summary: User logout
 *     description: Invalidate user session and JWT token
 *     tags: [Authentication]
 *     security:
 *       - BearerAuth: []
 *     responses:
 *       200:
 *         description: Logout successful
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/SuccessResponse'
 *             example:
 *               success: true
 *               message: Logged out successfully
 *       401:
 *         $ref: '#/components/responses/UnauthorizedError'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/logout', async (req: Request, res: Response): Promise<void> => {
  try {
    // Mock logout logic
    res.json({ success: true });
  } catch {
    res.status(500).json({ error: 'Logout failed' });
  }
});

/**
 * @swagger
 * /auth/me:
 *   get:
 *     summary: Get current user information
 *     description: Retrieve authenticated user's profile information
 *     tags: [Authentication]
 *     security:
 *       - BearerAuth: []
 *     responses:
 *       200:
 *         description: User information retrieved successfully
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/AuthUser'
 *             example:
 *               id: 1
 *               email: trader@example.com
 *               name: SMC Trader
 *       401:
 *         $ref: '#/components/responses/UnauthorizedError'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.get('/me', async (req: Request, res: Response): Promise<void> => {
  try {
    // Mock user info
    res.json({
      id: 1,
      email: 'trader@example.com',
      name: 'SMC Trader'
    });
  } catch {
    res.status(500).json({ error: 'Failed to get user info' });
  }
});

export default router;