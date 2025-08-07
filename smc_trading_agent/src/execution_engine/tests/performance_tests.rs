use super::*;
use crate::execution_engine::executor::*;
use crate::execution_engine::metrics::*;
use criterion::{criterion_group, criterion_main, Criterion};
use tokio::time::{Duration, Instant};

/// Performance benchmark for order execution
pub fn benchmark_order_execution(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    
    c.bench_function("order_execution_latency", |b| {
        b.iter(|| {
            rt.block_on(async {
                let metrics = ExecutionMetrics::new().unwrap();
                let order_id = "benchmark_order";
                let exchange = "benchmark_exchange";
                
                let start_time = metrics.record_order_execution_start(order_id, exchange);
                
                // Simulate minimal processing time
                tokio::time::sleep(Duration::from_micros(100)).await;
                
                metrics.record_execution_success(start_time, order_id, exchange);
            });
        });
    });
}

/// Performance test for latency threshold compliance
#[tokio::test]
async fn test_latency_threshold_compliance() {
    let metrics = ExecutionMetrics::new().unwrap();
    let target_latency_ms = 50;
    
    // Test multiple executions to ensure we stay under threshold
    let num_executions = 100;
    let mut total_latency = 0.0;
    let mut exceeded_threshold = 0;
    
    for i in 0..num_executions {
        let order_id = format!("latency_test_order_{}", i);
        let exchange = "latency_test_exchange";
        
        let start_time = metrics.record_order_execution_start(&order_id, exchange);
        
        // Simulate realistic processing time (should be well under 50ms)
        tokio::time::sleep(Duration::from_millis(5)).await;
        
        metrics.record_execution_success(start_time, &order_id, exchange);
        
        // Get the recorded latency
        let stats = metrics.get_exchange_stats(exchange).await.unwrap();
        let current_latency = stats.average_latency_ms;
        total_latency += current_latency;
        
        if current_latency > target_latency_ms as f64 {
            exceeded_threshold += 1;
        }
    }
    
    let average_latency = total_latency / num_executions as f64;
    
    // Assert that average latency is well under threshold
    assert!(average_latency < target_latency_ms as f64 * 0.8, 
            "Average latency {}ms exceeds 80% of threshold {}ms", 
            average_latency, target_latency_ms);
    
    // Assert that very few executions exceed threshold
    let exceed_rate = exceeded_threshold as f64 / num_executions as f64;
    assert!(exceed_rate < 0.05, 
            "Exceed rate {}% is too high (should be < 5%)", 
            exceed_rate * 100.0);
}

/// Performance test for high-frequency execution
#[tokio::test]
async fn test_high_frequency_execution() {
    let metrics = ExecutionMetrics::new().unwrap();
    let exchange = "hf_exchange";
    
    // Simulate high-frequency trading scenario
    let num_executions = 1000;
    let start_time = Instant::now();
    
    for i in 0..num_executions {
        let order_id = format!("hf_order_{}", i);
        
        let exec_start = metrics.record_order_execution_start(&order_id, exchange);
        
        // Minimal processing time for high-frequency scenario
        tokio::time::sleep(Duration::from_micros(500)).await;
        
        metrics.record_execution_success(exec_start, &order_id, exchange);
    }
    
    let total_time = start_time.elapsed();
    let throughput = num_executions as f64 / total_time.as_secs_f64();
    
    // Assert high throughput (should be > 1000 orders/second)
    assert!(throughput > 1000.0, 
            "Throughput {} orders/sec is too low (should be > 1000)", 
            throughput);
    
    // Get final stats
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    assert_eq!(stats.total_orders, num_executions);
    assert_eq!(stats.successful_orders, num_executions);
    assert!(stats.average_latency_ms < 1.0); // Should be very low for HF scenario
}

/// Performance test for concurrent execution
#[tokio::test]
async fn test_concurrent_execution() {
    let metrics = ExecutionMetrics::new().unwrap();
    let exchange = "concurrent_exchange";
    let num_concurrent = 10;
    let executions_per_task = 100;
    
    let start_time = Instant::now();
    
    // Spawn concurrent tasks
    let handles: Vec<_> = (0..num_concurrent)
        .map(|task_id| {
            let metrics = metrics.clone();
            tokio::spawn(async move {
                for i in 0..executions_per_task {
                    let order_id = format!("concurrent_order_{}_{}", task_id, i);
                    
                    let exec_start = metrics.record_order_execution_start(&order_id, exchange);
                    
                    // Simulate some processing time
                    tokio::time::sleep(Duration::from_millis(2)).await;
                    
                    metrics.record_execution_success(exec_start, &order_id, exchange);
                }
            })
        })
        .collect();
    
    // Wait for all tasks to complete
    for handle in handles {
        handle.await.unwrap();
    }
    
    let total_time = start_time.elapsed();
    let total_executions = num_concurrent * executions_per_task;
    let throughput = total_executions as f64 / total_time.as_secs_f64();
    
    // Assert good concurrent performance
    assert!(throughput > 500.0, 
            "Concurrent throughput {} orders/sec is too low (should be > 500)", 
            throughput);
    
    // Get final stats
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    assert_eq!(stats.total_orders, total_executions);
    assert_eq!(stats.successful_orders, total_executions);
}

/// Performance test for memory usage
#[tokio::test]
async fn test_memory_usage() {
    let metrics = ExecutionMetrics::new().unwrap();
    let exchange = "memory_test_exchange";
    
    // Execute many orders to test memory usage
    let num_executions = 10000;
    
    for i in 0..num_executions {
        let order_id = format!("memory_order_{}", i);
        
        let start_time = metrics.record_order_execution_start(&order_id, exchange);
        
        // Minimal processing
        tokio::time::sleep(Duration::from_micros(100)).await;
        
        metrics.record_execution_success(start_time, &order_id, exchange);
    }
    
    // Get stats to verify memory is being managed properly
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    assert_eq!(stats.total_orders, num_executions);
    
    // The test passes if we can complete 10k executions without memory issues
}

/// Performance test for error handling overhead
#[tokio::test]
async fn test_error_handling_performance() {
    let metrics = ExecutionMetrics::new().unwrap();
    let exchange = "error_perf_exchange";
    
    let num_executions = 1000;
    let start_time = Instant::now();
    
    for i in 0..num_executions {
        let order_id = format!("error_order_{}", i);
        
        let exec_start = metrics.record_order_execution_start(&order_id, exchange);
        
        // Simulate processing time
        tokio::time::sleep(Duration::from_millis(1)).await;
        
        // Alternate between success and failure to test error handling overhead
        if i % 2 == 0 {
            metrics.record_execution_success(exec_start, &order_id, exchange);
        } else {
            metrics.record_execution_failure(exec_start, &order_id, exchange, "api_error");
        }
    }
    
    let total_time = start_time.elapsed();
    let throughput = num_executions as f64 / total_time.as_secs_f64();
    
    // Error handling should not significantly impact performance
    assert!(throughput > 200.0, 
            "Error handling throughput {} orders/sec is too low (should be > 200)", 
            throughput);
    
    // Verify error metrics are recorded correctly
    let stats = metrics.get_exchange_stats(exchange).await.unwrap();
    assert_eq!(stats.total_orders, num_executions);
    assert_eq!(stats.successful_orders, num_executions / 2);
    assert_eq!(stats.failed_orders, num_executions / 2);
    assert_eq!(stats.api_errors, num_executions / 2);
}

// Criterion benchmark configuration
criterion_group!(benches, benchmark_order_execution);
criterion_main!(benches);
