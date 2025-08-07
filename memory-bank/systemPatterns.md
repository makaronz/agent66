# System Patterns: SMC Trading Agent

## 1. Architecture

The agent follows a modular, event-driven architecture. Components are decoupled and communicate through a central message bus or event queue. This allows for scalability, resilience, and easier maintenance.

```mermaid
C4Context
  title System Architecture Diagram

  System_Ext(DataProvider, "Market Data Provider")
  System_Ext(Broker, "Broker/Exchange")

  System_Boundary(SMCAgent, "SMC Trading Agent") {
    Component(Ingestion, "Data Ingestion", "Python", "Subscribes to market data streams.")
    Component(Detector, "SMC Detector", "Python/Rust", "Identifies SMC patterns from data.")
    Component(DecisionEngine, "Decision Engine", "Python/AI", "Evaluates trading opportunities.")
    Component(ExecutionEngine, "Execution Engine", "Rust", "Places and manages orders.")
    Component(RiskManager, "Risk Manager", "Python", "Monitors and controls risk exposure.")
    ComponentDb(DataStore, "Time-Series DB", "Stores market and trade data.")
    Component(Monitoring, "Monitoring", "Prometheus/Grafana", "Collects and visualizes metrics.")
  }

  Rel(DataProvider, Ingestion, "Provides real-time market data")
  Rel(Ingestion, Detector, "Feeds market data")
  Rel(Detector, DecisionEngine, "Signals potential patterns")
  Rel(DecisionEngine, RiskManager, "Checks against risk rules")
  Rel(DecisionEngine, ExecutionEngine, "Sends trade orders")
  Rel(ExecutionEngine, Broker, "Executes trades")
  Rel(Ingestion, DataStore, "Stores raw data")
  Rel_Back(Monitoring, SMCAgent, "Monitors all components")
```

## 2. Key Design Patterns

- **Observer Pattern:** Used for distributing market data updates from the ingestion service to various listeners (detector, storage, etc.).
- **Strategy Pattern:** The decision engine uses different strategy objects to evaluate various SMC setups (e.g., `OrderBlockStrategy`, `LiquidityGrabStrategy`). This allows for easy addition of new trading logic.
- **Circuit Breaker:** Implemented in the `risk_manager` to halt trading automatically under adverse conditions (e.g., excessive drawdown, API failures).

## 3. Pattern Graveyard

- **Rejected:** A monolithic architecture.
- **Reason:** A monolithic design would be difficult to scale, test, and maintain. The microservices/modular approach allows for independent development and deployment of components, and even mixing languages (e.g., Python for AI, Rust for performance-critical execution).

