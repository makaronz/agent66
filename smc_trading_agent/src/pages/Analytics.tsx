import { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Calendar,
  Download,
  Play,
  Settings,
  Target
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService, type EquityPoint } from '@/services/api';
import {
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

// Mock backtest results
const mockBacktestResults = {
  totalReturn: 24.5,
  sharpeRatio: 1.67,
  maxDrawdown: -8.2,
  winRate: 68.5,
  totalTrades: 156,
  avgTrade: 0.87,
  profitFactor: 2.34,
  calmarRatio: 2.98
};

// Mock equity curve data for future chart implementation
// const mockEquityCurve = [
//   { date: '2024-01', value: 10000 },
//   { date: '2024-02', value: 10250 },
//   { date: '2024-03', value: 10180 },
//   { date: '2024-04', value: 10420 },
//   { date: '2024-05', value: 10680 },
//   { date: '2024-06', value: 10590 },
//   { date: '2024-07', value: 10890 },
//   { date: '2024-08', value: 11120 },
//   { date: '2024-09', value: 11050 },
//   { date: '2024-10', value: 11380 },
//   { date: '2024-11', value: 11620 },
//   { date: '2024-12', value: 12450 }
// ];

const mockStrategies = [
  { name: 'SMC Momentum', returns: 18.5, sharpe: 1.45, drawdown: -6.2, active: true },
  { name: 'Order Block Hunter', returns: 22.1, sharpe: 1.78, drawdown: -8.1, active: true },
  { name: 'Liquidity Sweep', returns: 15.3, sharpe: 1.23, drawdown: -4.8, active: false },
  { name: 'CHoCH Detector', returns: 28.7, sharpe: 2.01, drawdown: -9.5, active: true }
];

export default function Analytics() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1Y');
  const [,] = useState('All Strategies');
  const [backtestRunning, setBacktestRunning] = useState(false);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [equityLoading, setEquityLoading] = useState(true);

  // Fetch equity curve data
  useEffect(() => {
    const fetchEquityCurve = async () => {
      try {
        setEquityLoading(true);
        const data = await apiService.getEquityCurve(selectedTimeframe);
        setEquityCurve(data);
      } catch (error) {
        console.error('Error fetching equity curve:', error);
      } finally {
        setEquityLoading(false);
      }
    };

    fetchEquityCurve();
    // Refresh every 30 seconds
    const interval = setInterval(fetchEquityCurve, 30000);
    return () => clearInterval(interval);
  }, [selectedTimeframe]);

  const handleRunBacktest = () => {
    setBacktestRunning(true);
    // Simulate backtest running
    setTimeout(() => {
      setBacktestRunning(false);
      // Refresh equity curve after backtest
      apiService.getEquityCurve(selectedTimeframe).then(setEquityCurve).catch(console.error);
    }, 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics & Backtesting</h1>
          <p className="text-gray-600">Historical performance analysis and strategy optimization</p>
        </div>
        <div className="flex items-center space-x-3">
          <select
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value)}
            className="text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="1M">1 Month</option>
            <option value="3M">3 Months</option>
            <option value="6M">6 Months</option>
            <option value="1Y">1 Year</option>
            <option value="ALL">All Time</option>
          </select>
          <button
            onClick={handleRunBacktest}
            disabled={backtestRunning}
            className={cn(
              "flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors",
              backtestRunning
                ? "bg-gray-400 text-white cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            )}
          >
            <Play className="h-4 w-4" />
            <span>{backtestRunning ? 'Running...' : 'Run Backtest'}</span>
          </button>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <TrendingUp className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Total Return</dt>
                <dd className="text-lg font-medium text-green-600">
                  +{mockBacktestResults.totalReturn}%
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Target className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Sharpe Ratio</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {mockBacktestResults.sharpeRatio}
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
                <dd className="text-lg font-medium text-red-600">
                  {mockBacktestResults.maxDrawdown}%
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <BarChart3 className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Win Rate</dt>
                <dd className="text-lg font-medium text-gray-900">
                  {mockBacktestResults.winRate}%
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Equity Curve */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">Equity Curve</h3>
              <div className="flex items-center space-x-2">
                <Calendar className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-500">{selectedTimeframe}</span>
              </div>
            </div>
          </div>
          <div className="p-6">
            {equityLoading ? (
              <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4 animate-pulse" />
                  <p className="text-gray-500">Loading equity curve...</p>
                </div>
              </div>
            ) : equityCurve.length === 0 ? (
              <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No equity data available</p>
                </div>
              </div>
            ) : (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityCurve.map(point => ({
                    date: new Date(point.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                    value: point.value,
                    drawdown: point.drawdown || 0
                  }))}>
                    <defs>
                      <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis 
                      dataKey="date" 
                      stroke="#6b7280"
                      fontSize={12}
                      tick={{ fill: '#6b7280' }}
                      interval="preserveStartEnd"
                    />
                    <YAxis 
                      yAxisId="left"
                      stroke="#6b7280"
                      fontSize={12}
                      tick={{ fill: '#6b7280' }}
                      domain={['auto', 'auto']}
                      tickFormatter={(value) => `$${value.toLocaleString()}`}
                    />
                    <YAxis 
                      yAxisId="right"
                      orientation="right"
                      stroke="#ef4444"
                      fontSize={12}
                      tick={{ fill: '#ef4444' }}
                      domain={['auto', 0]}
                      tickFormatter={(value) => `${value.toFixed(1)}%`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#f3f4f6'
                      }}
                      formatter={(value: any, name: string) => {
                        if (name === 'value') {
                          return [`$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Portfolio Value'];
                        }
                        if (name === 'drawdown') {
                          return [`${Number(value).toFixed(2)}%`, 'Drawdown'];
                        }
                        return [value, name];
                      }}
                    />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="value"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#colorValue)"
                      name="value"
                    />
                    <Area
                      yAxisId="right"
                      type="monotone"
                      dataKey="drawdown"
                      stroke="#ef4444"
                      strokeWidth={1}
                      strokeDasharray="5 5"
                      fill="url(#colorDrawdown)"
                      name="drawdown"
                    />
                    <Legend 
                      formatter={(value) => {
                        if (value === 'value') return 'Portfolio Value';
                        if (value === 'drawdown') return 'Drawdown';
                        return value;
                      }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* Strategy Performance */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Strategy Performance</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {mockStrategies.map((strategy, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <div className={cn(
                        "w-3 h-3 rounded-full",
                        strategy.active ? "bg-green-500" : "bg-gray-300"
                      )} />
                      <span className="text-sm font-medium text-gray-900">{strategy.name}</span>
                    </div>
                    <span className={cn(
                      "text-sm font-medium",
                      strategy.returns >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      +{strategy.returns}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                    <div>
                      <span className="block">Sharpe</span>
                      <span className="text-gray-900">{strategy.sharpe}</span>
                    </div>
                    <div>
                      <span className="block">Drawdown</span>
                      <span className="text-red-600">{strategy.drawdown}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Trade Statistics */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Trade Statistics</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{mockBacktestResults.totalTrades}</div>
                <div className="text-sm text-gray-500">Total Trades</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">+{mockBacktestResults.avgTrade}%</div>
                <div className="text-sm text-gray-500">Avg Trade</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{mockBacktestResults.profitFactor}</div>
                <div className="text-sm text-gray-500">Profit Factor</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{mockBacktestResults.calmarRatio}</div>
                <div className="text-sm text-gray-500">Calmar Ratio</div>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Metrics */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Risk Analysis</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Value at Risk (95%)</span>
                <span className="text-sm font-medium text-red-600">-2.4%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Expected Shortfall</span>
                <span className="text-sm font-medium text-red-600">-3.8%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Volatility (Annualized)</span>
                <span className="text-sm font-medium text-gray-900">14.6%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Beta (vs BTC)</span>
                <span className="text-sm font-medium text-gray-900">0.78</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Correlation (vs Market)</span>
                <span className="text-sm font-medium text-gray-900">0.65</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Backtest Configuration */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900">Backtest Configuration</h3>
            <button className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-700">
              <Settings className="h-4 w-4" />
              <span>Configure</span>
            </button>
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Initial Capital
              </label>
              <input
                type="number"
                defaultValue="10000"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Commission Rate
              </label>
              <input
                type="number"
                defaultValue="0.1"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Slippage (bps)
              </label>
              <input
                type="number"
                defaultValue="5"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="mt-6 flex justify-end space-x-3">
            <button className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors">
              <Download className="h-4 w-4" />
              <span>Export Results</span>
            </button>
            <button
              onClick={handleRunBacktest}
              disabled={backtestRunning}
              className={cn(
                "flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors",
                backtestRunning
                  ? "bg-gray-400 text-white cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              )}
            >
              <Play className="h-4 w-4" />
              <span>{backtestRunning ? 'Running Backtest...' : 'Run Full Backtest'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}