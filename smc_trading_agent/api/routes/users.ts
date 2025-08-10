import { Router, Request, Response } from 'express';
import { UserService } from '../services/userService';
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

    const user = await UserService.getUserById(req.user.id);
    
    if (!user) {
      // Create user profile if it doesn't exist
      const newUser = await UserService.upsertUser({
        id: req.user.id,
        email: req.user.email || '',
        full_name: req.user.user_metadata?.full_name || null,
        avatar_url: req.user.user_metadata?.avatar_url || null
      });
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
    
    const updatedUser = await UserService.updateUser(req.user.id, {
      full_name,
      avatar_url
    });

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

    const storedKeys = await UserService.storeApiKeys(
      req.user.id,
      exchange,
      apiKey,
      secret,
      isTestnet
    );

    // Return without sensitive data
    const { encrypted_api_key, encrypted_secret, ...safeData } = storedKeys;
    res.json(safeData);
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
    const apiKeys = await UserService.getApiKeys(
      req.user.id,
      exchange as 'binance' | 'bybit' | 'oanda' | undefined
    );

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
    const apiKeys = await UserService.getApiKeys(
      req.user.id,
      exchange as 'binance' | 'bybit' | 'oanda' | undefined
    );

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

    await UserService.deleteApiKeys(
      req.user.id,
      exchange as 'binance' | 'bybit' | 'oanda'
    );

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

    const storedConfig = await UserService.storeConfiguration(
      req.user.id,
      configName,
      config
    );

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

    const configurations = await UserService.getConfigurations(req.user.id);
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
    const configuration = await UserService.getActiveConfiguration(req.user.id, configName);
    
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