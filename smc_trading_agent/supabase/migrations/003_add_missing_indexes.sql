-- Production Performance Indexes (safe, concurrent, idempotent)
-- NOTE: Run during low-traffic window. Requires proper privileges.

-- Trades
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_id_created_at
  ON trades (user_id, timestamp);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol_timestamp
  ON trades (symbol, timestamp);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_status
  ON trades (status);

-- SMC Signals
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_user_id_created_at
  ON smc_signals (user_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_symbol_type_dir
  ON smc_signals (symbol, signal_type, direction, created_at);

-- Trading Sessions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_sessions_user_id_created_at
  ON trading_sessions (user_id, start_time);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_sessions_status
  ON trading_sessions (status);

-- Users (additional filter)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_subscription_tier
  ON users (subscription_tier);


