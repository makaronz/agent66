import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  maxRetries?: number;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  retryCount: number;
  isOnline: boolean;
  lastErrorTime: number;
}

class ErrorBoundary extends Component<Props, State> {
  private retryTimeoutId: NodeJS.Timeout | null = null;
  private onlineHandler: () => void;
  private offlineHandler: () => void;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      retryCount: 0,
      isOnline: navigator.onLine,
      lastErrorTime: 0
    };
    
    console.log('Enhanced ErrorBoundary initialized');
    
    // Network status handlers
    this.onlineHandler = () => {
      this.setState({ isOnline: true });
      // Auto-retry when connection is restored
      if (this.state.hasError && this.canRetry()) {
        this.handleRetry();
      }
    };
    
    this.offlineHandler = () => {
      this.setState({ isOnline: false });
    };
    
    // Add global error handlers
    window.addEventListener('error', this.handleGlobalError);
    window.addEventListener('unhandledrejection', this.handleUnhandledRejection);
    window.addEventListener('online', this.onlineHandler);
    window.addEventListener('offline', this.offlineHandler);
  }

  componentWillUnmount() {
    window.removeEventListener('error', this.handleGlobalError);
    window.removeEventListener('unhandledrejection', this.handleUnhandledRejection);
    window.removeEventListener('online', this.onlineHandler);
    window.removeEventListener('offline', this.offlineHandler);
    
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  private handleGlobalError = (event: ErrorEvent) => {
    console.error('Global error caught:', event.error);
    this.reportError(event.error, {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno
    });
  };

  private handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    console.error('Unhandled promise rejection:', event.reason);
    this.reportError(new Error(event.reason), { type: 'unhandledrejection' });
  };

  private reportError = (error: Error, context?: any) => {
    // Report to monitoring system
    try {
      fetch('/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            message: error.message,
            stack: error.stack,
            name: error.name
          },
          context,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href,
          isOnline: navigator.onLine
        })
      }).catch(err => console.warn('Failed to report error:', err));
    } catch (reportingError) {
      console.warn('Error reporting failed:', reportingError);
    }
  };

  private canRetry = (): boolean => {
    const { maxRetries = 3 } = this.props;
    const timeSinceLastError = Date.now() - this.state.lastErrorTime;
    return this.state.retryCount < maxRetries && timeSinceLastError > 5000; // 5 second cooldown
  };

  private handleRetry = () => {
    if (!this.canRetry()) return;
    
    console.log(`Retrying... (attempt ${this.state.retryCount + 1})`);
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      retryCount: this.state.retryCount + 1
    });
  };

  private scheduleAutoRetry = () => {
    if (!this.canRetry() || !this.state.isOnline) return;
    
    const delay = Math.min(1000 * Math.pow(2, this.state.retryCount), 30000); // Exponential backoff, max 30s
    this.retryTimeoutId = setTimeout(() => {
      this.handleRetry();
    }, delay);
  };

  static getDerivedStateFromError(error: Error): State {
    console.error('ErrorBoundary caught an error:', error);
    return {
      hasError: true,
      error,
      retryCount: 0,
      isOnline: navigator.onLine,
      lastErrorTime: Date.now()
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary details:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
      lastErrorTime: Date.now()
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Report error to monitoring
    this.reportError(error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true
    });

    // Schedule auto-retry for network-related errors
    if (this.isNetworkError(error)) {
      this.scheduleAutoRetry();
    }
  }

  private isNetworkError = (error: Error): boolean => {
    const networkErrorPatterns = [
      /network/i,
      /fetch/i,
      /connection/i,
      /timeout/i,
      /websocket/i
    ];
    return networkErrorPatterns.some(pattern => pattern.test(error.message));
  };

  render() {
    console.log('ErrorBoundary render called, hasError:', this.state.hasError);
    
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { maxRetries = 3 } = this.props;
      const canRetry = this.canRetry();
      const isNetworkError = this.state.error ? this.isNetworkError(this.state.error) : false;

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <div className="max-w-lg w-full bg-white rounded-lg shadow-lg p-6">
            <div className="text-center">
              {/* Connection Status Indicator */}
              <div className="flex justify-center items-center mb-4">
                <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-2 ${
                  this.state.isOnline ? 'bg-red-100' : 'bg-yellow-100'
                }`}>
                  <svg className={`w-8 h-8 ${
                    this.state.isOnline ? 'text-red-600' : 'text-yellow-600'
                  }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    {this.state.isOnline ? (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-12.728 12.728m0-12.728l12.728 12.728" />
                    )}
                  </svg>
                </div>
                <div className={`ml-2 w-3 h-3 rounded-full ${
                  this.state.isOnline ? 'bg-green-500' : 'bg-red-500'
                }`} title={this.state.isOnline ? 'Online' : 'Offline'}></div>
              </div>

              <h2 className="text-xl font-bold text-gray-900 mb-2">
                {isNetworkError ? 'Connection Error' : 'Application Error'}
              </h2>
              
              <p className="text-gray-600 mb-4">
                {isNetworkError 
                  ? 'Unable to connect to trading services. Please check your connection.'
                  : 'Something went wrong. The error has been reported automatically.'}
              </p>

              {/* Retry Information */}
              {this.state.retryCount > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-blue-800">
                    Retry attempt {this.state.retryCount} of {maxRetries}
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="space-y-3 mb-4">
                {canRetry && (
                  <button
                    onClick={this.handleRetry}
                    className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                  >
                    Try Again ({maxRetries - this.state.retryCount} attempts left)
                  </button>
                )}
                
                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Reload Application
                </button>
                
                <button
                  onClick={() => window.location.href = '/'}
                  className="w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Go to Home
                </button>
              </div>

              {/* Error Details */}
              <details className="text-left bg-gray-50 p-4 rounded-lg">
                <summary className="cursor-pointer font-medium text-gray-700 mb-2">
                  Technical Details
                </summary>
                <div className="space-y-2">
                  <div className="text-xs text-gray-600">
                    <strong>Error:</strong> {this.state.error?.name}
                  </div>
                  <div className="text-xs text-gray-600">
                    <strong>Message:</strong> {this.state.error?.message}
                  </div>
                  <div className="text-xs text-gray-600">
                    <strong>Time:</strong> {new Date(this.state.lastErrorTime).toLocaleString()}
                  </div>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-32">
                    {this.state.error?.stack}
                  </pre>
                  {this.state.errorInfo?.componentStack && (
                    <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-32">
                      Component Stack:
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;