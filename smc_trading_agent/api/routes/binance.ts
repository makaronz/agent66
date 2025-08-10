/**
 * Binance API integration routes
 * Handle connection testing, account info, and trading data
 */
import { Router, type Request, type Response } from 'express';
import ccxt from 'ccxt';
import { authenticateToken } from '../middleware/auth.js';
import { UserService } from '../services/userService';

const router = Router();

/**
 * Test Binance API Connection
 * POST /api/binance/test-connection
 */
router.post('/test-connection', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: 'User not authenticated'
      });
      return;
    }

    const { apiKey, secret, sandbox = false, saveKeys = false } = req.body;

    if (!apiKey || !secret) {
      res.status(400).json({
        success: false,
        error: 'API key and secret are required'
      });
      return;
    }

    // Save API keys if requested
    if (saveKeys) {
      await UserService.storeApiKeys(req.user.id, 'binance', apiKey, secret, sandbox);
    }

    // Create Binance exchange instance
    const exchange = new ccxt.binance({
      apiKey,
      secret,
      sandbox, // Use testnet by default
      enableRateLimit: true,
    });

    // Test connection by fetching exchange status
    const status = await exchange.fetchStatus();
    
    // Test API permissions by trying to fetch balance (this will fail if keys are invalid)
    await exchange.fetchBalance();

    res.json({
      success: true,
      message: 'Connection successful',
      data: {
        exchange: 'Binance',
        status: status.status,
        updated: status.updated,
        sandbox: sandbox
      }
    });
  } catch (error: any) {
    console.error('Binance connection test failed:', error.message);
    
    let errorMessage = error.message || 'Connection test failed';
    let statusCode = 400;
    
    // Handle specific Binance API errors
    if (error.message?.includes('Invalid API-key')) {
      errorMessage = 'Invalid API key or secret. Please check your credentials.';
      statusCode = 401;
    } else if (error.message?.includes('IP')) {
      errorMessage = 'IP address not whitelisted. Please add your IP to Binance API settings.';
      statusCode = 403;
    } else if (error.message?.includes('permissions')) {
      errorMessage = 'Insufficient API permissions. Please enable spot trading permissions.';
      statusCode = 403;
    } else if (error.message?.includes('testnet') || error.message?.includes('sandbox')) {
      errorMessage = 'Testnet not available for this endpoint. Using live environment.';
      statusCode = 400;
    }
    
    res.status(statusCode).json({
      success: false,
      error: errorMessage,
      details: req.body.sandbox ? 'Using testnet environment' : 'Using live environment',
      code: error.code || 'UNKNOWN_ERROR'
    });
  }
});

/**
 * Get Binance Account Information
 * GET /api/binance/account-info
 */
router.get('/account-info', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: 'User not authenticated'
      });
      return;
    }

    // Get stored API keys for the user
    const apiKeys = await UserService.getApiKeys(req.user.id, 'binance');
    
    if (!apiKeys || apiKeys.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No Binance API keys found. Please configure your API keys first.'
      });
      return;
    }

    const { decrypted_api_key: apiKey, decrypted_secret: secret, is_testnet: sandbox } = apiKeys[0];

    const exchange = new ccxt.binance({
      apiKey,
      secret,
      sandbox,
      enableRateLimit: true,
    });

    // Fetch account balance
    const balance = await exchange.fetchBalance();
    
    // Get trading fees
    const tradingFees = await exchange.fetchTradingFees();

    // Filter out zero balances for cleaner response
    const nonZeroBalances = Object.entries(balance.total)
      .filter(([_, amount]) => (amount as number) > 0)
      .reduce((acc, [currency, amount]) => {
        acc[currency] = {
          total: amount,
          free: balance.free[currency] || 0,
          used: balance.used[currency] || 0
        };
        return acc;
      }, {} as Record<string, any>);

    res.json({
      success: true,
      data: {
        balances: nonZeroBalances,
        tradingFees: {
          maker: tradingFees.maker,
          taker: tradingFees.taker
        },
        accountType: sandbox ? 'Testnet' : 'Live',
        timestamp: Date.now()
      }
    });
  } catch (error: any) {
    console.error('Failed to fetch account info:', error.message);
    
    let errorMessage = error.message || 'Failed to fetch account information';
    let statusCode = 400;
    
    // Handle specific Binance API errors
    if (error.message?.includes('Invalid API-key')) {
      errorMessage = 'Invalid API key or secret. Please check your credentials.';
      statusCode = 401;
    } else if (error.message?.includes('IP')) {
      errorMessage = 'IP address not whitelisted. Please add your IP to Binance API settings.';
      statusCode = 403;
    } else if (error.message?.includes('permissions')) {
      errorMessage = 'Insufficient API permissions. Please enable spot trading permissions.';
      statusCode = 403;
    }
    
    res.status(statusCode).json({
      success: false,
      error: errorMessage,
      details: req.body.sandbox ? 'Using testnet environment' : 'Using live environment',
      code: error.code || 'UNKNOWN_ERROR'
    });
  }
});

/**
 * Get Market Data
 * GET /api/binance/market-data/:symbol
 */
router.get('/market-data/:symbol', async (req: Request, res: Response): Promise<void> => {
  try {
    const { symbol } = req.params;
    const { sandbox = false } = req.query;

    const exchange = new ccxt.binance({
      sandbox: sandbox === 'true',
      enableRateLimit: true,
    });

    // Fetch ticker data
    const ticker = await exchange.fetchTicker(symbol);
    
    // Fetch recent trades
    const trades = await exchange.fetchTrades(symbol, undefined, 10);

    res.json({
      success: true,
      data: {
        symbol,
        price: ticker.last,
        bid: ticker.bid,
        ask: ticker.ask,
        volume: ticker.baseVolume,
        change: ticker.change,
        percentage: ticker.percentage,
        high: ticker.high,
        low: ticker.low,
        recentTrades: trades.slice(0, 5).map(trade => ({
          price: trade.price,
          amount: trade.amount,
          side: trade.side,
          timestamp: trade.timestamp
        }))
      }
    });
  } catch (error: any) {
    console.error('Failed to fetch market data:', error.message);
    res.status(400).json({
      success: false,
      error: error.message || 'Failed to fetch market data'
    });
  }
});

export default router;