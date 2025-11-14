import React, { useState } from 'react';
import { TrendingUp, TrendingDown, Clock, Target, Filter } from 'lucide-react';
import { useRealtime } from '../../hooks/useRealtime';
import { SmcSignal } from '../../types/database.types';
import RealtimeStatus from './RealtimeStatus';

interface LiveSignalsProps {
  className?: string;
  maxSignals?: number;
  showFilters?: boolean;
}

const LiveSignals: React.FC<LiveSignalsProps> = React.memo(({
  className = '',
  maxSignals = 20,
  showFilters = true
}) => {
  const { signals, isConnected } = useRealtime();
  const [filter, setFilter] = useState<'all' | 'bullish' | 'bearish'>('all');
  const [minConfidence, setMinConfidence] = useState(0.5);

  const filteredSignals = signals
    .filter(signal => {
      if (filter === 'bullish' && signal.direction !== 'bullish') return false;
      if (filter === 'bearish' && signal.direction !== 'bearish') return false;
      if (signal.confidence < minConfidence) return false;
      return true;
    })
    .slice(0, maxSignals);

  const getSignalIcon = (direction: string) => {
    switch (direction) {
      case 'bullish':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'bearish':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return <Target className="w-4 h-4 text-gray-500" />;
    }
  };

  const getSignalColor = (direction: string) => {
    switch (direction) {
      case 'bullish':
        return 'border-l-green-500 bg-green-50';
      case 'bearish':
        return 'border-l-red-500 bg-red-50';
      default:
        return 'border-l-gray-500 bg-gray-50';
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Teraz';
    if (diffMins < 60) return `${diffMins}m temu`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h temu`;
    return date.toLocaleDateString('pl-PL');
  };

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Sygnały SMC Live</h3>
          <RealtimeStatus />
        </div>
        
        {showFilters && (
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as 'all' | 'bullish' | 'bearish')}
                className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Wszystkie</option>
                <option value="bullish">Wzrostowe</option>
                <option value="bearish">Spadkowe</option>
              </select>
            </div>
            
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Min. pewność:</span>
              <select
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value={0.3}>30%</option>
                <option value={0.5}>50%</option>
                <option value={0.7}>70%</option>
                <option value={0.8}>80%</option>
                <option value={0.9}>90%</option>
              </select>
            </div>
          </div>
        )}
      </div>
      
      <div className="max-h-96 overflow-y-auto">
        {!isConnected && (
          <div className="p-4 text-center text-gray-500">
            <div className="flex items-center justify-center space-x-2">
              <Clock className="w-5 h-5" />
              <span>Łączenie z serwerem...</span>
            </div>
          </div>
        )}
        
        {isConnected && filteredSignals.length === 0 && (
          <div className="p-4 text-center text-gray-500">
            <div className="flex items-center justify-center space-x-2">
              <Target className="w-5 h-5" />
              <span>Brak sygnałów spełniających kryteria</span>
            </div>
          </div>
        )}
        
        {filteredSignals.map((signal) => (
          <div
            key={signal.id}
            className={`border-l-4 p-4 border-b border-gray-100 last:border-b-0 ${getSignalColor(signal.direction)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                {getSignalIcon(signal.direction)}
                <span className="font-medium text-gray-900">{signal.symbol}</span>
                <span className="text-xs px-2 py-1 bg-white rounded-full border">
                  {signal.direction.toUpperCase()}
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-900">
                    {(signal.confidence * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatTime(signal.created_at)}
                  </div>
                </div>
                
                {signal.is_processed && (
                  <div className="w-2 h-2 bg-blue-500 rounded-full" title="Przetworzony" />
                )}
              </div>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <div className="text-gray-600">
                Typ: <span className="font-medium">{signal.signal_type}</span> | Kierunek: <span className="font-medium">{signal.direction}</span>
              </div>
              
              <div className="flex items-center space-x-1">
                <div className="w-full bg-gray-200 rounded-full h-1.5 w-16">
                  <div
                    className={`h-1.5 rounded-full ${
                      signal.confidence >= 0.8
                        ? 'bg-green-500'
                        : signal.confidence >= 0.6
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${signal.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {filteredSignals.length > 0 && (
        <div className="p-3 bg-gray-50 text-center">
          <span className="text-xs text-gray-500">
            Wyświetlono {filteredSignals.length} z {signals.length} sygnałów
          </span>
        </div>
      )}
    </div>
  );
});

export default LiveSignals;