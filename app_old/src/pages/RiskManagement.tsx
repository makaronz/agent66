import { useState } from 'react';
import {
  Shield,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Activity,
  PieChart,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { cn } from '../utils';

const portfolioMetrics = {
  totalValue: 125000,
  totalPnL: 8750,
  totalPnLPercent: 7.5,
  dailyPnL: 1250,
  dailyPnLPercent: 1.2,
  maxDrawdown: -3.2,
  sharpeRatio: 1.85,
  winRate: 68.5,
  riskScore: 'Medium'
};

const riskLimits = {
  maxPositionSize: { current: 8500, limit: 10000, utilization: 85 },
  dailyLossLimit: { current: 350, limit: 500, utilization: 70 },
  maxDrawdown: { current: 3.2, limit: 10, utilization: 32 },
  leverage: { current: 2.1, limit: 3.0, utilization: 70 },
  concentration: { current: 15, limit: 25, utilization: 60 }
};

const positions = [
  {
    symbol: 'EURUSD',
    side: 'Long',
    size: 50000,
    entryPrice: 1.0850,
    currentPrice: 1.0875,
    pnl: 125,
    pnlPercent: 0.23,
    risk: 'Low',
    stopLoss: 1.0820,
    takeProfit: 1.0920
  },
  {
    symbol: 'GBPUSD',
    side: 'Short',
    size: 30000,
    entryPrice: 1.2650,
    currentPrice: 1.2625,
    pnl: 75,
    pnlPercent: 0.20,
    risk: 'Low',
    stopLoss: 1.2680,
    takeProfit: 1.2580
  },
  {
    symbol: 'USDJPY',
    side: 'Long',
    size: 75000,
    entryPrice: 148.50,
    currentPrice: 148.25,
    pnl: -187.5,
    pnlPercent: -0.17,
    risk: 'Medium',
    stopLoss: 147.80,
    takeProfit: 149.50
  },
  {
    symbol: 'XAUUSD',
    side: 'Long',
    size: 2.5,
    entryPrice: 2025.50,
    currentPrice: 2032.75,
    pnl: 18.13,
    pnlPercent: 0.36,
    risk: 'High',
    stopLoss: 2015.00,
    takeProfit: 2050.00
  }
];

const riskAlerts = [
  {
    id: 1,
    type: 'warning',
    message: 'Position size approaching limit (85% utilized)',
    symbol: 'Portfolio',
    timestamp: '5 minutes ago'
  },
  {
    id: 2,
    type: 'info',
    message: 'Stop loss triggered for AUDCAD position',
    symbol: 'AUDCAD',
    timestamp: '15 minutes ago'
  },
  {
    id: 3,
    type: 'error',
    message: 'High correlation detected between EURUSD and GBPUSD positions',
    symbol: 'Portfolio',
    timestamp: '1 hour ago'
  }
];

const correlationMatrix = [
  { pair1: 'EURUSD', pair2: 'GBPUSD', correlation: 0.85 },
  { pair1: 'EURUSD', pair2: 'USDJPY', correlation: -0.42 },
  { pair1: 'GBPUSD', pair2: 'USDJPY', correlation: -0.38 },
  { pair1: 'XAUUSD', pair2: 'EURUSD', correlation: 0.12 }
];

export default function RiskManagement() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1D');
  const [autoRiskManagement, setAutoRiskManagement] = useState(true);

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low':
        return 'text-green-600 bg-green-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'high':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization >= 90) return 'bg-red-500';
    if (utilization >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'info':
        return <CheckCircle className="h-4 w-4 text-blue-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getCorrelationColor = (correlation: number) => {
    const abs = Math.abs(correlation);
    if (abs >= 0.8) return 'text-red-600 bg-red-100';
    if (abs >= 0.5) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Risk Management</h1>
          <p className="text-gray-600">Portfolio overview, risk metrics, and position management</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Auto Risk Management</span>
            <button
              onClick={() => { setAutoRiskManagement(!autoRiskManagement); }}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                autoRiskManagement ? "bg-blue-600" : "bg-gray-200"
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                  autoRiskManagement ? "translate-x-6" : "translate-x-1"
                )}
              />
            </button>
          </div>
          <select
            value={selectedTimeframe}
            onChange={(e) => { setSelectedTimeframe(e.target.value); }}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="1D">1 Day</option>
            <option value="1W">1 Week</option>
            <option value="1M">1 Month</option>
            <option value="3M">3 Months</option>
          </select>
        </div>
      </div>

      {/* Portfolio Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Portfolio Value</p>
              <p className="text-2xl font-bold text-gray-900">${portfolioMetrics.totalValue.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <DollarSign className="h-6 w-6 text-blue-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-green-600">
            <TrendingUp className="h-4 w-4" />
            <span>+${portfolioMetrics.totalPnL.toLocaleString()} ({portfolioMetrics.totalPnLPercent}%)</span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Daily P&L</p>
              <p className="text-2xl font-bold text-gray-900">${portfolioMetrics.dailyPnL.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-green-100 rounded-full">
              <TrendingUp className="h-6 w-6 text-green-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-green-600">
            <TrendingUp className="h-4 w-4" />
            <span>+{portfolioMetrics.dailyPnLPercent}% today</span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Max Drawdown</p>
              <p className="text-2xl font-bold text-gray-900">{portfolioMetrics.maxDrawdown}%</p>
            </div>
            <div className="p-3 bg-red-100 rounded-full">
              <TrendingDown className="h-6 w-6 text-red-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-gray-600">
            <span>Within acceptable range</span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Risk Score</p>
              <p className="text-2xl font-bold text-gray-900">{portfolioMetrics.riskScore}</p>
            </div>
            <div className="p-3 bg-yellow-100 rounded-full">
              <Shield className="h-6 w-6 text-yellow-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-gray-600">
            <span>Sharpe: {portfolioMetrics.sharpeRatio} | Win Rate: {portfolioMetrics.winRate}%</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Limits */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
              <Target className="h-5 w-5" />
              <span>Risk Limits</span>
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-6">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Max Position Size</span>
                  <span className="text-sm text-gray-600">
                    ${riskLimits.maxPositionSize.current.toLocaleString()} / ${riskLimits.maxPositionSize.limit.toLocaleString()}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.maxPositionSize.utilization))}
                    style={{ width: `${riskLimits.maxPositionSize.utilization}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{riskLimits.maxPositionSize.utilization}% utilized</p>
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Daily Loss Limit</span>
                  <span className="text-sm text-gray-600">
                    ${riskLimits.dailyLossLimit.current} / ${riskLimits.dailyLossLimit.limit}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.dailyLossLimit.utilization))}
                    style={{ width: `${riskLimits.dailyLossLimit.utilization}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{riskLimits.dailyLossLimit.utilization}% utilized</p>
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Max Drawdown</span>
                  <span className="text-sm text-gray-600">
                    {riskLimits.maxDrawdown.current}% / {riskLimits.maxDrawdown.limit}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.maxDrawdown.utilization))}
                    style={{ width: `${riskLimits.maxDrawdown.utilization}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{riskLimits.maxDrawdown.utilization}% utilized</p>
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium text-gray-700">Leverage</span>
                  <span className="text-sm text-gray-600">
                    {riskLimits.leverage.current}x / {riskLimits.leverage.limit}x
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.leverage.utilization))}
                    style={{ width: `${riskLimits.leverage.utilization}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{riskLimits.leverage.utilization}% utilized</p>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Alerts */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5" />
              <span>Risk Alerts</span>
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {riskAlerts.map((alert) => (
                <div key={alert.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0 mt-0.5">
                    {getAlertIcon(alert.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <p className="text-xs text-gray-500">{alert.symbol}</p>
                      <span className="text-xs text-gray-400">•</span>
                      <p className="text-xs text-gray-500">{alert.timestamp}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Active Positions */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Active Positions</span>
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Symbol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Side
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Entry Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Current Price
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  P&L
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Level
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stop Loss
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Take Profit
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {positions.map((position, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {position.symbol}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className={cn(
                      "px-2 py-1 text-xs font-medium rounded-full",
                      position.side === 'Long' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    )}>
                      {position.side}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {position.size.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {position.entryPrice}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {position.currentPrice}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className={cn(
                      "flex items-center space-x-1",
                      position.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {position.pnl >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                      <span>${position.pnl} ({position.pnlPercent}%)</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={cn(
                      "px-2 py-1 text-xs font-medium rounded-full",
                      getRiskColor(position.risk)
                    )}>
                      {position.risk}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {position.stopLoss}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {position.takeProfit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Correlation Matrix */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
            <PieChart className="h-5 w-5" />
            <span>Position Correlation Matrix</span>
          </h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {correlationMatrix.map((item, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <span className="text-sm font-medium text-gray-900">
                    {item.pair1} / {item.pair2}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={cn(
                    "px-2 py-1 text-xs font-medium rounded-full",
                    getCorrelationColor(item.correlation)
                  )}>
                    {item.correlation > 0 ? '+' : ''}{item.correlation}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-500">
            <p>Correlation ranges from -1 (perfect negative) to +1 (perfect positive)</p>
            <p>High correlations (&gt;0.8) indicate increased portfolio risk</p>
          </div>
        </div>
      </div>
    </div>
  );
}