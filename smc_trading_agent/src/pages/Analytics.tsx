import { useState, useEffect, useRef } from 'react';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Calendar,
  Download,
  Play,
  Settings,
  Target,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService, type EquityPoint } from '@/services/api';
import AdvancedAnalytics from '@/components/AdvancedAnalytics';
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

// InfoTooltip component (renamed to avoid conflict with recharts Tooltip)
interface InfoTooltipProps {
  content: string;
  children: React.ReactNode;
}

function InfoTooltip({ content, children }: InfoTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = (e: React.MouseEvent) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setPosition({ x: e.clientX, y: e.clientY });
    setIsVisible(true);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isVisible) {
      setPosition({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseLeave = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(false);
    }, 100);
  };

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={handleMouseEnter}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {isVisible && (
        <div
          className="fixed z-50 px-4 py-3 text-sm text-white bg-gray-900 rounded-lg shadow-lg pointer-events-none"
          style={{
            left: `${Math.min(position.x + 15, window.innerWidth - 350)}px`,
            top: `${position.y + 15}px`,
            maxWidth: '320px',
            minWidth: '280px',
            lineHeight: '1.5',
            whiteSpace: 'normal',
            wordWrap: 'break-word',
            overflowWrap: 'break-word'
          }}
        >
          <div style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
            {content}
          </div>
        </div>
      )}
    </div>
  );
}

// Definitions for metrics and strategies
const definitions = {
  'Total Return': 'The total percentage return of the portfolio over the selected time period. Calculated as (Final Value - Initial Value) / Initial Value × 100%.',
  'Sharpe Ratio': 'A measure of risk-adjusted return. It indicates how much excess return you receive for the extra volatility you endure. Higher values indicate better risk-adjusted performance. Generally, a Sharpe ratio above 1 is considered good, above 2 is very good, and above 3 is excellent.',
  'Max Drawdown': 'The maximum peak-to-trough decline in portfolio value during the selected period. It represents the largest percentage loss from a peak value to a subsequent low. Lower (less negative) values indicate better downside protection.',
  'Win Rate': 'The percentage of profitable trades out of all trades executed. Calculated as (Winning Trades / Total Trades) × 100%. A higher win rate indicates more consistent profitability.',
  'SMC Momentum': 'A trading strategy that identifies and trades on momentum patterns using Smart Money Concepts (SMC). It looks for institutional order flow and follows the direction of smart money movements.',
  'Order Block Hunter': 'A strategy that specifically targets order blocks - areas where large institutional orders were placed. These zones often act as strong support or resistance levels and provide high-probability trading opportunities.',
  'Liquidity Sweep': 'A strategy that capitalizes on liquidity sweeps - when price moves to collect stop losses before reversing direction. This pattern is commonly used by institutions to gather liquidity before major moves.',
  'CHoCH Detector': 'Change of Character (CHoCH) detection strategy. CHoCH occurs when market structure shifts, indicating a potential change in institutional sentiment and trend direction.',
  'Profit Factor': 'The ratio of gross profit to gross loss. Calculated as Total Profits / Total Losses. A profit factor above 1.0 indicates profitability. Values above 2.0 are considered excellent.',
  'Calmar Ratio': 'The ratio of annualized return to maximum drawdown. It measures return per unit of risk. Higher values indicate better risk-adjusted returns. A Calmar ratio above 1 is good, above 2 is excellent.',
  'Avg Trade': 'The average percentage return per trade. Calculated as Total Return / Number of Trades. This metric helps assess the consistency of trading performance.',
  'Total Trades': 'The total number of trades executed during the backtest period. This includes both winning and losing trades.',
  'Value at Risk (95%)': 'The maximum expected loss at a 95% confidence level over a specified time period. It estimates the worst-case scenario loss that could occur under normal market conditions.',
  'Expected Shortfall': 'Also known as Conditional Value at Risk (CVaR). It measures the average loss that occurs in the worst 5% of scenarios, providing a more conservative risk estimate than VaR.',
  'Volatility (Annualized)': 'A measure of price variability, expressed as an annualized percentage. Higher volatility indicates greater price swings. It helps assess the riskiness of the trading strategy.',
  'Beta (vs BTC)': 'A measure of how the portfolio\'s returns move relative to Bitcoin. A beta of 1.0 means the portfolio moves in line with BTC. Values above 1 indicate higher volatility than BTC, below 1 indicates lower volatility.',
  'Correlation (vs Market)': 'A measure of how closely the portfolio\'s returns move with the overall market. Values range from -1 (perfect negative correlation) to +1 (perfect positive correlation). Lower correlation indicates better diversification.'
};

export default function Analytics() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1Y');
  const [,] = useState('All Strategies');
  const [showAdvancedAnalytics, setShowAdvancedAnalytics] = useState(false);
  const [backtestRunning, setBacktestRunning] = useState(false);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [equityLoading, setEquityLoading] = useState(true);
  const [performanceMetrics, setPerformanceMetrics] = useState<any>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);

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

  // Fetch performance metrics
  useEffect(() => {
    const fetchPerformanceMetrics = async () => {
      try {
        setMetricsLoading(true);
        const data = await apiService.getPerformanceMetrics();
        setPerformanceMetrics(data);
      } catch (error) {
        console.error('Error fetching performance metrics:', error);
      } finally {
        setMetricsLoading(false);
      }
    };

    fetchPerformanceMetrics();
    // Refresh every 30 seconds
    const interval = setInterval(fetchPerformanceMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

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
          <div className="mt-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-gray-700">
              <strong>What is Backtesting?</strong> Backtesting is the process of testing a trading strategy on historical data to evaluate its performance. 
              This section provides comprehensive analytics including performance metrics, risk analysis, and strategy comparisons. 
              Use the backtest feature to simulate how your trading strategies would have performed in the past, helping you optimize 
              parameters and identify the most profitable approaches before risking real capital.
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowAdvancedAnalytics(!showAdvancedAnalytics)}
            className={cn(
              "flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors",
              showAdvancedAnalytics
                ? "bg-green-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            )}
          >
            <BarChart3 className="h-4 w-4" />
            <span>{showAdvancedAnalytics ? 'Basic Analytics' : 'Advanced Analytics'}</span>
          </button>

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
                <dt className="text-sm font-medium text-gray-500 truncate flex items-center gap-1">
                  <InfoTooltip content={definitions['Total Return']}>
                    <span>Total Return</span>
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </InfoTooltip>
                </dt>
                <dd className="text-lg font-medium text-green-600">
                  {metricsLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : performanceMetrics ? (
                    <span>+{performanceMetrics.dailyReturn?.toFixed(2) || '0.00'}%</span>
                  ) : (
                    <span>+0.00%</span>
                  )}
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
                <dt className="text-sm font-medium text-gray-500 truncate flex items-center gap-1">
                  <InfoTooltip content={definitions['Sharpe Ratio']}>
                    <span>Sharpe Ratio</span>
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </InfoTooltip>
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {metricsLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : performanceMetrics ? (
                    <span>{performanceMetrics.sharpeRatio?.toFixed(2) || '0.00'}</span>
                  ) : (
                    <span>0.00</span>
                  )}
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
                <dt className="text-sm font-medium text-gray-500 truncate flex items-center gap-1">
                  <InfoTooltip content={definitions['Max Drawdown']}>
                    <span>Max Drawdown</span>
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </InfoTooltip>
                </dt>
                <dd className="text-lg font-medium text-red-600">
                  {metricsLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : performanceMetrics ? (
                    <span>{performanceMetrics.maxDrawdown?.toFixed(2) || '0.00'}%</span>
                  ) : (
                    <span>0.00%</span>
                  )}
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
                <dt className="text-sm font-medium text-gray-500 truncate flex items-center gap-1">
                  <InfoTooltip content={definitions['Win Rate']}>
                    <span>Win Rate</span>
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </InfoTooltip>
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {metricsLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : performanceMetrics ? (
                    <span>{performanceMetrics.winRate?.toFixed(1) || '0.0'}%</span>
                  ) : (
                    <span>0.0%</span>
                  )}
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
                      <InfoTooltip content={definitions[strategy.name as keyof typeof definitions] || 'Trading strategy performance metrics'}>
                        <span className="text-sm font-medium text-gray-900 flex items-center gap-1">
                          {strategy.name}
                          <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                        </span>
                      </InfoTooltip>
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
                <div className="text-2xl font-bold text-gray-900">
                  {metricsLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : performanceMetrics ? (
                    performanceMetrics.totalTrades || 0
                  ) : (
                    0
                  )}
                </div>
                <InfoTooltip content={definitions['Total Trades']}>
                  <div className="text-sm text-gray-500 flex items-center justify-center gap-1">
                    Total Trades
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </div>
                </InfoTooltip>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {metricsLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : performanceMetrics ? (
                    <span>+{((performanceMetrics.totalPnL / (performanceMetrics.totalTrades || 1)) * 100)?.toFixed(2) || '0.00'}%</span>
                  ) : (
                    <span>+0.00%</span>
                  )}
                </div>
                <InfoTooltip content={definitions['Avg Trade']}>
                  <div className="text-sm text-gray-500 flex items-center justify-center gap-1">
                    Avg Trade
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </div>
                </InfoTooltip>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {metricsLoading ? (
                    <span className="animate-pulse">Loading...</span>
                  ) : performanceMetrics ? (
                    <span>{performanceMetrics.profitFactor?.toFixed(2) || '0.00'}</span>
                  ) : (
                    <span>0.00</span>
                  )}
                </div>
                <InfoTooltip content={definitions['Profit Factor']}>
                  <div className="text-sm text-gray-500 flex items-center justify-center gap-1">
                    Profit Factor
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </div>
                </InfoTooltip>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{mockBacktestResults.calmarRatio}</div>
                <InfoTooltip content={definitions['Calmar Ratio']}>
                  <div className="text-sm text-gray-500 flex items-center justify-center gap-1">
                    Calmar Ratio
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </div>
                </InfoTooltip>
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
                <InfoTooltip content={definitions['Value at Risk (95%)']}>
                  <span className="text-sm text-gray-600 flex items-center gap-1">
                    Value at Risk (95%)
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </span>
                </InfoTooltip>
                <span className="text-sm font-medium text-red-600">-2.4%</span>
              </div>
              <div className="flex justify-between items-center">
                <InfoTooltip content={definitions['Expected Shortfall']}>
                  <span className="text-sm text-gray-600 flex items-center gap-1">
                    Expected Shortfall
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </span>
                </InfoTooltip>
                <span className="text-sm font-medium text-red-600">-3.8%</span>
              </div>
              <div className="flex justify-between items-center">
                <InfoTooltip content={definitions['Volatility (Annualized)']}>
                  <span className="text-sm text-gray-600 flex items-center gap-1">
                    Volatility (Annualized)
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </span>
                </InfoTooltip>
                <span className="text-sm font-medium text-gray-900">14.6%</span>
              </div>
              <div className="flex justify-between items-center">
                <InfoTooltip content={definitions['Beta (vs BTC)']}>
                  <span className="text-sm text-gray-600 flex items-center gap-1">
                    Beta (vs BTC)
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </span>
                </InfoTooltip>
                <span className="text-sm font-medium text-gray-900">0.78</span>
              </div>
              <div className="flex justify-between items-center">
                <InfoTooltip content={definitions['Correlation (vs Market)']}>
                  <span className="text-sm text-gray-600 flex items-center gap-1">
                    Correlation (vs Market)
                    <Info className="h-3 w-3 text-gray-400 hover:text-gray-600 cursor-help" />
                  </span>
                </InfoTooltip>
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

      {/* Advanced Analytics Section */}
      {showAdvancedAnalytics && (
        <div className="mt-6">
          <AdvancedAnalytics />
        </div>
      )}
    </div>
  );
}