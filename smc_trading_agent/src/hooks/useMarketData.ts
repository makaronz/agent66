import { useCallback, useEffect } from 'react';
import { MarketData } from '../services/binanceApi';
import { useMarketDataStore, TickerData } from '../stores/marketDataStore';
import { useExchangeInfoQuery } from './queries/useMarketDataQueries';
import { backgroundPatternDetection } from '../services/BackgroundPatternDetection';
import { smcSignalGenerator } from '../services/SMCSignalGenerator';

interface UseMarketDataOptions {
  symbols?: string[];
  autoConnect?: boolean;
  updateInterval?: number;
}

interface MarketDataHookReturn {
  data: Record<string, MarketData>;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  refresh: () => Promise<void>;
  getSymbolData: (symbol: string) => MarketData | null;
  getAllData: () => MarketData[];
  hasSymbol: (symbol: string) => boolean;
  getConnectionStatus: () => {
    isConnected: boolean;
    isLoading: boolean;
    error: string | null;
    lastUpdate: Date | null;
  };
  symbols: string[];
  hasData: boolean;
  dataCount: number;
}

// ITERATION 2: Refactored to use Zustand store and TanStack Query
// This provides better state management and caching capabilities
export function useMarketData(options: UseMarketDataOptions = {}): MarketDataHookReturn {
  console.log('🔄 useMarketData hook called with options:', options);
  console.log('🚀 HOOK EXECUTION STARTED - useMarketData using Zustand + TanStack Query!');
  
  const {
    symbols = ['BTCUSDT'], // Test with single symbol first
    autoConnect = true, // Enable auto-connect for better user experience
    updateInterval = 60000 // 60 seconds to respect rate limits
  } = options;

  // Use Zustand store for market data state
  const {
    tickers,
    wsState,
    isLoading,
    error,
    lastUpdate,
    setSelectedSymbols,
    connectWebSocket,
    disconnectWebSocket,
    setTicker,
    fetchMultipleTickers
  } = useMarketDataStore();

  // Data fetching is handled by the store
  const tickersLoading = false;
  const tickersError = null;

  const { data: exchangeInfo } = useExchangeInfoQuery();

  // Update background services when new data arrives
  const updateBackgroundServices = useCallback((data: Record<string, MarketData>) => {
    Object.values(data).forEach(marketData => {
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
    });
  }, []);

  // Set selected symbols in store when symbols change
  useEffect(() => {
    setSelectedSymbols(symbols);
  }, [symbols, setSelectedSymbols]);

  // Update background services when ticker data changes
  useEffect(() => {
    if (tickers && Object.keys(tickers).length > 0) {
      // Convert TickerData to MarketData format for background services
      const marketDataFormat: Record<string, MarketData> = {};
      Object.entries(tickers).forEach(([symbol, ticker]) => {
        marketDataFormat[symbol] = {
          symbol: ticker.symbol,
          price: parseFloat(ticker.price),
          change: parseFloat(ticker.priceChange),
          changePercent: parseFloat(ticker.priceChangePercent),
          volume: parseFloat(ticker.volume),
          high: parseFloat(ticker.high),
          low: parseFloat(ticker.low),
          open: parseFloat(ticker.open)
        };
      });
      updateBackgroundServices(marketDataFormat);
    }
  }, [tickers, updateBackgroundServices]);

  // Auto-connect effect
  useEffect(() => {
    if (autoConnect && !wsState.isConnected) {
      console.log('🔄 Starting auto-connect with symbols:', symbols);
      connectWebSocket();
      fetchMultipleTickers(symbols);
    }
  }, [autoConnect, wsState.isConnected, connectWebSocket, fetchMultipleTickers, symbols]);

  // Combine data from different sources - convert TickerData to MarketData
   const combinedData: Record<string, MarketData> = {};
   Object.entries(tickers).forEach(([symbol, ticker]) => {
     combinedData[symbol] = {
       symbol: ticker.symbol,
       price: parseFloat(ticker.price),
       change: parseFloat(ticker.priceChange),
       changePercent: parseFloat(ticker.priceChangePercent),
       volume: parseFloat(ticker.volume),
       high: parseFloat(ticker.high),
       low: parseFloat(ticker.low),
       open: parseFloat(ticker.open)
     };
   });

  // Combine loading states
  const combinedLoading = isLoading || tickersLoading;
  
  // Combine errors
  const combinedError = error || tickersError?.message || null;

  // Connect function - delegates to store
  const connect = useCallback(async () => {
    console.log('🔄 useMarketData connect called, delegating to store');
    connectWebSocket();
    await fetchMultipleTickers(symbols);
  }, [connectWebSocket, fetchMultipleTickers, symbols]);

  // Disconnect function - delegates to store
  const disconnect = useCallback(() => {
    console.log('🔄 useMarketData disconnect called');
    disconnectWebSocket();
  }, [disconnectWebSocket]);

  // Refresh function - refetch queries
  const refresh = useCallback(async () => {
    console.log('🔄 useMarketData refresh called');
    // Refetch data from store
    await fetchMultipleTickers(symbols);
  }, [fetchMultipleTickers, symbols]);

  // Get specific symbol data
  const getSymbolData = useCallback((symbol: string): MarketData | null => {
    return combinedData[symbol] || null;
  }, [combinedData]);

  // Get all symbols data as array
  const getAllData = useCallback((): MarketData[] => {
    return Object.values(combinedData);
  }, [combinedData]);

  // Check if specific symbol is available
  const hasSymbol = useCallback((symbol: string): boolean => {
    return symbol in combinedData;
  }, [combinedData]);

  // Get connection status
  const getConnectionStatus = useCallback(() => {
    return {
      isConnected: wsState.isConnected,
      isLoading: combinedLoading,
      error: combinedError,
      lastUpdate: new Date(lastUpdate)
    };
  }, [wsState.isConnected, combinedLoading, combinedError, lastUpdate]);

  return {
    // State
    data: combinedData,
    isConnected: wsState.isConnected,
    isLoading: combinedLoading,
    error: combinedError,
    lastUpdate: new Date(lastUpdate),
    
    // Actions
    connect,
    disconnect,
    refresh,
    
    // Data access
    getSymbolData,
    getAllData,
    hasSymbol,
    getConnectionStatus,
    
    // Computed values
    symbols,
    hasData: Object.keys(combinedData).length > 0,
    dataCount: Object.keys(combinedData).length
  };
}

// Export types for external use
export type { UseMarketDataOptions, MarketDataHookReturn };