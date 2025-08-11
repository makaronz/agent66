import { createClient } from '@supabase/supabase-js';
import { Database } from './types/database.types';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://fqhuoszrysapxrvyaqao.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxaHVvc3pyeXNhcHhydnlhcWFvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ4MjMwMTIsImV4cCI6MjA3MDM5OTAxMn0.aaAxrGxtl2Q7j0tRRGY5PBTJaN3mu2zxUOCo-oqIonU';

// Create Supabase client for frontend
export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
});

// Connection health check
export const checkSupabaseConnection = async (): Promise<{ connected: boolean; error?: string }> => {
  try {
    // Simple health check by trying to get the current session
    const { data, error } = await supabase.auth.getSession();
    
    if (error) {
      console.error('Supabase connection error:', error);
      return { connected: false, error: error.message };
    }
    
    return { connected: true };
  } catch (error) {
    console.error('Supabase connection failed:', error);
    return { 
      connected: false, 
      error: error instanceof Error ? error.message : 'Unknown connection error'
    };
  }
};

// Auth helper functions
export const auth = {
  // Sign up new user
  signUp: async (email: string, password: string, metadata?: any) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata
      }
    });
    return { data, error };
  },

  // Sign in user
  signIn: async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });
    return { data, error };
  },

  // Sign out user
  signOut: async () => {
    const { error } = await supabase.auth.signOut();
    return { error };
  },

  // Get current user
  getCurrentUser: async () => {
    const { data: { user }, error } = await supabase.auth.getUser();
    return { user, error };
  },

  // Get current session
  getCurrentSession: async () => {
    const { data: { session }, error } = await supabase.auth.getSession();
    return { session, error };
  },

  // Listen to auth changes
  onAuthStateChange: (callback: (event: string, session: any) => void) => {
    return supabase.auth.onAuthStateChange(callback);
  },

  // Reset password
  resetPassword: async (email: string) => {
    const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`
    });
    return { data, error };
  },

  // Update password
  updatePassword: async (password: string) => {
    const { data, error } = await supabase.auth.updateUser({
      password
    });
    return { data, error };
  }
};

// Database helper functions
export const db = {
  // Users
  users: {
    get: async (userId: string) => {
      const { data, error } = await supabase
        .from('users')
        .select('*')
        .eq('id', userId)
        .single();
      return { data, error };
    },
    
    upsert: async (userData: any) => {
      const { data, error } = await supabase
        .from('users')
        .upsert(userData)
        .select()
        .single();
      return { data, error };
    },
    
    update: async (userId: string, updates: any) => {
      const { data, error } = await supabase
        .from('users')
        .update(updates)
        .eq('id', userId)
        .select()
        .single();
      return { data, error };
    }
  },

  // User configurations
  configurations: {
    list: async (userId: string) => {
      const { data, error } = await supabase
        .from('user_configurations')
        .select('*')
        .eq('user_id', userId)
        .eq('is_active', true)
        .order('updated_at', { ascending: false });
      return { data, error };
    },
    
    get: async (userId: string, configName: string) => {
      const { data, error } = await supabase
        .from('user_configurations')
        .select('*')
        .eq('user_id', userId)
        .eq('config_name', configName)
        .eq('is_active', true)
        .single();
      return { data, error };
    },
    
    upsert: async (userId: string, configName: string, config: any) => {
      const { data, error } = await supabase
        .from('user_configurations')
        .upsert({
          user_id: userId,
          config_name: configName,
          config_json: config,
          is_active: true
        })
        .select()
        .single();
      return { data, error };
    }
  },

  // Trading sessions
  sessions: {
    list: async (userId: string) => {
      const { data, error } = await supabase
        .from('trading_sessions')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });
      return { data, error };
    },
    
    get: async (sessionId: string) => {
      const { data, error } = await supabase
        .from('trading_sessions')
        .select('*')
        .eq('id', sessionId)
        .single();
      return { data, error };
    },
    
    create: async (sessionData: any) => {
      const { data, error } = await supabase
        .from('trading_sessions')
        .insert(sessionData)
        .select()
        .single();
      return { data, error };
    },
    
    update: async (sessionId: string, updates: any) => {
      const { data, error } = await supabase
        .from('trading_sessions')
        .update(updates)
        .eq('id', sessionId)
        .select()
        .single();
      return { data, error };
    }
  },

  // Trades
  trades: {
    list: async (userId: string, sessionId?: string) => {
      let query = supabase
        .from('trades')
        .select('*')
        .eq('user_id', userId)
        .order('timestamp', { ascending: false });
      
      if (sessionId) {
        query = query.eq('session_id', sessionId);
      }
      
      const { data, error } = await query;
      return { data, error };
    },
    
    get: async (tradeId: string) => {
      const { data, error } = await supabase
        .from('trades')
        .select('*')
        .eq('id', tradeId)
        .single();
      return { data, error };
    },
    
    create: async (tradeData: any) => {
      const { data, error } = await supabase
        .from('trades')
        .insert(tradeData)
        .select()
        .single();
      return { data, error };
    },
    
    update: async (tradeId: string, updates: any) => {
      const { data, error } = await supabase
        .from('trades')
        .update(updates)
        .eq('id', tradeId)
        .select()
        .single();
      return { data, error };
    }
  },

  // SMC Signals
  signals: {
    list: async (userId?: string, limit: number = 50) => {
      let query = supabase
        .from('smc_signals')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit);
      
      if (userId) {
        query = query.eq('user_id', userId);
      }
      
      const { data, error } = await query;
      return { data, error };
    },
    
    get: async (signalId: string) => {
      const { data, error } = await supabase
        .from('smc_signals')
        .select('*')
        .eq('id', signalId)
        .single();
      return { data, error };
    },
    
    create: async (signalData: any) => {
      const { data, error } = await supabase
        .from('smc_signals')
        .insert(signalData)
        .select()
        .single();
      return { data, error };
    },
    
    update: async (signalId: string, updates: any) => {
      const { data, error } = await supabase
        .from('smc_signals')
        .update(updates)
        .eq('id', signalId)
        .select()
        .single();
      return { data, error };
    }
  }
};

// Real-time subscriptions
export const realtime = {
  // Subscribe to trades for a user
  subscribeTrades: (userId: string, callback: (payload: any) => void) => {
    return supabase
      .channel('trades')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'trades',
          filter: `user_id=eq.${userId}`
        },
        callback
      )
      .subscribe();
  },

  // Subscribe to SMC signals
  subscribeSignals: (callback: (payload: any) => void, userId?: string) => {
    const channel = supabase.channel('smc_signals');
    
    if (userId) {
      return channel
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'smc_signals',
            filter: `user_id=eq.${userId}`
          },
          callback
        )
        .subscribe();
    } else {
      return channel
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'smc_signals'
          },
          callback
        )
        .subscribe();
    }
  },

  // Subscribe to trading sessions
  subscribeSessions: (userId: string, callback: (payload: any) => void) => {
    return supabase
      .channel('trading_sessions')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'trading_sessions',
          filter: `user_id=eq.${userId}`
        },
        callback
      )
      .subscribe();
  },

  // Unsubscribe from channel
  unsubscribe: (channel: any) => {
    return supabase.removeChannel(channel);
  }
};

export default supabase;