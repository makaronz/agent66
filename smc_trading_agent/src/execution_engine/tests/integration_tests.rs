use super::*;
use crate::execution_engine::executor::*;
use crate::execution_engine::metrics::*;

#[tokio::test]
async fn test_execution_engine_integration() {
    // Integration test for complete execution engine workflow
    // This would test the full integration between OrderExecutor and ExecutionMetrics
    
    // Create metrics
    let metrics = ExecutionMetrics::new().unwrap();
    
    // Create executor
    let executor = OrderExecutor::new();
    
    // Test signal
    let signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "test_exchange".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };
    
    // This would test the complete integration
    // For now, we just verify the components can be created together
    assert!(executor.metrics_enabled);
    assert_eq!(metrics.get_config().latency_threshold_ms, 50);
}

#[tokio::test]
async fn test_prometheus_integration() {
    // Test Prometheus metrics integration
    let metrics = ExecutionMetrics::new().unwrap();
    
    // Record some test metrics
    let start_time = metrics.record_order_execution_start("test_order", "test_exchange");
    tokio::time::sleep(tokio::time::Duration::from_millis(25)).await;
    metrics.record_execution_success(start_time, "test_order", "test_exchange");
    
    // Get Prometheus metrics
    let prometheus_metrics = metrics.get_prometheus_metrics();
    
    // Verify metrics are present
    assert!(prometheus_metrics.contains("orders_executed_total"));
    assert!(prometheus_metrics.contains("order_execution_duration_ms"));
}

#[tokio::test]
async fn test_error_handling_integration() {
    // Test error handling integration between components
    let metrics = ExecutionMetrics::new().unwrap();
    
    // Test various error scenarios
    let error_scenarios = vec![
        ("timeout", "timeout"),
        ("api_error", "api_error"),
        ("circuit_breaker", "circuit_breaker"),
    ];
    
    for (order_id, error_type) in error_scenarios {
        let start_time = metrics.record_order_execution_start(order_id, "test_exchange");
        tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
        metrics.record_execution_failure(start_time, order_id, "test_exchange", error_type);
    }
    
    // Verify error metrics are recorded
    let stats = metrics.get_exchange_stats("test_exchange").await.unwrap();
    assert_eq!(stats.failed_orders, 3);
    assert_eq!(stats.timeout_errors, 1);
    assert_eq!(stats.api_errors, 1);
    assert_eq!(stats.circuit_breaker_failures, 1);
}
