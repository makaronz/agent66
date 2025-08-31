#![cfg(feature = "real_exchange")]

use uuid::Uuid;
use smc_trading_agent::execution_engine::executor::*;

// Minimal smoke test for real_exchange feature.
// This does not hit a live venue yet – it validates the adapter plumbing
// returns a plausible Order id and status.
#[tokio::test]
#[ignore]
async fn smoke_execute_limit_order_returns_ack() {
    let exchange = Exchange::new("binance", ExchangeConfig::default())
        .await
        .expect("exchange create");

    let symbol = "BTCUSDT";
    let order_type = CcxtOrderType::Limit;
    let side = CcxtSide::Buy;
    let amount = "0.001".to_string();
    let mut params = std::collections::HashMap::new();
    params.insert("price".to_string(), "30000".to_string());

    let ack = exchange
        .create_order(symbol, order_type, side, amount, params)
        .await
        .expect("order create");

    assert!(!ack.id.is_empty());
    assert!(ack.status == "new" || ack.status == "pending" || ack.status == "open");
}

