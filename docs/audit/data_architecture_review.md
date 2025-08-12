# Data Architecture Review

## Schema Highlights (Supabase)
- Core tables: `users`, `user_api_keys`, `user_configurations`, `trading_sessions`, `trades`, `smc_signals`, `market_data_cache`
- Indexing present on key access paths; RLS enabled across tables

## Data Flows
- Ingestion normalizes exchange data and streams to Kafka
- Signals and trades recorded; cache table for market data performance

## Security & Governance
- RLS policies enforce tenant isolation; ensure keys encrypted at rest
- Backups/retention policy to be defined; PII footprint minimized

## Recommendations
- Define data lineage and retention per table; add anonymization where possible
- Add timescaled hypertables and compression policies for time‑series
