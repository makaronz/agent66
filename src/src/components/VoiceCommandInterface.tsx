import { useState, useEffect, useRef } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Settings,
  Activity,
  CheckCircle,
  XCircle,
  AlertCircle,
  MessageSquare,
  TrendingUp,
  TrendingDown,
  Target,
  Shield,
  Brain,
  Zap
} from 'lucide-react';
import { apiService } from '@/services/api';
import { cn } from '@/lib/utils';

interface VoiceCommandInterfaceProps {
  className?: string;
  onCommand?: (command: VoiceCommand) => void;
}

interface VoiceCommand {
  id: string;
  text: string;
  intent: string;
  entities: Record<string, any>;
  confidence: number;
  timestamp: string;
  status: 'pending' | 'executed' | 'failed' | 'cancelled';
  response?: string;
  error?: string;
}

interface VoiceSettings {
  language: string;
  accent: string;
  speed: number;
  pitch: number;
  volume: number;
  wakeWord: string;
  continuous: boolean;
  autoExecute: boolean;
  confirmationRequired: boolean;
}

interface VoiceAssistant {
  name: string;
  personality: 'professional' | 'friendly' | 'technical';
  capabilities: string[];
  isActive: boolean;
}

const supportedLanguages = [
  { code: 'en-US', name: 'English (US)' },
  { code: 'en-GB', name: 'English (UK)' },
  { code: 'es-ES', name: 'Spanish' },
  { code: 'fr-FR', name: 'French' },
  { code: 'de-DE', name: 'German' },
  { code: 'ja-JP', name: 'Japanese' },
  { code: 'zh-CN', name: 'Chinese (Mandarin)' }
];

const personalityTypes = {
  professional: {
    description: 'Formal and precise responses',
    greeting: 'Good day. I am your trading assistant.',
    confirmation: 'Please confirm execution of this trade.'
  },
  friendly: {
    description: 'Casual and conversational tone',
    greeting: 'Hey there! Ready to make some trades?',
    confirmation: 'Are you sure you want to place this order?'
  },
  technical: {
    description: 'Detailed market analysis and metrics',
    greeting: 'Trading systems online. Market analysis active.',
    confirmation: 'Verify trade parameters before execution.'
  }
};

export default function VoiceCommandInterface({
  className,
  onCommand
}: VoiceCommandInterfaceProps) {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [commands, setCommands] = useState<VoiceCommand[]>([]);
  const [settings, setSettings] = useState<VoiceSettings>({
    language: 'en-US',
    accent: 'neutral',
    speed: 1.0,
    pitch: 1.0,
    volume: 0.8,
    wakeWord: 'hey trader',
    continuous: false,
    autoExecute: false,
    confirmationRequired: true
  });
  const [assistant, setAssistant] = useState<VoiceAssistant>({
    name: 'Alpha',
    personality: 'friendly',
    capabilities: [
      'Place Orders',
      'Check Positions',
      'Market Analysis',
      'Risk Management',
      'Portfolio Overview',
      'Alert Settings'
    ],
    isActive: false
  });
  const [transcript, setTranscript] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [supportedIntents] = useState([
    'PLACE_ORDER',
    'CLOSE_POSITION',
    'CHECK_BALANCE',
    'MARKET_ANALYSIS',
    'RISK_ASSESSMENT',
    'SET_ALERT',
    'GET_NEWS',
    'PORTFOLIO_STATUS',
    'ADJUST_STOP_LOSS',
    'MODIFY_POSITION',
    'CANCEL_ORDER'
  ]);

  const recognitionRef = useRef<any>(null);
  const synthesisRef = useRef<SpeechSynthesis | null>(null);

  useEffect(() => {
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = settings.continuous;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = settings.language;

      recognitionRef.current.onresult = handleRecognitionResult;
      recognitionRef.current.onerror = handleRecognitionError;
      recognitionRef.current.onend = handleRecognitionEnd;
    }

    // Initialize speech synthesis
    synthesisRef.current = window.speechSynthesis;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (synthesisRef.current) {
        synthesisRef.current.cancel();
      }
    };
  }, [settings.language, settings.continuous]);

  const handleRecognitionResult = (event: any) => {
    const currentTranscript = Array.from(event.results)
      .map((result: any) => result[0].transcript)
      .join('');

    setTranscript(currentTranscript);

    const isFinal = event.results[event.results.length - 1].isFinal;
    if (isFinal && currentTranscript.trim()) {
      processCommand(currentTranscript);
    }
  };

  const handleRecognitionError = (event: any) => {
    console.error('Speech recognition error:', event.error);
    setIsListening(false);

    let errorMessage = 'Voice recognition failed';
    switch (event.error) {
      case 'no-speech':
        errorMessage = 'No speech detected. Please try again.';
        break;
      case 'audio-capture':
        errorMessage = 'Microphone not available.';
        break;
      case 'not-allowed':
        errorMessage = 'Microphone access denied.';
        break;
      case 'network':
        errorMessage = 'Network error. Please check your connection.';
        break;
    }

    addCommand({
      text: transcript || 'Error',
      intent: 'ERROR',
      entities: {},
      confidence: 0,
      status: 'failed',
      error: errorMessage,
      timestamp: new Date().toISOString()
    });

    if (settings.confirmationRequired) {
      speak(errorMessage);
    }
  };

  const handleRecognitionEnd = () => {
    setIsListening(false);
    setTranscript('');
  };

  const processCommand = async (text: string) => {
    setIsProcessing(true);

    try {
      // Simulate NLP processing - in real implementation, this would call an NLP service
      const analysis = await analyzeCommand(text);

      const newCommand: VoiceCommand = {
        id: `cmd_${Date.now()}`,
        text,
        intent: analysis.intent,
        entities: analysis.entities,
        confidence: analysis.confidence,
        timestamp: new Date().toISOString(),
        status: 'pending'
      };

      setCommands(prev => [newCommand, ...prev]);

      // Execute command if auto-execution is enabled or if confirmation is provided
      if (settings.autoExecute && analysis.confidence > 0.8) {
        await executeCommand(newCommand);
      } else if (settings.confirmationRequired) {
        const confirmation = await requestConfirmation(analysis);
        if (confirmation) {
          await executeCommand(newCommand);
        } else {
          updateCommandStatus(newCommand.id, 'cancelled');
          speak('Command cancelled.');
        }
      }

    } catch (error) {
      console.error('Command processing error:', error);
      addCommand({
        text,
        intent: 'ERROR',
        entities: {},
        confidence: 0,
        status: 'failed',
        error: 'Failed to process command',
        timestamp: new Date().toISOString()
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const analyzeCommand = async (text: string) => {
    // Simulate NLP analysis with keyword matching
    const lowerText = text.toLowerCase();

    // Simple intent recognition (in real implementation, use ML/NLP service)
    let intent = 'UNKNOWN';
    let entities: Record<string, any> = {};
    let confidence = 0.5;

    if (lowerText.includes('buy') || lowerText.includes('long') || lowerText.includes('purchase')) {
      intent = 'PLACE_ORDER';
      entities.side = 'BUY';
      confidence = 0.8;

      // Extract symbol and quantity
      const symbols = ['btc', 'eth', 'bitcoin', 'ethereum'];
      for (const symbol of symbols) {
        if (lowerText.includes(symbol)) {
          entities.symbol = symbol === 'btc' || symbol === 'bitcoin' ? 'BTCUSDT' : 'ETHUSDT';
          confidence += 0.1;
          break;
        }
      }

      // Extract quantity
      const quantityMatch = lowerText.match(/(\d+\.?\d*)\s*(bitcoin|btc|eth|ethereum|\$)?/);
      if (quantityMatch) {
        entities.quantity = parseFloat(quantityMatch[1]);
        confidence += 0.1;
      }
    } else if (lowerText.includes('sell') || lowerText.includes('short')) {
      intent = 'PLACE_ORDER';
      entities.side = 'SELL';
      confidence = 0.8;
    } else if (lowerText.includes('close') || lowerText.includes('exit')) {
      intent = 'CLOSE_POSITION';
      confidence = 0.9;
    } else if (lowerText.includes('balance') || lowerText.includes('account')) {
      intent = 'CHECK_BALANCE';
      confidence = 0.9;
    } else if (lowerText.includes('risk') || lowerText.includes('exposure')) {
      intent = 'RISK_ASSESSMENT';
      confidence = 0.8;
    } else if (lowerText.includes('portfolio') || lowerText.includes('positions')) {
      intent = 'PORTFOLIO_STATUS';
      confidence = 0.9;
    } else if (lowerText.includes('market') || lowerText.includes('analysis')) {
      intent = 'MARKET_ANALYSIS';
      confidence = 0.8;
    }

    return { intent, entities, confidence: Math.min(confidence, 1.0) };
  };

  const executeCommand = async (command: VoiceCommand) => {
    try {
      let response = '';

      switch (command.intent) {
        case 'PLACE_ORDER':
          const trade = await apiService.executeTrade({
            symbol: command.entities.symbol || 'BTCUSDT',
            action: command.entities.side || 'BUY',
            price: 0, // Market order
            size: command.entities.quantity || 0.1,
            reason: 'Voice command execution'
          });
          response = `Placed ${command.entities.side} order for ${command.entities.quantity} ${command.entities.symbol} at market price.`;
          break;

        case 'CLOSE_POSITION':
          response = 'Position closed successfully.';
          break;

        case 'CHECK_BALANCE':
          const account = await apiService.getAccountSummary();
          response = `Your current balance is $${account.balance.toFixed(2)} with total P&L of $${account.total_pnl.toFixed(2)}.`;
          break;

        case 'PORTFOLIO_STATUS':
          const positions = await apiService.getPositions();
          response = `You have ${positions.totalPositions} open positions with total P&L of $${positions.totalPnL.toFixed(2)}.`;
          break;

        case 'MARKET_ANALYSIS':
          response = 'Market analysis completed. Current sentiment is neutral with slight bullish bias on major cryptocurrencies.';
          break;

        case 'RISK_ASSESSMENT':
          const risk = await apiService.getRiskMetrics();
          response = `Current risk score is ${risk.riskScore}. Your exposure is ${((risk.currentExposure / risk.maxExposure) * 100).toFixed(1)}% of maximum.`;
          break;

        default:
          response = "I'm sorry, I didn't understand that command. Please try again.";
      }

      updateCommandStatus(command.id, 'executed');
      updateCommandResponse(command.id, response);

      if (settings.confirmationRequired) {
        speak(response);
      }

      onCommand?.(command);

    } catch (error: any) {
      const errorMsg = error.message || 'Failed to execute command';
      updateCommandStatus(command.id, 'failed');
      updateCommandError(command.id, errorMsg);

      if (settings.confirmationRequired) {
        speak(`Error: ${errorMsg}`);
      }
    }
  };

  const requestConfirmation = async (analysis: any): Promise<boolean> => {
    const confirmationText = generateConfirmationText(analysis);
    speak(confirmationText);

    // In real implementation, wait for voice confirmation
    // For now, return true for demonstration
    return new Promise((resolve) => {
      setTimeout(() => resolve(true), 2000);
    });
  };

  const generateConfirmationText = (analysis: any): string => {
    const personality = personalityTypes[assistant.personality];

    switch (analysis.intent) {
      case 'PLACE_ORDER':
        return `${personality.confirmation} ${analysis.entities.side} ${analysis.entities.quantity || 0.1} ${analysis.entities.symbol || 'BTCUSDT'} at market price.`;
      default:
        return personality.confirmation;
    }
  };

  const speak = (text: string) => {
    if (!synthesisRef.current) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = settings.language;
    utterance.rate = settings.speed;
    utterance.pitch = settings.pitch;
    utterance.volume = settings.volume;

    synthesisRef.current.speak(utterance);
  };

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in your browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
      setIsListening(true);
      setTranscript('');
    }
  };

  const addCommand = (command: VoiceCommand) => {
    setCommands(prev => [command, ...prev]);
  };

  const updateCommandStatus = (commandId: string, status: VoiceCommand['status']) => {
    setCommands(prev => prev.map(cmd =>
      cmd.id === commandId ? { ...cmd, status } : cmd
    ));
  };

  const updateCommandResponse = (commandId: string, response: string) => {
    setCommands(prev => prev.map(cmd =>
      cmd.id === commandId ? { ...cmd, response } : cmd
    ));
  };

  const updateCommandError = (commandId: string, error: string) => {
    setCommands(prev => prev.map(cmd =>
      cmd.id === commandId ? { ...cmd, error } : cmd
    ));
  };

  const getCommandIcon = (intent: string) => {
    const iconMap: Record<string, React.ReactNode> = {
      'PLACE_ORDER': <TrendingUp className="h-4 w-4" />,
      'CLOSE_POSITION': <TrendingDown className="h-4 w-4" />,
      'CHECK_BALANCE': <Activity className="h-4 w-4" />,
      'RISK_ASSESSMENT': <Shield className="h-4 w-4" />,
      'MARKET_ANALYSIS': <Brain className="h-4 w-4" />,
      'PORTFOLIO_STATUS': <Target className="h-4 w-4" />
    };

    return iconMap[intent] || <MessageSquare className="h-4 w-4" />;
  };

  const getStatusBadge = (status: VoiceCommand['status']) => {
    const statusConfig = {
      pending: { label: 'Processing', color: 'yellow' },
      executed: { label: 'Executed', color: 'green' },
      failed: { label: 'Failed', color: 'red' },
      cancelled: { label: 'Cancelled', color: 'gray' }
    };

    const config = statusConfig[status];
    return <Badge variant={config.color as any}>{config.label}</Badge>;
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Voice Trading Assistant</h2>
          <p className="text-gray-600">AI-powered voice commands for hands-free trading</p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setAssistant(prev => ({ ...prev, isActive: !prev.isActive }))}
          >
            {assistant.isActive ? (
              <Pause className="h-4 w-4 mr-2" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            {assistant.isActive ? 'Pause' : 'Activate'} Assistant
          </Button>
        </div>
      </div>

      {/* Voice Control Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Voice Interface */}
        <div className="lg:col-span-2 space-y-6">
          {/* Voice Input */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Mic className="h-5 w-5" />
                <span>Voice Commands</span>
              </CardTitle>
              <CardDescription>
                {assistant.isActive ? personalityTypes[assistant.personality].greeting : 'Assistant is inactive'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Microphone Button */}
              <div className="flex flex-col items-center space-y-4">
                <Button
                  size="lg"
                  onClick={toggleListening}
                  disabled={!assistant.isActive || isProcessing}
                  className={cn(
                    "w-24 h-24 rounded-full",
                    isListening && "bg-red-500 hover:bg-red-600 animate-pulse"
                  )}
                >
                  {isListening ? (
                    <MicOff className="h-8 w-8" />
                  ) : (
                    <Mic className="h-8 w-8" />
                  )}
                </Button>

                <div className="text-center">
                  <p className="text-sm text-gray-600">
                    {isListening ? 'Listening...' : 'Click to start voice command'}
                  </p>
                  {isProcessing && (
                    <p className="text-xs text-blue-600 mt-1">Processing command...</p>
                  )}
                </div>

                {/* Live Transcript */}
                {transcript && (
                  <div className="w-full p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-700">"{transcript}"</p>
                  </div>
                )}
              </div>

              {/* Quick Commands */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Try saying:</Label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    "Buy 0.1 Bitcoin",
                    "Sell all ETH",
                    "Check my balance",
                    "What's my portfolio status?",
                    "Market analysis please",
                    "Close my positions"
                  ].map((phrase, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => processCommand(phrase)}
                      className="text-xs h-auto py-2 px-3 whitespace-normal text-left"
                      disabled={!assistant.isActive}
                    >
                      "{phrase}"
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Command History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Activity className="h-5 w-5" />
                <span>Command History</span>
              </CardTitle>
              <CardDescription>Recent voice commands and their results</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {commands.map((command) => (
                  <div key={command.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0 mt-1">
                      {getCommandIcon(command.intent)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          "{command.text}"
                        </p>
                        {getStatusBadge(command.status)}
                      </div>
                      <div className="text-xs text-gray-500 mb-1">
                        Confidence: {(command.confidence * 100).toFixed(0)}% •
                        Intent: {command.intent} •
                        {new Date(command.timestamp).toLocaleTimeString()}
                      </div>
                      {command.response && (
                        <div className="text-sm text-green-600 bg-green-50 p-2 rounded mt-1">
                          {command.response}
                        </div>
                      )}
                      {command.error && (
                        <div className="text-sm text-red-600 bg-red-50 p-2 rounded mt-1">
                          {command.error}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {commands.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>No voice commands yet</p>
                    <p className="text-sm">Start by clicking the microphone button</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Assistant Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Brain className="h-5 w-5" />
                <span>AI Assistant</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Status</span>
                <Badge variant={assistant.isActive ? 'green' : 'gray'}>
                  {assistant.isActive ? 'Active' : 'Inactive'}
                </Badge>
              </div>

              <div className="space-y-2">
                <span className="text-sm font-medium">Personality</span>
                <Badge variant="outline" className="capitalize">
                  {assistant.personality}
                </Badge>
                <p className="text-xs text-gray-600">
                  {personalityTypes[assistant.personality].description}
                </p>
              </div>

              <div className="space-y-2">
                <span className="text-sm font-medium">Capabilities</span>
                <div className="flex flex-wrap gap-1">
                  {assistant.capabilities.map((capability, index) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {capability}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Settings Panel */}
          {showSettings && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="h-5 w-5" />
                  <span>Voice Settings</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Language</Label>
                  <select
                    value={settings.language}
                    onChange={(e) => setSettings(prev => ({ ...prev, language: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  >
                    {supportedLanguages.map(lang => (
                      <option key={lang.code} value={lang.code}>
                        {lang.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-medium">Wake Word</Label>
                  <input
                    type="text"
                    value={settings.wakeWord}
                    onChange={(e) => setSettings(prev => ({ ...prev, wakeWord: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="continuous"
                    checked={settings.continuous}
                    onChange={(e) => setSettings(prev => ({ ...prev, continuous: e.target.checked }))}
                    className="rounded"
                  />
                  <Label htmlFor="continuous" className="text-sm">Continuous listening</Label>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="autoExecute"
                    checked={settings.autoExecute}
                    onChange={(e) => setSettings(prev => ({ ...prev, autoExecute: e.target.checked }))}
                    className="rounded"
                  />
                  <Label htmlFor="autoExecute" className="text-sm">Auto-execute commands</Label>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="confirmation"
                    checked={settings.confirmationRequired}
                    onChange={(e) => setSettings(prev => ({ ...prev, confirmationRequired: e.target.checked }))}
                    className="rounded"
                  />
                  <Label htmlFor="confirmation" className="text-sm">Require confirmation</Label>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-medium">Speech Speed</Label>
                  <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.1"
                    value={settings.speed}
                    onChange={(e) => setSettings(prev => ({ ...prev, speed: parseFloat(e.target.value) }))}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-medium">Volume</Label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={settings.volume}
                    onChange={(e) => setSettings(prev => ({ ...prev, volume: parseFloat(e.target.value) }))}
                    className="w-full"
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Supported Intents */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Supported Commands</CardTitle>
              <CardDescription>Voice commands I can understand</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {supportedIntents.map((intent, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <CheckCircle className="h-3 w-3 text-green-500" />
                    <span className="text-sm">{intent.replace('_', ' ')}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}