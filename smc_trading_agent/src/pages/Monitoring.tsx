import { useState } from 'react';
import {
  Activity,
  Server,
  Wifi,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  HardDrive,
  MemoryStick,
  TrendingUp,
  TrendingDown,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';

const systemMetrics = {
  cpu: { usage: 45, status: 'healthy' },
  memory: { usage: 68, status: 'warning' },
  disk: { usage: 32, status: 'healthy' },
  network: { latency: 12, status: 'healthy' }
};

const services = [
  { name: 'Data Pipeline', status: 'running', uptime: '99.9%', lastRestart: '2 days ago' },
  { name: 'SMC Detector', status: 'running', uptime: '99.8%', lastRestart: '1 day ago' },
  { name: 'Execution Engine', status: 'running', uptime: '100%', lastRestart: '5 days ago' },
  { name: 'Risk Manager', status: 'warning', uptime: '98.5%', lastRestart: '2 hours ago' },
  { name: 'Decision Engine', status: 'running', uptime: '99.7%', lastRestart: '3 days ago' },
  { name: 'Compliance Monitor', status: 'running', uptime: '99.9%', lastRestart: '4 days ago' }
];

const alerts = [
  {
    id: 1,
    type: 'warning',
    message: 'High memory usage detected on Risk Manager service',
    timestamp: '2 minutes ago',
    service: 'Risk Manager'
  },
  {
    id: 2,
    type: 'info',
    message: 'Data Pipeline successfully processed 1M+ market events',
    timestamp: '15 minutes ago',
    service: 'Data Pipeline'
  },
  {
    id: 3,
    type: 'error',
    message: 'Connection timeout to Binance API (recovered)',
    timestamp: '1 hour ago',
    service: 'Exchange Connector'
  }
];

const performanceData = [
  { time: '00:00', orders: 45, latency: 12 },
  { time: '04:00', orders: 32, latency: 15 },
  { time: '08:00', orders: 78, latency: 18 },
  { time: '12:00', orders: 156, latency: 22 },
  { time: '16:00', orders: 234, latency: 28 },
  { time: '20:00', orders: 189, latency: 25 }
];

export default function Monitoring() {
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState('24h');

  const handleRefresh = async () => {
    setRefreshing(true);
    // Simulate refresh
    setTimeout(() => {
      setRefreshing(false);
    }, 1000);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
      case 'healthy':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'error':
      case 'critical':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
      case 'healthy':
        return <CheckCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4" />;
      case 'error':
      case 'critical':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'info':
        return <CheckCircle className="h-4 w-4 text-blue-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Monitoring</h1>
          <p className="text-gray-600">Real-time system health, performance metrics, and alerts</p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={selectedTimeframe}
            onChange={(e) => { setSelectedTimeframe(e.target.value); }}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={cn(
              "flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors",
              refreshing
                ? "bg-gray-400 text-white cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 text-white"
            )}
          >
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">CPU Usage</p>
              <p className="text-2xl font-bold text-gray-900">{systemMetrics.cpu.usage}%</p>
            </div>
            <div className={cn(
              "p-3 rounded-full",
              getStatusColor(systemMetrics.cpu.status)
            )}>
              <Cpu className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${systemMetrics.cpu.usage}%` }}
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Memory Usage</p>
              <p className="text-2xl font-bold text-gray-900">{systemMetrics.memory.usage}%</p>
            </div>
            <div className={cn(
              "p-3 rounded-full",
              getStatusColor(systemMetrics.memory.status)
            )}>
              <MemoryStick className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-yellow-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${systemMetrics.memory.usage}%` }}
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Disk Usage</p>
              <p className="text-2xl font-bold text-gray-900">{systemMetrics.disk.usage}%</p>
            </div>
            <div className={cn(
              "p-3 rounded-full",
              getStatusColor(systemMetrics.disk.status)
            )}>
              <HardDrive className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${systemMetrics.disk.usage}%` }}
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Network Latency</p>
              <p className="text-2xl font-bold text-gray-900">{systemMetrics.network.latency}ms</p>
            </div>
            <div className={cn(
              "p-3 rounded-full",
              getStatusColor(systemMetrics.network.status)
            )}>
              <Wifi className="h-6 w-6" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-green-600">
            <TrendingDown className="h-4 w-4" />
            <span>-2ms from last hour</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Services Status */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
              <Server className="h-5 w-5" />
              <span>Services Status</span>
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {services.map((service, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={cn(
                      "p-2 rounded-full",
                      getStatusColor(service.status)
                    )}>
                      {getStatusIcon(service.status)}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{service.name}</p>
                      <p className="text-sm text-gray-500">Uptime: {service.uptime}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={cn(
                      "text-sm font-medium capitalize",
                      service.status === 'running' ? 'text-green-600' :
                      service.status === 'warning' ? 'text-yellow-600' : 'text-red-600'
                    )}>
                      {service.status}
                    </p>
                    <p className="text-xs text-gray-500">Last restart: {service.lastRestart}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5" />
              <span>Recent Alerts</span>
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {alerts.map((alert) => (
                <div key={alert.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0 mt-0.5">
                    {getAlertIcon(alert.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <p className="text-xs text-gray-500">{alert.service}</p>
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

      {/* Performance Metrics */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>Performance Metrics</span>
          </h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">1,234</p>
              <p className="text-sm text-gray-600">Orders Processed (24h)</p>
              <div className="flex items-center justify-center space-x-1 mt-1 text-green-600">
                <TrendingUp className="h-4 w-4" />
                <span className="text-sm">+12%</span>
              </div>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">18ms</p>
              <p className="text-sm text-gray-600">Avg Execution Latency</p>
              <div className="flex items-center justify-center space-x-1 mt-1 text-green-600">
                <TrendingDown className="h-4 w-4" />
                <span className="text-sm">-3ms</span>
              </div>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">99.8%</p>
              <p className="text-sm text-gray-600">System Uptime</p>
              <div className="flex items-center justify-center space-x-1 mt-1 text-green-600">
                <TrendingUp className="h-4 w-4" />
                <span className="text-sm">+0.1%</span>
              </div>
            </div>
          </div>

          {/* Simple Performance Chart */}
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-700 mb-4">Order Volume & Latency (24h)</h4>
            <div className="h-64 flex items-end space-x-2">
              {performanceData.map((data, index) => (
                <div key={index} className="flex-1 flex flex-col items-center space-y-2">
                  <div className="w-full flex flex-col space-y-1">
                    <div
                      className="bg-blue-500 rounded-t"
                      style={{ height: `${(data.orders / 250) * 100}px` }}
                      title={`Orders: ${data.orders}`}
                    />
                    <div
                      className="bg-red-400 rounded-b"
                      style={{ height: `${(data.latency / 30) * 50}px` }}
                      title={`Latency: ${data.latency}ms`}
                    />
                  </div>
                  <p className="text-xs text-gray-500">{data.time}</p>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center space-x-6 mt-4 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded" />
                <span className="text-gray-600">Orders</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-400 rounded" />
                <span className="text-gray-600">Latency (ms)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}