import React, { useState } from 'react';
import { ArrowUpRight, ArrowDownRight, Clock, DollarSign, Filter, CheckCircle, XCircle, Loader } from 'lucide-react';
import { useRealtime } from '../../hooks/useRealtime';
import { Trade } from '../../types/database.types';
import RealtimeStatus from './RealtimeStatus';

interface LiveTradesProps {
  className?: string;
  maxTrades?: number;
  showFilters?: boolean;
}

const LiveTrades: React.FC<LiveTradesProps> = ({
  className = '',
  maxTrades = 15,
  showFilters = true
}) => {
  const { trades, isConnected } = useRealtime();
  const [filter, setFilter] = useState<'all' | 'buy' | 'sell'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'filled' | 'cancelled'>('all');

  const filteredTrades = trades
    .filter(trade => {
      if (filter === 'buy' && trade.side !== 'buy') return false;
      if (filter === 'sell' && trade.side !== 'sell') return false;
      if (statusFilter !== 'all' && trade.status !== statusFilter) return false;
      return true;
    })
    .slice(0, maxTrades);

  const getTradeIcon = (side: string) => {
    return side === 'buy' ? (
      <ArrowUpRight className="w-4 h-4 text-green-500" />
    ) : (
      <ArrowDownRight className="w-4 h-4 text-red-500" />
    );
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'filled':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'pending':
        return <Loader className="w-4 h-4 text-yellow-500 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'filled':
        return 'bg-green-50 border-l-green-500';
      case 'cancelled':
        return 'bg-red-50 border-l-red-500';
      case 'pending':
        return 'bg-yellow-50 border-l-yellow-500';
      default:
        return 'bg-gray-50 border-l-gray-500';
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
    return date.toLocaleDateString('pl-PL', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('pl-PL', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 8
    }).format(price);
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('pl-PL', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 6
    }).format(amount);
  };

  const calculateValue = (amount: number, price: number) => {
    return new Intl.NumberFormat('pl-PL', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount * price);
  };

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Transakcje Live</h3>
          <RealtimeStatus />
        </div>
        
        {showFilters && (
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as 'all' | 'buy' | 'sell')}
                className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Wszystkie</option>
                <option value="buy">Kupno</option>
                <option value="sell">Sprzedaż</option>
              </select>
            </div>
            
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as 'all' | 'pending' | 'filled' | 'cancelled')}
                className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">Wszystkie</option>
                <option value="pending">Oczekujące</option>
                <option value="filled">Wykonane</option>
                <option value="cancelled">Anulowane</option>
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
        
        {isConnected && filteredTrades.length === 0 && (
          <div className="p-4 text-center text-gray-500">
            <div className="flex items-center justify-center space-x-2">
              <DollarSign className="w-5 h-5" />
              <span>Brak transakcji spełniających kryteria</span>
            </div>
          </div>
        )}
        
        {filteredTrades.map((trade) => (
          <div
            key={trade.id}
            className={`border-l-4 p-4 border-b border-gray-100 last:border-b-0 ${getStatusColor(trade.status)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                {getTradeIcon(trade.side)}
                <span className="font-medium text-gray-900">{trade.symbol}</span>
                <span className={`text-xs px-2 py-1 rounded-full border ${
                  trade.side === 'buy' 
                    ? 'bg-green-100 text-green-800 border-green-200'
                    : 'bg-red-100 text-red-800 border-red-200'
                }`}>
                  {trade.side.toUpperCase()}
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                {getStatusIcon(trade.status)}
                <div className="text-right">
                  <div className="text-xs text-gray-500">
                    {formatTime(trade.timestamp)}
                  </div>
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600">Ilość</div>
                <div className="font-medium">{formatAmount(trade.quantity)}</div>
              </div>
              
              <div>
                <div className="text-gray-600">Cena</div>
                <div className="font-medium">${formatPrice(trade.price)}</div>
              </div>
            </div>
            
            <div className="mt-2 pt-2 border-t border-gray-100">
              <div className="flex items-center justify-between text-sm">
                <div className="text-gray-600">Wartość całkowita</div>
                <div className="font-medium text-gray-900">
                  {calculateValue(trade.quantity, trade.price)}
                </div>
              </div>
              
              <div className="flex items-center justify-between text-xs text-gray-500 mt-1">
                <div>Status: {trade.status}</div>
                <div>ID: {trade.id.slice(0, 8)}...</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {filteredTrades.length > 0 && (
        <div className="p-3 bg-gray-50 text-center">
          <span className="text-xs text-gray-500">
            Wyświetlono {filteredTrades.length} z {trades.length} transakcji
          </span>
        </div>
      )}
    </div>
  );
};

export default LiveTrades;