import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { Toaster } from 'react-hot-toast';
import { store } from './store/store';
import PrivateRoute from './components/PrivateRoute';
import Layout from './components/Layout';

// Lazy load components for better performance
const LoginForm = lazy(() => import('./components/LoginForm'));
const RegisterForm = lazy(() => import('./components/RegisterForm'));
const Dashboard = lazy(() => import('./components/Dashboard'));
const TimeClock = lazy(() => import('./components/TimeClock'));
const Projects = lazy(() => import('./components/Projects'));
const Crew = lazy(() => import('./components/Crew'));
const Reports = lazy(() => import('./components/Reports'));

// Loading component for lazy loaded components
const LoadingSpinner = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
    <div className="ml-4 text-lg font-medium text-gray-700">Loading...</div>
  </div>
);

// Optimized React Query client with performance settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false, // Improve performance by disabling unnecessary refetches
      refetchOnReconnect: true,
      networkMode: 'online', // Don't attempt requests when offline
    },
    mutations: {
      retry: 1,
      networkMode: 'online',
    },
  },
  // Enable query deduplication to prevent duplicate requests
  queryCacheObserverOptions: {
    enabled: true,
  },
});

// Performance monitoring component
class PerformanceMonitor {
  static measureComponentLoad(componentName: string) {
    return (WrappedComponent: React.ComponentType<any>) => {
      return (props: any) => {
        React.useEffect(() => {
          const startTime = performance.now();

          return () => {
            const endTime = performance.now();
            console.log(`⚡ ${componentName} component load time: ${(endTime - startTime).toFixed(2)}ms`);
          };
        }, []);

        return <WrappedComponent {...props} />;
      };
    };
  }
}

function App() {
  // Performance monitoring for app load
  React.useEffect(() => {
    const appLoadTime = performance.now();
    console.log(`🚀 App load time: ${appLoadTime.toFixed(2)}ms`);

    // Report Web Vitals
    if (process.env.NODE_ENV === 'production') {
      import('./reportWebVitals').then(({ reportWebVitals }) => {
        reportWebVitals(console.log);
      });
    }
  }, []);

  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <Router>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#4ade80',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
          <div className="App min-h-screen bg-gray-50">
            <Routes>
              {/* Public routes with lazy loading */}
              <Route
                path="/login"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <LoginForm />
                  </Suspense>
                }
              />
              <Route
                path="/register"
                element={
                  <Suspense fallback={<LoadingSpinner />}>
                    <RegisterForm />
                  </Suspense>
                }
              />

              {/* Protected routes with lazy loading */}
              <Route path="/" element={<PrivateRoute />}>
                <Route element={<Layout />}>
                  <Route
                    index
                    element={
                      <Suspense fallback={<LoadingSpinner />}>
                        <Dashboard />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/time-clock"
                    element={
                      <Suspense fallback={<LoadingSpinner />}>
                        <TimeClock />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/projects"
                    element={
                      <Suspense fallback={<LoadingSpinner />}>
                        <Projects />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/projects/:id"
                    element={
                      <Suspense fallback={<LoadingSpinner />}>
                        <Projects />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/crew"
                    element={
                      <Suspense fallback={<LoadingSpinner />}>
                        <Crew />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/crew/:id"
                    element={
                      <Suspense fallback={<LoadingSpinner />}>
                        <Crew />
                      </Suspense>
                    }
                  />
                  <Route
                    path="/reports"
                    element={
                      <Suspense fallback={<LoadingSpinner />}>
                        <Reports />
                      </Suspense>
                    }
                  />
                </Route>
              </Route>

              {/* 404 route */}
              <Route
                path="*"
                element={
                  <div className="flex items-center justify-center min-h-screen">
                    <div className="text-center">
                      <h1 className="text-4xl font-bold text-gray-900 mb-4">404</h1>
                      <p className="text-lg text-gray-600 mb-8">Page not found</p>
                      <a
                        href="/"
                        className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
                      >
                        Go Home
                      </a>
                    </div>
                  </div>
                }
              />
            </Routes>
          </div>
        </Router>
      </QueryClientProvider>
    </Provider>
  );
}

export default App;

// Performance optimization utilities
export const performanceUtils = {
  // Measure component render time
  measureRender: (componentName: string) => {
    const startTime = performance.now();
    return () => {
      const endTime = performance.now();
      console.log(`🎨 ${componentName} render time: ${(endTime - startTime).toFixed(2)}ms`);
    };
  },

  // Debounce function for performance optimization
  debounce: <T extends (...args: any[]) => void>(
    func: T,
    delay: number
  ): ((...args: Parameters<T>) => void) => {
    let timeoutId: NodeJS.Timeout;
    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  },

  // Throttle function for performance optimization
  throttle: <T extends (...args: any[]) => void>(
    func: T,
    delay: number
  ): ((...args: Parameters<T>) => void) => {
    let lastCall = 0;
    return (...args: Parameters<T>) => {
      const now = Date.now();
      if (now - lastCall >= delay) {
        lastCall = now;
        func(...args);
      }
    };
  },

  // Memory usage monitoring
  getMemoryUsage: () => {
    if ('memory' in performance) {
      return {
        used: `${(performance.memory!.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
        total: `${(performance.memory!.totalJSHeapSize / 1024 / 1024).toFixed(2)} MB`,
        limit: `${(performance.memory!.jsHeapSizeLimit / 1024 / 1024).toFixed(2)} MB`,
      };
    }
    return null;
  },

  // Network performance monitoring
  measureNetworkRequest: async (url: string, options?: RequestInit) => {
    const startTime = performance.now();
    try {
      const response = await fetch(url, options);
      const endTime = performance.now();
      const duration = endTime - startTime;

      console.log(`🌐 ${url} - ${duration.toFixed(2)}ms - ${response.status}`);

      return {
        response,
        duration,
        size: response.headers.get('content-length') || 'unknown',
      };
    } catch (error) {
      const endTime = performance.now();
      const duration = endTime - startTime;

      console.error(`❌ ${url} - ${duration.toFixed(2)}ms - Failed`);

      throw error;
    }
  },
};