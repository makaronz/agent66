# Contributing to SMC Trading Agent

Thank you for your interest in contributing to the SMC Trading Agent project! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Project Structure](#project-structure)
5. [Coding Standards](#coding-standards)
6. [Commit Guidelines](#commit-guidelines)
7. [Pull Request Process](#pull-request-process)
8. [Testing Requirements](#testing-requirements)
9. [Documentation Standards](#documentation-standards)
10. [Report Issues](#report-issues)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Focus on constructive feedback
- Accept criticism gracefully
- Help create a positive environment for all contributors

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Node.js** 18+ installed
- **Python** 3.9+ installed
- **Git** configured with your name and email
- Basic knowledge of:
  - TypeScript/JavaScript
  - Python
  - React
  - Trading concepts (optional but helpful)

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/smc_trading_agent.git
   cd smc_trading_agent
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/smc_trading_agent.git
   ```

## Development Setup

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Install development dependencies (if needed)
pip install -r test-requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your configuration
# For development, you can use test API keys
nano .env
```

### 3. Verify Setup

```bash
# Run TypeScript type checking
npm run check

# Run Python linting
flake8 . --exclude=node_modules,venv,__pycache__

# Run tests
npm test
pytest tests/
```

## Project Structure

### Key Directories

```
smc_trading_agent/
├── api/                    # TypeScript backend (Express + WebSocket)
│   ├── app.ts             # Express app setup
│   ├── routes/            # API route handlers
│   ├── services/          # Business logic services
│   └── integrations/      # Exchange integrations
├── src/                   # React frontend
│   ├── pages/            # Page components
│   ├── components/       # Reusable components
│   └── services/         # API clients
├── execution_engine/      # Python trading execution
├── risk_manager/         # Risk management logic
├── smc_detector/         # SMC pattern detection
├── data_pipeline/        # Data ingestion and processing
├── decision_engine/      # Trading decision logic
├── config/               # Configuration files
├── tests/                # Test suites
└── docs/                 # Documentation
```

### Entry Points

- **Frontend**: `src/main.tsx` (React app entry)
- **TypeScript Backend**: `api/server.ts` (Express server)
- **Python Agent**: `main.py` (Main trading loop)

## Coding Standards

### TypeScript/JavaScript

**Style Guide**: Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)

**Key Rules**:
- Use TypeScript for all new code
- Prefer `const` over `let`, avoid `var`
- Use arrow functions for callbacks
- Use async/await instead of promises
- Export named exports, avoid default exports where possible

**Example**:
```typescript
// ✅ Good
export async function fetchMarketData(symbol: string): Promise<MarketData> {
  const response = await api.get(`/market-data/${symbol}`);
  return response.data;
}

// ❌ Bad
export default async (symbol) => {
  const response = await api.get('/market-data/' + symbol);
  return response.data;
}
```

### Python

**Style Guide**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)

**Key Rules**:
- Use type hints for all function signatures
- Follow PEP 8 formatting (use `black` formatter)
- Use docstrings for all public functions and classes
- Prefer `pathlib` over `os.path`
- Use async/await for I/O operations

**Example**:
```python
# ✅ Good
async def fetch_ohlcv_data(
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data from the data pipeline.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Timeframe (e.g., '1h', '4h', '1d')
        limit: Number of candles to fetch
        
    Returns:
        DataFrame with OHLCV data or None if error
    """
    # Implementation
    pass

# ❌ Bad
def fetch_ohlcv(symbol, tf="1h", lim=100):
    # no type hints, no docstring
    pass
```

### Code Formatting

**TypeScript**:
```bash
# Format code with Prettier
npm run lint --fix
```

**Python**:
```bash
# Format code with Black
black .

# Sort imports
isort .

# Type checking
mypy .
```

## Commit Guidelines

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Maintenance tasks

### Examples

```bash
# Good commit messages
feat(trading): add stop-loss trailing feature
fix(api): resolve WebSocket reconnection issue
docs(readme): update installation instructions
refactor(risk): simplify position sizing calculation
test(smc): add unit tests for order block detection

# Bad commit messages
fix bug
update
changes
wip
```

### Commit Best Practices

1. **Write clear, descriptive messages**
2. **Keep commits focused** - one logical change per commit
3. **Use present tense** ("add feature" not "added feature")
4. **Reference issues** when applicable: `fix #123`

## Pull Request Process

### Before Submitting

1. **Update your fork**:
   ```bash
   git checkout main
   git fetch upstream
   git merge upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

3. **Make your changes** following coding standards

4. **Run tests**:
   ```bash
   # Frontend tests
   npm test
   
   # Backend tests
   pytest tests/
   
   # Type checking
   npm run check
   mypy .
   ```

5. **Update documentation** if needed

### PR Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No console.logs or debug code left
- [ ] Error handling implemented
- [ ] Type safety ensured (TypeScript/Python types)

### PR Title Format

Use the same format as commit messages:
```
feat(trading): add trailing stop-loss feature
fix(api): resolve WebSocket reconnection bug
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

## Testing Requirements

### Test Coverage

- **Minimum coverage**: 70% for new code
- **Critical paths**: 100% coverage required
- **Integration tests**: Required for API endpoints

### Running Tests

```bash
# All tests
npm run test:all

# Frontend tests only
npm test

# Backend tests only
pytest tests/

# With coverage
pytest --cov=. tests/
```

### Writing Tests

**TypeScript Example**:
```typescript
import { describe, it, expect } from 'vitest';
import { fetchMarketData } from './api';

describe('fetchMarketData', () => {
  it('should return market data for valid symbol', async () => {
    const data = await fetchMarketData('BTCUSDT');
    expect(data).toHaveProperty('symbol', 'BTCUSDT');
    expect(data).toHaveProperty('price');
  });
  
  it('should throw error for invalid symbol', async () => {
    await expect(fetchMarketData('INVALID')).rejects.toThrow();
  });
});
```

**Python Example**:
```python
import pytest
from smc_detector.indicators import SMCIndicators

def test_detect_order_blocks():
    """Test order block detection."""
    indicators = SMCIndicators()
    df = create_test_dataframe()
    
    blocks = indicators.detect_order_blocks(df)
    
    assert len(blocks) > 0
    assert all('timestamp' in block for block in blocks)
```

## Documentation Standards

### Code Documentation

**TypeScript**:
```typescript
/**
 * Fetches live market data for a given symbol.
 * 
 * @param symbol - Trading symbol (e.g., 'BTCUSDT')
 * @param timeframe - Optional timeframe for OHLCV data
 * @returns Promise resolving to market data
 * @throws {Error} If API request fails
 */
export async function fetchMarketData(
  symbol: string,
  timeframe?: string
): Promise<MarketData> {
  // Implementation
}
```

**Python**:
```python
def detect_order_blocks(
    df: pd.DataFrame,
    lookback: int = 20
) -> List[Dict[str, Any]]:
    """
    Detect order blocks in price action.
    
    Args:
        df: DataFrame with OHLCV columns (open, high, low, close, volume)
        lookback: Number of candles to look back for pattern detection
        
    Returns:
        List of detected order blocks with timestamps and price levels
        
    Raises:
        ValueError: If DataFrame is empty or missing required columns
    """
    # Implementation
```

### README Updates

When adding features:
- Update main README.md if feature is user-facing
- Update relevant documentation in `docs/` directory
- Add examples if applicable

## Report Issues

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen

**Environment**
- OS: [e.g., macOS 14.0]
- Node.js version: [e.g., 18.17.0]
- Python version: [e.g., 3.11.0]
- Browser (if applicable): [e.g., Chrome 120]

**Additional context**
Screenshots, logs, etc.
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Clear description of the problem

**Describe the solution you'd like**
Clear description of desired solution

**Describe alternatives you've considered**
Alternative solutions or features

**Additional context**
Any other context, mockups, etc.
```

## Development Workflow

### Typical Workflow

1. **Fork and clone** the repository
2. **Create feature branch** from `main`
3. **Make changes** following coding standards
4. **Write tests** for new features
5. **Run tests** and ensure they pass
6. **Update documentation**
7. **Commit** with conventional commit format
8. **Push** to your fork
9. **Create PR** with clear description
10. **Address review feedback**
11. **Wait for approval and merge**

### Code Review Process

- All PRs require at least one approval
- Maintainers will review within 2-3 business days
- Address feedback promptly
- Keep PRs focused and manageable in size

## Getting Help

### Resources

- **Documentation**: See `docs/` directory
- **Issues**: Check existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions

### Contact

- Open an issue for bugs or feature requests
- Use Discussions for questions and ideas
- For security issues, please email privately

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

**Thank you for contributing to SMC Trading Agent!** 🚀




