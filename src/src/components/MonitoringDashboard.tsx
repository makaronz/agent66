import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, BarChart3, Bell, History, Activity,
  Menu, X, Settings, LogOut, User, Shield, TrendingUp,
  AlertTriangle, CheckCircle, Clock, Zap, Moon, Sun
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Import dashboard components
import EnhancedDashboard from './EnhancedDashboard';
import BusinessIntelligence from './BusinessIntelligence';
import RealTimeAlerts from './RealTimeAlerts';
import HistoricalAnalysis from './HistoricalAnalysis';

// Types
interface NavigationItem {
  id: string;
  label: string;
  icon: React.ElementType;
  path: string;
  badge?: number;
}

interface SystemStatus {
  overall: 'healthy' | 'warning' | 'critical';
  components: {
    name: string;
    status: 'healthy' | 'warning' | 'critical';
    latency: number;
  }[];
  uptime: number;
  lastUpdate: string;
}

const MonitoringDashboard: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    overall: 'healthy',
    components: [
      { name: 'Data Pipeline', status: 'healthy', latency: 12 },
      { name: 'SMC Detector', status: 'healthy', latency: 8 },
      { name: 'Risk Manager', status: 'warning', latency: 15 },
      { name: 'Execution Engine', status: 'healthy', latency: 5 }
    ],
    uptime: 99.7,
    lastUpdate: new Date().toISOString()
  });
  const [activeAlerts, setActiveAlerts] = useState(3);

  const navigation: NavigationItem[] = [
    {
      id: 'dashboard',
      label: 'Real-Time Dashboard',
      icon: LayoutDashboard,
      path: '/',
      badge: 0
    },
    {
      id: 'analytics',
      label: 'Business Intelligence',
      icon: BarChart3,
      path: '/analytics'
    },
    {
      id: 'alerts',
      label: 'Alerts Center',
      icon: Bell,
      path: '/alerts',
      badge: activeAlerts
    },
    {
      id: 'historical',
      label: 'Historical Analysis',
      icon: History,
      path: '/historical'
    }
  ];

  // Simulate system status updates
  useEffect(() => {
    const interval = setInterval(() => {
      setSystemStatus(prev => ({
        ...prev,
        components: prev.components.map(comp => ({
          ...comp,
          latency: comp.latency + Math.random() * 4 - 2,
          status: Math.random() > 0.9 ? 'warning' : 'healthy'
        })),
        lastUpdate: new Date().toISOString()
      }));

      // Simulate alert count changes
      setActiveAlerts(Math.floor(Math.random() * 8));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4" />;
      case 'warning': return <AlertTriangle className="w-4 h-4" />;
      case 'critical': return <X className="w-4 h-4" />;
      default: return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <Router>
      <div className={cn("min-h-screen", darkMode ? "dark bg-gray-900" : "bg-gray-50")}>
        {/* Sidebar */}
        <div className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-200 ease-in-out",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">SMC Monitor</h1>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <nav className="mt-6 px-4">
            <div className="space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const location = useLocation();
                const isActive = location.pathname === item.path;

                return (
                  <Link
                    key={item.id}
                    to={item.path}
                    className={cn(
                      "group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                      isActive
                        ? "bg-blue-100 text-blue-700"
                        : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                    )}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    <span className="flex-1">{item.label}</span>
                    {item.badge > 0 && (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>

            <div className="mt-8 pt-6 border-t border-gray-200">
              <div className="space-y-1">
                <Link
                  to="/settings"
                  className="group flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100 hover:text-gray-900"
                >
                  <Settings className="mr-3 h-5 w-5" />
                  Settings
                </Link>
                <button className="w-full group flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100 hover:text-gray-900">
                  <LogOut className="mr-3 h-5 w-5" />
                  Sign Out
                </button>
              </div>
            </div>
          </nav>

          {/* System Status Panel */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
            <div className="mb-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-500">System Status</span>
                <span className={cn(
                  "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                  getStatusColor(systemStatus.overall)
                )}>
                  {getStatusIcon(systemStatus.overall)}
                  <span className="ml-1">{systemStatus.overall}</span>
                </span>
              </div>
              <div className="space-y-1">
                {systemStatus.components.map((component) => (
                  <div key={component.name} className="flex items-center justify-between">
                    <span className="text-xs text-gray-600">{component.name}</span>
                    <div className="flex items-center space-x-1">
                      <span className="text-xs text-gray-500">{component.latency.toFixed(0)}ms</span>
                      <div className={cn("w-2 h-2 rounded-full",
                        component.status === 'healthy' ? "bg-green-500" :
                        component.status === 'warning' ? "bg-yellow-500" : "bg-red-500"
                      )} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="text-xs text-gray-500">
              Uptime: {systemStatus.uptime}% | Updated: {new Date(systemStatus.lastUpdate).toLocaleTimeString()}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className={cn("transition-all duration-200", sidebarOpen ? "lg:ml-64" : "lg:ml-0")}>
          {/* Top Bar */}
          <div className="sticky top-0 z-40 bg-white shadow-sm border-b border-gray-200">
            <div className="flex items-center justify-between h-16 px-6">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <Menu className="w-6 h-6" />
                </button>

                <div className="flex items-center space-x-2">
                  <Shield className="w-5 h-5 text-blue-600" />
                  <span className="text-sm font-medium text-gray-700">SMC Trading System</span>
                  <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                    Live
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                {/* Quick Stats */}
                <div className="hidden md:flex items-center space-x-6 text-sm">
                  <div className="flex items-center space-x-2">
                    <TrendingUp className="w-4 h-4 text-green-500" />
                    <span className="text-gray-600">P&L:</span>
                    <span className="font-medium text-green-600">+$2,847.32</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Activity className="w-4 h-4 text-blue-500" />
                    <span className="text-gray-600">Positions:</span>
                    <span className="font-medium">4</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Zap className="w-4 h-4 text-yellow-500" />
                    <span className="text-gray-600">Signals:</span>
                    <span className="font-medium">12</span>
                  </div>
                </div>

                {/* User Menu */}
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => setDarkMode(!darkMode)}
                    className="p-2 text-gray-400 hover:text-gray-600"
                  >
                    {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                  </button>

                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-gray-600" />
                    </div>
                    <div className="hidden md:block">
                      <p className="text-sm font-medium text-gray-900">Trader Admin</p>
                      <p className="text-xs text-gray-500">admin@smc-trading.com</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Page Content */}
          <main className="p-6">
            <Routes>
              <Route path="/" element={<EnhancedDashboard />} />
              <Route path="/analytics" element={<BusinessIntelligence />} />
              <Route path="/alerts" element={<RealTimeAlerts />} />
              <Route path="/historical" element={<HistoricalAnalysis />} />
              <Route path="/settings" element={
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-2xl font-bold text-gray-900 mb-4">Settings</h2>
                  <p className="text-gray-600">Settings panel coming soon...</p>
                </div>
              } />
            </Routes>
          </main>
        </div>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </div>
    </Router>
  );
};

export default MonitoringDashboard;