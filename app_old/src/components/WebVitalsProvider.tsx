import React, { useEffect, createContext, useContext, ReactNode } from 'react';
import { initWebVitals, destroyWebVitals, getWebVitalsTracker, VitalsData } from '../utils/webVitals';

interface WebVitalsContextType {
  getMetrics: () => VitalsData[];
  clearMetrics: () => void;
}

const WebVitalsContext = createContext<WebVitalsContextType | null>(null);

interface WebVitalsProviderProps {
  children: ReactNode;
  endpoint?: string;
  batchSize?: number;
  flushInterval?: number;
  enabled?: boolean;
}

export const WebVitalsProvider: React.FC<WebVitalsProviderProps> = ({
  children,
  endpoint,
  batchSize,
  flushInterval,
  enabled = true
}) => {
  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;

    // Initialize Web Vitals tracking
    const tracker = initWebVitals(endpoint, batchSize, flushInterval);

    // Cleanup on unmount
    return () => {
      destroyWebVitals();
    };
  }, [endpoint, batchSize, flushInterval, enabled]);

  const contextValue: WebVitalsContextType = {
    getMetrics: () => {
      const tracker = getWebVitalsTracker();
      return tracker ? tracker.getMetrics() : [];
    },
    clearMetrics: () => {
      const tracker = getWebVitalsTracker();
      if (tracker) {
        tracker.clearMetrics();
      }
    }
  };

  return (
    <WebVitalsContext.Provider value={contextValue}>
      {children}
    </WebVitalsContext.Provider>
  );
};

export const useWebVitals = (): WebVitalsContextType => {
  const context = useContext(WebVitalsContext);
  if (!context) {
    throw new Error('useWebVitals must be used within a WebVitalsProvider');
  }
  return context;
};

// Hook for development debugging
export const useWebVitalsDebug = () => {
  const { getMetrics } = useWebVitals();
  
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const logMetrics = () => {
        const metrics = getMetrics();
        if (metrics.length > 0) {
          console.group('📊 Web Vitals Metrics');
          metrics.forEach(metric => {
            const emoji = metric.rating === 'good' ? '✅' : metric.rating === 'needs-improvement' ? '⚠️' : '❌';
            console.log(`${emoji} ${metric.name}: ${metric.value.toFixed(2)}ms (${metric.rating})`);
          });
          console.groupEnd();
        }
      };

      const interval = setInterval(logMetrics, 10000); // Log every 10 seconds
      return () => clearInterval(interval);
    }
  }, [getMetrics]);
};

export default WebVitalsProvider;