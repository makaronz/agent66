import React, { useState } from 'react';
import { useAuthContext } from '../../contexts/AuthContext';
import AuthModal from './AuthModal';
import LoadingSpinner from '../ui/LoadingSpinner';

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  requireAuth?: boolean;
}

const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  fallback,
  requireAuth = true
}) => {
  console.log('🛡️ AuthGuard rendering...');
  
  const { user, loading, initialized, connectionError, isOffline } = useAuthContext();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authTimeout, setAuthTimeout] = useState(false);

  console.log('🛡️ AuthGuard state:', {
    user: !!user,
    loading,
    initialized,
    requireAuth,
    showAuthModal,
    connectionError
  });

  // Set timeout for auth initialization - reduced timeout since auth is now faster
  React.useEffect(() => {
    if (loading && initialized) {
      const timeoutId = setTimeout(() => {
        console.warn('🛡️ AuthGuard: Authentication loading timeout reached');
        setAuthTimeout(true);
      }, 8000); // 8 second timeout for loading state
      
      return () => clearTimeout(timeoutId);
    }
  }, [loading, initialized]);

  // Show loading spinner while auth is loading (with timeout, but not if offline)
  if (loading && !authTimeout && !isOffline) {
    console.log('🛡️ AuthGuard: Showing loading spinner', { initialized, loading });
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-600">Loading authentication...</p>
          <div className="mt-2 text-sm text-gray-500">
            <p>Initialized: {initialized ? 'Yes' : 'No'}</p>
            <p>Loading: {loading ? 'Yes' : 'No'}</p>
            <p>Offline: {isOffline ? 'Yes' : 'No'}</p>
          </div>
          <div className="mt-4">
            <button
              onClick={() => {
                setAuthTimeout(false);
                window.location.reload();
              }}
              className="text-blue-600 hover:text-blue-500 text-sm underline"
            >
              Refresh if stuck
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show offline mode indicator
  if (isOffline) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-yellow-100 border-b border-yellow-200 px-4 py-3">
          <div className="flex items-center justify-center">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-yellow-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span className="text-yellow-800 font-medium">Offline Mode</span>
              <span className="text-yellow-700 ml-2">Some features may be limited</span>
            </div>
          </div>
        </div>
        <div className="p-4">
          {children}
        </div>
      </div>
    );
  }

  // If connection error or auth timeout occurred, show error state
  if (connectionError || authTimeout) {
    const errorTitle = connectionError ? 'Connection Error' : 'Authentication Timeout';
    const errorMessage = connectionError || 'Authentication is taking longer than expected. This might be due to network issues or server problems.';
    
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">{errorTitle}</h2>
          <p className="text-gray-600 mb-2">{errorMessage}</p>
          {connectionError && (
            <p className="text-sm text-gray-500 mb-4">
              Please check your internet connection and try again.
            </p>
          )}
          <div className="space-y-2">
            <button
              onClick={() => {
                setAuthTimeout(false);
                window.location.reload();
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Retry
            </button>
            <button
              onClick={() => {
                setAuthTimeout(false);
                setShowAuthModal(true);
              }}
              className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Continue without authentication
            </button>
          </div>
        </div>
      </div>
    );
  }

  // If auth is not required, always show children
  if (!requireAuth) {
    console.log('🛡️ AuthGuard: Auth not required, showing children');
    return <>{children}</>;
  }

  // If user is authenticated, show children
  if (user) {
    console.log('🛡️ AuthGuard: User authenticated, showing children');
    return <>{children}</>;
  }
  
  console.log('🛡️ AuthGuard: User not authenticated, showing fallback');

  // If custom fallback is provided, show it
  if (fallback) {
    return <>{fallback}</>;
  }

  // Default fallback - show auth modal
  return (
    <>
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="mb-6">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Wymagane logowanie
              </h2>
              <p className="text-gray-600 mb-6">
                Aby uzyskać dostęp do tej funkcji, musisz się zalogować lub utworzyć nowe konto.
              </p>
            </div>
            
            <div className="space-y-3">
              <button
                onClick={() => setShowAuthModal(true)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                Zaloguj się
              </button>
              
              <p className="text-sm text-gray-500">
                Nie masz konta?{' '}
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="text-blue-600 hover:text-blue-500 font-medium"
                >
                  Zarejestruj się tutaj
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        initialMode="login"
      />
    </>
  );
};

export default AuthGuard;