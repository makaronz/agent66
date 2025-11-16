import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService, type SMCPattern, type Trade, type OHLCVData } from '@/services/api';
import {
  Line,
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

export default function TradingInterface() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('LIMIT');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [autoTrading, setAutoTrading] = useState(false);
  
  // Real data from API
  const [smcPatterns, setSmcPatterns] = useState<SMCPattern[]>([]);
  const [recentOrders, setRecentOrders] = useState<Trade[]>([]);
  const [ohlcvData, setOhlcvData] = useState<OHLCVData[]>([]);
  const [loading, setLoading] = useState(true);
  const [chartLoading, setChartLoading] = useState(true);
  const [orderLoading, setOrderLoading] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState('1h');

  // Fetch SMC patterns, recent orders, and OHLCV data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setChartLoading(true);
        const [patterns, orders, ohlcv] = await Promise.all([
          apiService.getSMCPatterns(),
          apiService.getTradingHistory(10, selectedSymbol),
          apiService.getOHLCVData(selectedSymbol, timeframe, 100)
        ]);
        setSmcPatterns(patterns);
        setRecentOrders(orders);
        setOhlcvData(ohlcv);
      } catch (error) {
        console.error('Error fetching trading data:', error);
      } finally {
        setLoading(false);
        setChartLoading(false);
      }
    };

    fetchData();
    // Refresh patterns every 30 seconds, orders every 10 seconds, chart every 60 seconds
    const patternsInterval = setInterval(() => {
      apiService.getSMCPatterns().then(setSmcPatterns).catch(console.error);
    }, 30000);
    
    const ordersInterval = setInterval(() => {
      apiService.getTradingHistory(10, selectedSymbol).then(setRecentOrders).catch(console.error);
    }, 10000);

    const chartInterval = setInterval(() => {
      apiService.getOHLCVData(selectedSymbol, timeframe, 100)
        .then(setOhlcvData)
        .catch(console.error);
    }, 60000);

    return () => {
      clearInterval(patternsInterval);
      clearInterval(ordersInterval);
      clearInterval(chartInterval);
    };
  }, [selectedSymbol, timeframe]);

  const handlePlaceOrder = async () => {
    if (!quantity || !price) {
      setOrderError('Please fill in quantity and price');
      return;
    }

    setOrderLoading(true);
    setOrderError(null);

    try {
      const trade = await apiService.executeTrade({
        symbol: selectedSymbol,
        action: orderSide,
        price: parseFloat(price),
        size: parseFloat(quantity),
        reason: `Manual ${orderSide} order`,
        stopLoss: stopLoss ? parseFloat(stopLoss) : undefined,
        takeProfit: takeProfit ? parseFloat(takeProfit) : undefined,
      });

      // Refresh orders list
      const orders = await apiService.getTradingHistory(10, selectedSymbol);
      setRecentOrders(orders);

      // Reset form
      setQuantity('');
      setPrice('');
      setStopLoss('');
      setTakeProfit('');

      alert(`Order placed successfully! Trade ID: ${trade.id}`);
    } catch (error: any) {
      setOrderError(error.message || 'Failed to place order');
      console.error('Error placing order:', error);
    } finally {
      setOrderLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trading Interface</h1>
          <p className="text-gray-600">Live SMC pattern detection and order management</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Auto Trading</span>
            <button
              onClick={() => setAutoTrading(!autoTrading)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                autoTrading ? "bg-green-600" : "bg-gray-200"
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                  autoTrading ? "translate-x-6" : "translate-x-1"
                )}
              />
            </button>
          </div>
          {autoTrading ? (
            <div className="flex items-center space-x-1 text-green-600">
              <Play className="h-4 w-4" />
              <span className="text-sm font-medium">Active</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1 text-gray-500">
              <Pause className="h-4 w-4" />
              <span className="text-sm font-medium">Paused</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SMC Pattern Detection */}
        <div className="lg:col-span-2 space-y-6">
          {/* Chart Placeholder */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">Price Chart & SMC Patterns</h3>
                <select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  className="text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="BTCUSDT">BTC/USDT</option>
                  <option value="ETHUSDT">ETH/USDT</option>
                  <option value="ADAUSDT">ADA/USDT</option>
                  <option value="SOLUSDT">SOL/USDT</option>
                </select>
              </div>
            </div>
            <div className="p-6">
              <div className="mb-4 flex items-center space-x-2">
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="1m">1 Minute</option>
                  <option value="5m">5 Minutes</option>
                  <option value="15m">15 Minutes</option>
                  <option value="1h">1 Hour</option>
                  <option value="4h">4 Hours</option>
                  <option value="1d">1 Day</option>
                </select>
              </div>
              {chartLoading ? (
                <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4 animate-pulse" />
                    <p className="text-gray-500">Loading chart data...</p>
                  </div>
                </div>
              ) : ohlcvData.length === 0 ? (
                <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                  <div className="text-center">
                    <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">No chart data available</p>
                  </div>
                </div>
              ) : (
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={ohlcvData.map(d => {
                      const isUp = d.close >= d.open;
                      return {
                        time: new Date(d.timestamp).toLocaleTimeString(),
                        timestamp: d.timestamp,
                        open: d.open,
                        high: d.high,
                        low: d.low,
                        close: d.close,
                        volume: d.volume,
                        isUp
                      };
                    })}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="time" 
                        stroke="#6b7280"
                        fontSize={12}
                        tick={{ fill: '#6b7280' }}
                        interval="preserveStartEnd"
                      />
                      <YAxis 
                        yAxisId="left"
                        stroke="#6b7280"
                        fontSize={12}
                        tick={{ fill: '#6b7280' }}
                        domain={['auto', 'auto']}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                          color: '#f3f4f6'
                        }}
                        formatter={(value: any, name: string) => {
                          if (['open', 'high', 'low', 'close'].includes(name)) {
                            return [`$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, name.toUpperCase()];
                          }
                          return [value, name];
                        }}
                      />
                      {/* Candlestick visualization using Area and Line */}
                      <Area
                        dataKey="high"
                        stroke="none"
                        fill="none"
                        yAxisId="left"
                      />
                      <Line
                        type="monotone"
                        dataKey="high"
                        stroke="#6b7280"
                        strokeWidth={1}
                        dot={false}
                        yAxisId="left"
                      />
                      <Line
                        type="monotone"
                        dataKey="low"
                        stroke="#6b7280"
                        strokeWidth={1}
                        dot={false}
                        yAxisId="left"
                      />
                      <Line
                        type="monotone"
                        dataKey="close"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={false}
                        yAxisId="left"
                        name="Close"
                      />
                      {/* SMC Pattern overlays */}
                      {smcPatterns
                        .filter(p => p.symbol === selectedSymbol)
                        .map((pattern) => {
                          const patternPrice = pattern.price || pattern.priceLevel || 0;
                          const isBullish = pattern.direction?.toLowerCase() === 'bullish';
                          return (
                            <ReferenceLine
                              key={pattern.id}
                              y={patternPrice}
                              yAxisId="left"
                              stroke={isBullish ? '#10b981' : '#ef4444'}
                              strokeDasharray="5 5"
                              strokeWidth={2}
                              label={{
                                value: `${pattern.type?.replace('_', ' ') || 'Pattern'}`,
                                position: 'right',
                                fill: isBullish ? '#10b981' : '#ef4444',
                                fontSize: 10
                              }}
                            />
                          );
                        })}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          {/* Detected Patterns */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Detected SMC Patterns</h3>
            </div>
            <div className="p-6">
              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading SMC patterns...</div>
              ) : smcPatterns.length === 0 ? (
                <div className="text-center py-8 text-gray-500">No SMC patterns detected yet</div>
              ) : (
                <div className="space-y-4">
                  {smcPatterns.map((pattern) => {
                    // Normalize direction for display
                    const direction = pattern.direction?.toLowerCase() === 'bullish' ? 'Bullish' : 'Bearish';
                    const price = pattern.price || pattern.priceLevel || 0;
                    const confidence = pattern.confidence || pattern.strength || 0;
                    const detectedTime = pattern.timestamp 
                      ? new Date(pattern.timestamp).toLocaleString() 
                      : 'Just now';
                    
                    return (
                      <div key={pattern.id} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <div className={cn(
                              "w-3 h-3 rounded-full",
                              direction === 'Bullish' ? "bg-green-500" : "bg-yellow-500"
                            )} />
                            <span className="font-medium text-gray-900">{pattern.symbol}</span>
                            <span className="text-sm text-gray-500 capitalize">{pattern.type?.replace('_', ' ') || 'order_block'}</span>
                            <span className={cn(
                              "px-2 py-1 text-xs font-medium rounded",
                              direction === 'Bullish' 
                                ? "bg-green-100 text-green-800" 
                                : "bg-red-100 text-red-800"
                            )}>
                              {direction}
                            </span>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium text-gray-900">
                              ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </div>
                            <div className="text-xs text-gray-500">1H</div>
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center space-x-4">
                            <span className="text-gray-500">Confidence:</span>
                            <div className="flex items-center space-x-2">
                              <div className="w-20 bg-gray-200 rounded-full h-2">
                                <div 
                                  className="bg-blue-600 h-2 rounded-full" 
                                  style={{ width: `${confidence * 100}%` }}
                                />
                              </div>
                              <span className="text-gray-900">{(confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                          <span className="text-gray-500">{detectedTime}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Order Management Panel */}
        <div className="space-y-6">
          {/* Place Order */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Place Order</h3>
            </div>
            <div className="p-6 space-y-4">
              {/* Order Side */}
              <div className="flex space-x-2">
                <button
                  onClick={() => setOrderSide('BUY')}
                  className={cn(
                    "flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors",
                    orderSide === 'BUY'
                      ? "bg-green-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  )}
                >
                  <TrendingUp className="h-4 w-4 inline mr-1" />
                  BUY
                </button>
                <button
                  onClick={() => setOrderSide('SELL')}
                  className={cn(
                    "flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors",
                    orderSide === 'SELL'
                      ? "bg-red-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  )}
                >
                  <TrendingDown className="h-4 w-4 inline mr-1" />
                  SELL
                </button>
              </div>

              {/* Order Type */}
              <div className="flex space-x-2">
                <button
                  onClick={() => setOrderType('MARKET')}
                  className={cn(
                    "flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors",
                    orderType === 'MARKET'
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  )}
                >
                  Market
                </button>
                <button
                  onClick={() => setOrderType('LIMIT')}
                  className={cn(
                    "flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors",
                    orderType === 'LIMIT'
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  )}
                >
                  Limit
                </button>
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantity
                </label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
              </div>

              {/* Price (for limit orders) */}
              {orderType === 'LIMIT' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Price
                  </label>
                  <input
                    type="number"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="0.00"
                  />
                </div>
              )}

              {/* Stop Loss */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Stop Loss
                </label>
                <input
                  type="number"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Optional"
                />
              </div>

              {/* Take Profit */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Take Profit
                </label>
                <input
                  type="number"
                  value={takeProfit}
                  onChange={(e) => setTakeProfit(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Optional"
                />
              </div>

              {/* Error message */}
              {orderError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
                  {orderError}
                </div>
              )}

              {/* Place Order Button */}
              <button
                onClick={handlePlaceOrder}
                disabled={orderLoading || !quantity || !price}
                className={cn(
                  "w-full py-3 px-4 text-sm font-medium rounded-md transition-colors",
                  orderLoading || !quantity || !price
                    ? "bg-gray-400 cursor-not-allowed text-white"
                    : orderSide === 'BUY'
                    ? "bg-green-600 hover:bg-green-700 text-white"
                    : "bg-red-600 hover:bg-red-700 text-white"
                )}
              >
                {orderLoading ? 'Placing Order...' : `Place ${orderSide} Order`}
              </button>
            </div>
          </div>

          {/* Recent Orders */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Recent Orders</h3>
            </div>
            <div className="p-6">
              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading orders...</div>
              ) : recentOrders.length === 0 ? (
                <div className="text-center py-8 text-gray-500">No recent orders</div>
              ) : (
                <div className="space-y-3">
                  {recentOrders.map((order) => (
                  <div key={order.id} className="border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium">{order.symbol}</span>
                        <span className={cn(
                          "px-2 py-1 text-xs font-medium rounded",
                          order.side === 'BUY' 
                            ? "bg-green-100 text-green-800" 
                            : "bg-red-100 text-red-800"
                        )}>
                          {order.side}
                        </span>
                        <span className="text-xs text-gray-500">{order.type}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        {order.status === 'FILLED' ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : order.status === 'PENDING' ? (
                          <Clock className="h-4 w-4 text-yellow-500" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-xs text-gray-500">{order.status}</span>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 space-y-1">
                      <div>Qty: {order.size}</div>
                      {order.price && <div>Price: ${order.price.toLocaleString()}</div>}
                      {order.pnl !== undefined && (
                        <div className={cn(
                          order.pnl >= 0 ? "text-green-600" : "text-red-600"
                        )}>
                          P&L: ${order.pnl.toFixed(2)}
                        </div>
                      )}
                      <div>Time: {new Date(order.timestamp).toLocaleTimeString()}</div>
                      {order.reason && <div className="text-gray-400 italic">{order.reason}</div>}
                    </div>
                  </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}