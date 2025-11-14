# 🎬 Film Industry Time Tracking System - Deployment & Operations Guide

## 📋 Table of Contents

1. [Infrastructure Overview](#infrastructure-overview)
2. [Zero-Downtime Deployment](#zero-downtime-deployment)
3. [Monitoring & Observability](#monitoring--observability)
4. [Security & Compliance](#security--compliance)
5. [Backup & Disaster Recovery](#backup--disaster-recovery)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)
8. [Runbooks](#runbooks)

---

## 🏗️ Infrastructure Overview

### Production Architecture

The Film Industry Time Tracking System uses a highly available, scalable architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CDN (Vercel)  │────│  Load Balancer  │────│  Application    │
│   (Static)      │    │   (Nginx)       │    │   (Backend)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │     Grafana     │    │   PostgreSQL    │
│   (Metrics)     │    │   (Dashboard)   │    │  (Primary)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Loki        │    │    Jaeger       │    │     Redis       │
│   (Logs)        │    │   (Tracing)     │    │    (Cache)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components

- **Frontend**: React/Vite application deployed on Vercel CDN
- **Backend**: Node.js/Express API with Docker containers
- **Database**: PostgreSQL with primary-replica setup
- **Cache**: Redis master-slave configuration
- **Monitoring**: Prometheus + Grafana + Loki + Jaeger
- **Load Balancer**: Nginx with SSL termination
- **Container Orchestration**: Docker Compose (with Kubernetes ready)

---

## 🚀 Zero-Downtime Deployment

### Blue-Green Deployment Strategy

Our deployment strategy ensures zero downtime by maintaining two identical environments:

```bash
# Deploy new version
./scripts/blue-green-deploy.sh deploy v2.1.0

# Check deployment status
./scripts/blue-green-deploy.sh status

# Rollback if needed
./scripts/blue-green-deploy.sh rollback
```

### Deployment Process

1. **Pre-deployment Checks**
   - Security scanning (Snyk, Trivy)
   - Code quality validation
   - Automated testing
   - Performance regression testing

2. **Deploy to Target Environment**
   - Pull latest Docker images
   - Start services in non-live environment
   - Health checks validation

3. **Traffic Switching**
   - Update load balancer configuration
   - Switch DNS/traffic gradually
   - Monitor for issues

4. **Post-deployment**
   - Cleanup old environment
   - Update monitoring dashboards
   - Send notifications

### Manual Deployment Commands

```bash
# Full deployment with health checks
docker-compose -f docker-compose.prod.yml up -d

# Scale specific services
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Rolling updates
docker-compose -f docker-compose.prod.yml up -d --no-deps backend
```

---

## 📊 Monitoring & Observability

### Metrics Collection

Our comprehensive monitoring setup includes:

#### Application Metrics
- HTTP request/response metrics
- Business KPIs (active users, projects, time entries)
- Database performance metrics
- Cache hit rates and latency
- WebSocket connection metrics

#### Infrastructure Metrics
- CPU, Memory, Disk usage
- Network I/O and latency
- Container resource usage
- Database connection pools

#### Custom Business Metrics
- Time entry creation rates
- Department-specific analytics
- Project progress tracking
- Crew member activity levels

### Accessing Monitoring Tools

- **Grafana Dashboards**: `https://monitoring.filmtracker.com:3001`
- **Prometheus**: `https://monitoring.filmtracker.com:9090`
- **Jaeger Tracing**: `https://monitoring.filmtracker.com:16686`
- **AlertManager**: `https://monitoring.filmtracker.com:9093`

### Alerting Rules

Critical alerts are configured for:
- Service downtime (5 minutes)
- High error rates (>5% over 5 minutes)
- Response time degradation (>1s P95)
- Database connection issues
- Memory/CPU usage (>90%)
- Disk space (>85%)

### Log Aggregation

All logs are centralized using Loki:
- Application logs (structured JSON)
- Access logs (Nginx)
- System logs (syslog)
- Container logs (Docker)

Query logs with LogQL:
```logql
{job="film-tracker"} |= "error"
{instance="backend-1"} |~ "HTTP.*5[0-9][0-9]"
```

---

## 🔒 Security & Compliance

### Security Measures

#### Application Security
- JWT-based authentication
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection
- Rate limiting (100 req/min)

#### Infrastructure Security
- SSL/TLS encryption
- Network segmentation
- Container security scanning
- Vulnerability management
- Access control (RBAC)
- Secrets management

#### Security Monitoring
- Real-time threat detection
- Anomaly detection
- Security event logging
- Compliance reporting

### Security Scanning

Our CI/CD pipeline includes:
- **Snyk**: Dependency vulnerability scanning
- **Trivy**: Container image scanning
- **CodeQL**: Static analysis security testing
- **npm audit**: Package vulnerability checking

### Compliance Features

- **GDPR**: Data protection and privacy
- **SOC 2**: Security controls and reporting
- **ISO 27001**: Information security management
- **Data Retention**: Automated cleanup policies

---

## 💾 Backup & Disaster Recovery

### Backup Strategy

#### Database Backups
- **Frequency**: Every 6 hours
- **Retention**: 30 days (daily), 90 days (weekly)
- **Storage**: Encrypted cloud storage (multiple regions)
- **Type**: Full + incremental

#### Application Backups
- Configuration files
- SSL certificates
- Environment variables
- Docker images

#### Backup Verification
- Daily integrity checks
- Weekly restore testing
- Monthly disaster recovery drills

### Disaster Recovery Procedures

#### RTO/RPO Targets
- **Recovery Time Objective (RTO)**: 2 hours
- **Recovery Point Objective (RPO)**: 15 minutes

#### Recovery Steps

1. **Assessment** (5 minutes)
   - Determine scope of outage
   - Identify affected services

2. **Communication** (10 minutes)
   - Notify stakeholders
   - Update status page

3. **Recovery** (60-90 minutes)
   - Restore from latest backup
   - Rebuild affected services
   - Validate data integrity

4. **Verification** (15 minutes)
   - Health checks
   - Smoke tests
   - Performance validation

### Backup Scripts

```bash
# Manual backup
./scripts/backup-database.sh
./scripts/backup-application.sh

# Restore from backup
./scripts/restore-database.sh backup-2024-01-15-12-00.sql
./scripts/restore-application.sh backup-2024-01-15-12-00.tar.gz
```

---

## ⚡ Performance Optimization

### Performance Monitoring

#### Key Metrics
- **Response Time**: P95 < 500ms
- **Availability**: > 99.9%
- **Error Rate**: < 0.1%
- **Throughput**: 1000+ RPS

#### Optimization Areas
- Database query optimization
- Caching strategies
- CDN configuration
- Image optimization
- Code splitting

### Database Optimization

#### Query Performance
- Index optimization
- Query plan analysis
- Connection pooling
- Read replicas for scaling

#### Monitoring Queries
```sql
-- Identify slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'time_entries';
```

### Caching Strategy

#### Multi-level Caching
1. **CDN Cache** (Vercel Edge)
   - Static assets: 1 year
   - API responses: 5 minutes

2. **Application Cache** (Redis)
   - User sessions: 24 hours
   - API responses: 1 hour
   - Database queries: 30 minutes

3. **Database Cache**
   - Query result cache
   - Prepared statements

### Frontend Optimization

- **Bundle Splitting**: Route-based and vendor splitting
- **Lazy Loading**: Components and images
- **Service Workers**: Offline caching
- **Image Optimization**: WebP format, responsive images

---

## 🔧 Troubleshooting

### Common Issues

#### Service Unavailable

**Symptoms**: 503 errors, health check failures

**Troubleshooting Steps**:
1. Check service status:
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

2. Check logs:
   ```bash
   docker-compose -f docker-compose.prod.yml logs backend
   ```

3. Check resource usage:
   ```bash
   docker stats
   ```

4. Verify database connectivity:
   ```bash
   docker exec -it film-tracker-postgres-primary psql -U postgres -d film_tracker -c "SELECT 1;"
   ```

#### Slow Performance

**Symptoms**: High response times, user complaints

**Troubleshooting Steps**:
1. Check system metrics in Grafana
2. Analyze database queries:
   ```sql
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   ```

3. Check cache hit rates:
   ```bash
   docker exec film-tracker-redis-master redis-cli info stats
   ```

4. Review recent deployments

#### Database Issues

**Symptoms**: Connection errors, query timeouts

**Troubleshooting Steps**:
1. Check connection pool:
   ```bash
   docker exec -it backend-1 npm run db:check
   ```

2. Monitor slow queries:
   ```sql
   SELECT query, mean_time, calls
   FROM pg_stat_statements
   ORDER BY mean_time DESC LIMIT 10;
   ```

3. Check replication status:
   ```sql
   SELECT * FROM pg_stat_replication;
   ```

### Diagnostic Commands

```bash
# System health check
./scripts/health-check.sh

# Service diagnostics
./scripts/diagnose-service.sh backend

# Performance test
./scripts/performance-test.sh

# Security audit
./scripts/security-audit.sh
```

---

## 📚 Runbooks

### Incident Response

#### Severity Levels

**P1 - Critical**: Service outage, data loss
- Response time: 15 minutes
- Escalation: Immediate
- Communication: Public status update

**P2 - High**: Performance degradation, partial outage
- Response time: 1 hour
- Escalation: 2 hours
- Communication: Stakeholder notification

**P3 - Medium**: Feature issues, minor impact
- Response time: 4 hours
- Escalation: 24 hours
- Communication: Team notification

**P4 - Low**: Documentation, improvements
- Response time: 1 week
- Escalation: Sprint planning
- Communication: Backlog entry

#### Incident Response Process

1. **Detection**
   - Automated monitoring alerts
   - User reports
   - System checks

2. **Assessment**
   - Determine severity level
   - Identify scope and impact
   - Create incident channel

3. **Response**
   - Implement immediate fixes
   - Communicate with stakeholders
   - Document actions taken

4. **Resolution**
   - Verify fix effectiveness
   - Implement permanent solutions
   - Update monitoring

5. **Post-mortem**
   - Root cause analysis
   - Process improvements
   - Knowledge sharing

### Maintenance Procedures

#### Scheduled Maintenance

1. **Planning**
   - Choose maintenance window
   - Communicate with users
   - Prepare rollback plan

2. **Execution**
   - Take system snapshots
   - Apply updates
   - Run smoke tests

3. **Validation**
   - Verify functionality
   - Check performance
   - Monitor for issues

4. **Cleanup**
   - Remove temporary files
   - Update documentation
   - Close maintenance window

#### Emergency Maintenance

1. **Immediate Response**
   - Stabilize system
   - Prevent data loss
   - Communicate status

2. **Investigation**
   - Identify root cause
   - Plan permanent fix
   - Estimate timeline

3. **Recovery**
   - Implement fixes
   - Restore services
   - Verify functionality

### Scaling Procedures

#### Horizontal Scaling

```bash
# Scale backend services
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Scale frontend services
docker-compose -f docker-compose.prod.yml up -d --scale frontend=2

# Update load balancer
./scripts/update-load-balancer.sh
```

#### Database Scaling

```bash
# Add read replica
docker-compose -f docker-compose.prod.yml up -d postgres-replica-2

# Update application configuration
./scripts/update-db-config.sh
```

#### Monitoring During Scaling

- Watch response times
- Monitor error rates
- Check resource utilization
- Validate data consistency

---

## 📞 Emergency Contacts

### Primary Contacts

- **DevOps Lead**: +1-555-0123
- **Backend Lead**: +1-555-0124
- **Frontend Lead**: +1-555-0125
- **Database Admin**: +1-555-0126

### Escalation Contacts

- **CTO**: +1-555-0100
- **VP Engineering**: +1-555-0101
- **CEO**: +1-555-0102

### Service Providers

- **Cloud Provider**: AWS Support - 1-800-AWS-HELP
- **CDN Provider**: Vercel Support - support@vercel.com
- **Database Provider**: PostgreSQL Community
- **Monitoring Provider**: Grafana Labs Support

---

## 📄 Documentation Updates

This guide should be updated when:
- Infrastructure changes are made
- New services are added
- Monitoring rules change
- Security policies update
- Performance baselines change
- Contact information changes

**Document Version**: 2.0.0
**Last Updated**: 2024-01-15
**Next Review**: 2024-04-15