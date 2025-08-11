import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { auth, db } from '../supabase';
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

type AuthContextType = AuthState & AuthActions;

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  console.log('🔐 AuthProvider initializing...');
  
  const [state, setState] = useState<AuthState>({
    user: null,
    profile: null,
    session: null,
    loading: true,
    initialized: false,
    connectionError: null,
    isOffline: false
  });

  // Initialize auth state on mount
  useEffect(() => {
    let mounted = true;
    let initializationTimeout: NodeJS.Timeout;

    console.log('🔐 AuthProvider starting initialization...');
    
    // Set fallback timeout
    initializationTimeout = setTimeout(() => {
      if (mounted) {
        console.warn('🔐 AuthProvider initialization timeout - completing without auth');
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
    }, 2000); // 2 second timeout for provider

    const initializeAuth = async () => {
      try {
        console.log('🔐 AuthProvider getting current session...');
        const { session, error: sessionError } = await auth.getCurrentSession();
        
        if (!mounted) return;
        
        clearTimeout(initializationTimeout);
        
        if (sessionError) {
          console.error('🔐 AuthProvider session error:', sessionError);
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
          return;
        }
        
        if (session?.user) {
          console.log('🔐 AuthProvider user session found:', session.user.email);
          setState(prev => ({
            ...prev,
            user: session.user,
            session,
            loading: false,
            initialized: true,
            connectionError: null,
            isOffline: false
          }));
          
          // Fetch profile in background
          try {
            const { data: profile } = await db.users.get(session.user.id);
            
            if (!mounted) return;
            
            if (!profile) {
              console.log('🔐 AuthProvider creating new user profile...');
              const { data: newProfile } = await db.users.upsert({
                id: session.user.id,
                email: session.user.email || '',
                full_name: session.user.user_metadata?.full_name || null,
                avatar_url: session.user.user_metadata?.avatar_url || null
              });
              
              setState(prev => ({
                ...prev,
                profile: newProfile
              }));
            } else {
              console.log('🔐 AuthProvider user profile loaded');
              setState(prev => ({
                ...prev,
                profile
              }));
            }
          } catch (profileError) {
            console.error('🔐 AuthProvider profile handling error:', profileError);
          }
        } else {
          console.log('🔐 AuthProvider no user session found');
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
      } catch (error) {
        console.error('🔐 AuthProvider error initializing auth:', error);
        if (mounted) {
          clearTimeout(initializationTimeout);
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
    };

    // Start initialization
    initializeAuth();

    // Listen for auth changes
    const { data: { subscription } } = auth.onAuthStateChange(async (event, session) => {
      if (!mounted) return;

      console.log('🔐 AuthProvider auth state change:', event, session?.user?.email);

      if (event === 'SIGNED_IN' && session?.user) {
        setState(prev => ({
          ...prev,
          user: session.user,
          session,
          loading: false,
          initialized: true,
          connectionError: null,
          isOffline: false
        }));
        
        // Get or create user profile
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
            
            setState(prev => ({
              ...prev,
              profile: newProfile
            }));
          } else {
            setState(prev => ({
              ...prev,
              profile
            }));
          }
        } catch (error) {
          console.error('🔐 AuthProvider profile error on sign in:', error);
        }
      } else if (event === 'SIGNED_OUT') {
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

  // Auth actions
  const signUp = async (email: string, password: string, metadata?: any) => {
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
  };

  const signIn = async (email: string, password: string) => {
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
  };

  const signOut = async () => {
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
  };

  const resetPassword = async (email: string) => {
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
  };

  const updatePassword = async (password: string) => {
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
  };

  const updateProfile = async (updates: Partial<DatabaseUser>) => {
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
  };

  const refreshProfile = async () => {
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
  };

  const contextValue: AuthContextType = {
    ...state,
    signUp,
    signIn,
    signOut,
    resetPassword,
    updatePassword,
    updateProfile,
    refreshProfile
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;