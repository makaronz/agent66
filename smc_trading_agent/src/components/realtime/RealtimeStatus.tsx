import React from 'react';
import { Wifi, WifiOff, RefreshCw, AlertCircle, TrendingUp, Database } from 'lucide-react';
import { useRealtime } from '../../hooks/useRealtime';
import { useMarketData } from '../../hooks/useMarketData';

interface RealtimeStatusProps {
  className?: string;
  showDetails?: boolean;
}

const RealtimeStatus: React.FC<RealtimeStatusProps> = React.memo(({
  className = '',
  showDetails = false
}) => {
  const { isConnected, connectionError, refreshData } = useRealtime();
  const { isConnected: binanceConnected, error: binanceError, getConnectionStatus, connect: connectToBinance } = useMarketData();
  
  const webSocketConnected = binanceConnected;

  const handleRefresh = async () => {
    await refreshData();
  };

  if (showDetails) {
    return (
      <div className={`bg-white rounded-lg shadow p-4 ${className}`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">Status połączenia</h3>
          <div className="flex space-x-1">
            <button
              onClick={handleRefresh}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
              title="Odśwież dane Supabase"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={connectToBinance}
              disabled={binanceConnected}
              className={`p-1 transition-colors ${
                binanceConnected 
                  ? 'text-gray-300 cursor-not-allowed' 
                  : 'text-gray-400 hover:text-gray-600'
              }`}
              title="Połącz z Binance WebSocket"
            >
              <Wifi className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="space-y-3">
          {/* Supabase Connection */}
          <div className="flex items-center space-x-2">
            <Database className="w-4 h-4" />
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-sm text-green-700">Supabase: Połączono</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-500" />
                <span className="text-sm text-red-700">Supabase: Rozłączono</span>
              </>
            )}
          </div>
          
          {/* Binance WebSocket Connection */}
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4" />
            {webSocketConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-sm text-green-700">Binance WebSocket: Połączono</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-500" />
                <span className="text-sm text-red-700">Binance WebSocket: Rozłączono</span>
              </>
            )}
          </div>
          
          {/* WebSocket Details */}
          {showDetails && (() => {
            const status = getConnectionStatus();
            const statusEntries = Object.entries(status);
            return statusEntries.length > 0 ? (
              <div className="ml-6 space-y-1">
                {statusEntries.map(([key, statusValue]) => (
                  <div key={key} className="flex items-center space-x-2 text-xs">
                    <div className={`w-2 h-2 rounded-full ${
                      statusValue === 'connected' ? 'bg-green-500' : 
                      statusValue === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'
                    }`} />
                    <span className="text-gray-600">{key}: {String(statusValue)}</span>
                  </div>
                ))}
              </div>
            ) : null;
          })()}
          
          {/* Overall Status */}
          <div className="flex items-center space-x-2 pt-2 border-t border-gray-200">
            {isConnected && webSocketConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium text-green-700">System: Online</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-500" />
                <span className="text-sm font-medium text-red-700">System: Offline</span>
              </>
            )}
          </div>
          
          {/* Error Messages */}
          {connectionError && (
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-amber-700">Supabase: {connectionError}</span>
            </div>
          )}
          
          {binanceError && (
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-amber-700">Binance: {binanceError}</span>
            </div>
          )}
          
          <div className="text-xs text-gray-500">
            Real-time dane rynkowe, transakcje i sygnały SMC
          </div>
        </div>
      </div>
    );
  }

  // Compact version
  const isFullyConnected = isConnected && webSocketConnected;
  const hasErrors = connectionError || binanceError;
  
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {isFullyConnected ? (
        <div className="flex items-center space-x-1 text-green-600">
          <Wifi className="w-4 h-4" />
          <span className="text-xs font-medium">Live</span>
        </div>
      ) : (
        <div className="flex items-center space-x-1 text-red-600">
          <WifiOff className="w-4 h-4" />
          <span className="text-xs font-medium">Offline</span>
        </div>
      )}
      
      {hasErrors && (
        <AlertCircle className="w-4 h-4 text-amber-500" />
      )}
      
      <button
        onClick={handleRefresh}
        className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
        title="Odśwież połączenie"
      >
        <RefreshCw className="w-3 h-3" />
      </button>
    </div>
  );
});

export default RealtimeStatus;