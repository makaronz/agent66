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

export type Tables<
  PublicTableNameOrOptions extends
    | keyof (Database['public']['Tables'])
    | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof (Database[PublicTableNameOrOptions['schema']]['Tables'])
    : never = never
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? (Database[PublicTableNameOrOptions['schema']]['Tables'] &
      Database[PublicTableNameOrOptions['schema']]['Views'])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : PublicTableNameOrOptions extends keyof (Database['public']['Tables'] &
      Database['public']['Views'])
  ? (Database['public']['Tables'] &
      Database['public']['Views'])[PublicTableNameOrOptions] extends {
      Row: infer R
    }
    ? R
    : never
  : never

export type TablesInsert<
  PublicTableNameOrOptions extends
    | keyof Database['public']['Tables']
    | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicTableNameOrOptions['schema']]['Tables']
    : never = never
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? Database[PublicTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : PublicTableNameOrOptions extends keyof Database['public']['Tables']
  ? Database['public']['Tables'][PublicTableNameOrOptions] extends {
      Insert: infer I
    }
    ? I
    : never
  : never

export type TablesUpdate<
  PublicTableNameOrOptions extends
    | keyof Database['public']['Tables']
    | { schema: keyof Database },
  TableName extends PublicTableNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicTableNameOrOptions['schema']]['Tables']
    : never = never
> = PublicTableNameOrOptions extends { schema: keyof Database }
  ? Database[PublicTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : PublicTableNameOrOptions extends keyof Database['public']['Tables']
  ? Database['public']['Tables'][PublicTableNameOrOptions] extends {
      Update: infer U
    }
    ? U
    : never
  : never

export type Enums<
  PublicEnumNameOrOptions extends
    | keyof Database['public']['Enums']
    | { schema: keyof Database },
  EnumName extends PublicEnumNameOrOptions extends { schema: keyof Database }
    ? keyof Database[PublicEnumNameOrOptions['schema']]['Enums']
    : never = never
> = PublicEnumNameOrOptions extends { schema: keyof Database }
  ? Database[PublicEnumNameOrOptions['schema']]['Enums'][EnumName]
  : PublicEnumNameOrOptions extends keyof Database['public']['Enums']
  ? Database['public']['Enums'][PublicEnumNameOrOptions]
  : never