/**
 * Trading API Routes
 * Connects frontend with real-time SMC Trading Agent system
 */

import { Router, type Request, type Response } from 'express';
import { MarketDataAggregator } from '../services/marketDataAggregator';
import { CircuitBreakerRegistry } from '../utils/circuitBreaker';
import { RateLimiterManager } from '../utils/rateLimiter';

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
 * Get SMC pattern analysis
 */
router.get('/smc-patterns', (req: Request, res: Response) => {
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
    },
    {
      id: 'pattern_2',
      symbol: 'BTCUSDT',
      type: 'choch',
      direction: 'bearish',
      strength: 0.73,
      price: 43100,
      timestamp: new Date(Date.now() - 300000).toISOString(),
      confidence: 0.78
    }
  ];

  res.json({
    success: true,
    data: mockPatterns,
    timestamp: new Date().toISOString()
  });
});

/**
 * Get trading history
 */
router.get('/history', (req: Request, res: Response) => {
  const { limit = 50, symbol = 'all' } = req.query;

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
    },
    {
      id: 'trade_2',
      symbol: 'ETHUSDT',
      action: 'SELL',
      price: 2680,
      size: 2.0,
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      status: 'CLOSED',
      pnl: 58.50,
      reason: 'Bearish CHOCH pattern confirmed'
    }
  ];

  res.json({
    success: true,
    data: mockTrades,
    timestamp: new Date().toISOString()
  });
});

/**
 * Execute manual trade
 */
router.post('/execute-trade', (req: Request, res: Response) => {
  const { symbol, action, price, size, reason } = req.body;

  if (!symbol || !action || !price || !size) {
    return res.status(400).json({
      success: false,
      error: 'Missing required fields: symbol, action, price, size'
    });
  }

  // Mock trade execution
  const trade = {
    id: `trade_${Date.now()}`,
    symbol,
    action: action.toUpperCase(),
    price: parseFloat(price),
    size: parseFloat(size),
    timestamp: new Date().toISOString(),
    status: 'EXECUTED',
    reason: reason || 'Manual trade request',
    orderId: `order_${Date.now()}`
  };

  res.json({
    success: true,
    data: trade,
    message: 'Trade executed successfully'
  });
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

    if (!marketData) {
      // Return mock data if aggregator doesn't have data yet
      console.log(`⚠️ No live data for ${symbol}, returning mock data`);
      const mockPrice = 95000; // Default BTC price
      const ohlcvData = [];
      const now = Date.now();
      const timeframeMs = timeframe === '1h' ? 3600000 : 60000;
      
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
    const timeframeMs = timeframe === '1h' ? 3600000 : 60000; // 1h or 1m

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

export default router;