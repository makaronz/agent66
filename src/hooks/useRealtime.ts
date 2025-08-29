import { useState, useEffect, useCallback } from 'react';
import { RealtimeChannel } from '@supabase/supabase-js';
import { realtime } from '../supabase';
import { useAuthStore } from '../stores/authStore';
import { useMarketDataStore } from '../stores/marketDataStore';
import { useUIStore } from '../stores/uiStore';
import { Trade, SmcSignal, TradingSession } from '../types/database.types';

interface RealtimeState {
  trades: Trade[];
  signals: SmcSignal[];
  sessions: TradingSession[];
  isConnected: boolean;
  connectionError: string | null;
  marketDataConnected: boolean;
}

interface RealtimeActions {
  subscribeTo: (table: 'trades' | 'smc_signals' | 'trading_sessions') => void;
  unsubscribeFrom: (table: 'trades' | 'smc_signals' | 'trading_sessions') => void;
  unsubscribeAll: () => void;
  refreshData: () => Promise<void>;
}

export const useRealtime = (): RealtimeState & RealtimeActions => {
  const user = useAuthStore(state => state.user);
  const { wsState: { isConnected: marketDataConnected }, error: marketDataError } = useMarketDataStore();
  const { addToast } = useUIStore();
  
  const [state, setState] = useState<RealtimeState>({
    trades: [],
    signals: [],
    sessions: [],
    isConnected: false,
    connectionError: null,
    marketDataConnected: false
  });
  
  const [channels, setChannels] = useState<Map<string, RealtimeChannel>>(new Map());

  // Handle trade updates
  const handleTradeUpdate = useCallback((payload: any) => {
    const { eventType, new: newRecord, old: oldRecord } = payload;
    
    setState(prev => {
      let updatedTrades = [...prev.trades];
      
      switch (eventType) {
        case 'INSERT':
          updatedTrades.push(newRecord as Trade);
          addToast({ type: 'success', title: 'Nowa transakcja', message: `${newRecord.symbol} ${newRecord.side}` });
          break;
        case 'UPDATE':
          const updateIndex = updatedTrades.findIndex(t => t.id === newRecord.id);
          if (updateIndex !== -1) {
            updatedTrades[updateIndex] = newRecord as Trade;
            if (newRecord.status === 'filled') {
              addToast({ type: 'success', title: 'Transakcja wykonana', message: newRecord.symbol });
            } else if (newRecord.status === 'cancelled') {
              addToast({ type: 'info', title: 'Transakcja anulowana', message: newRecord.symbol });
            }
          }
          break;
        case 'DELETE':
          updatedTrades = updatedTrades.filter(t => t.id !== oldRecord.id);
          break;
      }
      
      return { ...prev, trades: updatedTrades };
    });
  }, []);

  // Handle signal updates
  const handleSignalUpdate = useCallback((payload: any) => {
    const { eventType, new: newRecord, old: oldRecord } = payload;
    
    setState(prev => {
      let updatedSignals = [...prev.signals];
      
      switch (eventType) {
        case 'INSERT':
          updatedSignals.unshift(newRecord as SmcSignal); // Add to beginning
          // Keep only last 100 signals
          if (updatedSignals.length > 100) {
            updatedSignals = updatedSignals.slice(0, 100);
          }
          
          // Show notification for high confidence signals
          if (newRecord.confidence >= 0.8) {
            addToast({ 
              type: 'success',
              title: 'Połączenie',
              message: `Nowy sygnał SMC: ${newRecord.symbol} (${(newRecord.confidence * 100).toFixed(0)}%)`,
              duration: 6000
            });
          }
          break;
        case 'UPDATE':
          const updateIndex = updatedSignals.findIndex(s => s.id === newRecord.id);
          if (updateIndex !== -1) {
            updatedSignals[updateIndex] = newRecord as SmcSignal;
            if (newRecord.processed && !oldRecord.processed) {
              addToast({ type: 'info', title: 'Sygnał przetworzony', message: newRecord.symbol });
            }
          }
          break;
        case 'DELETE':
          updatedSignals = updatedSignals.filter(s => s.id !== oldRecord.id);
          break;
      }
      
      return { ...prev, signals: updatedSignals };
    });
  }, []);

  // Handle session updates
  const handleSessionUpdate = useCallback((payload: any) => {
    const { eventType, new: newRecord, old: oldRecord } = payload;
    
    setState(prev => {
      let updatedSessions = [...prev.sessions];
      
      switch (eventType) {
        case 'INSERT':
          updatedSessions.push(newRecord as TradingSession);
          addToast({ type: 'success', title: 'Sesja rozpoczęta', message: 'Nowa sesja tradingowa rozpoczęta' });
          break;
        case 'UPDATE':
          const updateIndex = updatedSessions.findIndex(s => s.id === newRecord.id);
          if (updateIndex !== -1) {
            updatedSessions[updateIndex] = newRecord as TradingSession;
            if (newRecord.status === 'completed' && oldRecord.status === 'active') {
              addToast({ type: 'info', title: 'Sesja zakończona', message: 'Sesja tradingowa zakończona' });
            }
          }
          break;
        case 'DELETE':
          updatedSessions = updatedSessions.filter(s => s.id !== oldRecord.id);
          break;
      }
      
      return { ...prev, sessions: updatedSessions };
    });
  }, []);

  // Subscribe to a specific table
  const subscribeTo = useCallback((table: 'trades' | 'smc_signals' | 'trading_sessions') => {
    if (!user) return;
    
    const channelName = `${table}_${user.id}`;
    
    // Don't subscribe if already subscribed
    if (channels.has(channelName)) return;
    
    let channel: RealtimeChannel;
    
    try {
      if (table === 'trades') {
        channel = realtime.subscribeTrades(user.id, handleTradeUpdate);
      } else if (table === 'smc_signals') {
        channel = realtime.subscribeSignals(handleSignalUpdate);
      } else if (table === 'trading_sessions') {
        channel = realtime.subscribeSessions(user.id, handleSessionUpdate);
      } else {
        return;
      }
      
      // Handle connection status
      channel.on('system', { event: '*' }, (payload) => {
        if (payload.type === 'connected') {
          setState(prev => ({ 
            ...prev, 
            isConnected: true, 
            connectionError: null,
            marketDataConnected 
          }));
        } else if (payload.type === 'error') {
          setState(prev => ({ 
            ...prev, 
            isConnected: false, 
            connectionError: payload.message || 'Connection error',
            marketDataConnected: false
          }));
        }
      });
      
      setChannels(prev => new Map(prev.set(channelName, channel)));
      
    } catch (error) {
      console.error(`Error subscribing to ${table}:`, error);
      setState(prev => ({ 
        ...prev, 
        connectionError: `Failed to subscribe to ${table}` 
      }));
    }
  }, [user, channels, handleTradeUpdate, handleSignalUpdate, handleSessionUpdate]);

  // Unsubscribe from a specific table
  const unsubscribeFrom = useCallback((table: 'trades' | 'smc_signals' | 'trading_sessions') => {
    if (!user) return;
    
    const channelName = `${table}_${user.id}`;
    const channel = channels.get(channelName);
    
    if (channel) {
      realtime.unsubscribe(channel);
      setChannels(prev => {
        const newChannels = new Map(prev);
        newChannels.delete(channelName);
        return newChannels;
      });
    }
  }, [user, channels]);

  // Unsubscribe from all channels
  const unsubscribeAll = useCallback(() => {
    channels.forEach((channel) => {
      realtime.unsubscribe(channel);
    });
    setChannels(new Map());
    setState(prev => ({ ...prev, isConnected: false, connectionError: null }));
  }, [channels]);

  // Refresh data from database
  const refreshData = useCallback(async () => {
    if (!user) return;
    
    try {
      // This would typically fetch fresh data from the database
      // For now, we'll just clear the local state to force re-subscription
      setState(prev => ({
        ...prev,
        trades: [],
        signals: [],
        sessions: []
      }));
    } catch (error) {
      console.error('Error refreshing data:', error);
      addToast({ type: 'error', title: 'Błąd', message: 'Błąd podczas odświeżania danych' });
    }
  }, [user]);

  // Update market data connection status
  useEffect(() => {
    setState(prev => ({
      ...prev,
      marketDataConnected,
      connectionError: marketDataError || prev.connectionError
    }));
  }, [marketDataConnected, marketDataError]);

  // Auto-subscribe to all tables when user is available
  useEffect(() => {
    if (user) {
      subscribeTo('trades');
      subscribeTo('smc_signals');
      subscribeTo('trading_sessions');
    } else {
      unsubscribeAll();
    }
    
    return () => {
      unsubscribeAll();
    };
  }, [user]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      unsubscribeAll();
    };
  }, []);

  return {
    ...state,
    subscribeTo,
    unsubscribeFrom,
    unsubscribeAll,
    refreshData
  };
};

export default useRealtime;