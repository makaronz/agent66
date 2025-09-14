import { onCLS, onINP, onFCP, onLCP, onTTFB, Metric } from 'web-vitals';

interface VitalsData {
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  timestamp: number;
  url: string;
  userAgent: string;
}

class WebVitalsTracker {
  private metrics: VitalsData[] = [];
  private endpoint: string;
  private batchSize: number;
  private flushInterval: number;
  private flushTimer: NodeJS.Timeout | null = null;

  constructor(endpoint = '/api/analytics/vitals', batchSize = 10, flushInterval = 30000) {
    this.endpoint = endpoint;
    this.batchSize = batchSize;
    this.flushInterval = flushInterval;
    this.startAutoFlush();
  }

  private getRating(name: string, value: number): 'good' | 'needs-improvement' | 'poor' {
    const thresholds = {
      CLS: { good: 0.1, poor: 0.25 },
      INP: { good: 200, poor: 500 },
      FCP: { good: 1800, poor: 3000 },
      LCP: { good: 2500, poor: 4000 },
      TTFB: { good: 800, poor: 1800 }
    };

    const threshold = thresholds[name as keyof typeof thresholds];
    if (!threshold) return 'good';

    if (value <= threshold.good) return 'good';
    if (value <= threshold.poor) return 'needs-improvement';
    return 'poor';
  }

  private handleMetric = (metric: Metric) => {
    const vitalsData: VitalsData = {
      name: metric.name,
      value: metric.value,
      rating: this.getRating(metric.name, metric.value),
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent
    };

    this.metrics.push(vitalsData);
    
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`Web Vital - ${metric.name}:`, {
        value: metric.value,
        rating: vitalsData.rating,
        url: vitalsData.url
      });
    }

    // Flush if batch size reached
    if (this.metrics.length >= this.batchSize) {
      this.flush();
    }
  };

  private async flush() {
    if (this.metrics.length === 0) return;

    const metricsToSend = [...this.metrics];
    this.metrics = [];

    try {
      await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ metrics: metricsToSend }),
        keepalive: true
      });
    } catch (error) {
      console.error('Failed to send Web Vitals data:', error);
      // Re-add metrics to queue for retry
      this.metrics.unshift(...metricsToSend);
    }
  }

  private startAutoFlush() {
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.flushInterval);
  }

  public init() {
    // Collect Core Web Vitals
    onCLS(this.handleMetric);
    onINP(this.handleMetric);
    onFCP(this.handleMetric);
    onLCP(this.handleMetric);
    onTTFB(this.handleMetric);

    // Flush remaining metrics on page unload
    window.addEventListener('beforeunload', () => {
      this.flush();
    });

    // Flush remaining metrics on visibility change (mobile)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.flush();
      }
    });
  }

  public destroy() {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    this.flush(); // Final flush
  }

  public getMetrics(): VitalsData[] {
    return [...this.metrics];
  }

  public clearMetrics() {
    this.metrics = [];
  }
}

// Singleton instance
let webVitalsTracker: WebVitalsTracker | null = null;

export const initWebVitals = (endpoint?: string, batchSize?: number, flushInterval?: number) => {
  if (typeof window === 'undefined') return; // Skip on server-side
  
  if (!webVitalsTracker) {
    webVitalsTracker = new WebVitalsTracker(endpoint, batchSize, flushInterval);
    webVitalsTracker.init();
  }
  
  return webVitalsTracker;
};

export const getWebVitalsTracker = () => webVitalsTracker;

export const destroyWebVitals = () => {
  if (webVitalsTracker) {
    webVitalsTracker.destroy();
    webVitalsTracker = null;
  }
};

// Export types
export type { VitalsData, Metric };