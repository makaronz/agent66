import React, { useEffect, useRef } from 'react';
import { TrendingUp, BarChart3, Activity } from 'lucide-react';

interface TradingViewChartProps {
  symbol: string;
  interval?: string;
  theme?: 'light' | 'dark';
  height?: number;
  className?: string;
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({
  symbol,
  interval = '15m',
  theme = 'light',
  height = 400,
  className = ''
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  useEffect(() => {
    // Clean up previous script
    if (scriptRef.current) {
      scriptRef.current.remove();
    }

    // Create TradingView widget script
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: `BINANCE:${symbol}`,
      interval: interval,
      timezone: 'Europe/Warsaw',
      theme: theme,
      style: '1',
      locale: 'pl',
      enable_publishing: false,
      allow_symbol_change: true,
      calendar: false,
      support_host: 'https://www.tradingview.com',
      studies: [
        'STD;SMA',
        'STD;EMA',
        'STD;RSI',
        'STD;MACD'
      ],
      show_popup_button: true,
      popup_width: '1000',
      popup_height: '650',
      container_id: `tradingview_${symbol.toLowerCase()}`
    });

    scriptRef.current = script;

    if (containerRef.current) {
      containerRef.current.appendChild(script);
    }

    return () => {
      if (scriptRef.current) {
        scriptRef.current.remove();
      }
    };
  }, [symbol, interval, theme]);

  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">{symbol} Chart</h3>
          </div>
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-green-500" />
            <span className="text-sm text-green-600 font-medium">Live</span>
          </div>
        </div>
      </div>
      
      <div className="relative" style={{ height: `${height}px` }}>
        <div 
          ref={containerRef}
          id={`tradingview_${symbol.toLowerCase()}`}
          className="w-full h-full"
        >
          {/* Fallback content while TradingView loads */}
          <div className="flex items-center justify-center h-full bg-gray-50">
            <div className="text-center">
              <TrendingUp className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">Ładowanie wykresu {symbol}...</p>
              <p className="text-sm text-gray-500 mt-2">Interwał: {interval}</p>
            </div>
          </div>
        </div>
      </div>
      
      <div className="p-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Powered by TradingView</span>
          <span>Real-time data from Binance</span>
        </div>
      </div>
    </div>
  );
};

export default TradingViewChart;