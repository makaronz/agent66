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
import { useAuth } from '@/hooks/useAuth';
import { useRealtime } from '@/hooks/useRealtime';
import LiveSignals from '@/components/realtime/LiveSignals';
import LiveTrades from '@/components/realtime/LiveTrades';
import RealtimeStatus from '@/components/realtime/RealtimeStatus';

// Mock data - replace with real API calls
const mockMarketData = [
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

export default function Dashboard() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const { user, profile } = useAuth();
  const { trades, signals, isConnected } = useRealtime();

  useEffect(() => {
    const timer = setInterval(() => { setCurrentTime(new Date()); }, 1000);
    return () => { clearInterval(timer); };
  }, []);

  // Calculate real P&L from live trades if available, otherwise use mock data
  const realTrades = trades.filter(trade => trade.status === 'filled');
  const totalPnL = realTrades.length > 0 
    ? realTrades.reduce((sum, trade) => {
        // Simple P&L calculation - in real app this would be more complex
        const pnl = trade.side === 'buy' ? (trade.price * trade.quantity * 0.01) : (trade.price * trade.quantity * -0.01);
        return sum + pnl;
      }, 0)
    : mockPositions.reduce((sum, pos) => sum + pos.pnl, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trading Dashboard</h1>
          <p className="text-gray-600">
            Witaj {profile?.full_name || user?.email || 'Trader'}! Real-time market overview and performance metrics
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <RealtimeStatus />
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <Clock className="h-4 w-4" />
            <span>{currentTime.toLocaleTimeString()}</span>
          </div>
        </div>
      </div>

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
                  totalPnL >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  ${totalPnL.toFixed(2)}
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
                <dd className="text-lg font-medium text-gray-900">1.67</dd>
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
                <dd className="text-lg font-medium text-gray-900">-3.2%</dd>
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
                <dt className="text-sm font-medium text-gray-500 truncate">Aktywne sygnały</dt>
                <dd className="text-lg font-medium text-gray-900">{signals.length}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Data Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Signals */}
        <LiveSignals className="" maxSignals={10} />
        
        {/* Live Trades */}
        <LiveTrades className="" maxTrades={10} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Market Overview */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Market Overview</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {mockMarketData.map((market) => (
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
              {mockPositions.map((position, index) => (
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
            {mockSystemHealth.map((service) => (
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