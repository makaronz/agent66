import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Vibration,
  Animated,
  Dimensions,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Speech from 'expo-speech';
import Constants from 'expo-constants';

import { VoiceService } from '../services/VoiceService';
import { TradingService } from '../services/TradingService';

const { width: screenWidth } = Dimensions.get('window');

interface VoiceCommand {
  id: string;
  text: string;
  intent: string;
  entities: Record<string, any>;
  confidence: number;
  status: 'pending' | 'executed' | 'failed';
  response?: string;
  timestamp: Date;
}

export default function VoiceTradingScreen() {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [commands, setCommands] = useState<VoiceCommand[]>([]);
  const [transcript, setTranscript] = useState('');
  const [animatedValue] = useState(new Animated.Value(0));
  const [settings, setSettings] = useState({
    voiceEnabled: true,
    autoExecute: false,
    confirmationRequired: true,
    language: 'en-US',
  });

  const voiceServiceRef = useRef<VoiceService | null>(null);

  useEffect(() => {
    initializeVoiceService();
    return () => {
      if (voiceServiceRef.current) {
        voiceServiceRef.current.destroy();
      }
    };
  }, []);

  const initializeVoiceService = async () => {
    try {
      const voiceService = new VoiceService({
        language: settings.language,
        onResult: handleVoiceResult,
        onError: handleVoiceError,
        onEnd: handleVoiceEnd,
      });

      await voiceService.initialize();
      voiceServiceRef.current = voiceService;
    } catch (error) {
      console.error('Voice service initialization error:', error);
      Alert.alert('Error', 'Failed to initialize voice service');
    }
  };

  const handleVoiceResult = async (text: string) => {
    setTranscript(text);
    setIsProcessing(true);

    try {
      // Process voice command
      const analysis = await VoiceService.analyzeCommand(text);

      const command: VoiceCommand = {
        id: Date.now().toString(),
        text,
        intent: analysis.intent,
        entities: analysis.entities,
        confidence: analysis.confidence,
        status: 'pending',
        timestamp: new Date(),
      };

      setCommands(prev => [command, ...prev]);

      // Execute command if confidence is high enough
      if (analysis.confidence > 0.7) {
        await executeCommand(command);
      } else {
        updateCommandStatus(command.id, 'failed');
        speak('I did not understand that command. Please try again.');
      }
    } catch (error) {
      console.error('Voice processing error:', error);
      setIsProcessing(false);
    }
  };

  const handleVoiceError = (error: string) => {
    console.error('Voice recognition error:', error);
    setIsListening(false);
    setIsProcessing(false);

    let errorMessage = 'Voice recognition failed';
    if (error.includes('no-speech')) {
      errorMessage = 'No speech detected. Please try again.';
    } else if (error.includes('not-allowed')) {
      errorMessage = 'Microphone permission denied.';
    }

    speak(errorMessage);
  };

  const handleVoiceEnd = () => {
    setIsListening(false);
    setIsProcessing(false);
    setTranscript('');
  };

  const executeCommand = async (command: VoiceCommand) => {
    try {
      let response = '';

      switch (command.intent) {
        case 'PLACE_ORDER':
          const trade = await TradingService.executeTrade({
            symbol: command.entities.symbol || 'BTCUSDT',
            action: command.entities.side || 'BUY',
            price: command.entities.price || 0,
            size: command.entities.quantity || 0.01,
            reason: 'Voice command execution',
          });
          response = `Placed ${command.entities.side} order for ${command.entities.quantity} ${command.entities.symbol}`;
          break;

        case 'CHECK_BALANCE':
          const account = await TradingService.getAccountSummary();
          response = `Your current balance is ${account.balance.toLocaleString()} dollars`;
          break;

        case 'GET_POSITIONS':
          const positions = await TradingService.getPositions();
          response = `You have ${positions.totalPositions} open positions`;
          break;

        case 'MARKET_ANALYSIS':
          response = 'Market analysis shows neutral sentiment with slight bullish bias';
          break;

        default:
          response = "I'm sorry, I didn't understand that command";
          updateCommandStatus(command.id, 'failed');
      }

      if (response) {
        updateCommandStatus(command.id, 'executed');
        updateCommandResponse(command.id, response);

        if (settings.voiceEnabled) {
          speak(response);
        }
      }
    } catch (error: any) {
      console.error('Command execution error:', error);
      updateCommandStatus(command.id, 'failed');
      updateCommandResponse(command.id, error.message || 'Command failed');

      if (settings.voiceEnabled) {
        speak(`Error: ${error.message || 'Command failed'}`);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const speak = (text: string) => {
    if (settings.voiceEnabled) {
      Speech.speak(text, {
        language: settings.language,
        pitch: 1.0,
        rate: 1.0,
        volume: 1.0,
      });
    }
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

  const toggleListening = async () => {
    if (!voiceServiceRef.current) {
      Alert.alert('Error', 'Voice service not available');
      return;
    }

    if (isListening) {
      await voiceServiceRef.current.stop();
    } else {
      try {
        await voiceServiceRef.current.start();
        setIsListening(true);
        Vibration.vibrate(100);

        // Start animation
        Animated.loop(
          Animated.sequence([
            Animated.timing(animatedValue, {
              toValue: 1,
              duration: 1000,
              useNativeDriver: false,
            }),
            Animated.timing(animatedValue, {
              toValue: 0,
              duration: 1000,
              useNativeDriver: false,
            }),
          ])
        ).start();
      } catch (error) {
        console.error('Failed to start voice recognition:', error);
      }
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: VoiceCommand['status']) => {
    switch (status) {
      case 'pending': return '#f59e0b';
      case 'executed': return '#10b981';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status: VoiceCommand['status']) => {
    switch (status) {
      case 'pending': return 'time-outline';
      case 'executed': return 'checkmark-circle-outline';
      case 'failed': return 'close-circle-outline';
      default: return 'help-outline';
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Voice Trading</Text>
        <TouchableOpacity
          style={styles.settingsButton}
          onPress={() => {
            // Settings implementation
            Alert.alert('Settings', 'Voice settings coming soon');
          }}
        >
          <Ionicons name="settings-outline" size={24} color="#374151" />
        </TouchableOpacity>
      </View>

      {/* Voice Interface */}
      <View style={styles.voiceContainer}>
        <View style={styles.microphoneContainer}>
          <TouchableOpacity
            style={[
              styles.microphoneButton,
              {
                backgroundColor: isListening ? '#ef4444' : '#10b981',
              }
            ]}
            onPress={toggleListening}
            disabled={isProcessing}
          >
            <Ionicons
              name={isListening ? 'stop' : 'mic'}
              size={48}
              color="#ffffff"
            />
          </TouchableOpacity>

          {isListening && (
            <View style={styles.listeningIndicator}>
              <Text style={styles.listeningText}>Listening...</Text>
              <Animated.View
                style={[
                  styles.waveform,
                  {
                    transform: [
                      {
                        scale: animatedValue.interpolate({
                          inputRange: [0, 1],
                          outputRange: [1, 1.2],
                        }),
                      },
                    ],
                  },
                ]}
              />
            </View>
          )}
        </View>

        {transcript && (
          <View style={styles.transcriptContainer}>
            <Text style={styles.transcriptLabel}>Transcript:</Text>
            <Text style={styles.transcriptText}>"{transcript}"</Text>
          </View>
        )}

        <View style={styles.quickCommands}>
          <Text style={styles.quickCommandsTitle}>Try saying:</Text>
          <View style={styles.commandGrid}>
            {[
              'Buy 0.1 Bitcoin',
              'Check my balance',
              'Show my positions',
              'Market analysis',
              'Sell all ETH',
            ].map((phrase, index) => (
              <TouchableOpacity
                key={index}
                style={styles.commandButton}
                onPress={() => handleVoiceResult(phrase)}
              >
                <Text style={styles.commandText}>"{phrase}"</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </View>

      {/* Command History */}
      <View style={styles.historyContainer}>
        <Text style={styles.historyTitle}>Command History</Text>
        {commands.length > 0 ? (
          commands.slice(0, 10).map((command) => (
            <View key={command.id} style={styles.commandItem}>
              <View style={styles.commandHeader}>
                <Ionicons
                  name={getStatusIcon(command.status)}
                  size={20}
                  color={getStatusColor(command.status)}
                />
                <Text style={styles.commandTime}>{formatTime(command.timestamp)}</Text>
                <View
                  style={[
                    styles.statusDot,
                    { backgroundColor: getStatusColor(command.status) }
                  ]}
                />
              </View>
              <Text style={styles.commandText}>{command.text}</Text>
              <Text style={styles.commandIntent}>
                Intent: {command.intent} ({Math.round(command.confidence * 100)}%)
              </Text>
              {command.response && (
                <Text style={styles.commandResponse}>{command.response}</Text>
              )}
            </View>
          ))
        ) : (
          <View style={styles.noCommandsContainer}>
            <Ionicons name="mic-off-outline" size={48} color="#d1d5db" />
            <Text style={styles.noCommandsText}>No commands yet</Text>
            <Text style={styles.noCommandsSubtext}>
              Tap the microphone button to start
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
    backgroundColor: '#ffffff',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  settingsButton: {
    padding: 8,
  },
  voiceContainer: {
    backgroundColor: '#ffffff',
    margin: 16,
    padding: 24,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  microphoneContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  microphoneButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  listeningIndicator: {
    alignItems: 'center',
    marginTop: 16,
  },
  listeningText: {
    fontSize: 16,
    color: '#ef4444',
    fontWeight: '600',
    marginBottom: 8,
  },
  waveform: {
    width: 60,
    height: 4,
    backgroundColor: '#ef4444',
    borderRadius: 2,
  },
  transcriptContainer: {
    backgroundColor: '#f3f4f6',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  transcriptLabel: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 4,
  },
  transcriptText: {
    fontSize: 16,
    color: '#1f2937',
    fontStyle: 'italic',
  },
  quickCommands: {
    marginBottom: 16,
  },
  quickCommandsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 12,
  },
  commandGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  commandButton: {
    width: '48%',
    backgroundColor: '#f3f4f6',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  commandText: {
    fontSize: 12,
    color: '#374151',
    textAlign: 'center',
  },
  historyContainer: {
    backgroundColor: '#ffffff',
    margin: 16,
    padding: 16,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    maxHeight: 400,
  },
  historyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 16,
  },
  commandItem: {
    backgroundColor: '#f9fafb',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  commandHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  commandTime: {
    fontSize: 12,
    color: '#6b7280',
    marginLeft: 8,
    marginRight: 'auto',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginLeft: 8,
  },
  commandIntent: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
    fontStyle: 'italic',
  },
  commandResponse: {
    fontSize: 14,
    color: '#10b981',
    marginTop: 4,
  },
  noCommandsContainer: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  noCommandsText: {
    fontSize: 16,
    color: '#6b7280',
    marginTop: 8,
    fontWeight: '600',
  },
  noCommandsSubtext: {
    fontSize: 14,
    color: '#9ca3af',
    marginTop: 4,
    textAlign: 'center',
  },
});