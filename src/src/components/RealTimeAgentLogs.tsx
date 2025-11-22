import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectItem } from '@/components/ui/select';
import {
  Download,
  RotateCcw,
  Pause,
  Play,
  Search,
  Filter,
  AlertTriangle,
  CheckCircle,
  Info,
  Zap,
  TrendingUp,
  TrendingDown,
  Clock,
  Trash2,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface LogEntry {
  id: string;
  agentId: string;
  agentName: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug' | 'trade';
  message: string;
  details?: Record<string, any>;
  category: 'system' | 'trading' | 'performance' | 'risk' | 'network';
}

interface RealTimeAgentLogsProps {
  agentId?: string;
  className?: string;
  maxHeight?: string;
  compact?: boolean;
}

const logLevelColors = {
  info: 'bg-blue-100 text-blue-800 border-blue-200',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  error: 'bg-red-100 text-red-800 border-red-200',
  debug: 'bg-gray-100 text-gray-800 border-gray-200',
  trade: 'bg-green-100 text-green-800 border-green-200'
};

const logLevelIcons = {
  info: Info,
  warning: AlertTriangle,
  error: AlertTriangle,
  debug: Info,
  trade: TrendingUp
};

const categoryColors = {
  system: 'text-gray-600',
  trading: 'text-blue-600',
  performance: 'text-purple-600',
  risk: 'text-red-600',
  network: 'text-green-600'
};

export default function RealTimeAgentLogs({
  agentId,
  className,
  maxHeight = '600px',
  compact = false
}: RealTimeAgentLogsProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [isMaximized, setIsMaximized] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getAgentLogs(agentId);
      setLogs(data);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
      // Use demo data as fallback
      const demoLogs: LogEntry[] = [
        {
          id: '1',
          agentId: 'agent_1',
          agentName: 'BTC_SMC_Agent_v1',
          timestamp: new Date().toISOString(),
          level: 'info',
          message: 'SMC pattern detector initialized successfully',
          category: 'system'
        },
        {
          id: '2',
          agentId: 'agent_1',
          agentName: 'BTC_SMC_Agent_v1',
          timestamp: new Date(Date.now() - 5000).toISOString(),
          level: 'trade',
          message: 'Order block detected at $43,250 - Bullish reversal potential',
          details: { price: 43250, volume: 1500000, confidence: 0.82 },
          category: 'trading'
        },
        {
          id: '3',
          agentId: 'agent_1',
          agentName: 'BTC_SMC_Agent_v1',
          timestamp: new Date(Date.now() - 10000).toISOString(),
          level: 'warning',
          message: 'High volatility detected - Risk parameters adjusted',
          category: 'risk'
        },
        {
          id: '4',
          agentId: 'agent_2',
          agentName: 'ETH_ML_Engine_v2',
          timestamp: new Date(Date.now() - 15000).toISOString(),
          level: 'error',
          message: 'API rate limit exceeded - Retrying in 5 seconds',
          category: 'network'
        }
      ];
      setLogs(demoLogs);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  const setupWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Simulate WebSocket connection for real-time updates
    const wsUrl = agentId
      ? `ws://localhost:3001/agent-logs/${agentId}`
      : 'ws://localhost:3001/agent-logs';

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Connected to agent logs WebSocket');
      };

      ws.onmessage = (event) => {
        if (!isPaused) {
          try {
            const newLog = JSON.parse(event.data);
            setLogs(prev => [newLog, ...prev].slice(0, 1000)); // Keep last 1000 logs
          } catch (error) {
            console.error('Failed to parse log message:', error);
          }
        }
      };

      ws.onclose = () => {
        console.log('Disconnected from agent logs WebSocket');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (!isPaused) {
            setupWebSocket();
          }
        }, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      // Fallback to polling
      const interval = setInterval(() => {
        if (!isPaused) {
          fetchLogs();
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [agentId, isPaused, fetchLogs]);

  useEffect(() => {
    fetchLogs();
    setupWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [fetchLogs, setupWebSocket]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter(log => {
    const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel;
    const matchesCategory = selectedCategory === 'all' || log.category === selectedCategory;
    const matchesSearch = searchTerm === '' ||
      log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.agentName.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesLevel && matchesCategory && matchesSearch;
  });

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleExportLogs = () => {
    const logText = filteredLogs.map(log =>
      `[${log.timestamp}] ${log.level.toUpperCase()} ${log.agentName}: ${log.message}`
    ).join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agent-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString() + '.' + date.getMilliseconds().toString().padStart(3, '0');
  };

  const getTimeAgo = (timestamp: string) => {
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  if (loading && logs.length === 0) {
    return (
      <Card className={cn('p-8', className)}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-lg">Loading logs...</span>
        </div>
      </Card>
    );
  }

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center space-x-2">
              <Clock className="h-5 w-5" />
              <span>Real-Time Agent Logs</span>
              {agentId && <Badge variant="outline">Agent Filtered</Badge>}
            </CardTitle>
            <CardDescription>
              Live streaming logs from all trading agents
            </CardDescription>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAutoScroll(!autoScroll)}
              className={cn(autoScroll && 'bg-blue-50')}
            >
              {autoScroll ? (
                <>
                  <Pause className="h-4 w-4 mr-1" />
                  Auto-scroll
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-1" />
                  Manual
                </>
              )}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsMaximized(!isMaximized)}
            >
              {isMaximized ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Filters and Controls */}
        <div className="flex flex-wrap items-center gap-3 pt-3">
          <div className="flex items-center space-x-2">
            <Select value={selectedLevel} onValueChange={setSelectedLevel} className="w-32">
              <SelectItem value="all">All Levels</SelectItem>
              <SelectItem value="info">Info</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
              <SelectItem value="error">Error</SelectItem>
              <SelectItem value="debug">Debug</SelectItem>
              <SelectItem value="trade">Trade</SelectItem>
            </Select>

            <Select value={selectedCategory} onValueChange={setSelectedCategory} className="w-32">
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="system">System</SelectItem>
              <SelectItem value="trading">Trading</SelectItem>
              <SelectItem value="performance">Performance</SelectItem>
              <SelectItem value="risk">Risk</SelectItem>
              <SelectItem value="network">Network</SelectItem>
            </Select>
          </div>

          <div className="flex-1 max-w-sm">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search logs..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPaused(!isPaused)}
              disabled={loading}
            >
              {isPaused ? (
                <>
                  <Play className="h-4 w-4 mr-1" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="h-4 w-4 mr-1" />
                  Pause
                </>
              )}
            </Button>

            <Button variant="outline" size="sm" onClick={fetchLogs} disabled={loading}>
              <RotateCcw className={cn('h-4 w-4 mr-1', loading && 'animate-spin')} />
              Refresh
            </Button>

            <Button variant="outline" size="sm" onClick={handleExportLogs}>
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>

            <Button variant="outline" size="sm" onClick={handleClearLogs}>
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div
          className={cn(
            'relative overflow-auto border-t',
            compact ? 'max-h-64' : isMaximized ? 'max-h-screen' : ''
          )}
          style={!compact && !isMaximized ? { maxHeight } : {}}
        >
          {filteredLogs.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-gray-500">
              <div className="text-center">
                <Clock className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                <p>No logs found</p>
                <p className="text-xs">Try adjusting your filters</p>
              </div>
            </div>
          ) : (
            <div className="space-y-0">
              {filteredLogs.map((log, index) => {
                const LevelIcon = logLevelIcons[log.level];
                const isLastItem = index === filteredLogs.length - 1;

                return (
                  <div
                    key={log.id}
                    className={cn(
                      'border-b last:border-b-0 p-3 hover:bg-gray-50 transition-colors',
                      'group'
                    )}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 mt-0.5">
                        <LevelIcon className={cn(
                          'h-4 w-4',
                          log.level === 'error' ? 'text-red-500' :
                          log.level === 'warning' ? 'text-yellow-500' :
                          log.level === 'trade' ? 'text-green-500' :
                          log.level === 'info' ? 'text-blue-500' :
                          'text-gray-500'
                        )} />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className={cn(
                            'text-xs font-medium px-2 py-0.5 rounded',
                            logLevelColors[log.level]
                          )}>
                            {log.level.toUpperCase()}
                          </span>
                          <span className={cn(
                            'text-xs font-medium',
                            categoryColors[log.category]
                          )}>
                            {log.category}
                          </span>
                          <span className="text-xs text-gray-500">
                            {log.agentName}
                          </span>
                          <span className="text-xs text-gray-400 ml-auto">
                            {formatTimestamp(log.timestamp)} • {getTimeAgo(log.timestamp)}
                          </span>
                        </div>

                        <p className="text-sm text-gray-900 leading-relaxed">
                          {log.message}
                        </p>

                        {log.details && Object.keys(log.details).length > 0 && (
                          <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-2 font-mono">
                            {Object.entries(log.details).map(([key, value]) => (
                              <div key={key} className="flex justify-between">
                                <span className="text-gray-500">{key}:</span>
                                <span className="text-gray-700">
                                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {isLastItem && <div ref={logsEndRef} />}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer with stats */}
        <div className="border-t px-4 py-2 bg-gray-50 text-xs text-gray-600 flex items-center justify-between">
          <div>
            Showing {filteredLogs.length} of {logs.length} logs
            {isPaused && <span className="ml-2 text-yellow-600 font-medium">⚸ Paused</span>}
          </div>
          <div className="flex items-center space-x-4">
            <span>Level: {selectedLevel}</span>
            <span>Category: {selectedCategory}</span>
            {searchTerm && <span>Filter: "{searchTerm}"</span>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}