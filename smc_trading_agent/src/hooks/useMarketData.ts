import { useState, useEffect, useCallback, useRef } from 'react';
import { binanceApi, MarketData } from '../services/binanceApi';
import { toast } from 'sonner';
import { backgroundPatternDetection } from '../services/backgroundPatternDetection';
import { smcSignalGenerator } from '../services/smcSignalGenerator';

interface UseMarketDataOptions {
  symbols?: string[];
  autoConnect?: boolean;
  updateInterval?: number;
}

interface MarketDataState {
  data: Record<string, MarketData>;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  lastUpdate: Date | null;
}

export function useMarketData(options: UseMarketDataOptions = {}) {
  const {
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'XRPUSDT', 'SOLUSDT'],
    autoConnect = false, // Disabled auto-connect to prevent IP ban issues
    updateInterval = 30000 // WebSocket connection monitoring interval
  } = options;

  const [state, setState] = useState<MarketDataState>({
    data: {},
    isConnected: false,
    isLoading: true,
    error: null,
    lastUpdate: null
  });

  const unsubscribeRef = useRef<(() => void) | null>(null);
  const mountedRef = useRef(true);

  // Update market data
  const updateMarketData = useCallback((marketData: MarketData) => {
    if (!mountedRef.current) return;
    
    setState(prev => ({
      ...prev,
      data: {
        ...prev.data,
        [marketData.symbol]: marketData
      },
      lastUpdate: new Date(),
      isLoading: false,
      error: null
    }));
    
    // Update background services with WebSocket data
    try {
      // Update background pattern detection
      backgroundPatternDetection.updatePriceData(marketData.symbol, {
        price: marketData.price,
        open: marketData.open,
        high: marketData.high,
        low: marketData.low,
        close: marketData.price,
        volume: marketData.volume
      });
      
      // Update SMC signal generator
      smcSignalGenerator.updatePriceFromWebSocket(marketData.symbol, {
        price: marketData.price,
        open: marketData.open,
        high: marketData.high,
        low: marketData.low,
        close: marketData.price,
        volume: marketData.volume
      });
    } catch (error) {
      console.error('Error updating background services:', error);
    }
  }, []);

  // Initialize empty data structure for symbols
  const initializeEmptyData = useCallback(() => {
    if (!mountedRef.current) return;
    
    const dataMap: Record<string, MarketData> = {};
    symbols.forEach(symbol => {
      // Initialize with empty/placeholder data that will be populated by WebSocket
      dataMap[symbol] = {
        symbol,
        price: 0,
        change: 0,
        changePercent: 0,
        volume: 0,
        high: 0,
        low: 0,
        open: 0
      };
    });
    
    setState(prev => ({
      ...prev,
      data: dataMap,
      isLoading: false,
      error: null,
      lastUpdate: new Date()
    }));
  }, [symbols]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    
    // Disconnect existing connection
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }

    setState(prev => ({ ...prev, isConnected: false, error: null }));

    try {
      // Subscribe to multiple tickers
      const unsubscribe = binanceApi.subscribeToMultipleTickers(symbols, updateMarketData);
      unsubscribeRef.current = unsubscribe;

      // Check connection status after a short delay
      setTimeout(() => {
        if (!mountedRef.current) return;
        
        const isConnected = binanceApi.isConnected();
        setState(prev => ({ ...prev, isConnected }));
        
        if (isConnected) {
          toast.success('Connected to live market data');
        }
      }, 1000);

      // WebSocket only approach - no fallback REST API calls
      
    } catch (error) {
      if (!mountedRef.current) return;
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to connect to market data';
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isConnected: false
      }));
      toast.error(errorMessage);
    }
  }, [symbols, updateMarketData]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    
    setState(prev => ({ ...prev, isConnected: false }));
  }, []);

  // Refresh data manually - WebSocket only approach
  const refresh = useCallback(async () => {
    // Initialize empty data and reconnect WebSocket
    initializeEmptyData();
    if (autoConnect) {
      connect();
    }
  }, [initializeEmptyData, autoConnect, connect]);

  // Get specific symbol data
  const getSymbolData = useCallback((symbol: string): MarketData | null => {
    return state.data[symbol] || null;
  }, [state.data]);

  // Get all symbols data as array
  const getAllData = useCallback((): MarketData[] => {
    return Object.values(state.data);
  }, [state.data]);

  // Check if specific symbol is available
  const hasSymbol = useCallback((symbol: string): boolean => {
    return symbol in state.data;
  }, [state.data]);

  // Get connection status details
  const getConnectionStatus = useCallback(() => {
    return binanceApi.getConnectionStatus();
  }, []);

  // Initialize
  useEffect(() => {
    mountedRef.current = true;
    
    // Initialize empty data structure
    initializeEmptyData();
    
    // Auto-connect if enabled
    if (autoConnect) {
      // Small delay to allow initialization
      const timer = setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, [autoConnect]); // Remove problematic dependencies

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [disconnect]);

  // Monitor connection status
  useEffect(() => {
    const interval = setInterval(() => {
      if (!mountedRef.current) return;
      
      const isConnected = binanceApi.isConnected();
      setState(prev => {
        if (prev.isConnected !== isConnected) {
          return { ...prev, isConnected };
        }
        return prev;
      });
    }, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }, []);

  return {
    marketData: Object.values(state.data),
    // State
    data: state.data,
    isConnected: state.isConnected,
    isLoading: state.isLoading,
    error: state.error,
    lastUpdate: state.lastUpdate,
    
    // Actions
    connect,
    disconnect,
    refresh,
    subscribeToSymbol: (symbol: string) => {
      // Implementation for subscribing to individual symbol
    },
    unsubscribeFromSymbol: (symbol: string) => {
      // Implementation for unsubscribing from individual symbol
    },
    
    // Getters
    getSymbolData,
    getAllData,
    getAllSymbols: () => Object.keys(state.data),
    hasSymbol,
    getConnectionStatus,
    
    // Computed
    symbolCount: Object.keys(state.data).length,
    isOnline: state.isConnected && !state.error,
    isEmpty: Object.keys(state.data).length === 0
  };
}

export type { MarketData, MarketDataState };