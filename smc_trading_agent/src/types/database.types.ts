export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string
          email: string
          full_name: string | null
          avatar_url: string | null
          subscription_tier: 'free' | 'premium' | 'enterprise'
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          email: string
          full_name?: string | null
          avatar_url?: string | null
          subscription_tier?: 'free' | 'premium' | 'enterprise'
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          email?: string
          full_name?: string | null
          avatar_url?: string | null
          subscription_tier?: 'free' | 'premium' | 'enterprise'
          created_at?: string
          updated_at?: string
        }
      }
      user_api_keys: {
        Row: {
          id: string
          user_id: string
          exchange: 'binance' | 'bybit' | 'oanda'
          encrypted_api_key: string
          encrypted_secret: string
          is_testnet: boolean
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          exchange: 'binance' | 'bybit' | 'oanda'
          encrypted_api_key: string
          encrypted_secret: string
          is_testnet?: boolean
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          exchange?: 'binance' | 'bybit' | 'oanda'
          encrypted_api_key?: string
          encrypted_secret?: string
          is_testnet?: boolean
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
      }
      user_configurations: {
        Row: {
          id: string
          user_id: string
          config_name: string
          config_json: Json
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          config_name?: string
          config_json?: Json
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          config_name?: string
          config_json?: Json
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
      }
      trading_sessions: {
        Row: {
          id: string
          user_id: string
          session_name: string
          status: 'inactive' | 'active' | 'paused' | 'stopped' | 'error'
          exchange: string
          config_id: string | null
          start_time: string | null
          end_time: string | null
          total_trades: number
          total_pnl: number
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          user_id: string
          session_name: string
          status?: 'inactive' | 'active' | 'paused' | 'stopped' | 'error'
          exchange: string
          config_id?: string | null
          start_time?: string | null
          end_time?: string | null
          total_trades?: number
          total_pnl?: number
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          user_id?: string
          session_name?: string
          status?: 'inactive' | 'active' | 'paused' | 'stopped' | 'error'
          exchange?: string
          config_id?: string | null
          start_time?: string | null
          end_time?: string | null
          total_trades?: number
          total_pnl?: number
          created_at?: string
          updated_at?: string
        }
      }
      trades: {
        Row: {
          id: string
          session_id: string
          user_id: string
          symbol: string
          side: 'buy' | 'sell'
          order_type: 'market' | 'limit' | 'stop' | 'stop_limit'
          quantity: number
          price: number | null
          executed_price: number | null
          executed_quantity: number | null
          status: 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected'
          exchange_order_id: string | null
          commission: number
          commission_asset: string | null
          pnl: number | null
          timestamp: string
          execution_time: string | null
          metadata: Json
        }
        Insert: {
          id?: string
          session_id: string
          user_id: string
          symbol: string
          side: 'buy' | 'sell'
          order_type: 'market' | 'limit' | 'stop' | 'stop_limit'
          quantity: number
          price?: number | null
          executed_price?: number | null
          executed_quantity?: number | null
          status?: 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected'
          exchange_order_id?: string | null
          commission?: number
          commission_asset?: string | null
          pnl?: number | null
          timestamp?: string
          execution_time?: string | null
          metadata?: Json
        }
        Update: {
          id?: string
          session_id?: string
          user_id?: string
          symbol?: string
          side?: 'buy' | 'sell'
          order_type?: 'market' | 'limit' | 'stop' | 'stop_limit'
          quantity?: number
          price?: number | null
          executed_price?: number | null
          executed_quantity?: number | null
          status?: 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected'
          exchange_order_id?: string | null
          commission?: number
          commission_asset?: string | null
          pnl?: number | null
          timestamp?: string
          execution_time?: string | null
          metadata?: Json
        }
      }
      smc_signals: {
        Row: {
          id: string
          user_id: string | null
          symbol: string
          timeframe: string
          signal_type: 'bos' | 'choch' | 'fvg' | 'order_block' | 'liquidity_sweep'
          direction: 'bullish' | 'bearish'
          confidence: number
          price_level: number
          stop_loss: number | null
          take_profit: number | null
          risk_reward_ratio: number | null
          is_processed: boolean
          processed_at: string | null
          expires_at: string | null
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          user_id?: string | null
          symbol: string
          timeframe: string
          signal_type: 'bos' | 'choch' | 'fvg' | 'order_block' | 'liquidity_sweep'
          direction: 'bullish' | 'bearish'
          confidence: number
          price_level: number
          stop_loss?: number | null
          take_profit?: number | null
          risk_reward_ratio?: number | null
          is_processed?: boolean
          processed_at?: string | null
          expires_at?: string | null
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          user_id?: string | null
          symbol?: string
          timeframe?: string
          signal_type?: 'bos' | 'choch' | 'fvg' | 'order_block' | 'liquidity_sweep'
          direction?: 'bullish' | 'bearish'
          confidence?: number
          price_level?: number
          stop_loss?: number | null
          take_profit?: number | null
          risk_reward_ratio?: number | null
          is_processed?: boolean
          processed_at?: string | null
          expires_at?: string | null
          metadata?: Json
          created_at?: string
        }
      }
      market_data_cache: {
        Row: {
          id: string
          symbol: string
          timeframe: string
          data_type: 'kline' | 'ticker' | 'orderbook'
          data: Json
          expires_at: string
          created_at: string
        }
        Insert: {
          id?: string
          symbol: string
          timeframe: string
          data_type: 'kline' | 'ticker' | 'orderbook'
          data: Json
          expires_at: string
          created_at?: string
        }
        Update: {
          id?: string
          symbol?: string
          timeframe?: string
          data_type?: 'kline' | 'ticker' | 'orderbook'
          data?: Json
          expires_at?: string
          created_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

// Helper types
export type User = Database['public']['Tables']['users']['Row'];
export type UserInsert = Database['public']['Tables']['users']['Insert'];
export type UserUpdate = Database['public']['Tables']['users']['Update'];

export type UserApiKey = Database['public']['Tables']['user_api_keys']['Row'];
export type UserApiKeyInsert = Database['public']['Tables']['user_api_keys']['Insert'];
export type UserApiKeyUpdate = Database['public']['Tables']['user_api_keys']['Update'];

export type UserConfiguration = Database['public']['Tables']['user_configurations']['Row'];
export type UserConfigurationInsert = Database['public']['Tables']['user_configurations']['Insert'];
export type UserConfigurationUpdate = Database['public']['Tables']['user_configurations']['Update'];

export type TradingSession = Database['public']['Tables']['trading_sessions']['Row'];
export type TradingSessionInsert = Database['public']['Tables']['trading_sessions']['Insert'];
export type TradingSessionUpdate = Database['public']['Tables']['trading_sessions']['Update'];

export type Trade = Database['public']['Tables']['trades']['Row'];
export type TradeInsert = Database['public']['Tables']['trades']['Insert'];
export type TradeUpdate = Database['public']['Tables']['trades']['Update'];

export type SmcSignal = Database['public']['Tables']['smc_signals']['Row'];
export type SmcSignalInsert = Database['public']['Tables']['smc_signals']['Insert'];
export type SmcSignalUpdate = Database['public']['Tables']['smc_signals']['Update'];

export type MarketDataCache = Database['public']['Tables']['market_data_cache']['Row'];
export type MarketDataCacheInsert = Database['public']['Tables']['market_data_cache']['Insert'];
export type MarketDataCacheUpdate = Database['public']['Tables']['market_data_cache']['Update'];