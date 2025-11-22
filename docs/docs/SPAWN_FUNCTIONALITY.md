# Agent Spawn Functionality

This document describes the comprehensive agent spawning and management system for the SMC Trading Agent platform.

## Overview

The spawn functionality allows users to create, configure, and monitor automated trading agents with real-time updates and robust error handling. The system supports multiple agent types, each optimized for specific trading strategies and risk profiles.

## Features

### 🚀 Agent Spawning
- **Intuitive Configuration**: User-friendly dialog with comprehensive validation
- **Real-time Validation**: Instant feedback on configuration errors and warnings
- **Resource Estimation**: Predict system resource requirements before spawning
- **Template System**: Pre-configured templates for common trading strategies

### 📊 Real-time Monitoring
- **Live Status Updates**: WebSocket-based real-time agent status monitoring
- **Performance Metrics**: Track P&L, win rate, trade count, and system resources
- **Interactive Dashboard**: Expandable agent cards with detailed information
- **Auto-refresh**: Configurable automatic data refresh intervals

### 📝 Comprehensive Logging
- **Multi-level Logging**: Info, warning, error, debug, and trade-specific logs
- **Real-time Stream**: Live log streaming with WebSocket connectivity
- **Advanced Filtering**: Filter by level, category, agent, or search terms
- **Export Functionality**: Download logs for offline analysis

### 🎛️ Agent Control
- **Start/Stop/Pause**: Full lifecycle control over trading agents
- **Configuration Updates**: Modify agent parameters without restart
- **Emergency Stop**: Immediate termination capability
- **Batch Operations**: Control multiple agents simultaneously

## Architecture

### Frontend Components

#### Core Components
- `AgentSpawnDialog`: Comprehensive agent configuration interface
- `AgentStatusDashboard`: Real-time agent monitoring dashboard
- `RealTimeAgentLogs`: Live log streaming and management
- `AgentManagement`: Main page integrating all agent functionality

#### UI Components
- `Dialog`: Modal dialogs for configuration
- `Card`: Responsive card layouts
- `Badge`: Status indicators and labels
- `Button`: Interactive controls with loading states
- `Tabs`: Tabbed interface for organization

### Services

#### API Service (`src/services/api.ts`)
- **Agent Management**: CRUD operations for agents
- **Configuration**: Agent configuration validation and updates
- **Monitoring**: Real-time status and performance data
- **Logging**: Log retrieval and filtering

#### WebSocket Service (`src/services/websocket.ts`)
- **Real-time Updates**: Live agent status changes
- **Market Data**: Streaming market information
- **Log Streaming**: Real-time log delivery
- **Event Notifications**: System and agent event alerts

## Agent Types

### 1. SMC Pattern Detector
- **Purpose**: Detects Smart Money Concepts patterns
- **Patterns**: Order Blocks, CHoCH/BOS, FVG, Liquidity Sweeps
- **Latency**: <10ms pattern detection
- **Resources**: 2-4 cores, 4-8GB RAM

### 2. ML Decision Engine
- **Purpose**: AI-powered trading decisions
- **Models**: LSTM, Transformer, PPO ensemble
- **Latency**: <5ms decision making
- **Resources**: 4-8 cores, 8-16GB RAM

### 3. Ultra-Low Latency Executor
- **Purpose**: Fast order execution
- **Latency**: <1ms order execution
- **Features**: Circuit breakers, retry logic
- **Resources**: 2-4 cores, 2-4GB RAM

### 4. Risk Manager
- **Purpose**: Real-time risk monitoring
- **Features**: VaR calculation, drawdown monitoring
- **Latency**: <20ms risk assessment
- **Resources**: 1-2 cores, 2-4GB RAM

## Configuration Options

### Basic Settings
- **Agent Name**: Unique identifier for the agent
- **Agent Type**: Selection from available agent types
- **Trading Symbol**: Market pair to trade (BTCUSDT, ETHUSDT, etc.)
- **Timeframe**: Analysis timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)

### Risk Management
- **Initial Capital**: Starting capital allocation ($100-$100,000)
- **Leverage**: Trading leverage (1x-100x)
- **Risk Level**: Conservative, moderate, or aggressive
- **Max Drawdown**: Maximum acceptable drawdown (1%-50%)
- **Daily Loss Limit**: Maximum daily loss ($10-$10,000)

### Trading Strategies
- **Order Block Trading**: Trade order block reversals
- **Liquidity Sweep**: Capitalize on liquidity sweeps
- **FVG Trading**: Fair Value Gap trading
- **Breakout Trading**: Momentum breakout strategies
- **Mean Reversion**: Statistical arbitrage

### Safety Features
- **Paper Trading Mode**: Test strategies without real capital
- **API Rate Limits**: Configurable rate limits per exchange
- **Circuit Breakers**: Automatic trading suspension on errors
- **Position Sizing**: Dynamic position size calculation

## Real-time Features

### WebSocket Events
```typescript
// Agent status updates
agent:update -> AgentStatusUpdate

// Market data updates
market:update -> MarketDataUpdate

// Log entries
logs:all -> LogEntry
logs:{agentId} -> LogEntry

// Trade alerts
trade:alert -> TradeAlert
trades:{agentId} -> TradeAlert

// System events
system:event -> SystemEvent
```

### Auto-reconnection
- **Exponential Backoff**: Smart reconnection strategy
- **Max Attempts**: Configurable reconnection limits
- **Fallback**: Automatic fallback to HTTP polling

## Error Handling

### Client-side
- **Form Validation**: Real-time configuration validation
- **API Error Handling**: Graceful error display and recovery
- **WebSocket Reconnection**: Automatic connection recovery
- **Loading States**: Loading indicators for all operations

### Server-side
- **Configuration Validation**: Server-side parameter validation
- **Resource Monitoring**: System resource usage tracking
- **Circuit Breakers**: Protection against cascade failures
- **Health Checks**: Regular system health monitoring

## Performance Optimizations

### Frontend
- **Lazy Loading**: Components loaded on demand
- **Memoization**: Optimized re-rendering
- **Virtual Scrolling**: Efficient log rendering
- **Debouncing**: Reduced API call frequency

### Backend
- **Connection Pooling**: Efficient database connections
- **Caching**: Redis caching for frequent data
- **Rate Limiting**: API rate limiting and throttling
- **Resource Monitoring**: System resource optimization

## Security Features

### Authentication
- **JWT Tokens**: Secure authentication
- **API Key Management**: Secure exchange API key storage
- **Role-based Access**: Granular permission control

### Data Protection
- **Encryption**: Sensitive data encryption
- **Audit Trails**: Complete action logging
- **Session Management**: Secure session handling

## Testing

### Unit Tests
- **Component Testing**: Jest + React Testing Library
- **Service Testing**: API and WebSocket service tests
- **Utility Testing**: Helper function validation

### Integration Tests
- **End-to-End**: Full workflow testing
- **API Testing**: Backend endpoint validation
- **WebSocket Testing**: Real-time communication testing

### Performance Testing
- **Load Testing**: System performance under load
- **Stress Testing**: System limits identification
- **Latency Testing**: Response time measurement

## Deployment

### Environment Variables
```bash
# WebSocket Configuration
WEBSOCKET_URL=ws://localhost:3001
WEBSOCKET_RECONNECT_ATTEMPTS=5
WEBSOCKET_RECONNECT_DELAY=1000

# API Configuration
API_BASE_URL=http://localhost:3001/api
API_TIMEOUT=10000

# Agent Configuration
MAX_AGENTS_PER_USER=10
DEFAULT_AGENT_TIMEOUT=30000
AGENT_HEALTH_CHECK_INTERVAL=5000
```

### Docker Configuration
```dockerfile
# Multi-stage build for optimization
FROM node:18-alpine as builder
# Build stage...

FROM node:18-alpine as runtime
# Runtime stage...
```

## Troubleshooting

### Common Issues

#### WebSocket Connection Failed
- **Check**: WebSocket server status
- **Solution**: Verify server is running and accessible
- **Fallback**: System automatically switches to HTTP polling

#### Agent Spawn Failed
- **Check**: Configuration validation
- **Solution**: Review error messages and adjust parameters
- **Resources**: Verify sufficient system resources

#### Real-time Updates Not Working
- **Check**: WebSocket connection status
- **Solution**: Refresh page or check network connectivity
- **Fallback**: Manual refresh available

### Debug Mode
Enable debug logging:
```typescript
// In browser console
localStorage.setItem('debug', 'smc:*');
```

## Future Enhancements

### Planned Features
- **Multi-asset Support**: Expand beyond cryptocurrency
- **Advanced Analytics**: ML-powered performance insights
- **Social Trading**: Agent strategy sharing
- **Mobile App**: Native mobile application

### Performance Improvements
- **Edge Computing**: Regional agent deployment
- **Database Optimization**: Query performance improvements
- **Caching Strategy**: Enhanced caching mechanisms
- **Load Balancing**: Scalable architecture

## API Reference

### Agent Endpoints
```
GET    /api/agents              - List all agents
POST   /api/agents/spawn        - Spawn new agent
GET    /api/agents/{id}         - Get agent details
PUT    /api/agents/{id}/config  - Update agent config
POST   /api/agents/{id}/control - Control agent
DELETE /api/agents/{id}         - Delete agent
```

### Log Endpoints
```
GET /api/agents/logs           - Get all agent logs
GET /api/agents/{id}/logs     - Get specific agent logs
```

### Performance Endpoints
```
GET /api/agents/{id}/performance - Get agent performance
GET /api/agents/{id}/resources   - Get agent resource usage
```

## Support

For issues, questions, or feature requests:
- **Documentation**: `/docs/` directory
- **Issues**: GitHub issue tracker
- **Support**: support@smc-trading.com