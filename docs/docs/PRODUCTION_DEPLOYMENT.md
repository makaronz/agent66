# SMC Trading Agent - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the SMC Trading Agent in a production environment with enterprise-grade security, performance optimization, and operational excellence.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Prerequisites](#prerequisites)
3. [Configuration Setup](#configuration-setup)
4. [Security Configuration](#security-configuration)
5. [Deployment Process](#deployment-process)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Maintenance and Operations](#maintenance-and-operations)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Recovery](#backup-and-recovery)

---

## System Architecture

### Production Stack Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│  Trading Agent  │────│  Database (PG)  │
│   (SSL/HTTPS)   │    │  (FastAPI)      │    │  + TimescaleDB  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Grafana      │    │     Redis       │    │   Prometheus    │
│   Dashboard     │    │     Cache       │    │    Metrics      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Service Responsibilities

- **Trading Agent**: Core application logic, ML inference, trading decisions
- **PostgreSQL + TimescaleDB**: Time-series data storage and analytics
- **Redis**: High-performance caching and session management
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and monitoring dashboard
- **Nginx**: Reverse proxy, SSL termination, load balancing

---

## Prerequisites

### System Requirements

- **CPU**: Minimum 4 cores, recommended 8 cores
- **Memory**: Minimum 8GB RAM, recommended 16GB
- **Storage**: Minimum 50GB SSD, recommended 100GB SSD
- **Network**: Stable internet connection with low latency to exchanges
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+

### Software Dependencies

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.9+
- Git
- SSL certificates (for HTTPS)

### API Requirements

- **Exchange API Keys**: Production API keys from Binance, ByBit, and OANDA
- **Rate Limits**: Ensure API rate limits support expected trading volume
- **IP Whitelisting**: Configure exchange IP whitelisting if enabled

---

## Configuration Setup

### 1. Environment Configuration

Create production environment file from template:

```bash
cp .env.production.example .env
```

Edit `.env` file with your production values:

```bash
# Critical security settings (must be changed)
JWT_SECRET=your_super_secure_jwt_secret_minimum_32_characters
DB_PASSWORD=your_secure_database_password_here
REDIS_PASSWORD=your_secure_redis_password_here
GRAFANA_PASSWORD=your_secure_grafana_password_here

# Exchange API credentials
BINANCE_API_KEY=your_binance_production_api_key_here
BINANCE_API_SECRET=your_binance_production_api_secret_here
BYBIT_API_KEY=your_bybit_production_api_key_here
BYBIT_API_SECRET=your_bybit_production_api_secret_here
OANDA_API_KEY=your_oanda_production_api_key_here
OANDA_ACCOUNT_ID=your_oanda_production_account_id_here
```

### 2. Main Configuration

The main configuration is in `config.production.yaml`:

- **Application Settings**: Production mode, logging, performance
- **Exchange Configuration**: API endpoints, rate limits, symbols
- **Risk Management**: Position limits, circuit breakers, compliance
- **ML Configuration**: Model paths, inference settings, monitoring
- **Performance Tuning**: Database pools, caching, timeouts

### 3. Docker Configuration

Production Docker setup in `docker-compose.production.yml`:

- **Resource Limits**: CPU and memory constraints
- **Health Checks**: Service health monitoring
- **Volume Management**: Persistent data storage
- **Network Security**: Internal network isolation
- **Security Options**: Non-privileged user execution

---

## Security Configuration

### 1. API Security

```yaml
security:
  authentication:
    enabled: true
    method: "jwt"
    jwt_secret: "${JWT_SECRET}"
    jwt_expiration: 3600  # 1 hour

  api:
    rate_limit:
      requests_per_minute: 100
      burst_size: 20
    cors_origins: ["https://yourdomain.com"]
    ip_whitelist_enabled: true
```

### 2. Database Security

```yaml
database:
  ssl_mode: "require"
  password: "${DB_PASSWORD}"
  connection_pool_size: 20
  max_overflow: 50
  pool_timeout: 30
```

### 3. Exchange API Security

- **API Key Rotation**: Rotate keys every 30-90 days
- **IP Whitelisting**: Restrict API access to your servers
- **Permission Limits**: Use minimum required permissions
- **Monitor Usage**: Track API usage and unusual activity

### 4. Network Security

- **SSL/TLS**: Encrypt all external communications
- **Firewall**: Restrict access to necessary ports only
- **VPN**: Use VPN for administrative access
- **Monitoring**: Network traffic monitoring and alerting

---

## Deployment Process

### 1. Validation

Run comprehensive configuration validation:

```bash
./scripts/validate_config.sh production
```

### 2. Automated Deployment

Use the deployment script:

```bash
./scripts/deploy.sh production
```

The deployment script performs:
- Pre-deployment checks
- Service backup
- Image building
- Service orchestration
- Health verification
- Post-deployment validation

### 3. Manual Deployment Steps

For manual deployment:

```bash
# Build images
docker-compose -f docker-compose.production.yml build --no-cache

# Stop existing services
docker-compose -f docker-compose.production.yml down

# Start services in dependency order
docker-compose -f docker-compose.production.yml up -d postgres redis
sleep 30  # Wait for database
docker-compose -f docker-compose.production.yml up -d

# Verify health
docker-compose -f docker-compose.production.yml ps
curl -f http://localhost:8000/health
```

### 4. Post-Deployment Verification

- **Health Checks**: All services should report healthy status
- **API Testing**: Verify API endpoints are responding
- **Database Connectivity**: Test database connections
- **Monitoring**: Verify metrics collection
- **Security**: Validate security configurations

---

## Monitoring and Alerting

### 1. Prometheus Metrics

Access Prometheus metrics: `http://localhost:9090`

Key metrics to monitor:
- **System Health**: CPU, memory, disk usage
- **Application Performance**: Response times, error rates
- **Trading Metrics**: Order execution, profit/loss
- **Risk Indicators**: Drawdown, position limits
- **ML Performance**: Model accuracy, inference latency

### 2. Grafana Dashboards

Access Grafana: `http://localhost:3000`

Default dashboards included:
- **System Overview**: Infrastructure health
- **Trading Performance**: Trading metrics and P&L
- **Risk Management**: Risk indicators and alerts
- **ML Model Performance**: Model accuracy and drift
- **Exchange API Status**: API health and rate limits

### 3. Alert Rules

Critical alerts configured:
- **System Down**: Service unavailability
- **High Error Rate**: >5% error rate for 2+ minutes
- **Risk Breach**: Drawdown or position limit exceeded
- **Trading Halt**: Automatic trading suspension
- **ML Model Drift**: Model performance degradation

### 4. Notification Channels

Configure notification channels in Grafana:
- **Email**: Critical alerts
- **Slack**: Operational alerts
- **PagerDuty**: Emergency alerts

---

## Maintenance and Operations

### 1. Regular Maintenance Tasks

**Daily:**
- Monitor system health dashboards
- Review trading performance
- Check for security alerts

**Weekly:**
- Update security patches
- Review logs for anomalies
- Backup configuration changes

**Monthly:**
- Rotate API keys and secrets
- Update SSL certificates
- Performance optimization review

**Quarterly:**
- Security audit and assessment
- Capacity planning review
- Disaster recovery testing

### 2. Log Management

```yaml
logging:
  level: "INFO"
  format: "json"
  outputs: ["console", "file"]

  file:
    path: "logs/smc_trading.log"
    max_size_mb: 100
    backup_count: 10
    rotation: "daily"
```

Log locations:
- **Application Logs**: `logs/smc_trading.log`
- **Access Logs**: Nginx access logs
- **System Logs**: Docker container logs
- **Audit Logs**: Security and compliance logs

### 3. Performance Tuning

**Database Optimization:**
- Connection pooling (20+ connections)
- Query optimization and indexing
- Regular vacuum and analyze operations
- Monitoring slow queries

**Caching Strategy:**
- Redis for session management
- Application-level caching
- CDN for static assets
- Database query caching

**Resource Management:**
- CPU and memory limits enforcement
- Horizontal scaling considerations
- Load balancing configuration
- Autoscaling policies

---

## Troubleshooting

### 1. Common Issues

**Service Won't Start:**
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs smc-trading-agent

# Check configuration
./scripts/validate_config.sh production

# Verify environment variables
docker-compose -f docker-compose.production.yml config
```

**Database Connection Issues:**
```bash
# Test database connectivity
docker-compose -f docker-compose.production.yml exec postgres pg_isready

# Check connection pool status
docker-compose -f docker-compose.production.yml exec smc-trading-agent python -c "
import psycopg2
# Test database connection
"
```

**High Memory Usage:**
```bash
# Check resource usage
docker stats

# Monitor memory trends
curl http://localhost:9090/api/v1/query?query=container_memory_usage_bytes
```

### 2. Performance Issues

**Slow API Response:**
- Check database query performance
- Verify Redis cache hit ratio
- Monitor network latency
- Review ML model inference time

**Trading Execution Delays:**
- Check exchange API latency
- Monitor order book depth
- Verify network connectivity
- Review rate limit usage

### 3. Security Issues

**Unauthorized Access:**
```bash
# Review access logs
grep "401\|403" /var/log/nginx/access.log

# Check API key usage
# Review exchange API logs
```

**SSL Certificate Issues:**
```bash
# Verify certificate
openssl s_client -connect yourdomain.com:443

# Check certificate expiry
openssl x509 -in /path/to/cert.pem -noout -dates
```

---

## Backup and Recovery

### 1. Data Backup Strategy

**Database Backups:**
```bash
# Daily automated backups
docker-compose -f docker-compose.production.yml exec postgres pg_dump \
  -U smc_user -d smc_trading_production | gzip > backup_$(date +%Y%m%d).sql.gz

# Store backups off-site
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://your-backup-bucket/
```

**Configuration Backups:**
```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  config.production.yaml .env docker-compose.production.yml
```

### 2. Recovery Procedures

**Service Recovery:**
```bash
# Quick restart
docker-compose -f docker-compose.production.yml restart

# Full restart with data preservation
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

**Database Recovery:**
```bash
# Restore from backup
gunzip -c backup_20240101.sql.gz | \
docker-compose -f docker-compose.production.yml exec -T postgres psql \
  -U smc_user -d smc_trading_production
```

**Complete System Recovery:**
1. Restore configuration files
2. Restart database services
3. Restore database from backup
4. Restart application services
5. Verify system health
6. Test trading functionality

### 3. Disaster Recovery

**Recovery Time Objective (RTO):** 4 hours
**Recovery Point Objective (RPO):** 1 hour

**Disaster Recovery Plan:**
1. Activate disaster recovery site
2. Restore from latest backup
3. Update DNS to point to DR site
4. Verify all services operational
5. Monitor system performance
6. Communicate status to stakeholders

---

## Compliance and Auditing

### 1. Regulatory Compliance

**MiFID II Requirements:**
- Transaction reporting enabled
- Best execution records maintained
- Timestamp accuracy (UTC synchronized)
- Data retention for 7 years

**Data Protection (GDPR):**
- Personal data anonymization
- Right to data deletion
- Data breach notification procedures
- Privacy policy compliance

### 2. Audit Trail

**Trading Operations:**
- All trades logged with timestamps
- Decision-making process documented
- Risk management decisions recorded
- Algorithm performance metrics

**System Changes:**
- Configuration change logs
- Deployment records
- Security incident logs
- Performance monitoring data

### 3. Reporting

**Daily Reports:**
- Trading performance summary
- Risk metrics summary
- System health report
- Exception reports

**Monthly Reports:**
- Performance analytics
- Risk assessment
- Compliance status
- Security review

---

## Contact and Support

### Technical Support

- **Documentation**: This guide and inline code comments
- **Monitoring**: Grafana dashboards and Prometheus alerts
- **Logs**: Comprehensive logging throughout the system
- **Health Checks**: Built-in health check endpoints

### Emergency Contacts

- **System Administrator**: [Contact details]
- **Security Team**: [Contact details]
- **Compliance Officer**: [Contact details]
- **Exchange Support**: [Contact details]

### Escalation Procedures

1. **Level 1**: Automated alerts and monitoring
2. **Level 2**: On-call system administrator
3. **Level 3**: Development team and security team
4. **Level 4**: Management and regulatory compliance

---

## Appendices

### A. Configuration Reference

Detailed configuration options and their meanings are documented inline in the configuration files with comments.

### B. API Documentation

REST API documentation is available at: `http://localhost:8000/docs`

### C. Monitoring Metrics

Complete list of available Prometheus metrics:
- `smc_trading_*`: Trading-specific metrics
- `smc_risk_*`: Risk management metrics
- `smc_ml_*`: Machine learning metrics
- `system_*`: System infrastructure metrics

### D. Security Checklist

- [ ] API keys are for production accounts
- [ ] SSL/TLS is enabled for all external connections
- [ ] Rate limits are configured according to exchange limits
- [ ] Circuit breakers are enabled and tested
- [ ] Backup and disaster recovery is configured
- [ ] Monitoring and alerting is functional
- [ ] Security settings are reviewed and validated
- [ ] Compliance requirements are met
- [ ] Performance targets are achievable
- [ ] Failover procedures are documented and tested

---

*Last Updated: $(date)*
*Version: 2.0.0*