import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  Eye,
  Settings,
  Trash2,
  Activity,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Zap,
  BarChart3,
  Shield,
  Cpu,
  HardDrive,
  Network,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface Agent {
  id: string;
  name: string;
  type: 'smc_detector' | 'decision_engine' | 'execution_engine' | 'risk_manager';
  status: 'running' | 'stopped' | 'error' | 'starting' | 'stopping';
  symbol: string;
  timeframe: string;
  capital: number;
  currentPnL: number;
  totalTrades: number;
  winRate: number;
  uptime: string;
  lastActivity: string;
  latency: string;
  memoryUsage: number;
  cpuUsage: number;
  networkUsage: number;
  errorCount: number;
  paperTrading: boolean;
  strategies: string[];
  startTime: string;
}

interface AgentStatusDashboardProps {
  className?: string;
  onAgentAction?: (action: string, agentId: string) => void;
  onViewDetails?: (agentId: string) => void;
  onConfigureAgent?: (agentId: string) => void;
}

const statusColors = {
  running: 'bg-green-100 text-green-800',
  stopped: 'bg-gray-100 text-gray-800',
  error: 'bg-red-100 text-red-800',
  starting: 'bg-blue-100 text-blue-800',
  stopping: 'bg-yellow-100 text-yellow-800'
};

const statusIcons = {
  running: CheckCircle,
  stopped: Square,
  error: XCircle,
  starting: Loader2,
  stopping: AlertTriangle
};

const agentTypeIcons = {
  smc_detector: BarChart3,
  decision_engine: TrendingUp,
  execution_engine: Zap,
  risk_manager: Shield
};

const agentTypeLabels = {
  smc_detector: 'SMC Detector',
  decision_engine: 'ML Decision Engine',
  execution_engine: 'Executor',
  risk_manager: 'Risk Manager'
};

export default function AgentStatusDashboard({
  className,
  onAgentAction,
  onViewDetails,
  onConfigureAgent
}: AgentStatusDashboardProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(2000);

  const fetchAgents = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getAgents();
      setAgents(data);
    } catch (error) {
      console.error('Failed to fetch agents:', error);
      // Use demo data as fallback
      setAgents([
        {
          id: 'agent_1',
          name: 'BTC_SMC_Agent_v1',
          type: 'smc_detector',
          status: 'running',
          symbol: 'BTCUSDT',
          timeframe: '5m',
          capital: 10000,
          currentPnL: 245.50,
          totalTrades: 47,
          winRate: 68.5,
          uptime: '2h 34m',
          lastActivity: '2 seconds ago',
          latency: '12ms',
          memoryUsage: 65,
          cpuUsage: 23,
          networkUsage: 15,
          errorCount: 0,
          paperTrading: true,
          strategies: ['Order Block Trading', 'Liquidity Sweep'],
          startTime: '2024-01-20T10:30:00Z'
        },
        {
          id: 'agent_2',
          name: 'ETH_ML_Engine_v2',
          type: 'decision_engine',
          status: 'running',
          symbol: 'ETHUSDT',
          timeframe: '15m',
          capital: 15000,
          currentPnL: -123.75,
          totalTrades: 32,
          winRate: 71.9,
          uptime: '1h 12m',
          lastActivity: '5 seconds ago',
          latency: '8ms',
          memoryUsage: 78,
          cpuUsage: 45,
          networkUsage: 22,
          errorCount: 2,
          paperTrading: true,
          strategies: ['Breakout Trading', 'Mean Reversion'],
          startTime: '2024-01-20T11:45:00Z'
        }
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();

    if (autoRefresh) {
      const interval = setInterval(fetchAgents, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchAgents, autoRefresh, refreshInterval]);

  const handleAgentAction = async (action: string, agentId: string) => {
    try {
      await apiService.controlAgent(agentId, action);
      onAgentAction?.(action, agentId);
      fetchAgents(); // Refresh after action
    } catch (error) {
      console.error(`Failed to ${action} agent ${agentId}:`, error);
    }
  };

  const getStatusBadge = (status: Agent['status']) => {
    const StatusIcon = statusIcons[status];
    return (
      <Badge className={cn(statusColors[status], 'flex items-center space-x-1')}>
        <StatusIcon className={cn('h-3 w-3', status === 'starting' && 'animate-spin')} />
        <span className="capitalize">{status}</span>
      </Badge>
    );
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  };

  const formatPercentage = (num: number) => `${num.toFixed(1)}%`;

  if (loading && agents.length === 0) {
    return (
      <Card className={cn('p-8', className)}>
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <span className="ml-2 text-lg">Loading agents...</span>
        </div>
      </Card>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-blue-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">Total Agents</p>
                <p className="text-2xl font-bold">{agents.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">Running</p>
                <p className="text-2xl font-bold text-green-600">
                  {agents.filter(a => a.status === 'running').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <DollarSign className="h-5 w-5 text-yellow-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">Total P&L</p>
                <p className={cn(
                  'text-2xl font-bold',
                  agents.reduce((sum, a) => sum + a.currentPnL, 0) >= 0 ? 'text-green-600' : 'text-red-600'
                )}>
                  ${formatNumber(agents.reduce((sum, a) => sum + a.currentPnL, 0))}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              <div>
                <p className="text-sm font-medium text-gray-600">Errors</p>
                <p className="text-2xl font-bold text-red-600">
                  {agents.reduce((sum, a) => sum + a.errorCount, 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-semibold">Active Agents</h3>
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="auto-refresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300"
            />
            <label htmlFor="auto-refresh" className="text-sm text-gray-600">
              Auto-refresh ({refreshInterval / 1000}s)
            </label>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchAgents()}
            disabled={loading}
          >
            <RotateCcw className={cn('h-4 w-4 mr-1', loading && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {agents.map((agent) => {
          const TypeIcon = agentTypeIcons[agent.type];
          const isSelected = selectedAgent === agent.id;

          return (
            <Card
              key={agent.id}
              className={cn(
                'transition-all hover:shadow-md',
                isSelected && 'ring-2 ring-blue-500'
              )}
              onClick={() => setSelectedAgent(isSelected ? null : agent.id)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <TypeIcon className="h-5 w-5 text-gray-600" />
                    <div>
                      <CardTitle className="text-base">{agent.name}</CardTitle>
                      <CardDescription className="text-xs">
                        {agentTypeLabels[agent.type]} • {agent.symbol} • {agent.timeframe}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(agent.status)}
                    {agent.paperTrading && (
                      <Badge variant="outline" className="text-xs">Paper</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Performance Metrics */}
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div className="p-2 bg-gray-50 rounded">
                    <div className="text-xs text-gray-600">P&L</div>
                    <div className={cn(
                      'text-sm font-semibold',
                      agent.currentPnL >= 0 ? 'text-green-600' : 'text-red-600'
                    )}>
                      ${formatNumber(agent.currentPnL)}
                    </div>
                  </div>
                  <div className="p-2 bg-gray-50 rounded">
                    <div className="text-xs text-gray-600">Trades</div>
                    <div className="text-sm font-semibold">{agent.totalTrades}</div>
                  </div>
                  <div className="p-2 bg-gray-50 rounded">
                    <div className="text-xs text-gray-600">Win Rate</div>
                    <div className="text-sm font-semibold">{formatPercentage(agent.winRate)}</div>
                  </div>
                  <div className="p-2 bg-gray-50 rounded">
                    <div className="text-xs text-gray-600">Uptime</div>
                    <div className="text-sm font-semibold">{agent.uptime}</div>
                  </div>
                </div>

                {/* System Resources */}
                {isSelected && (
                  <div className="space-y-3 pt-3 border-t">
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div className="flex items-center space-x-2">
                        <Cpu className="h-4 w-4 text-blue-500" />
                        <span>CPU: {agent.cpuUsage}%</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <HardDrive className="h-4 w-4 text-green-500" />
                        <span>Memory: {agent.memoryUsage}%</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Network className="h-4 w-4 text-purple-500" />
                        <span>Net: {agent.networkUsage}%</span>
                      </div>
                    </div>

                    <div className="text-sm text-gray-600">
                      <div className="flex justify-between mb-1">
                        <span>Latency:</span>
                        <span className="font-medium">{agent.latency}</span>
                      </div>
                      <div className="flex justify-between mb-1">
                        <span>Last Activity:</span>
                        <span className="font-medium">{agent.lastActivity}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Started:</span>
                        <span className="font-medium">
                          {new Date(agent.startTime).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {agent.strategies.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {agent.strategies.map((strategy, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {strategy}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {agent.errorCount > 0 && (
                      <div className="bg-red-50 border border-red-200 rounded p-2 text-sm text-red-700">
                        <div className="flex items-center space-x-1">
                          <AlertTriangle className="h-4 w-4" />
                          <span>{agent.errorCount} errors reported</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center space-x-2 pt-2">
                  {agent.status === 'running' ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentAction('pause', agent.id);
                      }}
                    >
                      <Pause className="h-4 w-4 mr-1" />
                      Pause
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAgentAction('start', agent.id);
                      }}
                    >
                      <Play className="h-4 w-4 mr-1" />
                      Start
                    </Button>
                  )}

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAgentAction('restart', agent.id);
                    }}
                  >
                    <RotateCcw className="h-4 w-4 mr-1" />
                    Restart
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewDetails?.(agent.id);
                    }}
                  >
                    <Eye className="h-4 w-4 mr-1" />
                    Details
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onConfigureAgent?.(agent.id);
                    }}
                  >
                    <Settings className="h-4 w-4 mr-1" />
                    Config
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAgentAction('stop', agent.id);
                    }}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Stop
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {agents.length === 0 && !loading && (
        <Card>
          <CardContent className="p-12 text-center">
            <div className="text-gray-500">
              <Activity className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium mb-2">No active agents</h3>
              <p className="text-sm">Spawn your first trading agent to get started.</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}