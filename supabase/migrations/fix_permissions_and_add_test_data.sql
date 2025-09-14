-- Grant permissions to anon and authenticated roles for all trading tables
GRANT SELECT ON trades TO anon;
GRANT ALL PRIVILEGES ON trades TO authenticated;

GRANT SELECT ON smc_signals TO anon;
GRANT ALL PRIVILEGES ON smc_signals TO authenticated;

GRANT SELECT ON trading_sessions TO anon;
GRANT ALL PRIVILEGES ON trading_sessions TO authenticated;

GRANT SELECT ON market_data_cache TO anon;
GRANT ALL PRIVILEGES ON market_data_cache TO authenticated;

-- Enable realtime for all trading tables
ALTER PUBLICATION supabase_realtime ADD TABLE trades;
ALTER PUBLICATION supabase_realtime ADD TABLE smc_signals;
ALTER PUBLICATION supabase_realtime ADD TABLE trading_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE market_data_cache;

-- Insert sample SMC signals for testing (using first available user_id)
INSERT INTO smc_signals (user_id, symbol, timeframe, signal_type, direction, confidence, price_level, stop_loss, take_profit, risk_reward_ratio, metadata) 
SELECT 
    (SELECT id FROM users LIMIT 1),
    'BTCUSDT', '1h', 'bos', 'bullish', 0.85, 45000.00, 44500.00, 46000.00, 2.0, '{"pattern": "break_of_structure", "volume_confirmation": true}'::jsonb
WHERE EXISTS (SELECT 1 FROM users)
UNION ALL
SELECT 
    (SELECT id FROM users LIMIT 1),
    'ETHUSDT', '4h', 'fvg', 'bearish', 0.78, 2800.00, 2850.00, 2700.00, 1.5, '{"pattern": "fair_value_gap", "liquidity_level": "high"}'::jsonb
WHERE EXISTS (SELECT 1 FROM users)
UNION ALL
SELECT 
    (SELECT id FROM users LIMIT 1),
    'ADAUSDT', '1h', 'order_block', 'bullish', 0.92, 0.45, 0.43, 0.48, 2.5, '{"pattern": "bullish_order_block", "institutional_level": true}'::jsonb
WHERE EXISTS (SELECT 1 FROM users);

-- Insert sample trading sessions (using first available user_id)
INSERT INTO trading_sessions (user_id, session_name, status, exchange, start_time, total_trades, total_pnl) 
SELECT 
    (SELECT id FROM users LIMIT 1),
    'Live Trading Session', 'active', 'binance', NOW() - INTERVAL '2 hours', 15, 245.50
WHERE EXISTS (SELECT 1 FROM users)
UNION ALL
SELECT 
    (SELECT id FROM users LIMIT 1),
    'Demo Session', 'paused', 'binance', NOW() - INTERVAL '1 day', 8, -12.30
WHERE EXISTS (SELECT 1 FROM users);

-- Insert sample trades
INSERT INTO trades (session_id, user_id, symbol, side, order_type, quantity, price, executed_price, executed_quantity, status, commission, pnl, execution_time) 
SELECT 
    (SELECT id FROM trading_sessions WHERE session_name = 'Live Trading Session' LIMIT 1),
    (SELECT id FROM users LIMIT 1),
    'BTCUSDT', 'buy', 'market', 0.001, NULL, 44850.00, 0.001, 'filled', 0.045, 15.20, NOW() - INTERVAL '30 minutes'
WHERE EXISTS (SELECT 1 FROM users) AND EXISTS (SELECT 1 FROM trading_sessions WHERE session_name = 'Live Trading Session')
UNION ALL
SELECT 
    (SELECT id FROM trading_sessions WHERE session_name = 'Live Trading Session' LIMIT 1),
    (SELECT id FROM users LIMIT 1),
    'ETHUSDT', 'sell', 'limit', 0.01, 2820.00, 2815.00, 0.01, 'filled', 0.028, 8.50, NOW() - INTERVAL '15 minutes'
WHERE EXISTS (SELECT 1 FROM users) AND EXISTS (SELECT 1 FROM trading_sessions WHERE session_name = 'Live Trading Session');

-- Insert sample market data cache
INSERT INTO market_data_cache (symbol, timeframe, data_type, data, expires_at) VALUES
('BTCUSDT', '1m', 'ticker', '{"price": 45120.50, "change": 2.34, "volume": 1234567.89, "high": 45500.00, "low": 44800.00}'::jsonb, NOW() + INTERVAL '1 minute'),
('ETHUSDT', '1m', 'ticker', '{"price": 2798.75, "change": -1.25, "volume": 987654.32, "high": 2850.00, "low": 2780.00}'::jsonb, NOW() + INTERVAL '1 minute'),
('ADAUSDT', '1m', 'ticker', '{"price": 0.4523, "change": 0.85, "volume": 5432109.87, "high": 0.4580, "low": 0.4480}'::jsonb, NOW() + INTERVAL '1 minute');