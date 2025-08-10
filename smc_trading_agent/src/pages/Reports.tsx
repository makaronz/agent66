import { useState } from 'react';
import {
  FileText,
  Download,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  PieChart,
  Activity,
  Clock,
  Target,
  Award,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Mail,
  Settings
} from 'lucide-react';
import { cn } from '@/lib/utils';

const reportTypes = [
  { id: 'daily', name: 'Daily Summary', description: 'Daily trading performance and activity' },
  { id: 'weekly', name: 'Weekly Analysis', description: 'Weekly performance metrics and trends' },
  { id: 'monthly', name: 'Monthly Report', description: 'Comprehensive monthly trading report' },
  { id: 'custom', name: 'Custom Period', description: 'Generate report for specific date range' }
];

const recentReports = [
  {
    id: 1,
    name: 'Daily Summary - January 15, 2024',
    type: 'Daily',
    date: '2024-01-15',
    status: 'completed',
    size: '2.3 MB',
    trades: 45,
    pnl: 1250.75,
    winRate: 68.9
  },
  {
    id: 2,
    name: 'Weekly Analysis - Week 2, 2024',
    type: 'Weekly',
    date: '2024-01-14',
    status: 'completed',
    size: '5.7 MB',
    trades: 312,
    pnl: 8750.25,
    winRate: 72.1
  },
  {
    id: 3,
    name: 'Monthly Report - December 2023',
    type: 'Monthly',
    date: '2024-01-01',
    status: 'completed',
    size: '12.4 MB',
    trades: 1456,
    pnl: 25680.50,
    winRate: 69.8
  },
  {
    id: 4,
    name: 'Custom Analysis - Q4 2023',
    type: 'Custom',
    date: '2024-01-02',
    status: 'generating',
    size: 'N/A',
    trades: 0,
    pnl: 0,
    winRate: 0
  }
];

const performanceMetrics = {
  totalTrades: 1456,
  winningTrades: 1016,
  losingTrades: 440,
  winRate: 69.8,
  totalPnL: 25680.50,
  avgWin: 45.25,
  avgLoss: -28.75,
  profitFactor: 1.87,
  sharpeRatio: 1.65,
  maxDrawdown: -3.2,
  bestDay: 1850.25,
  worstDay: -675.50
};

const tradingPairs = [
  { symbol: 'EURUSD', trades: 245, pnl: 5680.25, winRate: 72.1, volume: 12500000 },
  { symbol: 'GBPUSD', trades: 198, pnl: 4250.75, winRate: 68.7, volume: 9800000 },
  { symbol: 'USDJPY', trades: 187, pnl: 3890.50, winRate: 71.2, volume: 11200000 },
  { symbol: 'XAUUSD', trades: 156, pnl: 6750.25, winRate: 65.4, volume: 850000 },
  { symbol: 'AUDUSD', trades: 134, pnl: 2180.75, winRate: 69.4, volume: 6700000 },
  { symbol: 'USDCAD', trades: 112, pnl: 1850.50, winRate: 67.9, volume: 5600000 }
];

const smcPatternStats = [
  { pattern: 'Order Block', trades: 287, winRate: 78.5, avgPnL: 42.50 },
  { pattern: 'Fair Value Gap', trades: 234, winRate: 82.1, avgPnL: 38.75 },
  { pattern: 'Break of Structure', trades: 198, winRate: 75.3, avgPnL: 35.25 },
  { pattern: 'Liquidity Sweep', trades: 176, winRate: 80.7, avgPnL: 45.80 },
  { pattern: 'Change of Character', trades: 145, winRate: 85.5, avgPnL: 52.30 },
  { pattern: 'Inducement', trades: 89, winRate: 77.5, avgPnL: 48.90 }
];

export default function Reports() {
  const [selectedReportType, setSelectedReportType] = useState('daily');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [generating, setGenerating] = useState(false);

  const [autoReports, setAutoReports] = useState(true);

  const handleGenerateReport = async () => {
    setGenerating(true);
    // Simulate report generation
    setTimeout(() => {
      setGenerating(false);
    }, 3000);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'generating':
        return 'text-yellow-600 bg-yellow-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      case 'generating':
        return <RefreshCw className="h-4 w-4 animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
          <p className="text-gray-600">Generate comprehensive trading reports and performance analytics</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Auto Reports</span>
            <button
              onClick={() => setAutoReports(!autoReports)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                autoReports ? "bg-blue-600" : "bg-gray-200"
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                  autoReports ? "translate-x-6" : "translate-x-1"
                )}
              />
            </button>
          </div>
          <button className="flex items-center space-x-2 px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-md transition-colors">
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Generation */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>Generate Report</span>
              </h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Report Type
                </label>
                <select
                  value={selectedReportType}
                  onChange={(e) => setSelectedReportType(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {reportTypes.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {reportTypes.find(t => t.id === selectedReportType)?.description}
                </p>
              </div>

              {selectedReportType === 'custom' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={dateRange.start}
                      onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={dateRange.end}
                      onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Include Sections
                </label>
                <div className="space-y-2">
                  {[
                    'Performance Summary',
                    'Trade Analysis',
                    'SMC Pattern Statistics',
                    'Risk Metrics',
                    'Market Analysis',
                    'Recommendations'
                  ].map((section) => (
                    <label key={section} className="flex items-center">
                      <input
                        type="checkbox"
                        defaultChecked
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">{section}</span>
                    </label>
                  ))}
                </div>
              </div>

              <button
                onClick={handleGenerateReport}
                disabled={generating}
                className={cn(
                  "w-full flex items-center justify-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors",
                  generating
                    ? "bg-gray-400 text-white cursor-not-allowed"
                    : "bg-blue-600 hover:bg-blue-700 text-white"
                )}
              >
                {generating ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <FileText className="h-4 w-4" />
                )}
                <span>{generating ? 'Generating...' : 'Generate Report'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Recent Reports */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
                <Activity className="h-5 w-5" />
                <span>Recent Reports</span>
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Report
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Trades
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      P&L
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Win Rate
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recentReports.map((report) => (
                    <tr key={report.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">{report.name}</div>
                          <div className="text-sm text-gray-500">{report.size}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={cn(
                          "inline-flex items-center space-x-1 px-2 py-1 text-xs font-medium rounded-full",
                          getStatusColor(report.status)
                        )}>
                          {getStatusIcon(report.status)}
                          <span className="capitalize">{report.status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {report.trades > 0 ? report.trades.toLocaleString() : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {report.pnl > 0 ? (
                          <div className="flex items-center space-x-1 text-green-600">
                            <TrendingUp className="h-4 w-4" />
                            <span>${report.pnl.toLocaleString()}</span>
                          </div>
                        ) : report.pnl < 0 ? (
                          <div className="flex items-center space-x-1 text-red-600">
                            <TrendingDown className="h-4 w-4" />
                            <span>-${Math.abs(report.pnl).toLocaleString()}</span>
                          </div>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {report.winRate > 0 ? `${report.winRate}%` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex items-center space-x-2">
                          {report.status === 'completed' && (
                            <>
                              <button className="text-blue-600 hover:text-blue-900">
                                <Download className="h-4 w-4" />
                              </button>
                              <button className="text-gray-600 hover:text-gray-900">
                                <Mail className="h-4 w-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Trades</p>
              <p className="text-2xl font-bold text-gray-900">{performanceMetrics.totalTrades.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <BarChart3 className="h-6 w-6 text-blue-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-green-600">
            <TrendingUp className="h-4 w-4" />
            <span>Win Rate: {performanceMetrics.winRate}%</span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total P&L</p>
              <p className="text-2xl font-bold text-gray-900">${performanceMetrics.totalPnL.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-green-100 rounded-full">
              <DollarSign className="h-6 w-6 text-green-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-green-600">
            <TrendingUp className="h-4 w-4" />
            <span>Profit Factor: {performanceMetrics.profitFactor}</span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Sharpe Ratio</p>
              <p className="text-2xl font-bold text-gray-900">{performanceMetrics.sharpeRatio}</p>
            </div>
            <div className="p-3 bg-purple-100 rounded-full">
              <Award className="h-6 w-6 text-purple-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-gray-600">
            <span>Risk-adjusted returns</span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Max Drawdown</p>
              <p className="text-2xl font-bold text-gray-900">{performanceMetrics.maxDrawdown}%</p>
            </div>
            <div className="p-3 bg-red-100 rounded-full">
              <TrendingDown className="h-6 w-6 text-red-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center space-x-1 text-sm text-gray-600">
            <span>Within acceptable range</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trading Pairs Performance */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
              <PieChart className="h-5 w-5" />
              <span>Trading Pairs Performance</span>
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {tradingPairs.map((pair, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="font-medium text-gray-900">{pair.symbol}</div>
                    <div className="text-sm text-gray-600">{pair.trades} trades</div>
                  </div>
                  <div className="text-right">
                    <div className={cn(
                      "flex items-center space-x-1 text-sm font-medium",
                      pair.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      {pair.pnl >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                      <span>${pair.pnl.toLocaleString()}</span>
                    </div>
                    <div className="text-xs text-gray-500">Win Rate: {pair.winRate}%</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* SMC Pattern Statistics */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2">
              <Target className="h-5 w-5" />
              <span>SMC Pattern Statistics</span>
            </h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {smcPatternStats.map((pattern, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="font-medium text-gray-900">{pattern.pattern}</div>
                    <div className="text-sm text-gray-600">{pattern.trades} trades</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-green-600">
                      Win Rate: {pattern.winRate}%
                    </div>
                    <div className="text-xs text-gray-500">
                      Avg P&L: ${pattern.avgPnL}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}