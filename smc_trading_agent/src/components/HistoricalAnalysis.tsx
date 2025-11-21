import React, { useState, useEffect, useMemo } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, ScatterChart, Scatter, ComposedChart,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Treemap, ReferenceLine, ReferenceArea
} from 'recharts';
import {
  Calendar, TrendingUp, TrendingDown, BarChart3, Activity, Target,
  Download, Filter, RefreshCw, Settings, Info, Clock, DollarSign,
  Percent, Zap, AlertTriangle, ChevronDown, ChevronUp, Maximize2
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
interface HistoricalData {
  date: string;
  portfolio_value: number;
  returns: number;
  drawdown: number;
  sharpe_ratio: number;
  volatility: number;
  var_95: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
}

interface BacktestResult {
  strategy_name: string;
  period: string;
  starting_capital: number;
  ending_capital: number;
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  calmar_ratio: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_trade: number;
  best_trade: number;
  worst_trade: number;
  volatility: number;
  beta: number;
  alpha: number;
}

interface MarketRegime {
  start_date: string;
  end_date: string;
  regime_type: 'bull' | 'bear' | 'sideways' | 'volatile';
  performance: number;
  volatility: number;
  duration_days: number;
  characteristics: string[];
}

interface PerformanceAttribution {
  category: string;
  contribution: number;
  contribution_pct: number;
  breakdown: {
    name: string;
    value: number;
    percentage: number;
  }[];
}

const HistoricalAnalysis: React.FC = () => {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1Y');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [analysisType, setAnalysisType] = useState<'overview' | 'backtest' | 'regimes' | 'attribution'>('overview');
  const [isLoading, setIsLoading] = useState(false);
  const [comparisonMode, setComparisonMode] = useState(false);
  const [showStatistics, setShowStatistics] = useState(true);

  // Generate mock historical data
  const historicalData: HistoricalData[] = useMemo(() => {
    const days = analysisType === 'overview' ? 365 : selectedTimeframe === '1M' ? 30 : selectedTimeframe === '3M' ? 90 : selectedTimeframe === '6M' ? 180 : 365;

    return Array.from({ length: days }, (_, i) => {
      const baseDate = new Date();
      baseDate.setDate(baseDate.getDate() - (days - i));

      const baseValue = 10000;
      const dailyReturn = (Math.random() - 0.48) * 0.03; // Slightly positive bias
      const trend = i * 0.0003; // Upward trend
      const value = baseValue * (1 + trend + Math.sin(i * 0.1) * 0.05) * (1 + dailyReturn);

      const maxValues = Array.from({ length: i + 1 }, (_, j) =>
        baseValue * (1 + j * 0.0003 + Math.sin(j * 0.1) * 0.05)
      );

      const drawdownValue = Math.max(0, (Math.max(...maxValues) - value) / value * 100);

      return {
        date: baseDate.toISOString().split('T')[0],
        portfolio_value: value,
        returns: dailyReturn * 100,
        drawdown: drawdownValue,
        sharpe_ratio: 1.2 + Math.random() * 0.8,
        volatility: 12 + Math.random() * 8,
        var_95: -1.5 - Math.random() * 2,
        max_drawdown: -3 - Math.random() * 7,
        win_rate: 0.6 + Math.random() * 0.2,
        profit_factor: 1.5 + Math.random() * 1.5,
        total_trades: Math.floor(Math.random() * 5),
        winning_trades: Math.floor(Math.random() * 3),
        losing_trades: Math.floor(Math.random() * 2)
      };
    });
  }, [selectedTimeframe, analysisType]);

  // Mock backtest results
  const backtestResults: BacktestResult[] = [
    {
      strategy_name: 'SMC Momentum',
      period: '1 Year',
      starting_capital: 10000,
      ending_capital: 12850,
      total_return: 28.5,
      annualized_return: 28.5,
      sharpe_ratio: 1.67,
      max_drawdown: -8.2,
      calmar_ratio: 3.48,
      win_rate: 68.5,
      profit_factor: 2.34,
      total_trades: 156,
      avg_trade: 0.87,
      best_trade: 5.2,
      worst_trade: -2.8,
      volatility: 14.3,
      beta: 0.85,
      alpha: 12.3
    },
    {
      strategy_name: 'Order Block Hunter',
      period: '1 Year',
      starting_capital: 10000,
      ending_capital: 13210,
      total_return: 32.1,
      annualized_return: 32.1,
      sharpe_ratio: 1.89,
      max_drawdown: -9.8,
      calmar_ratio: 3.28,
      win_rate: 72.3,
      profit_factor: 2.89,
      total_trades: 89,
      avg_trade: 1.52,
      best_trade: 7.8,
      worst_trade: -3.1,
      volatility: 16.7,
      beta: 0.92,
      alpha: 15.6
    },
    {
      strategy_name: 'Liquidity Sweep',
      period: '1 Year',
      starting_capital: 10000,
      ending_capital: 11890,
      total_return: 18.9,
      annualized_return: 18.9,
      sharpe_ratio: 1.34,
      max_drawdown: -5.6,
      calmar_ratio: 3.37,
      win_rate: 64.2,
      profit_factor: 2.12,
      total_trades: 234,
      avg_trade: 0.45,
      best_trade: 3.2,
      worst_trade: -1.9,
      volatility: 11.8,
      beta: 0.73,
      alpha: 8.7
    }
  ];

  // Mock market regimes
  const marketRegimes: MarketRegime[] = [
    {
      start_date: '2024-01-01',
      end_date: '2024-02-15',
      regime_type: 'bull',
      performance: 8.2,
      volatility: 12.3,
      duration_days: 45,
      characteristics: ['Strong uptrend', 'High volume', 'Low volatility', 'Momentum driving']
    },
    {
      start_date: '2024-02-16',
      end_date: '2024-03-20',
      regime_type: 'volatile',
      performance: -2.1,
      volatility: 24.7,
      duration_days: 33,
      characteristics: ['High volatility', 'Uncertainty', 'Mixed signals', 'Range-bound']
    },
    {
      start_date: '2024-03-21',
      end_date: '2024-05-10',
      regime_type: 'bull',
      performance: 12.8,
      volatility: 15.2,
      duration_days: 51,
      characteristics: ['Recovery', 'Steady growth', 'Increasing volume', 'Trend following']
    },
    {
      start_date: '2024-05-11',
      end_date: '2024-06-30',
      regime_type: 'sideways',
      performance: 1.3,
      volatility: 9.8,
      duration_days: 50,
      characteristics: ['Range trading', 'Mean reversion', 'Low volume', 'Consolidation']
    }
  ];

  // Mock performance attribution
  const performanceAttribution: PerformanceAttribution[] = [
    {
      category: 'Strategy Returns',
      contribution: 18.5,
      contribution_pct: 65.2,
      breakdown: [
        { name: 'SMC Momentum', value: 8.2, percentage: 28.9 },
        { name: 'Order Block', value: 6.8, percentage: 24.0 },
        { name: 'Liquidity Sweep', value: 3.5, percentage: 12.3 }
      ]
    },
    {
      category: 'Market Timing',
      contribution: 4.2,
      contribution_pct: 14.8,
      breakdown: [
        { name: 'Entry Timing', value: 2.8, percentage: 9.9 },
        { name: 'Exit Timing', value: 1.4, percentage: 4.9 }
      ]
    },
    {
      category: 'Risk Management',
      contribution: 3.8,
      contribution_pct: 13.4,
      breakdown: [
        { name: 'Stop Loss', value: 2.1, percentage: 7.4 },
        { name: 'Position Sizing', value: 1.7, percentage: 6.0 }
      ]
    },
    {
      category: 'Market Beta',
      contribution: 1.9,
      contribution_pct: 6.7,
      breakdown: [
        { name: 'Market Correlation', value: 1.9, percentage: 6.7 }
      ]
    }
  ];

  // Calculated statistics
  const statistics = useMemo(() => {
    if (historicalData.length === 0) return {};

    const returns = historicalData.map(d => d.returns);
    const totalReturn = ((historicalData[historicalData.length - 1].portfolio_value - historicalData[0].portfolio_value) / historicalData[0].portfolio_value) * 100;
    const annualizedReturn = Math.pow(1 + totalReturn / 100, 365 / historicalData.length) - 1;
    const volatility = Math.sqrt(returns.reduce((sum, r) => sum + Math.pow(r - (returns.reduce((s, r) => s + r, 0) / returns.length), 2), 0) / returns.length) * Math.sqrt(365) * 100;
    const sharpeRatio = annualizedReturn / (volatility / 100);
    const maxDrawdown = Math.min(...historicalData.map(d => d.max_drawdown));
    const avgWinRate = historicalData.reduce((sum, d) => sum + d.win_rate, 0) / historicalData.length * 100;
    const profitFactor = historicalData.reduce((sum, d) => sum + d.profit_factor, 0) / historicalData.length;

    return {
      totalReturn,
      annualizedReturn: annualizedReturn * 100,
      volatility,
      sharpeRatio,
      maxDrawdown,
      avgWinRate,
      profitFactor,
      totalTrades: historicalData.reduce((sum, d) => sum + d.total_trades, 0),
      winRate: avgWinRate,
      calmarRatio: annualizedReturn * 100 / Math.abs(maxDrawdown)
    };
  }, [historicalData]);

  const handleExportData = () => {
    const csvContent = [
      ['Date', 'Portfolio Value', 'Returns', 'Drawdown', 'Sharpe Ratio', 'Volatility'],
      ...historicalData.map(data => [
        data.date,
        data.portfolio_value.toFixed(2),
        data.returns.toFixed(4),
        data.drawdown.toFixed(2),
        data.sharpe_ratio.toFixed(2),
        data.volatility.toFixed(2)
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `historical_analysis_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 2000);
  };

  const getRegimeColor = (regimeType: string) => {
    switch (regimeType) {
      case 'bull': return '#10b981';
      case 'bear': return '#ef4444';
      case 'sideways': return '#f59e0b';
      case 'volatile': return '#8b5cf6';
      default: return '#6b7280';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Historical Analysis</h1>
            <p className="text-gray-600 mt-1">Comprehensive analysis of trading performance over time</p>
          </div>

          <div className="flex items-center space-x-4">
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="1M">1 Month</option>
              <option value="3M">3 Months</option>
              <option value="6M">6 Months</option>
              <option value="1Y">1 Year</option>
              <option value="ALL">All Time</option>
            </select>

            <button
              onClick={() => setComparisonMode(!comparisonMode)}
              className={cn(
                "flex items-center space-x-2 px-4 py-2 rounded-md transition-colors",
                comparisonMode ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700"
              )}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Compare</span>
            </button>

            <button
              onClick={() => setShowStatistics(!showStatistics)}
              className={cn(
                "flex items-center space-x-2 px-4 py-2 rounded-md transition-colors",
                showStatistics ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700"
              )}
            >
              <Info className="w-4 h-4" />
              <span>Statistics</span>
            </button>

            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
              <span>Refresh</span>
            </button>

            <button
              onClick={handleExportData}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              <Download className="w-4 h-4" />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Analysis Type Selector */}
        <div className="mt-4 flex space-x-4">
          <button
            onClick={() => setAnalysisType('overview')}
            className={cn(
              "px-4 py-2 rounded-md font-medium transition-colors",
              analysisType === 'overview'
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <Activity className="w-4 h-4 inline mr-2" />
            Overview
          </button>
          <button
            onClick={() => setAnalysisType('backtest')}
            className={cn(
              "px-4 py-2 rounded-md font-medium transition-colors",
              analysisType === 'backtest'
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <Target className="w-4 h-4 inline mr-2" />
            Backtest Results
          </button>
          <button
            onClick={() => setAnalysisType('regimes')}
            className={cn(
              "px-4 py-2 rounded-md font-medium transition-colors",
              analysisType === 'regimes'
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <TrendingUp className="w-4 h-4 inline mr-2" />
            Market Regimes
          </button>
          <button
            onClick={() => setAnalysisType('attribution')}
            className={cn(
              "px-4 py-2 rounded-md font-medium transition-colors",
              analysisType === 'attribution'
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <BarChart3 className="w-4 h-4 inline mr-2" />
            Performance Attribution
          </button>
        </div>
      </div>

      {/* Statistics Panel */}
      {showStatistics && statistics.totalReturn !== undefined && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-6">
          <StatCard
            title="Total Return"
            value={`${statistics.totalReturn.toFixed(2)}%`}
            icon={TrendingUp}
            trend={statistics.totalReturn >= 0 ? 'up' : 'down'}
          />
          <StatCard
            title="Annualized Return"
            value={`${statistics.annualizedReturn.toFixed(2)}%`}
            icon={Percent}
            trend={statistics.annualizedReturn >= 0 ? 'up' : 'down'}
          />
          <StatCard
            title="Sharpe Ratio"
            value={statistics.sharpeRatio.toFixed(2)}
            icon={Target}
          />
          <StatCard
            title="Max Drawdown"
            value={`${statistics.maxDrawdown.toFixed(2)}%`}
            icon={TrendingDown}
            trend="down"
          />
          <StatCard
            title="Volatility"
            value={`${statistics.volatility.toFixed(2)}%`}
            icon={Activity}
          />
          <StatCard
            title="Win Rate"
            value={`${statistics.avgWinRate.toFixed(1)}%`}
            icon={Zap}
          />
          <StatCard
            title="Profit Factor"
            value={statistics.profitFactor.toFixed(2)}
            icon={DollarSign}
          />
          <StatCard
            title="Calmar Ratio"
            value={statistics.calmarRatio.toFixed(2)}
            icon={Percent}
          />
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Charts Area */}
        <div className="lg:col-span-2 space-y-6">
          {analysisType === 'overview' && (
            <>
              {/* Equity Curve */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Portfolio Equity Curve</h2>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-500">
                      Period: {selectedTimeframe}
                    </span>
                  </div>
                </div>

                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={historicalData}>
                    <defs>
                      <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      stroke="#6b7280"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis yAxisId="left" stroke="#6b7280" />
                    <YAxis yAxisId="right" orientation="right" stroke="#ef4444" />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                      formatter={(value: any, name: string) => [
                        name === 'portfolio_value' ? `$${value.toFixed(2)}` : `${value.toFixed(2)}%`,
                        name === 'portfolio_value' ? 'Portfolio Value' : name === 'drawdown' ? 'Drawdown' : name
                      ]}
                    />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="portfolio_value"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#colorValue)"
                    />
                    <Area
                      yAxisId="right"
                      type="monotone"
                      dataKey="drawdown"
                      stroke="#ef4444"
                      strokeWidth={1}
                      fill="url(#colorDrawdown)"
                    />
                    <Legend
                      formatter={(value) => value === 'portfolio_value' ? 'Portfolio Value' : 'Drawdown'}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Returns Distribution */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Returns Distribution</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={historicalData.filter((_, i) => i % 7 === 0)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                      formatter={(value: any) => [`${value.toFixed(2)}%`, 'Daily Return']}
                    />
                    <Bar dataKey="returns" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Risk Metrics */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Metrics Over Time</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={historicalData.filter((_, i) => i % 3 === 0)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                      formatter={(value: any, name: string) => [
                        typeof value === 'number' ? value.toFixed(2) : value,
                        name === 'volatility' ? 'Volatility %' :
                        name === 'var_95' ? 'VaR 95%' :
                        name === 'sharpe_ratio' ? 'Sharpe Ratio' : name
                      ]}
                    />
                    <Line type="monotone" dataKey="volatility" stroke="#f59e0b" name="volatility" />
                    <Line type="monotone" dataKey="var_95" stroke="#ef4444" name="var_95" />
                    <Line type="monotone" dataKey="sharpe_ratio" stroke="#10b981" name="sharpe_ratio" />
                    <Legend
                      formatter={(value) => value === 'volatility' ? 'Volatility %' :
                        value === 'var_95' ? 'VaR 95%' :
                        value === 'sharpe_ratio' ? 'Sharpe Ratio' : value}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {analysisType === 'backtest' && (
            <>
              {/* Backtest Comparison */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Backtest Performance Comparison</h2>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={backtestResults}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="strategy_name" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="total_return" fill="#10b981" name="Total Return %" />
                    <Bar yAxisId="right" dataKey="sharpe_ratio" fill="#3b82f6" name="Sharpe Ratio" />
                    <Bar yAxisId="left" dataKey="max_drawdown" fill="#ef4444" name="Max Drawdown %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Risk-Return Scatter */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk-Return Analysis</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="volatility" name="Volatility" />
                    <YAxis dataKey="total_return" name="Total Return" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Scatter name="Strategies" data={backtestResults} fill="#3b82f6">
                      {backtestResults.map((entry, index) => (
                        <cell key={`cell-${index}`} fill={['#3b82f6', '#10b981', '#f59e0b'][index]} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>

              {/* Detailed Backtest Table */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Detailed Backtest Results</h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strategy</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Return</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sharpe</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Max DD</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Win Rate</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Trades</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {backtestResults.map((result) => (
                        <tr key={result.strategy_name} className="hover:bg-gray-50">
                          <td className="px-4 py-2 text-sm font-medium text-gray-900">{result.strategy_name}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{result.total_return.toFixed(1)}%</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{result.sharpe_ratio.toFixed(2)}</td>
                          <td className="px-4 py-2 text-sm text-red-600">{result.max_drawdown.toFixed(1)}%</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{result.win_rate.toFixed(1)}%</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{result.total_trades}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {analysisType === 'regimes' && (
            <>
              {/* Market Regime Timeline */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Market Regime Analysis</h2>
                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={historicalData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />

                    {/* Portfolio Value */}
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="portfolio_value"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      name="Portfolio Value"
                    />

                    {/* Regime Backgrounds */}
                    {marketRegimes.map((regime, index) => (
                      <ReferenceArea
                        key={index}
                        yAxisId="left"
                        x1={regime.start_date}
                        x2={regime.end_date}
                        fillOpacity={0.2}
                        fill={getRegimeColor(regime.regime_type)}
                        stroke={getRegimeColor(regime.regime_type)}
                        strokeOpacity={0.3}
                      />
                    ))}
                  </ComposedChart>
                </ResponsiveContainer>

                {/* Regime Legend */}
                <div className="mt-4 flex flex-wrap gap-4">
                  {['bull', 'bear', 'sideways', 'volatile'].map((regime) => (
                    <div key={regime} className="flex items-center space-x-2">
                      <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: getRegimeColor(regime) }}
                      />
                      <span className="text-sm text-gray-600 capitalize">{regime} Market</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Regime Performance */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Performance by Market Regime</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={marketRegimes}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="regime_type" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="performance" fill="#10b981" name="Performance %" />
                    <Bar dataKey="volatility" fill="#f59e0b" name="Volatility %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {analysisType === 'attribution' && (
            <>
              {/* Performance Attribution Tree */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Performance Attribution</h2>
                <ResponsiveContainer width="100%" height={400}>
                  <Treemap
                    data={[
                      {
                        name: 'Strategy Returns',
                        size: performanceAttribution[0].contribution,
                        fill: '#10b981'
                      },
                      {
                        name: 'Market Timing',
                        size: performanceAttribution[1].contribution,
                        fill: '#3b82f6'
                      },
                      {
                        name: 'Risk Management',
                        size: performanceAttribution[2].contribution,
                        fill: '#f59e0b'
                      },
                      {
                        name: 'Market Beta',
                        size: performanceAttribution[3].contribution,
                        fill: '#8b5cf6'
                      }
                    ]}
                    dataKey="size"
                    aspectRatio={4 / 3}
                    stroke="#fff"
                    fill="#8884d8"
                  />
                </ResponsiveContainer>
              </div>

              {/* Attribution Breakdown */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Attribution Breakdown</h2>
                <div className="space-y-4">
                  {performanceAttribution.map((category) => (
                    <div key={category.category} className="border rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <h3 className="font-medium text-gray-900">{category.category}</h3>
                        <span className="text-sm font-bold text-gray-700">
                          {category.contribution.toFixed(2)}% ({category.contribution_pct.toFixed(1)}% of total)
                        </span>
                      </div>
                      <div className="space-y-2">
                        {category.breakdown.map((item) => (
                          <div key={item.name} className="flex justify-between items-center">
                            <span className="text-sm text-gray-600">{item.name}</span>
                            <span className="text-sm font-medium text-gray-900">
                              {item.value.toFixed(2)}% ({item.percentage.toFixed(1)}%)
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Performance Summary</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Best Day</span>
                <span className="text-sm font-medium text-green-600">
                  +{Math.max(...historicalData.map(d => d.returns)).toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Worst Day</span>
                <span className="text-sm font-medium text-red-600">
                  {Math.min(...historicalData.map(d => d.returns)).toFixed(2)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Avg Daily Return</span>
                <span className="text-sm font-medium text-gray-900">
                  {(historicalData.reduce((sum, d) => sum + d.returns, 0) / historicalData.length).toFixed(3)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Win Days</span>
                <span className="text-sm font-medium text-gray-900">
                  {historicalData.filter(d => d.returns > 0).length}/{historicalData.length}
                </span>
              </div>
            </div>
          </div>

          {/* Top Performing Periods */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Performing Periods</h2>
            <div className="space-y-2">
              {historicalData
                .sort((a, b) => b.returns - a.returns)
                .slice(0, 5)
                .map((day, index) => (
                  <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                    <span className="text-sm text-gray-600">
                      {new Date(day.date).toLocaleDateString()}
                    </span>
                    <span className="text-sm font-medium text-green-600">
                      +{day.returns.toFixed(2)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>

          {/* Risk Alerts */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Analysis</h2>
            <div className="space-y-3">
              <div className="p-3 bg-yellow-50 rounded-lg">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  <span className="text-sm font-medium text-gray-900">Drawdown Warning</span>
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  Current drawdown: {statistics.maxDrawdown?.toFixed(2)}%
                </p>
              </div>

              <div className="p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Info className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-gray-900">Volatility Analysis</span>
                </div>
                <p className="text-xs text-gray-600 mt-1">
                  Current volatility: {statistics.volatility?.toFixed(2)}%
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper Component
interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ElementType;
  trend?: 'up' | 'down';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon: Icon, trend }) => {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600';

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-600">{title}</p>
          <p className={cn("text-lg font-bold", trendColor)}>{value}</p>
        </div>
        <Icon className="w-5 h-5 text-gray-400" />
      </div>
    </div>
  );
};

export default HistoricalAnalysis;