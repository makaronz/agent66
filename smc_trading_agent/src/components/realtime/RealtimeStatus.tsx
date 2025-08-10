import React from 'react';
import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react';
import { useRealtime } from '../../hooks/useRealtime';

interface RealtimeStatusProps {
  className?: string;
  showDetails?: boolean;
}

const RealtimeStatus: React.FC<RealtimeStatusProps> = ({
  className = '',
  showDetails = false
}) => {
  const { isConnected, connectionError, refreshData } = useRealtime();

  const handleRefresh = async () => {
    await refreshData();
  };

  if (showDetails) {
    return (
      <div className={`bg-white rounded-lg shadow p-4 ${className}`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-900">Status połączenia</h3>
          <button
            onClick={handleRefresh}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            title="Odśwież połączenie"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-sm text-green-700">Połączono</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-500" />
                <span className="text-sm text-red-700">Rozłączono</span>
              </>
            )}
          </div>
          
          {connectionError && (
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-amber-700">{connectionError}</span>
            </div>
          )}
          
          <div className="text-xs text-gray-500">
            Real-time aktualizacje dla transakcji i sygnałów
          </div>
        </div>
      </div>
    );
  }

  // Compact version
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {isConnected ? (
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
      
      {connectionError && (
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
};

export default RealtimeStatus;