import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  subscription_tier?: 'free' | 'premium' | 'enterprise';
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  // State
  user: User | null;
  session: Session | null;
  profile: UserProfile | null;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;
  retryCount: number;
  
  // Actions
  setUser: (user: User | null) => void;
  setSession: (session: Session | null) => void;
  setProfile: (profile: UserProfile | null) => void;
  setLoading: (loading: boolean) => void;
  setInitialized: (initialized: boolean) => void;
  setError: (error: string | null) => void;
  incrementRetry: () => void;
  resetRetry: () => void;
  
  // Auth methods
  signIn: (email: string, password: string) => Promise<{ error?: any }>;
  signUp: (email: string, password: string) => Promise<{ error?: any }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error?: any }>;
  
  // Profile methods
  fetchProfile: (userId: string) => Promise<void>;
  updateProfile: (updates: Partial<UserProfile>) => Promise<{ error?: any }>;
  
  // Initialization
  initialize: () => Promise<void>;
}

const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY_BASE = 1000; // 1 second

export const useAuthStore = create<AuthState>()(immer((set, get) => ({
  // Initial state
  user: null,
  session: null,
  profile: null,
  isLoading: true,
  isInitialized: false,
  error: null,
  retryCount: 0,

  // State setters
  setUser: (user) => set((state) => {
    state.user = user;
  }),
  
  setSession: (session) => set((state) => {
    state.session = session;
  }),
  
  setProfile: (profile) => set((state) => {
    state.profile = profile;
  }),
  
  setLoading: (loading) => set((state) => {
    state.isLoading = loading;
  }),
  
  setInitialized: (initialized) => set((state) => {
    state.isInitialized = initialized;
  }),
  
  setError: (error) => set((state) => {
    state.error = error;
  }),
  
  incrementRetry: () => set((state) => {
    state.retryCount += 1;
  }),
  
  resetRetry: () => set((state) => {
    state.retryCount = 0;
  }),

  // Auth methods
  signIn: async (email, password) => {
    set((state) => {
      state.isLoading = true;
      state.error = null;
    });
    
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      
      if (error) throw error;
      
      // Auth state will be updated via the auth listener
      return { error: null };
    } catch (error: any) {
      set((state) => {
        state.error = error.message;
        state.isLoading = false;
      });
      return { error };
    }
  },

  signUp: async (email, password) => {
    set((state) => {
      state.isLoading = true;
      state.error = null;
    });
    
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      });
      
      if (error) throw error;
      
      return { error: null };
    } catch (error: any) {
      set((state) => {
        state.error = error.message;
        state.isLoading = false;
      });
      return { error };
    }
  },

  signOut: async () => {
    set((state) => {
      state.isLoading = true;
      state.error = null;
    });
    
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      
      // Clear all state
      set((state) => {
        state.user = null;
        state.session = null;
        state.profile = null;
        state.isLoading = false;
        state.error = null;
      });
    } catch (error: any) {
      set((state) => {
        state.error = error.message;
        state.isLoading = false;
      });
    }
  },

  resetPassword: async (email) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email);
      return { error };
    } catch (error: any) {
      return { error };
    }
  },

  // Profile methods
  fetchProfile: async (userId) => {
    try {
      const { data, error } = await supabase
        .from('users')
        .select('*')
        .eq('id', userId)
        .single();
      
      if (error && error.code !== 'PGRST116') {
        throw error;
      }
      
      set((state) => {
        state.profile = data;
      });
    } catch (error: any) {
      console.error('Error fetching profile:', error);
      set((state) => {
        state.error = error.message;
      });
    }
  },

  updateProfile: async (updates) => {
    const { user } = get();
    if (!user) return { error: new Error('No user logged in') };
    
    try {
      const { data, error } = await supabase
        .from('users')
        .upsert({
          id: user.id,
          email: user.email, // Required field in users table
          ...updates,
          updated_at: new Date().toISOString(),
        })
        .select()
        .single();
      
      if (error) throw error;
      
      set((state) => {
        state.profile = data;
      });
      
      return { error: null };
    } catch (error: any) {
      set((state) => {
        state.error = error.message;
      });
      return { error };
    }
  },

  // Initialization with retry logic
  initialize: async () => {
    const { retryCount, incrementRetry, resetRetry } = get();
    
    set((state) => {
      state.isLoading = true;
      state.error = null;
    });
    
    try {
      // Get initial session
      const { data: { session }, error } = await supabase.auth.getSession();
      
      if (error) throw error;
      
      if (session) {
        set((state) => {
          state.session = session;
          state.user = session.user;
        });
        
        // Fetch profile
        await get().fetchProfile(session.user.id);
      }
      
      set((state) => {
        state.isLoading = false;
        state.isInitialized = true;
      });
      
      resetRetry();
      
    } catch (error: any) {
      console.error('Auth initialization error:', error);
      
      if (retryCount < MAX_RETRY_ATTEMPTS) {
        incrementRetry();
        
        // Exponential backoff
        const delay = RETRY_DELAY_BASE * Math.pow(2, retryCount);
        
        setTimeout(() => {
          get().initialize();
        }, delay);
      } else {
        set((state) => {
          state.error = `Failed to initialize auth after ${MAX_RETRY_ATTEMPTS} attempts: ${error.message}`;
          state.isLoading = false;
          state.isInitialized = true; // Mark as initialized even on failure
        });
      }
    }
  },
})));

// Set up auth state listener
supabase.auth.onAuthStateChange(async (event, session) => {
  const { setSession, setUser, setLoading, fetchProfile } = useAuthStore.getState();
  
  console.log('Auth state change:', event, session?.user?.email);
  
  setSession(session);
  setUser(session?.user ?? null);
  
  if (session?.user) {
    // Fetch profile when user signs in
    await fetchProfile(session.user.id);
  } else {
    // Clear profile when user signs out
    useAuthStore.setState((state) => ({ ...state, profile: null }));
  }
  
  setLoading(false);
});