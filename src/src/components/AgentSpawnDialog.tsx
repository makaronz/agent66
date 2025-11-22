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
import { AlertCircle, CheckCircle, Loader2, Play, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface AgentConfig {
  id: string;
  name: string;
  type: 'smc_detector' | 'decision_engine' | 'execution_engine' | 'risk_manager';
  symbol: string;
  timeframe: string;
  capital: number;
  leverage: number;
  strategies: string[];
  riskLevel: 'conservative' | 'moderate' | 'aggressive';
  paperTrading: boolean;
  maxDrawdown: number;
  dailyLossLimit: number;
}

interface AgentSpawnDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAgentSpawned?: (agent: AgentConfig) => void;
}

const agentTypes = [
  { value: 'smc_detector', label: 'SMC Pattern Detector', description: 'Detects Smart Money Concepts patterns' },
  { value: 'decision_engine', label: 'ML Decision Engine', description: 'AI-powered trading decisions' },
  { value: 'execution_engine', label: 'Ultra-Low Latency Executor', description: 'Fast order execution (<50ms)' },
  { value: 'risk_manager', label: 'Risk Manager', description: 'Real-time risk monitoring' }
];

const timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d'];
const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'LINKUSDT'];
const strategies = ['Order Block Trading', 'Liquidity Sweep', 'FVG Trading', 'Breakout Trading', 'Mean Reversion'];

export default function AgentSpawnDialog({ open, onOpenChange, onAgentSpawned }: AgentSpawnDialogProps) {
  const [config, setConfig] = useState<Partial<AgentConfig>>({
    name: '',
    type: 'smc_detector',
    symbol: 'BTCUSDT',
    timeframe: '5m',
    capital: 10000,
    leverage: 1,
    strategies: [],
    riskLevel: 'moderate',
    paperTrading: true,
    maxDrawdown: 5,
    dailyLossLimit: 500
  });

  const [validating, setValidating] = useState(false);
  const [spawning, setSpawning] = useState(false);
  const [validation, setValidation] = useState<{
    isValid: boolean;
    errors: string[];
    warnings: string[];
  }>({ isValid: false, errors: [], warnings: [] });

  const [previewMode, setPreviewMode] = useState(false);
  const [resourceEstimate, setResourceEstimate] = useState<{
    cpu: string;
    memory: string;
    network: string;
    latency: string;
  } | null>(null);

  useEffect(() => {
    if (open && config.type) {
      validateConfig();
      estimateResources();
    }
  }, [config, open]);

  const validateConfig = async () => {
    setValidating(true);
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!config.name?.trim()) {
      errors.push('Agent name is required');
    }

    if (!config.type) {
      errors.push('Agent type is required');
    }

    if (config.capital && config.capital < 100) {
      errors.push('Minimum capital is $100');
    }

    if (config.leverage && config.leverage > 100) {
      errors.push('Leverage cannot exceed 100x');
    }

    if (config.maxDrawdown && config.maxDrawdown > 50) {
      warnings.push('High maximum drawdown threshold detected');
    }

    if (config.dailyLossLimit && config.dailyLossLimit > config.capital! * 0.2) {
      warnings.push('Daily loss limit exceeds 20% of capital');
    }

    setValidation({
      isValid: errors.length === 0,
      errors,
      warnings
    });

    setValidating(false);
  };

  const estimateResources = async () => {
    if (!config.type) return;

    // Simulate resource estimation based on agent type and configuration
    const estimates = {
      smc_detector: { cpu: '2-4 cores', memory: '4-8 GB', network: '10 Mbps', latency: '<10ms' },
      decision_engine: { cpu: '4-8 cores', memory: '8-16 GB', network: '50 Mbps', latency: '<5ms' },
      execution_engine: { cpu: '2-4 cores', memory: '2-4 GB', network: '100 Mbps', latency: '<1ms' },
      risk_manager: { cpu: '1-2 cores', memory: '2-4 GB', network: '5 Mbps', latency: '<20ms' }
    };

    setResourceEstimate(estimates[config.type as keyof typeof estimates]);
  };

  const handleSpawn = async () => {
    if (!validation.isValid || !config.name || !config.type) return;

    setSpawning(true);
    try {
      const agentData = {
        ...config,
        id: `agent_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      } as AgentConfig;

      // Call API to spawn agent
      await apiService.spawnAgent(agentData);

      onAgentSpawned?.(agentData);
      onOpenChange(false);

      // Reset form
      setConfig({
        name: '',
        type: 'smc_detector',
        symbol: 'BTCUSDT',
        timeframe: '5m',
        capital: 10000,
        leverage: 1,
        strategies: [],
        riskLevel: 'moderate',
        paperTrading: true,
        maxDrawdown: 5,
        dailyLossLimit: 500
      });
    } catch (error) {
      console.error('Failed to spawn agent:', error);
      // Handle error - could show a toast notification
    } finally {
      setSpawning(false);
    }
  };

  const handleStrategyToggle = (strategy: string, checked: boolean) => {
    setConfig(prev => ({
      ...prev,
      strategies: checked
        ? [...(prev.strategies || []), strategy]
        : prev.strategies?.filter(s => s !== strategy)
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Play className="h-5 w-5" />
            <span>Spawn New Trading Agent</span>
          </DialogTitle>
          <DialogDescription>
            Configure and launch a new automated trading agent with real-time monitoring capabilities.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Basic Configuration */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Agent Name</Label>
              <Input
                id="agent-name"
                value={config.name}
                onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., BTC_SMC_Agent_v1"
                className={cn(validation.errors.some(e => e.includes('name')) && 'border-red-500')}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="agent-type">Agent Type</Label>
              <Select value={config.type} onValueChange={(value) => setConfig(prev => ({ ...prev, type: value as any }))}>
                  {agentTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                  ))}
                </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Trading Symbol</Label>
                <Select value={config.symbol} onValueChange={(value) => setConfig(prev => ({ ...prev, symbol: value }))}>
                    {symbols.map((symbol) => (
                      <SelectItem key={symbol} value={symbol}>{symbol}</SelectItem>
                    ))}
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="timeframe">Timeframe</Label>
                <Select value={config.timeframe} onValueChange={(value) => setConfig(prev => ({ ...prev, timeframe: value }))}>
                    {timeframes.map((timeframe) => (
                      <SelectItem key={timeframe} value={timeframe}>{timeframe}</SelectItem>
                    ))}
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="capital">Initial Capital ($)</Label>
              <Input
                id="capital"
                type="number"
                value={config.capital}
                onChange={(e) => setConfig(prev => ({ ...prev, capital: parseFloat(e.target.value) || 0 }))}
                min="100"
                step="100"
                className={cn(validation.errors.some(e => e.includes('capital')) && 'border-red-500')}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="leverage">Leverage (x)</Label>
              <Input
                id="leverage"
                type="number"
                value={config.leverage}
                onChange={(e) => setConfig(prev => ({ ...prev, leverage: parseFloat(e.target.value) || 1 }))}
                min="1"
                max="100"
                step="0.1"
                className={cn(validation.errors.some(e => e.includes('leverage')) && 'border-red-500')}
              />
            </div>
          </div>

          {/* Risk & Strategy Configuration */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Risk Level</Label>
              <Select value={config.riskLevel} onValueChange={(value) => setConfig(prev => ({ ...prev, riskLevel: value as any }))}>
                  <SelectItem value="conservative">Conservative (Low risk, low returns)</SelectItem>
                  <SelectItem value="moderate">Moderate (Balanced risk/returns)</SelectItem>
                  <SelectItem value="aggressive">Aggressive (High risk, high returns)</SelectItem>
                </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="max-drawdown">Max Drawdown (%)</Label>
                <Input
                  id="max-drawdown"
                  type="number"
                  value={config.maxDrawdown}
                  onChange={(e) => setConfig(prev => ({ ...prev, maxDrawdown: parseFloat(e.target.value) || 0 }))}
                  min="1"
                  max="50"
                  step="0.5"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="daily-loss">Daily Loss Limit ($)</Label>
                <Input
                  id="daily-loss"
                  type="number"
                  value={config.dailyLossLimit}
                  onChange={(e) => setConfig(prev => ({ ...prev, dailyLossLimit: parseFloat(e.target.value) || 0 }))}
                  min="10"
                  step="10"
                />
              </div>
            </div>

            <div className="space-y-3">
              <Label>Trading Strategies</Label>
              <div className="space-y-2 max-h-32 overflow-y-auto border rounded-md p-3">
                {strategies.map((strategy) => (
                  <div key={strategy} className="flex items-center space-x-2">
                    <Checkbox
                      id={strategy}
                      checked={config.strategies?.includes(strategy) || false}
                      onCheckedChange={(checked) => handleStrategyToggle(strategy, checked as boolean)}
                    />
                    <Label htmlFor={strategy} className="text-sm font-normal">{strategy}</Label>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="paper-trading"
                checked={config.paperTrading}
                onCheckedChange={(checked) => setConfig(prev => ({ ...prev, paperTrading: checked as boolean }))}
              />
              <Label htmlFor="paper-trading">Paper Trading Mode (No real money)</Label>
            </div>

            {/* Resource Estimate */}
            {resourceEstimate && (
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <h4 className="font-medium text-blue-900 mb-2 flex items-center space-x-2">
                  <Settings className="h-4 w-4" />
                  <span>Resource Requirements</span>
                </h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-blue-700">CPU:</span>
                    <span className="text-blue-900 font-medium">{resourceEstimate.cpu}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-700">Memory:</span>
                    <span className="text-blue-900 font-medium">{resourceEstimate.memory}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-700">Network:</span>
                    <span className="text-blue-900 font-medium">{resourceEstimate.network}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-700">Latency:</span>
                    <span className="text-blue-900 font-medium">{resourceEstimate.latency}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Validation Messages */}
        {validation.errors.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-900">Configuration Errors</h4>
                <ul className="mt-2 text-sm text-red-700 list-disc list-inside">
                  {validation.errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {validation.warnings.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
              <div>
                <h4 className="font-medium text-yellow-900">Warnings</h4>
                <ul className="mt-2 text-sm text-yellow-700 list-disc list-inside">
                  {validation.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={spawning}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSpawn}
            disabled={!validation.isValid || spawning || validating}
            className="min-w-[120px]"
          >
            {spawning ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Spawning...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Spawn Agent
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}