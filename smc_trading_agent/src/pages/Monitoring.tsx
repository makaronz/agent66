import { useState, useEffect, useRef } from 'react';
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
  RefreshCw,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface SystemMetrics {
  cpu: { usage: number; status: string };
  memory: { usage: number; status: string };
  disk: { usage: number; status: string };
  network: { latency: number; status: string };
}

interface Service {
  name: string;
  status: string;
  uptime: string;
  lastRestart: string;
}

interface Alert {
  id: number;
  type: 'error' | 'warning' | 'info';
  message: string;
  timestamp: string;
  service: string;
}

interface PerformanceData {
  orders24h: number;
  avgLatency: number;
  systemUptime: string;
  performanceData: Array<{ time: string; orders: number; latency: number }>;
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

// Tooltip component for explanations
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

// Status explanations
const statusExplanations: Record<string, string> = {
  healthy: 'System is operating normally within acceptable parameters.',
  warning: 'System is functioning but approaching threshold limits. Monitor closely.',
  critical: 'System is at or exceeding critical thresholds. Immediate attention required.',
  running: 'Service is operational and processing requests normally.',
  error: 'Service has encountered an error and may not be functioning correctly.',
  'error-alert': 'Critical issue detected. This alert indicates a problem that requires immediate attention.',
  'warning-alert': 'Warning condition detected. This alert indicates a potential issue that should be monitored.',
  'info-alert': 'Informational message. This alert provides status updates or successful operation notifications.'
};

export default function Monitoring() {
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState('24h');
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [performance, setPerformance] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMonitoringData = async () => {
    try {
      setError(null);
      const [metrics, servicesData, alertsData, performanceData] = await Promise.all([
        apiService.getSystemMetrics(),
        apiService.getServicesStatus(),
        apiService.getAlerts(),
        apiService.getPerformanceMetrics(selectedTimeframe)
      ]);
      
      setSystemMetrics(metrics);
      setServices(servicesData);
      setAlerts(alertsData);
      setPerformance(performanceData);
    } catch (err) {
      console.error('Error fetching monitoring data:', err);
      setError('Failed to load monitoring data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();
    // Refresh every 5 seconds
    const interval = setInterval(fetchMonitoringData, 5000);
    return () => clearInterval(interval);
  }, [selectedTimeframe]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchMonitoringData();
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
            onChange={(e) => setSelectedTimeframe(e.target.value)}
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

      {error && (
        <InfoTooltip content="This error indicates that the monitoring system was unable to fetch data from the API. This could be due to network issues, backend service being down, or API endpoint errors. Check backend logs for more details.">
          <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded-md cursor-help">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </InfoTooltip>
      )}

      {loading && !systemMetrics ? (
        <div className="text-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-gray-400" />
          <p className="mt-4 text-gray-600">Loading monitoring data...</p>
        </div>
      ) : (
        <>
          {/* System Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {systemMetrics && (
              <>
                <InfoTooltip content={`CPU Usage: ${systemMetrics.cpu.usage}%. Status: ${systemMetrics.cpu.status}. ${statusExplanations[systemMetrics.cpu.status] || statusExplanations.healthy}`}>
                  <div className="bg-white rounded-lg shadow p-6 cursor-help w-full">
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
                </InfoTooltip>

                <InfoTooltip content={`Memory Usage: ${systemMetrics.memory.usage}%. Status: ${systemMetrics.memory.status}. ${statusExplanations[systemMetrics.memory.status] || statusExplanations.healthy}`}>
                  <div className="bg-white rounded-lg shadow p-6 cursor-help w-full">
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
                </InfoTooltip>

                <InfoTooltip content={`Disk Usage: ${systemMetrics.disk.usage}%. Status: ${systemMetrics.disk.status}. ${statusExplanations[systemMetrics.disk.status] || statusExplanations.healthy}`}>
                  <div className="bg-white rounded-lg shadow p-6 cursor-help w-full">
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
                </InfoTooltip>

                <InfoTooltip content={`Network Latency: ${systemMetrics.network.latency}ms. Status: ${systemMetrics.network.status}. ${statusExplanations[systemMetrics.network.status] || statusExplanations.healthy}`}>
                  <div className="bg-white rounded-lg shadow p-6 cursor-help w-full">
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
                      <span>Live</span>
                    </div>
                  </div>
                </InfoTooltip>
              </>
            )}
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
                <InfoTooltip 
                  key={index}
                  content={`${service.name} - Status: ${service.status}. ${statusExplanations[service.status] || statusExplanations.running} Uptime: ${service.uptime}. Last restart: ${service.lastRestart}.`}
                >
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-help">
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
                </InfoTooltip>
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
              {alerts.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No alerts</p>
              ) : (
                alerts.map((alert) => (
                  <InfoTooltip
                    key={alert.id}
                    content={`${statusExplanations[`${alert.type}-alert`] || statusExplanations['info-alert']} Service: ${alert.service}. Time: ${formatTimestamp(alert.timestamp)}.`}
                  >
                    <div className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg cursor-help">
                      <div className="flex-shrink-0 mt-0.5">
                        {getAlertIcon(alert.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                        <div className="flex items-center space-x-2 mt-1">
                          <p className="text-xs text-gray-500">{alert.service}</p>
                          <span className="text-xs text-gray-400">•</span>
                          <p className="text-xs text-gray-500">{formatTimestamp(alert.timestamp)}</p>
                        </div>
                      </div>
                    </div>
                  </InfoTooltip>
                ))
              )}
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
              {performance && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-blue-600">{performance.orders24h.toLocaleString()}</p>
                      <p className="text-sm text-gray-600">Orders Processed ({selectedTimeframe === '24h' ? '24h' : selectedTimeframe === '7d' ? '7d' : '30d'})</p>
                      <div className="flex items-center justify-center space-x-1 mt-1 text-green-600">
                        <TrendingUp className="h-4 w-4" />
                        <span className="text-sm">Live</span>
                      </div>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-green-600">{performance.avgLatency}ms</p>
                      <p className="text-sm text-gray-600">Avg Execution Latency</p>
                      <div className="flex items-center justify-center space-x-1 mt-1 text-green-600">
                        <TrendingDown className="h-4 w-4" />
                        <span className="text-sm">Live</span>
                      </div>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-purple-600">{performance.systemUptime}</p>
                      <p className="text-sm text-gray-600">System Uptime</p>
                      <div className="flex items-center justify-center space-x-1 mt-1 text-green-600">
                        <TrendingUp className="h-4 w-4" />
                        <span className="text-sm">Live</span>
                      </div>
                    </div>
                  </div>

                  {/* Simple Performance Chart */}
                  <div className="mt-6">
                    <h4 className="text-sm font-medium text-gray-700 mb-4">Order Volume & Latency ({selectedTimeframe === '24h' ? '24h' : selectedTimeframe === '7d' ? '7d' : '30d'})</h4>
                    <div className="h-64 flex items-end space-x-2">
                      {performance.performanceData.map((data, index) => {
                        const maxOrders = Math.max(...performance.performanceData.map(d => d.orders), 1);
                        const maxLatency = Math.max(...performance.performanceData.map(d => d.latency), 1);
                        return (
                          <div key={index} className="flex-1 flex flex-col items-center space-y-2">
                            <div className="w-full flex flex-col space-y-1">
                              <div
                                className="bg-blue-500 rounded-t"
                                style={{ height: `${(data.orders / maxOrders) * 200}px` }}
                                title={`Orders: ${data.orders}`}
                              />
                              <div
                                className="bg-red-400 rounded-b"
                                style={{ height: `${(data.latency / maxLatency) * 50}px` }}
                                title={`Latency: ${data.latency}ms`}
                              />
                            </div>
                            <p className="text-xs text-gray-500">{data.time}</p>
                          </div>
                        );
                      })}
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
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}