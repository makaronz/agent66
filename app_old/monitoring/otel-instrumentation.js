// OpenTelemetry Instrumentation for SMC Trading Agent
// Konfiguracja automatycznej instrumentacji dla Node.js backend

const { NodeSDK } = require('@opentelemetry/sdk-node');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-http');
const { OTLPMetricExporter } = require('@opentelemetry/exporter-otlp-http');
const { BatchSpanProcessor } = require('@opentelemetry/sdk-trace-node');
const { diag, DiagConsoleLogger, DiagLogLevel } = require('@opentelemetry/api');

// Enable OpenTelemetry debug logging (optional)
if (process.env.OTEL_LOG_LEVEL === 'debug') {
  diag.setLogger(new DiagConsoleLogger(), DiagLogLevel.DEBUG);
}

// Service configuration
const serviceName = process.env.OTEL_SERVICE_NAME || 'smc-trading-agent';
const serviceVersion = process.env.OTEL_SERVICE_VERSION || '1.0.0';
const environment = process.env.NODE_ENV || 'development';

// OTLP Collector endpoints
const otlpEndpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318';
const prometheusPort = parseInt(process.env.PROMETHEUS_PORT || '9464');

// Create resource with service information
const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: serviceName,
  [SemanticResourceAttributes.SERVICE_VERSION]: serviceVersion,
  [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: environment,
  [SemanticResourceAttributes.SERVICE_NAMESPACE]: 'smc-trading',
  [SemanticResourceAttributes.SERVICE_INSTANCE_ID]: process.env.HOSTNAME || 'localhost',
});

// Configure trace exporter
const traceExporter = new OTLPTraceExporter({
  url: `${otlpEndpoint}/v1/traces`,
  headers: {},
});

// Configure metric exporters
const prometheusExporter = new PrometheusExporter({
  port: prometheusPort,
  endpoint: '/metrics',
}, () => {
  console.log(`Prometheus metrics available at http://localhost:${prometheusPort}/metrics`);
});

const otlpMetricExporter = new OTLPMetricExporter({
  url: `${otlpEndpoint}/v1/metrics`,
  headers: {},
});

// Configure metric readers
const metricReaders = [
  prometheusExporter,
  new PeriodicExportingMetricReader({
    exporter: otlpMetricExporter,
    exportIntervalMillis: 5000,
  }),
];

// Configure auto-instrumentations
const instrumentations = getNodeAutoInstrumentations({
  // HTTP instrumentation
  '@opentelemetry/instrumentation-http': {
    enabled: true,
    requestHook: (span, request) => {
      span.setAttributes({
        'http.request.header.user-agent': request.headers['user-agent'],
        'smc.component': 'http-server',
      });
    },
  },
  
  // Express instrumentation
  '@opentelemetry/instrumentation-express': {
    enabled: true,
  },
  
  // Database instrumentations
  '@opentelemetry/instrumentation-pg': {
    enabled: true,
    enhancedDatabaseReporting: true,
  },
  
  '@opentelemetry/instrumentation-redis': {
    enabled: true,
    dbStatementSerializer: (cmdName, cmdArgs) => {
      return `${cmdName} ${cmdArgs.join(' ')}`;
    },
  },
  
  // File system instrumentation
  '@opentelemetry/instrumentation-fs': {
    enabled: true,
  },
  
  // DNS instrumentation
  '@opentelemetry/instrumentation-dns': {
    enabled: true,
  },
  
  // Net instrumentation
  '@opentelemetry/instrumentation-net': {
    enabled: true,
  },
  
  // Disable some instrumentations that might be noisy
  '@opentelemetry/instrumentation-fs': {
    enabled: false, // Can be very noisy
  },
});

// Initialize the SDK
const sdk = new NodeSDK({
  resource,
  traceReader: undefined,
  spanProcessor: new BatchSpanProcessor(traceExporter, {
    maxQueueSize: 1000,
    scheduledDelayMillis: 5000,
    exportTimeoutMillis: 30000,
    maxExportBatchSize: 512,
  }),
  metricReader: metricReaders,
  instrumentations,
});

// Custom metrics for SMC Trading Agent
const { metrics } = require('@opentelemetry/api');
const meter = metrics.getMeter('smc-trading-agent', '1.0.0');

// Trading-specific metrics
const tradingMetrics = {
  // Signal detection metrics
  signalsDetected: meter.createCounter('smc_signals_detected_total', {
    description: 'Total number of SMC signals detected',
  }),
  
  signalAccuracy: meter.createHistogram('smc_signal_accuracy', {
    description: 'Accuracy of SMC signal predictions',
    unit: 'percent',
  }),
  
  // Order execution metrics
  ordersExecuted: meter.createCounter('smc_orders_executed_total', {
    description: 'Total number of orders executed',
  }),
  
  orderLatency: meter.createHistogram('smc_order_execution_latency', {
    description: 'Order execution latency',
    unit: 'ms',
  }),
  
  // Market data metrics
  marketDataLatency: meter.createHistogram('smc_market_data_latency', {
    description: 'Market data processing latency',
    unit: 'ms',
  }),
  
  priceUpdates: meter.createCounter('smc_price_updates_total', {
    description: 'Total number of price updates processed',
  }),
  
  // System health metrics
  activeConnections: meter.createUpDownCounter('smc_active_connections', {
    description: 'Number of active exchange connections',
  }),
  
  memoryUsage: meter.createObservableGauge('smc_memory_usage_bytes', {
    description: 'Memory usage in bytes',
  }),
};

// Memory usage callback
meter.addBatchObservableCallback(
  (observableResult) => {
    const memUsage = process.memoryUsage();
    observableResult.observe(tradingMetrics.memoryUsage, memUsage.heapUsed, {
      type: 'heap_used',
    });
    observableResult.observe(tradingMetrics.memoryUsage, memUsage.heapTotal, {
      type: 'heap_total',
    });
    observableResult.observe(tradingMetrics.memoryUsage, memUsage.rss, {
      type: 'rss',
    });
  },
  [tradingMetrics.memoryUsage]
);

// Export metrics for use in application
module.exports = {
  sdk,
  tradingMetrics,
  
  // Initialize OpenTelemetry
  init: () => {
    try {
      sdk.start();
      console.log('OpenTelemetry initialized successfully');
      
      // Graceful shutdown
      process.on('SIGTERM', async () => {
        try {
          await sdk.shutdown();
          console.log('OpenTelemetry terminated');
        } catch (error) {
          console.error('Error terminating OpenTelemetry', error);
        } finally {
          process.exit(0);
        }
      });
      
    } catch (error) {
      console.error('Error initializing OpenTelemetry', error);
    }
  },
  
  // Shutdown OpenTelemetry
  shutdown: async () => {
    try {
      await sdk.shutdown();
      console.log('OpenTelemetry shutdown completed');
    } catch (error) {
      console.error('Error shutting down OpenTelemetry', error);
    }
  },
};

// Auto-initialize if this file is run directly
if (require.main === module) {
  module.exports.init();
}