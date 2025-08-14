# SMC Trading Agent

A sophisticated algorithmic trading system that implements Smart Money Concepts (SMC) for automated cryptocurrency and forex trading.

## Core Features

- **Multi-Exchange Support**: Integrates with Binance, Bybit, and Oanda for diverse market access
- **SMC Pattern Detection**: Advanced algorithms to identify order blocks, liquidity zones, and institutional trading patterns
- **Risk Management**: Comprehensive position sizing, stop-loss, and circuit breaker mechanisms
- **Real-time Processing**: Live market data ingestion and analysis with sub-second latency
- **Model Ensemble**: Machine learning models including LSTM, Random Forest, and Gradient Boosting for decision making
- **Web Interface**: React-based dashboard for monitoring, configuration, and manual intervention

## Architecture

The system follows a microservices architecture with:
- Python backend for trading logic and data processing
- Rust execution engine for high-performance trade execution
- React frontend for user interface
- Express.js API layer for client-server communication
- Kafka for real-time data streaming
- TimescaleDB for time-series data storage
- Redis for caching and session management

## Target Users

Professional traders, quantitative analysts, and trading firms looking to implement institutional-grade Smart Money Concepts in their automated trading strategies.