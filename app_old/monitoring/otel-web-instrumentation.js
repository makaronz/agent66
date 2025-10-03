// OpenTelemetry Web Instrumentation for SMC Trading Agent Frontend
// Konfiguracja instrumentacji dla aplikacji React

import { WebSDK } from '@opentelemetry/sdk-web';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-otlp-http';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { UserInteractionInstrumentation } from '@opentelemetry/instrumentation-user-interaction';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';

// Service configuration
const serviceName = 'smc-trading-agent-web';
const serviceVersion = process.env.REACT_APP_VERSION || '1.0.0';
const environment = process.env.NODE_ENV || 'development';

// OTLP Collector endpoint for web
const otlpEndpoint = process.env.REACT_APP_OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318';

// Create resource with service information
const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: serviceName,
  [SemanticResourceAttributes.SERVICE_VERSION]: serviceVersion,
  [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: environment,
  [SemanticResourceAttributes.SERVICE_NAMESPACE]: 'smc-trading',
  'browser.name': navigator.userAgent,
  'browser.version': navigator.appVersion,
  'browser.language': navigator.language,
  'screen.resolution': `${screen.width}x${screen.height}`,
});

// Configure trace exporter
const traceExporter = new OTLPTraceExporter({
  url: `${otlpEndpoint}/v1/traces`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Configure span processor
const spanProcessor = new BatchSpanProcessor(traceExporter, {
  maxQueueSize: 100,
  scheduledDelayMillis: 500,
  exportTimeoutMillis: 30000,
  maxExportBatchSize: 10,
});

// Configure context manager
const contextManager = new ZoneContextManager();

// Configure instrumentations
const instrumentations = [
  // Auto instrumentations
  ...getWebAutoInstrumentations({
    '@opentelemetry/instrumentation-document-load': {
      enabled: true,
    },
    '@opentelemetry/instrumentation-user-interaction': {
      enabled: true,
      eventNames: ['click', 'submit', 'keydown'],
    },
    '@opentelemetry/instrumentation-xml-http-request': {
      enabled: true,
      propagateTraceHeaderCorsUrls: [
        /^https?:\/\/localhost.*/,
        /^https?:\/\/.*\.smc-trading\.com.*/,
      ],
    },
    '@opentelemetry/instrumentation-fetch': {
      enabled: true,
      propagateTraceHeaderCorsUrls: [
        /^https?:\/\/localhost.*/,
        /^https?:\/\/.*\.smc-trading\.com.*/,
      ],
      clearTimingResources: true,
    },
  }),
  
  // Custom user interaction instrumentation
  new UserInteractionInstrumentation({
    eventNames: ['click', 'submit', 'keydown', 'change'],
    shouldPreventSpanCreation: (eventType, element, span) => {
      // Don't create spans for certain elements
      if (element.tagName === 'INPUT' && element.type === 'password') {
        return true;
      }
      return false;
    },
  }),
  
  // Document load instrumentation
  new DocumentLoadInstrumentation(),
  
  // Fetch instrumentation with custom configuration
  new FetchInstrumentation({
    propagateTraceHeaderCorsUrls: [
      /^https?:\/\/localhost.*/,
      /^https?:\/\/.*\.smc-trading\.com.*/,
    ],
    clearTimingResources: true,
    requestHook: (span, request) => {
      span.setAttributes({
        'http.request.method': request.method || 'GET',
        'smc.component': 'web-client',
      });
    },
    responseHook: (span, response) => {
      span.setAttributes({
        'http.response.status_code': response.status,
        'http.response.status_text': response.statusText,
      });
    },
  }),
];

// Initialize the Web SDK
const sdk = new WebSDK({
  resource,
  spanProcessor,
  contextManager,
  instrumentations,
});

// Custom metrics for web application
class SMCWebMetrics {
  constructor() {
    this.pageViews = 0;
    this.userInteractions = 0;
    this.apiCalls = 0;
    this.errors = 0;
  }
  
  // Track page views
  trackPageView(pageName) {
    this.pageViews++;
    console.log(`Page view: ${pageName} (Total: ${this.pageViews})`);
    
    // Send custom event
    if (window.gtag) {
      window.gtag('event', 'page_view', {
        page_title: pageName,
        page_location: window.location.href,
      });
    }
  }
  
  // Track user interactions
  trackUserInteraction(action, element) {
    this.userInteractions++;
    console.log(`User interaction: ${action} on ${element} (Total: ${this.userInteractions})`);
  }
  
  // Track API calls
  trackApiCall(endpoint, method, duration) {
    this.apiCalls++;
    console.log(`API call: ${method} ${endpoint} (${duration}ms) (Total: ${this.apiCalls})`);
  }
  
  // Track errors
  trackError(error, context) {
    this.errors++;
    console.error(`Error tracked: ${error.message} in ${context} (Total: ${this.errors})`);
  }
  
  // Get metrics summary
  getMetrics() {
    return {
      pageViews: this.pageViews,
      userInteractions: this.userInteractions,
      apiCalls: this.apiCalls,
      errors: this.errors,
    };
  }
}

// Create global metrics instance
const webMetrics = new SMCWebMetrics();

// Error tracking
window.addEventListener('error', (event) => {
  webMetrics.trackError(event.error, 'global');
});

window.addEventListener('unhandledrejection', (event) => {
  webMetrics.trackError(new Error(event.reason), 'promise');
});

// Performance monitoring
const performanceObserver = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.entryType === 'navigation') {
      console.log(`Page load time: ${entry.loadEventEnd - entry.loadEventStart}ms`);
    } else if (entry.entryType === 'measure') {
      console.log(`Custom measure: ${entry.name} - ${entry.duration}ms`);
    }
  }
});

// Observe performance entries
if ('PerformanceObserver' in window) {
  performanceObserver.observe({ entryTypes: ['navigation', 'measure'] });
}

// Custom performance markers
const markPerformance = {
  start: (name) => {
    if ('performance' in window && 'mark' in performance) {
      performance.mark(`${name}-start`);
    }
  },
  
  end: (name) => {
    if ('performance' in window && 'mark' in performance && 'measure' in performance) {
      performance.mark(`${name}-end`);
      performance.measure(name, `${name}-start`, `${name}-end`);
    }
  },
};

// Initialize OpenTelemetry Web SDK
const initializeWebTelemetry = () => {
  try {
    sdk.start();
    console.log('OpenTelemetry Web SDK initialized successfully');
    
    // Track initial page load
    webMetrics.trackPageView(document.title);
    
    return true;
  } catch (error) {
    console.error('Error initializing OpenTelemetry Web SDK:', error);
    return false;
  }
};

// Shutdown function
const shutdownWebTelemetry = async () => {
  try {
    await sdk.shutdown();
    console.log('OpenTelemetry Web SDK shutdown completed');
  } catch (error) {
    console.error('Error shutting down OpenTelemetry Web SDK:', error);
  }
};

// Export for use in React application
export {
  sdk,
  webMetrics,
  markPerformance,
  initializeWebTelemetry,
  shutdownWebTelemetry,
};

// Auto-initialize if not in test environment
if (process.env.NODE_ENV !== 'test') {
  initializeWebTelemetry();
}

// React integration helpers
export const withTelemetry = (WrappedComponent) => {
  return function TelemetryWrapper(props) {
    React.useEffect(() => {
      markPerformance.start('component-render');
      return () => {
        markPerformance.end('component-render');
      };
    }, []);
    
    return React.createElement(WrappedComponent, props);
  };
};

// Custom hook for tracking user interactions
export const useTelemetry = () => {
  const trackEvent = React.useCallback((action, element) => {
    webMetrics.trackUserInteraction(action, element);
  }, []);
  
  const trackPageView = React.useCallback((pageName) => {
    webMetrics.trackPageView(pageName);
  }, []);
  
  const trackApiCall = React.useCallback((endpoint, method, duration) => {
    webMetrics.trackApiCall(endpoint, method, duration);
  }, []);
  
  const trackError = React.useCallback((error, context) => {
    webMetrics.trackError(error, context);
  }, []);
  
  return {
    trackEvent,
    trackPageView,
    trackApiCall,
    trackError,
    metrics: webMetrics.getMetrics(),
  };
};