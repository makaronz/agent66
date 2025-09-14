# SMC Trading Agent - Integration Tests

This directory contains comprehensive integration tests for the SMC Trading Agent that validate real exchange API integrations using sandbox/testnet environments.

## Overview

The integration tests cover the following requirements:

- **1.5**: Real exchange API integration verification (requires API keys)
- **2.5**: Comprehensive error handling tests for exchange failures
- **3.3**: Circuit breaker testing with real API rate limits and failover mechanism testing between exchanges

## Test Structure

### Test Files

1. **`test_sandbox_integration.py`** - Core sandbox/testnet integration tests

   - Sandbox configuration for Binance, Bybit, and Oanda
   - Real API connection testing
   - Rate limiting validation
   - Error handling with real APIs
   - Production factory integration

2. **`test_circuit_breaker_integration.py`** - Circuit breaker integration tests

   - Circuit breaker behavior with real API rate limits
   - Integration with exchange connectors and error handling
   - Real-time monitoring and alerting
   - Performance testing under load

3. **`test_failover_integration.py`** - Failover mechanism tests
   - Failover between exchanges with real API connections
   - Health monitoring and automatic failover triggering
   - Recovery and failback mechanisms
   - Complex failover scenarios

### Configuration Files

- **`conftest.py`** - Test configuration and fixtures
- **`run_integration_tests.py`** - Comprehensive test runner
- **`README.md`** - This documentation file

## Prerequisites

### Exchange API Credentials

To run integration tests, you need API credentials for sandbox/testnet environments:

#### Binance Testnet

```bash
export BINANCE_TESTNET_API_KEY="your_binance_testnet_api_key"
export BINANCE_TESTNET_API_SECRET="your_binance_testnet_api_secret"
```

**How to get Binance testnet credentials:**

1. Visit [Binance Testnet](https://testnet.binance.vision/)
2. Create an account or log in
3. Generate API keys in the API Management section
4. Enable spot trading permissions

#### Bybit Testnet

```bash
export BYBIT_TESTNET_API_KEY="your_bybit_testnet_api_key"
export BYBIT_TESTNET_API_SECRET="your_bybit_testnet_api_secret"
```

**How to get Bybit testnet credentials:**

1. Visit [Bybit Testnet](https://testnet.bybit.com/)
2. Create an account or log in
3. Go to API Management and create new API key
4. Enable trading permissions for testnet

#### Oanda Practice Account

```bash
export OANDA_PRACTICE_API_KEY="your_oanda_practice_api_key"
export OANDA_PRACTICE_API_SECRET="your_oanda_practice_api_secret"
export OANDA_PRACTICE_ACCOUNT_ID="your_oanda_practice_account_id"
```

**How to get Oanda practice credentials:**

1. Visit [Oanda](https://www.oanda.com/)
2. Create a practice account
3. Generate API token in the API section
4. Note your practice account ID

### Environment Setup

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio
   ```

2. **Set Environment Variables**

   ```bash
   # Copy and modify the example
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Verify Setup**
   ```bash
   python tests/integration/run_integration_tests.py --check-env
   ```

## Running Tests

### Using the Test Runner (Recommended)

The integration test runner provides multiple options:

```bash
# Check environment setup
python tests/integration/run_integration_tests.py --check-env

# Run basic connection tests
python tests/integration/run_integration_tests.py --suite basic

# Run full integration suite
python tests/integration/run_integration_tests.py --suite full

# Run specific test pattern
python tests/integration/run_integration_tests.py --custom "binance and connection"

# Interactive mode
python tests/integration/run_integration_tests.py
```

### Available Test Suites

1. **Basic Tests** (`--suite basic`)

   - Connection testing for all exchanges
   - Basic API functionality validation
   - Configuration verification

2. **Rate Limiting Tests** (`--suite rate-limiting`)

   - Rate limit validation with real APIs
   - Rate limiter integration testing
   - Backoff and retry mechanism validation

3. **Error Handling Tests** (`--suite error-handling`)

   - Real API error scenarios
   - Error classification and recovery
   - Integration with error handling system

4. **Circuit Breaker Tests** (`--suite circuit-breaker`)

   - Circuit breaker triggering with real conditions
   - Integration with risk management
   - Performance under load

5. **Failover Tests** (`--suite failover`)

   - Failover between real exchanges
   - Health monitoring and recovery
   - Complex failover scenarios

6. **Full Suite** (`--suite full`)

   - All integration tests
   - Comprehensive validation
   - End-to-end scenarios

7. **Performance Tests** (`--suite performance`)
   - Load testing with real APIs
   - Concurrent operation validation
   - Performance benchmarking

### Using Pytest Directly

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_sandbox_integration.py -v

# Run tests with specific marker
pytest tests/integration/ -m "integration" -v

# Run tests matching pattern
pytest tests/integration/ -k "binance and connection" -v

# Run with detailed output
pytest tests/integration/ -v -s --tb=short
```

## Test Configuration

### Markers

- `@pytest.mark.integration` - Integration test requiring real API credentials
- `@pytest.mark.slow` - Slow running test (performance, load testing)

### Fixtures

- `sandbox_config` - Sandbox configuration with API credentials
- `skip_if_no_credentials` - Skip test if no credentials available
- `circuit_breaker_harness` - Circuit breaker test harness
- `failover_harness` - Failover test harness

### Environment Variables

| Variable                     | Description                | Required   |
| ---------------------------- | -------------------------- | ---------- |
| `BINANCE_TESTNET_API_KEY`    | Binance testnet API key    | Optional\* |
| `BINANCE_TESTNET_API_SECRET` | Binance testnet API secret | Optional\* |
| `BYBIT_TESTNET_API_KEY`      | Bybit testnet API key      | Optional\* |
| `BYBIT_TESTNET_API_SECRET`   | Bybit testnet API secret   | Optional\* |
| `OANDA_PRACTICE_API_KEY`     | Oanda practice API key     | Optional\* |
| `OANDA_PRACTICE_API_SECRET`  | Oanda practice API secret  | Optional\* |
| `OANDA_PRACTICE_ACCOUNT_ID`  | Oanda practice account ID  | Optional\* |

\*At least one exchange's credentials are required to run integration tests.

## Test Scenarios

### Connection Testing

- WebSocket connection establishment
- REST API connectivity
- Authentication validation
- Health status monitoring

### Rate Limiting

- Rate limit enforcement
- Backoff strategies
- Burst handling
- Recovery mechanisms

### Error Handling

- API error classification
- Network error recovery
- Authentication failures
- Timeout handling

### Circuit Breaker

- Risk threshold monitoring
- Automatic triggering
- Position closure
- Alert notifications

### Failover Mechanism

- Health monitoring
- Automatic failover
- Manual failover
- Recovery and failback
- Cascading failures

## Troubleshooting

### Common Issues

1. **No Credentials Available**

   ```
   Error: No sandbox/testnet credentials available
   ```

   **Solution**: Set environment variables for at least one exchange

2. **Connection Timeouts**

   ```
   Error: Connection timeout to exchange API
   ```

   **Solution**: Check network connectivity and API status

3. **Rate Limit Errors**

   ```
   Error: Rate limit exceeded
   ```

   **Solution**: This is expected in rate limiting tests

4. **Authentication Failures**
   ```
   Error: Invalid API key or signature
   ```
   **Solution**: Verify API credentials and permissions

### Debug Mode

Enable verbose logging for debugging:

```bash
python tests/integration/run_integration_tests.py --suite basic --verbose
```

### Test Isolation

Each test is designed to be independent and can be run in isolation:

```bash
pytest tests/integration/test_sandbox_integration.py::TestBinanceTestnetIntegration::test_binance_testnet_connection -v
```

## Performance Considerations

### Test Duration

- Basic tests: ~2-5 minutes
- Rate limiting tests: ~5-10 minutes
- Circuit breaker tests: ~3-8 minutes
- Failover tests: ~5-15 minutes
- Full suite: ~15-30 minutes

### Resource Usage

- Network: Moderate (API calls to exchanges)
- CPU: Low to moderate
- Memory: Low (~100-500MB)

### Rate Limits

Tests are designed to respect exchange rate limits:

- Conservative request rates
- Proper backoff strategies
- Rate limit testing is controlled

## Continuous Integration

### GitHub Actions Integration

```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    if: contains(github.event.head_commit.message, '[integration]')

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Run integration tests
        env:
          BINANCE_TESTNET_API_KEY: ${{ secrets.BINANCE_TESTNET_API_KEY }}
          BINANCE_TESTNET_API_SECRET: ${{ secrets.BINANCE_TESTNET_API_SECRET }}
          BYBIT_TESTNET_API_KEY: ${{ secrets.BYBIT_TESTNET_API_KEY }}
          BYBIT_TESTNET_API_SECRET: ${{ secrets.BYBIT_TESTNET_API_SECRET }}
        run: |
          python tests/integration/run_integration_tests.py --suite basic
```

### Local CI Testing

```bash
# Run tests that would run in CI
python tests/integration/run_integration_tests.py --suite basic --verbose
```

## Security Considerations

### API Key Safety

- Use testnet/sandbox credentials only
- Never commit credentials to version control
- Rotate credentials regularly
- Use minimal required permissions

### Test Data

- All tests use sandbox/testnet environments
- No real money or production data
- Test data is automatically cleaned up

### Network Security

- Tests connect to official exchange testnet endpoints
- All connections use HTTPS/WSS
- No sensitive data in logs (credentials are masked)

## Contributing

### Adding New Tests

1. **Create test file** in `tests/integration/`
2. **Use appropriate fixtures** from `conftest.py`
3. **Add integration marker**: `@pytest.mark.integration`
4. **Handle missing credentials** gracefully
5. **Update test runner** if needed

### Test Guidelines

- Tests should be independent and idempotent
- Use descriptive test names and docstrings
- Handle network failures gracefully
- Respect rate limits and be good API citizens
- Clean up resources in finally blocks

### Example Test Structure

```python
@pytest.mark.asyncio
async def test_new_feature(sandbox_config, skip_if_no_credentials):
    """Test new feature with real API integration."""
    if ExchangeType.BINANCE not in skip_if_no_credentials:
        pytest.skip("Binance credentials not available")

    connector = BinanceConnector(sandbox_config.binance_testnet)

    try:
        # Test implementation
        result = await connector.some_new_feature()
        assert result is not None

    finally:
        # Cleanup
        await connector.disconnect_websocket()
```

## Support

For issues with integration tests:

1. Check environment variables with `--check-env`
2. Run basic tests first to verify setup
3. Check exchange API status pages
4. Review test logs for specific error messages
5. Consult exchange API documentation

## License

These integration tests are part of the SMC Trading Agent project and follow the same license terms.
