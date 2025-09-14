-- Performance optimization indexes for SMC Trading Agent
-- This migration adds missing indexes based on query pattern analysis

-- Enable pg_stat_statements extension for query analysis
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Composite indexes for common query patterns

-- Trading sessions - frequently queried by user and status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_sessions_user_status 
ON public.trading_sessions(user_id, status) 
WHERE status IN ('active', 'paused');

-- Trading sessions - time-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_sessions_start_time 
ON public.trading_sessions(start_time DESC) 
WHERE start_time IS NOT NULL;

-- Trades - composite index for user and session queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_session_time 
ON public.trades(user_id, session_id, timestamp DESC);

-- Trades - symbol and time for market analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol_time 
ON public.trades(symbol, timestamp DESC);

-- Trades - status for order management
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_status_time 
ON public.trades(status, timestamp DESC) 
WHERE status IN ('pending', 'partially_filled');

-- SMC signals - composite index for user and processing status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_user_processed 
ON public.smc_signals(user_id, is_processed, created_at DESC);

-- SMC signals - symbol and signal type for pattern analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_symbol_type 
ON public.smc_signals(symbol, signal_type, created_at DESC);

-- SMC signals - confidence and direction for filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_confidence_direction 
ON public.smc_signals(confidence DESC, direction) 
WHERE confidence >= 0.7;

-- SMC signals - expiration for cleanup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_expires_at 
ON public.smc_signals(expires_at) 
WHERE expires_at IS NOT NULL;

-- User API keys - exchange lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_api_keys_exchange_active 
ON public.user_api_keys(exchange, is_active) 
WHERE is_active = true;

-- Market data cache - efficient lookups and cleanup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_cache_lookup 
ON public.market_data_cache(symbol, timeframe, data_type, expires_at);

-- Partial indexes for active/recent data only

-- Active trading sessions only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_sessions_active 
ON public.trading_sessions(user_id, updated_at DESC) 
WHERE status = 'active';

-- Recent trades (last 30 days) for performance queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_recent 
ON public.trades(user_id, symbol, timestamp DESC) 
WHERE timestamp > (NOW() - INTERVAL '30 days');

-- Unprocessed signals for real-time processing
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_unprocessed 
ON public.smc_signals(created_at ASC) 
WHERE is_processed = false AND (expires_at IS NULL OR expires_at > NOW());

-- Functional indexes for common operations

-- Case-insensitive symbol lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol_lower 
ON public.trades(LOWER(symbol));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_symbol_lower 
ON public.smc_signals(LOWER(symbol));

-- Date-based partitioning support indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_date 
ON public.trades(DATE(timestamp));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_smc_signals_date 
ON public.smc_signals(DATE(created_at));

-- Indexes for aggregation queries

-- PnL calculations by user and time period
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_pnl_calc 
ON public.trades(user_id, timestamp, pnl) 
WHERE pnl IS NOT NULL;

-- Volume analysis by symbol
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_volume_analysis 
ON public.trades(symbol, timestamp, quantity, executed_price) 
WHERE status = 'filled';

-- Performance monitoring indexes

-- Query performance tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_sessions_performance 
ON public.trading_sessions(total_trades, total_pnl, updated_at DESC) 
WHERE status IN ('active', 'stopped');

-- User activity tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_activity 
ON public.users(updated_at DESC, subscription_tier);

-- Cleanup and maintenance indexes

-- Expired cache entries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_cache_cleanup 
ON public.market_data_cache(expires_at) 
WHERE expires_at < NOW();

-- Old completed trades for archival
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_archival 
ON public.trades(timestamp) 
WHERE status IN ('filled', 'cancelled') AND timestamp < (NOW() - INTERVAL '1 year');

-- Statistics and monitoring views

-- Create materialized view for trading performance metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS public.trading_performance_summary AS
SELECT 
    user_id,
    DATE_TRUNC('day', timestamp) as trading_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl,
    MAX(pnl) as max_win,
    MIN(pnl) as max_loss,
    COUNT(DISTINCT symbol) as symbols_traded
FROM public.trades 
WHERE status = 'filled' AND pnl IS NOT NULL
GROUP BY user_id, DATE_TRUNC('day', timestamp);

-- Index for the materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_trading_performance_summary_unique 
ON public.trading_performance_summary(user_id, trading_date);

CREATE INDEX IF NOT EXISTS idx_trading_performance_summary_date 
ON public.trading_performance_summary(trading_date DESC);

-- Create materialized view for SMC signal effectiveness
CREATE MATERIALIZED VIEW IF NOT EXISTS public.smc_signal_effectiveness AS
SELECT 
    signal_type,
    direction,
    symbol,
    DATE_TRUNC('day', created_at) as signal_date,
    COUNT(*) as total_signals,
    AVG(confidence) as avg_confidence,
    COUNT(CASE WHEN is_processed THEN 1 END) as processed_signals,
    -- This would need to be joined with actual trade results
    0.0 as success_rate  -- Placeholder
FROM public.smc_signals
GROUP BY signal_type, direction, symbol, DATE_TRUNC('day', created_at);

-- Index for SMC signal effectiveness view
CREATE UNIQUE INDEX IF NOT EXISTS idx_smc_signal_effectiveness_unique 
ON public.smc_signal_effectiveness(signal_type, direction, symbol, signal_date);

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_performance_views()
RETURNS void AS $
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.trading_performance_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.smc_signal_effectiveness;
END;
$ LANGUAGE plpgsql;

-- Function to analyze table statistics and suggest optimizations
CREATE OR REPLACE FUNCTION analyze_table_performance()
RETURNS TABLE(
    table_name text,
    seq_scan bigint,
    seq_tup_read bigint,
    idx_scan bigint,
    idx_tup_fetch bigint,
    n_tup_ins bigint,
    n_tup_upd bigint,
    n_tup_del bigint,
    n_live_tup bigint,
    n_dead_tup bigint,
    seq_scan_ratio numeric,
    suggestion text
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        st.relname::text,
        st.seq_scan,
        st.seq_tup_read,
        st.idx_scan,
        st.idx_tup_fetch,
        st.n_tup_ins,
        st.n_tup_upd,
        st.n_tup_del,
        st.n_live_tup,
        st.n_dead_tup,
        CASE 
            WHEN (st.seq_scan + st.idx_scan) > 0 
            THEN ROUND(st.seq_scan::numeric / (st.seq_scan + st.idx_scan), 4)
            ELSE 0
        END as seq_scan_ratio,
        CASE 
            WHEN st.seq_scan > st.idx_scan AND st.n_live_tup > 1000 
            THEN 'Consider adding indexes - high sequential scan ratio'
            WHEN st.n_dead_tup > st.n_live_tup * 0.1 
            THEN 'Consider VACUUM - high dead tuple ratio'
            WHEN st.seq_tup_read > st.n_live_tup * 10 
            THEN 'Inefficient queries detected - review query patterns'
            ELSE 'Performance looks good'
        END as suggestion
    FROM pg_stat_user_tables st
    WHERE st.schemaname = 'public'
    ORDER BY st.seq_scan DESC, st.n_live_tup DESC;
END;
$ LANGUAGE plpgsql;

-- Function to get slow query recommendations
CREATE OR REPLACE FUNCTION get_slow_query_recommendations()
RETURNS TABLE(
    query_hash text,
    query text,
    calls bigint,
    total_exec_time numeric,
    mean_exec_time numeric,
    recommendation text
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        md5(pss.query) as query_hash,
        pss.query,
        pss.calls,
        ROUND(pss.total_exec_time::numeric, 2),
        ROUND(pss.mean_exec_time::numeric, 2),
        CASE 
            WHEN pss.mean_exec_time > 1000 THEN 'Critical: Review query structure and add indexes'
            WHEN pss.mean_exec_time > 500 THEN 'Warning: Consider optimization'
            WHEN pss.calls > 10000 AND pss.mean_exec_time > 100 THEN 'High frequency query - optimize or cache'
            ELSE 'Monitor performance'
        END as recommendation
    FROM pg_stat_statements pss
    WHERE pss.mean_exec_time > 100  -- Queries taking more than 100ms on average
    ORDER BY pss.total_exec_time DESC
    LIMIT 20;
END;
$ LANGUAGE plpgsql;

-- Create a function to automatically maintain indexes
CREATE OR REPLACE FUNCTION maintain_database_performance()
RETURNS void AS $
BEGIN
    -- Update table statistics
    ANALYZE;
    
    -- Refresh materialized views
    PERFORM refresh_performance_views();
    
    -- Clean up expired cache entries
    DELETE FROM public.market_data_cache WHERE expires_at < NOW();
    
    -- Log maintenance completion
    INSERT INTO public.system_logs (log_level, message, created_at) 
    VALUES ('INFO', 'Database performance maintenance completed', NOW())
    ON CONFLICT DO NOTHING;
    
EXCEPTION WHEN OTHERS THEN
    -- Log any errors
    INSERT INTO public.system_logs (log_level, message, created_at) 
    VALUES ('ERROR', 'Database maintenance failed: ' || SQLERRM, NOW())
    ON CONFLICT DO NOTHING;
END;
$ LANGUAGE plpgsql;

-- Create system logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.system_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    log_level TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_logs_level_time 
ON public.system_logs(log_level, created_at DESC);

-- Grant necessary permissions
GRANT SELECT ON pg_stat_statements TO authenticated;
GRANT EXECUTE ON FUNCTION analyze_table_performance() TO authenticated;
GRANT EXECUTE ON FUNCTION get_slow_query_recommendations() TO authenticated;
GRANT EXECUTE ON FUNCTION refresh_performance_views() TO authenticated;

-- Schedule automatic maintenance (this would typically be done via cron or pg_cron)
-- For now, we'll create the function and let the application call it periodically

COMMENT ON FUNCTION maintain_database_performance() IS 'Performs routine database maintenance including statistics updates and cache cleanup';
COMMENT ON FUNCTION analyze_table_performance() IS 'Analyzes table performance and provides optimization suggestions';
COMMENT ON FUNCTION get_slow_query_recommendations() IS 'Returns slow queries with optimization recommendations';
COMMENT ON MATERIALIZED VIEW public.trading_performance_summary IS 'Daily trading performance metrics by user';
COMMENT ON MATERIALIZED VIEW public.smc_signal_effectiveness IS 'SMC signal effectiveness metrics by type and symbol';