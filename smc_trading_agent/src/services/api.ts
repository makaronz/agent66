/**
 * API service for connecting frontend with SMC Trading Agent
 */

const API_BASE_URL = 'http://localhost:3001/api';

export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  volume: string;
}

export interface Position {
  symbol: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}

export interface SystemHealth {
  name: string;
  status: 'healthy' | 'warning' | 'error';
  latency: string;
}

export interface SMCPattern {
  id: string;
  symbol: string;
  type: string;
  direction: 'bullish' | 'bearish';
  strength: number;
  price: number;
  timestamp: string;
  confidence: number;
}

export interface Trade {
  id: string;
  symbol: string;
  action: string;
  price: number;
  size: number;
  timestamp: string;
  status: string;
  pnl?: number;
  reason?: string;
  orderId?: string;
}

export interface PerformanceMetrics {
  totalPnL: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  averageWin: number;
  averageLoss: number;
  profitFactor: number;
  dailyReturn: number;
}

export interface RiskMetrics {
  currentExposure: number;
  maxExposure: number;
  marginUsed: number;
  varDaily: number;
  varWeekly: number;
  leverage: number;
  positionSize: number;
  maxDrawdown: number;
  riskScore: 'LOW' | 'MEDIUM' | 'HIGH';
  alerts: string[];
}

export interface OHLCVData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface EquityPoint {
  timestamp: string;
  value: number;
  drawdown?: number;
}

class ApiService {
  // Market data
  async getMarketData(): Promise<MarketData[]> {
    const response = await fetch(`${API_BASE_URL}/trading/market-data`);
    const data = await response.json();
    return data.data;
  }

  // Positions
  async getPositions(): Promise<{ positions: Position[]; totalPnL: number; totalPositions: number }> {
    const response = await fetch(`${API_BASE_URL}/trading/positions`);
    const data = await response.json();
    return data.data;
  }

  // System health
  async getSystemHealth(): Promise<{ components: SystemHealth[]; overall: string }> {
    const response = await fetch(`${API_BASE_URL}/trading/system-health`);
    const data = await response.json();
    return data.data;
  }

  // SMC patterns
  async getSMCPatterns(): Promise<SMCPattern[]> {
    const response = await fetch(`${API_BASE_URL}/trading/smc-patterns`);
    const data = await response.json();
    return data.data;
  }

  // Trading history
  async getTradingHistory(limit?: number, symbol?: string): Promise<Trade[]> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (symbol && symbol !== 'all') params.append('symbol', symbol);

    const response = await fetch(`${API_BASE_URL}/trading/history?${params}`);
    const data = await response.json();
    return data.data;
  }

  // Performance metrics
  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    const response = await fetch(`${API_BASE_URL}/trading/performance`);
    const data = await response.json();
    return data.data;
  }

  // Risk metrics
  async getRiskMetrics(): Promise<RiskMetrics> {
    const response = await fetch(`${API_BASE_URL}/trading/risk-metrics`);
    const data = await response.json();
    return data.data;
  }

  // Execute manual trade
  async executeTrade(tradeData: {
    symbol: string;
    action: string;
    price: number;
    size: number;
    reason?: string;
    stopLoss?: number;
    takeProfit?: number;
  }): Promise<Trade> {
    const response = await fetch(`${API_BASE_URL}/trading/execute-trade`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(tradeData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to execute trade');
    }

    const data = await response.json();
    return data.data;
  }

  // Get OHLCV data for charting
  async getOHLCVData(symbol: string, timeframe: string = '1h', limit: number = 100): Promise<OHLCVData[]> {
    const params = new URLSearchParams();
    params.append('symbol', symbol);
    params.append('timeframe', timeframe);
    params.append('limit', limit.toString());

    const response = await fetch(`${API_BASE_URL}/trading/live-ohlcv?${params}`);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch OHLCV data');
    }
    
    return data.data;
  }

  // Get equity curve data from trading history
  async getEquityCurve(timeframe: string = '1Y'): Promise<EquityPoint[]> {
    try {
      // Get all trading history
      const trades = await this.getTradingHistory(1000);
      
      if (trades.length === 0) {
        // Return mock data if no trades
        return this.generateMockEquityCurve();
      }

      // Calculate equity curve from trades
      const equityPoints: EquityPoint[] = [];
      let currentEquity = 10000; // Starting capital
      let peakEquity = currentEquity;
      
      // Sort trades by timestamp
      const sortedTrades = [...trades].sort((a, b) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );

      // Group trades by time period based on timeframe
      const periodMap = new Map<string, { pnl: number; timestamp: string }[]>();
      
      sortedTrades.forEach(trade => {
        const tradeDate = new Date(trade.timestamp);
        let periodKey: string;
        
        switch (timeframe) {
          case '1M':
            periodKey = `${tradeDate.getFullYear()}-${String(tradeDate.getMonth() + 1).padStart(2, '0')}-${String(tradeDate.getDate()).padStart(2, '0')}`;
            break;
          case '3M':
          case '6M':
            periodKey = `${tradeDate.getFullYear()}-${String(tradeDate.getMonth() + 1).padStart(2, '0')}-W${Math.ceil(tradeDate.getDate() / 7)}`;
            break;
          case '1Y':
          case 'ALL':
          default:
            periodKey = `${tradeDate.getFullYear()}-${String(tradeDate.getMonth() + 1).padStart(2, '0')}`;
            break;
        }
        
        if (!periodMap.has(periodKey)) {
          periodMap.set(periodKey, []);
        }
        
        periodMap.get(periodKey)!.push({
          pnl: trade.pnl || 0,
          timestamp: trade.timestamp
        });
      });

      // Calculate equity for each period
      const sortedPeriods = Array.from(periodMap.entries()).sort((a, b) => 
        a[0].localeCompare(b[0])
      );

      sortedPeriods.forEach(([period, periodTrades]) => {
        const periodPnL = periodTrades.reduce((sum, t) => sum + t.pnl, 0);
        currentEquity += periodPnL;
        
        if (currentEquity > peakEquity) {
          peakEquity = currentEquity;
        }
        
        const drawdown = ((currentEquity - peakEquity) / peakEquity) * 100;
        
        equityPoints.push({
          timestamp: periodTrades[0].timestamp,
          value: currentEquity,
          drawdown: drawdown
        });
      });

      return equityPoints.length > 0 ? equityPoints : this.generateMockEquityCurve();
    } catch (error) {
      console.error('Error fetching equity curve:', error);
      return this.generateMockEquityCurve();
    }
  }

  // Generate mock equity curve for demonstration
  private generateMockEquityCurve(): EquityPoint[] {
    const points: EquityPoint[] = [];
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 12);
    let equity = 10000;
    let peakEquity = equity;

    for (let i = 0; i < 12; i++) {
      const date = new Date(startDate);
      date.setMonth(date.getMonth() + i);
      
      // Simulate growth with some volatility
      const change = (Math.random() - 0.4) * 500; // Slight positive bias
      equity += change;
      
      if (equity > peakEquity) {
        peakEquity = equity;
      }
      
      const drawdown = ((equity - peakEquity) / peakEquity) * 100;
      
      points.push({
        timestamp: date.toISOString(),
        value: equity,
        drawdown: drawdown
      });
    }

    return points;
  }

  // Health check
  async healthCheck(): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return await response.json();
  }
}

export const apiService = new ApiService();