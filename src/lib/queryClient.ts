import { QueryClient } from '@tanstack/react-query';

// Query client configuration optimized for trading application
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache time - how long data stays in cache when component unmounts
      gcTime: 1000 * 60 * 5, // 5 minutes
      
      // Stale time - how long data is considered fresh
      staleTime: 1000 * 30, // 30 seconds for market data
      
      // Retry configuration for failed requests
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors (client errors)
        if (error?.status >= 400 && error?.status < 500) {
          return false;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      
      // Retry delay with exponential backoff
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      
      // Refetch on window focus for real-time data
      refetchOnWindowFocus: true,
      
      // Refetch on reconnect
      refetchOnReconnect: true,
      
      // Don't refetch on mount if data is fresh
      refetchOnMount: 'always',
      
      // Network mode - continue queries when offline for cached data
      networkMode: 'online',
    },
    mutations: {
      // Retry mutations once
      retry: 1,
      
      // Retry delay for mutations
      retryDelay: 1000,
      
      // Network mode for mutations
      networkMode: 'online',
    },
  },
});

// Query keys factory for consistent key management
export const queryKeys = {
  // Market data keys
  marketData: {
    all: ['marketData'] as const,
    tickers: () => [...queryKeys.marketData.all, 'tickers'] as const,
    ticker: (symbol: string) => [...queryKeys.marketData.tickers(), symbol] as const,
    orderBook: (symbol: string) => [...queryKeys.marketData.all, 'orderBook', symbol] as const,
    klines: (symbol: string, interval: string) => 
      [...queryKeys.marketData.all, 'klines', symbol, interval] as const,
    trades: (symbol: string) => [...queryKeys.marketData.all, 'trades', symbol] as const,
  },
  
  // Exchange info keys
  exchange: {
    all: ['exchange'] as const,
    info: () => [...queryKeys.exchange.all, 'info'] as const,
    symbols: () => [...queryKeys.exchange.all, 'symbols'] as const,
    filters: () => [...queryKeys.exchange.all, 'filters'] as const,
  },
  
  // User data keys
  user: {
    all: ['user'] as const,
    profile: (userId: string) => [...queryKeys.user.all, 'profile', userId] as const,
    preferences: (userId: string) => [...queryKeys.user.all, 'preferences', userId] as const,
  },
  
  // Chart data keys
  chart: {
    all: ['chart'] as const,
    candlesticks: (symbol: string, timeframe: string) => 
      [...queryKeys.chart.all, 'candlesticks', symbol, timeframe] as const,
    indicators: (symbol: string) => [...queryKeys.chart.all, 'indicators', symbol] as const,
  },
} as const;

// Query invalidation helpers
export const invalidateQueries = {
  // Invalidate all market data
  allMarketData: () => queryClient.invalidateQueries({ 
    queryKey: queryKeys.marketData.all 
  }),
  
  // Invalidate specific ticker
  ticker: (symbol: string) => queryClient.invalidateQueries({ 
    queryKey: queryKeys.marketData.ticker(symbol) 
  }),
  
  // Invalidate order book
  orderBook: (symbol: string) => queryClient.invalidateQueries({ 
    queryKey: queryKeys.marketData.orderBook(symbol) 
  }),
  
  // Invalidate exchange info
  exchangeInfo: () => queryClient.invalidateQueries({ 
    queryKey: queryKeys.exchange.info() 
  }),
  
  // Invalidate user data
  userProfile: (userId: string) => queryClient.invalidateQueries({ 
    queryKey: queryKeys.user.profile(userId) 
  }),
  
  // Invalidate chart data
  chartData: (symbol: string) => queryClient.invalidateQueries({ 
    queryKey: [...queryKeys.chart.all, symbol] 
  }),
};

// Prefetch helpers for better UX
export const prefetchQueries = {
  // Prefetch exchange info on app start
  exchangeInfo: () => queryClient.prefetchQuery({
    queryKey: queryKeys.exchange.info(),
    staleTime: 1000 * 60 * 10, // 10 minutes - exchange info doesn't change often
  }),
  
  // Prefetch popular tickers
  popularTickers: (symbols: string[]) => {
    symbols.forEach(symbol => {
      queryClient.prefetchQuery({
        queryKey: queryKeys.marketData.ticker(symbol),
        staleTime: 1000 * 10, // 10 seconds for ticker data
      });
    });
  },
};

// Error handling utilities
export const handleQueryError = (error: any, context?: string) => {
  console.error(`Query error${context ? ` in ${context}` : ''}:`, error);
  
  // You can add toast notifications here
  // toast.error(`Failed to load ${context || 'data'}. Please try again.`);
  
  // Track errors for monitoring
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', 'query_error', {
      error_message: error.message,
      context: context || 'unknown',
    });
  }
};

// Cache management utilities
export const cacheUtils = {
  // Clear all cache
  clearAll: () => queryClient.clear(),
  
  // Clear market data cache
  clearMarketData: () => queryClient.removeQueries({ 
    queryKey: queryKeys.marketData.all 
  }),
  
  // Clear user data cache (useful on logout)
  clearUserData: () => queryClient.removeQueries({ 
    queryKey: queryKeys.user.all 
  }),
  
  // Get cache size (for debugging)
  getCacheSize: () => {
    const cache = queryClient.getQueryCache();
    return cache.getAll().length;
  },
  
  // Get cached data for debugging
  getCachedData: (queryKey: any[]) => {
    return queryClient.getQueryData(queryKey);
  },
};

// Development helpers
if (process.env.NODE_ENV === 'development') {
  // Add query client to window for debugging
  (window as any).queryClient = queryClient;
  (window as any).queryKeys = queryKeys;
  (window as any).cacheUtils = cacheUtils;
}