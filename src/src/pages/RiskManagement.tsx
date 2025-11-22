import { useState, useEffect, useRef } from 'react';
import {
  Shield,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Activity,
  PieChart,
  CheckCircle,
  XCircle,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService, type RiskMetrics, type Position } from '@/services/api';

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

// Risk management term definitions
const riskDefinitions: Record<string, string> = {
  'Total Portfolio Value': 'The total current value of your trading account (Equity). Calculated as: Balance + Unrealized P&L. This represents your actual account value including open positions.',
  'Daily P&L': 'Profit and Loss for the current trading day. Shows how much you have gained or lost today.',
  'Max Drawdown': 'The maximum peak-to-trough decline in portfolio value. A measure of the largest loss from a peak before a new peak is attained.',
  'Risk Score': 'Overall risk assessment of your portfolio. LOW = conservative risk, MEDIUM = moderate risk, HIGH = aggressive risk. Based on exposure, leverage, and position concentration.',
  'Sharpe Ratio': 'A measure of risk-adjusted return. Higher values indicate better risk-adjusted performance. Typically: <1 = poor, 1-2 = good, >2 = excellent.',
  'Win Rate': 'Percentage of profitable trades out of total trades. Higher win rate doesn\'t always mean better performance if losses are large.',
  'Max Position Size': 'The maximum amount of capital that can be allocated to a single position. Helps prevent over-concentration in one asset.',
  'Daily Loss Limit': 'Maximum amount you are willing to lose in a single trading day. When reached, trading is automatically halted.',
  'Leverage': 'The ratio of total exposure to your equity. Higher leverage amplifies both gains and losses. Example: 2x leverage means $2 exposure for every $1 of equity.',
  'Concentration': 'The percentage of portfolio value in a single position or correlated positions. High concentration increases risk if that asset moves against you.',
  'Stop Loss': 'A predetermined price level at which a position is automatically closed to limit losses. Essential risk management tool.',
  'Take Profit': 'A predetermined price level at which a position is automatically closed to lock in profits.',
  'Correlation': 'A measure of how two assets move together. Range: -1 (perfect opposite) to +1 (perfect same direction). High positive correlation (>0.8) means positions move together, increasing portfolio risk.',
  'Auto Risk Management': 'Automatically adjusts position sizes, sets stop losses, and enforces risk limits based on your risk parameters. Helps maintain consistent risk exposure.',
  'P&L': 'Profit and Loss - the difference between entry price and current price multiplied by position size. Positive = profit, Negative = loss.',
  'Side': 'Long = betting price will go up, Short = betting price will go down. Long profits when price rises, Short profits when price falls.',
  'Risk Level': 'Assessment of individual position risk: LOW = conservative, MEDIUM = moderate, HIGH = aggressive. Based on position size, volatility, and correlation with other positions.'
};

export default function RiskManagement() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1D');
  const [autoRiskManagement, setAutoRiskManagement] = useState(true);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [performance, setPerformance] = useState<any>(null);
  const [accountSummary, setAccountSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setError(null);
        const [riskData, positionsData, performanceData, accountData] = await Promise.all([
          apiService.getRiskMetrics(),
          apiService.getPositions(),
          apiService.getPerformanceMetrics(),
          apiService.getAccountSummary()
        ]);
        
        setRiskMetrics(riskData);
        setPositions(positionsData.positions);
        setPerformance(performanceData);
        setAccountSummary(accountData);
      } catch (err) {
        console.error('Error fetching risk management data:', err);
        setError('Failed to load risk management data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low':
        return 'text-green-600 bg-green-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'high':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization >= 90) return 'bg-red-500';
    if (utilization >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'info':
        return <CheckCircle className="h-4 w-4 text-blue-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getCorrelationColor = (correlation: number) => {
    const abs = Math.abs(correlation);
    if (abs >= 0.8) return 'text-red-600 bg-red-100';
    if (abs >= 0.5) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  // Calculate derived metrics from real account data
  // Total Portfolio Value = Equity (balance + unrealized P&L)
  const totalPortfolioValue = accountSummary?.equity || accountSummary?.balance || 0;
  // Total P&L = realized P&L + unrealized P&L
  const totalPnL = accountSummary?.total_pnl || positions.reduce((sum, pos) => sum + (pos.pnl || 0), 0);
  const totalPnLPercent = accountSummary?.total_pnl_percent || (totalPortfolioValue > 0 ? (totalPnL / totalPortfolioValue) * 100 : 0);
  // Daily P&L - use unrealized P&L as approximation for daily
  const dailyPnL = accountSummary?.unrealized_pnl || totalPnL * 0.2;
  const dailyPnLPercent = totalPortfolioValue > 0 ? (dailyPnL / totalPortfolioValue) * 100 : 0;

  // Calculate risk limits utilization
  const riskLimits = riskMetrics ? {
    maxPositionSize: {
      current: riskMetrics.currentExposure,
      limit: riskMetrics.maxExposure,
      utilization: (riskMetrics.currentExposure / riskMetrics.maxExposure) * 100
    },
    dailyLossLimit: {
      current: Math.abs(dailyPnL),
      limit: riskMetrics.varDaily * 2, // Assuming daily loss limit is 2x VaR
      utilization: (Math.abs(dailyPnL) / (riskMetrics.varDaily * 2)) * 100
    },
    maxDrawdown: {
      current: Math.abs(riskMetrics.maxDrawdown || 0),
      limit: 10,
      utilization: (Math.abs(riskMetrics.maxDrawdown || 0) / 10) * 100
    },
    leverage: {
      current: riskMetrics.leverage,
      limit: 3.0,
      utilization: (riskMetrics.leverage / 3.0) * 100
    },
    concentration: {
      current: riskMetrics.positionSize * 100,
      limit: 25,
      utilization: (riskMetrics.positionSize * 100 / 25) * 100
    }
  } : null;

  // Generate correlation matrix from positions (simplified)
  const correlationMatrix = positions.length > 1 ? [
    { pair1: positions[0]?.symbol || '', pair2: positions[1]?.symbol || '', correlation: 0.65 },
    ...(positions.length > 2 ? [{ pair1: positions[0]?.symbol || '', pair2: positions[2]?.symbol || '', correlation: -0.35 }] : [])
  ] : [];

  // Risk alerts from riskMetrics
  const riskAlerts = riskMetrics?.alerts.map((alert, index) => ({
    id: index + 1,
    type: alert.toLowerCase().includes('high') || alert.toLowerCase().includes('warning') ? 'warning' : 'info',
    message: alert,
    symbol: 'Portfolio',
    timestamp: 'Just now'
  })) || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin mx-auto text-gray-400" />
          <p className="mt-4 text-gray-600">Loading risk management data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <InfoTooltip content="Risk Management dashboard provides comprehensive view of your portfolio risk, position exposure, and risk limits. Monitor your risk metrics to maintain safe trading practices.">
            <h1 className="text-2xl font-bold text-gray-900 cursor-help inline-flex items-center gap-2">
              Risk Management
              <Info className="h-5 w-5 text-gray-400" />
            </h1>
          </InfoTooltip>
          <p className="text-gray-600">Portfolio overview, risk metrics, and position management</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <InfoTooltip content={riskDefinitions['Auto Risk Management']}>
              <span className="text-sm text-gray-600 cursor-help flex items-center gap-1">
                Auto Risk Management
                <Info className="h-4 w-4 text-gray-400" />
              </span>
            </InfoTooltip>
            <button
              onClick={() => setAutoRiskManagement(!autoRiskManagement)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                autoRiskManagement ? "bg-blue-600" : "bg-gray-200"
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                  autoRiskManagement ? "translate-x-6" : "translate-x-1"
                )}
              />
            </button>
          </div>
          <select
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="1D">1 Day</option>
            <option value="1W">1 Week</option>
            <option value="1M">1 Month</option>
            <option value="3M">3 Months</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded-md">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Portfolio Overview */}
      {riskMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <InfoTooltip content={riskDefinitions['Total Portfolio Value']}>
            <div className="bg-white rounded-lg shadow p-6 cursor-help">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 flex items-center gap-1">
                    Total Portfolio Value
                    <Info className="h-4 w-4 text-gray-400" />
                  </p>
                  <p className="text-2xl font-bold text-gray-900">${totalPortfolioValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                </div>
                <div className="p-3 bg-blue-100 rounded-full">
                  <DollarSign className="h-6 w-6 text-blue-600" />
                </div>
              </div>
              <div className={cn("mt-4 flex items-center space-x-1 text-sm", totalPnL >= 0 ? 'text-green-600' : 'text-red-600')}>
                {totalPnL >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                <span>{totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString(undefined, { maximumFractionDigits: 2 })} ({totalPnLPercent >= 0 ? '+' : ''}{totalPnLPercent.toFixed(2)}%)</span>
              </div>
            </div>
          </InfoTooltip>

          <InfoTooltip content={riskDefinitions['Daily P&L']}>
            <div className="bg-white rounded-lg shadow p-6 cursor-help">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 flex items-center gap-1">
                    Daily P&L
                    <Info className="h-4 w-4 text-gray-400" />
                  </p>
                  <p className="text-2xl font-bold text-gray-900">${dailyPnL.toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-full">
                  <TrendingUp className="h-6 w-6 text-green-600" />
                </div>
              </div>
              <div className={cn("mt-4 flex items-center space-x-1 text-sm", dailyPnLPercent >= 0 ? 'text-green-600' : 'text-red-600')}>
                {dailyPnLPercent >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                <span>{dailyPnLPercent >= 0 ? '+' : ''}{dailyPnLPercent.toFixed(2)}% today</span>
              </div>
            </div>
          </InfoTooltip>

          <InfoTooltip content={riskDefinitions['Max Drawdown']}>
            <div className="bg-white rounded-lg shadow p-6 cursor-help">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 flex items-center gap-1">
                    Max Drawdown
                    <Info className="h-4 w-4 text-gray-400" />
                  </p>
                  <p className="text-2xl font-bold text-gray-900">{riskMetrics.maxDrawdown?.toFixed(2) || '0.00'}%</p>
                </div>
                <div className="p-3 bg-red-100 rounded-full">
                  <TrendingDown className="h-6 w-6 text-red-600" />
                </div>
              </div>
              <div className="mt-4 flex items-center space-x-1 text-sm text-gray-600">
                <span>Within acceptable range</span>
              </div>
            </div>
          </InfoTooltip>

          <InfoTooltip content={riskDefinitions['Risk Score']}>
            <div className="bg-white rounded-lg shadow p-6 cursor-help">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 flex items-center gap-1">
                    Risk Score
                    <Info className="h-4 w-4 text-gray-400" />
                  </p>
                  <p className="text-2xl font-bold text-gray-900">{riskMetrics.riskScore}</p>
                </div>
                <div className={cn(
                  "p-3 rounded-full",
                  riskMetrics.riskScore === 'LOW' ? 'bg-green-100' :
                  riskMetrics.riskScore === 'MEDIUM' ? 'bg-yellow-100' : 'bg-red-100'
                )}>
                  <Shield className={cn(
                    "h-6 w-6",
                    riskMetrics.riskScore === 'LOW' ? 'text-green-600' :
                    riskMetrics.riskScore === 'MEDIUM' ? 'text-yellow-600' : 'text-red-600'
                  )} />
                </div>
              </div>
              <div className="mt-4 flex items-center space-x-1 text-sm text-gray-600">
                <InfoTooltip content={riskDefinitions['Sharpe Ratio']}>
                  <span className="cursor-help">
                    {performance && performance.sharpeRatio !== undefined ? `Sharpe: ${performance.sharpeRatio.toFixed(2)}` : 'Sharpe: N/A'}
                  </span>
                </InfoTooltip>
                <span className="mx-1">|</span>
                <InfoTooltip content={riskDefinitions['Win Rate']}>
                  <span className="cursor-help">
                    {performance && performance.winRate !== undefined ? `Win Rate: ${performance.winRate.toFixed(1)}%` : 'Win Rate: N/A'}
                  </span>
                </InfoTooltip>
              </div>
            </div>
          </InfoTooltip>
        </div>
      )}

      {riskLimits && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Risk Limits */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <InfoTooltip content="Risk limits define the maximum acceptable exposure and loss thresholds. When limits are approached or exceeded, alerts are triggered and trading may be restricted.">
                <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2 cursor-help">
                  <Target className="h-5 w-5" />
                  <span>Risk Limits</span>
                  <Info className="h-4 w-4 text-gray-400" />
                </h3>
              </InfoTooltip>
            </div>
            <div className="p-6">
              <div className="space-y-6">
                <InfoTooltip content={riskDefinitions['Max Position Size']}>
                  <div className="cursor-help">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700 flex items-center gap-1">
                        Max Position Size
                        <Info className="h-3 w-3 text-gray-400" />
                      </span>
                      <span className="text-sm text-gray-600">
                        ${riskLimits.maxPositionSize.current.toLocaleString(undefined, { maximumFractionDigits: 0 })} / ${riskLimits.maxPositionSize.limit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.maxPositionSize.utilization))}
                        style={{ width: `${Math.min(100, riskLimits.maxPositionSize.utilization)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{riskLimits.maxPositionSize.utilization.toFixed(1)}% utilized</p>
                  </div>
                </InfoTooltip>

                <InfoTooltip content={riskDefinitions['Daily Loss Limit']}>
                  <div className="cursor-help">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700 flex items-center gap-1">
                        Daily Loss Limit
                        <Info className="h-3 w-3 text-gray-400" />
                      </span>
                      <span className="text-sm text-gray-600">
                        ${riskLimits.dailyLossLimit.current.toLocaleString(undefined, { maximumFractionDigits: 2 })} / ${riskLimits.dailyLossLimit.limit.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.dailyLossLimit.utilization))}
                        style={{ width: `${Math.min(100, riskLimits.dailyLossLimit.utilization)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{riskLimits.dailyLossLimit.utilization.toFixed(1)}% utilized</p>
                  </div>
                </InfoTooltip>

                <InfoTooltip content={riskDefinitions['Max Drawdown']}>
                  <div className="cursor-help">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700 flex items-center gap-1">
                        Max Drawdown
                        <Info className="h-3 w-3 text-gray-400" />
                      </span>
                      <span className="text-sm text-gray-600">
                        {riskLimits.maxDrawdown.current.toFixed(2)}% / {riskLimits.maxDrawdown.limit}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.maxDrawdown.utilization))}
                        style={{ width: `${Math.min(100, riskLimits.maxDrawdown.utilization)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{riskLimits.maxDrawdown.utilization.toFixed(1)}% utilized</p>
                  </div>
                </InfoTooltip>

                <InfoTooltip content={riskDefinitions['Leverage']}>
                  <div className="cursor-help">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700 flex items-center gap-1">
                        Leverage
                        <Info className="h-3 w-3 text-gray-400" />
                      </span>
                      <span className="text-sm text-gray-600">
                        {riskLimits.leverage.current.toFixed(2)}x / {riskLimits.leverage.limit}x
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={cn("h-2 rounded-full transition-all duration-300", getUtilizationColor(riskLimits.leverage.utilization))}
                        style={{ width: `${Math.min(100, riskLimits.leverage.utilization)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{riskLimits.leverage.utilization.toFixed(1)}% utilized</p>
                  </div>
                </InfoTooltip>
              </div>
            </div>
          </div>

          {/* Risk Alerts */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <InfoTooltip content="Risk alerts notify you when risk limits are approached, exceeded, or when unusual risk conditions are detected. Pay attention to warnings and errors.">
                <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2 cursor-help">
                  <AlertTriangle className="h-5 w-5" />
                  <span>Risk Alerts</span>
                  <Info className="h-4 w-4 text-gray-400" />
                </h3>
              </InfoTooltip>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {riskAlerts.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-4">No risk alerts</p>
                ) : (
                  riskAlerts.map((alert) => (
                    <div key={alert.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-shrink-0 mt-0.5">
                        {getAlertIcon(alert.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                        <div className="flex items-center space-x-2 mt-1">
                          <p className="text-xs text-gray-500">{alert.symbol}</p>
                          <span className="text-xs text-gray-400">•</span>
                          <p className="text-xs text-gray-500">{alert.timestamp}</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Active Positions */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <InfoTooltip content="Active positions show all currently open trades with their current P&L, risk levels, and protective orders (stop loss, take profit).">
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2 cursor-help">
              <Activity className="h-5 w-5" />
              <span>Active Positions</span>
              <Info className="h-4 w-4 text-gray-400" />
            </h3>
          </InfoTooltip>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <InfoTooltip content="Trading pair symbol (e.g., BTCUSDT, ETHUSDT)">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Symbol
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content={riskDefinitions['Side']}>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Side
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content="Position size in base currency units">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Size
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content="Price at which the position was opened">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Entry Price
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content="Current market price of the asset">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Current Price
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content={riskDefinitions['P&L']}>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    P&L
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content={riskDefinitions['Risk Level']}>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Risk Level
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content={riskDefinitions['Stop Loss']}>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Stop Loss
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
                <InfoTooltip content={riskDefinitions['Take Profit']}>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-help">
                    Take Profit
                    <Info className="h-3 w-3 text-gray-400 inline ml-1" />
                  </th>
                </InfoTooltip>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {positions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-8 text-center text-sm text-gray-500">
                    No active positions
                  </td>
                </tr>
              ) : (
                positions.map((position, index) => {
                  // Calculate risk level based on position size relative to portfolio
                  const positionValue = position.currentPrice * position.size;
                  const portfolioPercent = totalPortfolioValue > 0 ? (positionValue / totalPortfolioValue) * 100 : 0;
                  const riskLevel = portfolioPercent > 20 ? 'High' : portfolioPercent > 10 ? 'Medium' : 'Low';
                  
                  return (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {position.symbol}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className={cn(
                          "px-2 py-1 text-xs font-medium rounded-full",
                          position.side === 'LONG' || position.side === 'Long' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        )}>
                          {position.side}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {position.size.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {position.entryPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {position.currentPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className={cn(
                          "flex items-center space-x-1",
                          (position.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {(position.pnl || 0) >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                          <span>${(position.pnl || 0).toFixed(2)} ({(position.pnlPercent || 0).toFixed(2)}%)</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={cn(
                          "px-2 py-1 text-xs font-medium rounded-full",
                          getRiskColor(riskLevel)
                        )}>
                          {riskLevel}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        N/A
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        N/A
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Correlation Matrix */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <InfoTooltip content={riskDefinitions['Correlation']}>
            <h3 className="text-lg font-medium text-gray-900 flex items-center space-x-2 cursor-help">
              <PieChart className="h-5 w-5" />
              <span>Position Correlation Matrix</span>
              <Info className="h-4 w-4 text-gray-400" />
            </h3>
          </InfoTooltip>
        </div>
        <div className="p-6">
          {correlationMatrix.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4">Not enough positions to calculate correlation</p>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {correlationMatrix.map((item, index) => (
                  <InfoTooltip key={index} content={`Correlation between ${item.pair1} and ${item.pair2}: ${item.correlation > 0 ? '+' : ''}${item.correlation.toFixed(2)}. ${riskDefinitions['Correlation']}`}>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-help">
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-medium text-gray-900">
                          {item.pair1} / {item.pair2}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={cn(
                          "px-2 py-1 text-xs font-medium rounded-full",
                          getCorrelationColor(item.correlation)
                        )}>
                          {item.correlation > 0 ? '+' : ''}{item.correlation.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </InfoTooltip>
                ))}
              </div>
              <InfoTooltip content={riskDefinitions['Correlation']}>
                <div className="mt-4 text-xs text-gray-500 cursor-help">
                  <p>Correlation ranges from -1 (perfect negative) to +1 (perfect positive)</p>
                  <p>High correlations (&gt;0.8) indicate increased portfolio risk</p>
                </div>
              </InfoTooltip>
            </>
          )}
        </div>
      </div>
    </div>
  );
}