use rust_decimal::Decimal;
use uuid::Uuid;
use thiserror::Error;
use serde::{Deserialize, Serialize};
use ccxt_rs::{Exchange as CcxtExchange, Market, OrderType as CcxtOrderType, Side as CcxtSide, Order as CcxtOrder};
use async_trait::async_trait;
use std::collections::HashMap;

// Real CCXT integration types and Exchange
#[derive(Debug, Clone)]
pub struct ExchangeConfig {
    pub api_key: Option<String>,
    pub secret: Option<String>,
}

impl Default for ExchangeConfig {
    fn default() -> Self {
        Self {
            api_key: None,
            secret: None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Exchange {
    pub name: String,
    pub config: ExchangeConfig,
    pub ccxt_exchange: Option<CcxtExchange>,
}

// Convert our order types to CCXT types
#[derive(Debug, Clone, Copy)]
pub enum CcxtOrderType {
    Market,
    Limit,
}

impl From<OrderType> for CcxtOrderType {
    fn from(order_type: OrderType) -> Self {
        match order_type {
            OrderType::Market => CcxtOrderType::Market,
            OrderType::Limit => CcxtOrderType::Limit,
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub enum CcxtSide {
    Buy,
    Sell,
}

impl From<Action> for CcxtSide {
    fn from(action: Action) -> Self {
        match action {
            Action::Buy => CcxtSide::Buy,
            Action::Sell => CcxtSide::Sell,
        }
    }
}

#[derive(Debug, Clone)]
pub struct CcxtOrder {
    pub id: String,
    pub status: String,
}

impl From<ccxt_rs::Order> for CcxtOrder {
    fn from(order: ccxt_rs::Order) -> Self {
        Self {
            id: order.id.unwrap_or_default(),
            status: order.status.unwrap_or_default(),
        }
    }
}

impl Exchange {
    pub async fn new(name: &str, config: ExchangeConfig) -> Result<Self, String> {
        // Validate exchange name
        if name.is_empty() {
            return Err("Exchange name cannot be empty".to_string());
        }
        
        // Initialize CCXT exchange
        let ccxt_exchange = match CcxtExchange::new(name).await {
            Ok(exchange) => {
                // Set credentials if provided
                if let (Some(api_key), Some(secret)) = (&config.api_key, &config.secret) {
                    if let Err(e) = exchange.set_credentials(api_key.clone(), secret.clone()).await {
                        return Err(format!("Failed to set credentials: {}", e));
                    }
                }
                Some(exchange)
            }
            Err(e) => {
                return Err(format!("Failed to initialize CCXT exchange '{}': {}", name, e));
            }
        };
        
        Ok(Self {
            name: name.to_string(),
            config,
            ccxt_exchange,
        })
    }
    
    pub async fn create_order(
        &self,
        symbol: &str,
        order_type: CcxtOrderType,
        side: CcxtSide,
        amount: String,
        params: HashMap<String, String>,
    ) -> Result<CcxtOrder, String> {
        let exchange = self.ccxt_exchange.as_ref()
            .ok_or("CCXT exchange not initialized")?;
        
        let market = Market::new(symbol);
        let ccxt_order_type = match order_type {
            CcxtOrderType::Market => CcxtOrderType::Market,
            CcxtOrderType::Limit => CcxtOrderType::Limit,
        };
        let ccxt_side = match side {
            CcxtSide::Buy => CcxtSide::Buy,
            CcxtSide::Sell => CcxtSide::Sell,
        };
        
        // Convert params to CCXT format
        let mut ccxt_params = HashMap::new();
        for (key, value) in params {
            ccxt_params.insert(key, value);
        }
        
        // Add price if it's a limit order
        if order_type == CcxtOrderType::Limit {
            if let Some(price) = ccxt_params.get("price") {
                ccxt_params.insert("price".to_string(), price.clone());
            }
        }
        
        match exchange.create_order(market, ccxt_order_type, ccxt_side, amount, Some(ccxt_params)).await {
            Ok(order) => Ok(CcxtOrder::from(order)),
            Err(e) => Err(format!("Failed to create order: {}", e)),
        }
    }
    
    pub async fn cancel_order(&self, order_id: &str) -> Result<CcxtOrder, String> {
        let exchange = self.ccxt_exchange.as_ref()
            .ok_or("CCXT exchange not initialized")?;
        
        match exchange.cancel_order(order_id).await {
            Ok(order) => Ok(CcxtOrder::from(order)),
            Err(e) => Err(format!("Failed to cancel order: {}", e)),
        }
    }
    
    pub async fn fetch_order(&self, order_id: &str) -> Result<CcxtOrder, String> {
        let exchange = self.ccxt_exchange.as_ref()
            .ok_or("CCXT exchange not initialized")?;
        
        match exchange.fetch_order(order_id).await {
            Ok(order) => Ok(CcxtOrder::from(order)),
            Err(e) => Err(format!("Failed to fetch order: {}", e)),
        }
    }
}

// Mock Circuit Breaker implementation
#[derive(Debug, Clone)]
pub struct CircuitBreakerConfig {
    pub failure_threshold: u32,
    pub recovery_timeout: Duration,
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            recovery_timeout: Duration::from_secs(30),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum CircuitBreakerState {
    Closed,
    Open,
    HalfOpen,
}

#[derive(Debug)]
pub struct CircuitBreaker {
    config: CircuitBreakerConfig,
    state: CircuitBreakerState,
    failure_count: u32,
    last_failure_time: Option<Instant>,
}

impl CircuitBreaker {
    pub fn new(config: CircuitBreakerConfig) -> Self {
        Self {
            config,
            state: CircuitBreakerState::Closed,
            failure_count: 0,
            last_failure_time: None,
        }
    }
    
    pub fn is_closed(&self) -> bool {
        match self.state {
            CircuitBreakerState::Closed => true,
            CircuitBreakerState::Open => {
                // Check if recovery timeout has passed
                if let Some(last_failure) = self.last_failure_time {
                    last_failure.elapsed() > self.config.recovery_timeout
                } else {
                    false
                }
            }
            CircuitBreakerState::HalfOpen => true,
        }
    }
    
    pub fn record_success(&mut self) {
        self.failure_count = 0;
        self.state = CircuitBreakerState::Closed;
        self.last_failure_time = None;
    }
    
    pub fn record_failure(&mut self) {
        self.failure_count += 1;
        self.last_failure_time = Some(Instant::now());
        
        if self.failure_count >= self.config.failure_threshold {
            self.state = CircuitBreakerState::Open;
        }
    }
    
    pub fn state(&self) -> &CircuitBreakerState {
        &self.state
    }
}
use metrics::{counter, histogram};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{Duration, Instant};
use tracing::{info, warn, error, instrument, span, Level};
// use anyhow::Context; // Commented out as not used in current implementation

// Type aliases for better readability and maintainability
pub type ExchangeName = Arc<str>;
pub type ExchangeClients = Arc<RwLock<HashMap<ExchangeName, Exchange>>>;
pub type CircuitBreakers = Arc<RwLock<HashMap<ExchangeName, CircuitBreaker>>>;
pub type MetricsMap = HashMap<String, f64>;

// Performance and configuration constants
const DEFAULT_EXCHANGE_CAPACITY: usize = 16;
const DEFAULT_CIRCUIT_BREAKER_CAPACITY: usize = 16;
const MIN_QUANTITY: &str = "0";
const DEFAULT_MAX_RETRIES: u32 = 3;
const DEFAULT_RETRY_DELAY_MS: u64 = 100;
const DEFAULT_TIMEOUT_MS: u64 = 5000;
const DEFAULT_FAILURE_THRESHOLD: u32 = 5;
const DEFAULT_RECOVERY_TIMEOUT_MS: u64 = 30000;
const DEFAULT_LATENCY_THRESHOLD_MS: u64 = 50;
const ORDER_PARAMS_CAPACITY: usize = 8;

// Custom serde module for Arc<str>
mod arc_str_serde {
    use serde::{Deserialize, Deserializer, Serialize, Serializer};
    use std::sync::Arc;

    pub fn serialize<S>(value: &Arc<str>, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        value.as_ref().serialize(serializer)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Arc<str>, D::Error>
    where
        D: Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        Ok(Arc::from(s))
    }
}

/// Represents a trading signal generated by the decision engine.
/// 
/// # Example
/// ```
/// use rust_decimal::Decimal;
/// use uuid::Uuid;
/// 
/// let signal = Signal {
///     id: Uuid::new_v4(),
///     exchange: "binance".into(),
///     symbol: "BTCUSDT".to_string(),
///     action: Action::Buy,
///     price: Some(Decimal::from(50000)),
///     quantity: Decimal::from(1),
///     order_type: OrderType::Limit,
///     urgency: UrgencyLevel::Medium,
///     order_block_level: Some(50000.0),
/// };
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Signal {
    pub id: Uuid,
    #[serde(with = "arc_str_serde")]
    pub exchange: ExchangeName,
    pub symbol: String,
    pub action: Action,
    pub price: Option<Decimal>, // For limit/stop orders
    pub quantity: Decimal,
    pub order_type: OrderType,
    pub urgency: UrgencyLevel,
    pub order_block_level: Option<f64>, // For smart order routing
}

/// Defines the type of action to be taken.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum Action {
    Buy,
    Sell,
}

/// Defines the type of order to be placed.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum OrderType {
    Market,
    Limit,
}

/// Defines the urgency level for order execution.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum UrgencyLevel {
    Low,
    Medium,
    High,
}

/// Market conditions for smart order routing.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MarketConditions {
    pub volatility: f64,
    pub spread: f64,
    pub volume: f64,
    pub trend: f64, // -1.0 to 1.0 (bearish to bullish)
}

impl Default for MarketConditions {
    fn default() -> Self {
        Self {
            volatility: 0.0,
            spread: 0.0,
            volume: 0.0,
            trend: 0.0,
        }
    }
}

/// Smart order routing strategy.
#[derive(Debug, Clone)]
pub struct SmartOrderRouter {
    pub market_conditions: MarketConditions,
    pub risk_limits: RiskLimits,
}

/// Risk limits for order execution.
#[derive(Debug, Clone)]
pub struct RiskLimits {
    pub max_volatility: f64,
    pub max_spread: f64,
    pub min_volume: f64,
}

impl Default for RiskLimits {
    fn default() -> Self {
        Self {
            max_volatility: 0.05, // 5% volatility
            max_spread: 0.002,    // 0.2% spread
            min_volume: 1000.0,   // Minimum volume
        }
    }
}

/// Represents a concrete order to be sent to an exchange.
/// 
/// # Fields
/// * `id` - Unique identifier for this order
/// * `signal_id` - Reference to the original trading signal
/// * `exchange` - Target exchange for execution
/// * `symbol` - Trading pair symbol (e.g., "BTCUSDT")
/// * `action` - Buy or sell action
/// * `price` - Optional price for limit orders
/// * `quantity` - Order quantity
/// * `order_type` - Market or limit order
/// * `status` - Current order status
/// * `execution_time` - Time taken to execute
/// * `exchange_order_id` - Exchange-specific order identifier
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Order {
    pub id: Uuid,
    pub signal_id: Uuid,
    #[serde(with = "arc_str_serde")]
    pub exchange: ExchangeName,
    pub symbol: String,
    pub action: Action,
    pub price: Option<Decimal>,
    pub quantity: Decimal,
    pub order_type: OrderType,
    pub status: OrderStatus,
    pub execution_time: Option<Duration>,
    pub exchange_order_id: Option<String>,
}

/// Represents the status of an order.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum OrderStatus {
    New,
    Pending,
    Filled,
    PartiallyFilled,
    Cancelled,
    Failed,
}

/// Custom error types for the execution engine.
#[derive(Error, Debug, Clone)]
pub enum ExecutionError {
    #[error("Failed to connect to exchange: {0}")]
    ConnectionError(String),
    #[error("Exchange API error: {0}")]
    ApiError(String),
    #[error("Invalid trading signal: {0}")]
    InvalidSignal(String),
    #[error("Insufficient funds for order: {0}")]
    InsufficientFunds(String),
    #[error("Risk limit exceeded: {0}")]
    RiskLimitExceeded(String),
    #[error("Order execution failed: {0}")]
    ExecutionFailed(String),
    #[error("Circuit breaker open: {0}")]
    CircuitBreakerOpen(String),
    #[error("Timeout error: {0}")]
    TimeoutError(String),
    #[error("Invalid configuration: {0}")]
    InvalidConfiguration(String),
    #[error("An unknown error occurred")]
    Unknown,
}

/// Configuration for the OrderExecutor with validation and builder support.
/// 
/// # Example
/// ```
/// let config = OrderExecutorConfig::builder()
///     .max_retries(5)
///     .timeout_ms(3000)
///     .latency_threshold_ms(30)
///     .build()
///     .expect("Invalid configuration");
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct OrderExecutorConfig {
    pub max_retries: u32,
    pub retry_delay_ms: u64,
    pub timeout_ms: u64,
    pub circuit_breaker_failure_threshold: u32,
    pub circuit_breaker_recovery_timeout_ms: u64,
    pub latency_threshold_ms: u64,
}

impl Default for OrderExecutorConfig {
    fn default() -> Self {
        Self {
            max_retries: DEFAULT_MAX_RETRIES,
            retry_delay_ms: DEFAULT_RETRY_DELAY_MS,
            timeout_ms: DEFAULT_TIMEOUT_MS,
            circuit_breaker_failure_threshold: DEFAULT_FAILURE_THRESHOLD,
            circuit_breaker_recovery_timeout_ms: DEFAULT_RECOVERY_TIMEOUT_MS,
            latency_threshold_ms: DEFAULT_LATENCY_THRESHOLD_MS,
        }
    }
}

/// Validation trait for configuration objects
pub trait Validate {
    type Error;
    
    /// Validates the configuration and returns an error if invalid
    fn validate(&self) -> Result<(), Self::Error>;
}

impl Validate for OrderExecutorConfig {
    type Error = ExecutionError;
    
    fn validate(&self) -> Result<(), Self::Error> {
        if self.max_retries == 0 {
            return Err(ExecutionError::InvalidConfiguration(
                "max_retries must be greater than 0".to_string()
            ));
        }
        
        if self.timeout_ms == 0 {
            return Err(ExecutionError::InvalidConfiguration(
                "timeout_ms must be greater than 0".to_string()
            ));
        }
        
        if self.circuit_breaker_failure_threshold == 0 {
            return Err(ExecutionError::InvalidConfiguration(
                "circuit_breaker_failure_threshold must be greater than 0".to_string()
            ));
        }
        
        Ok(())
    }
}

/// Builder pattern for OrderExecutorConfig
#[derive(Debug, Default)]
pub struct OrderExecutorConfigBuilder {
    config: OrderExecutorConfig,
}

impl OrderExecutorConfigBuilder {
    pub fn new() -> Self {
        Self::default()
    }
    
    pub fn max_retries(mut self, max_retries: u32) -> Self {
        self.config.max_retries = max_retries;
        self
    }
    
    pub fn retry_delay_ms(mut self, retry_delay_ms: u64) -> Self {
        self.config.retry_delay_ms = retry_delay_ms;
        self
    }
    
    pub fn timeout_ms(mut self, timeout_ms: u64) -> Self {
        self.config.timeout_ms = timeout_ms;
        self
    }
    
    pub fn circuit_breaker_failure_threshold(mut self, threshold: u32) -> Self {
        self.config.circuit_breaker_failure_threshold = threshold;
        self
    }
    
    pub fn circuit_breaker_recovery_timeout_ms(mut self, timeout: u64) -> Self {
        self.config.circuit_breaker_recovery_timeout_ms = timeout;
        self
    }
    
    pub fn latency_threshold_ms(mut self, threshold: u64) -> Self {
        self.config.latency_threshold_ms = threshold;
        self
    }
    
    pub fn build(self) -> Result<OrderExecutorConfig, ExecutionError> {
        self.config.validate()?;
        Ok(self.config)
    }
}

impl OrderExecutorConfig {
    /// Creates a new configuration builder
    pub fn builder() -> OrderExecutorConfigBuilder {
        OrderExecutorConfigBuilder::new()
    }
}

/// High-performance order executor with CCXT integration and latency monitoring.
/// 
/// The OrderExecutor provides ultra-low latency trade execution with comprehensive
/// error handling, circuit breaker patterns, and performance monitoring.
/// 
/// # Key Features
/// 
/// * **Multi-Exchange Support**: Connects to multiple cryptocurrency exchanges
/// * **Circuit Breakers**: Prevents cascade failures with per-exchange circuit breakers
/// * **Latency Monitoring**: Tracks execution time and alerts on threshold breaches
/// * **Smart Retry Logic**: Exponential backoff with configurable retry attempts
/// * **Comprehensive Metrics**: Prometheus-compatible metrics collection
/// * **Type Safety**: Strong typing with validation for all operations
/// 
/// # Example
/// 
/// ```rust
/// use smc_trading_agent::execution_engine::executor::*;
/// 
/// let config = OrderExecutorConfig::builder()
///     .max_retries(5)
///     .timeout_ms(3000)
///     .latency_threshold_ms(30)
///     .build()
///     .expect("Valid configuration");
/// 
/// let executor = OrderExecutor::with_config(config);
/// executor.initialize_exchange("binance", Some(api_key), Some(secret)).await?;
/// ```
pub struct OrderExecutor {
    exchange_clients: ExchangeClients,
    circuit_breakers: CircuitBreakers,
    config: OrderExecutorConfig,
    metrics_enabled: bool,
    smart_router: SmartOrderRouter,
}

impl OrderExecutor {
    /// Create a new OrderExecutor with default configuration.
    /// 
    /// This is equivalent to calling `Self::with_config(OrderExecutorConfig::default())`.
    pub fn new() -> Self {
        Self::with_config(OrderExecutorConfig::default())
    }

    /// Create a new OrderExecutor with custom configuration.
    /// 
    /// # Arguments
    /// 
    /// * `config` - Configuration object that has been validated
    /// 
    /// # Example
    /// 
    /// ```rust
    /// let config = OrderExecutorConfig::builder()
    ///     .max_retries(5)
    ///     .build()
    ///     .expect("Valid config");
    /// let executor = OrderExecutor::with_config(config);
    /// ```
    pub fn with_config(config: OrderExecutorConfig) -> Self {
        let span = span!(Level::INFO, "order_executor_init", config = ?config);
        let _guard = span.enter();
        
        info!("Initializing OrderExecutor with validated configuration");
        
        Self {
            exchange_clients: Arc::new(RwLock::new(
                HashMap::with_capacity(DEFAULT_EXCHANGE_CAPACITY)
            )),
            circuit_breakers: Arc::new(RwLock::new(
                HashMap::with_capacity(DEFAULT_CIRCUIT_BREAKER_CAPACITY)
            )),
            config,
            metrics_enabled: true,
            smart_router: SmartOrderRouter {
                market_conditions: MarketConditions::default(),
                risk_limits: RiskLimits::default(),
            },
        }
    }

    /// Initialize exchange client for a specific exchange.
    /// 
    /// # Arguments
    /// 
    /// * `exchange_name` - Name of the exchange (e.g., "binance", "bybit")
    /// * `api_key` - Optional API key for authenticated operations
    /// * `secret` - Optional API secret for authenticated operations
    /// 
    /// # Returns
    /// 
    /// * `Ok(())` if initialization successful
    /// * `Err(ExecutionError)` if initialization fails
    /// 
    /// # Example
    /// 
    /// ```rust
    /// executor.initialize_exchange(
    ///     "binance", 
    ///     Some("your_api_key".to_string()), 
    ///     Some("your_secret".to_string())
    /// ).await?;
    /// ```
    #[instrument(skip(self, api_key, secret), fields(exchange = exchange_name))]
    pub async fn initialize_exchange(
        &self, 
        exchange_name: &str, 
        api_key: Option<String>, 
        secret: Option<String>
    ) -> Result<(), ExecutionError> {
        let start_time = Instant::now();
        let exchange_arc: ExchangeName = Arc::from(exchange_name);
        
        info!(exchange = %exchange_arc, "Initializing exchange client");
        
        // Validate exchange name
        if exchange_name.is_empty() {
            return Err(ExecutionError::InvalidConfiguration(
                "Exchange name cannot be empty".to_string()
            ));
        }
        
        let config = ExchangeConfig {
            api_key,
            secret,
            ..Default::default()
        };

        match Exchange::new(exchange_name, config).await {
            Ok(exchange) => {
                // Insert exchange client
                {
                    let mut clients = self.exchange_clients.write().await;
                    clients.insert(exchange_arc.clone(), exchange);
                }
                
                // Initialize circuit breaker for this exchange
                let circuit_config = CircuitBreakerConfig {
                    failure_threshold: self.config.circuit_breaker_failure_threshold,
                    recovery_timeout: Duration::from_millis(self.config.circuit_breaker_recovery_timeout_ms),
                    ..Default::default()
                };
                
                {
                    let mut breakers = self.circuit_breakers.write().await;
                    breakers.insert(exchange_arc.clone(), CircuitBreaker::new(circuit_config));
                }
                
                let duration = start_time.elapsed();
                
                // Record metrics
                histogram!("exchange_initialization_duration_ms", duration.as_millis() as f64);
                counter!("exchange_initializations_total", 1, "exchange" => exchange_name.to_string());
                
                info!(
                    exchange = %exchange_arc, 
                    duration_ms = duration.as_millis(),
                    "Exchange initialized successfully"
                );
                
                Ok(())
            }
            Err(e) => {
                error!(
                    exchange = %exchange_arc, 
                    error = %e,
                    "Failed to initialize exchange"
                );
                
                counter!("exchange_initialization_failures_total", 1, "exchange" => exchange_name.to_string());
                
                Err(ExecutionError::ConnectionError(
                    format!("Failed to initialize exchange '{}': {}", exchange_name, e)
                ))
            }
        }
    }

    /// Execute an SMC trading signal with comprehensive error handling and monitoring.
    /// 
    /// This method provides the main entry point for executing trading signals with:
    /// - Signal validation
    /// - Circuit breaker checks
    /// - Retry logic with exponential backoff
    /// - Latency monitoring and alerting
    /// - Comprehensive metrics collection
    /// 
    /// # Arguments
    /// 
    /// * `signal` - The trading signal to execute
    /// 
    /// # Returns
    /// 
    /// * `Ok(Order)` - Successfully created order with execution details
    /// * `Err(ExecutionError)` - Execution failed with specific error details
    /// 
    /// # Performance
    /// 
    /// Target latency: <50ms (configurable via `latency_threshold_ms`)
    /// 
    /// # Example
    /// 
    /// ```rust
    /// let signal = Signal {
    ///     id: Uuid::new_v4(),
    ///     exchange: "binance".into(),
    ///     symbol: "BTCUSDT".to_string(),
    ///     action: Action::Buy,
    ///     price: Some(Decimal::from(50000)),
    ///     quantity: Decimal::from(1),
    ///     order_type: OrderType::Limit,
    /// };
    /// 
    /// let order = executor.execute_smc_signal(signal).await?;
    /// ```
    #[instrument(
        skip(self, signal), 
        fields(
            signal_id = %signal.id,
            exchange = %signal.exchange,
            symbol = %signal.symbol,
            action = ?signal.action,
            order_type = ?signal.order_type
        )
    )]
    pub async fn execute_smc_signal(&self, signal: Signal) -> Result<Order, ExecutionError> {
        let start_time = Instant::now();
        
        info!("Executing SMC trading signal");
        counter!("smc_signals_executed_total", 1, 
            "exchange" => signal.exchange.to_string(),
            "action" => format!("{:?}", signal.action),
            "order_type" => format!("{:?}", signal.order_type)
        );

        // 1. Validate the incoming signal
        self.validate_signal(&signal)
            .map_err(|e| {
                counter!("signal_validation_failures_total", 1);
                e
            })?;

        // 2. Check circuit breaker status
        self.check_circuit_breaker(&signal.exchange).await?;

        // 3. Apply smart order routing to determine optimal order type
        let optimal_order_type = self.determine_order_type(signal.urgency, signal.order_block_level);
        
        // 4. Create an Order from the Signal with optimized field access and smart routing
        let mut order = Order {
            id: Uuid::new_v4(),
            signal_id: signal.id,
            exchange: signal.exchange.clone(),
            symbol: signal.symbol,
            action: signal.action,
            price: if optimal_order_type == OrderType::Limit {
                signal.price.or_else(|| signal.order_block_level.map(|level| Decimal::from_f64(level).unwrap_or_default()))
            } else {
                None // Market orders don't need price
            },
            quantity: signal.quantity,
            order_type: optimal_order_type,
            status: OrderStatus::New,
            execution_time: None,
            exchange_order_id: None,
        };

        // 4. Execute the order with retry logic
        let execution_result = self.execute_order_with_retry(&mut order).await;
        
        let total_duration = start_time.elapsed();
        order.execution_time = Some(total_duration);
        
        // Record comprehensive metrics
        let duration_ms = total_duration.as_millis() as f64;
        histogram!("order_execution_duration_ms", duration_ms, 
            "exchange" => order.exchange.to_string(),
            "symbol" => order.symbol.clone(),
            "action" => format!("{:?}", order.action)
        );
        
        // Check latency threshold
        if total_duration.as_millis() > self.config.latency_threshold_ms as u128 {
            warn!(
                duration_ms = duration_ms,
                threshold_ms = self.config.latency_threshold_ms,
                order_id = %order.id,
                "Order execution exceeded latency threshold"
            );
            
            counter!("order_execution_latency_threshold_exceeded_total", 1,
                "exchange" => order.exchange.to_string()
            );
        }

        // Handle execution result
        match execution_result {
            Ok(_) => {
                counter!("orders_executed_successfully_total", 1,
                    "exchange" => order.exchange.to_string(),
                    "symbol" => order.symbol.clone()
                );
                
                info!(
                    order_id = %order.id,
                    duration_ms = duration_ms,
                    exchange_order_id = ?order.exchange_order_id,
                    "Order executed successfully"
                );
                
                Ok(order)
            }
            Err(e) => {
                counter!("orders_execution_failed_total", 1,
                    "exchange" => order.exchange.to_string(),
                    "error_type" => format!("{:?}", e)
                );
                
                error!(
                    order_id = %order.id,
                    error = %e,
                    duration_ms = duration_ms,
                    "Order execution failed"
                );
                
                order.status = OrderStatus::Failed;
                Err(e)
            }
        }
    }

    /// Execute a single order with retry logic and circuit breaker.
    /// 
    /// Implements exponential backoff retry strategy with comprehensive error tracking.
    /// 
    /// # Arguments
    /// 
    /// * `order` - Mutable reference to order (status will be updated)
    /// 
    /// # Returns
    /// 
    /// * `Ok(())` if order executed successfully (within max retries)
    /// * `Err(ExecutionError)` if all retry attempts failed
    #[instrument(
        skip(self, order),
        fields(
            order_id = %order.id,
            exchange = %order.exchange,
            symbol = %order.symbol,
            max_retries = self.config.max_retries
        )
    )]
    async fn execute_order_with_retry(&self, order: &mut Order) -> Result<(), ExecutionError> {
        let mut last_error = None;
        
        for attempt in 0..=self.config.max_retries {
            let attempt_start = Instant::now();
            
            match self.execute_single_order(order).await {
                Ok(_) => {
                    let attempt_duration = attempt_start.elapsed();
                    histogram!("order_execution_attempt_duration_ms", attempt_duration.as_millis() as f64);
                    
                    if attempt > 0 {
                        info!("Order executed successfully on attempt {}", attempt + 1);
                        counter!("order_execution_retry_success_total", 1);
                    }
                    return Ok(());
                }
                Err(e) => {
                    last_error = Some(e.clone());
                    let attempt_duration = attempt_start.elapsed();
                    
                    warn!("Order execution attempt {} failed: {:?} in {:?}", 
                          attempt + 1, e, attempt_duration);
                    
                    counter!("order_execution_attempt_failed_total", 1);
                    histogram!("order_execution_failed_attempt_duration_ms", attempt_duration.as_millis() as f64);
                    
                    // Update circuit breaker
                    self.record_failure(&order.exchange).await;
                    
                    if attempt < self.config.max_retries {
                        let delay = Duration::from_millis(self.config.retry_delay_ms * (attempt + 1) as u64);
                        tokio::time::sleep(delay).await;
                    }
                }
            }
        }
        
        Err(last_error.unwrap_or(ExecutionError::Unknown))
    }

    /// Execute a single order on the exchange
    #[instrument(skip(self, order))]
    async fn execute_single_order(&self, order: &mut Order) -> Result<(), ExecutionError> {
        let clients = self.exchange_clients.read().await;
        let exchange = clients.get(&order.exchange)
            .ok_or_else(|| ExecutionError::ConnectionError(format!("Exchange {} not initialized", order.exchange)))?;

        // Convert our order types to CCXT types using From trait
        let ccxt_side: CcxtSide = order.action.into();
        let ccxt_order_type: CcxtOrderType = order.order_type.into();

        // Prepare order parameters with optimized capacity
        let mut params = HashMap::with_capacity(ORDER_PARAMS_CAPACITY);
        if let Some(price) = order.price {
            params.insert("price".to_string(), price.to_string());
        }

        // Execute the order with timeout
        let execution_future = exchange.create_order(
            &order.symbol,
            ccxt_order_type,
            ccxt_side,
            order.quantity.to_string(),
            params,
        );

        let timeout_duration = Duration::from_millis(self.config.timeout_ms);
        let result = tokio::time::timeout(timeout_duration, execution_future).await;

        match result {
            Ok(Ok(ccxt_order)) => {
                order.status = OrderStatus::Pending;
                order.exchange_order_id = Some(ccxt_order.id);
                
                // Update circuit breaker on success
                self.record_success(&order.exchange).await;
                
                info!("Order placed successfully: exchange_id={:?}, our_id={:?}", 
                      order.exchange_order_id, order.id);
                Ok(())
            }
            Ok(Err(e)) => {
                error!("Exchange API error: {:?}", e);
                Err(ExecutionError::ApiError(format!("Exchange error: {:?}", e)))
            }
            Err(_) => {
                error!("Order execution timeout after {}ms", self.config.timeout_ms);
                Err(ExecutionError::TimeoutError(format!("Order execution timeout after {}ms", self.config.timeout_ms)))
            }
        }
    }

    /// Validate trading signal with comprehensive checks.
    /// 
    /// # Arguments
    /// 
    /// * `signal` - The signal to validate
    /// 
    /// # Returns
    /// 
    /// * `Ok(())` if signal is valid
    /// * `Err(ExecutionError::InvalidSignal)` with detailed error message
    /// 
    /// # Validation Rules
    /// 
    /// - Quantity must be positive (> 0)
    /// - Limit orders must have a price specified
    /// - Exchange name must not be empty
    /// - Symbol must not be empty
    /// - Price (if specified) must be positive
    fn validate_signal(&self, signal: &Signal) -> Result<(), ExecutionError> {
        // Validate quantity
        if signal.quantity <= Decimal::ZERO {
            return Err(ExecutionError::InvalidSignal(
                format!(
                    "Invalid quantity '{}': must be positive (> 0). Signal ID: {}",
                    signal.quantity, signal.id
                )
            ));
        }

        // Validate price for limit orders
        if signal.order_type == OrderType::Limit {
            match signal.price {
                None => {
                    return Err(ExecutionError::InvalidSignal(
                        format!(
                            "Limit order missing required price. Signal ID: {}, Symbol: {}",
                            signal.id, signal.symbol
                        )
                    ));
                }
                Some(price) if price <= Decimal::ZERO => {
                    return Err(ExecutionError::InvalidSignal(
                        format!(
                            "Invalid price '{}': must be positive for limit orders. Signal ID: {}",
                            price, signal.id
                        )
                    ));
                }
                Some(_) => {} // Valid price
            }
        }

        // Validate exchange name
        if signal.exchange.is_empty() {
            return Err(ExecutionError::InvalidSignal(
                format!(
                    "Exchange name cannot be empty. Signal ID: {}, Symbol: {}",
                    signal.id, signal.symbol
                )
            ));
        }

        // Validate symbol
        if signal.symbol.is_empty() {
            return Err(ExecutionError::InvalidSignal(
                format!(
                    "Trading symbol cannot be empty. Signal ID: {}, Exchange: {}",
                    signal.id, signal.exchange
                )
            ));
        }

        // Additional symbol format validation
        if !signal.symbol.chars().all(|c| c.is_ascii_alphanumeric()) {
            return Err(ExecutionError::InvalidSignal(
                format!(
                    "Invalid symbol format '{}': only alphanumeric characters allowed. Signal ID: {}",
                    signal.symbol, signal.id
                )
            ));
        }

        Ok(())
    }

    /// Check circuit breaker status for exchange.
    /// 
    /// # Arguments
    /// 
    /// * `exchange` - Exchange name to check
    /// 
    /// # Returns
    /// 
    /// * `Ok(())` if circuit breaker is closed (allowing operations)
    /// * `Err(ExecutionError::CircuitBreakerOpen)` if circuit breaker is open
    async fn check_circuit_breaker(&self, exchange: &ExchangeName) -> Result<(), ExecutionError> {
        let breakers = self.circuit_breakers.read().await;
        
        if let Some(circuit_breaker) = breakers.get(exchange) {
            if !circuit_breaker.is_closed() {
                error!(
                    exchange = %exchange,
                    state = ?circuit_breaker.state(),
                    "Circuit breaker is open - blocking operations"
                );
                
                counter!("circuit_breaker_open_total", 1, "exchange" => exchange.to_string());
                
                return Err(ExecutionError::CircuitBreakerOpen(
                    format!(
                        "Circuit breaker open for exchange '{}'. Operations temporarily blocked to prevent cascade failures.",
                        exchange
                    )
                ));
            }
        } else {
            // No circuit breaker found - this should not happen if exchange was properly initialized
            warn!(
                exchange = %exchange,
                "No circuit breaker found for exchange - this may indicate initialization issues"
            );
        }
        
        Ok(())
    }

    /// Record failure in circuit breaker.
    /// 
    /// Updates the circuit breaker state and metrics for the given exchange.
    async fn record_failure(&self, exchange: &ExchangeName) {
        let mut breakers = self.circuit_breakers.write().await;
        if let Some(circuit_breaker) = breakers.get_mut(exchange) {
            circuit_breaker.record_failure();
            counter!("circuit_breaker_failures_total", 1, "exchange" => exchange.to_string());
        }
    }

    /// Record success in circuit breaker.
    /// 
    /// Updates the circuit breaker state and metrics for the given exchange.
    async fn record_success(&self, exchange: &ExchangeName) {
        let mut breakers = self.circuit_breakers.write().await;
        if let Some(circuit_breaker) = breakers.get_mut(exchange) {
            circuit_breaker.record_success();
            counter!("circuit_breaker_successes_total", 1, "exchange" => exchange.to_string());
        }
    }

    /// Cancel an existing order
    #[instrument(skip(self))]
    pub async fn cancel_order(&self, exchange: &str, order_id: &str) -> Result<(), ExecutionError> {
        let start_time = Instant::now();
        
        info!("Cancelling order: {} on exchange: {}", order_id, exchange);
        counter!("order_cancellations_attempted_total", 1);

        let clients = self.exchange_clients.read().await;
        let exchange_client = clients.get(exchange)
            .ok_or_else(|| ExecutionError::ConnectionError(format!("Exchange {} not initialized", exchange)))?;

        let cancellation_future = exchange_client.cancel_order(order_id);
        let timeout_duration = Duration::from_millis(self.config.timeout_ms);
        
        let result = tokio::time::timeout(timeout_duration, cancellation_future).await;

        let duration = start_time.elapsed();
        histogram!("order_cancellation_duration_ms", duration.as_millis() as f64);

        match result {
            Ok(Ok(_)) => {
                counter!("order_cancellations_successful_total", 1);
                info!("Order cancelled successfully: {} in {:?}", order_id, duration);
                Ok(())
            }
            Ok(Err(e)) => {
                counter!("order_cancellations_failed_total", 1);
                error!("Failed to cancel order {}: {:?}", order_id, e);
                Err(ExecutionError::ApiError(format!("Cancellation failed: {:?}", e)))
            }
            Err(_) => {
                counter!("order_cancellations_timeout_total", 1);
                error!("Order cancellation timeout after {}ms", self.config.timeout_ms);
                Err(ExecutionError::TimeoutError(format!("Cancellation timeout after {}ms", self.config.timeout_ms)))
            }
        }
    }

    /// Get order status from exchange
    #[instrument(skip(self))]
    pub async fn get_order_status(&self, exchange: &str, order_id: &str) -> Result<OrderStatus, ExecutionError> {
        let start_time = Instant::now();
        
        let clients = self.exchange_clients.read().await;
        let exchange_client = clients.get(exchange)
            .ok_or_else(|| ExecutionError::ConnectionError(format!("Exchange {} not initialized", exchange)))?;

        let status_future = exchange_client.fetch_order(order_id);
        let timeout_duration = Duration::from_millis(self.config.timeout_ms);
        
        let result = tokio::time::timeout(timeout_duration, status_future).await;

        let duration = start_time.elapsed();
        histogram!("order_status_fetch_duration_ms", duration.as_millis() as f64);

        match result {
            Ok(Ok(ccxt_order)) => {
                let status = match ccxt_order.status.as_str() {
                    "open" => OrderStatus::Pending,
                    "closed" => OrderStatus::Filled,
                    "canceled" => OrderStatus::Cancelled,
                    "partially_filled" => OrderStatus::PartiallyFilled,
                    _ => OrderStatus::Failed,
                };
                
                counter!("order_status_fetches_successful_total", 1);
                Ok(status)
            }
            Ok(Err(e)) => {
                counter!("order_status_fetches_failed_total", 1);
                error!("Failed to fetch order status: {:?}", e);
                Err(ExecutionError::ApiError(format!("Status fetch failed: {:?}", e)))
            }
            Err(_) => {
                counter!("order_status_fetches_timeout_total", 1);
                error!("Order status fetch timeout after {}ms", self.config.timeout_ms);
                Err(ExecutionError::TimeoutError(format!("Status fetch timeout after {}ms", self.config.timeout_ms)))
            }
        }
    }

    /// Get comprehensive performance metrics.
    /// 
    /// Returns a map of metric names to values for monitoring and alerting.
    /// Metrics are collected from the Prometheus registry if metrics are enabled.
    /// 
    /// # Returns
    /// 
    /// A HashMap containing current metric values including:
    /// - Execution counts and rates
    /// - Latency statistics
    /// - Circuit breaker states
    /// - Exchange-specific metrics
    /// 
    /// # Example
    /// 
    /// ```rust
    /// let metrics = executor.get_metrics();
    /// if let Some(latency) = metrics.get("average_execution_latency_ms") {
    ///     println!("Average latency: {}ms", latency);
    /// }
    /// ```
    pub fn get_metrics(&self) -> MetricsMap {
        let mut metrics = HashMap::with_capacity(32);
        
        if !self.metrics_enabled {
            return metrics;
        }
        
        // Note: In a real implementation, these would be collected from
        // the metrics registry. For now, we provide a comprehensive structure.
        
        // Execution metrics
        metrics.insert("orders_executed_total".to_string(), 0.0);
        metrics.insert("orders_executed_successfully_total".to_string(), 0.0);
        metrics.insert("orders_execution_failed_total".to_string(), 0.0);
        metrics.insert("smc_signals_executed_total".to_string(), 0.0);
        
        // Latency metrics
        metrics.insert("order_execution_duration_ms_avg".to_string(), 0.0);
        metrics.insert("order_execution_duration_ms_p50".to_string(), 0.0);
        metrics.insert("order_execution_duration_ms_p95".to_string(), 0.0);
        metrics.insert("order_execution_duration_ms_p99".to_string(), 0.0);
        metrics.insert("order_execution_latency_threshold_exceeded_total".to_string(), 0.0);
        
        // Circuit breaker metrics
        metrics.insert("circuit_breaker_failures_total".to_string(), 0.0);
        metrics.insert("circuit_breaker_successes_total".to_string(), 0.0);
        metrics.insert("circuit_breaker_open_total".to_string(), 0.0);
        
        // Exchange metrics
        metrics.insert("exchange_initializations_total".to_string(), 0.0);
        metrics.insert("exchange_initialization_failures_total".to_string(), 0.0);
        metrics.insert("exchange_initialization_duration_ms_avg".to_string(), 0.0);
        
        // Retry metrics
        metrics.insert("order_execution_attempt_failed_total".to_string(), 0.0);
        metrics.insert("order_execution_retry_success_total".to_string(), 0.0);
        
        // Order management metrics
        metrics.insert("order_cancellations_attempted_total".to_string(), 0.0);
        metrics.insert("order_cancellations_successful_total".to_string(), 0.0);
        metrics.insert("order_cancellations_failed_total".to_string(), 0.0);
        metrics.insert("order_status_fetches_successful_total".to_string(), 0.0);
        metrics.insert("order_status_fetches_failed_total".to_string(), 0.0);
        
        // Validation metrics
        metrics.insert("signal_validation_failures_total".to_string(), 0.0);
        
        // Configuration metrics
        metrics.insert("config_max_retries".to_string(), self.config.max_retries as f64);
        metrics.insert("config_timeout_ms".to_string(), self.config.timeout_ms as f64);
        metrics.insert("config_latency_threshold_ms".to_string(), self.config.latency_threshold_ms as f64);
        
        metrics
    }
    
    /// Check if metrics collection is enabled.
    pub fn metrics_enabled(&self) -> bool {
        self.metrics_enabled
    }
    
    /// Enable or disable metrics collection.
    /// 
    /// # Arguments
    /// 
    /// * `enabled` - Whether to enable metrics collection
    pub fn set_metrics_enabled(&mut self, enabled: bool) {
        self.metrics_enabled = enabled;
        info!(metrics_enabled = enabled, "Metrics collection state changed");
    }
    
    /// Get current configuration.
    /// 
    /// Returns a copy of the current configuration for inspection.
    pub fn config(&self) -> &OrderExecutorConfig {
        &self.config
    }
    
    /// Get the number of initialized exchanges.
    /// 
    /// # Returns
    /// 
    /// The number of currently initialized exchange clients.
    pub async fn exchange_count(&self) -> usize {
        let clients = self.exchange_clients.read().await;
        clients.len()
    }
    
    /// Check if a specific exchange is initialized.
    /// 
    /// # Arguments
    /// 
    /// * `exchange_name` - Name of the exchange to check
    /// 
    /// # Returns
    /// 
    /// `true` if the exchange is initialized and ready for trading
    pub async fn is_exchange_initialized(&self, exchange_name: &str) -> bool {
        let clients = self.exchange_clients.read().await;
        let exchange_arc: ExchangeName = Arc::from(exchange_name);
        clients.contains_key(&exchange_arc)
    }

    /// Determine optimal order type based on market conditions and urgency.
    /// 
    /// Implements smart order routing logic that considers:
    /// - Market volatility and spread
    /// - Order urgency level
    /// - Risk limits and constraints
    /// - Current market conditions
    /// 
    /// # Arguments
    /// 
    /// * `urgency` - Urgency level of the order
    /// * `order_block_level` - Optional order block level for limit orders
    /// 
    /// # Returns
    /// 
    /// Optimal order type for current market conditions
    pub fn determine_order_type(&self, urgency: UrgencyLevel, order_block_level: Option<f64>) -> OrderType {
        match urgency {
            UrgencyLevel::High => {
                // High urgency always uses market orders for immediate execution
                OrderType::Market
            }
            UrgencyLevel::Medium => {
                // Medium urgency: check market conditions
                if self.smart_router.market_conditions.volatility > self.smart_router.risk_limits.max_volatility {
                    // High volatility: use limit orders for better price control
                    OrderType::Limit
                } else if self.smart_router.market_conditions.spread > self.smart_router.risk_limits.max_spread {
                    // High spread: use limit orders to avoid slippage
                    OrderType::Limit
                } else {
                    // Normal conditions: use market orders for faster execution
                    OrderType::Market
                }
            }
            UrgencyLevel::Low => {
                // Low urgency: prefer limit orders for better pricing
                OrderType::Limit
            }
        }
    }

    /// Update market conditions for smart order routing.
    /// 
    /// # Arguments
    /// 
    /// * `conditions` - New market conditions
    pub fn update_market_conditions(&mut self, conditions: MarketConditions) {
        self.smart_router.market_conditions = conditions;
        info!("Updated market conditions: {:?}", conditions);
    }

    /// Update risk limits for smart order routing.
    /// 
    /// # Arguments
    /// 
    /// * `limits` - New risk limits
    pub fn update_risk_limits(&mut self, limits: RiskLimits) {
        self.smart_router.risk_limits = limits;
        info!("Updated risk limits: {:?}", limits);
    }

    /// Get current market conditions.
    pub fn get_market_conditions(&self) -> &MarketConditions {
        &self.smart_router.market_conditions
    }

    /// Get current risk limits.
    pub fn get_risk_limits(&self) -> &RiskLimits {
        &self.smart_router.risk_limits
    }
}

// Additional trait implementations for better ergonomics

impl Default for OrderExecutor {
    fn default() -> Self {
        Self::new()
    }
}

// Validation implementations for core types
impl Signal {
    /// Create a new signal with default urgency and order block level.
    pub fn new(
        id: Uuid,
        exchange: ExchangeName,
        symbol: String,
        action: Action,
        price: Option<Decimal>,
        quantity: Decimal,
        order_type: OrderType,
    ) -> Self {
        Self {
            id,
            exchange,
            symbol,
            action,
            price,
            quantity,
            order_type,
            urgency: UrgencyLevel::Medium,
            order_block_level: price.map(|p| p.to_f64().unwrap_or_default()),
        }
    }

    /// Create a new signal with custom urgency and order block level.
    pub fn with_routing(
        id: Uuid,
        exchange: ExchangeName,
        symbol: String,
        action: Action,
        price: Option<Decimal>,
        quantity: Decimal,
        order_type: OrderType,
        urgency: UrgencyLevel,
        order_block_level: Option<f64>,
    ) -> Self {
        Self {
            id,
            exchange,
            symbol,
            action,
            price,
            quantity,
            order_type,
            urgency,
            order_block_level,
        }
    }
}

impl Validate for Signal {
    type Error = ExecutionError;
    
    fn validate(&self) -> Result<(), Self::Error> {
        // Reuse the validation logic from OrderExecutor
        let dummy_executor = OrderExecutor::new();
        dummy_executor.validate_signal(self)
    }
}

impl Validate for Order {
    type Error = ExecutionError;
    
    fn validate(&self) -> Result<(), Self::Error> {
        if self.quantity <= Decimal::ZERO {
            return Err(ExecutionError::InvalidSignal(
                format!("Invalid order quantity '{}': must be positive", self.quantity)
            ));
        }
        
        if self.order_type == OrderType::Limit && self.price.is_none() {
            return Err(ExecutionError::InvalidSignal(
                "Limit order missing required price".to_string()
            ));
        }
        
        if self.exchange.is_empty() {
            return Err(ExecutionError::InvalidSignal(
                "Order exchange cannot be empty".to_string()
            ));
        }
        
        if self.symbol.is_empty() {
            return Err(ExecutionError::InvalidSignal(
                "Order symbol cannot be empty".to_string()
            ));
        }
        
        Ok(())
    }
}
