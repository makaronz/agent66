import { useState, useEffect, useCallback, useRef } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { auth, db } from '../supabase';
import { User as DatabaseUser } from '../types/database.types';
import toast from 'react-hot-toast';

// Global state cache to persist auth state across component re-renders
let globalAuthState: AuthState | null = null;
let globalAuthStateListeners: Set<(state: AuthState) => void> = new Set();

// Helper functions for global state management
const updateGlobalAuthState = (newState: AuthState) => {
  globalAuthState = newState;
  globalAuthStateListeners.forEach(listener => listener(newState));
};

const subscribeToGlobalAuthState = (listener: (state: AuthState) => void) => {
  globalAuthStateListeners.add(listener);
  return () => globalAuthStateListeners.delete(listener);
};

interface AuthState {
  user: User | null;
  profile: DatabaseUser | null;
  session: Session | null;
  loading: boolean;
  initialized: boolean;
  connectionError: string | null;
  isOffline: boolean;
}

interface AuthActions {
  signUp: (email: string, password: string, metadata?: any) => Promise<{ success: boolean; error?: string }>;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ success: boolean; error?: string }>;
  updatePassword: (password: string) => Promise<{ success: boolean; error?: string }>;
  updateProfile: (updates: Partial<DatabaseUser>) => Promise<{ success: boolean; error?: string }>;
  refreshProfile: () => Promise<void>;
}

export const useAuth = (): AuthState & AuthActions => {
  console.log('🔐 useAuth hook initializing...');
  
  // Initialize state from global cache if available, otherwise use default
  const [state, setState] = useState<AuthState>(() => {
    if (globalAuthState) {
      console.log('🔐 Using cached global auth state:', globalAuthState);
      return globalAuthState;
    }
    return {
      user: null,
      profile: null,
      session: null,
      loading: true,
      initialized: false,
      connectionError: null,
      isOffline: false
    };
  });
  
  const isInitializing = useRef(false);
  
  console.log('🔐 useAuth state initialized:', state);
  
  // Enhanced setState that also updates global state
  const setStateAndGlobal = useCallback((updater: AuthState | ((prev: AuthState) => AuthState)) => {
    setState(prev => {
      const newState = typeof updater === 'function' ? updater(prev) : updater;
      updateGlobalAuthState(newState);
      return newState;
    });
  }, []);
  
  // Update local state when global state changes
  useEffect(() => {
    const unsubscribe = subscribeToGlobalAuthState((newState) => {
      console.log('🔐 Global auth state updated, syncing local state:', newState);
      setState(newState);
    });
    
    return () => {
      unsubscribe();
    };
  }, [setStateAndGlobal]);

  // Initialize auth state
  useEffect(() => {
    let mounted = true;
    let initializationTimeout: NodeJS.Timeout;

    // Skip initialization if already initialized or currently initializing
    if (state.initialized || isInitializing.current) {
      console.log('🔐 Auth already initialized or initializing, skipping...');
      return;
    }

    isInitializing.current = true;
    console.log('🔐 Starting auth initialization...');
    
    // Set a shorter fallback timeout to ensure we never get stuck loading
    initializationTimeout = setTimeout(() => {
      if (mounted) {
        console.warn('🔐 Auth initialization fallback timeout - completing without auth');
        setStateAndGlobal(prev => ({
          ...prev,
          user: null,
          profile: null,
          session: null,
          loading: false,
          initialized: true,
          connectionError: null,
          isOffline: false // Don't assume offline, just no session
        }));
        isInitializing.current = false;
      }
    }, 1000); // Reduced to 1 second timeout

    const initializeAuth = async () => {
      try {
        console.log('🔐 Getting current session...');
        const { session, error: sessionError } = await auth.getCurrentSession();
        
        if (!mounted) return;
        
        clearTimeout(initializationTimeout);
        
        if (sessionError) {
          console.error('🔐 Session error:', sessionError);
          // Don't treat session errors as fatal - just proceed without auth
          setStateAndGlobal(prev => ({
            ...prev,
            user: null,
            profile: null,
            session: null,
            loading: false,
            initialized: true,
            connectionError: null,
            isOffline: false
          }));
          isInitializing.current = false;
          return;
        }
        
        if (session?.user) {
          console.log('🔐 User session found:', session.user.email);
          // Set user immediately, fetch profile in background
          setStateAndGlobal(prev => ({
            ...prev,
            user: session.user,
            session,
            loading: false,
            initialized: true,
            connectionError: null,
            isOffline: false
          }));
          isInitializing.current = false;
          
          // Fetch profile in background - don't block UI
          try {
            const { data: profile } = await db.users.get(session.user.id);
            
            if (!mounted) return;
            
            if (!profile) {
              console.log('🔐 Creating new user profile...');
              const { data: newProfile } = await db.users.upsert({
                id: session.user.id,
                email: session.user.email || '',
                full_name: session.user.user_metadata?.full_name || null,
                avatar_url: session.user.user_metadata?.avatar_url || null
              });
              
              setStateAndGlobal(prev => ({
                ...prev,
                profile: newProfile
              }));
            } else {
              console.log('🔐 User profile loaded');
              setStateAndGlobal(prev => ({
                ...prev,
                profile
              }));
            }
          } catch (profileError) {
            console.error('🔐 Profile handling error:', profileError);
            // Profile errors don't affect authentication - user can still use the app
          }
        } else {
          console.log('🔐 No user session found');
          setStateAndGlobal(prev => ({
            ...prev,
            user: null,
            profile: null,
            session: null,
            loading: false,
            initialized: true,
            connectionError: null,
            isOffline: false
          }));
          isInitializing.current = false;
        }
      } catch (error) {
        console.error('🔐 Error initializing auth:', error);
        if (mounted) {
          clearTimeout(initializationTimeout);
          setStateAndGlobal(prev => ({
            ...prev,
            user: null,
            profile: null,
            session: null,
            loading: false,
            initialized: true,
            connectionError: null,
            isOffline: false
          }));
          isInitializing.current = false;
        }
      }
    };

    // Start initialization
    initializeAuth();

    // Listen for auth changes
    const { data: { subscription } } = auth.onAuthStateChange(async (event, session) => {
      if (!mounted) return;

      console.log('🔐 Auth state change:', event, session?.user?.email);

      if (event === 'SIGNED_IN' && session?.user) {
        setStateAndGlobal(prev => ({
          ...prev,
          user: session.user,
          session,
          loading: false,
          initialized: true,
          connectionError: null,
          isOffline: false
        }));
        
        // Get or create user profile in background
        try {
          const { data: profile } = await db.users.get(session.user.id);
          
          if (!mounted) return;
          
          if (!profile) {
            const { data: newProfile } = await db.users.upsert({
              id: session.user.id,
              email: session.user.email || '',
              full_name: session.user.user_metadata?.full_name || null,
              avatar_url: session.user.user_metadata?.avatar_url || null
            });
            
            setStateAndGlobal(prev => ({
              ...prev,
              profile: newProfile
            }));
          } else {
            setStateAndGlobal(prev => ({
              ...prev,
              profile
            }));
          }
        } catch (error) {
          console.error('🔐 Profile error on sign in:', error);
        }
      } else if (event === 'SIGNED_OUT') {
        setStateAndGlobal(prev => ({
          ...prev,
          user: null,
          profile: null,
          session: null,
          loading: false,
          initialized: true,
          connectionError: null,
          isOffline: false
        }));
      } else if (event === 'TOKEN_REFRESHED' && session) {
        setStateAndGlobal(prev => ({
          ...prev,
          session,
          user: session.user
        }));
      }
    });

    return () => {
      mounted = false;
      if (initializationTimeout) {
        clearTimeout(initializationTimeout);
      }
      subscription.unsubscribe();
    };
  }, [state.initialized, setStateAndGlobal]);

  // Sign up
  const signUp = useCallback(async (email: string, password: string, metadata?: any) => {
    try {
      setStateAndGlobal(prev => ({ ...prev, loading: true }));
      
      const { data, error } = await auth.signUp(email, password, metadata);
      
      if (error) {
        toast.error(error.message);
        return { success: false, error: error.message };
      }
      
      if (data.user && !data.session) {
        toast.success('Sprawdź swoją skrzynkę e-mail, aby potwierdzić konto');
      }
      
      return { success: true };
    } catch (error: any) {
      const errorMessage = error.message || 'Błąd podczas rejestracji';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setStateAndGlobal(prev => ({ ...prev, loading: false }));
    }
  }, [setStateAndGlobal]);

  // Sign in
  const signIn = useCallback(async (email: string, password: string) => {
    try {
      setStateAndGlobal(prev => ({ ...prev, loading: true }));
      
      const { data, error } = await auth.signIn(email, password);
      
      if (error) {
        toast.error(error.message);
        return { success: false, error: error.message };
      }
      
      toast.success('Zalogowano pomyślnie!');
      return { success: true };
    } catch (error: any) {
      const errorMessage = error.message || 'Błąd podczas logowania';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setStateAndGlobal(prev => ({ ...prev, loading: false }));
    }
  }, [setStateAndGlobal]);

  // Sign out
  const signOut = useCallback(async () => {
    try {
      setStateAndGlobal(prev => ({ ...prev, loading: true }));
      
      const { error } = await auth.signOut();
      
      if (error) {
        toast.error(error.message);
      } else {
        toast.success('Wylogowano pomyślnie');
      }
    } catch (error: any) {
      toast.error(error.message || 'Błąd podczas wylogowywania');
    } finally {
      setStateAndGlobal(prev => ({ ...prev, loading: false }));
    }
  }, [setStateAndGlobal]);

  // Reset password
  const resetPassword = useCallback(async (email: string) => {
    try {
      const { data, error } = await auth.resetPassword(email);
      
      if (error) {
        toast.error(error.message);
        return { success: false, error: error.message };
      }
      
      toast.success('Link do resetowania hasła został wysłany na Twój e-mail');
      return { success: true };
    } catch (error: any) {
      const errorMessage = error.message || 'Błąd podczas resetowania hasła';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, []);

  // Update password
  const updatePassword = useCallback(async (password: string) => {
    try {
      const { data, error } = await auth.updatePassword(password);
      
      if (error) {
        toast.error(error.message);
        return { success: false, error: error.message };
      }
      
      toast.success('Hasło zostało zaktualizowane');
      return { success: true };
    } catch (error: any) {
      const errorMessage = error.message || 'Błąd podczas aktualizacji hasła';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, []);

  // Update profile
  const updateProfile = useCallback(async (updates: Partial<DatabaseUser>) => {
    try {
      const { user } = await auth.getCurrentUser();
      if (!user) {
        return { success: false, error: 'Użytkownik nie jest zalogowany' };
      }
      
      const { data, error } = await db.users.update(user.id, updates);
      
      if (error) {
        toast.error(error.message);
        return { success: false, error: error.message };
      }
      
      setStateAndGlobal(prev => ({ ...prev, profile: data }));
      toast.success('Profil został zaktualizowany');
      return { success: true };
    } catch (error: any) {
      const errorMessage = error.message || 'Błąd podczas aktualizacji profilu';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, []);

  // Refresh profile
  const refreshProfile = useCallback(async () => {
    try {
      const { user } = await auth.getCurrentUser();
      if (!user) return;
      
      const { data } = await db.users.get(user.id);
      
      if (data) {
        setStateAndGlobal(prev => ({ ...prev, profile: data }));
      }
    } catch (error) {
      console.error('Error refreshing profile:', error);
    }
  }, [setStateAndGlobal]);

  return {
    ...state,
    signUp,
    signIn,
    signOut,
    resetPassword,
    updatePassword,
    updateProfile,
    refreshProfile
  };
};

export default useAuth;