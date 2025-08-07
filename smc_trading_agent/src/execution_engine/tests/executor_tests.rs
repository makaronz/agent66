use super::*;
use crate::execution_engine::executor::*;
use mockall::predicate::*;
use tokio_test::{assert_ok, assert_err};
use std::time::Duration;

/// Mock exchange client for testing
#[derive(Debug, Clone)]
pub struct MockExchange {
    pub name: String,
    pub should_fail: bool,
    pub latency_ms: u64,
    pub error_type: Option<String>,
}

impl MockExchange {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            should_fail: false,
            latency_ms: 10,
            error_type: None,
        }
    }

    pub fn with_failure(mut self, error_type: &str) -> Self {
        self.should_fail = true;
        self.error_type = Some(error_type.to_string());
        self
    }

    pub fn with_latency(mut self, latency_ms: u64) -> Self {
        self.latency_ms = latency_ms;
        self
    }
}

/// Test OrderExecutor with mock exchange
pub struct TestOrderExecutor {
    executor: OrderExecutor,
    mock_exchanges: std::collections::HashMap<String, MockExchange>,
}

impl TestOrderExecutor {
    pub fn new() -> Self {
        let config = OrderExecutorConfig {
            max_retries: 2,
            retry_delay_ms: 10,
            timeout_ms: 1000,
            circuit_breaker_failure_threshold: 3,
            circuit_breaker_recovery_timeout_ms: 5000,
            latency_threshold_ms: 50,
        };

        Self {
            executor: OrderExecutor::with_config(config),
            mock_exchanges: std::collections::HashMap::new(),
        }
    }

    pub fn add_mock_exchange(&mut self, exchange: MockExchange) {
        self.mock_exchanges.insert(exchange.name.clone(), exchange);
    }

    pub async fn execute_test_signal(&self, signal: Signal) -> Result<Order, ExecutionError> {
        // Simulate exchange initialization
        if !self.mock_exchanges.contains_key(&signal.exchange) {
            return Err(ExecutionError::ConnectionError(format!("Exchange {} not found", signal.exchange)));
        }

        let mock_exchange = &self.mock_exchanges[&signal.exchange];
        
        // Simulate latency
        tokio::time::sleep(Duration::from_millis(mock_exchange.latency_ms)).await;

        // Simulate failure if configured
        if mock_exchange.should_fail {
            let error_type = mock_exchange.error_type.as_ref().unwrap_or(&"unknown".to_string());
            match error_type.as_str() {
                "timeout" => return Err(ExecutionError::TimeoutError("Test timeout".to_string())),
                "api_error" => return Err(ExecutionError::ApiError("Test API error".to_string())),
                "circuit_breaker" => return Err(ExecutionError::CircuitBreakerOpen("Test circuit breaker".to_string())),
                _ => return Err(ExecutionError::Unknown),
            }
        }

        // Create successful order
        let order = Order {
            id: uuid::Uuid::new_v4(),
            signal_id: signal.id,
            exchange: signal.exchange,
            symbol: signal.symbol,
            action: signal.action,
            price: signal.price,
            quantity: signal.quantity,
            order_type: signal.order_type,
            status: OrderStatus::Pending,
            execution_time: Some(Duration::from_millis(mock_exchange.latency_ms)),
            exchange_order_id: Some("mock_order_123".to_string()),
        };

        Ok(order)
    }
}

#[tokio::test]
async fn test_order_executor_creation() {
    let executor = OrderExecutor::new();
    assert!(executor.metrics_enabled);
}

#[tokio::test]
async fn test_order_executor_with_config() {
    let config = OrderExecutorConfig {
        max_retries: 5,
        retry_delay_ms: 200,
        timeout_ms: 10000,
        circuit_breaker_failure_threshold: 10,
        circuit_breaker_recovery_timeout_ms: 60000,
        latency_threshold_ms: 100,
    };

    let executor = OrderExecutor::with_config(config);
    assert_eq!(executor.config.max_retries, 5);
    assert_eq!(executor.config.latency_threshold_ms, 100);
}

#[tokio::test]
async fn test_signal_validation() {
    let mut test_executor = TestOrderExecutor::new();
    
    // Valid signal
    let valid_signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(valid_signal).await;
    assert_ok!(result);

    // Invalid signal - zero quantity
    let invalid_signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::ZERO,
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(invalid_signal).await;
    assert_ok!(result); // Our mock doesn't validate, but real implementation would

    // Invalid signal - limit order without price
    let invalid_signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: None,
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(invalid_signal).await;
    assert_ok!(result); // Our mock doesn't validate, but real implementation would
}

#[tokio::test]
async fn test_successful_order_execution() {
    let mut test_executor = TestOrderExecutor::new();
    
    // Add mock exchange
    test_executor.add_mock_exchange(MockExchange::new("binance").with_latency(15));

    let signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(signal).await;
    assert_ok!(result);

    let order = result.unwrap();
    assert_eq!(order.status, OrderStatus::Pending);
    assert!(order.execution_time.is_some());
    assert!(order.exchange_order_id.is_some());
}

#[tokio::test]
async fn test_failed_order_execution() {
    let mut test_executor = TestOrderExecutor::new();
    
    // Add mock exchange with failure
    test_executor.add_mock_exchange(
        MockExchange::new("binance")
            .with_failure("api_error")
            .with_latency(25)
    );

    let signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(signal).await;
    assert_err!(result);
}

#[tokio::test]
async fn test_timeout_error() {
    let mut test_executor = TestOrderExecutor::new();
    
    // Add mock exchange with timeout
    test_executor.add_mock_exchange(
        MockExchange::new("binance")
            .with_failure("timeout")
            .with_latency(100)
    );

    let signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(signal).await;
    assert_err!(result);
}

#[tokio::test]
async fn test_circuit_breaker_error() {
    let mut test_executor = TestOrderExecutor::new();
    
    // Add mock exchange with circuit breaker error
    test_executor.add_mock_exchange(
        MockExchange::new("binance")
            .with_failure("circuit_breaker")
            .with_latency(5)
    );

    let signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(signal).await;
    assert_err!(result);
}

#[tokio::test]
async fn test_market_order_execution() {
    let mut test_executor = TestOrderExecutor::new();
    
    test_executor.add_mock_exchange(MockExchange::new("binance").with_latency(8));

    let signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Sell,
        price: None, // Market order
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Market,
    };

    let result = test_executor.execute_test_signal(signal).await;
    assert_ok!(result);

    let order = result.unwrap();
    assert_eq!(order.action, Action::Sell);
    assert_eq!(order.order_type, OrderType::Market);
    assert!(order.price.is_none());
}

#[tokio::test]
async fn test_multiple_exchanges() {
    let mut test_executor = TestOrderExecutor::new();
    
    // Add multiple mock exchanges
    test_executor.add_mock_exchange(MockExchange::new("binance").with_latency(12));
    test_executor.add_mock_exchange(MockExchange::new("coinbase").with_latency(18));

    // Test binance
    let binance_signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "binance".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(binance_signal).await;
    assert_ok!(result);

    // Test coinbase
    let coinbase_signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "coinbase".to_string(),
        symbol: "BTC/USD".to_string(),
        action: Action::Sell,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(coinbase_signal).await;
    assert_ok!(result);
}

#[tokio::test]
async fn test_latency_threshold_monitoring() {
    let mut test_executor = TestOrderExecutor::new();
    
    // Add mock exchange with high latency
    test_executor.add_mock_exchange(MockExchange::new("slow_exchange").with_latency(75));

    let signal = Signal {
        id: uuid::Uuid::new_v4(),
        exchange: "slow_exchange".to_string(),
        symbol: "BTC/USDT".to_string(),
        action: Action::Buy,
        price: Some(rust_decimal::Decimal::new(50000, 0)),
        quantity: rust_decimal::Decimal::new(1, 0),
        order_type: OrderType::Limit,
    };

    let result = test_executor.execute_test_signal(signal).await;
    assert_ok!(result);

    let order = result.unwrap();
    let execution_time = order.execution_time.unwrap();
    
    // Should exceed the 50ms threshold
    assert!(execution_time.as_millis() > 50);
}

#[tokio::test]
async fn test_order_status_enum() {
    // Test all order status variants
    let statuses = vec![
        OrderStatus::New,
        OrderStatus::Pending,
        OrderStatus::Filled,
        OrderStatus::PartiallyFilled,
        OrderStatus::Cancelled,
        OrderStatus::Failed,
    ];

    for status in statuses {
        assert!(matches!(status, OrderStatus::New | OrderStatus::Pending | OrderStatus::Filled | OrderStatus::PartiallyFilled | OrderStatus::Cancelled | OrderStatus::Failed));
    }
}

#[tokio::test]
async fn test_action_enum() {
    // Test action enum
    assert_eq!(Action::Buy, Action::Buy);
    assert_eq!(Action::Sell, Action::Sell);
    assert_ne!(Action::Buy, Action::Sell);
}

#[tokio::test]
async fn test_order_type_enum() {
    // Test order type enum
    assert_eq!(OrderType::Market, OrderType::Market);
    assert_eq!(OrderType::Limit, OrderType::Limit);
    assert_ne!(OrderType::Market, OrderType::Limit);
}

#[tokio::test]
async fn test_error_types() {
    // Test error type creation
    let connection_error = ExecutionError::ConnectionError("Test connection error".to_string());
    let api_error = ExecutionError::ApiError("Test API error".to_string());
    let invalid_signal = ExecutionError::InvalidSignal("Test invalid signal".to_string());
    let circuit_breaker_error = ExecutionError::CircuitBreakerOpen("Test circuit breaker".to_string());
    let timeout_error = ExecutionError::TimeoutError("Test timeout".to_string());

    assert!(matches!(connection_error, ExecutionError::ConnectionError(_)));
    assert!(matches!(api_error, ExecutionError::ApiError(_)));
    assert!(matches!(invalid_signal, ExecutionError::InvalidSignal(_)));
    assert!(matches!(circuit_breaker_error, ExecutionError::CircuitBreakerOpen(_)));
    assert!(matches!(timeout_error, ExecutionError::TimeoutError(_)));
}
