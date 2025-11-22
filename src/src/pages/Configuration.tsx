import { useState, useEffect } from 'react';
import {
  Settings,
  Shield,
  Globe,
  Save,
  TestTube,
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiService } from '@/services/api';

interface ExchangeConfig {
  id: string;
  name: string;
  connected: boolean;
  hasApiKey: boolean;
  latency: string;
}

const smcParameters = {
  orderBlockMinVolume: 1000000,
  chochConfidenceThreshold: 0.75,
  liquiditySweepSensitivity: 0.8,
  fvgMinSize: 0.001,
  patternExpiryHours: 24
};

const riskParameters = {
  maxPositionSize: 10000,
  dailyLossLimit: 500,
  maxDrawdownPercent: 10,
  positionSizePercent: 2,
  stopLossPercent: 2,
  takeProfitRatio: 2
};

export default function Configuration() {
  const [activeTab, setActiveTab] = useState('exchanges');
  const [showApiKeys, setShowApiKeys] = useState<{[key: string]: boolean}>({});
  const [apiKeys, setApiKeys] = useState<{[key: string]: {key: string, secret: string}}>({});
  const [testingConnection, setTestingConnection] = useState<string | null>(null);
  const [exchanges, setExchanges] = useState<ExchangeConfig[]>([
    { id: 'binance', name: 'Binance', connected: false, hasApiKey: false, latency: 'N/A' },
    { id: 'bybit', name: 'ByBit', connected: false, hasApiKey: false, latency: 'N/A' },
    { id: 'oanda', name: 'OANDA', connected: false, hasApiKey: false, latency: 'N/A' }
  ]);
  const [loading, setLoading] = useState(true);

  // Load exchange configuration status
  useEffect(() => {
    const loadExchangeConfig = async () => {
      try {
        setLoading(true);
        const config = await apiService.getExchangeConfig();
        setExchanges(config);
      } catch (error) {
        console.error('Failed to load exchange config:', error);
      } finally {
        setLoading(false);
      }
    };

    loadExchangeConfig();
    // Refresh every 5 seconds
    const interval = setInterval(loadExchangeConfig, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTestConnection = async (exchangeId: string) => {
    setTestingConnection(exchangeId);
    // Simulate API test
    setTimeout(() => {
      setTestingConnection(null);
    }, 2000);
  };

  const handleSaveConfiguration = () => {
    // TODO: Implement save logic
    console.log('Saving configuration...');
  };

  const toggleApiKeyVisibility = (exchangeId: string) => {
    setShowApiKeys(prev => ({
      ...prev,
      [exchangeId]: !prev[exchangeId]
    }));
  };

  const tabs = [
    { id: 'exchanges', name: 'Exchange Setup', icon: Globe },
    { id: 'smc', name: 'SMC Parameters', icon: Settings },
    { id: 'risk', name: 'Risk Management', icon: Shield },
    { id: 'execution', name: 'Execution Engine', icon: TestTube }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configuration</h1>
          <p className="text-gray-600">Exchange connections, trading parameters, and system settings</p>
        </div>
        <button
          onClick={handleSaveConfiguration}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
        >
          <Save className="h-4 w-4" />
          <span>Save Configuration</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors",
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {/* Exchange Setup */}
        {activeTab === 'exchanges' && (
          <div className="space-y-6">
            {exchanges.map((exchange) => {
              // Determine status: connected only if both connected AND has API key
              // Check if user has entered API key in form OR backend reports it has API key
              const userHasApiKey = apiKeys[exchange.id]?.key?.trim() !== '';
              const hasApiKey = userHasApiKey || exchange.hasApiKey;
              // Only show connected if exchange is connected AND has API key configured
              const isConnected = exchange.connected && hasApiKey;
              const status = isConnected ? 'connected' : 'disconnected';
              
              return (
              <div key={exchange.id} className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-medium text-gray-900">{exchange.name}</h3>
                      <div className="flex items-center space-x-1">
                        {status === 'connected' ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <AlertCircle className="h-5 w-5 text-red-500" />
                        )}
                        <span className={cn(
                          "text-sm font-medium",
                          status === 'connected' ? "text-green-600" : "text-red-600"
                        )}>
                          {status === 'connected' ? 'Connected' : 'Disconnected'}
                        </span>
                      </div>
                      {status === 'connected' && (
                        <span className="text-sm text-gray-500">Latency: {exchange.latency}</span>
                      )}
                      {!hasApiKey && (
                        <span className="text-sm text-yellow-600">API key required</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleTestConnection(exchange.id)}
                      disabled={testingConnection === exchange.id}
                      className={cn(
                        "flex items-center space-x-2 px-3 py-1 text-sm font-medium rounded-md transition-colors",
                        testingConnection === exchange.id
                          ? "bg-gray-400 text-white cursor-not-allowed"
                          : "bg-blue-600 hover:bg-blue-700 text-white"
                      )}
                    >
                      <TestTube className="h-4 w-4" />
                      <span>{testingConnection === exchange.id ? 'Testing...' : 'Test Connection'}</span>
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        API Key
                      </label>
                      <div className="relative">
                        <input
                          type={showApiKeys[exchange.id] ? 'text' : 'password'}
                          value={apiKeys[exchange.id]?.key || ''}
                          onChange={(e) => setApiKeys(prev => ({
                            ...prev,
                            [exchange.id]: { ...prev[exchange.id], key: e.target.value }
                          }))}
                          className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Enter API key"
                        />
                        <button
                          type="button"
                          onClick={() => toggleApiKeyVisibility(exchange.id)}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        >
                          {showApiKeys[exchange.id] ? (
                            <EyeOff className="h-4 w-4 text-gray-400" />
                          ) : (
                            <Eye className="h-4 w-4 text-gray-400" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Secret Key
                      </label>
                      <div className="relative">
                        <input
                          type={showApiKeys[exchange.id] ? 'text' : 'password'}
                          value={apiKeys[exchange.id]?.secret || ''}
                          onChange={(e) => setApiKeys(prev => ({
                            ...prev,
                            [exchange.id]: { ...prev[exchange.id], secret: e.target.value }
                          }))}
                          className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Enter secret key"
                        />
                        <button
                          type="button"
                          onClick={() => toggleApiKeyVisibility(exchange.id)}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        >
                          {showApiKeys[exchange.id] ? (
                            <EyeOff className="h-4 w-4 text-gray-400" />
                          ) : (
                            <Eye className="h-4 w-4 text-gray-400" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Sandbox Mode
                      </label>
                      <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option value="true">Enabled</option>
                        <option value="false">Disabled</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Rate Limit (req/min)
                      </label>
                      <input
                        type="number"
                        defaultValue="1200"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Timeout (ms)
                      </label>
                      <input
                        type="number"
                        defaultValue="5000"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
            })}
          </div>
        )}

        {/* SMC Parameters */}
        {activeTab === 'smc' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Smart Money Concepts Parameters</h3>
              <p className="text-sm text-gray-600">Configure detection thresholds and sensitivity for SMC patterns</p>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Order Block Min Volume
                  </label>
                  <input
                    type="number"
                    defaultValue={smcParameters.orderBlockMinVolume}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Minimum volume required to identify order blocks</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    CHoCH Confidence Threshold
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    defaultValue={smcParameters.chochConfidenceThreshold}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Minimum confidence score for CHoCH detection (0-1)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Liquidity Sweep Sensitivity
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    defaultValue={smcParameters.liquiditySweepSensitivity}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Sensitivity for liquidity sweep detection (0-1)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    FVG Minimum Size
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    defaultValue={smcParameters.fvgMinSize}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Minimum size for Fair Value Gap detection</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Pattern Expiry (Hours)
                  </label>
                  <input
                    type="number"
                    defaultValue={smcParameters.patternExpiryHours}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Hours after which patterns expire if not triggered</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Risk Management */}
        {activeTab === 'risk' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Risk Management Settings</h3>
              <p className="text-sm text-gray-600">Configure position limits, stop losses, and risk controls</p>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Position Size (USD)
                  </label>
                  <input
                    type="number"
                    defaultValue={riskParameters.maxPositionSize}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Daily Loss Limit (USD)
                  </label>
                  <input
                    type="number"
                    defaultValue={riskParameters.dailyLossLimit}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Drawdown (%)
                  </label>
                  <input
                    type="number"
                    defaultValue={riskParameters.maxDrawdownPercent}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Position Size (% of Portfolio)
                  </label>
                  <input
                    type="number"
                    defaultValue={riskParameters.positionSizePercent}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Default Stop Loss (%)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    defaultValue={riskParameters.stopLossPercent}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Take Profit Ratio
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    defaultValue={riskParameters.takeProfitRatio}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Execution Engine */}
        {activeTab === 'execution' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Execution Engine Settings</h3>
              <p className="text-sm text-gray-600">Configure order execution, slippage, and latency parameters</p>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Slippage (bps)
                  </label>
                  <input
                    type="number"
                    defaultValue="10"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Order Timeout (ms)
                  </label>
                  <input
                    type="number"
                    defaultValue="5000"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Retry Attempts
                  </label>
                  <input
                    type="number"
                    defaultValue="3"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Circuit Breaker Threshold
                  </label>
                  <input
                    type="number"
                    defaultValue="5"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Failed orders before circuit breaker activates</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}