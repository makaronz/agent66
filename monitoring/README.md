# SMC Trading Agent - Monitoring & Observability

Kompletny stack monitoringu i observability dla SMC Trading Agent z wykorzystaniem OpenTelemetry, Prometheus, Grafana i Jaeger.

## 🏗️ Architektura Monitoringu

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend       │    │  Rust Engine   │
│   (React)       │    │   (Node.js)      │    │                 │
│                 │    │                  │    │                 │
│ OTel Web SDK    │───▶│ OTel Node SDK    │───▶│ Custom Metrics  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌──────────────────────┐
                    │ OpenTelemetry        │
                    │ Collector            │
                    └──────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
           ┌─────────────┐ ┌──────────┐ ┌──────────┐
           │ Prometheus  │ │ Jaeger   │ │ Grafana  │
           │ (Metrics)   │ │ (Traces) │ │ (Dashboards)│
           └─────────────┘ └──────────┘ └──────────┘
                    │                       │
                    ▼                       ▼
           ┌─────────────┐         ┌──────────────┐
           │AlertManager │         │  Dashboards  │
           │ (Alerts)    │         │  & Analytics │
           └─────────────┘         └──────────────┘
```

## 📦 Komponenty

### 1. OpenTelemetry Collector
- **Plik**: `otel-collector-config.yaml`
- **Funkcja**: Centralny punkt zbierania telemetrii
- **Port**: 4317 (gRPC), 4318 (HTTP)

### 2. Prometheus
- **Plik**: `prometheus.yml`
- **Funkcja**: Zbieranie i przechowywanie metryk
- **Port**: 9090
- **Metryki**: System, aplikacja, trading, infrastruktura

### 3. Grafana
- **Porty**: 3000
- **Dashboardy**: System overview, Trading analytics
- **Provisioning**: Automatyczne ładowanie dashboardów

### 4. Jaeger
- **Port**: 16686
- **Funkcja**: Distributed tracing
- **Storage**: In-memory (development)

### 5. AlertManager
- **Plik**: `alertmanager.yml`
- **Port**: 9093
- **Funkcja**: Zarządzanie alertami

## 🚀 Szybki Start

### 1. Uruchomienie Stacku Monitoringu

```bash
# Przejdź do katalogu projektu
cd smc_trading_agent

# Uruchom stack monitoringu
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Sprawdź status kontenerów
docker-compose -f monitoring/docker-compose.monitoring.yml ps
```

### 2. Dostęp do Interfejsów

| Serwis | URL | Opis |
|--------|-----|------|
| Grafana | http://localhost:3000 | Dashboardy i wizualizacje |
| Prometheus | http://localhost:9090 | Metryki i zapytania |
| Jaeger | http://localhost:16686 | Distributed tracing |
| AlertManager | http://localhost:9093 | Zarządzanie alertami |
| OTel Collector | http://localhost:13133 | Health check |

### 3. Domyślne Loginy

**Grafana:**
- Username: `admin`
- Password: `admin123`

## 🔧 Konfiguracja Aplikacji

### Backend (Node.js)

```javascript
// Na początku aplikacji (przed innymi importami)
require('./monitoring/otel-instrumentation').init();

// W kodzie aplikacji
const { tradingMetrics } = require('./monitoring/otel-instrumentation');

// Przykład użycia metryk
tradingMetrics.signalsDetected.add(1, {
  signal_type: 'order_block',
  timeframe: '1h',
  pair: 'EURUSD'
});
```

### Frontend (React)

```javascript
// W src/index.js lub App.js
import { initializeWebTelemetry, useTelemetry } from './monitoring/otel-web-instrumentation';

// Inicjalizacja (automatyczna)
initializeWebTelemetry();

// W komponencie React
function TradingDashboard() {
  const { trackEvent, trackPageView } = useTelemetry();
  
  useEffect(() => {
    trackPageView('Trading Dashboard');
  }, []);
  
  const handleTradeClick = () => {
    trackEvent('trade_button_click', 'trading_panel');
    // logika tradingu...
  };
}
```

### Rust Engine

```rust
// W Cargo.toml
[dependencies]
prometheus = "0.13"
tokio = { version = "1.0", features = ["full"] }

// W kodzie Rust
use prometheus::{Counter, Histogram, register_counter, register_histogram};

lazy_static! {
    static ref ORDERS_EXECUTED: Counter = register_counter!(
        "smc_orders_executed_total",
        "Total number of orders executed"
    ).unwrap();
    
    static ref ORDER_LATENCY: Histogram = register_histogram!(
        "smc_order_execution_latency_seconds",
        "Order execution latency in seconds"
    ).unwrap();
}

// Użycie
ORDERS_EXECUTED.inc();
ORDER_LATENCY.observe(execution_time.as_secs_f64());
```

## 📊 Dashboardy

### 1. System Overview
- **Plik**: `smc-system-overview.json`
- **Metryki**: CPU, Memory, Network, Disk
- **Komponenty**: All services health status

### 2. Trading Dashboard
- **Plik**: `smc-trading-dashboard.json`
- **Metryki**: Signals, Orders, P&L, Latency
- **Analityka**: Trading performance

### 3. Custom Dashboards
Możesz tworzyć własne dashboardy w Grafana UI lub dodawać pliki JSON do katalogu `grafana/provisioning/dashboards/`.

## 🚨 Alerty

### Skonfigurowane Alerty

1. **System Health**
   - Service down
   - High CPU/Memory usage
   - Disk space low

2. **Trading Alerts**
   - High order latency
   - Failed orders
   - Signal detection issues

3. **Infrastructure**
   - Database connection issues
   - Redis connectivity
   - Network problems

### Konfiguracja Powiadomień

Edytuj `alertmanager.yml` aby skonfigurować:
- Email notifications
- Slack webhooks
- PagerDuty integration
- Custom webhooks

## 🔍 Metryki

### System Metrics
- `up` - Service availability
- `process_cpu_seconds_total` - CPU usage
- `process_resident_memory_bytes` - Memory usage
- `http_requests_total` - HTTP request count
- `http_request_duration_seconds` - Request latency

### Trading Metrics
- `smc_signals_detected_total` - Signal detection count
- `smc_signal_accuracy` - Signal accuracy percentage
- `smc_orders_executed_total` - Order execution count
- `smc_order_execution_latency` - Order latency
- `smc_market_data_latency` - Market data processing time
- `smc_active_connections` - Active exchange connections

### Custom Metrics
Dodaj własne metryki używając OpenTelemetry SDK:

```javascript
// Node.js
const customCounter = meter.createCounter('custom_metric_total');
customCounter.add(1, { label: 'value' });

// Rust
static ref CUSTOM_METRIC: Counter = register_counter!(
    "custom_metric_total",
    "Description"
).unwrap();
CUSTOM_METRIC.inc();
```

## 🐛 Debugging

### Sprawdzanie Logów

```bash
# Wszystkie serwisy
docker-compose -f monitoring/docker-compose.monitoring.yml logs

# Konkretny serwis
docker-compose -f monitoring/docker-compose.monitoring.yml logs grafana
docker-compose -f monitoring/docker-compose.monitoring.yml logs prometheus
docker-compose -f monitoring/docker-compose.monitoring.yml logs otel-collector
```

### Testowanie Konfiguracji

```bash
# Test konfiguracji Prometheus
docker run --rm -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus:latest promtool check config /etc/prometheus/prometheus.yml

# Test reguł alertów
docker run --rm -v $(pwd)/monitoring/alert-rules.yml:/etc/prometheus/alert-rules.yml prom/prometheus:latest promtool check rules /etc/prometheus/alert-rules.yml
```

### Health Checks

```bash
# OpenTelemetry Collector
curl http://localhost:13133/

# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health

# Jaeger
curl http://localhost:14269/
```

## 📈 Performance Tuning

### OpenTelemetry Collector
- Adjust batch sizes in `otel-collector-config.yaml`
- Configure memory limits
- Tune export intervals

### Prometheus
- Adjust scrape intervals
- Configure retention policies
- Optimize query performance

### Grafana
- Use query caching
- Optimize dashboard queries
- Configure data source settings

## 🔒 Security

### Production Considerations

1. **Authentication**
   - Enable Grafana authentication
   - Secure Prometheus with basic auth
   - Use TLS for all communications

2. **Network Security**
   - Use internal networks
   - Configure firewalls
   - Limit external access

3. **Data Privacy**
   - Sanitize sensitive data in traces
   - Configure data retention
   - Implement access controls

## 🚀 Production Deployment

### Environment Variables

```bash
# .env file
OTEL_SERVICE_NAME=smc-trading-agent
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
PROMETHEUS_PORT=9464
GRAFANA_ADMIN_PASSWORD=secure_password
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/...
ALERT_EMAIL_FROM=alerts@smc-trading.com
ALERT_EMAIL_TO=admin@smc-trading.com
```

### Docker Compose Override

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  grafana:
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-storage:/var/lib/grafana
      
  prometheus:
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    volumes:
      - prometheus-storage:/prometheus

volumes:
  grafana-storage:
  prometheus-storage:
```

## 📚 Dodatkowe Zasoby

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [SMC Trading Strategy Guide](../docs/smc-strategy.md)

## 🤝 Wsparcie

W przypadku problemów:
1. Sprawdź logi serwisów
2. Zweryfikuj konfigurację
3. Przetestuj connectivity
4. Skonsultuj dokumentację
5. Otwórz issue w repozytorium