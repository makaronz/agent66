use super::*;
use crate::execution_engine::metrics::*;
use tokio::time::{Duration, Instant};

#[tokio::test]
async fn test_metrics_creation() {
    let metrics = ExecutionMetrics::new();
    assert!(metrics.is_ok());
    
    let metrics = metrics.unwrap();
    assert_eq!(metrics.get_config().prometheus_port, 9090);
    assert_eq!(metrics.get_config().latency_threshold_ms, 50);
}

#[tokio::test]
async fn test_metrics_with_config() {
    let config = MetricsConfig {
        prometheus_port: 9091,
        latency_threshold_ms: 100,
        enable_detailed_metrics: true,
        metrics_retention_duration: Duration::from_secs(7200),
    };

    let metrics = ExecutionMetrics::with_config(config);
    assert!(metrics.is_ok());
    
    let metrics = metrics.unwrap();
    assert_eq!(metrics.get_config().prometheus_port, 9091);
    assert_eq!(metrics.get_config().latency_threshold_ms, 100);
}

#[tokio::test]
async fn test_order_execution_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let order_id = "test_order_123";
    let exchange = "binance";
    
    // Record execution start
    let start_time = metrics.record_order_execution_start(order_id, exchange);
    
    // Simulate some processing time
    tokio::time::sleep(Duration::from_millis(25)).await;
    
    // Record successful execution
    metrics.record_execution_success(start_time, order_id, exchange);
    
    // Get performance stats
    let stats = metrics.get_exchange_stats(exchange).await;
    assert!(stats.is_some());
    
    let stats = stats.unwrap();
    assert_eq!(stats.total_orders, 1);
    assert_eq!(stats.successful_orders, 1);
    assert_eq!(stats.failed_orders, 0);
    assert!(stats.average_latency_ms > 20.0); // Should be around 25ms
}

#[tokio::test]
async fn test_failed_execution_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let order_id = "test_order_456";
    let exchange = "coinbase";
    
    // Record execution start
    let start_time = metrics.record_order_execution_start(order_id, exchange);
    
    // Simulate some processing time
    tokio::time::sleep(Duration::from_millis(15)).await;
    
    // Record failed execution
    metrics.record_execution_failure(start_time, order_id, exchange, "api_error");
    
    // Get performance stats
    let stats = metrics.get_exchange_stats(exchange).await;
    assert!(stats.is_some());
    
    let stats = stats.unwrap();
    assert_eq!(stats.total_orders, 1);
    assert_eq!(stats.successful_orders, 0);
    assert_eq!(stats.failed_orders, 1);
    assert_eq!(stats.api_errors, 1);
    assert!(stats.average_latency_ms > 10.0); // Should be around 15ms
}

#[tokio::test]
async fn test_latency_threshold_monitoring() {
    let config = MetricsConfig {
        latency_threshold_ms: 30,
        ..Default::default()
    };
    
    let metrics = ExecutionMetrics::with_config(config).unwrap();
    
    let order_id = "test_order_789";
    let exchange = "slow_exchange";
    
    // Record execution start
    let start_time = metrics.record_order_execution_start(order_id, exchange);
    
    // Simulate high latency
    tokio::time::sleep(Duration::from_millis(50)).await;
    
    // Record successful execution (but with high latency)
    metrics.record_execution_success(start_time, order_id, exchange);
    
    // Check if latency threshold was exceeded
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    assert!(stats.average_latency_ms > 30.0); // Should exceed threshold
}

#[tokio::test]
async fn test_circuit_breaker_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let exchange = "unreliable_exchange";
    
    // Record circuit breaker events
    metrics.record_circuit_breaker_event(exchange, "failure");
    metrics.record_circuit_breaker_event(exchange, "failure");
    metrics.record_circuit_breaker_event(exchange, "open");
    metrics.record_circuit_breaker_event(exchange, "success");
    
    // Get performance stats
    let stats = metrics.get_exchange_stats(exchange).await;
    assert!(stats.is_some());
    
    let stats = stats.unwrap();
    assert_eq!(stats.circuit_breaker_failures, 0); // Not updated in this test
}

#[tokio::test]
async fn test_exchange_initialization_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let exchange = "new_exchange";
    
    // Record successful initialization
    let start_time = Instant::now();
    tokio::time::sleep(Duration::from_millis(100)).await;
    let duration = start_time.elapsed();
    
    metrics.record_exchange_initialization(exchange, duration, true);
    
    // Record failed initialization
    let start_time = Instant::now();
    tokio::time::sleep(Duration::from_millis(50)).await;
    let duration = start_time.elapsed();
    
    metrics.record_exchange_initialization(exchange, duration, false);
}

#[tokio::test]
async fn test_order_cancellation_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let order_id = "cancel_order_123";
    
    // Record successful cancellation
    let start_time = Instant::now();
    tokio::time::sleep(Duration::from_millis(20)).await;
    let duration = start_time.elapsed();
    
    metrics.record_order_cancellation(order_id, duration, true);
    
    // Record failed cancellation
    let start_time = Instant::now();
    tokio::time::sleep(Duration::from_millis(10)).await;
    let duration = start_time.elapsed();
    
    metrics.record_order_cancellation(order_id, duration, false);
}

#[tokio::test]
async fn test_order_status_fetch_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let order_id = "status_order_123";
    
    // Record successful status fetch
    let start_time = Instant::now();
    tokio::time::sleep(Duration::from_millis(5)).await;
    let duration = start_time.elapsed();
    
    metrics.record_order_status_fetch(order_id, duration, true);
    
    // Record failed status fetch
    let start_time = Instant::now();
    tokio::time::sleep(Duration::from_millis(8)).await;
    let duration = start_time.elapsed();
    
    metrics.record_order_status_fetch(order_id, duration, false);
}

#[tokio::test]
async fn test_smc_signal_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let signal_id = "smc_signal_123";
    
    // Record SMC signal execution
    metrics.record_smc_signal_execution(signal_id);
}

#[tokio::test]
async fn test_retry_metrics() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    // Record retry success
    metrics.record_retry_success(1);
    metrics.record_retry_success(2);
    
    // Record execution attempt failure
    let duration = Duration::from_millis(30);
    metrics.record_execution_attempt_failure(0, duration);
    metrics.record_execution_attempt_failure(1, duration);
}

#[tokio::test]
async fn test_multiple_exchanges_performance() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let exchanges = vec!["binance", "coinbase", "kraken"];
    
    for (i, exchange) in exchanges.iter().enumerate() {
        let order_id = format!("order_{}", i);
        
        // Record execution start
        let start_time = metrics.record_order_execution_start(&order_id, exchange);
        
        // Simulate different latencies for each exchange
        let latency = 10 + (i * 5) as u64;
        tokio::time::sleep(Duration::from_millis(latency)).await;
        
        // Record successful execution
        metrics.record_execution_success(start_time, &order_id, exchange);
    }
    
    // Get all performance stats
    let all_stats = metrics.get_performance_stats().await;
    assert_eq!(all_stats.len(), 3);
    
    // Check each exchange has stats
    for exchange in exchanges {
        assert!(all_stats.contains_key(exchange));
        let stats = &all_stats[exchange];
        assert_eq!(stats.total_orders, 1);
        assert_eq!(stats.successful_orders, 1);
    }
}

#[tokio::test]
async fn test_prometheus_metrics_endpoint() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    // Get Prometheus metrics
    let prometheus_metrics = metrics.get_prometheus_metrics();
    
    // Should contain some basic metrics
    assert!(prometheus_metrics.contains("# HELP"));
    assert!(prometheus_metrics.contains("# TYPE"));
}

#[tokio::test]
async fn test_latency_threshold_checking() {
    let config = MetricsConfig {
        latency_threshold_ms: 25,
        ..Default::default()
    };
    
    let metrics = ExecutionMetrics::with_config(config).unwrap();
    
    // Test below threshold
    assert!(!metrics.is_latency_threshold_exceeded(20.0));
    
    // Test at threshold
    assert!(!metrics.is_latency_threshold_exceeded(25.0));
    
    // Test above threshold
    assert!(metrics.is_latency_threshold_exceeded(30.0));
}

#[tokio::test]
async fn test_performance_stats_accumulation() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let exchange = "test_exchange";
    let order_ids = vec!["order_1", "order_2", "order_3", "order_4", "order_5"];
    
    for (i, order_id) in order_ids.iter().enumerate() {
        let start_time = metrics.record_order_execution_start(order_id, exchange);
        
        // Simulate varying latencies
        let latency = 10 + (i * 2) as u64;
        tokio::time::sleep(Duration::from_millis(latency)).await;
        
        // Alternate between success and failure
        if i % 2 == 0 {
            metrics.record_execution_success(start_time, order_id, exchange);
        } else {
            metrics.record_execution_failure(start_time, order_id, exchange, "api_error");
        }
    }
    
    // Get final stats
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    
    assert_eq!(stats.total_orders, 5);
    assert_eq!(stats.successful_orders, 3); // orders 0, 2, 4
    assert_eq!(stats.failed_orders, 2); // orders 1, 3
    assert_eq!(stats.api_errors, 2);
    
    // Check latency statistics
    assert!(stats.average_latency_ms > 10.0);
    assert!(stats.min_latency_ms >= 10.0);
    assert!(stats.max_latency_ms <= 20.0);
}

#[tokio::test]
async fn test_metrics_recorder_trait() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let order_id = "trait_test_order";
    let exchange = "trait_test_exchange";
    
    // Test trait methods
    let start_time = metrics.record_execution_start(order_id, exchange);
    
    tokio::time::sleep(Duration::from_millis(15)).await;
    
    metrics.record_execution_success(start_time, order_id, exchange);
    metrics.record_circuit_breaker_event(exchange, "success");
    
    // Verify metrics were recorded
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    assert_eq!(stats.total_orders, 1);
    assert_eq!(stats.successful_orders, 1);
}

#[tokio::test]
async fn test_error_type_classification() {
    let metrics = ExecutionMetrics::new().unwrap();
    
    let order_id = "error_test_order";
    let exchange = "error_test_exchange";
    
    let error_types = vec!["circuit_breaker", "timeout", "api_error", "unknown"];
    
    for error_type in error_types {
        let start_time = metrics.record_order_execution_start(order_id, exchange);
        tokio::time::sleep(Duration::from_millis(5)).await;
        metrics.record_execution_failure(start_time, order_id, exchange, error_type);
    }
    
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    assert_eq!(stats.total_orders, 4);
    assert_eq!(stats.failed_orders, 4);
    assert_eq!(stats.circuit_breaker_failures, 1);
    assert_eq!(stats.timeout_errors, 1);
    assert_eq!(stats.api_errors, 1);
}
