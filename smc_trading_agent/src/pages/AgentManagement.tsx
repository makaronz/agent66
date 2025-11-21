import { useState, useEffect } from 'react';
import {
  Plus,
  Activity,
  Users,
  Settings,
  Download,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import AgentStatusDashboard from '@/components/AgentStatusDashboard';
import AgentSpawnDialog from '@/components/AgentSpawnDialog';
import RealTimeAgentLogs from '@/components/RealTimeAgentLogs';
import AgentConfigDialog from '@/components/AgentConfigDialog';
import AgentPerformanceMonitor from '@/components/AgentPerformanceMonitor';
import { apiService, type Agent } from '@/services/api';
import { websocketService } from '@/services/websocket';

export default function AgentManagement() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showSpawnDialog, setShowSpawnDialog] = useState(false);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [configAgent, setConfigAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    total: 0,
    running: 0,
    stopped: 0,
    error: 0,
    totalPnL: 0
  });

  useEffect(() => {
    fetchAgents();
    setupWebSocketSubscriptions();

    return () => {
      cleanupWebSocketSubscriptions();
    };
  }, []);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getAgents();
      setAgents(data);
      updateStats(data);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
      setError('Failed to load agents. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const setupWebSocketSubscriptions = () => {
    try {
      // Connect to WebSocket for real-time updates
      websocketService.connect().catch(error => {
        console.log('WebSocket connection failed, falling back to polling');
      });

      // Subscribe to agent updates
      const unsubscribeAgentUpdates = websocketService.subscribeToAllAgents((updates) => {
        setAgents(prev => {
          const updatedAgents = [...prev];
          updates.forEach(update => {
            const index = updatedAgents.findIndex(a => a.id === update.agentId);
            if (index !== -1) {
              updatedAgents[index] = {
                ...updatedAgents[index],
                status: update.status,
                ...update.metrics,
                ...update.performance
              };
            }
          });
          return updatedAgents;
        });
      });

      return () => {
        unsubscribeAgentUpdates();
      };
    } catch (error) {
      console.error('Failed to setup WebSocket subscriptions:', error);
    }
  };

  const cleanupWebSocketSubscriptions = () => {
    try {
      websocketService.disconnect();
    } catch (error) {
      console.error('Failed to cleanup WebSocket subscriptions:', error);
    }
  };

  const updateStats = (agentData: Agent[]) => {
    setStats({
      total: agentData.length,
      running: agentData.filter(a => a.status === 'running').length,
      stopped: agentData.filter(a => a.status === 'stopped').length,
      error: agentData.filter(a => a.status === 'error').length,
      totalPnL: agentData.reduce((sum, a) => sum + a.currentPnL, 0)
    });
  };

  const handleAgentAction = async (action: string, agentId: string) => {
    try {
      await apiService.controlAgent(agentId, action);
      fetchAgents(); // Refresh data after action
    } catch (error) {
      console.error(`Failed to ${action} agent:`, error);
      // Show error toast notification here
    }
  };

  const handleAgentSpawned = (agent: Agent) => {
    setAgents(prev => [...prev, agent]);
    updateStats([...agents, agent]);
  };

  const handleViewDetails = (agentId: string) => {
    const agent = agents.find(a => a.id === agentId);
    setSelectedAgent(agent);
  };

  const handleConfigureAgent = (agentId: string) => {
    const agent = agents.find(a => a.id === agentId);
    setConfigAgent(agent);
    setShowConfigDialog(true);
  };

  const handleExportAgentData = () => {
    const agentData = agents.map(agent => ({
      id: agent.id,
      name: agent.name,
      type: agent.type,
      status: agent.status,
      symbol: agent.symbol,
      timeframe: agent.timeframe,
      capital: agent.capital,
      currentPnL: agent.currentPnL,
      totalTrades: agent.totalTrades,
      winRate: agent.winRate,
      uptime: agent.uptime,
      paperTrading: agent.paperTrading
    }));

    const csv = [
      Object.keys(agentData[0]).join(','),
      ...agentData.map(agent => Object.values(agent).map(v => `"${v}"`).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agents-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && agents.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="text-lg">Loading agents...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Management</h1>
          <p className="text-gray-600">Spawn, monitor, and manage your trading agents</p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            onClick={handleExportAgentData}
            disabled={agents.length === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export Data
          </Button>

          <Button onClick={() => setShowSpawnDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Spawn Agent
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <div>
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <Users className="h-8 w-8 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Total Agents</p>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <Activity className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Running</p>
              <p className="text-2xl font-bold text-green-600">{stats.running}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <Settings className="h-8 w-8 text-gray-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Stopped</p>
              <p className="text-2xl font-bold text-gray-600">{stats.stopped}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <AlertTriangle className="h-8 w-8 text-red-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Errors</p>
              <p className="text-2xl font-bold text-red-600">{stats.error}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <Users className="h-8 w-8 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Total P&L</p>
              <p className={`text-2xl font-bold ${stats.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${stats.totalPnL.toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="agents" className="space-y-6">
        <TabsList>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="logs">Real-time Logs</TabsTrigger>
          <TabsTrigger value="monitoring">System Monitoring</TabsTrigger>
        </TabsList>

        <TabsContent value="agents" className="space-y-6">
          <AgentStatusDashboard
            onAgentAction={handleAgentAction}
            onViewDetails={handleViewDetails}
            onConfigureAgent={handleConfigureAgent}
          />
        </TabsContent>

        <TabsContent value="performance" className="space-y-6">
          {selectedAgent ? (
            <AgentPerformanceMonitor agent={selectedAgent} />
          ) : (
            <div className="text-center py-12 bg-gray-50 rounded-lg">
              <Activity className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium mb-2">Select an Agent</h3>
              <p className="text-sm text-gray-500">Choose an agent from the Agents tab to view detailed performance metrics.</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <RealTimeAgentLogs
            agentId={selectedAgent?.id || undefined}
            compact={false}
          />
        </TabsContent>

        <TabsContent value="monitoring" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* System Health */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">System Health</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">WebSocket Connection</span>
                  <span className="text-sm font-medium text-green-600">Connected</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">API Response Time</span>
                  <span className="text-sm font-medium text-blue-600">12ms</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">System Uptime</span>
                  <span className="text-sm font-medium text-gray-900">2h 34m</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Memory Usage</span>
                  <span className="text-sm font-medium text-yellow-600">78%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">CPU Usage</span>
                  <span className="text-sm font-medium text-green-600">45%</span>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
              <div className="space-y-3">
                <div className="text-sm">
                  <span className="text-gray-500">2 min ago</span>
                  <p className="text-gray-900">BTC_SMC_Agent_v1 detected new order block</p>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">5 min ago</span>
                  <p className="text-gray-900">ETH_ML_Engine_v2 executed trade (+$45.20)</p>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">12 min ago</span>
                  <p className="text-gray-900">Risk Manager adjusted stop loss for BTC position</p>
                </div>
                <div className="text-sm">
                  <span className="text-gray-500">18 min ago</span>
                  <p className="text-gray-900">System backup completed successfully</p>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Spawn Agent Dialog */}
      <AgentSpawnDialog
        open={showSpawnDialog}
        onOpenChange={setShowSpawnDialog}
        onAgentSpawned={handleAgentSpawned}
      />

      {/* Agent Configuration Dialog */}
      <AgentConfigDialog
        open={showConfigDialog}
        onOpenChange={setShowConfigDialog}
        agent={configAgent}
        onConfigUpdated={(updatedAgent) => {
          // Update the agent in the list
          setAgents(prev => prev.map(a => a.id === updatedAgent.id ? updatedAgent : a));
          if (selectedAgent?.id === updatedAgent.id) {
            setSelectedAgent(updatedAgent);
          }
        }}
      />
    </div>
  );
}