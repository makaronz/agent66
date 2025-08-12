# Monitoring & Observability Assessment

## Current State
- Health endpoints: `/health`, `/health/ready`, `/health/live`, `/metrics` via `EnhancedHealthMonitor`
- Grafana dashboard JSON stub; Prometheus planned in Compose

## Gaps
- No alerting rules documented; limited dashboards; no tracing
- Missing common RED/USE metrics for API and services

## Recommendations
- Integrate OpenTelemetry (traces + metrics + logs) across Node, Python, Rust
- Define SLOs and alerts (latency, error rate, saturation)
- Expand dashboards: request rates, p95 latency, CB state, Kafka lag, DB health
