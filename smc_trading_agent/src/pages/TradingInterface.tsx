import { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  Settings
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService, type SMCPattern, type Trade, type OHLCVData } from '@/services/api';
import AdvancedOrderTypes from '@/components/AdvancedOrderTypes';
import CandlestickChart from '@/components/CandlestickChart';
import { Button } from '@/components/ui/button';

export default function TradingInterface() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('LIMIT');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [autoTrading, setAutoTrading] = useState(false);
  const [showAdvancedOrders, setShowAdvancedOrders] = useState(false);

  // Real data from API
  const [smcPatterns, setSmcPatterns] = useState<SMCPattern[]>([]);
  const [recentOrders, setRecentOrders] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [orderLoading, setOrderLoading] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState('1h');

  // Fetch SMC patterns and recent orders
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [patterns, orders] = await Promise.all([
          apiService.getSMCPatterns(),
          apiService.getTradingHistory(10, selectedSymbol)
        ]);
        setSmcPatterns(patterns);
        setRecentOrders(orders);
      } catch (error) {
        console.error('Error fetching trading data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh patterns every 30 seconds, orders every 10 seconds
    const patternsInterval = setInterval(() => {
      apiService.getSMCPatterns().then(setSmcPatterns).catch(console.error);
    }, 30000);

    const ordersInterval = setInterval(() => {
      apiService.getTradingHistory(10, selectedSymbol).then(setRecentOrders).catch(console.error);
    }, 10000);

    return () => {
      clearInterval(patternsInterval);
      clearInterval(ordersInterval);
    };
  }, [selectedSymbol]);

  const handlePlaceOrder = async () => {
    if (!quantity || (orderType === 'LIMIT' && !price)) {
      setOrderError('Please fill in quantity and price');
      return;
    }

    setOrderLoading(true);
    setOrderError(null);

    try {
      const trade = await apiService.executeTrade({
        symbol: selectedSymbol,
        action: orderSide,
        price: orderType === 'MARKET' ? 0 : parseFloat(price),
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
          <Button
            variant={showAdvancedOrders ? "default" : "outline"}
            size="sm"
            onClick={() => setShowAdvancedOrders(!showAdvancedOrders)}
          >
            <Settings className="h-4 w-4 mr-2" />
            {showAdvancedOrders ? 'Basic Orders' : 'Advanced Orders'}
          </Button>

          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Auto Trading</span>
            <button
              onClick={() => setAutoTrading(!autoTrading)}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                autoTrading ? "bg-green-600" : "bg-gray-200"
              )}
              aria-label="Toggle auto trading"
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
          {/* Chart */}
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
              <CandlestickChart
                symbol={selectedSymbol}
                timeframe={timeframe}
                height={384}
                showVolume={true}
                showGrid={true}
                autoRefresh={true}
                className="mt-4"
              />
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
                    const direction = pattern.direction?.toLowerCase() === 'bullish' ? 'Bullish' : 'Bearish';
                    const price = pattern.price || 0;
                    const confidence = pattern.confidence || pattern.strength || 0;
                    const detectedTime = pattern.timestamp
                      ? new Date(pattern.timestamp).toLocaleString()
                      : 'Just now';

                    return (
                      <div
                        key={pattern.id}
                        className={cn(
                          "p-4 rounded-lg border",
                          direction === 'Bullish'
                            ? "bg-green-50 border-green-200"
                            : "bg-red-50 border-red-200"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <div className={cn(
                              "w-3 h-3 rounded-full",
                              direction === 'Bullish' ? "bg-green-500" : "bg-red-500"
                            )} />
                            <div>
                              <div className="font-medium text-gray-900">
                                {pattern.type?.replace('_', ' ') || 'Unknown Pattern'}
                              </div>
                              <div className="text-sm text-gray-600">
                                {direction} • ${price.toFixed(2)}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium text-gray-900">
                              {confidence.toFixed(1)}% Confidence
                            </div>
                            <div className="text-xs text-gray-500">
                              {detectedTime}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Trading Panel */}
        <div className="space-y-6">
          {/* Order Form */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Place Order</h3>
            </div>
            <div className="p-6 space-y-4">
              {/* Order Side */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Order Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setOrderSide('BUY')}
                    className={cn(
                      "px-4 py-2 text-sm font-medium rounded-md transition-colors",
                      orderSide === 'BUY'
                        ? "bg-green-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    )}
                  >
                    Buy
                  </button>
                  <button
                    onClick={() => setOrderSide('SELL')}
                    className={cn(
                      "px-4 py-2 text-sm font-medium rounded-md transition-colors",
                      orderSide === 'SELL'
                        ? "bg-red-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    )}
                  >
                    Sell
                  </button>
                </div>
              </div>

              {/* Order Execution Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Execution Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setOrderType('MARKET')}
                    className={cn(
                      "px-4 py-2 text-sm font-medium rounded-md transition-colors",
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
                      "px-4 py-2 text-sm font-medium rounded-md transition-colors",
                      orderType === 'LIMIT'
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    )}
                  >
                    Limit
                  </button>
                </div>
              </div>

              {/* Price (only for limit orders) */}
              {orderType === 'LIMIT' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Price (USDT)
                  </label>
                  <input
                    type="number"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter price"
                  />
                </div>
              )}

              {/* Quantity */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity
                </label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter quantity"
                />
              </div>

              {/* Stop Loss and Take Profit */}
              {showAdvancedOrders && (
                <div className="space-y-3 pt-3 border-t border-gray-200">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Stop Loss (optional)
                    </label>
                    <input
                      type="number"
                      value={stopLoss}
                      onChange={(e) => setStopLoss(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Stop loss price"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Take Profit (optional)
                    </label>
                    <input
                      type="number"
                      value={takeProfit}
                      onChange={(e) => setTakeProfit(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Take profit price"
                    />
                  </div>
                </div>
              )}

              {/* Error Display */}
              {orderError && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <p className="text-sm text-red-600">{orderError}</p>
                </div>
              )}

              {/* Submit Button */}
              <button
                onClick={handlePlaceOrder}
                disabled={orderLoading}
                className={cn(
                  "w-full flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md transition-colors",
                  orderLoading
                    ? "bg-gray-400 text-white cursor-not-allowed"
                    : orderSide === 'BUY'
                    ? "bg-green-600 hover:bg-green-700 text-white"
                    : "bg-red-600 hover:bg-red-700 text-white"
                )}
              >
                {orderLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Placing Order...
                  </>
                ) : (
                  `${orderSide} ${selectedSymbol.replace('USDT', '/USDT')}`
                )}
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
                  {recentOrders.map((order) => {
                    const isProfit = order.pnl && order.pnl > 0;
                    return (
                      <div
                        key={order.id}
                        className={cn(
                          "p-3 rounded-lg border",
                          order.action === 'BUY'
                            ? "bg-green-50 border-green-200"
                            : "bg-red-50 border-red-200"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-gray-900">
                              {order.action} {order.symbol}
                            </div>
                            <div className="text-sm text-gray-600">
                              {order.size} @ ${order.price}
                            </div>
                          </div>
                          <div className="text-right">
                            {order.pnl !== undefined && (
                              <div className={cn(
                                "text-sm font-medium",
                                isProfit ? "text-green-600" : "text-red-600"
                              )}>
                                {isProfit ? '+' : ''}{order.pnl.toFixed(2)}
                              </div>
                            )}
                            <div className="text-xs text-gray-500">
                              {new Date(order.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Orders Modal */}
      {showAdvancedOrders && (
        <AdvancedOrderTypes
          onClose={() => setShowAdvancedOrders(false)}
        />
      )}
    </div>
  );
}