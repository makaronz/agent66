use metrics::{counter, histogram, gauge, describe_counter, describe_histogram, describe_gauge};
use metrics_exporter_prometheus::{PrometheusBuilder, PrometheusRecorder};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{Duration, Instant};
use tracing::{info, warn, error};
use serde::{Deserialize, Serialize};

/// Detailed latency statistics for monitoring
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LatencyStats {
    pub average_ms: f64,
    pub min_ms: f64,
    pub max_ms: f64,
    pub p50_ms: f64,
    pub p95_ms: f64,
    pub p99_ms: f64,
    pub p999_ms: f64,
    pub jitter_ms: f64,
    pub threshold_exceeded_count: u64,
    pub measurement_count: usize,
}

/// Performance alert types
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AlertType {
    LatencyThresholdExceeded,
    HighJitter,
    HighFailureRate,
    CircuitBreakerOpen,
    ExchangeUnavailable,
}

/// Alert severity levels
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AlertSeverity {
    Info,
    Warning,
    Critical,
}

/// Performance alert information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceAlert {
    pub exchange: String,
    pub alert_type: AlertType,
    pub message: String,
    pub severity: AlertSeverity,
}

/// Overall performance summary
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceSummary {
    pub total_exchanges: usize,
    pub total_orders: u64,
    pub successful_orders: u64,
    pub failed_orders: u64,
    pub average_latency_ms: f64,
    pub alerts: Vec<PerformanceAlert>,
}

/// Performance metrics configuration
#[derive(Debug, Clone)]
pub struct MetricsConfig {
    pub prometheus_port: u16,
    pub latency_threshold_ms: u64,
    pub enable_detailed_metrics: bool,
    pub metrics_retention_duration: Duration,
}

impl Default for MetricsConfig {
    fn default() -> Self {
        Self {
            prometheus_port: 9090,
            latency_threshold_ms: 50,
            enable_detailed_metrics: true,
            metrics_retention_duration: Duration::from_secs(3600), // 1 hour
        }
    }
}

/// High-performance metrics collector for the execution engine
pub struct ExecutionMetrics {
    prometheus_recorder: PrometheusRecorder,
    config: MetricsConfig,
    performance_data: Arc<RwLock<HashMap<String, PerformanceStats>>>,
}

/// Performance statistics for tracking with enhanced latency monitoring
#[derive(Debug, Clone)]
pub struct PerformanceStats {
    pub total_orders: u64,
    pub successful_orders: u64,
    pub failed_orders: u64,
    pub average_latency_ms: f64,
    pub min_latency_ms: f64,
    pub max_latency_ms: f64,
    pub p50_latency_ms: f64,
    pub p95_latency_ms: f64,
    pub p99_latency_ms: f64,
    pub p999_latency_ms: f64,
    pub jitter_ms: f64, // Standard deviation of latency
    pub circuit_breaker_failures: u64,
    pub timeout_errors: u64,
    pub api_errors: u64,
    pub latency_threshold_exceeded: u64,
    pub measurements: Vec<f64>, // Raw latency measurements for percentile calculation
}

impl Default for PerformanceStats {
    fn default() -> Self {
        Self {
            total_orders: 0,
            successful_orders: 0,
            failed_orders: 0,
            average_latency_ms: 0.0,
            min_latency_ms: f64::MAX,
            max_latency_ms: 0.0,
            p50_latency_ms: 0.0,
            p95_latency_ms: 0.0,
            p99_latency_ms: 0.0,
            p999_latency_ms: 0.0,
            jitter_ms: 0.0,
            circuit_breaker_failures: 0,
            timeout_errors: 0,
            api_errors: 0,
            latency_threshold_exceeded: 0,
            measurements: Vec::new(),
        }
    }
}

impl PerformanceStats {
    /// Add a new latency measurement and update statistics
    pub fn add_measurement(&mut self, latency_ms: f64) {
        self.measurements.push(latency_ms);
        
        // Keep only the last 1000 measurements to prevent memory bloat
        if self.measurements.len() > 1000 {
            self.measurements.remove(0);
        }
        
        // Update basic statistics
        self.total_orders += 1;
        self.min_latency_ms = self.min_latency_ms.min(latency_ms);
        self.max_latency_ms = self.max_latency_ms.max(latency_ms);
        
        // Update average
        let total = self.measurements.iter().sum::<f64>();
        self.average_latency_ms = total / self.measurements.len() as f64;
        
        // Calculate percentiles
        self.update_percentiles();
        
        // Calculate jitter (standard deviation)
        self.calculate_jitter();
    }
    
    /// Update percentile calculations
    fn update_percentiles(&mut self) {
        if self.measurements.is_empty() {
            return;
        }
        
        let mut sorted = self.measurements.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        
        let len = sorted.len();
        self.p50_latency_ms = sorted[(len as f64 * 0.5) as usize];
        self.p95_latency_ms = sorted[(len as f64 * 0.95) as usize];
        self.p99_latency_ms = sorted[(len as f64 * 0.99) as usize];
        self.p999_latency_ms = sorted[(len as f64 * 0.999) as usize];
    }
    
    /// Calculate jitter (standard deviation)
    fn calculate_jitter(&mut self) {
        if self.measurements.len() < 2 {
            self.jitter_ms = 0.0;
            return;
        }
        
        let mean = self.average_latency_ms;
        let variance = self.measurements.iter()
            .map(|&x| (x - mean).powi(2))
            .sum::<f64>() / (self.measurements.len() - 1) as f64;
        
        self.jitter_ms = variance.sqrt();
    }
    
    /// Check if latency exceeds threshold
    pub fn check_latency_threshold(&mut self, threshold_ms: f64) -> bool {
        if self.average_latency_ms > threshold_ms {
            self.latency_threshold_exceeded += 1;
            true
        } else {
            false
        }
    }
    
    /// Get current performance summary
    pub fn get_summary(&self) -> String {
        format!(
            "Orders: {}/{}, Latency: avg={:.2}ms, p95={:.2}ms, p99={:.2}ms, jitter={:.2}ms",
            self.successful_orders,
            self.total_orders,
            self.average_latency_ms,
            self.p95_latency_ms,
            self.p99_latency_ms,
            self.jitter_ms
        )
    }
}

impl ExecutionMetrics {
    /// Create a new metrics collector with default configuration
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        Self::with_config(MetricsConfig::default())
    }

    /// Create a new metrics collector with custom configuration
    pub fn with_config(config: MetricsConfig) -> Result<Self, Box<dyn std::error::Error>> {
        info!("Initializing execution metrics with config: {:?}", config);

        // Initialize Prometheus metrics
        let (prometheus_recorder, _) = PrometheusBuilder::new()
            .build()?;

        // Register metric descriptions
        Self::register_metric_descriptions();

        let port = config.prometheus_port;
        
        let metrics = Self {
            prometheus_recorder,
            config,
            performance_data: Arc::new(RwLock::new(HashMap::new())),
        };

        info!("Execution metrics initialized successfully on port {}", port);
        Ok(metrics)
    }

    /// Register metric descriptions for Prometheus
    fn register_metric_descriptions() {
        // Order execution metrics
        describe_counter!("orders_executed_total", "Total number of orders executed");
        describe_counter!("orders_executed_successfully_total", "Total number of successfully executed orders");
        describe_counter!("orders_execution_failed_total", "Total number of failed order executions");
        describe_counter!("orders_execution_retry_success_total", "Total number of successful retries");
        describe_counter!("orders_execution_attempt_failed_total", "Total number of failed execution attempts");

        // Latency metrics
        describe_histogram!("order_execution_duration_ms", "Order execution latency in milliseconds");
        describe_histogram!("order_execution_attempt_duration_ms", "Individual execution attempt latency");
        describe_histogram!("order_execution_failed_attempt_duration_ms", "Failed execution attempt latency");
        describe_histogram!("exchange_initialization_duration_ms", "Exchange initialization latency");
        describe_histogram!("order_cancellation_duration_ms", "Order cancellation latency");
        describe_histogram!("order_status_fetch_duration_ms", "Order status fetch latency");

        // Circuit breaker metrics
        describe_counter!("circuit_breaker_open_total", "Total number of circuit breaker opens");
        describe_counter!("circuit_breaker_failures_total", "Total number of circuit breaker failures");
        describe_counter!("circuit_breaker_successes_total", "Total number of circuit breaker successes");

        // Error metrics
        describe_counter!("exchange_initialization_failures_total", "Total exchange initialization failures");
        describe_counter!("order_execution_latency_threshold_exceeded_total", "Orders exceeding latency threshold");
        describe_counter!("order_cancellations_attempted_total", "Total order cancellation attempts");
        describe_counter!("order_cancellations_successful_total", "Successful order cancellations");
        describe_counter!("order_cancellations_failed_total", "Failed order cancellations");
        describe_counter!("order_cancellations_timeout_total", "Order cancellation timeouts");
        describe_counter!("order_status_fetches_successful_total", "Successful order status fetches");
        describe_counter!("order_status_fetches_failed_total", "Failed order status fetches");
        describe_counter!("order_status_fetches_timeout_total", "Order status fetch timeouts");

        // SMC-specific metrics
        describe_counter!("smc_signals_executed_total", "Total SMC signals executed");
    }

    /// Record order execution start
    pub fn record_order_execution_start(&self, order_id: &str, exchange: &str) -> Instant {
        let start_time = Instant::now();
        
        info!("Starting order execution: {} on exchange: {}", order_id, exchange);
        
        start_time
    }

    /// Record successful order execution
    pub fn record_order_execution_success(&self, start_time: Instant, order_id: &str, exchange: &str) {
        let duration = start_time.elapsed();
        let duration_ms = duration.as_millis() as f64;

        // Record metrics
        counter!("orders_executed_total", 1);
        counter!("orders_executed_successfully_total", 1);
        histogram!("order_execution_duration_ms", duration_ms);

        // Check latency threshold
        if duration_ms > self.config.latency_threshold_ms as f64 {
            warn!("Order execution exceeded latency threshold: {}ms > {}ms for order {}", 
                  duration_ms, self.config.latency_threshold_ms, order_id);
            counter!("order_execution_latency_threshold_exceeded_total", 1);
        }

        // Update performance statistics
        self.update_performance_stats(exchange, duration_ms, true, None);

        info!("Order execution completed successfully: {} in {:?}", order_id, duration);
    }

    /// Record failed order execution
    pub fn record_order_execution_failure(&self, start_time: Instant, order_id: &str, exchange: &str, error_type: &str) {
        let duration = start_time.elapsed();
        let duration_ms = duration.as_millis() as f64;

        // Record metrics
        counter!("orders_executed_total", 1);
        counter!("orders_execution_failed_total", 1);
        histogram!("order_execution_duration_ms", duration_ms);
        histogram!("order_execution_failed_attempt_duration_ms", duration_ms);

        // Record specific error types
        match error_type {
            "circuit_breaker" => counter!("circuit_breaker_failures_total", 1),
            "timeout" => counter!("timeout_errors_total", 1),
            "api_error" => counter!("api_errors_total", 1),
            _ => counter!("unknown_errors_total", 1),
        }

        // Update performance statistics
        self.update_performance_stats(exchange, duration_ms, false, Some(error_type));

        error!("Order execution failed: {} in {:?} - Error: {}", order_id, duration, error_type);
    }

    /// Record retry success
    pub fn record_retry_success(&self, attempt: u32) {
        counter!("orders_execution_retry_success_total", 1);
        info!("Order executed successfully on retry attempt {}", attempt + 1);
    }

    /// Record execution attempt failure
    pub fn record_execution_attempt_failure(&self, attempt: u32, duration: Duration) {
        counter!("orders_execution_attempt_failed_total", 1);
        histogram!("order_execution_failed_attempt_duration_ms", duration.as_millis() as f64);
        warn!("Order execution attempt {} failed in {:?}", attempt + 1, duration);
    }

    /// Record circuit breaker events
    pub fn record_circuit_breaker_event(&self, exchange: &str, event_type: &str) {
        match event_type {
            "open" => {
                counter!("circuit_breaker_open_total", 1);
                error!("Circuit breaker opened for exchange: {}", exchange);
            }
            "failure" => {
                counter!("circuit_breaker_failures_total", 1);
                warn!("Circuit breaker failure recorded for exchange: {}", exchange);
            }
            "success" => {
                counter!("circuit_breaker_successes_total", 1);
                info!("Circuit breaker success recorded for exchange: {}", exchange);
            }
            _ => warn!("Unknown circuit breaker event: {} for exchange: {}", event_type, exchange),
        }
    }

    /// Record exchange initialization
    pub fn record_exchange_initialization(&self, exchange: &str, duration: Duration, success: bool) {
        let duration_ms = duration.as_millis() as f64;
        histogram!("exchange_initialization_duration_ms", duration_ms);

        if success {
            counter!("exchange_initializations_total", 1);
            info!("Exchange {} initialized successfully in {:?}", exchange, duration);
        } else {
            counter!("exchange_initialization_failures_total", 1);
            error!("Exchange {} initialization failed in {:?}", exchange, duration);
        }
    }

    /// Record order cancellation
    pub fn record_order_cancellation(&self, order_id: &str, duration: Duration, success: bool) {
        let duration_ms = duration.as_millis() as f64;
        histogram!("order_cancellation_duration_ms", duration_ms);
        counter!("order_cancellations_attempted_total", 1);

        if success {
            counter!("order_cancellations_successful_total", 1);
            info!("Order {} cancelled successfully in {:?}", order_id, duration);
        } else {
            counter!("order_cancellations_failed_total", 1);
            error!("Order {} cancellation failed in {:?}", order_id, duration);
        }
    }

    /// Record order status fetch
    pub fn record_order_status_fetch(&self, order_id: &str, duration: Duration, success: bool) {
        let duration_ms = duration.as_millis() as f64;
        histogram!("order_status_fetch_duration_ms", duration_ms);

        if success {
            counter!("order_status_fetches_successful_total", 1);
            info!("Order {} status fetched successfully in {:?}", order_id, duration);
        } else {
            counter!("order_status_fetches_failed_total", 1);
            error!("Order {} status fetch failed in {:?}", order_id, duration);
        }
    }

    /// Record SMC signal execution
    pub fn record_smc_signal_execution(&self, signal_id: &str) {
        counter!("smc_signals_executed_total", 1);
        info!("SMC signal executed: {}", signal_id);
    }

    /// Update performance statistics for an exchange with enhanced latency monitoring
    async fn update_performance_stats(&self, exchange: &str, latency_ms: f64, success: bool, error_type: Option<&str>) {
        let mut stats = self.performance_data.write().await;
        let exchange_stats = stats.entry(exchange.to_string()).or_insert_with(PerformanceStats::default);

        // Update basic counters
        if success {
            exchange_stats.successful_orders += 1;
        } else {
            exchange_stats.failed_orders += 1;
        }

        // Add latency measurement with enhanced statistics
        exchange_stats.add_measurement(latency_ms);

        // Check latency threshold
        if exchange_stats.check_latency_threshold(self.config.latency_threshold_ms as f64) {
            warn!("Latency threshold exceeded for exchange {}: {}ms > {}ms", 
                  exchange, exchange_stats.average_latency_ms, self.config.latency_threshold_ms);
        }

        // Update error counters
        if let Some(error_type) = error_type {
            match error_type {
                "circuit_breaker" => exchange_stats.circuit_breaker_failures += 1,
                "timeout" => exchange_stats.timeout_errors += 1,
                "api_error" => exchange_stats.api_errors += 1,
                _ => {}
            }
        }

        // Update comprehensive gauges for real-time monitoring
        gauge!("exchange_total_orders", exchange_stats.total_orders as f64, "exchange" => exchange.to_string());
        gauge!("exchange_successful_orders", exchange_stats.successful_orders as f64, "exchange" => exchange.to_string());
        gauge!("exchange_failed_orders", exchange_stats.failed_orders as f64, "exchange" => exchange.to_string());
        gauge!("exchange_average_latency_ms", exchange_stats.average_latency_ms, "exchange" => exchange.to_string());
        gauge!("exchange_min_latency_ms", exchange_stats.min_latency_ms, "exchange" => exchange.to_string());
        gauge!("exchange_max_latency_ms", exchange_stats.max_latency_ms, "exchange" => exchange.to_string());
        gauge!("exchange_p50_latency_ms", exchange_stats.p50_latency_ms, "exchange" => exchange.to_string());
        gauge!("exchange_p95_latency_ms", exchange_stats.p95_latency_ms, "exchange" => exchange.to_string());
        gauge!("exchange_p99_latency_ms", exchange_stats.p99_latency_ms, "exchange" => exchange.to_string());
        gauge!("exchange_p999_latency_ms", exchange_stats.p999_latency_ms, "exchange" => exchange.to_string());
        gauge!("exchange_jitter_ms", exchange_stats.jitter_ms, "exchange" => exchange.to_string());
        gauge!("exchange_latency_threshold_exceeded", exchange_stats.latency_threshold_exceeded as f64, "exchange" => exchange.to_string());
    }

    /// Get performance statistics for all exchanges
    pub async fn get_performance_stats(&self) -> HashMap<String, PerformanceStats> {
        self.performance_data.read().await.clone()
    }

    /// Get performance statistics for a specific exchange
    pub async fn get_exchange_stats(&self, exchange: &str) -> Option<PerformanceStats> {
        self.performance_data.read().await.get(exchange).cloned()
    }

    /// Get Prometheus metrics endpoint
    pub fn get_prometheus_metrics(&self) -> String {
        self.prometheus_recorder.handle().render()
    }

    /// Get metrics configuration
    pub fn get_config(&self) -> &MetricsConfig {
        &self.config
    }

    /// Check if latency threshold is exceeded
    pub fn is_latency_threshold_exceeded(&self, latency_ms: f64) -> bool {
        latency_ms > self.config.latency_threshold_ms as f64
    }

    /// Get latency threshold
    pub fn get_latency_threshold(&self) -> u64 {
        self.config.latency_threshold_ms
    }

    /// Get detailed latency statistics for an exchange
    pub async fn get_exchange_latency_stats(&self, exchange: &str) -> Option<LatencyStats> {
        let stats = self.performance_data.read().await;
        stats.get(exchange).map(|perf_stats| LatencyStats {
            average_ms: perf_stats.average_latency_ms,
            min_ms: perf_stats.min_latency_ms,
            max_ms: perf_stats.max_latency_ms,
            p50_ms: perf_stats.p50_latency_ms,
            p95_ms: perf_stats.p95_latency_ms,
            p99_ms: perf_stats.p99_latency_ms,
            p999_ms: perf_stats.p999_latency_ms,
            jitter_ms: perf_stats.jitter_ms,
            threshold_exceeded_count: perf_stats.latency_threshold_exceeded,
            measurement_count: perf_stats.measurements.len(),
        })
    }

    /// Get performance alert status for all exchanges
    pub async fn get_performance_alerts(&self) -> Vec<PerformanceAlert> {
        let mut alerts = Vec::new();
        let stats = self.performance_data.read().await;
        
        for (exchange, perf_stats) in stats.iter() {
            // Check latency threshold
            if perf_stats.average_latency_ms > self.config.latency_threshold_ms as f64 {
                alerts.push(PerformanceAlert {
                    exchange: exchange.clone(),
                    alert_type: AlertType::LatencyThresholdExceeded,
                    message: format!("Average latency {}ms exceeds threshold {}ms", 
                                   perf_stats.average_latency_ms, self.config.latency_threshold_ms),
                    severity: AlertSeverity::Warning,
                });
            }
            
            // Check high jitter
            if perf_stats.jitter_ms > 10.0 { // 10ms jitter threshold
                alerts.push(PerformanceAlert {
                    exchange: exchange.clone(),
                    alert_type: AlertType::HighJitter,
                    message: format!("High jitter detected: {}ms", perf_stats.jitter_ms),
                    severity: AlertSeverity::Warning,
                });
            }
            
            // Check failure rate
            let failure_rate = if perf_stats.total_orders > 0 {
                perf_stats.failed_orders as f64 / perf_stats.total_orders as f64
            } else {
                0.0
            };
            
            if failure_rate > 0.1 { // 10% failure rate threshold
                alerts.push(PerformanceAlert {
                    exchange: exchange.clone(),
                    alert_type: AlertType::HighFailureRate,
                    message: format!("High failure rate: {:.2}%", failure_rate * 100.0),
                    severity: AlertSeverity::Critical,
                });
            }
        }
        
        alerts
    }

    /// Get real-time performance summary
    pub async fn get_performance_summary(&self) -> PerformanceSummary {
        let stats = self.performance_data.read().await;
        let mut summary = PerformanceSummary {
            total_exchanges: stats.len(),
            total_orders: 0,
            successful_orders: 0,
            failed_orders: 0,
            average_latency_ms: 0.0,
            alerts: Vec::new(),
        };
        
        for (_, perf_stats) in stats.iter() {
            summary.total_orders += perf_stats.total_orders;
            summary.successful_orders += perf_stats.successful_orders;
            summary.failed_orders += perf_stats.failed_orders;
        }
        
        // Calculate overall average latency
        if summary.total_orders > 0 {
            let total_latency: f64 = stats.values()
                .map(|s| s.average_latency_ms * s.total_orders as f64)
                .sum();
            summary.average_latency_ms = total_latency / summary.total_orders as f64;
        }
        
        // Get alerts
        summary.alerts = self.get_performance_alerts().await;
        
        summary
    }
}

/// Convenience trait for easy metrics integration
pub trait MetricsRecorder {
    fn record_execution_start(&self, order_id: &str, exchange: &str) -> Instant;
    fn record_execution_success(&self, start_time: Instant, order_id: &str, exchange: &str);
    fn record_execution_failure(&self, start_time: Instant, order_id: &str, exchange: &str, error_type: &str);
    fn record_circuit_breaker_event(&self, exchange: &str, event_type: &str);
}

impl MetricsRecorder for ExecutionMetrics {
    fn record_execution_start(&self, order_id: &str, exchange: &str) -> Instant {
        self.record_order_execution_start(order_id, exchange)
    }

    fn record_execution_success(&self, start_time: Instant, order_id: &str, exchange: &str) {
        self.record_order_execution_success(start_time, order_id, exchange);
    }

    fn record_execution_failure(&self, start_time: Instant, order_id: &str, exchange: &str, error_type: &str) {
        self.record_order_execution_failure(start_time, order_id, exchange, error_type);
    }

    fn record_circuit_breaker_event(&self, exchange: &str, event_type: &str) {
        self.record_circuit_breaker_event(exchange, event_type);
    }
}
