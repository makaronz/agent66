# Specifications & Data Contracts: SMC Trading Agent

## 1. REST API (Future)

- **Endpoint Versioning:** `/api/v1/...`
- **Authentication:** Bearer Token (JWT)

## 2. WebSocket Message Formats

- **Market Data Stream:**
    ```json
    {
      "type": "market_data",
      "timestamp": "2023-10-27T10:00:00Z",
      "symbol": "BTC/USD",
      "data": {
        "open": 60000.5,
        "high": 60100.0,
        "low": 59900.0,
        "close": 60050.0,
        "volume": 120.5
      }
    }
    ```
- **Trade Signal:**
    ```json
    {
      "type": "trade_signal",
      "timestamp": "2023-10-27T10:05:00Z",
      "signal_id": "sig_12345",
      "strategy": "OrderBlock_H1",
      "details": {
        "symbol": "BTC/USD",
        "direction": "long",
        "entry": 60050.0,
        "stop_loss": 59800.0,
        "take_profit": 61000.0,
        "confidence": 0.85
      }
    }
    ```

## 3. JSON Schema for Configuration

A `config.schema.json` will be maintained to validate the structure of `config.yml`.

## 4. Deprecation Policy

- **Minor Versions:** No breaking changes.
- **Major Versions:** Breaking changes are permissible. A 3-month deprecation window will be provided for any retired API endpoints, with advance notice in the documentation.

