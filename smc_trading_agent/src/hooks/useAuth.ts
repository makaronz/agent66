import { useState, useEffect, useCallback } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { auth, db } from '../lib/supabase';
import { User as DatabaseUser } from '../types/database.types';
import toast from 'react-hot-toast';

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
  
  const [state, setState] = useState<AuthState>({
    user: null,
    profile: null,
    session: null,
    loading: true,
    initialized: false,
    connectionError: null,
    isOffline: false
  });
  
  console.log('🔐 useAuth state initialized:', state);

  // Initialize auth state
  useEffect(() => {
    let mounted = true;
    let initializationTimeout: NodeJS.Timeout;

    console.log('🔐 Starting auth initialization...');
    
    // Set initialized to true immediately to prevent infinite loading
    // We'll update the auth state asynchronously
    setState(prev => ({
      ...prev,
      loading: true,
      initialized: true, // Set to true immediately
      connectionError: null,
      isOffline: false
    }));

    // Set a fallback timeout to ensure we never get stuck loading
    initializationTimeout = setTimeout(() => {
      if (mounted) {
        console.warn('🔐 Auth initialization fallback timeout - completing without auth');
        setState(prev => ({
          ...prev,
          user: null,
          profile: null,
          session: null,
          loading: false,
          initialized: true,
          connectionError: null,
          isOffline: true // Assume offline if timeout occurs
        }));
      }
    }, 3000); // 3 second fallback timeout

    const initializeAuth = async () => {
      try {
        console.log('🔐 Getting current session...');
        const { session, error: sessionError } = await auth.getCurrentSession();
        
        if (mounted) {
          clearTimeout(initializationTimeout);
          
          if (sessionError) {
            console.error('🔐 Session error:', sessionError);
            // Don't treat session errors as fatal - just proceed without auth
            const isNetworkError = sessionError.message?.includes('fetch') || sessionError.message?.includes('network');
            setState(prev => ({
              ...prev,
              user: null,
              profile: null,
              session: null,
              loading: false,
              initialized: true,
              connectionError: null,
              isOffline: isNetworkError
            }));
            return;
          }
          
          if (session?.user) {
            console.log('🔐 User session found');
            // Set user immediately, fetch profile in background
            setState(prev => ({
              ...prev,
              user: session.user,
              session,
              loading: false,
              initialized: true,
              connectionError: null,
              isOffline: false
            }));
            
            // Fetch profile in background - don't block UI
            try {
              const { data: profile } = await db.users.get(session.user.id);
              
              if (mounted) {
                if (!profile) {
                  console.log('🔐 Creating new user profile...');
                  const { data: newProfile } = await db.users.upsert({
                    id: session.user.id,
                    email: session.user.email || '',
                    full_name: session.user.user_metadata?.full_name || null,
                    avatar_url: session.user.user_metadata?.avatar_url || null
                  });
                  
                  setState(prev => ({
                    ...prev,
                    profile: newProfile,
                    isOffline: false
                  }));
                } else {
                  console.log('🔐 User profile loaded');
                  setState(prev => ({
                    ...prev,
                    profile,
                    isOffline: false
                  }));
                }
              }
            } catch (profileError) {
              console.error('🔐 Profile handling error:', profileError);
              // Profile errors don't affect authentication - user can still use the app
              const isNetworkError = profileError.message?.includes('fetch') || profileError.message?.includes('network');
              if (mounted && isNetworkError) {
                setState(prev => ({
                  ...prev,
                  isOffline: true
                }));
              }
            }
          } else {
            console.log('🔐 No user session found');
            setState(prev => ({
              ...prev,
              user: null,
              profile: null,
              session: null,
              loading: false,
              initialized: true,
              connectionError: null,
              isOffline: false
            }));
          }
        }
      } catch (error) {
        console.error('🔐 Error initializing auth:', error);
        if (mounted) {
          clearTimeout(initializationTimeout);
          // Don't show connection errors - just proceed without auth
          setState(prev => ({
            ...prev,
            user: null,
            profile: null,
            session: null,
            loading: false,
            initialized: true,
            connectionError: null
          }));
        }
      }
    };

    // Start initialization but don't block UI
    initializeAuth();

    // Listen for auth changes
    const { data: { subscription } } = auth.onAuthStateChange(async (event, session) => {
      if (!mounted) return;

      if (event === 'SIGNED_IN' && session?.user) {
        // Get or create user profile
        const { data: profile } = await db.users.get(session.user.id);
        
        if (!profile) {
          const { data: newProfile } = await db.users.upsert({
            id: session.user.id,
            email: session.user.email || '',
            full_name: session.user.user_metadata?.full_name || null,
            avatar_url: session.user.user_metadata?.avatar_url || null
          });
          
          setState({
          user: session.user,
          profile: null,
          session,
          loading: false,
          initialized: true,
          connectionError: null,
          isOffline: false
        });
        } else {
          setState({
          user: session.user,
          profile: null,
          session,
          loading: false,
          initialized: true,
          connectionError: null,
          isOffline: false
        });
        }
      } else if (event === 'SIGNED_OUT') {
        setState({
        user: null,
        profile: null,
        session: null,
        loading: false,
        initialized: true,
        connectionError: null,
        isOffline: false
      });
      } else if (event === 'TOKEN_REFRESHED' && session) {
        setState(prev => ({
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
  }, []);

  // Sign up
  const signUp = useCallback(async (email: string, password: string, metadata?: any) => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      
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
      setState(prev => ({ ...prev, loading: false }));
    }
  }, []);

  // Sign in
  const signIn = useCallback(async (email: string, password: string) => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      
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
      setState(prev => ({ ...prev, loading: false }));
    }
  }, []);

  // Sign out
  const signOut = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      
      const { error } = await auth.signOut();
      
      if (error) {
        toast.error(error.message);
      } else {
        toast.success('Wylogowano pomyślnie');
      }
    } catch (error: any) {
      toast.error(error.message || 'Błąd podczas wylogowywania');
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, []);

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
      
      setState(prev => ({ ...prev, profile: data }));
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
        setState(prev => ({ ...prev, profile: data }));
      }
    } catch (error) {
      console.error('Error refreshing profile:', error);
    }
  }, []);

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