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
  console.log('🔄 useMarketData hook called with options:', options);
  console.log('🚀 HOOK EXECUTION STARTED - useMarketData is running!');
  
  const {
    symbols = ['BTCUSDT'], // Test with single symbol first
    autoConnect = true, // Enable auto-connect for better user experience
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
      if (backgroundPatternDetection && typeof backgroundPatternDetection.updatePriceData === 'function') {
        backgroundPatternDetection.updatePriceData(marketData.symbol, {
          price: marketData.price,
          open: marketData.open,
          high: marketData.high,
          low: marketData.low,
          close: marketData.price,
          volume: marketData.volume
        });
      }
      
      // Update SMC signal generator
      if (smcSignalGenerator && typeof smcSignalGenerator.updatePriceFromWebSocket === 'function') {
        smcSignalGenerator.updatePriceFromWebSocket(marketData.symbol, {
          price: marketData.price,
          open: marketData.open,
          high: marketData.high,
          low: marketData.low,
          close: marketData.price,
          volume: marketData.volume
        });
      }
    } catch (error) {
      console.error('❌ Error updating background services:', error);
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

  // Connect using REST API fallback
  const connect = useCallback(async () => {
    console.log('🔄 useMarketData connect called, using REST API fallback');
    if (!mountedRef.current) return;
    
    console.log('🚀 Starting market data connection with REST API...');
    setState(prev => ({ ...prev, isConnected: false, error: null, isLoading: true }));

    try {
      const tickers = await binanceApi.get24hrTicker();
      const filteredTickers = tickers.filter(ticker => 
        symbols.includes(ticker.symbol)
      );
      
      const newData: Record<string, MarketData> = {};
      filteredTickers.forEach(ticker => {
        newData[ticker.symbol] = {
          symbol: ticker.symbol,
          price: parseFloat(ticker.price),
          change: parseFloat(ticker.priceChange),
          changePercent: parseFloat(ticker.priceChangePercent),
          volume: parseFloat(ticker.volume),
          high: parseFloat(ticker.highPrice),
          low: parseFloat(ticker.lowPrice),
          open: parseFloat(ticker.openPrice)
        };
      });
      
      if (mountedRef.current) {
        setState(prev => ({
          ...prev,
          data: newData,
          isLoading: false,
          isConnected: true,
          lastUpdate: new Date()
        }));
        
        console.log('✅ Market data connection established via REST API');
        toast.success('Connected to market data via REST API');
      }
      
    } catch (error) {
      if (!mountedRef.current) return;
      
      console.error('❌ Failed to connect to market data:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to connect to market data';
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isConnected: false,
        isLoading: false
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

  // Refresh data manually - REST API approach
  const refresh = useCallback(async () => {
    // Fetch fresh data from REST API
    await connect();
  }, [connect]);

  // Get specific symbol data
  const getSymbolData = useCallback((symbol: string): MarketData | null => {
    return state.data[symbol] || null;
  }, []);

  // Get all symbols data as array
  const getAllData = useCallback((): MarketData[] => {
    return Object.values(state.data);
  }, []);

  // Check if specific symbol is available
  const hasSymbol = useCallback((symbol: string): boolean => {
    return symbol in state.data;
  }, []);

  // Get connection status details
  const getConnectionStatus = useCallback(() => {
    return binanceApi.getConnectionStatus();
  }, []);

  // Initialize with REST API fallback
  useEffect(() => {
    console.log('🔧 useMarketData useEffect triggered, using REST API fallback');
    mountedRef.current = true;
    let intervalId: NodeJS.Timeout;
    
    // Fallback to REST API due to WebSocket CORS issues in browser
    const fetchMarketData = async () => {
      try {
        setState(prev => ({ ...prev, isLoading: true, error: null }));
        
        const tickers = await binanceApi.get24hrTicker();
        const filteredTickers = tickers.filter(ticker => 
          symbols.includes(ticker.symbol)
        );
        
        const newData: Record<string, MarketData> = {};
        filteredTickers.forEach(ticker => {
          newData[ticker.symbol] = {
            symbol: ticker.symbol,
            price: parseFloat(ticker.price),
            change: parseFloat(ticker.priceChange),
            changePercent: parseFloat(ticker.priceChangePercent),
            volume: parseFloat(ticker.volume),
            high: parseFloat(ticker.highPrice),
            low: parseFloat(ticker.lowPrice),
            open: parseFloat(ticker.openPrice)
          };
        });
        
        if (mountedRef.current) {
          setState(prev => ({
            ...prev,
            data: newData,
            isLoading: false,
            isConnected: true,
            lastUpdate: new Date()
          }));
        }
      } catch (error) {
        if (mountedRef.current) {
          console.error('Error fetching market data:', error);
          const errorMessage = error instanceof Error ? error.message : 'Failed to fetch market data';
          setState(prev => ({
            ...prev,
            error: errorMessage,
            isLoading: false,
            isConnected: false
          }));
        }
      }
    };

    // Initial fetch with delay to avoid rate limiting
    const timeoutId = setTimeout(() => {
      fetchMarketData();
      // Update every 60 seconds to avoid rate limiting
      intervalId = setInterval(fetchMarketData, 60000);
    }, 1000);

    return () => {
      clearTimeout(timeoutId);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [symbols.join(',')]); // Use string join to avoid array reference issues

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