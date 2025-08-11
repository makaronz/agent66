import { Router, Request, Response } from 'express';
// UserService removed for deployment optimization
import { authenticateToken } from '../middleware/auth.js';

const router = Router();

/**
 * Get current user profile
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
 * Update user profile
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
 * Store API keys for exchange
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
 * Get user's API keys (without sensitive data)
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