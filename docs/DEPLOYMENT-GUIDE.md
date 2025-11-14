# Film Industry Time Tracking System - Deployment Guide

## Overview

This guide covers the complete deployment process for the Film Industry Time Tracking System, including containerization, CI/CD pipelines, monitoring, backup strategies, and scaling considerations for handling multiple film productions.

## 🏗️ Architecture Overview

The system is designed with a microservices architecture supporting:

- **Frontend**: React-based SPA with Vite build system
- **Backend**: Node.js/Express API with TypeScript
- **Database**: PostgreSQL with Redis caching
- **Monitoring**: Prometheus + Grafana stack
- **Load Balancing**: Nginx for high availability

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+
- pnpm 8.15.4+
- AWS CLI (for S3 backups)

### Environment Setup

1. **Clone the repository**
```bash
git clone https://github.com/your-org/film-industry-time-tracker.git
cd film-industry-time-tracker
```

2. **Set up environment variables**
```bash
# Copy environment template
cp .env.example .env.staging
cp .env.example .env.production

# Edit environment files with your values
nano .env.staging
nano .env.production
```

3. **Development deployment**
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:3002
# Database Admin: http://localhost:8080
```

## 🐳 Container Deployment

### Production Deployment

1. **Build and deploy**
```bash
# Deploy to staging
./scripts/deploy.sh staging

# Deploy to production (requires approval)
./scripts/deploy.sh production
```

2. **Health checks**
```bash
# Run health checks
./scripts/deploy.sh health

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### Environment Files

Required environment variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@host:5432/database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=film_tracker

# Redis Configuration
REDIS_URL=redis://user:password@host:6379
REDIS_PASSWORD=redis_password

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Security
ENCRYPTION_KEY=your-32-character-encryption-key
JWT_SECRET=your-jwt-secret

# Application
NODE_ENV=production
PORT=3002
CORS_ORIGIN=https://your-domain.com
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

The project uses GitHub Actions for automated deployment:

- **Trigger**: Push to main branch or manual workflow dispatch
- **Security**: Automated security scans and vulnerability checks
- **Testing**: Unit, integration, and E2E tests
- **Build**: Docker multi-platform builds (AMD64/ARM64)
- **Deploy**: Staging and production environments

### Pipeline Stages

1. **Security & Quality Checks**
   - npm audit
   - Code quality validation
   - Security scanning

2. **Build & Test**
   - Multi-service build matrix
   - Unit and integration tests
   - Test coverage reporting

3. **Docker Build**
   - Multi-platform image builds
   - Container registry push
   - Image tagging strategy

4. **Deployment**
   - Staging deployment (automatic)
   - Production deployment (manual approval)
   - Health checks and smoke tests

### Manual Deployment

```bash
# Force deployment (skips tests)
FORCE_DEPLOY=true ./scripts/deploy.sh production

# Rollback deployment
./scripts/deploy.sh rollback

# Cleanup unused resources
./scripts/deploy.sh cleanup
```

## 📊 Monitoring & Logging

### Prometheus Metrics

Key metrics tracked:

- **Application**: Response times, error rates, request counts
- **Database**: Connection usage, query performance
- **Cache**: Hit rates, memory usage
- **System**: CPU, memory, disk usage

### Grafana Dashboards

Pre-configured dashboards:

- **System Overview**: Infrastructure health
- **Application Performance**: API metrics
- **Database Performance**: PostgreSQL metrics
- **Cache Performance**: Redis metrics

### Alerting

Alerts configured for:

- **Critical**: Service downtime, database failures
- **Warning**: High resource usage, slow responses
- **Info**: Deployment events, backup completion

### Log Management

Application logs are structured and include:

- Request/response logging
- Error stack traces
- Performance metrics
- Security events

## 💾 Backup Strategy

### Automated Backups

Daily backups include:

1. **Database**: PostgreSQL dumps with compression
2. **Cache**: Redis RDB files
3. **Files**: Uploaded documents and media
4. **Configuration**: Environment and config files

### Backup Execution

```bash
# Run all backups
./scripts/backup-strategy.sh all

# Run specific backup types
./scripts/backup-strategy.sh database
./scripts/backup-strategy.sh redis
./scripts/backup-strategy.sh files

# Cleanup old backups
./scripts/backup-strategy.sh cleanup

# Verify backup integrity
./scripts/backup-strategy.sh verify
```

### Retention Policy

- **Local**: 7 days
- **S3**: 30 days (Standard IA storage)
- **Archive**: 1 year (Glacier storage)

### Disaster Recovery

1. **Identify failure point**
2. **Rollback to last known good state**
3. **Restore from latest backup**
4. **Verify system integrity**
5. **Resume normal operations**

## 📈 Scaling Strategy

### Horizontal Scaling

The system supports:

- **Frontend**: Multiple Nginx instances behind load balancer
- **Backend**: Multiple API servers with session affinity
- **Database**: Primary-replica PostgreSQL configuration
- **Cache**: Redis master-slave replication

### Multi-Production Support

For handling multiple film productions:

1. **Database Sharding**
   - Separate databases per production
   - Connection pooling per shard
   - Cross-shard query optimization

2. **Resource Isolation**
   - Dedicated containers per large production
   - Resource limits and quotas
   - Performance monitoring per production

3. **Load Distribution**
   - Geographic distribution for global productions
   - CDN integration for media files
   - Intelligent routing based on location

### Auto-scaling Configuration

```yaml
# Docker Compose with auto-scaling
services:
  backend:
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 🔒 Security Considerations

### Container Security

- Non-root user execution
- Read-only filesystems where possible
- Secrets management via environment variables
- Regular security scanning

### Network Security

- Internal network isolation
- Firewall rules for service communication
- SSL/TLS encryption for all endpoints
- Rate limiting and DDoS protection

### Data Protection

- Encryption at rest (database, file storage)
- Encryption in transit (API calls, cache)
- Regular security audits
- Compliance with GDPR/CCPA

## 🛠️ Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   # Check logs
   docker-compose logs service-name

   # Check resource usage
   docker stats
   ```

2. **Database connection issues**
   ```bash
   # Verify database connectivity
   docker exec -it postgres-container psql -U postgres

   # Check connection pool
   docker exec backend-container npm run db:status
   ```

3. **High memory usage**
   ```bash
   # Check memory usage
   docker stats --no-stream

   # Restart specific service
   docker-compose restart service-name
   ```

### Performance Tuning

1. **Database Optimization**
   - Index optimization
   - Query tuning
   - Connection pool sizing

2. **Cache Optimization**
   - Redis memory tuning
   - Cache warming strategies
   - Eviction policies

3. **Application Optimization**
   - Code profiling
   - Memory leak detection
   - Load testing

## 📞 Support

For deployment issues:

1. **Check logs**: Application and system logs
2. **Run diagnostics**: Health checks and smoke tests
3. **Review metrics**: Prometheus/Grafana dashboards
4. **Contact support**: Provide logs and error details

## 🔄 Version Updates

### Update Process

1. **Prepare environment**
   ```bash
   # Backup current deployment
   ./scripts/backup-strategy.sh all
   ```

2. **Update code**
   ```bash
   # Pull latest changes
   git pull origin main

   # Update dependencies
   pnpm install
   ```

3. **Deploy**
   ```bash
   # Deploy to staging first
   ./scripts/deploy.sh staging

   # Test thoroughly
   ./scripts/deploy.sh health

   # Deploy to production
   ./scripts/deploy.sh production
   ```

### Rollback Process

```bash
# Quick rollback
./scripts/deploy.sh rollback

# Full database restore
./scripts/restore-from-backup.sh backup-date
```

---

*This deployment guide is maintained and updated with each release. For the latest version, check the repository documentation.*