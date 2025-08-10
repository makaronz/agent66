# Testing Heuristics: SMC Trading Agent

## 1. Testing Philosophy

Testing is a core part of the development process, not an afterthought. The goal is to build a robust and reliable system through a multi-layered testing strategy. We aim for high test coverage on all critical components.

## 2. Unit Tests

- **Framework:** `pytest` for Python, standard Rust testing framework.
- **Scope:** Each function should have unit tests covering its logic, including happy paths, edge cases, and expected failures.
- **Location:** `tests/` directory, mirroring the structure of the main application.

## 3. Integration Tests

- **Purpose:** To verify the interactions between different components of the system (e.g., does the `Decision Engine` correctly process a signal from the `SMC Detector`?).
- **Tools:** `pytest` with fixtures to manage services (e.g., starting a mock data provider).

## 4. End-to-End (E2E) Backtesting

- **The Ultimate Test:** The backtesting module serves as the primary E2E test of the entire system's trading logic.
- **Process:** Run the agent against historical data for a variety of market conditions and assets to validate the profitability and robustness of the strategies.
- **Fuzzing:** Introduce malformed data or unexpected market events (e.g., flash crashes) into the backtesting data to ensure the system remains stable.

## 5. Performance Testing

- **Goal:** Ensure the system can handle real-time data flow without significant latency.
- **Tools:** Use profiling tools to identify and optimize bottlenecks, particularly in the data ingestion and execution paths.


## 6. Replicating CI pytest behavior locally

To mirror the CI test environment and avoid failures caused by third‑party pytest plugins autoloaded in your local environment, run tests with plugin autoload disabled. This isolates validation to repository code only.

Recommended commands (macOS/Linux):

```bash
cd smc_trading_agent
# CI-like isolation (plugins disabled) — async tests will be skipped unless plugin enabled explicitly
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q

# CI-like isolation but run asyncio tests by enabling plugin explicitly
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -p pytest_asyncio
```

Notes:
- The repository includes a pytest configuration at `smc_trading_agent/pytest.ini` that disables a known problematic plugin via:
  ```ini
  [pytest]
  addopts = -p no:opik
  markers =
      asyncio: mark a test as asyncio
  asyncio_mode = auto
  ```
- The environment variable `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` prevents autoloading of external plugins that may be present in your Python environment.
- Combined, these settings reproduce CI isolation locally and help ensure deterministic, repo‑scoped test runs.

