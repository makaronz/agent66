# Developer Guide - SMC Trading Agent

Comprehensive guide for developers working on the SMC Trading Agent codebase.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Development Environment](#development-environment)
4. [Code Organization](#code-organization)
5. [Key Components](#key-components)
6. [Data Flow](#data-flow)
7. [Adding New Features](#adding-new-features)
8. [Debugging](#debugging)
9. [Performance Optimization](#performance-optimization)
10. [Testing Strategy](#testing-strategy)

## Overview

The SMC Trading Agent is a hybrid trading system combining:
- **Frontend**: React + TypeScript for user interface
- **Backend**: Express.js + TypeScript for API and WebSocket connections
- **Trading Engine**: Python for SMC analysis and trade execution

### System Requirements

- **Node.js**: 18.0.0 or higher
- **Python**: 3.9 or higher
- **npm/pip**: Latest versions
- **Git**: For version control

## Architecture Deep Dive

### System Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│              (React Frontend - Port 5173)                │
│  • Dashboard, Trading UI, Monitoring, Configuration     │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST API
┌───────────────────────▼─────────────────────────────────┐
│                    API Layer                             │
│          (Express.js Backend - Port 3001)                │
│  • REST Endpoints, WebSocket Server, Data Aggregation   │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST API
┌───────────────────────▼─────────────────────────────────┐
│                  Business Logic Layer                    │
│              (Python Trading Engine)                     │
│  • SMC Detection, Risk Management, Trade Execution      │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API / WebSocket
┌───────────────────────▼─────────────────────────────────┐
│                    Data Layer                            │
│                 (Binance Exchange)                       │
│  • Market Data, Order Book, Trade History               │
└─────────────────────────────────────────────────────────┘
```

### Component Communication

**Frontend ↔ Backend**:
- REST API: `http://localhost:3001/api/*`
- WebSocket: `ws://localhost:3001` (for real-time updates)

**Backend ↔ Python Agent**:
- REST API: `http://localhost:8000/api/python/*`
- TypeScript fetches OHLCV data from Python: `/api/trading/live-ohlcv`

**Python Agent ↔ Backend**:
- REST API: Python fetches OHLCV from TypeScript: `http://localhost:3001/api/trading/live-ohlcv`

## Development Environment

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/smc_trading_agent.git
cd smc_trading_agent

# 2. Install Node.js dependencies
npm install

# 3. Install Python dependencies
pip install -r requirements.txt
pip install -r test-requirements.txt

# 4. Setup environment variables
cp env.example .env
# Edit .env with your API keys

# 5. Verify installation
npm run check  # TypeScript type checking
pytest tests/  # Run Python tests
```

### Development Scripts

**TypeScript/Node.js**:
```bash
# Development server (with hot reload)
npm run server:dev

# Frontend dev server
npm run client:dev

# Run both frontend and backend
npm run dev

# Type checking
npm run check

# Linting
npm run lint

# Build production
npm run build
```

**Python**:
```bash
# Run main trading agent
python main.py

# Run with specific config
python main.py --config config/development.yaml

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. --cov-report=html tests/

# Type checking
mypy .

# Format code
black .
isort .
```

### IDE Configuration

**VS Code Recommended Extensions**:
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- Python (ms-python.python)
- TypeScript Vue Plugin (Vue.volar)
- Black Formatter (ms-python.black-formatter)

**VS Code Settings** (`.vscode/settings.json`):
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  },
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "typescript.tsdk": "node_modules/typescript/lib"
}
```

## Code Organization

### Frontend Structure (`src/`)

```
src/
├── main.tsx              # Application entry point
├── App.tsx               # Root component
├── pages/                # Page components
│   ├── Dashboard.tsx    # Main dashboard
│   ├── Trading.tsx      # Trading interface
│   ├── RiskManagement.tsx
│   └── Monitoring.tsx
├── components/           # Reusable components
│   ├── ui/              # UI primitives (buttons, inputs)
│   ├── charts/          # Chart components
│   └── layout/          # Layout components
├── services/            # API clients and services
│   ├── api.ts          # Main API client
│   └── websocket.ts    # WebSocket client
├── hooks/               # Custom React hooks
├── store/               # State management (Zustand)
├── types/               # TypeScript type definitions
└── utils/               # Utility functions
```

### Backend Structure (`api/`)

```
api/
├── server.ts            # Server entry point
├── app.ts               # Express app configuration
├── routes/              # API route handlers
│   ├── trading.ts      # Trading endpoints
│   └── health.ts       # Health check endpoints
├── services/            # Business logic services
│   └── marketDataAggregator.ts
├── integrations/        # External service integrations
│   ├── binanceWebsocket.ts
│   └── binanceRest.ts
├── utils/               # Utility functions
│   ├── logger.ts
│   ├── errors.ts
│   └── validation.ts
└── types/               # TypeScript type definitions
```

### Python Structure

```
.
├── main.py              # Main trading loop entry point
├── execution_engine/    # Trade execution
│   └── paper_trading.py
├── risk_manager/        # Risk management
│   └── smc_risk_manager.py
├── smc_detector/        # SMC pattern detection
│   └── indicators.py
├── data_pipeline/       # Data ingestion
│   ├── live_data_client.py
│   └── ingestion.py
├── decision_engine/     # Trading decisions
│   ├── simple_heuristic.py
│   └── ml_decision_engine.py
├── config/              # Configuration files
├── tests/               # Test suites
└── utils/               # Utility modules
```

## Key Components

### 1. Market Data Aggregator (`api/services/marketDataAggregator.ts`)

**Purpose**: Aggregates real-time market data from Binance WebSocket streams.

**Key Methods**:
```typescript
class MarketDataAggregator {
  // Initialize WebSocket connections
  async initialize(): Promise<void>
  
  // Subscribe to symbol updates
  subscribe(symbol: string): void
  
  // Get current market data
  getMarketData(symbol: string): MarketData | null
  
  // Get OHLCV data for Python backend
  getOHLCVData(symbol: string, timeframe: string, limit: number): OHLCVData[]
}
```

**Usage Example**:
```typescript
const aggregator = new MarketDataAggregator();
await aggregator.initialize();
aggregator.subscribe('BTCUSDT');

// Get latest data
const marketData = aggregator.getMarketData('BTCUSDT');
const ohlcv = aggregator.getOHLCVData('BTCUSDT', '1h', 100);
```

### 2. Live Data Client (`data_pipeline/live_data_client.py`)

**Purpose**: Fetches live OHLCV data from TypeScript backend for Python agent.

**Key Methods**:
```python
class LiveDataClient:
    async def get_latest_ohlcv_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from TypeScript backend."""
        pass
    
    async def close(self):
        """Close HTTP session."""
        pass
```

**Usage Example**:
```python
client = LiveDataClient(base_url="http://localhost:3001")
df = await client.get_latest_ohlcv_data("BTCUSDT", timeframe="1h", limit=100)
# df contains columns: timestamp, open, high, low, close, volume
await client.close()
```

### 3. SMC Indicators (`smc_detector/indicators.py`)

**Purpose**: Detects Smart Money Concepts patterns (order blocks, CHOCH, BOS).

**Key Methods**:
```python
class SMCIndicators:
    def detect_order_blocks(
        self,
        df: pd.DataFrame,
        lookback: int = 20
    ) -> List[Dict[str, Any]]:
        """Detect order blocks in price action."""
        pass
    
    def detect_choch(
        self,
        df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Detect Change of Character (CHOCH)."""
        pass
    
    def detect_bos(
        self,
        df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Detect Break of Structure (BOS)."""
        pass
```

**Usage Example**:
```python
indicators = SMCIndicators()
df = await client.get_latest_ohlcv_data("BTCUSDT")

order_blocks = indicators.detect_order_blocks(df)
choch = indicators.detect_choch(df)
bos = indicators.detect_bos(df)
```

### 4. Risk Manager (`risk_manager/smc_risk_manager.py`)

**Purpose**: Manages risk through position sizing, stop-loss, and daily limits.

**Key Methods**:
```python
class SMCRiskManager:
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        account_balance: float,
        risk_per_trade: float = 0.02
    ) -> float:
        """Calculate position size based on risk."""
        pass
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        order_block: Dict[str, Any],
        side: str
    ) -> float:
        """Calculate stop loss based on order block."""
        pass
    
    def validate_trade(
        self,
        symbol: str,
        size: float,
        side: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate trade against risk limits."""
        pass
```

### 5. Paper Trading Engine (`execution_engine/paper_trading.py`)

**Purpose**: Simulates trade execution with live prices for paper trading.

**Key Methods**:
```python
class PaperTradingEngine:
    async def execute_order(
        self,
        symbol: str,
        side: str,
        size: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> Position:
        """Execute a paper trade."""
        pass
    
    async def update_positions(self):
        """Update open positions with live prices."""
        pass
    
    def get_positions(self) -> List[Position]:
        """Get all open positions."""
        pass
    
    def get_account_summary(self) -> AccountSummary:
        """Get account balance and P&L."""
        pass
```

## Data Flow

### Real-Time Market Data Flow

```
Binance WebSocket
    ↓
TypeScript Backend (MarketDataAggregator)
    ├─→ Stores in memory
    ├─→ Serves to Frontend via REST/WebSocket
    └─→ Serves OHLCV to Python via REST
```

### Trading Decision Flow

```
1. Python Agent (every 60s)
   ↓
2. Fetch OHLCV from TypeScript backend
   ↓
3. Detect SMC patterns (order blocks, CHOCH, BOS)
   ↓
4. Generate trading signal (heuristic or ML)
   ↓
5. Apply risk management (position size, SL/TP)
   ↓
6. Execute paper trade (if confidence > threshold)
   ↓
7. Update positions with live prices
   ↓
8. Check stop-loss/take-profit triggers
```

### API Request Flow

```
Frontend
  → REST API (/api/trading/market-data)
  → TypeScript Backend
  → MarketDataAggregator (in-memory)
  → Response (JSON)

Python Agent
  → REST API (http://localhost:3001/api/trading/live-ohlcv)
  → TypeScript Backend
  → MarketDataAggregator (in-memory)
  → Response (JSON with OHLCV data)
```

## Adding New Features

### Adding a New API Endpoint

**Step 1**: Define route in `api/routes/trading.ts`:
```typescript
router.get('/new-endpoint', async (req, res) => {
  try {
    // Implementation
    res.json({ data: result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

**Step 2**: Add to API documentation (`docs/API_DOCUMENTATION.md`)

**Step 3**: Add frontend service method (`src/services/api.ts`):
```typescript
export async function getNewEndpoint(): Promise<ResponseType> {
  const response = await api.get('/api/trading/new-endpoint');
  return response.data;
}
```

**Step 4**: Add tests (`tests/api/trading.test.ts`):
```typescript
describe('GET /api/trading/new-endpoint', () => {
  it('should return expected data', async () => {
    const response = await request(app).get('/api/trading/new-endpoint');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('data');
  });
});
```

### Adding a New SMC Indicator

**Step 1**: Add method to `smc_detector/indicators.py`:
```python
def detect_new_pattern(
    self,
    df: pd.DataFrame,
    params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Detect new SMC pattern.
    
    Args:
        df: OHLCV DataFrame
        params: Pattern detection parameters
        
    Returns:
        List of detected patterns
    """
    # Implementation
    patterns = []
    # ... detection logic ...
    return patterns
```

**Step 2**: Add tests (`tests/smc_detector/test_indicators.py`):
```python
def test_detect_new_pattern():
    indicators = SMCIndicators()
    df = create_test_dataframe()
    
    patterns = indicators.detect_new_pattern(df, {})
    
    assert len(patterns) >= 0
    assert all('timestamp' in p for p in patterns)
```

**Step 3**: Integrate into main trading loop (`main.py`):
```python
# In trading loop
new_patterns = indicators.detect_new_pattern(df, params)
if new_patterns:
    # Generate signal based on pattern
    signal = generate_signal_from_pattern(new_patterns[0])
```

## Debugging

### Frontend Debugging

**React DevTools**: Install browser extension for component inspection

**Console Logging**:
```typescript
// Use structured logging
console.log('[Component]', { data, timestamp: Date.now() });

// Use React Query DevTools for API debugging
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
```

**Network Debugging**:
- Use browser DevTools Network tab
- Check WebSocket messages in DevTools
- Verify API responses

### Backend Debugging

**TypeScript Debugging**:
```bash
# Use Node.js debugger
node --inspect api/server.ts

# Or use VS Code debugger configuration
# .vscode/launch.json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Server",
  "runtimeExecutable": "tsx",
  "args": ["api/server.ts"],
  "console": "integratedTerminal"
}
```

**Logging**:
```typescript
import logger from './utils/logger';

logger.info('Processing request', { symbol, timestamp });
logger.error('Error occurred', { error, stack: error.stack });
```

### Python Debugging

**Python Debugger**:
```python
import pdb

# Add breakpoint
pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

**VS Code Python Debugger**:
```json
{
  "type": "python",
  "request": "launch",
  "name": "Python: Debug Main",
  "program": "${workspaceFolder}/main.py",
  "console": "integratedTerminal"
}
```

**Logging**:
```python
import logging

logger = logging.getLogger(__name__)
logger.info('Processing symbol', extra={'symbol': symbol})
logger.error('Error occurred', exc_info=True)
```

## Performance Optimization

### Frontend Optimization

- **Code Splitting**: Lazy load routes and components
- **Memoization**: Use `React.memo` and `useMemo` for expensive calculations
- **Virtualization**: Use `react-window` for long lists
- **Debouncing**: Debounce API calls and search inputs

### Backend Optimization

- **Caching**: Cache frequently accessed market data
- **Connection Pooling**: Reuse WebSocket connections
- **Batch Operations**: Batch database queries when possible
- **Compression**: Enable gzip compression for API responses

### Python Optimization

- **Async I/O**: Use async/await for I/O operations
- **Data Processing**: Use pandas vectorized operations
- **Caching**: Cache expensive calculations (order blocks, indicators)
- **Memory Management**: Release large DataFrames when done

## Testing Strategy

### Test Types

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **E2E Tests**: Test full user workflows
4. **Performance Tests**: Test system performance under load

### Running Tests

```bash
# All tests
npm run test:all

# Frontend tests
npm test
npm run test:watch  # Watch mode

# Backend tests
pytest tests/
pytest tests/ -v  # Verbose
pytest tests/ --cov  # With coverage

# Specific test file
pytest tests/test_smc_detector.py

# Specific test
pytest tests/test_smc_detector.py::test_detect_order_blocks
```

### Writing Tests

**Frontend Example**:
```typescript
import { render, screen } from '@testing-library/react';
import { Dashboard } from './Dashboard';

describe('Dashboard', () => {
  it('renders market data', async () => {
    render(<Dashboard />);
    const price = await screen.findByText(/BTCUSDT/);
    expect(price).toBeInTheDocument();
  });
});
```

**Python Example**:
```python
import pytest
from smc_detector.indicators import SMCIndicators

@pytest.fixture
def sample_df():
    """Create sample OHLCV DataFrame."""
    return pd.DataFrame({
        'open': [100, 101, 102],
        'high': [105, 106, 107],
        'low': [99, 100, 101],
        'close': [104, 105, 106],
        'volume': [1000, 1100, 1200]
    })

def test_detect_order_blocks(sample_df):
    indicators = SMCIndicators()
    blocks = indicators.detect_order_blocks(sample_df)
    assert isinstance(blocks, list)
```

---

**For more information, see**:
- [API Documentation](./API_DOCUMENTATION.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [Contributing Guide](../CONTRIBUTING.md)

