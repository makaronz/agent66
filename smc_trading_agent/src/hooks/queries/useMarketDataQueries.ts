import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { marketDataService } from '../../services/MarketDataService';
import { queryKeys, handleQueryError } from '../../lib/queryClient';
import { useMarketDataStore } from '../../stores/marketDataStore';
import { toast } from 'sonner';

// Types for market data
export interface TickerData {
  symbol: string;
  price: string;
  priceChange: string;
  priceChangePercent: string;
  volume: string;
  high: string;
  low: string;
  open: string;
  prevClose: string;
  count: number;
}

export interface OrderBookEntry {
  price: string;
  quantity: string;
}

export interface OrderBookData {
  symbol: string;
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
  lastUpdateId: number;
}

export interface ExchangeInfo {
  timezone: string;
  serverTime: number;
  symbols: Array<{
    symbol: string;
    status: string;
    baseAsset: string;
    quoteAsset: string;
    filters: any[];
  }>;
}

export interface KlineData {
  openTime: number;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
  closeTime: number;
  quoteAssetVolume: string;
  numberOfTrades: number;
  takerBuyBaseAssetVolume: string;
  takerBuyQuoteAssetVolume: string;
}

// Exchange Info Query
export const useExchangeInfoQuery = () => {
  return useQuery({
    queryKey: queryKeys.exchange.info(),
    queryFn: async (): Promise<ExchangeInfo> => {
      try {
        const data = await marketDataService.getExchangeInfo();
        return data;
      } catch (error: any) {
        handleQueryError(error, 'exchange info');
        throw error;
      }
    },
    staleTime: 1000 * 60 * 10, // 10 minutes - exchange info doesn't change often
    gcTime: 1000 * 60 * 30, // 30 minutes
    retry: 2,
  });
};

// All Tickers Query
export const useAllTickersQuery = (enabled: boolean = true) => {
  return useQuery({
    queryKey: queryKeys.marketData.tickers(),
    queryFn: async (): Promise<TickerData[]> => {
      try {
        const data = await marketDataService.getAllTickers();
        return data;
      } catch (error: any) {
        handleQueryError(error, 'all tickers');
        throw error;
      }
    },
    enabled,
    staleTime: 1000 * 10, // 10 seconds
    gcTime: 1000 * 60 * 2, // 2 minutes
    refetchInterval: 5000, // Refetch every 5 seconds for real-time data
  });
};

// Single Ticker Query
export const useTickerQuery = (symbol: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: queryKeys.marketData.ticker(symbol),
    queryFn: async (): Promise<TickerData> => {
      try {
        const data = await marketDataService.getTicker(symbol);
        return data;
      } catch (error: any) {
        handleQueryError(error, `ticker for ${symbol}`);
        throw error;
      }
    },
    enabled: enabled && !!symbol,
    staleTime: 1000 * 5, // 5 seconds
    gcTime: 1000 * 60, // 1 minute
    refetchInterval: 3000, // Refetch every 3 seconds
  });
};

// Order Book Query
export const useOrderBookQuery = (symbol: string, limit: number = 100, enabled: boolean = true) => {
  return useQuery({
    queryKey: queryKeys.marketData.orderBook(symbol),
    queryFn: async (): Promise<OrderBookData> => {
      try {
        const data = await marketDataService.getOrderBook(symbol, limit);
        return data;
      } catch (error: any) {
        handleQueryError(error, `order book for ${symbol}`);
        throw error;
      }
    },
    enabled: enabled && !!symbol,
    staleTime: 1000 * 2, // 2 seconds
    gcTime: 1000 * 30, // 30 seconds
    refetchInterval: 2000, // Refetch every 2 seconds
  });
};

// Klines (Candlestick) Query
export const useKlinesQuery = (
  symbol: string,
  interval: string = '1h',
  limit: number = 100,
  enabled: boolean = true
) => {
  return useQuery({
    queryKey: ['klines', symbol, interval, limit],
    queryFn: async () => {
      try {
        // TODO: Implement getKlines in MarketDataService
        throw new Error('getKlines not implemented yet');
      } catch (error: any) {
        console.error('Failed to fetch klines:', error);
        throw error;
      }
    },
    enabled: false, // Disabled until implemented
    staleTime: 1000 * 30, // 30 seconds
    gcTime: 1000 * 60 * 5, // 5 minutes
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

// Recent Trades Query
export const useRecentTradesQuery = (symbol: string, limit: number = 100) => {
  return useQuery({
    queryKey: ['recentTrades', symbol, limit],
    queryFn: async () => {
      if (!symbol) throw new Error('Symbol is required');
      
      try {
        // TODO: Implement getRecentTrades in MarketDataService
        throw new Error('getRecentTrades not implemented yet');
      } catch (error) {
        console.error('Failed to fetch recent trades:', error);
        throw error;
      }
    },
    enabled: false, // Disabled until implemented
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // 1 minute
  });
};

// Infinite Query for Historical Klines
export const useInfiniteKlinesQuery = (
  symbol: string,
  interval: string,
  limit: number = 500
) => {
  return useInfiniteQuery({
    queryKey: [...queryKeys.marketData.klines(symbol, interval), 'infinite'],
    queryFn: async ({ pageParam = undefined }) => {
      try {
        const data = await marketDataService.getKlines(
          symbol, 
          interval, 
          limit
        );
        return data;
      } catch (error: any) {
        handleQueryError(error, `infinite klines for ${symbol}`);
        throw error;
      }
    },
    getNextPageParam: (lastPage: KlineData[]) => {
      if (lastPage.length < limit) return undefined;
      return lastPage[0]?.openTime; // Use first item's timestamp for next page
    },
    initialPageParam: undefined,
    staleTime: 1000 * 60, // 1 minute
    gcTime: 1000 * 60 * 10, // 10 minutes
  });
};

// Mutation for subscribing to WebSocket streams
export const useSubscribeToSymbolMutation = () => {
  const queryClient = useQueryClient();
  // WebSocket subscriptions are handled by the store directly

  return useMutation({
    mutationFn: async ({ symbol, streams }: { symbol: string; streams: string[] }) => {
      try {
        // TODO: Implement WebSocket subscription in MarketDataService
        console.log(`Subscribing to ${symbol} with streams:`, streams);
        return { symbol, streams };
      } catch (error: any) {
        console.error(`Error subscribing to ${symbol}:`, error);
        throw error;
      }
    },
    onSuccess: ({ symbol }) => {
      // Invalidate related queries to refresh data
      queryClient.invalidateQueries({ queryKey: queryKeys.marketData.ticker(symbol) });
      queryClient.invalidateQueries({ queryKey: queryKeys.marketData.orderBook(symbol) });
      
      toast.success(`Subscribed to ${symbol} data streams`);
    },
    onError: (error: any, { symbol }) => {
      toast.error(`Failed to subscribe to ${symbol}: ${error.message}`);
    },
  });
};

// Mutation for unsubscribing from WebSocket streams
export const useUnsubscribeFromSymbolMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ symbol, streams }: { symbol: string; streams?: string[] }) => {
      try {
        // TODO: Implement WebSocket unsubscription in MarketDataService
        console.log(`Unsubscribing from ${symbol} with streams:`, streams);
        return { symbol, streams };
      } catch (error: any) {
        console.error(`Error unsubscribing from ${symbol}:`, error);
        throw error;
      }
    },
    onSuccess: ({ symbol }) => {
      toast.success(`Unsubscribed from ${symbol} data streams`);
    },
    onError: (error: any, { symbol }) => {
      toast.error(`Failed to unsubscribe from ${symbol}: ${error.message}`);
    },
  });
};

// Combined hook for easy market data access
export const useMarketData = (symbol: string) => {
  const ticker = useTickerQuery(symbol);
  const orderBook = useOrderBookQuery(symbol, 20); // Limit to 20 levels for performance
  const klines = useKlinesQuery(symbol, '1h', 100); // 1 hour interval, 100 candles
  const recentTrades = useRecentTradesQuery(symbol, 50); // Last 50 trades

  return {
    ticker: {
      data: ticker.data,
      isLoading: ticker.isLoading,
      error: ticker.error,
      refetch: ticker.refetch,
    },
    orderBook: {
      data: orderBook.data,
      isLoading: orderBook.isLoading,
      error: orderBook.error,
      refetch: orderBook.refetch,
    },
    klines: {
      data: klines.data,
      isLoading: klines.isLoading,
      error: klines.error,
      refetch: klines.refetch,
    },
    recentTrades: {
      data: recentTrades.data,
      isLoading: recentTrades.isLoading,
      error: recentTrades.error,
      refetch: recentTrades.refetch,
    },
    isLoading: ticker.isLoading || orderBook.isLoading || klines.isLoading || recentTrades.isLoading,
    hasError: !!(ticker.error || orderBook.error || klines.error || recentTrades.error),
  };
};

// Hook for popular trading pairs
export const usePopularPairs = () => {
  const popularSymbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'];
  
  const queries = popularSymbols.map(symbol => ({
    symbol,
    ...useTickerQuery(symbol)
  }));

  return {
    data: queries.map(q => ({ symbol: q.symbol, ...q.data })).filter(Boolean),
    isLoading: queries.some(q => q.isLoading),
    hasError: queries.some(q => q.error),
    refetchAll: () => queries.forEach(q => q.refetch()),
  };
};