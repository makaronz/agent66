import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectItem } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Settings,
  AlertTriangle,
  CheckCircle,
  Info,
  TrendingUp,
  Shield,
  Zap,
  BarChart3,
  Brain,
  Activity,
  DollarSign,
  Clock,
  Target
} from 'lucide-react';
import { apiService, type Agent, type AgentConfig } from '@/services/api';
import { cn } from '@/lib/utils';

interface AgentConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent: Agent | null;
  onConfigUpdated?: (agent: Agent) => void;
}

const agentTypeDescriptions = {
  smc_detector: {
    title: 'Smart Money Concepts Detector',
    description: 'Identifies market structure patterns, order blocks, and liquidity zones',
    icon: BarChart3,
    color: 'blue',
    defaultStrategies: ['Order Block Trading', 'Breakout Trading', 'Liquidity Sweep']
  },
  decision_engine: {
    title: 'ML Decision Engine',
    description: 'Uses ensemble models to analyze signals and make trading decisions',
    icon: Brain,
    color: 'purple',
    defaultStrategies: ['Trend Following', 'Mean Reversion', 'Volatility Trading']
  },
  execution_engine: {
    title: 'Ultra-Low Latency Executor',
    description: 'Optimizes order execution with minimal slippage and market impact',
    icon: Zap,
    color: 'yellow',
    defaultStrategies: ['Market Making', 'Arbitrage', 'Statistical Arbitrage']
  },
  risk_manager: {
    title: 'Risk Management Guardian',
    description: 'Monitors and manages portfolio risk with dynamic position sizing',
    icon: Shield,
    color: 'green',
    defaultStrategies: ['Portfolio Hedging', 'Dynamic Sizing', 'Circuit Breaker']
  }
};

const riskLevelConfig = {
  conservative: {
    maxDrawdown: 5,
    dailyLossLimit: 2,
    leverage: 2,
    positionSize: 0.02,
    color: 'green'
  },
  moderate: {
    maxDrawdown: 10,
    dailyLossLimit: 5,
    leverage: 5,
    positionSize: 0.05,
    color: 'yellow'
  },
  aggressive: {
    maxDrawdown: 20,
    dailyLossLimit: 10,
    leverage: 10,
    positionSize: 0.1,
    color: 'red'
  }
};

export default function AgentConfigDialog({
  open,
  onOpenChange,
  agent,
  onConfigUpdated
}: AgentConfigDialogProps) {
  const [config, setConfig] = useState<Partial<AgentConfig>>({
    name: '',
    symbol: 'BTCUSDT',
    timeframe: '5m',
    capital: 10000,
    leverage: 2,
    strategies: [],
    riskLevel: 'moderate',
    paperTrading: true,
    maxDrawdown: 10,
    dailyLossLimit: 5
  });

  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<{
    isValid: boolean;
    errors: string[];
    warnings: string[];
    resourceEstimate: any;
  } | null>(null);

  const [availableStrategies] = useState([
    'Order Block Trading',
    'Liquidity Sweep',
    'Breakout Trading',
    'Trend Following',
    'Mean Reversion',
    'Volatility Trading',
    'Market Making',
    'Arbitrage',
    'Statistical Arbitrage',
    'Portfolio Hedging',
    'Dynamic Sizing',
    'Circuit Breaker',
    'Scalping',
    'Swing Trading',
    'Position Trading'
  ]);

  const [symbols] = useState(['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'LINKUSDT']);
  const [timeframes] = useState(['1m', '5m', '15m', '30m', '1h', '4h', '1d']);

  useEffect(() => {
    if (agent && open) {
      setConfig({
        name: agent.name,
        symbol: agent.symbol,
        timeframe: agent.timeframe,
        capital: agent.capital,
        leverage: 2, // Default, not stored in agent
        strategies: agent.strategies || [],
        riskLevel: 'moderate', // Default, not stored in agent
        paperTrading: agent.paperTrading,
        maxDrawdown: 10, // Default, not stored in agent
        dailyLossLimit: 5 // Default, not stored in agent
      });
    } else if (open) {
      // Reset to defaults for new agent
      setConfig({
        name: '',
        symbol: 'BTCUSDT',
        timeframe: '5m',
        capital: 10000,
        leverage: 2,
        strategies: [],
        riskLevel: 'moderate',
        paperTrading: true,
        maxDrawdown: 10,
        dailyLossLimit: 5
      });
    }
  }, [agent, open]);

  useEffect(() => {
    if (config.riskLevel) {
      const riskConfig = riskLevelConfig[config.riskLevel];
      setConfig(prev => ({
        ...prev,
        maxDrawdown: riskConfig.maxDrawdown,
        dailyLossLimit: riskConfig.dailyLossLimit,
        leverage: riskConfig.leverage
      }));
    }
  }, [config.riskLevel]);

  const validateConfig = async () => {
    if (!config.name || !config.symbol || !config.timeframe) {
      setValidation({
        isValid: false,
        errors: ['Please fill in all required fields'],
        warnings: [],
        resourceEstimate: null
      });
      return;
    }

    try {
      setValidating(true);
      const validationData = await apiService.validateAgentConfig(config);
      setValidation(validationData);
    } catch (error) {
      console.error('Validation failed:', error);
      setValidation({
        isValid: false,
        errors: ['Validation service unavailable'],
        warnings: [],
        resourceEstimate: null
      });
    } finally {
      setValidating(false);
    }
  };

  useEffect(() => {
    if (open && (config.name || config.symbol || config.timeframe)) {
      validateConfig();
    }
  }, [config.name, config.symbol, config.timeframe, config.capital, config.riskLevel]);

  const handleSave = async () => {
    if (!validation?.isValid) {
      return;
    }

    setLoading(true);
    try {
      if (agent) {
        // Update existing agent
        const updatedAgent = await apiService.updateAgentConfig(agent.id, config);
        onConfigUpdated?.(updatedAgent);
      } else {
        // Spawn new agent
        await apiService.spawnAgent(config as AgentConfig);
      }
      onOpenChange(false);
    } catch (error: any) {
      console.error('Failed to save agent config:', error);
      // Show error notification
      alert(error.message || 'Failed to save agent configuration');
    } finally {
      setLoading(false);
    }
  };

  const toggleStrategy = (strategy: string) => {
    setConfig(prev => ({
      ...prev,
      strategies: prev.strategies?.includes(strategy)
        ? prev.strategies.filter(s => s !== strategy)
        : [...(prev.strategies || []), strategy]
    }));
  };

  const agentTypeInfo = agent ? agentTypeDescriptions[agent.type] : null;
  const isEditing = !!agent;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            {agentTypeInfo && <agentTypeInfo.icon className="h-5 w-5" />}
            <span>{isEditing ? 'Configure' : 'Spawn'} Agent</span>
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? `Modify configuration and settings for ${agent.name}`
              : 'Create a new intelligent trading agent with custom parameters'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 py-4">
          {/* Main Configuration */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Basic Configuration</CardTitle>
                <CardDescription>Essential agent parameters</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Agent Name</Label>
                    <Input
                      id="name"
                      value={config.name || ''}
                      onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="e.g., BTC_SMC_Agent_v1"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="symbol">Trading Symbol</Label>
                    <Select
                      value={config.symbol}
                      onValueChange={(value) => setConfig(prev => ({ ...prev, symbol: value }))}
                    >
                      {symbols.map(symbol => (
                        <SelectItem key={symbol} value={symbol}>{symbol}</SelectItem>
                      ))}
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="timeframe">Timeframe</Label>
                    <Select
                      value={config.timeframe}
                      onValueChange={(value) => setConfig(prev => ({ ...prev, timeframe: value }))}
                    >
                      {timeframes.map(timeframe => (
                        <SelectItem key={timeframe} value={timeframe}>{timeframe}</SelectItem>
                      ))}
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="riskLevel">Risk Level</Label>
                    <Select
                      value={config.riskLevel}
                      onValueChange={(value: 'conservative' | 'moderate' | 'aggressive') =>
                        setConfig(prev => ({ ...prev, riskLevel: value }))
                      }
                    >
                      <SelectItem value="conservative">Conservative</SelectItem>
                      <SelectItem value="moderate">Moderate</SelectItem>
                      <SelectItem value="aggressive">Aggressive</SelectItem>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="capital">Initial Capital ($)</Label>
                    <Input
                      id="capital"
                      type="number"
                      value={config.capital || ''}
                      onChange={(e) => setConfig(prev => ({ ...prev, capital: parseFloat(e.target.value) || 0 }))}
                      placeholder="10000"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="leverage">Leverage</Label>
                    <Input
                      id="leverage"
                      type="number"
                      value={config.leverage || ''}
                      onChange={(e) => setConfig(prev => ({ ...prev, leverage: parseFloat(e.target.value) || 1 }))}
                      placeholder="2"
                      min="1"
                      max="100"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="paperTrading"
                    checked={config.paperTrading || false}
                    onCheckedChange={(checked) =>
                      setConfig(prev => ({ ...prev, paperTrading: checked as boolean }))
                    }
                  />
                  <Label htmlFor="paperTrading">Paper Trading Mode (Simulated)</Label>
                </div>
              </CardContent>
            </Card>

            {/* Trading Strategies */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Trading Strategies</CardTitle>
                <CardDescription>Select strategies for this agent to implement</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {availableStrategies.map(strategy => (
                    <div
                      key={strategy}
                      className={cn(
                        "flex items-center space-x-2 p-3 rounded-lg border cursor-pointer transition-colors",
                        config.strategies?.includes(strategy)
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      )}
                      onClick={() => toggleStrategy(strategy)}
                    >
                      <Checkbox
                        checked={config.strategies?.includes(strategy) || false}
                        onChange={() => {}} // Handled by click
                      />
                      <span className="text-sm font-medium">{strategy}</span>
                    </div>
                  ))}
                </div>

                {agentTypeInfo && (
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-blue-800">
                      <strong>Recommended for {agentTypeInfo.title}:</strong> {agentTypeInfo.defaultStrategies.join(', ')}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Agent Type Info */}
            {agentTypeInfo && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <agentTypeInfo.icon className="h-5 w-5" />
                    <span className="text-lg">{agentTypeInfo.title}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600 mb-4">{agentTypeInfo.description}</p>

                  {isEditing && (
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2 text-sm">
                        <Activity className="h-4 w-4 text-gray-500" />
                        <span>Status: <Badge variant="outline">{agent.status}</Badge></span>
                      </div>
                      <div className="flex items-center space-x-2 text-sm">
                        <Clock className="h-4 w-4 text-gray-500" />
                        <span>Uptime: {agent.uptime}</span>
                      </div>
                      <div className="flex items-center space-x-2 text-sm">
                        <DollarSign className="h-4 w-4 text-gray-500" />
                        <span>Current P&L:
                          <span className={cn(
                            "ml-1 font-medium",
                            agent.currentPnL >= 0 ? "text-green-600" : "text-red-600"
                          )}>
                            ${agent.currentPnL.toFixed(2)}
                          </span>
                        </span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Risk Parameters */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Shield className="h-5 w-5" />
                  <span className="text-lg">Risk Parameters</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-gray-600">Max Drawdown</Label>
                    <div className="font-medium">{config.maxDrawdown}%</div>
                  </div>
                  <div>
                    <Label className="text-gray-600">Daily Loss Limit</Label>
                    <div className="font-medium">{config.dailyLossLimit}%</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <Label className="text-gray-600">Position Size</Label>
                    <div className="font-medium">
                      {((config.leverage || 1) * 0.02 * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <Label className="text-gray-600">Risk Score</Label>
                    <div className={cn(
                      "font-medium",
                      config.riskLevel === 'conservative' ? "text-green-600" :
                      config.riskLevel === 'moderate' ? "text-yellow-600" :
                      "text-red-600"
                    )}>
                      {config.riskLevel?.toUpperCase()}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Validation Status */}
            {validation && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    {validation.isValid ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-red-500" />
                    )}
                    <span className="text-lg">Validation</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {validation.errors.length > 0 && (
                    <div className="space-y-2 mb-4">
                      {validation.errors.map((error, index) => (
                        <div key={index} className="flex items-start space-x-2 text-sm text-red-600">
                          <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                          <span>{error}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {validation.warnings.length > 0 && (
                    <div className="space-y-2 mb-4">
                      {validation.warnings.map((warning, index) => (
                        <div key={index} className="flex items-start space-x-2 text-sm text-yellow-600">
                          <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                          <span>{warning}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {validation.resourceEstimate && (
                    <div className="text-sm space-y-2">
                      <Label>Estimated Resource Usage</Label>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>CPU: {validation.resourceEstimate.cpu}</div>
                        <div>Memory: {validation.resourceEstimate.memory}</div>
                        <div>Network: {validation.resourceEstimate.network}</div>
                        <div>Latency: {validation.resourceEstimate.latency}</div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!validation?.isValid || loading || validating}
          >
            {loading ? 'Saving...' : isEditing ? 'Update Agent' : 'Spawn Agent'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}