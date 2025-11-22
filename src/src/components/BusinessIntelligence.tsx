import React, { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell,
  Treemap, ComposedChart, Area
} from 'recharts';
import {
  TrendingUp, BarChart3, PieChart as PieChartIcon, Target, Activity,
  Filter, Download, Calendar, RefreshCw, Settings, Info, AlertTriangle,
  DollarSign, Percent, Clock, Zap, Shield, TrendingDown
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
interface StrategyPerformance {
  name: string;
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  profitFactor: number;
  calmarRatio: number;
  totalTrades: number;
  avgTrade: number;
  volatility: number;
  var95: number;
  active: boolean;
}

interface MarketRegime {
  period: string;
  regime: 'trending' | 'ranging' | 'volatile' | 'quiet';
  duration: number;
  performance: number;
  volatility: number;
  volume: number;
}

interface RiskAnalysis {
  date: string;
  portfolio_value: number;
  var_95: number;
  expected_shortfall: number;
  beta: number;
  correlation: number;
  concentration_risk: number;
  liquidity_risk: number;
}

interface PatternEffectiveness {
  pattern: string;
  frequency: number;
  success_rate: number;
  avg_return: number;
  risk_adjusted_return: number;
  market_conditions: string[];
}

const BusinessIntelligence: React.FC = () => {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1M');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [analysisType, setAnalysisType] = useState<'performance' | 'risk' | 'patterns' | 'regimes'>('performance');
  const [isLoading, setIsLoading] = useState(false);

  // Mock data - in real implementation, this would come from API
  const [strategyData] = useState<StrategyPerformance[]>([
    {
      name: 'SMC Momentum',
      totalReturn: 18.5,
      sharpeRatio: 1.45,
      maxDrawdown: -6.2,
      winRate: 68.5,
      profitFactor: 2.34,
      calmarRatio: 2.98,
      totalTrades: 156,
      avgTrade: 0.87,
      volatility: 12.3,
      var95: -2.4,
      active: true
    },
    {
      name: 'Order Block Hunter',
      totalReturn: 22.1,
      sharpeRatio: 1.78,
      maxDrawdown: -8.1,
      winRate: 72.3,
      profitFactor: 2.89,
      calmarRatio: 2.73,
      totalTrades: 89,
      avgTrade: 1.52,
      volatility: 15.7,
      var95: -3.1,
      active: true
    },
    {
      name: 'Liquidity Sweep',
      totalReturn: 15.3,
      sharpeRatio: 1.23,
      maxDrawdown: -4.8,
      winRate: 64.2,
      profitFactor: 2.12,
      calmarRatio: 3.19,
      totalTrades: 234,
      avgTrade: 0.45,
      volatility: 9.8,
      var95: -1.8,
      active: false
    },
    {
      name: 'CHoCH Detector',
      totalReturn: 28.7,
      sharpeRatio: 2.01,
      maxDrawdown: -9.5,
      winRate: 75.8,
      profitFactor: 3.45,
      calmarRatio: 3.02,
      totalTrades: 67,
      avgTrade: 2.18,
      volatility: 18.2,
      var95: -3.9,
      active: true
    },
    {
      name: 'Market Structure',
      totalReturn: 12.4,
      sharpeRatio: 0.98,
      maxDrawdown: -5.6,
      winRate: 61.3,
      profitFactor: 1.87,
      calmarRatio: 2.21,
      totalTrades: 198,
      avgTrade: 0.38,
      volatility: 11.5,
      var95: -2.1,
      active: false
    }
  ]);

  const [marketRegimes] = useState<MarketRegime[]>([
    { period: '2024-01', regime: 'trending', duration: 15, performance: 8.2, volatility: 14.3, volume: 1.2 },
    { period: '2024-02', regime: 'ranging', duration: 12, performance: 2.1, volatility: 8.7, volume: 0.8 },
    { period: '2024-03', regime: 'volatile', duration: 8, performance: -3.4, volatility: 22.1, volume: 1.8 },
    { period: '2024-04', regime: 'quiet', duration: 18, performance: 4.7, volatility: 6.2, volume: 0.6 },
    { period: '2024-05', regime: 'trending', duration: 14, performance: 12.8, volatility: 16.5, volume: 1.4 },
    { period: '2024-06', regime: 'ranging', duration: 10, performance: 1.9, volatility: 9.3, volume: 0.9 }
  ]);

  const [riskAnalysis] = useState<RiskAnalysis[]>(Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    portfolio_value: 10000 + Math.random() * 2000,
    var_95: -Math.random() * 4,
    expected_shortfall: -Math.random() * 5,
    beta: 0.5 + Math.random() * 1.0,
    correlation: Math.random() * 0.8,
    concentration_risk: Math.random() * 0.5,
    liquidity_risk: Math.random() * 0.3
  })));

  const [patternEffectiveness] = useState<PatternEffectiveness[]>([
    {
      pattern: 'Order Block',
      frequency: 245,
      success_rate: 71.2,
      avg_return: 1.85,
      risk_adjusted_return: 1.43,
      market_conditions: ['trending', 'low_volatility']
    },
    {
      pattern: 'Break of Structure',
      frequency: 189,
      success_rate: 68.4,
      avg_return: 2.12,
      risk_adjusted_return: 1.67,
      market_conditions: ['trending', 'high_volume']
    },
    {
      pattern: 'Liquidity Sweep',
      frequency: 156,
      success_rate: 74.8,
      avg_return: 1.56,
      risk_adjusted_return: 1.38,
      market_conditions: ['volatile', 'reversal']
    },
    {
      pattern: 'Fair Value Gap',
      frequency: 203,
      success_rate: 65.3,
      avg_return: 1.24,
      risk_adjusted_return: 1.12,
      market_conditions: ['ranging', 'mean_reversion']
    },
    {
      pattern: 'CHOCH',
      frequency: 134,
      success_rate: 78.9,
      avg_return: 2.45,
      risk_adjusted_return: 1.89,
      market_conditions: ['trending', 'momentum']
    }
  ]);

  // Computed metrics
  const overallMetrics = useMemo(() => {
    const activeStrategies = strategyData.filter(s => s.active);
    const totalReturn = activeStrategies.reduce((sum, s) => sum + s.totalReturn, 0) / activeStrategies.length;
    const avgSharpe = activeStrategies.reduce((sum, s) => sum + s.sharpeRatio, 0) / activeStrategies.length;
    const totalTrades = activeStrategies.reduce((sum, s) => sum + s.totalTrades, 0);
    const avgWinRate = activeStrategies.reduce((sum, s) => sum + s.winRate, 0) / activeStrategies.length;

    return {
      totalReturn,
      avgSharpe,
      totalTrades,
      avgWinRate,
      maxDrawdown: Math.min(...activeStrategies.map(s => s.maxDrawdown))
    };
  }, [strategyData]);

  // Strategy comparison data for radar chart
  const radarData = useMemo(() => {
    const metrics = ['sharpeRatio', 'winRate', 'profitFactor', 'calmarRatio'];
    return metrics.map(metric => ({
      metric: metric.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase()),
      ...strategyData.reduce((acc, strategy) => ({
        ...acc,
        [strategy.name]: strategy[metric as keyof StrategyPerformance]
      }), {})
    }));
  }, [strategyData]);

  // Risk metrics over time
  const riskMetricsData = useMemo(() => {
    return riskAnalysis.map(risk => ({
      date: risk.date,
      VaR: risk.var_95,
      'Expected Shortfall': risk.expected_shortfall,
      Beta: risk.beta,
      Correlation: risk.correlation * 100,
      'Concentration Risk': risk.concentration_risk * 100,
      'Liquidity Risk': risk.liquidity_risk * 100
    }));
  }, [riskAnalysis]);

  // Performance by market regime
  const regimePerformance = useMemo(() => {
    const regimes = ['trending', 'ranging', 'volatile', 'quiet'];
    return regimes.map(regime => {
      const regimeData = marketRegimes.filter(r => r.regime === regime);
      const avgPerformance = regimeData.reduce((sum, r) => sum + r.performance, 0) / regimeData.length;
      const avgVolatility = regimeData.reduce((sum, r) => sum + r.volatility, 0) / regimeData.length;
      const totalDuration = regimeData.reduce((sum, r) => sum + r.duration, 0);

      return {
        regime: regime.charAt(0).toUpperCase() + regime.slice(1),
        performance: avgPerformance,
        volatility: avgVolatility,
        duration: totalDuration
      };
    });
  }, [marketRegimes]);

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  const handleExportData = () => {
    // Implementation for data export
    console.log('Exporting data...');
  };

  const handleRefresh = () => {
    setIsLoading(true);
    // Simulate data refresh
    setTimeout(() => setIsLoading(false), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Business Intelligence Analytics</h1>
            <p className="text-gray-600 mt-1">Deep insights into trading performance and market behavior</p>
          </div>

          <div className="flex items-center space-x-4">
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="1W">1 Week</option>
              <option value="1M">1 Month</option>
              <option value="3M">3 Months</option>
              <option value="6M">6 Months</option>
              <option value="1Y">1 Year</option>
              <option value="ALL">All Time</option>
            </select>

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
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Return</p>
              <p className="text-2xl font-bold text-gray-900">{overallMetrics.totalReturn.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-100 rounded-lg">
              <Target className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Avg Sharpe Ratio</p>
              <p className="text-2xl font-bold text-gray-900">{overallMetrics.avgSharpe.toFixed(2)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-purple-100 rounded-lg">
              <Activity className="w-6 h-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Trades</p>
              <p className="text-2xl font-bold text-gray-900">{overallMetrics.totalTrades}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-3 bg-yellow-100 rounded-lg">
              <Percent className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Avg Win Rate</p>
              <p className="text-2xl font-bold text-gray-900">{overallMetrics.avgWinRate.toFixed(1)}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Analysis Type Selector */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex space-x-4">
          <button
            onClick={() => setAnalysisType('performance')}
            className={cn(
              "px-4 py-2 rounded-md font-medium transition-colors",
              analysisType === 'performance'
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <BarChart3 className="w-4 h-4 inline mr-2" />
            Performance Analysis
          </button>
          <button
            onClick={() => setAnalysisType('risk')}
            className={cn(
              "px-4 py-2 rounded-md font-medium transition-colors",
              analysisType === 'risk'
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <Shield className="w-4 h-4 inline mr-2" />
            Risk Analysis
          </button>
          <button
            onClick={() => setAnalysisType('patterns')}
            className={cn(
              "px-4 py-2 rounded-md font-medium transition-colors",
              analysisType === 'patterns'
                ? "bg-blue-600 text-white"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <PieChartIcon className="w-4 h-4 inline mr-2" />
            Pattern Effectiveness
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
            <Activity className="w-4 h-4 inline mr-2" />
            Market Regimes
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Charts */}
        <div className="lg:col-span-2 space-y-6">
          {analysisType === 'performance' && (
            <>
              {/* Strategy Performance Comparison */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Strategy Performance Comparison</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={strategyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip formatter={(value: any, name: string) => [
                      typeof value === 'number' ? value.toFixed(2) : value,
                      name === 'totalReturn' ? 'Return (%)' : name === 'maxDrawdown' ? 'Max Drawdown (%)' : name
                    ]} />
                    <Legend />
                    <Bar yAxisId="left" dataKey="totalReturn" fill="#10b981" name="Total Return %" />
                    <Bar yAxisId="right" dataKey="maxDrawdown" fill="#ef4444" name="Max Drawdown %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Risk-Return Scatter Plot */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk-Return Analysis</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="sharpeRatio" name="Sharpe Ratio" />
                    <YAxis dataKey="totalReturn" name="Total Return %" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Scatter name="Strategies" data={strategyData} fill="#3b82f6">
                      {strategyData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>

              {/* Strategy Radar Chart */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Multi-Metric Comparison</h2>
                <ResponsiveContainer width="100%" height={400}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="metric" />
                    <PolarRadiusAxis />
                    {strategyData.filter(s => s.active).map((strategy, index) => (
                      <Radar
                        key={strategy.name}
                        name={strategy.name}
                        dataKey={strategy.name}
                        stroke={COLORS[index % COLORS.length]}
                        fill={COLORS[index % COLORS.length]}
                        fillOpacity={0.6}
                      />
                    ))}
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {analysisType === 'risk' && (
            <>
              {/* Risk Metrics Over Time */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Metrics Over Time</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={riskMetricsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Area yAxisId="left" type="monotone" dataKey="VaR" fill="#ef4444" fillOpacity={0.3} stroke="#ef4444" />
                    <Area yAxisId="left" type="monotone" dataKey="Expected Shortfall" fill="#f59e0b" fillOpacity={0.3} stroke="#f59e0b" />
                    <Line yAxisId="right" type="monotone" dataKey="Beta" stroke="#3b82f6" />
                    <Line yAxisId="right" type="monotone" dataKey="Correlation" stroke="#10b981" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Risk Distribution */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Distribution Analysis</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Market Risk', value: 45, fill: '#3b82f6' },
                        { name: 'Liquidity Risk', value: 20, fill: '#10b981' },
                        { name: 'Concentration Risk', value: 15, fill: '#f59e0b' },
                        { name: 'Operational Risk', value: 12, fill: '#ef4444' },
                        { name: 'Model Risk', value: 8, fill: '#8b5cf6' }
                      ]}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {[
                        { name: 'Market Risk', value: 45, fill: '#3b82f6' },
                        { name: 'Liquidity Risk', value: 20, fill: '#10b981' },
                        { name: 'Concentration Risk', value: 15, fill: '#f59e0b' },
                        { name: 'Operational Risk', value: 12, fill: '#ef4444' },
                        { name: 'Model Risk', value: 8, fill: '#8b5cf6' }
                      ].map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {analysisType === 'patterns' && (
            <>
              {/* Pattern Effectiveness */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">SMC Pattern Effectiveness</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={patternEffectiveness}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="pattern" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="success_rate" fill="#10b981" name="Success Rate %" />
                    <Bar yAxisId="right" dataKey="avg_return" fill="#3b82f6" name="Avg Return %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Pattern Frequency Distribution */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Pattern Frequency Distribution</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <Treemap
                    data={[
                      { name: 'Order Block', size: 245, fill: '#3b82f6' },
                      { name: 'Fair Value Gap', size: 203, fill: '#10b981' },
                      { name: 'Break of Structure', size: 189, fill: '#f59e0b' },
                      { name: 'Liquidity Sweep', size: 156, fill: '#ef4444' },
                      { name: 'CHOCH', size: 134, fill: '#8b5cf6' }
                    ]}
                    dataKey="size"
                    aspectRatio={4 / 3}
                    stroke="#fff"
                    fill="#8884d8"
                  />
                </ResponsiveContainer>
              </div>
            </>
          )}

          {analysisType === 'regimes' && (
            <>
              {/* Market Regime Performance */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Performance by Market Regime</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={regimePerformance}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="regime" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="performance" fill="#10b981" name="Performance %" />
                    <Bar yAxisId="right" dataKey="duration" fill="#3b82f6" name="Duration (days)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Regime Timeline */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Market Regime Timeline</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={marketRegimes}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" />
                    <YAxis />
                    <Tooltip />
                    <Area type="monotone" dataKey="volume" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                    <Line type="monotone" dataKey="volatility" stroke="#ef4444" />
                    <Line type="monotone" dataKey="performance" stroke="#10b981" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Strategy Details Table */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Strategy Performance</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Strategy</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Return</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sharpe</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Win Rate</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {strategyData.map((strategy) => (
                    <tr key={strategy.name} className={cn("hover:bg-gray-50", !strategy.active && "opacity-50")}>
                      <td className="px-3 py-2 text-sm font-medium text-gray-900">
                        {strategy.name}
                        {strategy.active && (
                          <div className="w-2 h-2 bg-green-500 rounded-full inline-block ml-2" />
                        )}
                      </td>
                      <td className="px-3 py-2 text-sm text-gray-900">
                        {strategy.totalReturn.toFixed(1)}%
                      </td>
                      <td className="px-3 py-2 text-sm text-gray-900">
                        {strategy.sharpeRatio.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-sm text-gray-900">
                        {strategy.winRate.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Top Performers */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Performers</h2>
            <div className="space-y-3">
              {strategyData
                .sort((a, b) => b.totalReturn - a.totalReturn)
                .slice(0, 3)
                .map((strategy, index) => (
                  <div key={strategy.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center text-white font-bold",
                        index === 0 ? "bg-yellow-500" :
                        index === 1 ? "bg-gray-400" :
                        "bg-orange-600"
                      )}>
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{strategy.name}</p>
                        <p className="text-xs text-gray-500">{strategy.totalTrades} trades</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-green-600">{strategy.totalReturn.toFixed(1)}%</p>
                      <p className="text-xs text-gray-500">Sharpe: {strategy.sharpeRatio.toFixed(2)}</p>
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Risk Alerts */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Alerts</h2>
            <div className="space-y-2">
              <div className="flex items-start space-x-2 p-2 bg-yellow-50 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-900">High Volatility Detected</p>
                  <p className="text-xs text-gray-600">Market volatility exceeds 20% threshold</p>
                </div>
              </div>
              <div className="flex items-start space-x-2 p-2 bg-red-50 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Concentration Risk</p>
                  <p className="text-xs text-gray-600">Single position exceeds 15% of portfolio</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BusinessIntelligence;