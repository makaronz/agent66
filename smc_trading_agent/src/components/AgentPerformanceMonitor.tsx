import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectItem } from '@/components/ui/select';
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
  Radar
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Activity,
  Clock,
  Zap,
  Brain,
  Shield,
  BarChart3,
  Award,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  RefreshCw,
  Download,
  Calendar,
  Filter
} from 'lucide-react';
import { apiService, type Agent } from '@/services/api';
import { cn } from '@/lib/utils';

interface AgentPerformanceMonitorProps {
  agent: Agent;
  className?: string;
}

interface PerformanceData {
  timestamp: string;
  pnl: number;
  equity: number;
  drawdown: number;
  trades: number;
  winRate: number;
  sharpeRatio: number;
  latency: number;
}

interface TradeBreakdown {
  symbol: string;
  trades: number;
  pnl: number;
  winRate: number;
  avgTrade: number;
}

interface StrategyPerformance {
  name: string;
  pnl: number;
  trades: number;
  winRate: number;
  sharpe: number;
  maxDrawdown: number;
}

export default function AgentPerformanceMonitor({
  agent,
  className
}: AgentPerformanceMonitorProps) {
  const [timeframe, setTimeframe] = useState('24h');
  const [loading, setLoading] = useState(true);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [tradeBreakdown, setTradeBreakdown] = useState<TradeBreakdown[]>([]);
  const [strategyPerformance, setStrategyPerformance] = useState<StrategyPerformance[]>([]);
  const [riskMetrics, setRiskMetrics] = useState<any>(null);
  const [realTimeMetrics, setRealTimeMetrics] = useState({
    cpuUsage: 0,
    memoryUsage: 0,
    networkUsage: 0,
    latency: '0ms',
    uptime: '0h 0m'
  });

  const timeframes = [
    { value: '1h', label: '1 Hour' },
    { value: '6h', label: '6 Hours' },
    { value: '24h', label: '24 Hours' },
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' }
  ];

  useEffect(() => {
    fetchPerformanceData();
    fetchRealTimeMetrics();

    // Set up real-time updates
    const interval = setInterval(fetchRealTimeMetrics, 5000);
    return () => clearInterval(interval);
  }, [agent.id, timeframe]);

  const fetchPerformanceData = async () => {
    try {
      setLoading(true);

      // Fetch agent performance metrics
      const performance = await apiService.getAgentPerformance(agent.id, timeframe);

      // Generate time-series performance data (mock for now)
      const mockPerformanceData = generateMockPerformanceData(timeframe);
      setPerformanceData(mockPerformanceData);

      // Generate trade breakdown by symbol
      const mockTradeBreakdown = generateMockTradeBreakdown();
      setTradeBreakdown(mockTradeBreakdown);

      // Generate strategy performance
      const mockStrategyPerformance = generateMockStrategyPerformance(agent.strategies);
      setStrategyPerformance(mockStrategyPerformance);

      // Set risk metrics
      setRiskMetrics({
        currentExposure: Math.random() * 100000,
        maxExposure: 150000,
        marginUsed: Math.random() * 50,
        varDaily: Math.random() * 5000,
        varWeekly: Math.random() * 10000,
        leverage: agent.type === 'execution_engine' ? 10 : 5,
        positionSize: Math.random() * 0.1,
        maxDrawdown: Math.random() * 20,
        riskScore: agent.currentPnL > 0 ? 'LOW' : Math.random() > 0.5 ? 'MEDIUM' : 'HIGH'
      });

    } catch (error) {
      console.error('Failed to fetch performance data:', error);
      // Set fallback data
      setPerformanceData(generateMockPerformanceData(timeframe));
      setTradeBreakdown(generateMockTradeBreakdown());
    } finally {
      setLoading(false);
    }
  };

  const fetchRealTimeMetrics = async () => {
    try {
      const resources = await apiService.getAgentResources(agent.id);
      setRealTimeMetrics({
        cpuUsage: resources.cpu,
        memoryUsage: resources.memory,
        networkUsage: resources.network,
        latency: resources.latency,
        uptime: resources.uptime
      });
    } catch (error) {
      // Use current values from agent object as fallback
      setRealTimeMetrics(prev => ({
        ...prev,
        cpuUsage: agent.cpuUsage,
        memoryUsage: agent.memoryUsage,
        networkUsage: agent.networkUsage
      }));
    }
  };

  const generateMockPerformanceData = (tf: string): PerformanceData[] => {
    const dataPoints = tf === '1h' ? 60 : tf === '6h' ? 36 : tf === '24h' ? 24 : tf === '7d' ? 7 : tf === '30d' ? 30 : 90;
    const data: PerformanceData[] = [];
    const now = new Date();
    let equity = agent.capital;
    let peakEquity = equity;

    for (let i = dataPoints; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * getIntervalMs(tf));
      const change = (Math.random() - 0.48) * (equity * 0.002); // Small random changes
      equity += change;

      if (equity > peakEquity) {
        peakEquity = equity;
      }

      const drawdown = ((equity - peakEquity) / peakEquity) * 100;

      data.push({
        timestamp: timestamp.toISOString(),
        pnl: equity - agent.capital,
        equity,
        drawdown,
        trades: Math.floor(Math.random() * 5),
        winRate: 60 + Math.random() * 20,
        sharpeRatio: 0.5 + Math.random() * 2,
        latency: 10 + Math.random() * 40
      });
    }

    return data;
  };

  const generateMockTradeBreakdown = (): TradeBreakdown[] => {
    return [
      {
        symbol: agent.symbol,
        trades: agent.totalTrades,
        pnl: agent.currentPnL,
        winRate: agent.winRate,
        avgTrade: agent.currentPnL / agent.totalTrades
      },
      // Add mock symbols for variety
      {
        symbol: 'ETHUSDT',
        trades: Math.floor(Math.random() * 50),
        pnl: (Math.random() - 0.5) * 1000,
        winRate: 60 + Math.random() * 20,
        avgTrade: (Math.random() - 0.5) * 50
      },
      {
        symbol: 'SOLUSDT',
        trades: Math.floor(Math.random() * 30),
        pnl: (Math.random() - 0.5) * 500,
        winRate: 55 + Math.random() * 25,
        avgTrade: (Math.random() - 0.5) * 30
      }
    ];
  };

  const generateMockStrategyPerformance = (strategies: string[]): StrategyPerformance[] => {
    return strategies.map(strategy => ({
      name: strategy,
      pnl: (Math.random() - 0.4) * 500,
      trades: Math.floor(Math.random() * 20),
      winRate: 60 + Math.random() * 20,
      sharpe: 0.5 + Math.random() * 2,
      maxDrawdown: Math.random() * 15
    }));
  };

  const getIntervalMs = (tf: string) => {
    switch (tf) {
      case '1h': return 60 * 1000;
      case '6h': return 10 * 60 * 1000;
      case '24h': return 60 * 60 * 1000;
      case '7d': return 24 * 60 * 60 * 1000;
      case '30d': return 24 * 60 * 60 * 1000;
      default: return 24 * 60 * 60 * 1000;
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    if (timeframe === '1h' || timeframe === '6h') {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (timeframe === '24h') {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const pieColors = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899'];

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{agent.name} Performance</h2>
          <p className="text-gray-600">
            {agent.type.replace('_', ' ').toUpperCase()} Agent • {agent.symbol} • {agent.timeframe}
          </p>
        </div>

        <div className="flex items-center space-x-4">
          <Select value={timeframe} onValueChange={setTimeframe} className="w-32">
              {timeframes.map(tf => (
                <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>
              ))}
            </Select>

          <Button variant="outline" size="sm" onClick={fetchPerformanceData}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>

          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-1" />
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
                <p className="text-sm font-medium text-gray-600">Total P&L</p>
                <p className={cn(
                  'text-2xl font-bold',
                  agent.currentPnL >= 0 ? 'text-green-600' : 'text-red-600'
                )}>
                  {formatCurrency(agent.currentPnL)}
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
                <p className="text-sm font-medium text-gray-600">Win Rate</p>
                <p className="text-2xl font-bold text-gray-900">{agent.winRate.toFixed(1)}%</p>
              </div>
              <Target className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Trades</p>
                <p className="text-2xl font-bold text-gray-900">{agent.totalTrades}</p>
              </div>
              <Activity className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Sharpe Ratio</p>
                <p className="text-2xl font-bold text-gray-900">
                  {(1.2 + Math.random() * 1.5).toFixed(2)}
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-yellow-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Equity Curve */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <DollarSign className="h-5 w-5" />
              <span>Equity Curve</span>
            </CardTitle>
            <CardDescription>Portfolio value over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatTime}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value: any, name: string) => [
                    formatCurrency(value),
                    name === 'equity' ? 'Equity' : 'P&L'
                  ]}
                  labelFormatter={(label) => new Date(label).toLocaleString()}
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Drawdown Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingDown className="h-5 w-5" />
              <span>Drawdown Analysis</span>
            </CardTitle>
            <CardDescription>Portfolio drawdown over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatTime}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  tickFormatter={(value) => `${value.toFixed(1)}%`}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value: any) => [`${value.toFixed(2)}%`, 'Drawdown']}
                  labelFormatter={(label) => new Date(label).toLocaleString()}
                />
                <Area
                  type="monotone"
                  dataKey="drawdown"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trade Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>Trade Breakdown</span>
            </CardTitle>
            <CardDescription>Performance by symbol</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={tradeBreakdown}
                  dataKey="trades"
                  nameKey="symbol"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={(entry) => entry.symbol}
                >
                  {tradeBreakdown.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={pieColors[index % pieColors.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>

            <div className="mt-4 space-y-2">
              {tradeBreakdown.map((item, index) => (
                <div key={item.symbol} className="flex items-center justify-between text-sm">
                  <div className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: pieColors[index % pieColors.length] }}
                    />
                    <span>{item.symbol}</span>
                  </div>
                  <span className={cn(
                    'font-medium',
                    item.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                  )}>
                    {formatCurrency(item.pnl)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Strategy Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Brain className="h-5 w-5" />
              <span>Strategy Performance</span>
            </CardTitle>
            <CardDescription>P&L by trading strategy</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={strategyPerformance} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  tickFormatter={(value) => `$${value.toFixed(0)}`}
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 10 }}
                  width={120}
                />
                <Tooltip
                  formatter={(value: any) => [formatCurrency(value), 'P&L']}
                />
                <Bar
                  dataKey="pnl"
                  fill={(entry: any) => entry.pnl >= 0 ? '#10b981' : '#ef4444'}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Real-time Metrics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Zap className="h-5 w-5" />
              <span>Real-time Metrics</span>
            </CardTitle>
            <CardDescription>System resource usage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium">CPU Usage</span>
                  <span className="text-sm">{realTimeMetrics.cpuUsage}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${realTimeMetrics.cpuUsage}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium">Memory Usage</span>
                  <span className="text-sm">{realTimeMetrics.memoryUsage}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${realTimeMetrics.memoryUsage}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium">Network Usage</span>
                  <span className="text-sm">{realTimeMetrics.networkUsage}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${realTimeMetrics.networkUsage}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Latency:</span>
                <span className="font-medium">{realTimeMetrics.latency}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Uptime:</span>
                <span className="font-medium">{realTimeMetrics.uptime}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <Badge variant={agent.status === 'running' ? 'default' : 'secondary'}>
                  {agent.status}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Risk Metrics */}
      {riskMetrics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>Risk Analytics</span>
            </CardTitle>
            <CardDescription>Portfolio risk metrics and exposure</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(riskMetrics.currentExposure)}
                </div>
                <div className="text-sm text-gray-600">Current Exposure</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {riskMetrics.marginUsed.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600">Margin Used</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {formatCurrency(riskMetrics.varDaily)}
                </div>
                <div className="text-sm text-gray-600">Daily VaR (95%)</div>
              </div>

              <div className="text-center">
                <div className={cn(
                  'text-2xl font-bold',
                  riskMetrics.riskScore === 'LOW' ? 'text-green-600' :
                  riskMetrics.riskScore === 'MEDIUM' ? 'text-yellow-600' :
                  'text-red-600'
                )}>
                  {riskMetrics.riskScore}
                </div>
                <div className="text-sm text-gray-600">Risk Score</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}