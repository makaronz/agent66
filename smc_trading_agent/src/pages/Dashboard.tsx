import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  BarChart3
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService, type MarketData, type Position, type SystemHealth, type PerformanceMetrics } from '@/services/api';

export default function Dashboard() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [marketData, setMarketData] = useState<MarketData[]>([]);
  const [positions, setPositions] = useState<{ positions: Position[]; totalPnL: number; totalPositions: number }>({
    positions: [],
    totalPnL: 0,
    totalPositions: 0
  });
  const [systemHealth, setSystemHealth] = useState<{ components: SystemHealth[]; overall: string }>({
    components: [],
    overall: 'unknown'
  });
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tradingMode] = useState<'paper' | 'real'>('paper'); // Trading mode indicator

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch data from API
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [marketDataRes, positionsRes, healthRes, performanceRes] = await Promise.all([
          apiService.getMarketData(),
          apiService.getPositions(),
          apiService.getSystemHealth(),
          apiService.getPerformanceMetrics()
        ]);

        setMarketData(marketDataRes);
        setPositions(positionsRes);
        setSystemHealth(healthRes);
        setPerformance(performanceRes);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Failed to load data. Using demo mode.');

        // Fallback to demo mode
        setMarketData([
          { symbol: 'BTCUSDT', price: 43250.50, change: 2.45, volume: '1.2B' },
          { symbol: 'ETHUSDT', price: 2650.75, change: -1.23, volume: '890M' },
          { symbol: 'ADAUSDT', price: 0.485, change: 3.67, volume: '245M' },
          { symbol: 'SOLUSDT', price: 98.32, change: 1.89, volume: '156M' },
        ]);
        setPositions({
          positions: [
            { symbol: 'BTCUSDT', side: 'LONG', size: 0.5, entryPrice: 42800, currentPrice: 43250.50, pnl: 225.25, pnlPercent: 1.05 },
            { symbol: 'ETHUSDT', side: 'SHORT', size: 2.0, entryPrice: 2680, currentPrice: 2650.75, pnl: 58.50, pnlPercent: 1.09 },
          ],
          totalPnL: 283.75,
          totalPositions: 2
        });
        setSystemHealth({
          components: [
            { name: 'Data Pipeline', status: 'healthy', latency: '12ms' },
            { name: 'SMC Detection', status: 'healthy', latency: '8ms' },
            { name: 'Execution Engine', status: 'warning', latency: '45ms' },
            { name: 'Risk Manager', status: 'healthy', latency: '5ms' },
          ],
          overall: 'warning'
        });
        setPerformance({
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
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh data every 2 seconds
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trading Dashboard</h1>
          <p className="text-gray-600">Real-time market overview and performance metrics</p>
        </div>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <Clock className="h-4 w-4" />
          <span>{currentTime.toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Trading Mode Banner */}
      {tradingMode === 'paper' && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-md">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <AlertCircle className="h-5 w-5 text-yellow-400" />
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700">
                <strong className="font-semibold">PAPER TRADING MODE</strong> - All trades are simulated with live market prices. No real capital at risk.
              </p>
            </div>
          </div>
        </div>
      )}

      {tradingMode === 'real' && (
        <div className="bg-red-50 border-l-4 border-red-600 p-4 rounded-md">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <AlertCircle className="h-5 w-5 text-red-600" />
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">
                <strong className="font-semibold">⚠️ LIVE TRADING MODE</strong> - Real capital at risk. Trades execute on live exchange.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Loading/ Error Status */}
      {loading && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <Activity className="h-5 w-5 text-blue-400" />
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                Loading trading data... {error && '(Using demo mode)'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <DollarSign className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Total P&L</dt>
                <dd className={cn(
                  "text-lg font-medium",
                  positions.totalPnL >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  ${positions.totalPnL.toFixed(2)}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <TrendingUp className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Sharpe Ratio</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {performance && performance.sharpeRatio !== undefined ? performance.sharpeRatio.toFixed(2) : '1.67'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <TrendingDown className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Max Drawdown</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {performance && performance.maxDrawdown !== undefined ? `${performance.maxDrawdown.toFixed(1)}%` : '-3.2%'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Activity className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Win Rate</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {performance && performance.winRate !== undefined ? `${performance.winRate.toFixed(1)}%` : '68.5%'}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market Overview */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Market Overview</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {marketData.map((market) => (
                <div key={market.symbol} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      <BarChart3 className="h-5 w-5 text-gray-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{market.symbol}</p>
                      <p className="text-xs text-gray-500">Vol: {market.volume}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">
                      ${market.price.toLocaleString()}
                    </p>
                    <p className={cn(
                      "text-xs",
                      market.change >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      {market.change >= 0 ? '+' : ''}{market.change}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Active Positions */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Active Positions</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {positions.positions.map((position, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-gray-900">{position.symbol}</span>
                      <span className={cn(
                        "px-2 py-1 text-xs font-medium rounded",
                        position.side === 'LONG' 
                          ? "bg-green-100 text-green-800" 
                          : "bg-red-100 text-red-800"
                      )}>
                        {position.side}
                      </span>
                    </div>
                    <div className={cn(
                      "text-sm font-medium",
                      position.pnl >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      ${position.pnl.toFixed(2)} ({position.pnlPercent.toFixed(2)}%)
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-xs text-gray-500">
                    <div>
                      <span className="block">Size</span>
                      <span className="text-gray-900">{position.size}</span>
                    </div>
                    <div>
                      <span className="block">Entry</span>
                      <span className="text-gray-900">${position.entryPrice.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="block">Current</span>
                      <span className="text-gray-900">${position.currentPrice.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">System Health</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {systemHealth.components.map((service) => (
              <div key={service.name} className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  {service.status === 'healthy' ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-yellow-500" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {service.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {service.latency}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}