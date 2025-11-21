import React, { useState, useEffect } from 'react';
import {
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Bar,
  Cell
} from 'recharts';
import { useLiveMarketData } from '@/hooks/useLiveMarketData';
import { apiService, OHLCVData } from '@/services/api';
import { cn } from '@/lib/utils';

interface CandlestickData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  date: string;
  time: string;
  body: number;
  wick: number;
  bullish: boolean;
  color: string;
}

interface CandlestickChartProps {
  symbol?: string;
  timeframe?: string;
  height?: number;
  showVolume?: boolean;
  showGrid?: boolean;
  autoRefresh?: boolean;
  className?: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as CandlestickData;
    return (
      <div className="bg-white border border-gray-300 rounded-lg p-3 shadow-lg">
        <div className="text-sm font-medium text-gray-900 mb-2">
          {data.date} {data.time}
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-600">Open:</span>
            <span className={cn(
              "font-medium",
              data.bullish ? "text-green-600" : "text-red-600"
            )}>
              ${data.open.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">High:</span>
            <span className="font-medium text-gray-900">
              ${data.high.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Low:</span>
            <span className="font-medium text-gray-900">
              ${data.low.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Close:</span>
            <span className={cn(
              "font-medium",
              data.bullish ? "text-green-600" : "text-red-600"
            )}>
              ${data.close.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between col-span-2">
            <span className="text-gray-600">Volume:</span>
            <span className="font-medium text-gray-900">
              {data.volume.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between col-span-2">
            <span className="text-gray-600">Change:</span>
            <span className={cn(
              "font-medium",
              data.bullish ? "text-green-600" : "text-red-600"
            )}>
              {data.bullish ? '+' : ''}{((data.close - data.open) / data.open * 100).toFixed(2)}%
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

const CustomCandlestick: React.FC<any> = (props) => {
  const { x, y, width, height, payload } = props;
  const { bullish, body, wick } = payload as CandlestickData;

  if (!width || !height) return null;

  const bodyHeight = (body / (body + wick)) * height;
  const wickHeight = height - bodyHeight;
  const candleWidth = Math.max(width * 0.6, 2);

  return (
    <g>
      {/* Wick */}
      <line
        x1={x + width / 2}
        y1={y}
        x2={x + width / 2}
        y2={y + height}
        stroke={bullish ? '#10b981' : '#ef4444'}
        strokeWidth={1}
      />
      {/* Body */}
      <rect
        x={x + (width - candleWidth) / 2}
        y={bullish ? y + (height - bodyHeight) : y}
        width={candleWidth}
        height={bodyHeight}
        fill={bullish ? '#10b981' : '#ef4444'}
        stroke={bullish ? '#10b981' : '#ef4444'}
      />
    </g>
  );
};

const VolumeBar: React.FC<any> = (props) => {
  const { x, y, width, height, payload } = props;
  const { bullish, volume } = payload as CandlestickData;

  return (
    <rect
      x={x}
      y={y}
      width={width}
      height={height}
      fill={bullish ? '#10b98140' : '#ef444440'}
      stroke={bullish ? '#10b98180' : '#ef444480'}
      strokeWidth={1}
    />
  );
};

export default function CandlestickChart({
  symbol = 'BTCUSDT',
  timeframe = '1h',
  height = 400,
  showVolume = true,
  showGrid = true,
  autoRefresh = true,
  className
}: CandlestickChartProps) {
  const [candlestickData, setCandlestickData] = useState<CandlestickData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  // Get live market data
  const {
    data: ohlcvData,
    marketData,
    loading: marketLoading,
    forceRefresh
  } = useLiveMarketData({
    symbol,
    timeframe,
    enableRealtime: autoRefresh,
    refreshInterval: 5000,
  });

  // Transform OHLCV data to candlestick format
  const transformCandlestickData = (data: OHLCVData[]): CandlestickData[] => {
    return data.map(item => {
      const date = new Date(item.timestamp);
      const bullish = item.close >= item.open;
      const body = Math.abs(item.close - item.open);
      const wick = item.high - item.low;

      return {
        ...item,
        date: date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          ...(timeframe.includes('d') && { year: 'numeric' })
        }),
        time: date.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        }),
        body,
        wick,
        bullish,
        color: bullish ? '#10b981' : '#ef4444'
      };
    }).sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  };

  // Update candlestick data when OHLCV data changes
  useEffect(() => {
    if (ohlcvData && ohlcvData.length > 0) {
      const transformedData = transformCandlestickData(ohlcvData);
      setCandlestickData(transformedData);
      setCurrentPrice(transformedData[transformedData.length - 1]?.close || null);
    }
  }, [ohlcvData, timeframe]);

  // Get current market price for reference line
  useEffect(() => {
    if (marketData && marketData.length > 0) {
      const currentMarket = marketData.find(m => m.symbol === symbol);
      if (currentMarket) {
        setCurrentPrice(currentMarket.price);
      }
    }
  }, [marketData, symbol]);

  // Fetch initial data
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        setError(null);

        const limit = timeframe === '1m' ? 60 : timeframe === '5m' ? 144 : 100;
        const data = await apiService.getOHLCVData(symbol, timeframe, limit);

        if (data && data.length > 0) {
          const transformedData = transformCandlestickData(data);
          setCandlestickData(transformedData);
          setCurrentPrice(transformedData[transformedData.length - 1]?.close || null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch candlestick data');
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, [symbol, timeframe]);

  // Calculate price range for Y-axis
  const priceRange = candlestickData.length > 0 ? {
    min: Math.min(...candlestickData.map(d => d.low)) * 0.999,
    max: Math.max(...candlestickData.map(d => d.high)) * 1.001
  } : { min: 0, max: 0 };

  const volumeRange = candlestickData.length > 0 ? {
    min: 0,
    max: Math.max(...candlestickData.map(d => d.volume)) * 1.1
  } : { min: 0, max: 0 };

  if (loading && candlestickData.length === 0) {
    return (
      <div className={cn("flex items-center justify-center bg-gray-50 rounded-lg", className)} style={{ height }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-gray-600 text-sm">Loading chart data...</p>
        </div>
      </div>
    );
  }

  if (error && candlestickData.length === 0) {
    return (
      <div className={cn("flex items-center justify-center bg-red-50 rounded-lg", className)} style={{ height }}>
        <div className="text-center">
          <p className="text-red-600 text-sm">{error}</p>
          <button
            onClick={forceRefresh}
            className="mt-2 px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const chartHeight = showVolume ? height * 0.75 : height;
  const volumeHeight = height * 0.25;

  return (
    <div className={cn("w-full", className)}>
      <div className="relative" style={{ height }}>
        {/* Connection Status */}
        <div className="absolute top-2 right-2 z-10">
          <div className={cn(
            "flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium",
            marketLoading ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800"
          )}>
            <div className={cn(
              "w-2 h-2 rounded-full",
              marketLoading ? "bg-yellow-400 animate-pulse" : "bg-green-400"
            )}></div>
            <span>{marketLoading ? "Loading..." : "Live"}</span>
          </div>
        </div>

        {/* Current Price Display */}
        {currentPrice && (
          <div className="absolute top-2 left-2 z-10">
            <div className="bg-white/90 backdrop-blur px-3 py-2 rounded-lg shadow-sm">
              <div className="text-xs text-gray-600">{symbol}</div>
              <div className="text-lg font-bold text-gray-900">${currentPrice.toFixed(2)}</div>
            </div>
          </div>
        )}

        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={candlestickData}
            margin={{ top: 40, right: 10, bottom: 20, left: 10 }}
          >
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}

            <XAxis
              dataKey="time"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
              tickFormatter={(value) => value}
            />

            <YAxis
              yAxisId="price"
              domain={[priceRange.min, priceRange.max]}
              tick={{ fontSize: 10 }}
              tickFormatter={(value) => `$${value.toFixed(0)}`}
            />

            {showVolume && (
              <YAxis
                yAxisId="volume"
                orientation="right"
                domain={[0, volumeRange.max]}
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => {
                  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
                  return value.toFixed(0);
                }}
              />
            )}

            <Tooltip content={<CustomTooltip />} />

            {/* Current Price Reference Line */}
            {currentPrice && (
              <ReferenceLine
                yAxisId="price"
                y={currentPrice}
                stroke="#3b82f6"
                strokeDasharray="5 5"
                strokeWidth={1}
                label={{ value: `Current: $${currentPrice.toFixed(2)}`, position: "right" }}
              />
            )}

            {/* Candlesticks */}
            <Bar
              yAxisId="price"
              dataKey="high"
              shape={<CustomCandlestick />}
              fill="transparent"
            />

            {/* Volume Bars */}
            {showVolume && (
              <Bar
                yAxisId="volume"
                dataKey="volume"
                shape={<VolumeBar />}
                fill="transparent"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}