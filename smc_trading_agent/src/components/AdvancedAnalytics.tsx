import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectItem } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ComposedChart,
  ScatterChart,
  Scatter,
  Treemap
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Target,
  BarChart3,
  PieChart as PieChartIcon,
  Calendar,
  Download,
  Filter,
  Zap,
  Brain,
  Shield,
  Award,
  AlertTriangle,
  Info,
  RefreshCw,
  FileText,
  Eye,
  TrendingUp as AnalyticsIcon
} from 'lucide-react';
import { apiService } from '@/services/api';
import { cn } from '@/lib/utils';

interface AdvancedAnalyticsProps {
  className?: string;
}

interface StrategyAttribution {
  strategy: string;
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  profitFactor: number;
  contribution: number;
}

interface MarketImpact {
  symbol: string;
  tradeSize: number;
  priceImpact: number;
  executionCost: number;
  timingCost: number;
  totalCost: number;
  efficiency: number;
  benchmark: string;
}

interface SlippageAnalysis {
  symbol: string;
  expectedPrice: number;
  executionPrice: number;
  slippage: number;
  slippagePercent: number;
  volume: number;
  side: 'BUY' | 'SELL';
  timestamp: string;
  marketCondition: 'normal' | 'volatile' | 'thin';
}

interface PerformanceForecast {
  period: string;
  expectedReturn: number;
  confidence: number;
  volatility: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winProbability: number;
}

interface RevenueMetrics {
  month: string;
  tradingRevenue: number;
  fees: number;
  netRevenue: number;
  activeStrategies: number;
  totalVolume: number;
  avgDailyReturn: number;
}

const attributionColors = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899'];
const marketConditionColors = {
  normal: '#10b981',
  volatile: '#f59e0b',
  thin: '#ef4444'
};

export default function AdvancedAnalytics({
  className
}: AdvancedAnalyticsProps) {
  const [timeframe, setTimeframe] = useState('30d');
  const [loading, setLoading] = useState(true);
  const [strategyAttribution, setStrategyAttribution] = useState<StrategyAttribution[]>([]);
  const [marketImpact, setMarketImpact] = useState<MarketImpact[]>([]);
  const [slippageAnalysis, setSlippageAnalysis] = useState<SlippageAnalysis[]>([]);
  const [performanceForecast, setPerformanceForecast] = useState<PerformanceForecast[]>([]);
  const [revenueMetrics, setRevenueMetrics] = useState<RevenueMetrics[]>([]);
  const [selectedMetric, setSelectedMetric] = useState('return');

  const timeframes = [
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
    { value: '180d', label: '6 Months' },
    { value: '1y', label: '1 Year' },
    { value: 'all', label: 'All Time' }
  ];

  const metricTypes = [
    { value: 'return', label: 'Return Attribution' },
    { value: 'sharpe', label: 'Risk-Adjusted Returns' },
    { value: 'drawdown', label: 'Drawdown Analysis' },
    { value: 'frequency', label: 'Trading Frequency' }
  ];

  useEffect(() => {
    fetchAnalyticsData();
  }, [timeframe]);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);

      // Fetch real data from backend API
      const [strategyData, marketImpactData, slippageData, forecastData, revenueData] = await Promise.all([
        apiService.getStrategyAttribution(timeframe),
        apiService.getMarketImpact(timeframe),
        apiService.getSlippageAnalysis(undefined, 50),
        apiService.getPerformanceForecast(),
        apiService.getRevenueMetrics(timeframe)
      ]);

      setStrategyAttribution(strategyData);
      setMarketImpact(marketImpactData);
      setSlippageAnalysis(slippageData);
      setPerformanceForecast(forecastData);
      setRevenueMetrics(revenueData);

    } catch (error) {
      console.error('Failed to fetch analytics data:', error);
    } finally {
      setLoading(false);
    }
  };

  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const getEfficiencyColor = (efficiency: number) => {
    if (efficiency > 0.8) return '#10b981';
    if (efficiency > 0.6) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Advanced Analytics</h2>
          <p className="text-gray-600">Strategy attribution, market impact, and performance forecasting</p>
        </div>

        <div className="flex items-center space-x-4">
          <Select value={selectedMetric} onValueChange={setSelectedMetric} className="w-48">
              {metricTypes.map(metric => (
                <SelectItem key={metric.value} value={metric.value}>
                  {metric.label}
                </SelectItem>
              ))}
            </Select>

          <Select value={timeframe} onValueChange={setTimeframe} className="w-32">
              {timeframes.map(tf => (
                <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
              ))}
            </Select>

          <Button variant="outline" size="sm" onClick={fetchAnalyticsData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>

          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Attribution</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(strategyAttribution.reduce((sum, s) => sum + s.totalReturn, 0))}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Market Impact</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {(marketImpact.reduce((sum, m) => sum + m.priceImpact, 0) / marketImpact.length * 100).toFixed(3)}%
                </p>
              </div>
              <Activity className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Slippage</p>
                <p className="text-2xl font-bold text-orange-600">
                  {(slippageAnalysis.reduce((sum, s) => sum + s.slippagePercent, 0) / slippageAnalysis.length).toFixed(3)}%
                </p>
              </div>
              <Target className="h-8 w-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Forecast Return</p>
                <p className="text-2xl font-bold text-blue-600">
                  {formatPercent(performanceForecast[0]?.expectedReturn || 0)}
                </p>
              </div>
              <Brain className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Analytics */}
      <Tabs defaultValue="attribution" className="space-y-6">
        <TabsList>
          <TabsTrigger value="attribution">Strategy Attribution</TabsTrigger>
          <TabsTrigger value="impact">Market Impact</TabsTrigger>
          <TabsTrigger value="slippage">Slippage Analysis</TabsTrigger>
          <TabsTrigger value="forecasting">Performance Forecast</TabsTrigger>
          <TabsTrigger value="revenue">Revenue Analytics</TabsTrigger>
        </TabsList>

        {/* Strategy Attribution */}
        <TabsContent value="attribution" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Return Attribution Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>Return Attribution</span>
                </CardTitle>
                <CardDescription>Strategy contribution to total returns</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={strategyAttribution}
                      dataKey="totalReturn"
                      nameKey="strategy"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={(entry) => `${entry.strategy}: ${formatPercent(entry.contribution)}`}
                    >
                      {strategyAttribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={attributionColors[index % attributionColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: any) => [formatCurrency(value), 'Return']}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Risk-Adjusted Performance */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>Risk-Adjusted Performance</span>
                </CardTitle>
                <CardDescription>Sharpe ratio and maximum drawdown by strategy</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={strategyAttribution}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="strategy"
                      tick={{ fontSize: 10 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        name === 'sharpeRatio' ? value.toFixed(2) : formatPercent(value),
                        name === 'sharpeRatio' ? 'Sharpe Ratio' : 'Max Drawdown'
                      ]}
                    />
                <Legend />
                    <Bar dataKey="sharpeRatio" fill="#3b82f6" name="Sharpe Ratio" />
                    <Bar dataKey="maxDrawdown" fill="#ef4444" name="Max Drawdown (%)" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Strategy Performance Radar */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Target className="h-5 w-5" />
                <span>Strategy Performance Radar</span>
              </CardTitle>
              <CardDescription>Multi-dimensional performance comparison</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <RadarChart data={strategyAttribution.slice(0, 5)}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="strategy" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis />
                  <Radar
                    name="Win Rate"
                    dataKey="winRate"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.3}
                  />
                  <Radar
                    name="Profit Factor"
                    dataKey="profitFactor"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.3}
                  />
                  <Radar
                    name="Trade Frequency"
                    dataKey="totalTrades"
                    stroke="#f59e0b"
                    fill="#f59e0b"
                    fillOpacity={0.3}
                  />
                  <Legend />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Market Impact */}
        <TabsContent value="impact" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Price Impact Analysis */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Price Impact by Trade Size</span>
                </CardTitle>
                <CardDescription>Market impact analysis across different symbols</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="tradeSize"
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                      name="Trade Size"
                    />
                    <YAxis
                      tickFormatter={(value) => `${(value * 100).toFixed(2)}%`}
                      name="Price Impact"
                    />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        name === 'priceImpact' ? formatPercent(value) : formatCurrency(value),
                        name === 'priceImpact' ? 'Price Impact' : 'Trade Size'
                      ]}
                    />
                    <Scatter
                      name="Price Impact"
                      data={marketImpact.map(m => ({
                        ...m,
                        fill: getEfficiencyColor(m.efficiency)
                      }))}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Execution Costs */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <DollarSign className="h-5 w-5" />
                  <span>Execution Cost Breakdown</span>
                </CardTitle>
                <CardDescription>Detailed cost analysis by trading symbol</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={marketImpact}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="symbol" />
                    <YAxis tickFormatter={(value) => formatCurrency(value)} />
                    <Tooltip
                      formatter={(value: any) => [formatCurrency(value), 'Cost']}
                    />
                    <Legend />
                    <Bar dataKey="executionCost" stackId="a" fill="#3b82f6" name="Execution Cost" />
                    <Bar dataKey="timingCost" stackId="a" fill="#f59e0b" name="Timing Cost" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Market Impact Table */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Eye className="h-5 w-5" />
                <span>Detailed Market Impact Analysis</span>
              </CardTitle>
              <CardDescription>Comprehensive impact metrics across all trades</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Symbol
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Trade Size
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Price Impact
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Total Cost
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Efficiency
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Benchmark
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {marketImpact.map((impact, index) => (
                      <tr key={index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {impact.symbol}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatCurrency(impact.tradeSize)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatPercent(impact.priceImpact)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatCurrency(impact.totalCost)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <div
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: getEfficiencyColor(impact.efficiency) }}
                            />
                            <span className="text-sm text-gray-900">
                              {formatPercent(impact.efficiency)}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {impact.benchmark}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Slippage Analysis */}
        <TabsContent value="slippage" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Slippage Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="h-5 w-5" />
                  <span>Slippage Distribution</span>
                </CardTitle>
                <CardDescription>Analysis of slippage across different market conditions</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={slippageAnalysis.slice(0, 20)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis tickFormatter={(value) => `${value.toFixed(3)}%`} />
                    <Tooltip
                      formatter={(value: any) => [`${value.toFixed(3)}%`, 'Slippage']}
                      labelFormatter={(label) => new Date(label).toLocaleString()}
                    />
                    <Bar
                      dataKey="slippagePercent"
                      fill={(entry: any) => marketConditionColors[entry.marketCondition]}
                    />
                  </BarChart>
                </ResponsiveContainer>

                <div className="mt-4 flex justify-center space-x-4">
                  {Object.entries(marketConditionColors).map(([condition, color]) => (
                    <div key={condition} className="flex items-center space-x-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-sm capitalize">{condition}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Volume vs Slippage */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Volume vs Slippage</span>
                </CardTitle>
                <CardDescription>Correlation between trading volume and slippage</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="volume"
                      tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
                      name="Volume"
                    />
                    <YAxis
                      tickFormatter={(value) => `${value.toFixed(3)}%`}
                      name="Slippage (%)"
                    />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        name === 'slippagePercent' ? `${value.toFixed(3)}%` : formatCurrency(value),
                        name === 'slippagePercent' ? 'Slippage' : 'Volume'
                      ]}
                    />
                    <Scatter
                      name="Volume vs Slippage"
                      data={slippageAnalysis.map(s => ({
                        ...s,
                        fill: s.side === 'BUY' ? '#10b981' : '#ef4444'
                      }))}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Performance Forecast */}
        <TabsContent value="forecasting" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Return Forecast */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Brain className="h-5 w-5" />
                  <span>Performance Forecast</span>
                </CardTitle>
                <CardDescription>Expected returns with confidence intervals</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={performanceForecast}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" />
                    <YAxis tickFormatter={(value) => formatPercent(value)} />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        formatPercent(value),
                        name === 'expectedReturn' ? 'Expected Return' :
                        name === 'volatility' ? 'Volatility' : 'Confidence'
                      ]}
                    />
                    <Legend />
                    <Bar dataKey="expectedReturn" fill="#10b981" name="Expected Return" />
                    <Bar dataKey="volatility" fill="#f59e0b" name="Volatility" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Risk Metrics Forecast */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span>Risk Metrics Forecast</span>
                </CardTitle>
                <CardDescription>Projected risk metrics for different time horizons</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={performanceForecast}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" />
                    <YAxis />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        name === 'maxDrawdown' ? formatPercent(value) :
                        name === 'winProbability' ? formatPercent(value) :
                        value.toFixed(2),
                        name === 'maxDrawdown' ? 'Max Drawdown' :
                        name === 'winProbability' ? 'Win Probability' :
                        'Sharpe Ratio'
                      ]}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="sharpeRatio"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      name="Sharpe Ratio"
                    />
                    <Line
                      type="monotone"
                      dataKey="maxDrawdown"
                      stroke="#ef4444"
                      strokeWidth={2}
                      name="Max Drawdown (%)"
                    />
                    <Line
                      type="monotone"
                      dataKey="winProbability"
                      stroke="#10b981"
                      strokeWidth={2}
                      name="Win Probability (%)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Revenue Analytics */}
        <TabsContent value="revenue" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue Trends */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <DollarSign className="h-5 w-5" />
                  <span>Revenue Trends</span>
                </CardTitle>
                <CardDescription>Monthly revenue and performance metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={revenueMetrics}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis yAxisId="left" tickFormatter={(value) => formatCurrency(value)} />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        name.includes('Revenue') || name.includes('Fees') ? formatCurrency(value) :
                        value.toFixed(2),
                        name
                      ]}
                    />
                    <Legend />
                    <Bar yAxisId="left" dataKey="tradingRevenue" fill="#10b981" name="Trading Revenue" />
                    <Bar yAxisId="left" dataKey="fees" fill="#ef4444" name="Fees" />
                <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="avgDailyReturn"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      name="Avg Daily Return (%)"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Active Strategies */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>Strategy Performance</span>
                </CardTitle>
                <CardDescription>Active strategies and trading volume</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={revenueMetrics}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip
                      formatter={(value: any, name: string) => [
                        name === 'totalVolume' ? formatCurrency(value) : value,
                        name === 'totalVolume' ? 'Total Volume' : 'Active Strategies'
                      ]}
                    />
                    <Legend />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="totalVolume"
                      stackId="1"
                      stroke="#8b5cf6"
                      fill="#8b5cf6"
                      fillOpacity={0.3}
                      name="Total Volume"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="activeStrategies"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      name="Active Strategies"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}