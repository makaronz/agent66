import { useState } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import {
  TrendingUp,
  TrendingDown,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  Loader2
} from 'lucide-react';
import { cn } from '../utils';
import { useAuthContext } from '../contexts/AuthContext';

// Mock SMC patterns data
const mockSMCPatterns = [
  {
    id: 1,
    symbol: 'BTCUSDT',
    type: 'Order Block',
    direction: 'Bullish',
    confidence: 0.85,
    priceLevel: 42800,
    timeframe: '1H',
    detected: '2 min ago',
    status: 'active'
  },
  {
    id: 2,
    symbol: 'ETHUSDT',
    type: 'CHoCH',
    direction: 'Bearish',
    confidence: 0.72,
    priceLevel: 2680,
    timeframe: '4H',
    detected: '5 min ago',
    status: 'triggered'
  },
  {
    id: 3,
    symbol: 'ADAUSDT',
    type: 'Liquidity Sweep',
    direction: 'Bullish',
    confidence: 0.91,
    priceLevel: 0.485,
    timeframe: '15M',
    detected: '1 min ago',
    status: 'active'
  }
];

const mockOrders = [
  {
    id: 'ORD001',
    symbol: 'BTCUSDT',
    side: 'BUY',
    type: 'LIMIT',
    quantity: 0.5,
    price: 42800,
    status: 'FILLED',
    fillPrice: 42805,
    timestamp: '10:30:45'
  },
  {
    id: 'ORD002',
    symbol: 'ETHUSDT',
    side: 'SELL',
    type: 'MARKET',
    quantity: 2.0,
    price: null,
    status: 'PENDING',
    fillPrice: null,
    timestamp: '10:32:12'
  }
];

// Types for order data and API responses
interface OrderData {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  quantity: number;
  price?: number;
  stopLoss?: number;
  takeProfit?: number;
}

interface OrderResponse {
  success: boolean;
  orderId?: string;
  message?: string;
  error?: string;
}

export default function TradingInterface() {
  const { user } = useAuthContext();
  const isAuthenticated = !!user;
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('LIMIT');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [autoTrading, setAutoTrading] = useState(false);
  const [isPlacingOrder, setIsPlacingOrder] = useState(false);

  const handlePlaceOrder = async () => {
    // Authentication check
    if (!user) {
      toast.error('Please log in to place orders');
      return;
    }

    // Form validation
    if (!quantity || parseFloat(quantity) <= 0) {
      toast.error('Please enter a valid quantity');
      return;
    }

    if (orderType === 'LIMIT' && (!price || parseFloat(price) <= 0)) {
      toast.error('Please enter a valid price for limit orders');
      return;
    }

    // Prevent multiple submissions
    if (isPlacingOrder) {
      return;
    }

    setIsPlacingOrder(true);

    try {
      // Prepare order data
      const orderData: OrderData = {
        symbol: selectedSymbol,
        side: orderSide,
        type: orderType,
        quantity: parseFloat(quantity),
      };

      // Add price for limit orders
      if (orderType === 'LIMIT' && price) {
        orderData.price = parseFloat(price);
      }

      // Add optional stop loss and take profit
      if (stopLoss && parseFloat(stopLoss) > 0) {
        orderData.stopLoss = parseFloat(stopLoss);
      }

      if (takeProfit && parseFloat(takeProfit) > 0) {
        orderData.takeProfit = parseFloat(takeProfit);
      }

      // Make API call to place order
      const response = await axios.post<OrderResponse>('/api/binance/place-order', orderData, {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 30000, // 30 second timeout
      });

      if (response.data.success) {
        // Success handling
        toast.success(`${orderSide} order placed successfully! Order ID: ${response.data.orderId}`);
        
        // Clear form fields after successful order placement
        setQuantity('');
        setPrice('');
        setStopLoss('');
        setTakeProfit('');
        
        // TODO: Update recent orders list with new order
        console.log('Order placed successfully:', response.data);
      } else {
        // Handle API error response
        toast.error(response.data.message || response.data.error || 'Failed to place order');
      }
    } catch (error) {
      // Comprehensive error handling
      console.error('Order placement error:', error);
      
      if (axios.isAxiosError(error)) {
        if (error.response) {
          // Server responded with error status
          const errorMessage = error.response.data?.message || error.response.data?.error || 'Server error occurred';
          toast.error(`Order failed: ${errorMessage}`);
        } else if (error.request) {
          // Network error
          toast.error('Network error: Unable to connect to trading server');
        } else {
          // Request setup error
          toast.error('Request error: Failed to send order');
        }
      } else {
        // Non-Axios error
        toast.error('Unexpected error occurred while placing order');
      }
    } finally {
      setIsPlacingOrder(false);
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
              onClick={() => { setAutoTrading(!autoTrading); }}
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
                  onChange={(e) => { setSelectedSymbol(e.target.value); }}
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
              <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                <div className="text-center">
                  <BarChart3 className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">TradingView Chart Integration</p>
                  <p className="text-sm text-gray-400">Real-time {selectedSymbol} chart with SMC overlays</p>
                </div>
              </div>
            </div>
          </div>

          {/* Detected Patterns */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Detected SMC Patterns</h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {mockSMCPatterns.map((pattern) => (
                  <div key={pattern.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-3">
                        <div className={cn(
                          "w-3 h-3 rounded-full",
                          pattern.status === 'active' ? "bg-green-500" : "bg-yellow-500"
                        )} />
                        <span className="font-medium text-gray-900">{pattern.symbol}</span>
                        <span className="text-sm text-gray-500">{pattern.type}</span>
                        <span className={cn(
                          "px-2 py-1 text-xs font-medium rounded",
                          pattern.direction === 'Bullish' 
                            ? "bg-green-100 text-green-800" 
                            : "bg-red-100 text-red-800"
                        )}>
                          {pattern.direction}
                        </span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium text-gray-900">
                          ${pattern.priceLevel.toLocaleString()}
                        </div>
                        <div className="text-xs text-gray-500">{pattern.timeframe}</div>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center space-x-4">
                        <span className="text-gray-500">Confidence:</span>
                        <div className="flex items-center space-x-2">
                          <div className="w-20 bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full" 
                              style={{ width: `${pattern.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-gray-900">{(pattern.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                      <span className="text-gray-500">{pattern.detected}</span>
                    </div>
                  </div>
                ))}
              </div>
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
                  onClick={() => { setOrderSide('BUY'); }}
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
                  onClick={() => { setOrderSide('SELL'); }}
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
                  onClick={() => { setOrderType('MARKET'); }}
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
                  onClick={() => { setOrderType('LIMIT'); }}
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
                  onChange={(e) => { setQuantity(e.target.value); }}
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
                    onChange={(e) => { setPrice(e.target.value); }}
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
                  onChange={(e) => { setStopLoss(e.target.value); }}
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
                  onChange={(e) => { setTakeProfit(e.target.value); }}                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Optional"
                />
              </div>

              {/* Place Order Button */}
              <button
                onClick={handlePlaceOrder}
                disabled={isPlacingOrder || !isAuthenticated}
                className={cn(
                  "w-full py-3 px-4 text-sm font-medium rounded-md transition-colors flex items-center justify-center space-x-2",
                  isPlacingOrder || !isAuthenticated
                    ? "bg-gray-400 cursor-not-allowed text-white"
                    : orderSide === 'BUY'
                    ? "bg-green-600 hover:bg-green-700 text-white"
                    : "bg-red-600 hover:bg-red-700 text-white"
                )}
              >
                {isPlacingOrder && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>
                  {isPlacingOrder 
                    ? 'Placing Order...' 
                    : !isAuthenticated 
                    ? 'Login Required' 
                    : `Place ${orderSide} Order`
                  }
                </span>
              </button>
            </div>
          </div>

          {/* Recent Orders */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Recent Orders</h3>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {mockOrders.map((order) => (
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
                      <div>Qty: {order.quantity}</div>
                      {order.price && <div>Price: ${order.price.toLocaleString()}</div>}
                      {order.fillPrice && <div>Fill: ${order.fillPrice.toLocaleString()}</div>}
                      <div>Time: {order.timestamp}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}