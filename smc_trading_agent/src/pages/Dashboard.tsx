import { useState, useEffect, Suspense, lazy } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  BarChart3,
  AlertTriangle
} from 'lucide-react';
import { cn } from '../utils';
import { useAuthStore } from '../stores/authStore';
import { useMarketDataStore } from '../stores/marketDataStore';
import { useUIStore } from '../stores/uiStore';
import { useRealtime } from '../hooks/useRealtime';
import { useAllTickersQuery } from '../hooks/queries/useMarketDataQueries';
import { smcSignalGenerator } from '../services/smcSignalGenerator';
import { backgroundPatternDetection } from '../services/backgroundPatternDetection';
import SEOHead, { SEOConfigs, getStructuredData } from '../components/SEOHead';

// Lazy load heavy components
const TradingViewChart = lazy(() => import('../components/charts/TradingViewChart'));
const LiveSignals = lazy(() => import('../components/realtime/LiveSignals'));
const LiveTrades = lazy(() => import('../components/realtime/LiveTrades'));
const RealtimeStatus = lazy(() => import('../components/realtime/RealtimeStatus'));

// Symbols to track
const TRACKED_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'];

const mockPositions = [
  { symbol: 'BTCUSDT', side: 'LONG', size: 0.5, entryPrice: 42800, currentPrice: 43250.50, pnl: 225.25, pnlPercent: 1.05 },
  { symbol: 'ETHUSDT', side: 'SHORT', size: 2.0, entryPrice: 2680, currentPrice: 2650.75, pnl: 58.50, pnlPercent: 1.09 },
];

export default function Dashboard() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const { user, profile } = useAuthStore();
  const { tickers, wsState, error: marketError } = useMarketDataStore();
  const binanceConnected = wsState.isConnected;
  const { addToast } = useUIStore();
  const { trades, signals, isConnected, marketDataConnected } = useRealtime();
  const { data: allTickersData, isLoading: tickersLoading } = useAllTickersQuery();
  const [systemStarted, setSystemStarted] = useState(false);
  const [patternDetectionActive, setPatternDetectionActive] = useState(false);

  // System health based on real connection status
  const systemHealth = [
    { 
      name: 'Supabase Realtime', 
      status: isConnected ? 'healthy' : 'error', 
      latency: isConnected ? '12ms' : 'N/A' 
    },
    { 
      name: 'Binance Market Data', 
      status: binanceConnected ? 'healthy' : 'error', 
      latency: binanceConnected ? '8ms' : 'N/A' 
    },
    { 
      name: 'SMC Signal Generator', 
      status: systemStarted ? 'healthy' : 'warning', 
      latency: systemStarted ? '15ms' : 'N/A' 
    },
    { 
      name: 'Pattern Detection', 
      status: patternDetectionActive ? 'healthy' : 'warning', 
      latency: patternDetectionActive ? '20ms' : 'N/A' 
    },
    { 
      name: 'Database Connection', 
      status: marketDataConnected ? 'healthy' : 'warning', 
      latency: marketDataConnected ? '5ms' : 'N/A' 
    },
  ];

  useEffect(() => {
    const timer = setInterval(() => { setCurrentTime(new Date()); }, 1000);
    return () => { clearInterval(timer); };
  }, []);

  // Start SMC signal generator when user is authenticated
  useEffect(() => {
    const initializeSystem = async () => {
      if (user && !systemStarted) {
        try {
          console.log('Starting SMC Signal Generator...');
          smcSignalGenerator.start();
          
          console.log('Starting background pattern detection...');
          await backgroundPatternDetection.start();
          setPatternDetectionActive(true);
          
          setSystemStarted(true);
          addToast({
            type: 'success',
            title: 'System Started',
            message: 'Trading system initialized successfully'
          });
          console.log('Trading system initialized successfully');
        } catch (error) {
          console.error('Failed to initialize trading system:', error);
          addToast({
            type: 'error',
            title: 'System Error',
            message: 'Failed to initialize trading system'
          });
        }
      }
    };
    
    initializeSystem();
    
    return () => {
      if (systemStarted) {
        smcSignalGenerator.stop();
      }
      if (patternDetectionActive) {
        backgroundPatternDetection.stop();
      }
    };
  }, [user, systemStarted, patternDetectionActive]);

  // Get real market data for tracked symbols
  const getMarketDataForSymbol = (symbol: string) => {
    // Try from Zustand store first
    const storeData = tickers[symbol];
    if (storeData) {
      return {
        symbol,
        price: parseFloat(storeData.price),
        change: parseFloat(storeData.priceChangePercent),
        volume: storeData.volume
      };
    }
    
    // Fallback to TanStack Query data
    const queryData = allTickersData?.find(t => t.symbol === symbol);
    if (queryData) {
      return {
        symbol,
        price: parseFloat(queryData.price),
        change: parseFloat(queryData.priceChangePercent),
        volume: queryData.volume
      };
    }
    
    return null;
  };

  const realMarketData = TRACKED_SYMBOLS.map(symbol => getMarketDataForSymbol(symbol)).filter(Boolean);

  // Calculate real P&L from live trades if available, otherwise use mock data
  const realTrades = trades.filter(trade => trade.status === 'filled');
  const totalPnL = realTrades.length > 0 
    ? realTrades.reduce((sum, trade) => {
        // Simple P&L calculation - in real app this would be more complex
        const pnl = trade.side === 'buy' ? (trade.price * trade.quantity * 0.01) : (trade.price * trade.quantity * -0.01);
        return sum + pnl;
      }, 0)
    : mockPositions.reduce((sum, pos) => sum + pos.pnl, 0);

  return (
    <>
      <SEOHead 
        title="Trading Dashboard - SMC Trading Agent"
        description="Real-time trading dashboard with market data, performance metrics, and live signals for cryptocurrency trading."
        keywords="trading dashboard, cryptocurrency, market data, trading signals, portfolio"
      />
      <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trading Dashboard</h1>
          <p className="text-gray-600">
            Witaj {profile?.full_name || user?.email || 'Trader'}! Real-time market overview and performance metrics
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <Suspense fallback={
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <div className="animate-pulse h-4 w-4 bg-gray-300 rounded"></div>
              <span>Loading status...</span>
            </div>
          }>
            <RealtimeStatus />
          </Suspense>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <Clock className="h-4 w-4" />
            <span>{currentTime.toLocaleTimeString()}</span>
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <DollarSign className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Total P&L</dt>
                <dd className={cn(
                  "text-lg font-medium",
                  totalPnL >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  ${totalPnL.toFixed(2)}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <TrendingUp className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Sharpe Ratio</dt>
                <dd className="text-lg font-medium text-gray-900">1.67</dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <TrendingDown className="h-8 w-8 text-red-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Max Drawdown</dt>
                <dd className="text-lg font-medium text-gray-900">-3.2%</dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Activity className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">Aktywne sygnały</dt>
                <dd className="text-lg font-medium text-gray-900">{signals.length}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Data Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Signals */}
        <Suspense fallback={
          <div className="bg-white rounded-lg shadow p-6">
            <div className="animate-pulse">
              <div className="h-6 bg-gray-300 rounded mb-4"></div>
              <div className="space-y-3">
                <div className="h-4 bg-gray-300 rounded"></div>
                <div className="h-4 bg-gray-300 rounded"></div>
                <div className="h-4 bg-gray-300 rounded"></div>
              </div>
            </div>
          </div>
        }>
          <LiveSignals className="" maxSignals={10} />
        </Suspense>
        
        {/* Live Trades */}
        <Suspense fallback={
          <div className="bg-white rounded-lg shadow p-6">
            <div className="animate-pulse">
              <div className="h-6 bg-gray-300 rounded mb-4"></div>
              <div className="space-y-3">
                <div className="h-4 bg-gray-300 rounded"></div>
                <div className="h-4 bg-gray-300 rounded"></div>
                <div className="h-4 bg-gray-300 rounded"></div>
              </div>
            </div>
          </div>
        }>
          <LiveTrades className="" maxTrades={10} />
        </Suspense>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Market Overview */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Market Overview</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {tickersLoading ? (
                <div className="text-center py-4">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <p className="text-sm text-gray-500">Ładowanie danych rynkowych...</p>
                </div>
              ) : realMarketData.length > 0 ? (
                realMarketData.map((market) => (
                  <div key={market.symbol} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        <BarChart3 className="h-5 w-5 text-gray-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{market.symbol}</p>
                        <p className="text-xs text-gray-500">Vol: {parseFloat(market.volume).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        ${market.price.toLocaleString()}
                      </p>
                      <p className={cn(
                        "text-xs",
                        market.change >= 0 ? "text-green-600" : "text-red-600"
                      )}>
                        {market.change >= 0 ? '+' : ''}{market.change.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-4">
                  <p className="text-sm text-gray-500">
                    {binanceConnected ? 'Brak danych dla śledzonych symboli' : 'Brak połączenia z Binance API'}
                  </p>
                  {marketError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <div className="flex items-center">
                        <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
                        <span className="text-red-700">
                          {marketError}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Live Chart */}
        <div className="lg:col-span-2">
          <Suspense fallback={
            <div className="bg-white rounded-lg shadow p-6 h-[500px] flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading TradingView Chart...</p>
              </div>
            </div>
          }>
            <TradingViewChart 
              symbol="BTCUSDT" 
              interval="15m" 
              height={500}
              className="h-full"
            />
          </Suspense>
        </div>

        {/* Active Positions */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Active Positions</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {mockPositions.map((position, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-gray-900">{position.symbol}</span>
                      <span className={cn(
                        "px-2 py-1 text-xs font-medium rounded",
                        position.side === 'LONG' 
                          ? "bg-green-100 text-green-800" 
                          : "bg-red-100 text-red-800"
                      )}>
                        {position.side}
                      </span>
                    </div>
                    <div className={cn(
                      "text-sm font-medium",
                      position.pnl >= 0 ? "text-green-600" : "text-red-600"
                    )}>
                      ${position.pnl.toFixed(2)} ({position.pnlPercent.toFixed(2)}%)
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-xs text-gray-500">
                    <div>
                      <span className="block">Size</span>
                      <span className="text-gray-900">{position.size}</span>
                    </div>
                    <div>
                      <span className="block">Entry</span>
                      <span className="text-gray-900">${position.entryPrice.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="block">Current</span>
                      <span className="text-gray-900">${position.currentPrice.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">System Health</h3>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {systemHealth.map((service) => (
              <div key={service.name} className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  {service.status === 'healthy' ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : service.status === 'warning' ? (
                    <AlertCircle className="h-5 w-5 text-yellow-500" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {service.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {service.latency}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
    </>
  );
}