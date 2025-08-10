import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle, Activity, TrendingUp, Clock } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { supabase } from '../../lib/supabase';

interface ComplianceData {
  complianceLevel: 'critical' | 'low' | 'medium' | 'high';
  enabledMethods: string[];
  methodCount: number;
  recommendations: string[];
  recentActivity: Array<{
    action: string;
    method_type: string;
    success: boolean;
    created_at: string;
  }>;
  lastUpdated: string | null;
}

interface SecurityAlert {
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

interface UsageStats {
  totalAttempts: number;
  successfulAttempts: number;
  failedAttempts: number;
  methodUsage: Record<string, number>;
  dailyUsage: Record<string, number>;
}

const SecurityDashboard: React.FC = () => {
  const [compliance, setCompliance] = useState<ComplianceData | null>(null);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSecurityData();
  }, []);

  const fetchSecurityData = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Please log in to view security dashboard');
        return;
      }

      const headers = {
        'Authorization': `Bearer ${session.access_token}`
      };

      // Fetch compliance data
      const complianceResponse = await fetch('/api/security/mfa-compliance', { headers });
      if (complianceResponse.ok) {
        const complianceData = await complianceResponse.json();
        setCompliance(complianceData);
      }

      // Fetch security alerts
      const alertsResponse = await fetch('/api/security/alerts', { headers });
      if (alertsResponse.ok) {
        const alertsData = await alertsResponse.json();
        setAlerts(alertsData.alerts);
      }

      // Fetch usage statistics
      const statsResponse = await fetch('/api/security/stats', { headers });
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

    } catch (error) {
      console.error('Error fetching security data:', error);
      toast.error('Failed to load security dashboard');
    } finally {
      setLoading(false);
    }
  };

  const getComplianceColor = (level: string) => {
    switch (level) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'low': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'high': return 'text-green-600 bg-green-50 border-green-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getAlertColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Compliance Overview */}
      {compliance && (
        <div className={`rounded-lg border-2 p-6 ${getComplianceColor(compliance.complianceLevel)}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <Shield className="h-8 w-8" />
              <div>
                <h3 className="text-lg font-semibold">MFA Compliance Status</h3>
                <p className="text-sm opacity-80">
                  Security Level: {compliance.complianceLevel.charAt(0).toUpperCase() + compliance.complianceLevel.slice(1)}
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold">{compliance.methodCount}</div>
              <div className="text-sm opacity-80">Methods Enabled</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium mb-2">Enabled Methods:</h4>
              {compliance.enabledMethods.length > 0 ? (
                <ul className="text-sm space-y-1">
                  {compliance.enabledMethods.map((method, index) => (
                    <li key={index} className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4" />
                      <span>{method}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm opacity-80">No MFA methods enabled</p>
              )}
            </div>

            <div>
              <h4 className="font-medium mb-2">Recommendations:</h4>
              <ul className="text-sm space-y-1">
                {compliance.recommendations.slice(0, 3).map((rec, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <span className="text-xs mt-1">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Security Alerts */}
      {alerts.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <AlertTriangle className="h-5 w-5 mr-2" />
            Security Alerts
          </h3>
          <div className="space-y-3">
            {alerts.map((alert, index) => (
              <div key={index} className={`rounded-lg border p-4 ${getAlertColor(alert.severity)}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium">{alert.title}</h4>
                    <p className="text-sm mt-1">{alert.message}</p>
                  </div>
                  <div className="text-xs opacity-75">
                    {formatDate(alert.timestamp)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Usage Statistics */}
      {stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* MFA Usage Overview */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Activity className="h-5 w-5 mr-2" />
              MFA Usage (Last 30 Days)
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats.totalAttempts}</div>
                <div className="text-sm text-gray-600">Total Attempts</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.successfulAttempts}</div>
                <div className="text-sm text-gray-600">Successful</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{stats.failedAttempts}</div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
            </div>

            {stats.totalAttempts > 0 && (
              <div className="mt-4">
                <div className="text-sm text-gray-600 mb-2">Success Rate</div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-600 h-2 rounded-full" 
                    style={{ width: `${(stats.successfulAttempts / stats.totalAttempts) * 100}%` }}
                  ></div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {Math.round((stats.successfulAttempts / stats.totalAttempts) * 100)}% success rate
                </div>
              </div>
            )}
          </div>

          {/* Method Usage Breakdown */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <TrendingUp className="h-5 w-5 mr-2" />
              Method Usage
            </h3>
            {Object.keys(stats.methodUsage).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.methodUsage)
                  .sort(([,a], [,b]) => b - a)
                  .map(([method, count]) => (
                    <div key={method} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">{method}</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ width: `${(count / Math.max(...Object.values(stats.methodUsage))) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-600 w-8 text-right">{count}</span>
                      </div>
                    </div>
                  ))
                }
              </div>
            ) : (
              <p className="text-sm text-gray-500">No MFA usage data available</p>
            )}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {compliance?.recentActivity && compliance.recentActivity.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Clock className="h-5 w-5 mr-2" />
            Recent MFA Activity
          </h3>
          <div className="space-y-2">
            {compliance.recentActivity.slice(0, 5).map((activity, index) => (
              <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-b-0">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    activity.success ? 'bg-green-500' : 'bg-red-500'
                  }`}></div>
                  <span className="text-sm font-medium text-gray-700">
                    {activity.action.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="text-sm text-gray-500">via {activity.method_type}</span>
                </div>
                <span className="text-xs text-gray-400">
                  {formatDate(activity.created_at)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SecurityDashboard;