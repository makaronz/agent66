import { useState, useEffect, useRef } from 'react';
import { apiService, OHLCVData, MarketData } from '@/services/api';

interface UseLiveMarketDataOptions {
  symbol?: string;
  timeframe?: string;
  enableRealtime?: boolean;
  refreshInterval?: number;
}

interface LiveMarketDataReturn {
  data: OHLCVData[];
  marketData: MarketData[];
  loading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  isConnected: boolean;
  forceRefresh: () => Promise<void>;
}

export function useLiveMarketData({
  symbol = 'BTCUSDT',
  timeframe = '1h',
  enableRealtime = true,
  refreshInterval = 5000, // 5 seconds
}: UseLiveMarketDataOptions = {}): LiveMarketDataReturn {
  const [data, setData] = useState<OHLCVData[]>([]);
  const [marketData, setMarketData] = useState<MarketData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = async () => {
    try {
      setError(null);

      // Fetch OHLCV data
      const ohlcvData = await apiService.getOHLCVData(symbol, timeframe, 100);

      // Fetch market data
      const market = await apiService.getMarketData();

      setData(ohlcvData);
      setMarketData(market);
      setLastUpdate(new Date());
      setIsConnected(true);
    } catch (err) {
      console.error('Failed to fetch market data:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const forceRefresh = async () => {
    setLoading(true);
    await fetchData();
  };

  useEffect(() => {
    // Initial fetch
    fetchData();

    // Set up real-time updates
    if (enableRealtime && refreshInterval > 0) {
      intervalRef.current = setInterval(fetchData, refreshInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [symbol, timeframe, enableRealtime, refreshInterval]);

  return {
    data,
    marketData,
    loading,
    error,
    lastUpdate,
    isConnected,
    forceRefresh,
  };
}

export default useLiveMarketData;