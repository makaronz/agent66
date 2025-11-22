import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  AlertTriangle, Bell, BellRing, CheckCircle, XCircle, Info, Zap, Shield,
  Clock, TrendingUp, TrendingDown, Activity, Filter, Search, X,
  ChevronDown, ChevronRight, Volume2, VolumeX, Settings, Download
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
interface Alert {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'system' | 'trading' | 'risk' | 'performance' | 'data';
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  resolved: boolean;
  component: string;
  metrics?: Record<string, any>;
  actions?: AlertAction[];
  details?: AlertDetails;
}

interface AlertAction {
  id: string;
  label: string;
  type: 'primary' | 'secondary' | 'danger';
  handler: () => void;
}

interface AlertDetails {
  current_value: number;
  threshold_value: number;
  historical_data?: Array<{ timestamp: string; value: number }>;
  recommendations: string[];
  related_alerts: string[];
}

interface AlertRule {
  id: string;
  name: string;
  enabled: boolean;
  metric: string;
  condition: 'greater_than' | 'less_than' | 'equal' | 'not_equal';
  threshold: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'system' | 'trading' | 'risk' | 'performance' | 'data';
  cooldown_minutes: number;
  notification_channels: string[];
}

const RealTimeAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [autoAcknowledge, setAutoAcknowledge] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [expandedAlert, setExpandedAlert] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Mock initial data
  useEffect(() => {
    // Initialize with sample alerts
    const sampleAlerts: Alert[] = [
      {
        id: '1',
        severity: 'critical',
        category: 'risk',
        title: 'Maximum Drawdown Exceeded',
        message: 'Portfolio drawdown has exceeded the 10% threshold. Current drawdown: 12.3%',
        timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
        acknowledged: false,
        resolved: false,
        component: 'Risk Manager',
        metrics: {
          current_drawdown: 12.3,
          max_allowed_drawdown: 10,
          portfolio_value: 8765,
          initial_capital: 10000
        },
        actions: [
          {
            id: 'reduce_positions',
            label: 'Reduce Positions',
            type: 'danger',
            handler: () => console.log('Reducing positions...')
          },
          {
            id: 'review_strategy',
            label: 'Review Strategy',
            type: 'primary',
            handler: () => console.log('Opening strategy review...')
          }
        ],
        details: {
          current_value: 12.3,
          threshold_value: 10,
          recommendations: [
            'Consider reducing position sizes',
            'Review stop-loss levels',
            'Analyze recent losing trades',
            'Consider temporary trading halt'
          ],
          related_alerts: ['2', '3']
        }
      },
      {
        id: '2',
        severity: 'high',
        category: 'system',
        title: 'High CPU Usage',
        message: 'System CPU usage has been above 80% for the last 10 minutes',
        timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
        acknowledged: true,
        resolved: false,
        component: 'System Monitor',
        metrics: {
          cpu_usage: 85.2,
          memory_usage: 67.8,
          active_processes: 147
        },
        details: {
          current_value: 85.2,
          threshold_value: 80,
          recommendations: [
            'Check for resource-intensive processes',
            'Consider scaling up resources',
            'Monitor system performance'
          ],
          related_alerts: []
        }
      },
      {
        id: '3',
        severity: 'medium',
        category: 'trading',
        title: 'Low Win Rate Detected',
        message: 'Strategy win rate has dropped below 50% over the last 50 trades',
        timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        acknowledged: false,
        resolved: false,
        component: 'Performance Monitor',
        metrics: {
          current_win_rate: 48.2,
          minimum_win_rate: 50,
          recent_trades: 50,
          winning_trades: 24
        }
      },
      {
        id: '4',
        severity: 'low',
        category: 'data',
        title: 'Data Quality Degradation',
        message: 'Market data delay detected. Average latency: 250ms (threshold: 200ms)',
        timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
        acknowledged: false,
        resolved: false,
        component: 'Data Pipeline',
        metrics: {
          current_latency: 250,
          threshold_latency: 200,
          completeness_score: 0.94
        }
      }
    ];

    setAlerts(sampleAlerts);

    // Initialize alert rules
    const sampleRules: AlertRule[] = [
      {
        id: 'rule1',
        name: 'Max Drawdown Alert',
        enabled: true,
        metric: 'drawdown_percentage',
        condition: 'greater_than',
        threshold: 10,
        severity: 'critical',
        category: 'risk',
        cooldown_minutes: 15,
        notification_channels: ['web', 'email', 'sms']
      },
      {
        id: 'rule2',
        name: 'CPU Usage Alert',
        enabled: true,
        metric: 'cpu_usage',
        condition: 'greater_than',
        threshold: 80,
        severity: 'high',
        category: 'system',
        cooldown_minutes: 10,
        notification_channels: ['web']
      },
      {
        id: 'rule3',
        name: 'Win Rate Alert',
        enabled: true,
        metric: 'win_rate',
        condition: 'less_than',
        threshold: 50,
        severity: 'medium',
        category: 'trading',
        cooldown_minutes: 30,
        notification_channels: ['web', 'email']
      }
    ];

    setAlertRules(sampleRules);
  }, []);

  // WebSocket connection for real-time alerts
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const wsUrl = process.env.NODE_ENV === 'production'
          ? `wss://${window.location.host}/ws/alerts`
          : `ws://localhost:8000/ws/alerts`;

        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          setIsConnected(true);
          console.log('Alerts WebSocket connected');
        };

        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'new_alert') {
              handleNewAlert(data.alert);
            } else if (data.type === 'alert_updated') {
              handleAlertUpdated(data.alert);
            }
          } catch (error) {
            console.error('Error parsing alert message:', error);
          }
        };

        wsRef.current.onclose = () => {
          setIsConnected(false);
          setTimeout(connectWebSocket, 5000);
        };

        wsRef.current.onerror = (error) => {
          console.error('Alerts WebSocket error:', error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error('Failed to connect alerts WebSocket:', error);
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleNewAlert = useCallback((alert: Alert) => {
    setAlerts(prev => [alert, ...prev]);

    if (soundEnabled && !alert.acknowledged) {
      playAlertSound(alert.severity);
    }

    if (autoAcknowledge && alert.severity === 'low') {
      acknowledgeAlert(alert.id);
    }
  }, [soundEnabled, autoAcknowledge]);

  const handleAlertUpdated = useCallback((updatedAlert: Alert) => {
    setAlerts(prev => prev.map(alert =>
      alert.id === updatedAlert.id ? updatedAlert : alert
    ));
  }, []);

  const playAlertSound = (severity: string) => {
    if (!soundEnabled) return;

    const audio = new Audio();
    switch (severity) {
      case 'critical':
        audio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
        break;
      case 'high':
        audio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
        break;
      default:
        return;
    }
    audio.play().catch(console.error);
  };

  const acknowledgeAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert =>
      alert.id === alertId ? { ...alert, acknowledged: true } : alert
    ));

    // Send acknowledgment to server
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'acknowledge_alert',
        alert_id: alertId
      }));
    }
  };

  const resolveAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert =>
      alert.id === alertId ? { ...alert, resolved: true } : alert
    ));

    // Send resolution to server
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'resolve_alert',
        alert_id: alertId
      }));
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    const matchesSeverity = selectedSeverity === 'all' || alert.severity === selectedSeverity;
    const matchesCategory = selectedCategory === 'all' || alert.category === selectedCategory;
    const matchesSearch = searchQuery === '' ||
      alert.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.message.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesSeverity && matchesCategory && matchesSearch;
  });

  const unacknowledgedCount = alerts.filter(a => !a.acknowledged).length;
  const criticalCount = alerts.filter(a => a.severity === 'critical' && !a.resolved).length;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'system': return Activity;
      case 'trading': return TrendingUp;
      case 'risk': return Shield;
      case 'performance': return TrendingDown;
      case 'data': return Info;
      default: return Bell;
    }
  };

  const exportAlerts = () => {
    const csvContent = [
      ['ID', 'Severity', 'Category', 'Title', 'Message', 'Timestamp', 'Acknowledged', 'Resolved'],
      ...filteredAlerts.map(alert => [
        alert.id,
        alert.severity,
        alert.category,
        alert.title,
        alert.message,
        alert.timestamp,
        alert.acknowledged,
        alert.resolved
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `alerts_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-gray-900">Real-Time Alerts</h1>
              <div className="flex items-center space-x-2">
                <div className={cn(
                  "w-3 h-3 rounded-full",
                  isConnected ? "bg-green-500" : "bg-red-500"
                )} />
                <span className="text-sm text-gray-600">
                  {isConnected ? "Connected" : "Disconnected"}
                </span>
              </div>
              {unacknowledgedCount > 0 && (
                <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium">
                  {unacknowledgedCount} unacknowledged
                </span>
              )}
              {criticalCount > 0 && (
                <span className="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-medium animate-pulse">
                  {criticalCount} critical
                </span>
              )}
            </div>

            <div className="flex items-center space-x-4">
              <button
                onClick={() => setSoundEnabled(!soundEnabled)}
                className={cn(
                  "p-2 rounded-lg transition-colors",
                  soundEnabled ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"
                )}
              >
                {soundEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
              </button>

              <button
                onClick={() => setShowRules(!showRules)}
                className={cn(
                  "p-2 rounded-lg transition-colors",
                  showRules ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"
                )}
              >
                <Settings className="w-5 h-5" />
              </button>

              <button
                onClick={exportAlerts}
                className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <Download className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="mt-4 flex flex-wrap gap-4">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Categories</option>
                <option value="system">System</option>
                <option value="trading">Trading</option>
                <option value="risk">Risk</option>
                <option value="performance">Performance</option>
                <option value="data">Data</option>
              </select>
            </div>

            <div className="flex items-center space-x-2 flex-1 max-w-md">
              <Search className="w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search alerts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <label className="flex items-center space-x-2 text-sm">
              <input
                type="checkbox"
                checked={autoAcknowledge}
                onChange={(e) => setAutoAcknowledge(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-700">Auto-acknowledge low severity</span>
            </label>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-4">
        {showRules ? (
          /* Alert Rules Configuration */
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Alert Rules Configuration</h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {alertRules.map((rule) => (
                  <div key={rule.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <input
                          type="checkbox"
                          checked={rule.enabled}
                          onChange={(e) => {
                            setAlertRules(prev => prev.map(r =>
                              r.id === rule.id ? { ...r, enabled: e.target.checked } : r
                            ));
                          }}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <p className="font-medium text-gray-900">{rule.name}</p>
                          <p className="text-sm text-gray-500">
                            {rule.metric} {rule.condition} {rule.threshold} ({rule.severity})
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={cn(
                          "px-2 py-1 text-xs font-medium rounded",
                          rule.category === 'system' ? "bg-blue-100 text-blue-800" :
                          rule.category === 'trading' ? "bg-green-100 text-green-800" :
                          rule.category === 'risk' ? "bg-red-100 text-red-800" :
                          rule.category === 'performance' ? "bg-purple-100 text-purple-800" :
                          "bg-gray-100 text-gray-800"
                        )}>
                          {rule.category}
                        </span>
                        <button className="text-gray-400 hover:text-gray-600">
                          <Settings className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6">
                <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                  Add New Rule
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Alerts List */
          <div className="space-y-4">
            {filteredAlerts.length === 0 ? (
              <div className="bg-white rounded-lg shadow p-8 text-center">
                <BellRing className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No alerts found</h3>
                <p className="text-gray-500">
                  {searchQuery || selectedSeverity !== 'all' || selectedCategory !== 'all'
                    ? 'Try adjusting your filters'
                    : 'All systems are running normally'
                  }
                </p>
              </div>
            ) : (
              filteredAlerts.map((alert) => {
                const CategoryIcon = getCategoryIcon(alert.category);
                const isExpanded = expandedAlert === alert.id;

                return (
                  <div
                    key={alert.id}
                    className={cn(
                      "bg-white rounded-lg shadow border-l-4 transition-all",
                      getSeverityColor(alert.severity),
                      alert.resolved && "opacity-60"
                    )}
                  >
                    <div className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3 flex-1">
                          <div className={cn(
                            "p-2 rounded-lg",
                            alert.severity === 'critical' ? "bg-red-100" :
                            alert.severity === 'high' ? "bg-orange-100" :
                            alert.severity === 'medium' ? "bg-yellow-100" :
                            "bg-blue-100"
                          )}>
                            <AlertTriangle className={cn(
                              "w-5 h-5",
                              alert.severity === 'critical' ? "text-red-600" :
                              alert.severity === 'high' ? "text-orange-600" :
                              alert.severity === 'medium' ? "text-yellow-600" :
                              "text-blue-600"
                            )} />
                          </div>

                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <h3 className="text-lg font-medium text-gray-900">{alert.title}</h3>
                              {!alert.acknowledged && (
                                <span className="bg-red-100 text-red-800 px-2 py-1 text-xs font-medium rounded">
                                  New
                                </span>
                              )}
                              {alert.resolved && (
                                <span className="bg-green-100 text-green-800 px-2 py-1 text-xs font-medium rounded">
                                  Resolved
                                </span>
                              )}
                            </div>

                            <p className="text-gray-700 mb-2">{alert.message}</p>

                            <div className="flex items-center space-x-4 text-sm text-gray-500">
                              <div className="flex items-center space-x-1">
                                <CategoryIcon className="w-4 h-4" />
                                <span className="capitalize">{alert.category}</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <Clock className="w-4 h-4" />
                                <span>{new Date(alert.timestamp).toLocaleString()}</span>
                              </div>
                              <div>
                                <span className="capitalize">{alert.component}</span>
                              </div>
                            </div>

                            {alert.actions && alert.actions.length > 0 && (
                              <div className="mt-4 flex flex-wrap gap-2">
                                {alert.actions.map((action) => (
                                  <button
                                    key={action.id}
                                    onClick={action.handler}
                                    className={cn(
                                      "px-3 py-1 text-sm font-medium rounded transition-colors",
                                      action.type === 'primary' ? "bg-blue-600 text-white hover:bg-blue-700" :
                                      action.type === 'secondary' ? "bg-gray-200 text-gray-700 hover:bg-gray-300" :
                                      "bg-red-600 text-white hover:bg-red-700"
                                    )}
                                  >
                                    {action.label}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 ml-4">
                          {alert.details && (
                            <button
                              onClick={() => setExpandedAlert(isExpanded ? null : alert.id)}
                              className="p-2 text-gray-400 hover:text-gray-600"
                            >
                              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            </button>
                          )}

                          {!alert.acknowledged && (
                            <button
                              onClick={() => acknowledgeAlert(alert.id)}
                              className="p-2 text-yellow-600 hover:text-yellow-700"
                              title="Acknowledge"
                            >
                              <CheckCircle className="w-5 h-5" />
                            </button>
                          )}

                          {!alert.resolved && (
                            <button
                              onClick={() => resolveAlert(alert.id)}
                              className="p-2 text-green-600 hover:text-green-700"
                              title="Resolve"
                            >
                              <XCircle className="w-5 h-5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Expanded Details */}
                      {isExpanded && alert.details && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                              <h4 className="font-medium text-gray-900 mb-2">Current vs Threshold</h4>
                              <div className="space-y-1">
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Current Value:</span>
                                  <span className="font-medium">{alert.details.current_value}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Threshold:</span>
                                  <span className="font-medium">{alert.details.threshold_value}</span>
                                </div>
                              </div>
                            </div>

                            {alert.details.recommendations && (
                              <div>
                                <h4 className="font-medium text-gray-900 mb-2">Recommendations</h4>
                                <ul className="list-disc list-inside space-y-1">
                                  {alert.details.recommendations.map((rec, index) => (
                                    <li key={index} className="text-sm text-gray-600">{rec}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>

                          {alert.metrics && (
                            <div className="mt-4">
                              <h4 className="font-medium text-gray-900 mb-2">Metrics</h4>
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {Object.entries(alert.metrics).map(([key, value]) => (
                                  <div key={key} className="bg-gray-50 rounded p-2">
                                    <p className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                                    <p className="text-sm font-medium text-gray-900">{value}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RealTimeAlerts;