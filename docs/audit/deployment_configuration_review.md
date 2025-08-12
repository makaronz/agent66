# Deployment Configuration Review

## Dockerfiles
- `smc_agent.Dockerfile` and `data_pipeline.Dockerfile` install Python deps and run modules; consider slim images + non‑root user + multi‑stage builds

## Docker Compose
- Services: smc‑agent, data‑ingestion, timescaledb, redis, prometheus, grafana
- Networking: single bridge `smc-network`
- Improvements: healthchecks, resource limits, secrets via env files or secrets, volumes for configs

## Kubernetes
- Deployment + Service + HPA sample; probes at `/health` and `/ready`
- Add: ConfigMaps/Secrets, PodSecurity, RBAC, NetworkPolicies, resource requests/limits per service

## Environment
- Document required envs; standardize `.env.example`; ensure no secrets in repo
