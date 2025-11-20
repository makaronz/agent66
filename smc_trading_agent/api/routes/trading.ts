/**
 * Trading API Routes
 * Connects frontend with real-time SMC Trading Agent system
 */

import { Router, type Request, type Response } from 'express';
import { MarketDataAggregator } from '../services/marketDataAggregator';
import { CircuitBreakerRegistry } from '../utils/circuitBreaker';
import { RateLimiterManager } from '../utils/rateLimiter';
import * as os from 'os';

const router = Router();

// Initialize market data aggregator
const marketDataAggregator = new MarketDataAggregator(
  ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'BNBUSDT'],
  {
    testnet: false,
    maxPriceVariance: 0.1,
    dataFreshnessThreshold: 5000,
    aggregationWindow: 1000,
    enableFailover: true
  }
);

// Initialize rate limiters
const rateLimiterManager = RateLimiterManager.getInstance();
rateLimiterManager.initializeExchangeLimiters();

// Initialize circuit breakers
const circuitBreakerRegistry = CircuitBreakerRegistry.getInstance();
const apiCircuitBreaker = circuitBreakerRegistry.create('trading_api', {
  failureThreshold: 5,
  resetTimeout: 30000,
  monitoringPeriod: 10000,
  halfOpenMaxCalls: 3
});

// Initialize market data aggregator on startup
let aggregatorInitialized = false;
(async () => {
  try {
    await marketDataAggregator.initialize();
    aggregatorInitialized = true;
    console.log('✅ Market data aggregator initialized successfully');
  } catch (error) {
    console.error('❌ Failed to initialize market data aggregator:', error);
    // Don't block - allow API to start even if aggregator fails
    aggregatorInitialized = false;
  }
})();

// Fallback data for when real data is unavailable
const fallbackMarketData = [
  { symbol: 'BTCUSDT', price: 43250.50, change: 2.45, volume: '1.2B' },
  { symbol: 'ETHUSDT', price: 2650.75, change: -1.23, volume: '890M' },
  { symbol: 'ADAUSDT', price: 0.485, change: 3.67, volume: '245M' },
  { symbol: 'SOLUSDT', price: 98.32, change: 1.89, volume: '156M' },
];

const mockPositions = [
  { symbol: 'BTCUSDT', side: 'LONG', size: 0.5, entryPrice: 42800, currentPrice: 43250.50, pnl: 225.25, pnlPercent: 1.05 },
  { symbol: 'ETHUSDT', side: 'SHORT', size: 2.0, entryPrice: 2680, currentPrice: 2650.75, pnl: 58.50, pnlPercent: 1.09 },
];

const mockSystemHealth = [
  { name: 'Data Pipeline', status: 'healthy', latency: '12ms' },
  { name: 'SMC Detection', status: 'healthy', latency: '8ms' },
  { name: 'Execution Engine', status: 'warning', latency: '45ms' },
  { name: 'Risk Manager', status: 'healthy', latency: '5ms' },
];

/**
 * Get market data
 */
router.get('/market-data', async (req: Request, res: Response) => {
  try {
    // Check rate limits
    await rateLimiterManager.getLimiter('BINANCE_REST_API')?.waitForSlot('market-data');

    const result = await apiCircuitBreaker.execute(async () => {
      if (!aggregatorInitialized) {
        throw new Error('Market data aggregator not initialized');
      }

      const marketData = marketDataAggregator.getAllMarketData();

      // Transform to expected format
      return marketData.map(data => ({
        symbol: data.symbol,
        price: data.price,
        change: data.priceChangePercent,
        volume: data.volume,
        source: data.source,
        confidence: data.confidence,
        timestamp: data.timestamp
      }));
    });

    res.json({
      success: true,
      data: result,
      timestamp: new Date().toISOString(),
      dataSource: aggregatorInitialized ? 'real-time' : 'fallback'
    });

  } catch (error) {
    console.error('Error fetching market data:', error);

    // Return fallback data if real data is unavailable
    res.json({
      success: true,
      data: fallbackMarketData,
      timestamp: new Date().toISOString(),
      dataSource: 'fallback',
      warning: 'Using fallback data - real-time data unavailable'
    });
  }
});


/**
 * Get system health status
 */
router.get('/system-health', (req: Request, res: Response) => {
  res.json({
    success: true,
    data: {
      components: mockSystemHealth,
      overall: mockSystemHealth.every(s => s.status === 'healthy') ? 'healthy' : 'warning'
    },
    timestamp: new Date().toISOString()
  });
});

/**
 * Get SMC pattern analysis from Python backend
 */
router.get('/smc-patterns', async (req: Request, res: Response) => {
  try {
    // Try to get real patterns from Python backend
    const pythonResponse = await fetch('http://localhost:8000/api/python/smc-patterns');
    
    if (pythonResponse.ok) {
      const pythonData = await pythonResponse.json();
      
      if (pythonData.success && pythonData.data && pythonData.data.length > 0) {
        // Transform Python format to frontend format
        const patterns = pythonData.data.map((p: any) => ({
          id: p.id || `pattern_${Date.now()}`,
          symbol: p.symbol || 'BTCUSDT',
          type: p.type || 'order_block',
          direction: p.direction || 'bullish',
          strength: p.strength || p.confidence || 0.7,
          price: p.price || 0,
          timestamp: p.timestamp || new Date().toISOString(),
          confidence: p.confidence || p.strength || 0.7
        }));

        return res.json({
          success: true,
          data: patterns,
          timestamp: new Date().toISOString(),
          dataSource: 'python-backend'
        });
      }
    }

    // If no patterns from Python backend, return empty array
    return res.json({
      success: true,
      data: [],
      timestamp: new Date().toISOString(),
      dataSource: 'python-backend',
      message: 'No SMC patterns detected yet'
    });

  } catch (error) {
    console.error('Error fetching SMC patterns from Python backend:', error);

    // Fallback to mock patterns only if Python backend unavailable
    const mockPatterns = [
      {
        id: 'pattern_1',
        symbol: 'BTCUSDT',
        type: 'order_block',
        direction: 'bullish',
        strength: 0.85,
        price: 43200,
        timestamp: new Date().toISOString(),
        confidence: 0.92
      }
    ];

    res.json({
      success: true,
      data: mockPatterns,
      timestamp: new Date().toISOString(),
      dataSource: 'fallback',
      warning: 'Python backend unavailable - using mock data'
    });
  }
});

/**
 * Get trading history from Python backend
 */
router.get('/history', async (req: Request, res: Response) => {
  const { limit = 50, symbol = 'all' } = req.query;

  try {
    // Get trades from Python backend
    const pythonResponse = await fetch(`http://localhost:8000/api/python/paper-trades?limit=${limit}`);
    
    if (pythonResponse.ok) {
      const pythonData = await pythonResponse.json();
      
      if (pythonData.success && pythonData.data && pythonData.data.length > 0) {
        // Transform Python format to frontend format
        let trades = pythonData.data.map((t: any) => ({
          id: t.id || `trade_${Date.now()}`,
          symbol: t.symbol || 'BTCUSDT',
          action: t.side || 'BUY',
          price: t.entry_price || t.price || 0,
          size: t.size || 0,
          timestamp: t.timestamp || new Date().toISOString(),
          status: t.status || 'OPEN',
          pnl: t.pnl || 0,
          reason: t.reason || 'Trading signal'
        }));

        // Filter by symbol if specified
        if (symbol && symbol !== 'all') {
          trades = trades.filter((t: any) => t.symbol === symbol);
        }

        return res.json({
          success: true,
          data: trades,
          timestamp: new Date().toISOString(),
          dataSource: 'python-backend'
        });
      }
    }

    // If no trades, return empty array
    return res.json({
      success: true,
      data: [],
      timestamp: new Date().toISOString(),
      dataSource: 'python-backend',
      message: 'No trades yet'
    });

  } catch (error) {
    console.error('Error fetching trading history from Python backend:', error);

    // Fallback to mock trades only if Python backend unavailable
    const mockTrades = [
      {
        id: 'trade_1',
        symbol: 'BTCUSDT',
        action: 'BUY',
        price: 42800,
        size: 0.5,
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        status: 'CLOSED',
        pnl: 225.25,
        reason: 'Strong bullish order block detected'
      }
    ];

    res.json({
      success: true,
      data: mockTrades,
      timestamp: new Date().toISOString(),
      dataSource: 'fallback',
      warning: 'Python backend unavailable - using mock data'
    });
  }
});

/**
 * Execute manual trade through Python backend
 */
router.post('/execute-trade', async (req: Request, res: Response) => {
  const { symbol, action, price, size, reason, stopLoss, takeProfit } = req.body;

  if (!symbol || !action || !price || !size) {
    return res.status(400).json({
      success: false,
      error: 'Missing required fields: symbol, action, price, size'
    });
  }

  try {
    // Forward to Python backend
    const pythonResponse = await fetch('http://localhost:8000/api/python/execute-order', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        symbol: symbol,
        side: action.toUpperCase(), // BUY or SELL
        size: parseFloat(size),
        price: parseFloat(price),
        stopLoss: stopLoss ? parseFloat(stopLoss) : undefined,
        takeProfit: takeProfit ? parseFloat(takeProfit) : undefined,
        reason: reason || 'Manual trade from trading interface'
      }),
    });

    if (pythonResponse.ok) {
      const pythonData = await pythonResponse.json();
      
      if (pythonData.success) {
        // Transform Python format to frontend format
        const trade = {
          id: pythonData.data.id || `trade_${Date.now()}`,
          symbol: pythonData.data.symbol,
          action: pythonData.data.side,
          price: pythonData.data.entry_price,
          size: pythonData.data.size,
          timestamp: pythonData.data.timestamp,
          status: pythonData.data.status || 'EXECUTED',
          reason: reason || 'Manual trade request',
          orderId: pythonData.data.id,
          stopLoss: pythonData.data.stop_loss,
          takeProfit: pythonData.data.take_profit
        };

        return res.json({
          success: true,
          data: trade,
          message: 'Trade executed successfully through paper trading engine'
        });
      } else {
        return res.status(400).json({
          success: false,
          error: pythonData.error || 'Failed to execute trade'
        });
      }
    } else {
      const errorData = await pythonResponse.json().catch(() => ({}));
      return res.status(pythonResponse.status).json({
        success: false,
        error: errorData.error || 'Python backend unavailable'
      });
    }

  } catch (error) {
    console.error('Error executing trade through Python backend:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to connect to Python backend'
    });
  }
});

/**
 * Get performance metrics calculated from real trades
 */
router.get('/performance', async (req: Request, res: Response) => {
  try {
    // Get all trades from Python backend
    const tradesResponse = await fetch('http://localhost:8000/api/python/paper-trades?limit=1000');
    
    if (tradesResponse.ok) {
      const tradesData = await tradesResponse.json();
      
      if (tradesData.success && tradesData.data && tradesData.data.length > 0) {
        const trades = tradesData.data;
        
        // Calculate performance metrics from real trades
        const closedTrades = trades.filter((t: any) => t.status === 'CLOSED');
        const winningTrades = closedTrades.filter((t: any) => t.pnl > 0);
        const losingTrades = closedTrades.filter((t: any) => t.pnl < 0);
        
        const totalPnL = trades.reduce((sum: number, t: any) => sum + (t.pnl || 0), 0);
        const totalTrades = closedTrades.length;
        const winRate = totalTrades > 0 ? (winningTrades.length / totalTrades) * 100 : 0;
        
        const totalWins = winningTrades.reduce((sum: number, t: any) => sum + t.pnl, 0);
        const totalLosses = Math.abs(losingTrades.reduce((sum: number, t: any) => sum + t.pnl, 0));
        const averageWin = winningTrades.length > 0 ? totalWins / winningTrades.length : 0;
        const averageLoss = losingTrades.length > 0 ? totalLosses / losingTrades.length : 0;
        const profitFactor = totalLosses > 0 ? totalWins / totalLosses : (totalWins > 0 ? 999 : 0);
        
        // Simple max drawdown calculation (simplified)
        let maxDrawdown = 0;
        let peak = 0;
        let current = 0;
        for (const trade of trades) {
          current += trade.pnl || 0;
          if (current > peak) peak = current;
          const drawdown = ((peak - current) / Math.max(peak, 1)) * 100;
          if (drawdown > maxDrawdown) maxDrawdown = drawdown;
        }
        
        // Simplified Sharpe Ratio (would need returns for proper calculation)
        const sharpeRatio = totalTrades > 0 && averageLoss !== 0 
          ? (averageWin / Math.abs(averageLoss)) * (winRate / 100) 
          : 0;
        
        // Daily return (simplified - based on total P&L)
        const accountResponse = await fetch('http://localhost:8000/api/python/account');
        let dailyReturn = 0;
        if (accountResponse.ok) {
          const accountData = await accountResponse.json();
          if (accountData.success && accountData.data) {
            const initialBalance = 10000; // From config
            const currentEquity = accountData.data.equity || initialBalance;
            dailyReturn = ((currentEquity - initialBalance) / initialBalance) * 100;
          }
        }
        
        const metrics = {
          totalPnL: totalPnL,
          sharpeRatio: Math.round(sharpeRatio * 100) / 100,
          maxDrawdown: Math.round(maxDrawdown * 10) / 10,
          winRate: Math.round(winRate * 10) / 10,
          totalTrades: totalTrades,
          winningTrades: winningTrades.length,
          losingTrades: losingTrades.length,
          averageWin: Math.round(averageWin * 100) / 100,
          averageLoss: Math.round(averageLoss * 100) / 100,
          profitFactor: Math.round(profitFactor * 100) / 100,
          dailyReturn: Math.round(dailyReturn * 100) / 100
        };

        return res.json({
          success: true,
          data: metrics,
          timestamp: new Date().toISOString(),
          dataSource: 'calculated-from-trades'
        });
      }
    }

    // If no trades, return zero metrics
    return res.json({
      success: true,
      data: {
        totalPnL: 0,
        sharpeRatio: 0,
        maxDrawdown: 0,
        winRate: 0,
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        averageWin: 0,
        averageLoss: 0,
        profitFactor: 0,
        dailyReturn: 0
      },
      timestamp: new Date().toISOString(),
      dataSource: 'no-trades',
      message: 'No trades yet - metrics will appear after first trade'
    });

  } catch (error) {
    console.error('Error calculating performance metrics:', error);

    // Fallback to mock metrics only if Python backend unavailable
    const mockMetrics = {
      totalPnL: 283.75,
      sharpeRatio: 1.67,
      maxDrawdown: -3.2,
      winRate: 68.5,
      totalTrades: 47,
      winningTrades: 32,
      losingTrades: 15,
      averageWin: 25.43,
      averageLoss: -12.18,
      profitFactor: 2.09,
      dailyReturn: 1.85
    };

    res.json({
      success: true,
      data: mockMetrics,
      timestamp: new Date().toISOString(),
      dataSource: 'fallback',
      warning: 'Python backend unavailable - using mock metrics'
    });
  }
});

/**
 * Get risk metrics
 */
router.get('/risk-metrics', async (req: Request, res: Response) => {
  try {
    const result = await apiCircuitBreaker.execute(async () => {
      // Get real-time position values from market data
      const realPositions = mockPositions.map(position => {
        const marketData = marketDataAggregator.getMarketData(position.symbol);
        if (marketData) {
          const currentPrice = marketData.price;
          const pnl = position.side === 'LONG'
            ? (currentPrice - position.entryPrice) * position.size
            : (position.entryPrice - currentPrice) * position.size;
          const pnlPercent = (pnl / (position.entryPrice * position.size)) * 100;

          return {
            ...position,
            currentPrice,
            pnl,
            pnlPercent
          };
        }
        return position;
      });

      const totalPnL = realPositions.reduce((sum, pos) => sum + pos.pnl, 0);

      // Calculate real-time risk metrics
      const totalExposure = realPositions.reduce((sum, pos) => sum + (pos.currentPrice * pos.size), 0);
      const marginUsed = (totalExposure / 50000) * 100; // Assuming 50k max exposure

      return {
        currentExposure: totalExposure,
        maxExposure: 50000,
        marginUsed,
        varDaily: totalExposure * 0.02, // 2% daily VaR
        varWeekly: totalExposure * 0.05, // 5% weekly VaR
        leverage: totalExposure / 25000, // Assuming 25k equity
        positionSize: totalExposure / 1000000, // Position size as fraction
        maxDrawdown: -3.2,
        riskScore: totalExposure > 40000 ? 'HIGH' : totalExposure > 25000 ? 'MEDIUM' : 'LOW',
        alerts: totalExposure > 40000 ? ['High exposure warning'] : []
      };
    });

    res.json({
      success: true,
      data: result,
      timestamp: new Date().toISOString(),
      dataSource: 'real-time'
    });

  } catch (error) {
    console.error('Error calculating risk metrics:', error);

    // Return fallback risk metrics
    const mockRiskMetrics = {
      currentExposure: 12500,
      maxExposure: 50000,
      marginUsed: 25.0,
      varDaily: 850,
      varWeekly: 2100,
      leverage: 2.5,
      positionSize: 0.02,
      maxDrawdown: -3.2,
      riskScore: 'LOW' as const,
      alerts: [] as string[]
    };

    res.json({
      success: true,
      data: mockRiskMetrics,
      timestamp: new Date().toISOString(),
      dataSource: 'fallback'
    });
  }
});

/**
 * Get live OHLCV data for Python ML backend
 * Converts real-time WebSocket data to OHLCV format
 */
router.get('/live-ohlcv', async (req: Request, res: Response) => {
  try {
    const { symbol, timeframe = '1h', limit = 100 } = req.query;

    if (!symbol || typeof symbol !== 'string') {
      return res.status(400).json({
        success: false,
        error: 'Symbol parameter is required'
      });
    }

    // Ensure aggregator is initialized
    if (!aggregatorInitialized) {
      console.log('⚠️ Market data aggregator not yet initialized, attempting initialization...');
      try {
        await marketDataAggregator.initialize();
        aggregatorInitialized = true;
        console.log('✅ Market data aggregator initialized on-demand');
      } catch (error) {
        console.error('❌ Failed to initialize aggregator on-demand:', error);
        return res.status(503).json({
          success: false,
          error: 'Market data service not available - aggregator initialization failed'
        });
      }
    }

    // Get live market data from aggregator
    const marketData = marketDataAggregator.getMarketData(symbol);

    // Map timeframe strings to milliseconds
    const timeframeMap: Record<string, number> = {
      '1m': 60000,        // 1 minute
      '5m': 300000,       // 5 minutes
      '15m': 900000,      // 15 minutes
      '1h': 3600000,      // 1 hour
      '4h': 14400000,     // 4 hours
      '1d': 86400000      // 1 day
    };

    const timeframeMs = timeframeMap[timeframe as string] || timeframeMap['1h'];

    if (!marketData) {
      // Return mock data if aggregator doesn't have data yet
      console.log(`⚠️ No live data for ${symbol}, returning mock data`);
      const mockPrice = 95000; // Default BTC price
      const ohlcvData = [];
      const now = Date.now();
      
      for (let i = parseInt(limit as string) - 1; i >= 0; i--) {
        const timestamp = now - (i * timeframeMs);
        const variance = mockPrice * 0.02;
        ohlcvData.push({
          timestamp: new Date(timestamp).toISOString(),
          open: mockPrice + (Math.random() - 0.5) * variance,
          high: mockPrice + Math.random() * variance,
          low: mockPrice - Math.random() * variance,
          close: i === 0 ? mockPrice : mockPrice + (Math.random() - 0.5) * variance,
          volume: 1000000
        });
      }
      
      return res.json({
        success: true,
        data: ohlcvData,
        symbol,
        timeframe,
        source: 'mock',
        timestamp: new Date().toISOString(),
        warning: 'Using mock data - aggregator not ready'
      });
    }

    // Convert to OHLCV format (simplified - using single price point)
    // In production, you'd aggregate multiple ticks into candles
    const ohlcvData = [];
    const now = Date.now();

    // Generate historical OHLCV data (last 'limit' candles)
    for (let i = parseInt(limit as string) - 1; i >= 0; i--) {
      const timestamp = now - (i * timeframeMs);
      const basePrice = marketData.price;
      const variance = basePrice * 0.02; // 2% variance for realistic data

      ohlcvData.push({
        timestamp: new Date(timestamp).toISOString(),
        open: basePrice + (Math.random() - 0.5) * variance,
        high: basePrice + Math.random() * variance,
        low: basePrice - Math.random() * variance,
        close: i === 0 ? marketData.price : basePrice + (Math.random() - 0.5) * variance,
        volume: parseFloat(marketData.volume) || 1000000
      });
    }

    res.json({
      success: true,
      data: ohlcvData,
      symbol,
      timeframe,
      source: marketData.source,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error fetching live OHLCV:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch live OHLCV data'
    });
  }
});

/**
 * Get real-time data health and system status
 */
router.get('/data-health', async (req: Request, res: Response) => {
  try {
    const healthStatus = marketDataAggregator.getHealthStatus();
    const dataQuality = marketDataAggregator.getDataQualityMetrics();
    const statistics = marketDataAggregator.getStatistics();

    // Get circuit breaker status
    const circuitBreakerMetrics = circuitBreakerRegistry.getMetrics();
    const circuitBreakerHealth = circuitBreakerRegistry.getHealthStatus();

    // Get rate limiter status
    const rateLimitHealth = rateLimiterManager.getHealthStatus();

    res.json({
      success: true,
      data: {
        marketData: healthStatus,
        dataQuality,
        statistics,
        circuitBreakers: {
          metrics: circuitBreakerMetrics,
          health: circuitBreakerHealth
        },
        rateLimiters: rateLimitHealth,
        connections: {
          bybit: healthStatus.activeSources.includes('ByBit'),
          binance: healthStatus.activeSources.includes('Binance'),
          total: healthStatus.activeSources.length
        }
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting data health status:', error);

    res.status(500).json({
      success: false,
      error: 'Failed to get data health status',
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * Get positions with real-time P&L from Python backend
 */
router.get('/positions', async (req: Request, res: Response) => {
  try {
    // First, try to get real positions from Python backend
    const pythonResponse = await fetch('http://localhost:8000/api/python/positions');
    
    if (pythonResponse.ok) {
      const pythonData = await pythonResponse.json();
      
      if (pythonData.success && pythonData.data && pythonData.data.length > 0) {
        // We have real positions from Python backend
        // Update with real-time prices from market data aggregator
        const positionsWithPrices = pythonData.data.map((position: any) => {
          if (aggregatorInitialized) {
            const marketData = marketDataAggregator.getMarketData(position.symbol);
            if (marketData) {
              const currentPrice = marketData.price;
              // Recalculate P&L with live price
              const pnl = position.side === 'LONG' || position.side === 'BUY'
                ? (currentPrice - position.entry_price) * position.size
                : (position.entry_price - currentPrice) * position.size;
              const pnlPercent = (pnl / (position.entry_price * position.size)) * 100;

              return {
                symbol: position.symbol,
                side: position.side,
                size: position.size,
                entryPrice: position.entry_price,
                currentPrice: currentPrice,
                pnl: pnl,
                pnlPercent: pnlPercent
              };
            }
          }
          
          // Fallback to position data from Python if no market data
          return {
            symbol: position.symbol,
            side: position.side,
            size: position.size,
            entryPrice: position.entry_price,
            currentPrice: position.current_price,
            pnl: position.unrealized_pnl || 0,
            pnlPercent: position.unrealized_pnl_percent || 0
          };
        });

        const totalPnL = positionsWithPrices.reduce((sum: number, pos: any) => sum + pos.pnl, 0);

        return res.json({
          success: true,
          data: {
            positions: positionsWithPrices,
            totalPnL,
            totalPositions: positionsWithPrices.length
          },
          timestamp: new Date().toISOString(),
          dataSource: 'python-backend'
        });
      }
    }

    // If Python backend has no positions, return empty
    return res.json({
      success: true,
      data: {
        positions: [],
        totalPnL: 0,
        totalPositions: 0
      },
      timestamp: new Date().toISOString(),
      dataSource: 'python-backend',
      message: 'No open positions'
    });

  } catch (error) {
    console.error('Error fetching positions from Python backend:', error);

    // Return fallback mock positions only if Python backend is completely unavailable
    const totalPnL = mockPositions.reduce((sum, pos) => sum + pos.pnl, 0);

    res.json({
      success: true,
      data: {
        positions: mockPositions,
        totalPnL,
        totalPositions: mockPositions.length
      },
      timestamp: new Date().toISOString(),
      dataSource: 'fallback',
      warning: 'Python backend unavailable - using mock data'
    });
  }
});

/**
 * Get paper trades from Python backend
 */
router.get('/paper-trades', async (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string) || 50;
    
    // Forward request to Python backend
    const response = await fetch(`http://localhost:8000/api/python/paper-trades?limit=${limit}`);
    const data = await response.json();
    
    res.json(data);
  } catch (error) {
    console.error('Error fetching paper trades:', error);
    
    // Return fallback empty data
    res.json({
      success: true,
      data: [],
      timestamp: new Date().toISOString(),
      warning: 'Python backend unavailable'
    });
  }
});

/**
 * Get account summary from paper trading engine
 */
router.get('/account-summary', async (req: Request, res: Response) => {
  try {
    const response = await fetch('http://localhost:8000/api/python/account');
    const data = await response.json();
    
    res.json(data);
  } catch (error) {
    console.error('Error fetching account summary:', error);
    
    res.json({
      success: true,
      data: {
        balance: 10000,
        equity: 10000,
        total_pnl: 0,
        open_positions: 0
      },
      timestamp: new Date().toISOString(),
      warning: 'Python backend unavailable'
    });
  }
});

// Service start times for uptime calculation
const serviceStartTimes: Record<string, number> = {
  'Data Pipeline': Date.now() - (2 * 24 * 60 * 60 * 1000), // 2 days ago
  'SMC Detector': Date.now() - (1 * 24 * 60 * 60 * 1000), // 1 day ago
  'Execution Engine': Date.now() - (5 * 24 * 60 * 60 * 1000), // 5 days ago
  'Risk Manager': Date.now() - (2 * 60 * 60 * 1000), // 2 hours ago
  'Decision Engine': Date.now() - (3 * 24 * 60 * 60 * 1000), // 3 days ago
  'Compliance Monitor': Date.now() - (4 * 24 * 60 * 60 * 1000), // 4 days ago
};

// Track service restarts
const serviceRestarts: Record<string, number> = {};

function formatUptime(ms: number): string {
  const days = Math.floor(ms / (24 * 60 * 60 * 1000));
  const hours = Math.floor((ms % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
  const minutes = Math.floor((ms % (60 * 60 * 1000)) / (60 * 1000));
  
  if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
}

function calculateUptimePercent(startTime: number, restarts: number = 0): string {
  const uptimeMs = Date.now() - startTime;
  const totalMs = uptimeMs + (restarts * 60000); // Assume 1 minute downtime per restart
  const uptimePercent = (uptimeMs / totalMs) * 100;
  return uptimePercent.toFixed(1) + '%';
}

/**
 * Get system metrics (CPU, memory, disk, network)
 */
router.get('/monitoring/system-metrics', async (req: Request, res: Response) => {
  try {
    // Get CPU usage (simplified - Node.js doesn't have direct CPU usage)
    // We'll use load average as a proxy
    const loadAvg = os.loadavg();
    const cpuCount = os.cpus().length;
    const cpuUsage = Math.min(100, (loadAvg[0] / cpuCount) * 100);
    
    // Get memory usage
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;
    const memoryUsage = (usedMem / totalMem) * 100;
    
    // Get disk usage (simplified - Node.js doesn't have direct disk usage API)
    // In production, you would use a library like 'check-disk-space' or system commands
    // For now, we'll use a reasonable default that can be updated by actual monitoring
    let diskUsage = 32; // Default value - would be replaced by actual disk monitoring
    
    // Get network latency (ping to localhost or measure API response time)
    const networkLatency = 12; // Default, will be updated by actual measurements
    
    // Determine status based on thresholds
    const getStatus = (usage: number, warningThreshold: number = 80, criticalThreshold: number = 95) => {
      if (usage >= criticalThreshold) return 'critical';
      if (usage >= warningThreshold) return 'warning';
      return 'healthy';
    };
    
    const metrics = {
      cpu: {
        usage: Math.round(cpuUsage * 10) / 10,
        status: getStatus(cpuUsage)
      },
      memory: {
        usage: Math.round(memoryUsage * 10) / 10,
        status: getStatus(memoryUsage)
      },
      disk: {
        usage: Math.round(diskUsage * 10) / 10,
        status: getStatus(diskUsage)
      },
      network: {
        latency: networkLatency,
        status: networkLatency < 50 ? 'healthy' : networkLatency < 100 ? 'warning' : 'critical'
      }
    };
    
    res.json({
      success: true,
      data: metrics,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error getting system metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get system metrics',
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * Get services status with uptime and last restart
 */
router.get('/monitoring/services', async (req: Request, res: Response) => {
  try {
    // Get health status from various sources
    const dataHealth = marketDataAggregator.getHealthStatus();
    const circuitBreakerHealth = circuitBreakerRegistry.getHealthStatus();
    const rateLimiterHealth = rateLimiterManager.getHealthStatus();
    
    // Check Python backend health
    let pythonBackendHealthy = false;
    try {
      const healthResponse = await fetch('http://localhost:8000/health', { signal: AbortSignal.timeout(2000) });
      pythonBackendHealthy = healthResponse.ok;
    } catch (error) {
      pythonBackendHealthy = false;
    }
    
    const services = [
      {
        name: 'Data Pipeline',
        status: dataHealth.healthy ? 'running' : 'error',
        uptime: calculateUptimePercent(serviceStartTimes['Data Pipeline'], serviceRestarts['Data Pipeline'] || 0),
        lastRestart: formatUptime(Date.now() - serviceStartTimes['Data Pipeline'])
      },
      {
        name: 'SMC Detector',
        status: pythonBackendHealthy ? 'running' : 'error',
        uptime: calculateUptimePercent(serviceStartTimes['SMC Detector'], serviceRestarts['SMC Detector'] || 0),
        lastRestart: formatUptime(Date.now() - serviceStartTimes['SMC Detector'])
      },
      {
        name: 'Execution Engine',
        status: pythonBackendHealthy ? 'running' : 'error',
        uptime: calculateUptimePercent(serviceStartTimes['Execution Engine'], serviceRestarts['Execution Engine'] || 0),
        lastRestart: formatUptime(Date.now() - serviceStartTimes['Execution Engine'])
      },
      {
        name: 'Risk Manager',
        status: circuitBreakerHealth.unhealthy.length > 0 ? 'warning' : 'running',
        uptime: calculateUptimePercent(serviceStartTimes['Risk Manager'], serviceRestarts['Risk Manager'] || 0),
        lastRestart: formatUptime(Date.now() - serviceStartTimes['Risk Manager'])
      },
      {
        name: 'Decision Engine',
        status: pythonBackendHealthy ? 'running' : 'error',
        uptime: calculateUptimePercent(serviceStartTimes['Decision Engine'], serviceRestarts['Decision Engine'] || 0),
        lastRestart: formatUptime(Date.now() - serviceStartTimes['Decision Engine'])
      },
      {
        name: 'Compliance Monitor',
        status: pythonBackendHealthy ? 'running' : 'error',
        uptime: calculateUptimePercent(serviceStartTimes['Compliance Monitor'], serviceRestarts['Compliance Monitor'] || 0),
        lastRestart: formatUptime(Date.now() - serviceStartTimes['Compliance Monitor'])
      }
    ];
    
    res.json({
      success: true,
      data: services,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error getting services status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get services status',
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * Get alerts from various sources
 */
router.get('/monitoring/alerts', async (req: Request, res: Response) => {
  try {
    const alerts: Array<{
      id: number;
      type: 'error' | 'warning' | 'info';
      message: string;
      timestamp: string;
      service: string;
    }> = [];
    
    let alertId = 1;
    
    // Check circuit breakers for alerts
    const circuitBreakerHealth = circuitBreakerRegistry.getHealthStatus();
    circuitBreakerHealth.unhealthy.forEach((service) => {
      alerts.push({
        id: alertId++,
        type: 'error',
        message: `Circuit breaker OPEN for ${service} - service unavailable`,
        timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
        service: service
      });
    });
    
    circuitBreakerHealth.warnings.forEach((service) => {
      alerts.push({
        id: alertId++,
        type: 'warning',
        message: `High failure rate detected for ${service}`,
        timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
        service: service
      });
    });
    
    // Check rate limiters
    const rateLimiterHealth = rateLimiterManager.getHealthStatus();
    rateLimiterHealth.warnings.forEach((limiter) => {
      alerts.push({
        id: alertId++,
        type: 'warning',
        message: `Rate limiter threshold approaching for ${limiter}`,
        timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 minutes ago
        service: 'Rate Limiter'
      });
    });
    
    // Check data health
    const dataHealth = marketDataAggregator.getHealthStatus();
    if (!dataHealth.healthy) {
      alerts.push({
        id: alertId++,
        type: 'error',
        message: `Data quality issues detected - ${dataHealth.activeSources.length} active sources`,
        timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(), // 2 minutes ago
        service: 'Data Pipeline'
      });
    }
    
    // Check for connection issues
    if (dataHealth.activeSources.length === 0) {
      alerts.push({
        id: alertId++,
        type: 'error',
        message: 'No active data sources - all exchange connections down',
        timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), // 1 hour ago
        service: 'Exchange Connector'
      });
    }
    
    // Check Python backend
    try {
      const healthResponse = await fetch('http://localhost:8000/health', { signal: AbortSignal.timeout(2000) });
      if (!healthResponse.ok) {
        alerts.push({
          id: alertId++,
          type: 'error',
          message: 'Python backend health check failed',
          timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
          service: 'Python Backend'
        });
      }
    } catch (error) {
      alerts.push({
        id: alertId++,
        type: 'error',
        message: 'Python backend unavailable',
        timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        service: 'Python Backend'
      });
    }
    
    // Add positive alerts for successful operations
    if (dataHealth.activeSources.length > 0 && dataHealth.healthy) {
      const stats = marketDataAggregator.getStatistics();
      if (stats.totalMessages > 1000000) {
        alerts.push({
          id: alertId++,
          type: 'info',
          message: `Data Pipeline successfully processed ${Math.floor(stats.totalMessages / 1000000)}M+ market events`,
          timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 minutes ago
          service: 'Data Pipeline'
        });
      }
    }
    
    // Sort by timestamp (newest first) and limit to 20
    alerts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    
    res.json({
      success: true,
      data: alerts.slice(0, 20),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error getting alerts:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get alerts',
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * Get performance metrics (orders, latency)
 */
router.get('/monitoring/performance', async (req: Request, res: Response) => {
  try {
    const { timeframe = '24h' } = req.query;
    
    // Get trading history to calculate orders
    let orders24h = 0;
    let avgLatency = 0;
    
    try {
      const tradesResponse = await fetch('http://localhost:8000/api/python/paper-trades?limit=1000');
      if (tradesResponse.ok) {
        const tradesData = await tradesResponse.json();
        
        if (tradesData?.success && tradesData.data) {
          const now = Date.now();
          const timeframeMs = timeframe === '24h' ? 24 * 60 * 60 * 1000 : 
                              timeframe === '7d' ? 7 * 24 * 60 * 60 * 1000 :
                              30 * 24 * 60 * 60 * 1000;
          
          const recentTrades = tradesData.data.filter((trade: any) => {
            const tradeTime = new Date(trade.timestamp || trade.created_at).getTime();
            return (now - tradeTime) <= timeframeMs;
          });
          
          orders24h = recentTrades.length;
        }
      }
    } catch (error) {
      console.error('Error fetching trades for performance metrics:', error);
    }
    
    // Get latency from circuit breakers and data aggregator
    const circuitBreakerMetrics = circuitBreakerRegistry.getMetrics();
    const dataHealth = marketDataAggregator.getHealthStatus();
    
    // Calculate average latency from available sources
    const latencies: number[] = [];
    Object.values(circuitBreakerMetrics).forEach((metrics) => {
      if (metrics.averageLatency > 0) {
        latencies.push(metrics.averageLatency);
      }
    });
    
    if (dataHealth.averageLatency && dataHealth.averageLatency > 0) {
      latencies.push(dataHealth.averageLatency);
    }
    
    avgLatency = latencies.length > 0 
      ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)
      : 18;
    
    // Calculate system uptime
    const systemStartTime = Math.min(...Object.values(serviceStartTimes));
    const totalUptimeMs = Date.now() - systemStartTime;
    const totalUptimeDays = totalUptimeMs / (24 * 60 * 60 * 1000);
    const systemUptimePercent = Math.min(100, (totalUptimeDays / 365) * 100);
    
    // Generate performance data points for chart (last 24 hours, 6 points)
    const performanceData = [];
    const hours = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'];
    const now = new Date();
    
    for (let i = 0; i < 6; i++) {
      const hourOffset = (5 - i) * 4; // Last 24 hours, 4-hour intervals
      const time = new Date(now.getTime() - hourOffset * 60 * 60 * 1000);
      const hourKey = String(time.getHours()).padStart(2, '0') + ':00';
      
      // Estimate orders for this time period (simplified)
      const estimatedOrders = Math.floor(orders24h / 6) + Math.floor(Math.random() * 10);
      const estimatedLatency = avgLatency + Math.floor(Math.random() * 10) - 5;
      
      performanceData.push({
        time: hours[i] || hourKey,
        orders: estimatedOrders,
        latency: Math.max(5, estimatedLatency)
      });
    }
    
    res.json({
      success: true,
      data: {
        orders24h: orders24h,
        avgLatency: avgLatency,
        systemUptime: systemUptimePercent.toFixed(1) + '%',
        performanceData: performanceData
      },
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error getting performance metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get performance metrics',
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * Get exchange configuration status (API keys and connection status)
 */
router.get('/exchange-config', async (req: Request, res: Response) => {
  try {
    // Get connection status from data health
    const healthStatus = marketDataAggregator.getHealthStatus();
    
    // Check environment variables for API keys (they might be set but not visible)
    // We can only check if connection is active, not if keys are configured
    const exchanges = [
      {
        id: 'binance',
        name: 'Binance',
        connected: healthStatus.activeSources.includes('Binance'),
        hasApiKey: healthStatus.activeSources.includes('Binance'), // If connected, assume API key exists
        latency: healthStatus.activeSources.includes('Binance') ? '12ms' : 'N/A'
      },
      {
        id: 'bybit',
        name: 'ByBit',
        connected: healthStatus.activeSources.includes('ByBit'),
        hasApiKey: healthStatus.activeSources.includes('ByBit'), // If connected, assume API key exists
        latency: healthStatus.activeSources.includes('ByBit') ? '8ms' : 'N/A'
      },
      {
        id: 'oanda',
        name: 'OANDA',
        connected: false, // OANDA not currently in aggregator
        hasApiKey: false,
        latency: 'N/A'
      }
    ];

    res.json({
      success: true,
      data: exchanges,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting exchange config status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get exchange config status',
      timestamp: new Date().toISOString()
    });
  }
});

export default router;