-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table (extends Supabase auth.users)
CREATE TABLE public.users (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'premium', 'enterprise')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User API keys table (encrypted storage)
CREATE TABLE public.user_api_keys (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    exchange TEXT NOT NULL CHECK (exchange IN ('binance', 'bybit', 'oanda')),
    encrypted_api_key TEXT NOT NULL,
    encrypted_secret TEXT NOT NULL,
    is_testnet BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, exchange)
);

-- User configurations table
CREATE TABLE public.user_configurations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    config_name TEXT NOT NULL DEFAULT 'default',
    config_json JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, config_name)
);

-- Trading sessions table
CREATE TABLE public.trading_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    session_name TEXT NOT NULL,
    status TEXT DEFAULT 'inactive' CHECK (status IN ('inactive', 'active', 'paused', 'stopped', 'error')),
    exchange TEXT NOT NULL,
    config_id UUID REFERENCES public.user_configurations(id),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    total_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(15,8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trades table
CREATE TABLE public.trades (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES public.trading_sessions(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type TEXT NOT NULL CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    executed_price DECIMAL(20,8),
    executed_quantity DECIMAL(20,8),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'filled', 'partially_filled', 'cancelled', 'rejected')),
    exchange_order_id TEXT,
    commission DECIMAL(20,8) DEFAULT 0,
    commission_asset TEXT,
    pnl DECIMAL(15,8),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    execution_time TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- SMC signals table
CREATE TABLE public.smc_signals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('bos', 'choch', 'fvg', 'order_block', 'liquidity_sweep')),
    direction TEXT NOT NULL CHECK (direction IN ('bullish', 'bearish')),
    confidence DECIMAL(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    price_level DECIMAL(20,8) NOT NULL,
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    risk_reward_ratio DECIMAL(10,4),
    is_processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market data cache table (for performance)
CREATE TABLE public.market_data_cache (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('kline', 'ticker', 'orderbook')),
    data JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(symbol, timeframe, data_type)
);

-- Indexes for performance
CREATE INDEX idx_user_api_keys_user_id ON public.user_api_keys(user_id);
CREATE INDEX idx_user_configurations_user_id ON public.user_configurations(user_id);
CREATE INDEX idx_trading_sessions_user_id ON public.trading_sessions(user_id);
CREATE INDEX idx_trading_sessions_status ON public.trading_sessions(status);
CREATE INDEX idx_trades_session_id ON public.trades(session_id);
CREATE INDEX idx_trades_user_id ON public.trades(user_id);
CREATE INDEX idx_trades_symbol ON public.trades(symbol);
CREATE INDEX idx_trades_timestamp ON public.trades(timestamp);
CREATE INDEX idx_smc_signals_user_id ON public.smc_signals(user_id);
CREATE INDEX idx_smc_signals_symbol ON public.smc_signals(symbol);
CREATE INDEX idx_smc_signals_processed ON public.smc_signals(is_processed);
CREATE INDEX idx_smc_signals_created_at ON public.smc_signals(created_at);
CREATE INDEX idx_market_data_cache_symbol_timeframe ON public.market_data_cache(symbol, timeframe);
CREATE INDEX idx_market_data_cache_expires_at ON public.market_data_cache(expires_at);

-- Row Level Security (RLS) policies
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trading_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.smc_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.market_data_cache ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- User API keys policies
CREATE POLICY "Users can manage own API keys" ON public.user_api_keys
    FOR ALL USING (auth.uid() = user_id);

-- User configurations policies
CREATE POLICY "Users can manage own configurations" ON public.user_configurations
    FOR ALL USING (auth.uid() = user_id);

-- Trading sessions policies
CREATE POLICY "Users can manage own trading sessions" ON public.trading_sessions
    FOR ALL USING (auth.uid() = user_id);

-- Trades policies
CREATE POLICY "Users can view own trades" ON public.trades
    FOR ALL USING (auth.uid() = user_id);

-- SMC signals policies
CREATE POLICY "Users can view own signals" ON public.smc_signals
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Public signals for anonymous users" ON public.smc_signals
    FOR SELECT USING (user_id IS NULL);

-- Market data cache policies (public read access)
CREATE POLICY "Market data cache public read" ON public.market_data_cache
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "Market data cache authenticated write" ON public.market_data_cache
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Market data cache authenticated update" ON public.market_data_cache
    FOR UPDATE TO authenticated USING (true);

-- Functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER handle_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_user_api_keys_updated_at
    BEFORE UPDATE ON public.user_api_keys
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_user_configurations_updated_at
    BEFORE UPDATE ON public.user_configurations
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_trading_sessions_updated_at
    BEFORE UPDATE ON public.trading_sessions
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Function to clean expired market data cache
CREATE OR REPLACE FUNCTION public.clean_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM public.market_data_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO authenticated;

-- Grant limited permissions to anonymous users
GRANT SELECT ON public.market_data_cache TO anon;
GRANT SELECT ON public.smc_signals TO anon;