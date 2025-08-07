# Tech Context: SMC Trading Agent

## 1. Core Technologies

- **Primary Language:** Python (for AI/ML, data processing, and high-level logic)
- **Performance-critical Language:** Rust (for the execution engine where speed is paramount)
- **Data Storage:** InfluxDB or TimescaleDB for time-series market data.
- **Messaging/Events:** RabbitMQ or Redis Pub/Sub for inter-service communication.
- **Containerization:** Docker & Docker Compose for development and testing.
- **Deployment:** Kubernetes for production orchestration.

## 2. Development Setup

1.  **Prerequisites:**
    *   Python 3.10+
    *   Rust (latest stable)
    *   Docker & Docker Compose
2.  **Clone the repository:**
    ```bash
    git clone [repo-url]
    cd smc-trading-agent
    ```
3.  **Set up environment variables:**
    *   Copy `.env.example` to `.env`.
    *   Fill in API keys for data providers and brokers.
4.  **Launch services:**
    ```bash
    docker-compose up --build
    ```

## 3. Debugging and Tracing

- **Logging:** Standardized JSON-formatted logs are outputted from all services.
- **Tracing:** OpenTelemetry will be integrated for distributed tracing across services to debug complex interaction flows.
- **Debugging Hooks:** The Python services will use `debugpy` to allow remote debugger attachment.

