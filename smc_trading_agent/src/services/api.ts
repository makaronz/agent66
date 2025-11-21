/**
 * API service for connecting frontend with SMC Trading Agent
 */

const API_BASE_URL = 'http://localhost:3002/api';

// Agent management interfaces
export interface AgentConfig {
  id: string;
  name: string;
  type: 'smc_detector' | 'decision_engine' | 'execution_engine' | 'risk_manager';
  symbol: string;
  timeframe: string;
  capital: number;
  leverage: number;
  strategies: string[];
  riskLevel: 'conservative' | 'moderate' | 'aggressive';
  paperTrading: boolean;
  maxDrawdown: number;
  dailyLossLimit: number;
}

export interface Agent {
  id: string;
  name: string;
  type: 'smc_detector' | 'decision_engine' | 'execution_engine' | 'risk_manager';
  status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping';
  symbol: string;
  timeframe: string;
  capital: number;
  currentPnL: number;
  totalTrades: number;
  winRate: number;
  uptime: string;
  lastActivity: string;
  latency: string;
  memoryUsage: number;
  cpuUsage: number;
  networkUsage: number;
  errorCount: number;
  paperTrading: boolean;
  strategies: string[];
  startTime: string;
}

export interface LogEntry {
  id: string;
  agentId: string;
  agentName: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug' | 'trade';
  message: string;
  details?: Record<string, any>;
  category: 'system' | 'trading' | 'performance' | 'risk' | 'network';
}

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

  // Account summary
  async getAccountSummary(): Promise<{
    balance: number;
    equity: number;
    initial_balance: number;
    total_pnl: number;
    total_pnl_percent: number;
    unrealized_pnl: number;
    used_margin: number;
    free_margin: number;
    margin_level: number;
    open_positions: number;
    max_positions: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
  }> {
    const response = await fetch(`${API_BASE_URL}/trading/account-summary`);
    const data = await response.json();
    return data.data;
  }

  // Monitoring endpoints
  async getSystemMetrics(): Promise<{
    cpu: { usage: number; status: string };
    memory: { usage: number; status: string };
    disk: { usage: number; status: string };
    network: { latency: number; status: string };
  }> {
    const response = await fetch(`${API_BASE_URL}/trading/monitoring/system-metrics`);
    const data = await response.json();
    return data.data;
  }

  async getServicesStatus(): Promise<Array<{
    name: string;
    status: string;
    uptime: string;
    lastRestart: string;
  }>> {
    const response = await fetch(`${API_BASE_URL}/trading/monitoring/services`);
    const data = await response.json();
    return data.data;
  }

  async getAlerts(): Promise<Array<{
    id: number;
    type: 'error' | 'warning' | 'info';
    message: string;
    timestamp: string;
    service: string;
  }>> {
    const response = await fetch(`${API_BASE_URL}/trading/monitoring/alerts`);
    const data = await response.json();
    return data.data;
  }

  async getSystemPerformanceMetrics(timeframe: string = '24h'): Promise<{
    orders24h: number;
    avgLatency: number;
    systemUptime: string;
    performanceData: Array<{ time: string; orders: number; latency: number }>;
  }> {
    const response = await fetch(`${API_BASE_URL}/trading/monitoring/performance?timeframe=${timeframe}`);
    const data = await response.json();
    return data.data;
  }

  // Exchange configuration status
  async getExchangeConfig(): Promise<Array<{
    id: string;
    name: string;
    connected: boolean;
    hasApiKey: boolean;
    latency: string;
  }>> {
    const response = await fetch(`${API_BASE_URL}/trading/exchange-config`);
    const data = await response.json();
    return data.data;
  }

  // Agent Management Methods

  // Spawn a new trading agent
  async spawnAgent(config: AgentConfig): Promise<Agent> {
    const response = await fetch(`${API_BASE_URL}/agents/spawn`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to spawn agent');
    }

    const data = await response.json();
    return data.data;
  }

  // Get all agents
  async getAgents(): Promise<Agent[]> {
    const response = await fetch(`${API_BASE_URL}/agents`);
    const data = await response.json();
    return data.data || [];
  }

  // Get a specific agent
  async getAgent(agentId: string): Promise<Agent> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`);
    const data = await response.json();
    return data.data;
  }

  // Control agent (start, stop, pause, restart)
  async controlAgent(agentId: string, action: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ action }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Failed to ${action} agent`);
    }
  }

  // Update agent configuration
  async updateAgentConfig(agentId: string, config: Partial<AgentConfig>): Promise<Agent> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to update agent configuration');
    }

    const data = await response.json();
    return data.data;
  }

  // Delete/terminate an agent
  async deleteAgent(agentId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete agent');
    }
  }

  // Get agent logs
  async getAgentLogs(agentId?: string, limit: number = 100): Promise<LogEntry[]> {
    const url = agentId
      ? `${API_BASE_URL}/agents/${agentId}/logs?limit=${limit}`
      : `${API_BASE_URL}/agents/logs?limit=${limit}`;

    const response = await fetch(url);
    const data = await response.json();
    return data.data || [];
  }

  // Get agent performance metrics
  async getAgentPerformance(agentId: string, timeframe: string = '24h'): Promise<{
    totalPnL: number;
    winRate: number;
    totalTrades: number;
    profitFactor: number;
    sharpeRatio: number;
    maxDrawdown: number;
    averageWin: number;
    averageLoss: number;
  }> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/performance?timeframe=${timeframe}`);
    const data = await response.json();
    return data.data;
  }

  // Get agent resource usage
  async getAgentResources(agentId: string): Promise<{
    cpu: number;
    memory: number;
    network: number;
    latency: string;
    uptime: string;
  }> {
    const response = await fetch(`${API_BASE_URL}/agents/${agentId}/resources`);
    const data = await response.json();
    return data.data;
  }

  // Get available agent templates
  async getAgentTemplates(): Promise<Array<{
    id: string;
    name: string;
    description: string;
    type: string;
    defaultConfig: Partial<AgentConfig>;
  }>> {
    const response = await fetch(`${API_BASE_URL}/agents/templates`);
    const data = await response.json();
    return data.data || [];
  }

  // Validate agent configuration before spawning
  async validateAgentConfig(config: Partial<AgentConfig>): Promise<{
    isValid: boolean;
    errors: string[];
    warnings: string[];
    resourceEstimate: {
      cpu: string;
      memory: string;
      network: string;
      latency: string;
    };
  }> {
    const response = await fetch(`${API_BASE_URL}/agents/validate-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });

    const data = await response.json();
    return data.data;
  }

  // Advanced Analytics Methods

  // Get strategy attribution data
  async getStrategyAttribution(timeframe: string = '30d'): Promise<Array<{
    strategy: string;
    totalReturn: number;
    sharpeRatio: number;
    maxDrawdown: number;
    winRate: number;
    totalTrades: number;
    profitFactor: number;
    contribution: number;
  }>> {
    const response = await fetch(`${API_BASE_URL}/analytics/strategy-attribution?timeframe=${timeframe}`);
    const data = await response.json();
    return data.data || this.generateMockStrategyAttribution();
  }

  // Get market impact analysis
  async getMarketImpact(timeframe: string = '30d'): Promise<Array<{
    symbol: string;
    tradeSize: number;
    priceImpact: number;
    executionCost: number;
    timingCost: number;
    totalCost: number;
    efficiency: number;
    benchmark: string;
  }>> {
    const response = await fetch(`${API_BASE_URL}/analytics/market-impact?timeframe=${timeframe}`);
    const data = await response.json();
    return data.data || this.generateMockMarketImpact();
  }

  // Get slippage analysis
  async getSlippageAnalysis(symbol?: string, limit: number = 50): Promise<Array<{
    symbol: string;
    expectedPrice: number;
    executionPrice: number;
    slippage: number;
    slippagePercent: number;
    volume: number;
    side: 'BUY' | 'SELL';
    timestamp: string;
    marketCondition: 'normal' | 'volatile' | 'thin';
  }>> {
    const params = new URLSearchParams();
    if (symbol) params.append('symbol', symbol);
    params.append('limit', limit.toString());

    const response = await fetch(`${API_BASE_URL}/analytics/slippage-analysis?${params}`);
    const data = await response.json();
    return data.data || this.generateMockSlippageAnalysis();
  }

  // Get performance forecast
  async getPerformanceForecast(): Promise<Array<{
    period: string;
    expectedReturn: number;
    confidence: number;
    volatility: number;
    sharpeRatio: number;
    maxDrawdown: number;
    winProbability: number;
  }>> {
    const response = await fetch(`${API_BASE_URL}/analytics/performance-forecast`);
    const data = await response.json();
    return data.data || this.generateMockPerformanceForecast();
  }

  // Get revenue metrics
  async getRevenueMetrics(timeframe: string = '6M'): Promise<Array<{
    month: string;
    tradingRevenue: number;
    fees: number;
    netRevenue: number;
    activeStrategies: number;
    totalVolume: number;
    avgDailyReturn: number;
  }>> {
    const response = await fetch(`${API_BASE_URL}/analytics/revenue-metrics?timeframe=${timeframe}`);
    const data = await response.json();
    return data.data || this.generateMockRevenueMetrics();
  }

  // Mock data generators (fallback when API is not available)
  private generateMockStrategyAttribution() {
    const strategies = [
      'Order Block Trading',
      'Liquidity Sweep',
      'Breakout Trading',
      'Mean Reversion',
      'Volatility Trading',
      'Market Making'
    ];

    return strategies.map((strategy, index) => ({
      strategy,
      totalReturn: (Math.random() - 0.2) * 5000,
      sharpeRatio: 0.5 + Math.random() * 2,
      maxDrawdown: Math.random() * 15,
      winRate: 60 + Math.random() * 20,
      totalTrades: Math.floor(Math.random() * 100),
      profitFactor: 1 + Math.random() * 2,
      contribution: Math.random() * 100
    }));
  }

  private generateMockMarketImpact() {
    const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT'];

    return symbols.map(symbol => ({
      symbol,
      tradeSize: Math.random() * 1000000,
      priceImpact: Math.random() * 0.005,
      executionCost: Math.random() * 500,
      timingCost: Math.random() * 200,
      totalCost: Math.random() * 700,
      efficiency: 0.7 + Math.random() * 0.3,
      benchmark: 'VWAP'
    }));
  }

  private generateMockSlippageAnalysis() {
    const data = [];
    const now = new Date();

    for (let i = 0; i < 50; i++) {
      const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
      const side = Math.random() > 0.5 ? 'BUY' : 'SELL';
      const expectedPrice = 40000 + Math.random() * 5000;
      const actualPrice = expectedPrice * (1 + (Math.random() - 0.5) * 0.001);

      data.push({
        symbol: 'BTCUSDT',
        tradeSize: Math.random() * 50000,
        expectedPrice,
        executionPrice: actualPrice,
        slippage: side === 'BUY' ? actualPrice - expectedPrice : expectedPrice - actualPrice,
        slippagePercent: Math.abs((actualPrice - expectedPrice) / expectedPrice) * 100,
        volume: Math.random() * 1000000,
        side,
        timestamp: timestamp.toISOString(),
        marketCondition: Math.random() > 0.7 ? 'volatile' : Math.random() > 0.5 ? 'thin' : 'normal'
      });
    }

    return data;
  }

  private generateMockPerformanceForecast() {
    const periods = ['Next Week', 'Next Month', 'Next Quarter', 'Next 6 Months'];

    return periods.map(period => ({
      period,
      expectedReturn: (Math.random() - 0.3) * 10,
      confidence: 0.6 + Math.random() * 0.3,
      volatility: 5 + Math.random() * 10,
      sharpeRatio: 0.5 + Math.random() * 2,
      maxDrawdown: Math.random() * 20,
      winProbability: 0.5 + Math.random() * 0.3
    }));
  }

  private generateMockRevenueMetrics() {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
    const data = [];
    let cumulativeRevenue = 10000;

    months.forEach(month => {
      const tradingRevenue = (Math.random() - 0.2) * 5000;
      const fees = Math.abs(tradingRevenue) * 0.001;
      const netRevenue = tradingRevenue - fees;

      cumulativeRevenue += netRevenue;

      data.push({
        month,
        tradingRevenue,
        fees,
        netRevenue,
        activeStrategies: Math.floor(Math.random() * 5) + 2,
        totalVolume: Math.random() * 10000000,
        avgDailyReturn: (Math.random() - 0.3) * 2
      });
    });

    return data;
  }
}

export const apiService = new ApiService();