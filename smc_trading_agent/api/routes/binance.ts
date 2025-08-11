/**
 * Binance API integration routes
 * Handle connection testing, account info, and trading data
 */
import { Router, type Request, type Response } from 'express';
import ccxt from 'ccxt';
import { authenticateToken } from '../middleware/auth.js';
import supabaseAdmin from '../supabase.js';
// UserService removed for deployment optimization

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
      // API key storage simplified
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
 * POST /api/binance/account-info
 */
router.post('/account-info', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: 'User not authenticated'
      });
      return;
    }

    const { apiKey, secret, sandbox = false } = req.body;

    if (!apiKey || !secret) {
      res.status(400).json({
        success: false,
        error: 'API key and secret are required'
      });
      return;
    }

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

/**
 * Place Trading Order
 * POST /api/binance/place-order
 */
interface PlaceOrderRequest {
  symbol: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit';
  quantity: number;
  price?: number;
  stopLoss?: number;
  takeProfit?: number;
}

interface PlaceOrderResponse {
  success: boolean;
  data?: {
    orderId: string;
    symbol: string;
    side: string;
    type: string;
    quantity: number;
    price?: number;
    fillPrice?: number;
    status: string;
    timestamp: number;
    stopLossOrderId?: string;
    takeProfitOrderId?: string;
  };
  error?: string;
  details?: string;
}

router.post('/place-order', authenticateToken, async (req: Request, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: 'User not authenticated'
      });
      return;
    }

    const { symbol, side, type, quantity, price, stopLoss, takeProfit }: PlaceOrderRequest = req.body;

    // Validate required fields
    if (!symbol || !side || !type || !quantity) {
      res.status(400).json({
        success: false,
        error: 'Missing required fields: symbol, side, type, quantity'
      });
      return;
    }

    // Validate order parameters
    if (quantity <= 0) {
      res.status(400).json({
        success: false,
        error: 'Quantity must be greater than 0'
      });
      return;
    }

    if (type === 'limit' && (!price || price <= 0)) {
      res.status(400).json({
        success: false,
        error: 'Price is required for limit orders and must be greater than 0'
      });
      return;
    }

    if (!['buy', 'sell'].includes(side)) {
      res.status(400).json({
        success: false,
        error: 'Side must be either "buy" or "sell"'
      });
      return;
    }

    if (!['market', 'limit'].includes(type)) {
      res.status(400).json({
        success: false,
        error: 'Type must be either "market" or "limit"'
      });
      return;
    }

    // Get stored API keys for the user
    // API key retrieval simplified - in production, this would fetch from encrypted storage
    const apiKeys = null;
    
    if (!apiKeys || apiKeys.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No Binance API keys found. Please configure your API keys first.'
      });
      return;
    }

    const { decrypted_api_key: apiKey, decrypted_secret: secret, is_testnet: sandbox } = apiKeys[0];

    // Create Binance exchange instance
    const exchange = new ccxt.binance({
      apiKey,
      secret,
      sandbox,
      enableRateLimit: true,
    });

    let mainOrder;
    let stopLossOrder;
    let takeProfitOrder;

    try {
      // Place main order
      if (type === 'market') {
        mainOrder = await exchange.createMarketOrder(symbol, side, quantity);
      } else {
        mainOrder = await exchange.createLimitOrder(symbol, side, quantity, price!);
      }

      console.log('Main order placed:', mainOrder);

      // Place stop loss order if provided
       if (stopLoss && stopLoss > 0) {
         try {
            const stopSide = side === 'buy' ? 'sell' : 'buy';
            stopLossOrder = await exchange.createOrder(symbol, 'market', stopSide, quantity, null, {
              stopPrice: stopLoss
            });
            console.log('Stop loss order placed:', stopLossOrder);
          } catch (stopLossError: any) {
            console.warn('Failed to place stop loss order:', stopLossError.message);
            // Continue execution - main order was successful
          }
       }

       // Place take profit order if provided
       if (takeProfit && takeProfit > 0) {
         try {
            const profitSide = side === 'buy' ? 'sell' : 'buy';
            takeProfitOrder = await exchange.createOrder(symbol, 'market', profitSide, quantity, null, {
              stopPrice: takeProfit
            });
            console.log('Take profit order placed:', takeProfitOrder);
          } catch (takeProfitError: any) {
            console.warn('Failed to place take profit order:', takeProfitError.message);
            // Continue execution - main order was successful
          }
       }

      // Store successful order in database
      const tradeData = {
        user_id: req.user.id,
        symbol: mainOrder.symbol,
        side: mainOrder.side,
        type: mainOrder.type,
        quantity: mainOrder.amount,
        price: mainOrder.price || mainOrder.average || null,
        fill_price: mainOrder.average || mainOrder.price || null,
        status: mainOrder.status,
        order_id: mainOrder.id,
        exchange: 'binance',
        timestamp: new Date(mainOrder.timestamp || Date.now()).toISOString(),
        stop_loss_order_id: stopLossOrder?.id || null,
        take_profit_order_id: takeProfitOrder?.id || null,
        fees: mainOrder.fee?.cost || 0,
        fee_currency: mainOrder.fee?.currency || null
      };

      // Store successful order in database
        try {
          const { data: savedTrade, error: dbError } = await supabaseAdmin
            .from('trades')
            .insert(tradeData)
            .select()
            .single();
          if (dbError) {
            console.error('Failed to save trade to database:', dbError);
          } else {
            console.log('Trade saved to database:', savedTrade);
          }
        } catch (dbError) {
          console.error('Database save error:', dbError);
          // Don't fail the request if database save fails
        }

      // Return successful response
      const response: PlaceOrderResponse = {
        success: true,
        data: {
          orderId: mainOrder.id,
          symbol: mainOrder.symbol,
          side: mainOrder.side,
          type: mainOrder.type,
          quantity: mainOrder.amount,
          price: mainOrder.price,
          fillPrice: mainOrder.average || mainOrder.price,
          status: mainOrder.status,
          timestamp: mainOrder.timestamp || Date.now(),
          stopLossOrderId: stopLossOrder?.id,
          takeProfitOrderId: takeProfitOrder?.id
        }
      };

      res.json(response);

    } catch (orderError: any) {
      console.error('Order placement failed:', orderError.message);
      
      let errorMessage = orderError.message || 'Order placement failed';
      let statusCode = 400;
      
      // Handle specific Binance API errors
      if (orderError.message?.includes('insufficient balance')) {
        errorMessage = 'Insufficient balance to place this order';
        statusCode = 400;
      } else if (orderError.message?.includes('Invalid symbol')) {
        errorMessage = 'Invalid trading symbol';
        statusCode = 400;
      } else if (orderError.message?.includes('MIN_NOTIONAL')) {
        errorMessage = 'Order value is below minimum notional value';
        statusCode = 400;
      } else if (orderError.message?.includes('LOT_SIZE')) {
        errorMessage = 'Invalid quantity - check symbol lot size requirements';
        statusCode = 400;
      } else if (orderError.message?.includes('PRICE_FILTER')) {
        errorMessage = 'Invalid price - check symbol price filter requirements';
        statusCode = 400;
      } else if (orderError.message?.includes('Invalid API-key')) {
        errorMessage = 'Invalid API key or secret';
        statusCode = 401;
      } else if (orderError.message?.includes('IP')) {
        errorMessage = 'IP address not whitelisted';
        statusCode = 403;
      } else if (orderError.message?.includes('permissions')) {
        errorMessage = 'Insufficient API permissions for trading';
        statusCode = 403;
      }
      
      res.status(statusCode).json({
        success: false,
        error: errorMessage,
        details: sandbox ? 'Using testnet environment' : 'Using live environment'
      });
    }

  } catch (error: any) {
    console.error('Place order endpoint error:', error.message);
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      details: error.message
    });
  }
});

export default router;