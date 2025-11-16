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

  // Health check
  async healthCheck(): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return await response.json();
  }
}

export const apiService = new ApiService();