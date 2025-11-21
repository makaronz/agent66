import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectItem } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart
} from 'recharts';
import {
  Plus,
  TrendingUp,
  TrendingDown,
  Settings,
  Play,
  Pause,
  RefreshCw,
  Info,
  AlertTriangle,
  CheckCircle,
  Clock,
  Target,
  Shield,
  Zap,
  BarChart3,
  Layers,
  Timer,
  Waves,
  Activity,
  DollarSign,
  Percent,
  ArrowUpRight,
  ArrowDownRight,
  Minus
} from 'lucide-react';
import { apiService } from '@/services/api';
import { cn } from '@/lib/utils';

interface AdvancedOrderTypesProps {
  className?: string;
  selectedSymbol?: string;
}

interface BracketOrder {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  entryPrice: number;
  quantity: number;
  stopLoss: number;
  takeProfit: number;
  trailingStop?: boolean;
  trailingDistance?: number;
  status: 'active' | 'filled' | 'cancelled' | 'partial';
  filledQuantity?: number;
  averageFillPrice?: number;
  realizedPnL?: number;
  createdAt: string;
  updatedAt: string;
}

interface IcebergOrder {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  totalQuantity: number;
  displayedQuantity: number;
  limitPrice?: number;
  randomization?: number;
  status: 'active' | 'filled' | 'cancelled' | 'partial';
  filledQuantity: number;
  executedLegs: number;
  totalLegs: number;
  averageFillPrice?: number;
  createdAt: string;
  updatedAt: string;
}

interface TWAPVWAPOrder {
  id: string;
  type: 'TWAP' | 'VWAP';
  symbol: string;
  side: 'BUY' | 'SELL';
  totalQuantity: number;
  startTime: string;
  endTime: string;
  participationRate?: number;
  limitPrice?: number;
  status: 'active' | 'completed' | 'cancelled' | 'paused';
  filledQuantity: number;
  averageFillPrice?: number;
  remainingQuantity: number;
  executions: Array<{
    time: string;
    quantity: number;
    price: number;
  }>;
  createdAt: string;
  updatedAt: string;
}

interface SmartPosition {
  symbol: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
  riskScore: 'LOW' | 'MEDIUM' | 'HIGH';
  stopLoss: number;
  takeProfit: number;
  trailingStop: boolean;
  positionSizing: 'fixed' | 'dynamic' | 'kelly';
  riskPercentage: number;
  maxDrawdown: number;
  sharpeRatio: number;
  lastAdjustment: string;
}

const orderTypeDescriptions = {
  bracket: {
    title: 'Dynamic Bracket Orders',
    description: 'Automatically manage stop loss and take profit levels with AI-driven adjustments',
    icon: Shield,
    color: 'blue'
  },
  iceberg: {
    title: 'Iceberg Orders',
    description: 'Execute large positions by breaking them into smaller, hidden orders',
    icon: Layers,
    color: 'purple'
  },
  twap_vwap: {
    title: 'TWAP/VWAP Algorithms',
    description: 'Time-weighted and volume-weighted average price execution strategies',
    icon: Timer,
    color: 'green'
  },
  smart_sizing: {
    title: 'Smart Position Sizing',
    description: 'AI-powered position sizing based on real-time risk assessment',
    icon: BarChart3,
    color: 'orange'
  }
};

export default function AdvancedOrderTypes({
  className,
  selectedSymbol = 'BTCUSDT'
}: AdvancedOrderTypesProps) {
  const [activeTab, setActiveTab] = useState('bracket');
  const [bracketOrders, setBracketOrders] = useState<BracketOrder[]>([]);
  const [icebergOrders, setIcebergOrders] = useState<IcebergOrder[]>([]);
  const [twapVwapOrders, setTwapVwapOrders] = useState<TWAPVWAPOrder[]>([]);
  const [smartPositions, setSmartPositions] = useState<SmartPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewOrderDialog, setShowNewOrderDialog] = useState(false);
  const [newOrderType, setNewOrderType] = useState<'bracket' | 'iceberg' | 'twap_vwap'>('bracket');

  // Form states for different order types
  const [bracketForm, setBracketForm] = useState({
    side: 'BUY' as 'BUY' | 'SELL',
    quantity: '',
    entryPrice: '',
    stopLoss: '',
    takeProfit: '',
    trailingStop: false,
    trailingDistance: ''
  });

  const [icebergForm, setIcebergForm] = useState({
    side: 'BUY' as 'BUY' | 'SELL',
    totalQuantity: '',
    displayedQuantity: '',
    limitPrice: '',
    randomization: '20'
  });

  const [twapVwapForm, setTwapVwapForm] = useState({
    type: 'TWAP' as 'TWAP' | 'VWAP',
    side: 'BUY' as 'BUY' | 'SELL',
    totalQuantity: '',
    startTime: '',
    endTime: '',
    participationRate: '10',
    limitPrice: ''
  });

  useEffect(() => {
    fetchAdvancedOrders();
    fetchSmartPositions();
  }, [selectedSymbol]);

  const fetchAdvancedOrders = async () => {
    try {
      setLoading(true);
      // Mock data for now - replace with actual API calls
      setBracketOrders(generateMockBracketOrders());
      setIcebergOrders(generateMockIcebergOrders());
      setTwapVwapOrders(generateMockTWAPVWAPOrders());
    } catch (error) {
      console.error('Failed to fetch advanced orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSmartPositions = async () => {
    try {
      // Mock smart positions data
      setSmartPositions(generateMockSmartPositions());
    } catch (error) {
      console.error('Failed to fetch smart positions:', error);
    }
  };

  const generateMockBracketOrders = (): BracketOrder[] => {
    return [
      {
        id: 'bracket_1',
        symbol: selectedSymbol,
        side: 'BUY',
        entryPrice: 43250,
        quantity: 0.1,
        stopLoss: 42800,
        takeProfit: 44500,
        trailingStop: true,
        trailingDistance: 500,
        status: 'active',
        createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        updatedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString()
      },
      {
        id: 'bracket_2',
        symbol: selectedSymbol,
        side: 'SELL',
        entryPrice: 44100,
        quantity: 0.15,
        stopLoss: 44500,
        takeProfit: 42500,
        status: 'filled',
        filledQuantity: 0.15,
        averageFillPrice: 44085,
        realizedPnL: 2250,
        createdAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
        updatedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString()
      }
    ];
  };

  const generateMockIcebergOrders = (): IcebergOrder[] => {
    return [
      {
        id: 'iceberg_1',
        symbol: selectedSymbol,
        side: 'BUY',
        totalQuantity: 2.5,
        displayedQuantity: 0.1,
        randomization: 20,
        status: 'active',
        filledQuantity: 1.2,
        executedLegs: 12,
        totalLegs: 25,
        averageFillPrice: 43120,
        createdAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
        updatedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString()
      }
    ];
  };

  const generateMockTWAPVWAPOrders = (): TWAPVWAPOrder[] => {
    const now = new Date();
    const startTime = new Date(now.getTime() - 2 * 60 * 60 * 1000);
    const endTime = new Date(now.getTime() + 2 * 60 * 60 * 1000);

    return [
      {
        id: 'twap_1',
        type: 'TWAP',
        symbol: selectedSymbol,
        side: 'SELL',
        totalQuantity: 1.0,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        limitPrice: 44000,
        status: 'active',
        filledQuantity: 0.35,
        averageFillPrice: 43250,
        remainingQuantity: 0.65,
        executions: [
          { time: new Date(now.getTime() - 90 * 60 * 1000).toISOString(), quantity: 0.15, price: 43300 },
          { time: new Date(now.getTime() - 60 * 60 * 1000).toISOString(), quantity: 0.1, price: 43280 },
          { time: new Date(now.getTime() - 30 * 60 * 1000).toISOString(), quantity: 0.1, price: 43220 }
        ],
        createdAt: startTime.toISOString(),
        updatedAt: new Date(now.getTime() - 5 * 60 * 1000).toISOString()
      }
    ];
  };

  const generateMockSmartPositions = (): SmartPosition[] => {
    return [
      {
        symbol: selectedSymbol,
        side: 'LONG',
        size: 0.25,
        entryPrice: 42800,
        currentPrice: 43250,
        unrealizedPnL: 112.5,
        unrealizedPnLPercent: 1.05,
        riskScore: 'MEDIUM',
        stopLoss: 42400,
        takeProfit: 44500,
        trailingStop: false,
        positionSizing: 'dynamic',
        riskPercentage: 2.5,
        maxDrawdown: 5.2,
        sharpeRatio: 1.8,
        lastAdjustment: new Date(Date.now() - 30 * 60 * 1000).toISOString()
      }
    ];
  };

  const handlePlaceBracketOrder = async () => {
    try {
      // Simulate API call
      const newOrder: BracketOrder = {
        id: `bracket_${Date.now()}`,
        symbol: selectedSymbol,
        side: bracketForm.side,
        entryPrice: parseFloat(bracketForm.entryPrice),
        quantity: parseFloat(bracketForm.quantity),
        stopLoss: parseFloat(bracketForm.stopLoss),
        takeProfit: parseFloat(bracketForm.takeProfit),
        trailingStop: bracketForm.trailingStop,
        trailingDistance: bracketForm.trailingDistance ? parseFloat(bracketForm.trailingDistance) : undefined,
        status: 'active',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };

      setBracketOrders(prev => [newOrder, ...prev]);
      setShowNewOrderDialog(false);

      // Reset form
      setBracketForm({
        side: 'BUY',
        quantity: '',
        entryPrice: '',
        stopLoss: '',
        takeProfit: '',
        trailingStop: false,
        trailingDistance: ''
      });

    } catch (error) {
      console.error('Failed to place bracket order:', error);
    }
  };

  const handleCancelOrder = async (orderId: string, orderType: 'bracket' | 'iceberg' | 'twap_vwap') => {
    try {
      // Update order status in local state
      if (orderType === 'bracket') {
        setBracketOrders(prev => prev.map(order =>
          order.id === orderId ? { ...order, status: 'cancelled' as const } : order
        ));
      } else if (orderType === 'iceberg') {
        setIcebergOrders(prev => prev.map(order =>
          order.id === orderId ? { ...order, status: 'cancelled' as const } : order
        ));
      } else if (orderType === 'twap_vwap') {
        setTwapVwapOrders(prev => prev.map(order =>
          order.id === orderId ? { ...order, status: 'cancelled' as const } : order
        ));
      }
    } catch (error) {
      console.error('Failed to cancel order:', error);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      active: { label: 'Active', color: 'green' },
      filled: { label: 'Filled', color: 'blue' },
      cancelled: { label: 'Cancelled', color: 'red' },
      partial: { label: 'Partial', color: 'yellow' },
      completed: { label: 'Completed', color: 'blue' },
      paused: { label: 'Paused', color: 'orange' }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || { label: status, color: 'gray' };

    return (
      <Badge variant={config.color as any} className="capitalize">
        {config.label}
      </Badge>
    );
  };

  const getExecutionProgress = (order: TWAPVWAPOrder) => {
    const progress = (order.filledQuantity / order.totalQuantity) * 100;
    return progress;
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Advanced Order Types</h2>
          <p className="text-gray-600">AI-powered execution strategies and smart position management</p>
        </div>

        <Dialog open={showNewOrderDialog} onOpenChange={setShowNewOrderDialog}>
          <DialogTrigger asChild>
            <Button onClick={() => setNewOrderType('bracket')}>
              <Plus className="h-4 w-4 mr-2" />
              New Advanced Order
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create Advanced Order</DialogTitle>
              <DialogDescription>
                Configure sophisticated order types with AI-driven optimization
              </DialogDescription>
            </DialogHeader>

            <Tabs value={newOrderType} onValueChange={(value) => setNewOrderType(value as any)}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="bracket">Bracket</TabsTrigger>
                <TabsTrigger value="iceberg">Iceberg</TabsTrigger>
                <TabsTrigger value="twap_vwap">TWAP/VWAP</TabsTrigger>
              </TabsList>

              <TabsContent value="bracket" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Side</Label>
                    <Select value={bracketForm.side} onValueChange={(value) =>
                      setBracketForm(prev => ({ ...prev, side: value as 'BUY' | 'SELL' }))
                    }>
                      <SelectItem value="BUY">BUY</SelectItem>
                      <SelectItem value="SELL">SELL</SelectItem>
                    </Select>
                  </div>
                  <div>
                    <Label>Quantity</Label>
                    <Input
                      type="number"
                      value={bracketForm.quantity}
                      onChange={(e) => setBracketForm(prev => ({ ...prev, quantity: e.target.value }))}
                      placeholder="0.00"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Entry Price</Label>
                    <Input
                      type="number"
                      value={bracketForm.entryPrice}
                      onChange={(e) => setBracketForm(prev => ({ ...prev, entryPrice: e.target.value }))}
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <Label>Stop Loss</Label>
                    <Input
                      type="number"
                      value={bracketForm.stopLoss}
                      onChange={(e) => setBracketForm(prev => ({ ...prev, stopLoss: e.target.value }))}
                      placeholder="0.00"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Take Profit</Label>
                    <Input
                      type="number"
                      value={bracketForm.takeProfit}
                      onChange={(e) => setBracketForm(prev => ({ ...prev, takeProfit: e.target.value }))}
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <Label>Trailing Distance (optional)</Label>
                    <Input
                      type="number"
                      value={bracketForm.trailingDistance}
                      onChange={(e) => setBracketForm(prev => ({ ...prev, trailingDistance: e.target.value }))}
                      placeholder="500"
                      disabled={!bracketForm.trailingStop}
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="trailing-stop"
                    checked={bracketForm.trailingStop}
                    onCheckedChange={(checked) =>
                      setBracketForm(prev => ({ ...prev, trailingStop: checked as boolean }))
                    }
                  />
                  <Label htmlFor="trailing-stop">Enable Trailing Stop</Label>
                </div>
              </TabsContent>

              {/* Additional tabs content would go here */}

            </Tabs>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowNewOrderDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handlePlaceBracketOrder}>
                Place Order
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Order Types Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Object.entries(orderTypeDescriptions).map(([key, desc]) => {
          const Icon = desc.icon;
          return (
            <Card key={key} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center space-x-3">
                  <div className={cn(
                    'p-2 rounded-lg',
                    key === 'bracket' ? 'bg-blue-100' :
                    key === 'iceberg' ? 'bg-purple-100' :
                    key === 'twap_vwap' ? 'bg-green-100' :
                    'bg-orange-100'
                  )}>
                    <Icon className={cn(
                      'h-5 w-5',
                      key === 'bracket' ? 'text-blue-600' :
                      key === 'iceberg' ? 'text-purple-600' :
                      key === 'twap_vwap' ? 'text-green-600' :
                      'text-orange-600'
                    )} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{desc.title}</h3>
                    <p className="text-xs text-gray-600">{desc.description}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="bracket">Bracket Orders</TabsTrigger>
          <TabsTrigger value="iceberg">Iceberg Orders</TabsTrigger>
          <TabsTrigger value="twap_vwap">TWAP/VWAP</TabsTrigger>
          <TabsTrigger value="smart_positions">Smart Positions</TabsTrigger>
        </TabsList>

        {/* Bracket Orders */}
        <TabsContent value="bracket" className="space-y-4">
          <div className="grid gap-4">
            {bracketOrders.map((order) => (
              <Card key={order.id}>
                <CardContent className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center space-x-3">
                      <Shield className="h-5 w-5 text-blue-500" />
                      <div>
                        <h3 className="font-semibold">{order.symbol}</h3>
                        <div className="flex items-center space-x-2">
                          <Badge variant={order.side === 'BUY' ? 'green' : 'red'}>
                            {order.side}
                          </Badge>
                          {getStatusBadge(order.status)}
                          {order.trailingStop && (
                            <Badge variant="outline">Trailing</Badge>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {order.status === 'active' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelOrder(order.id, 'bracket')}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div>
                      <Label className="text-xs text-gray-600">Entry</Label>
                      <div className="font-semibold">{formatCurrency(order.entryPrice)}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Stop Loss</Label>
                      <div className="font-semibold text-red-600">{formatCurrency(order.stopLoss)}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Take Profit</Label>
                      <div className="font-semibold text-green-600">{formatCurrency(order.takeProfit)}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Quantity</Label>
                      <div className="font-semibold">{order.quantity}</div>
                    </div>
                  </div>

                  {order.realizedPnL !== undefined && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Realized P&L:</span>
                        <span className={cn(
                          'font-semibold',
                          order.realizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {formatCurrency(order.realizedPnL)}
                        </span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}

            {bracketOrders.length === 0 && (
              <Card>
                <CardContent className="p-12 text-center">
                  <Shield className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium mb-2">No Bracket Orders</h3>
                  <p className="text-sm text-gray-500">Create your first bracket order to automatically manage risk.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Iceberg Orders */}
        <TabsContent value="iceberg" className="space-y-4">
          <div className="grid gap-4">
            {icebergOrders.map((order) => (
              <Card key={order.id}>
                <CardContent className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center space-x-3">
                      <Layers className="h-5 w-5 text-purple-500" />
                      <div>
                        <h3 className="font-semibold">{order.symbol}</h3>
                        <div className="flex items-center space-x-2">
                          <Badge variant={order.side === 'BUY' ? 'green' : 'red'}>
                            {order.side}
                          </Badge>
                          {getStatusBadge(order.status)}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {order.status === 'active' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelOrder(order.id, 'iceberg')}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                    <div>
                      <Label className="text-xs text-gray-600">Total Quantity</Label>
                      <div className="font-semibold">{order.totalQuantity}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Displayed</Label>
                      <div className="font-semibold">{order.displayedQuantity}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Filled</Label>
                      <div className="font-semibold">{order.filledQuantity}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Progress</Label>
                      <div className="font-semibold">
                        {((order.filledQuantity / order.totalQuantity) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(order.filledQuantity / order.totalQuantity) * 100}%` }}
                    />
                  </div>

                  {order.averageFillPrice && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Average Fill Price:</span>
                        <span className="font-semibold">{formatCurrency(order.averageFillPrice)}</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}

            {icebergOrders.length === 0 && (
              <Card>
                <CardContent className="p-12 text-center">
                  <Layers className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium mb-2">No Iceberg Orders</h3>
                  <p className="text-sm text-gray-500">Execute large positions without revealing your full size.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* TWAP/VWAP Orders */}
        <TabsContent value="twap_vwap" className="space-y-4">
          <div className="grid gap-4">
            {twapVwapOrders.map((order) => (
              <Card key={order.id}>
                <CardContent className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center space-x-3">
                      <Timer className="h-5 w-5 text-green-500" />
                      <div>
                        <h3 className="font-semibold">{order.type} - {order.symbol}</h3>
                        <div className="flex items-center space-x-2">
                          <Badge variant={order.side === 'BUY' ? 'green' : 'red'}>
                            {order.side}
                          </Badge>
                          {getStatusBadge(order.status)}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {order.status === 'active' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelOrder(order.id, 'twap_vwap')}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                    <div>
                      <Label className="text-xs text-gray-600">Total Quantity</Label>
                      <div className="font-semibold">{order.totalQuantity}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Filled</Label>
                      <div className="font-semibold">{order.filledQuantity}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Remaining</Label>
                      <div className="font-semibold">{order.remainingQuantity}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Progress</Label>
                      <div className="font-semibold">{getExecutionProgress(order).toFixed(1)}%</div>
                    </div>
                  </div>

                  <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                    <div
                      className="bg-green-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${getExecutionProgress(order)}%` }}
                    />
                  </div>

                  {order.executions.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-xs text-gray-600">Recent Executions</Label>
                      <div className="space-y-1">
                        {order.executions.slice(-3).reverse().map((execution, index) => (
                          <div key={index} className="flex justify-between text-sm">
                            <span className="text-gray-600">
                              {new Date(execution.time).toLocaleTimeString()}
                            </span>
                            <span>{execution.quantity} @ {formatCurrency(execution.price)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {order.averageFillPrice && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Average Fill Price:</span>
                        <span className="font-semibold">{formatCurrency(order.averageFillPrice)}</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}

            {twapVwapOrders.length === 0 && (
              <Card>
                <CardContent className="p-12 text-center">
                  <Timer className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium mb-2">No TWAP/VWAP Orders</h3>
                  <p className="text-sm text-gray-500">Execute large orders over time with minimal market impact.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Smart Positions */}
        <TabsContent value="smart_positions" className="space-y-4">
          <div className="grid gap-4">
            {smartPositions.map((position, index) => (
              <Card key={index}>
                <CardContent className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center space-x-3">
                      <BarChart3 className="h-5 w-5 text-orange-500" />
                      <div>
                        <h3 className="font-semibold">{position.symbol}</h3>
                        <div className="flex items-center space-x-2">
                          <Badge variant={position.side === 'LONG' ? 'green' : 'red'}>
                            {position.side}
                          </Badge>
                          <Badge variant={position.riskScore === 'LOW' ? 'green' :
                                       position.riskScore === 'MEDIUM' ? 'yellow' : 'red'}>
                            {position.riskScore} Risk
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                    <div>
                      <Label className="text-xs text-gray-600">Position Size</Label>
                      <div className="font-semibold">{position.size}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Entry Price</Label>
                      <div className="font-semibold">{formatCurrency(position.entryPrice)}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Current Price</Label>
                      <div className="font-semibold">{formatCurrency(position.currentPrice)}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Unrealized P&L</Label>
                      <div className={cn(
                        'font-semibold',
                        position.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        {formatCurrency(position.unrealizedPnL)} ({formatPercent(position.unrealizedPnLPercent)})
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                    <div>
                      <Label className="text-xs text-gray-600">Stop Loss</Label>
                      <div className="font-semibold text-red-600">{formatCurrency(position.stopLoss)}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Take Profit</Label>
                      <div className="font-semibold text-green-600">{formatCurrency(position.takeProfit)}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Position Sizing</Label>
                      <div className="font-semibold capitalize">{position.positionSizing}</div>
                    </div>
                    <div>
                      <Label className="text-xs text-gray-600">Risk %</Label>
                      <div className="font-semibold">{formatPercent(position.riskPercentage)}</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t">
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center space-x-1">
                        <Activity className="h-4 w-4" />
                        <span>Sharpe: {position.sharpeRatio.toFixed(2)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <TrendingDown className="h-4 w-4" />
                        <span>Max DD: {formatPercent(position.maxDrawdown)}</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {position.trailingStop && (
                        <Badge variant="outline">Trailing Stop</Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {smartPositions.length === 0 && (
              <Card>
                <CardContent className="p-12 text-center">
                  <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium mb-2">No Smart Positions</h3>
                  <p className="text-sm text-gray-500">AI-driven position sizing will appear here when positions are active.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}