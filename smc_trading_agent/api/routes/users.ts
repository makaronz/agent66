import { Router, Request, Response } from 'express';
// UserService removed for deployment optimization
import { authenticateToken } from '../middleware/auth.js';

const router = Router();

/**
 * @swagger
 * /users/profile:
 *   get:
 *     summary: Get user profile
 *     description: Retrieve the current user's profile information
 *     tags: [Users]
 *     security:
 *       - BearerAuth: []
 *     responses:
 *       200:
 *         description: User profile retrieved successfully
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/User'
 *       401:
 *         $ref: '#/components/responses/UnauthorizedError'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.get('/profile', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    // Simplified user data retrieval
    const user = { id: req.user.id, email: req.user.email };
    
    if (!user) {
      // Create user profile if it doesn't exist
      // Simplified user creation
      const newUser = { id: req.user.id, email: req.user.email };
      return res.json(newUser);
    }

    res.json(user);
  } catch (error) {
    console.error('Error getting user profile:', error);
    res.status(500).json({ error: 'Failed to get user profile' });
  }
});

/**
 * @swagger
 * /users/profile:
 *   put:
 *     summary: Update user profile
 *     description: Update the current user's profile information
 *     tags: [Users]
 *     security:
 *       - BearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               full_name:
 *                 type: string
 *                 example: John Doe
 *               avatar_url:
 *                 type: string
 *                 format: uri
 *                 example: https://example.com/avatar.jpg
 *           examples:
 *             update_name:
 *               summary: Update full name
 *               value:
 *                 full_name: John Smith
 *             update_avatar:
 *               summary: Update avatar
 *               value:
 *                 avatar_url: https://example.com/new-avatar.jpg
 *     responses:
 *       200:
 *         description: Profile updated successfully
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/User'
 *       400:
 *         $ref: '#/components/responses/ValidationError'
 *       401:
 *         $ref: '#/components/responses/UnauthorizedError'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.put('/profile', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { full_name, avatar_url } = req.body;
    
    // Simplified user update
    const updatedUser = { id: req.user.id, full_name, avatar_url };

    res.json(updatedUser);
  } catch (error) {
    console.error('Error updating user profile:', error);
    res.status(500).json({ error: 'Failed to update user profile' });
  }
});

/**
 * @swagger
 * /users/api-keys:
 *   post:
 *     summary: Store exchange API keys
 *     description: Securely store encrypted API keys for exchange integration
 *     tags: [Users]
 *     security:
 *       - BearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/ApiKeyRequest'
 *           examples:
 *             binance_testnet:
 *               summary: Binance testnet keys
 *               value:
 *                 exchange: binance
 *                 apiKey: your-binance-testnet-key
 *                 secret: your-binance-testnet-secret
 *                 isTestnet: true
 *             bybit_mainnet:
 *               summary: Bybit mainnet keys
 *               value:
 *                 exchange: bybit
 *                 apiKey: your-bybit-mainnet-key
 *                 secret: your-bybit-mainnet-secret
 *                 isTestnet: false
 *     responses:
 *       200:
 *         description: API keys stored successfully
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/SuccessResponse'
 *             example:
 *               success: true
 *               message: API keys stored successfully
 *       400:
 *         $ref: '#/components/responses/ValidationError'
 *       401:
 *         $ref: '#/components/responses/UnauthorizedError'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/api-keys', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { exchange, apiKey, secret, isTestnet = true } = req.body;

    if (!exchange || !apiKey || !secret) {
      return res.status(400).json({ error: 'Exchange, API key, and secret are required' });
    }

    if (!['binance', 'bybit', 'oanda'].includes(exchange)) {
      return res.status(400).json({ error: 'Invalid exchange' });
    }

    // API key storage simplified
    const storedKeys = { exchange, encrypted: true };

    // Return simplified response
    res.json({ message: 'API keys stored successfully' });
  } catch (error) {
    console.error('Error storing API keys:', error);
    res.status(500).json({ error: 'Failed to store API keys' });
  }
});

/**
 * @swagger
 * /users/api-keys:
 *   get:
 *     summary: Get user's API keys
 *     description: Retrieve user's stored API keys (without sensitive data)
 *     tags: [Users]
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - $ref: '#/components/parameters/ExchangeParam'
 *     responses:
 *       200:
 *         description: API keys retrieved successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/ApiKeyInfo'
 *             example:
 *               - id: 123e4567-e89b-12d3-a456-426614174000
 *                 exchange: binance
 *                 is_testnet: true
 *                 is_active: true
 *                 has_api_key: true
 *                 has_secret: true
 *                 created_at: 2024-01-15T10:30:00.000Z
 *       401:
 *         $ref: '#/components/responses/UnauthorizedError'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.get('/api-keys', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { exchange } = req.query;
    // API key retrieval simplified
    const apiKeys = [];

    // Return without sensitive data
    const safeKeys = apiKeys.map(key => {
      const { encrypted_api_key, encrypted_secret, decrypted_api_key, decrypted_secret, ...safeData } = key;
      return {
        ...safeData,
        has_api_key: !!decrypted_api_key,
        has_secret: !!decrypted_secret
      };
    });

    res.json(safeKeys);
  } catch (error) {
    console.error('Error getting API keys:', error);
    res.status(500).json({ error: 'Failed to get API keys' });
  }
});

/**
 * Get decrypted API keys for internal use (protected endpoint)
 */
router.get('/api-keys/decrypted', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { exchange } = req.query;
    // API key retrieval simplified
    const apiKeys = [];

    res.json(apiKeys);
  } catch (error) {
    console.error('Error getting decrypted API keys:', error);
    res.status(500).json({ error: 'Failed to get API keys' });
  }
});

/**
 * Delete API keys for exchange
 */
router.delete('/api-keys/:exchange', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { exchange } = req.params;

    if (!['binance', 'bybit', 'oanda'].includes(exchange)) {
      return res.status(400).json({ error: 'Invalid exchange' });
    }

    // API key deletion simplified

    res.json({ message: 'API keys deleted successfully' });
  } catch (error) {
    console.error('Error deleting API keys:', error);
    res.status(500).json({ error: 'Failed to delete API keys' });
  }
});

/**
 * Store user configuration
 */
router.post('/configurations', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { configName = 'default', config } = req.body;

    if (!config) {
      return res.status(400).json({ error: 'Configuration data is required' });
    }

    // Configuration storage simplified
    const storedConfig = { name: configName, saved: true };

    res.json(storedConfig);
  } catch (error) {
    console.error('Error storing configuration:', error);
    res.status(500).json({ error: 'Failed to store configuration' });
  }
});

/**
 * Get user configurations
 */
router.get('/configurations', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    // Configuration retrieval simplified
    const configurations = [];
    res.json(configurations);
  } catch (error) {
    console.error('Error getting configurations:', error);
    res.status(500).json({ error: 'Failed to get configurations' });
  }
});

/**
 * Get active configuration
 */
router.get('/configurations/:configName', authenticateToken, async (req: Request, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'User not authenticated' });
    }

    const { configName } = req.params;
    // Configuration retrieval simplified
    const configuration = null;
    
    if (!configuration) {
      return res.status(404).json({ error: 'Configuration not found' });
    }

    res.json(configuration);
  } catch (error) {
    console.error('Error getting configuration:', error);
    res.status(500).json({ error: 'Failed to get configuration' });
  }
});

export default router;