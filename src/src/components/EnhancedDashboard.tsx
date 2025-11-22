import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts';
import {
  Activity, AlertTriangle, TrendingUp, TrendingDown, DollarSign,
  Cpu, HardDrive, Zap, Target, Clock, Bell, CheckCircle, XCircle,
  RefreshCw, Download, Settings, Filter, Search, Calendar, ChevronDown
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types for dashboard data
interface DashboardMetric {
  id: string;
  name: string;
  value: number;
  unit: string;
  timestamp: string;
  change_24h?: number;
  change_pct_24h?: number;
  status: 'normal' | 'warning' | 'critical';
  metadata?: Record<string, any>;
}

interface AlertNotification {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  component: string;
  metrics?: Record<string, any>;
}

interface TradingSignal {
  id: string;
  symbol: string;
  strategy: string;
  signal_type: 'buy' | 'sell' | 'hold';
  confidence: number;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  timestamp: string;
  smc_patterns: string[];
  risk_score: number;
}

interface PerformanceData {
  timestamp: string;
  portfolio_value: number;
  drawdown: number;
  returns: number;
  sharpe_ratio: number;
  win_rate: number;
  profit_factor: number;
}

interface SystemMetrics {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: number;
  latency: number;
}

const EnhancedDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<Record<string, DashboardMetric>>({});
  const [alerts, setAlerts] = useState<AlertNotification[]>([]);
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1H');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [alertFilter, setAlertFilter] = useState<string>('all');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const wsUrl = process.env.NODE_ENV === 'production'
          ? `wss://${window.location.host}/ws/dashboard`
          : `ws://localhost:8000/ws/dashboard`;

        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          console.log('Dashboard WebSocket connected');
          setIsConnected(true);
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
        };

        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        wsRef.current.onclose = () => {
          console.log('Dashboard WebSocket disconnected');
          setIsConnected(false);
          // Attempt to reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
        };

        wsRef.current.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleWebSocketMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'initial_data':
        setMetrics(data.data.metrics);
        setAlerts(data.data.alerts);
        setSignals(data.data.signals);
        if (data.data.performance) {
          setPerformanceData([data.data.performance]);
        }
        break;
      case 'metrics_update':
        setMetrics(prev => ({ ...prev, ...data.data }));
        break;
      case 'alert':
        setAlerts(prev => [data.data, ...prev.slice(0, 49)]); // Keep last 50
        break;
      case 'signal':
        setSignals(prev => [data.data, ...prev.slice(0, 19)]); // Keep last 20
        break;
      case 'performance_update':
        setPerformanceData(prev => [...prev.slice(-99), data.data]); // Keep last 100
        break;
      case 'system_metrics_update':
        setSystemMetrics(prev => [...prev.slice(-99), data.data]); // Keep last 100
        break;
    }
  }, []);

  // Calculate performance metrics
  const calculatePerformanceMetrics = useCallback(() => {
    if (performanceData.length < 2) return null;

    const latest = performanceData[performanceData.length - 1];
    const previous = performanceData[performanceData.length - 2];

    return {
      totalReturn: ((latest.portfolio_value - 10000) / 10000) * 100, // Assuming $10k starting capital
      dailyReturn: ((latest.portfolio_value - previous.portfolio_value) / previous.portfolio_value) * 100,
      currentDrawdown: latest.drawdown,
      sharpeRatio: latest.sharpe_ratio,
      winRate: latest.win_rate * 100,
      profitFactor: latest.profit_factor,
      volatility: calculateVolatility(performanceData)
    };
  }, [performanceData]);

  const calculateVolatility = (data: PerformanceData[]) => {
    if (data.length < 2) return 0;

    const returns = data.slice(1).map((point, i) =>
      (point.portfolio_value - data[i].portfolio_value) / data[i].portfolio_value
    );

    const mean = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / returns.length;

    return Math.sqrt(variance * 252) * 100; // Annualized volatility
  };

  const performanceMetrics = calculatePerformanceMetrics();

  // Mock data for demonstration
  const mockPerformanceData = Array.from({ length: 50 }, (_, i) => ({
    timestamp: new Date(Date.now() - (49 - i) * 3600000).toISOString(),
    portfolio_value: 10000 + Math.random() * 2000 - 500,
    drawdown: Math.random() * 0.1,
    returns: Math.random() * 0.05 - 0.02,
    sharpe_ratio: 1 + Math.random() * 0.5,
    win_rate: 0.6 + Math.random() * 0.2,
    profit_factor: 1.5 + Math.random()
  }));

  const mockSystemMetrics = Array.from({ length: 50 }, (_, i) => ({
    timestamp: new Date(Date.now() - (49 - i) * 60000).toISOString(),
    cpu_usage: 20 + Math.random() * 60,
    memory_usage: 40 + Math.random() * 40,
    disk_usage: 60 + Math.random() * 20,
    network_io: Math.random() * 100,
    latency: 10 + Math.random() * 40
  }));

  const displayData = {
    performance: performanceData.length > 0 ? performanceData : mockPerformanceData,
    systemMetrics: systemMetrics.length > 0 ? systemMetrics : mockSystemMetrics
  };

  const filteredAlerts = alerts.filter(alert =>
    alertFilter === 'all' || alert.severity === alertFilter
  );

  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert =>
      alert.id === alertId ? { ...alert, acknowledged: true } : alert
    ));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical': return 'text-red-600 bg-red-50';
      case 'warning': return 'text-yellow-600 bg-yellow-50';
      case 'normal': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-500 bg-red-50';
      case 'high': return 'border-orange-500 bg-orange-50';
      case 'medium': return 'border-yellow-500 bg-yellow-50';
      case 'low': return 'border-blue-500 bg-blue-50';
      default: return 'border-gray-500 bg-gray-50';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      {/* Header */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Enhanced Trading Dashboard</h1>
            <p className="text-gray-600 mt-1">Real-time monitoring and analytics for SMC Trading System</p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={cn(
                "w-3 h-3 rounded-full",
                isConnected ? "bg-green-500" : "bg-red-500"
              )} />
              <span className="text-sm text-gray-600">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>

            {/* Timeframe Selector */}
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="5M">5 Minutes</option>
              <option value="15M">15 Minutes</option>
              <option value="1H">1 Hour</option>
              <option value="4H">4 Hours</option>
              <option value="1D">1 Day</option>
            </select>

            {/* Auto Refresh Toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn(
                "flex items-center space-x-2 px-3 py-2 rounded-md transition-colors",
                autoRefresh
                  ? "bg-green-100 text-green-700 hover:bg-green-200"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              )}
            >
              <RefreshCw className={cn("w-4 h-4", autoRefresh && "animate-spin")} />
              <span className="text-sm">Auto Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Key Performance Metrics */}
      {performanceMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Total Return"
            value={`${performanceMetrics.totalReturn.toFixed(2)}%`}
            change={performanceMetrics.dailyReturn}
            icon={TrendingUp}
            trend={performanceMetrics.dailyReturn >= 0 ? 'up' : 'down'}
          />
          <MetricCard
            title="Sharpe Ratio"
            value={performanceMetrics.sharpeRatio.toFixed(2)}
            icon={Target}
          />
          <MetricCard
            title="Win Rate"
            value={`${performanceMetrics.winRate.toFixed(1)}%`}
            icon={CheckCircle}
          />
          <MetricCard
            title="Profit Factor"
            value={performanceMetrics.profitFactor.toFixed(2)}
            icon={DollarSign}
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Charts Area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Portfolio Performance Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Portfolio Performance</h2>
              <div className="flex space-x-2">
                <button className="p-2 text-gray-500 hover:text-gray-700">
                  <Download className="w-4 h-4" />
                </button>
                <button className="p-2 text-gray-500 hover:text-gray-700">
                  <Settings className="w-4 h-4" />
                </button>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={displayData.performance}>
                <defs>
                  <linearGradient id="colorPortfolio" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="timestamp"
                  stroke="#6b7280"
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <YAxis yAxisId="left" stroke="#6b7280" />
                <YAxis yAxisId="right" orientation="right" stroke="#ef4444" />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                  formatter={(value: any, name: string) => [
                    name === 'portfolio_value' ? `$${value.toFixed(2)}` : `${(value * 100).toFixed(2)}%`,
                    name === 'portfolio_value' ? 'Portfolio Value' : 'Drawdown'
                  ]}
                />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="portfolio_value"
                  stroke="#10b981"
                  fill="url(#colorPortfolio)"
                  strokeWidth={2}
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="drawdown"
                  stroke="#ef4444"
                  fill="url(#colorDrawdown)"
                  strokeWidth={1}
                />
                <Legend
                  formatter={(value) => value === 'portfolio_value' ? 'Portfolio Value' : 'Drawdown'}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* System Metrics Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">System Resources</h2>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Activity className="w-4 h-4" />
                <span>Live</span>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={displayData.systemMetrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="timestamp"
                  stroke="#6b7280"
                  tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                />
                <YAxis stroke="#6b7280" domain={[0, 100]} />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                  formatter={(value: any, name: string) => [
                    `${value.toFixed(1)}%`,
                    name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="cpu_usage"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="memory_usage"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="disk_usage"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                />
                <Legend
                  formatter={(value) => value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Trading Signals */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Recent Trading Signals</h2>
              <span className="text-sm text-gray-500">Last 20 signals</span>
            </div>

            <div className="space-y-3 max-h-64 overflow-y-auto">
              {signals.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No signals received</p>
              ) : (
                signals.map((signal) => (
                  <div key={signal.id} className="border rounded-lg p-3 hover:bg-gray-50">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-gray-900">{signal.symbol}</span>
                          <span className={cn(
                            "px-2 py-1 text-xs font-medium rounded",
                            signal.signal_type === 'buy' ? "bg-green-100 text-green-800" :
                            signal.signal_type === 'sell' ? "bg-red-100 text-red-800" :
                            "bg-gray-100 text-gray-800"
                          )}>
                            {signal.signal_type.toUpperCase()}
                          </span>
                          <span className="text-sm text-gray-500">{signal.strategy}</span>
                        </div>
                        <div className="mt-1 text-sm text-gray-600">
                          Confidence: {(signal.confidence * 100).toFixed(1)}%
                          {signal.entry_price && ` | Entry: $${signal.entry_price.toFixed(2)}`}
                        </div>
                        {signal.smc_patterns.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {signal.smc_patterns.map((pattern, i) => (
                              <span key={i} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                                {pattern}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 ml-4">
                        {new Date(signal.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* System Health */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">System Health</h2>
            <div className="space-y-3">
              <HealthIndicator
                name="Data Pipeline"
                status={metrics['data_pipeline_status']?.status || 'normal'}
                latency={metrics['data_pipeline_latency']?.value || 12}
              />
              <HealthIndicator
                name="SMC Detector"
                status={metrics['smc_detector_status']?.status || 'normal'}
                latency={metrics['smc_detector_latency']?.value || 8}
              />
              <HealthIndicator
                name="Risk Manager"
                status={metrics['risk_manager_status']?.status || 'warning'}
                latency={metrics['risk_manager_latency']?.value || 15}
              />
              <HealthIndicator
                name="Execution Engine"
                status={metrics['execution_engine_status']?.status || 'normal'}
                latency={metrics['execution_engine_latency']?.value || 5}
              />
            </div>
          </div>

          {/* Alerts */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Active Alerts</h2>
              <select
                value={alertFilter}
                onChange={(e) => setAlertFilter(e.target.value)}
                className="text-xs border border-gray-300 rounded px-2 py-1"
              >
                <option value="all">All</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {filteredAlerts.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No active alerts</p>
              ) : (
                filteredAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={cn(
                      "border-l-4 p-3 rounded-r",
                      getSeverityColor(alert.severity),
                      alert.acknowledged && "opacity-60"
                    )}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <p className="font-medium text-sm text-gray-900">{alert.title}</p>
                        <p className="text-xs text-gray-600 mt-1">{alert.message}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {alert.component} • {new Date(alert.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                      {!alert.acknowledged && (
                        <button
                          onClick={() => acknowledgeAlert(alert.id)}
                          className="ml-2 p-1 text-gray-400 hover:text-gray-600"
                          title="Acknowledge"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Risk Metrics */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Metrics</h2>
            <div className="space-y-3">
              <RiskMetric
                label="Current Risk Score"
                value={metrics['risk_score']?.value || 0.3}
                max={1}
                unit=""
                threshold={0.7}
              />
              <RiskMetric
                label="Daily VaR (95%)"
                value={metrics['daily_var']?.value || 2.1}
                max={5}
                unit="%"
                threshold={4}
              />
              <RiskMetric
                label="Max Drawdown"
                value={performanceMetrics?.currentDrawdown || 0.05}
                max={0.2}
                unit="%"
                threshold={0.15}
              />
              <RiskMetric
                label="Open Positions"
                value={metrics['open_positions']?.value || 3}
                max={10}
                unit=""
                threshold={8}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper Components
interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ElementType;
  trend?: 'up' | 'down';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, change, icon: Icon, trend }) => {
  const changeColor = change && change >= 0 ? 'text-green-600' : 'text-red-600';
  const TrendIcon = change && change >= 0 ? TrendingUp : TrendingDown;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {change !== undefined && (
            <div className={cn("flex items-center mt-2 text-sm", changeColor)}>
              <TrendIcon className="w-4 h-4 mr-1" />
              <span>{Math.abs(change).toFixed(2)}%</span>
            </div>
          )}
        </div>
        <Icon className="w-8 h-8 text-gray-400" />
      </div>
    </div>
  );
};

interface HealthIndicatorProps {
  name: string;
  status: string;
  latency: number;
}

const HealthIndicator: React.FC<HealthIndicatorProps> = ({ name, status, latency }) => {
  const statusColors = {
    normal: 'bg-green-500',
    warning: 'bg-yellow-500',
    critical: 'bg-red-500'
  };

  return (
    <div className="flex items-center justify-between p-2 rounded hover:bg-gray-50">
      <div className="flex items-center space-x-3">
        <div className={cn("w-2 h-2 rounded-full", statusColors[status as keyof typeof statusColors])} />
        <span className="text-sm font-medium text-gray-700">{name}</span>
      </div>
      <span className="text-xs text-gray-500">{latency}ms</span>
    </div>
  );
};

interface RiskMetricProps {
  label: string;
  value: number;
  max: number;
  unit: string;
  threshold: number;
}

const RiskMetric: React.FC<RiskMetricProps> = ({ label, value, max, unit, threshold }) => {
  const percentage = (value / max) * 100;
  const isWarning = value > threshold;

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={cn("text-sm font-medium", isWarning ? 'text-red-600' : 'text-gray-900')}>
          {unit === '%' ? (value * 100).toFixed(1) : value.toFixed(1)}{unit}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={cn(
            "h-2 rounded-full transition-all duration-300",
            isWarning ? 'bg-red-500' : percentage > 70 ? 'bg-yellow-500' : 'bg-green-500'
          )}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
};

export default EnhancedDashboard;