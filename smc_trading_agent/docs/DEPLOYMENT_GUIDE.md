# SMC Trading Agent Deployment Guide

This comprehensive guide covers the deployment of the Smart Money Concepts (SMC) Trading Agent in various environments from development to production.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Installation Methods](#installation-methods)
5. [Docker Deployment](#docker-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Configuration Management](#configuration-management)
8. [Database Setup](#database-setup)
9. [Security Configuration](#security-configuration)
10. [Monitoring and Logging](#monitoring-and-logging)
11. [Performance Tuning](#performance-tuning)
12. [Validation and Testing](#validation-and-testing)
13. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **CPU**: 2 vCPU cores
- **Memory**: 4GB RAM
- **Storage**: 20GB available disk space
- **Network**: Stable internet connection with <100ms latency to exchanges

### Recommended Requirements
- **CPU**: 4+ vCPU cores
- **Memory**: 8GB+ RAM
- **Storage**: 50GB+ SSD storage
- **Network**: Low-latency connection (<50ms to major exchanges)

### Supported Platforms
- **Operating Systems**: Ubuntu 20.04+, CentOS 8+, RHEL 8+, macOS 10.15+, Windows 10/11 (with WSL2)
- **Container Runtimes**: Docker 20.10+, containerd 1.4+
- **Kubernetes**: v1.24+

## Prerequisites

### Software Dependencies

**For Development/Local Setup:**
```bash
# Python 3.11+
python --version

# Node.js 18+ and npm
node --version
npm --version

# Rust toolchain (for execution engine)
rustc --version
cargo --version

# Docker
docker --version
docker-compose --version
```

**For Production:**
```bash
# Kubernetes cluster
kubectl version --client

# Helm (optional, for charts)
helm version
```

### API Keys and Credentials

You'll need API credentials for exchanges:

**Binance (required):**
- API Key
- API Secret
- Testnet credentials for paper trading

**Optional Exchanges:**
- Bybit API Key/Secret
- OANDA API Key/Secret

### Infrastructure Requirements

**Database:**
- PostgreSQL 13+ (production)
- Redis 6+ (caching and session storage)

**Message Queue (production):**
- Apache Kafka 2.8+ (for high-throughput data streaming)

**Monitoring:**
- Prometheus (metrics collection)
- Grafana (visualization)

## Environment Setup

### 1. Repository Clone and Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-org/smc-trading-agent.git
cd smc-trading-agent

# Create environment configuration
cp .env.example .env
```

### 2. Environment Variables Configuration

Edit `.env` file with your configuration:

```bash
# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret

# Trading Configuration
TRADING_MODE=paper  # paper or live
INITIAL_BALANCE=10000
MAX_DAILY_LOSS=500

# Database Configuration
DATABASE_URL=postgresql://smc_user:password@localhost:5432/smc_trading
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET=your_jwt_secret_key_here
API_KEY_REQUIRED=true

# Performance
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### 3. Python Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Rust execution engine
cd src/execution_engine
cargo build --release
```

### 4. Frontend Setup (Optional)

```bash
# Install Node.js dependencies
cd frontend
npm install

# Build for production
npm run build
```

## Installation Methods

### Method 1: Docker Compose (Recommended for Development)

**Advantages:**
- Complete stack with all dependencies
- Easy to start and stop
- Persistent data volumes
- Development and production configurations

**Steps:**
```bash
# Copy production environment file
cp .env.example .env.production

# Edit with your production values
nano .env.production

# Start the complete stack
docker-compose -f docker-compose.optimized.yml --env-file .env.production up -d

# Check container status
docker-compose ps

# View logs
docker-compose logs -f smc-agent
```

### Method 2: Kubernetes (Recommended for Production)

**Advantages:**
- Scalability and high availability
- Automatic rollouts and rollbacks
- Resource management and isolation
- Production-grade networking and storage

**Steps:**
```bash
# Create namespace
kubectl apply -f deployment/kubernetes/namespace.yaml

# Create secrets (from your .env file)
kubectl apply -f deployment/kubernetes/secrets.yaml

# Create configmaps
kubectl apply -f deployment/kubernetes/configmap.yaml

# Deploy database and cache
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml
kubectl apply -f deployment/kubernetes/redis-deployment.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n smc-trading --timeout=300s

# Deploy main application
kubectl apply -f deployment/kubernetes/smc-agent-deployment.yaml

# Check deployment status
kubectl get pods -n smc-trading
kubectl logs -f deployment/smc-agent -n smc-trading
```

### Method 3: Native Installation (Advanced)

**Advantages:**
- Maximum performance
- Full control over the environment
- Custom optimizations

**Steps:**
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3.11-dev python3-pip postgresql-13 redis-server

# Set up database
sudo -u postgres createdb smc_trading
sudo -u postgres createuser smc_user
sudo -u postgres psql -c "ALTER USER smc_user PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE smc_trading TO smc_user;"

# Run database migrations
python -m alembic upgrade head

# Start services
redis-server &
python main.py &
```

## Docker Deployment

### Development Docker Compose

For development and testing with all services:

```bash
# Start development environment
docker-compose up -d

# View running services
docker-compose ps

# Access services
# Frontend: http://localhost:3000
# API: http://localhost:8000
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
```

### Production Docker Compose

For production deployment:

```bash
# Create production environment
cp .env.example .env.production
# Edit .env.production with production values

# Start production stack
docker-compose -f docker-compose.optimized.yml --env-file .env.production up -d

# Scale services if needed
docker-compose -f docker-compose.optimized.yml up -d --scale smc-agent=2
```

### Docker Build and Run

Build custom Docker image:

```bash
# Build optimized image
docker build -f Dockerfile.optimized -t smc-trading-agent:latest .

# Run with environment variables
docker run -d \
  --name smc-agent \
  -p 8000:8000 \
  -p 8008:8008 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e BINANCE_API_KEY="$BINANCE_API_KEY" \
  -e BINANCE_API_SECRET="$BINANCE_API_SECRET" \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  smc-trading-agent:latest
```

## Kubernetes Deployment

### 1. Namespace and RBAC Setup

```yaml
# deployment/kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: smc-trading
  labels:
    name: smc-trading
```

### 2. Secrets Management

Create secrets from environment variables:

```bash
# Create secrets from .env file
kubectl create secret generic smc-secrets \
  --from-env-file=.env \
  --namespace=smc-trading
```

Or use the provided secrets manifest:

```bash
kubectl apply -f deployment/kubernetes/secrets.yaml
```

### 3. Configuration Management

ConfigMaps for application configuration:

```bash
kubectl apply -f deployment/kubernetes/configmap.yaml
```

### 4. Database Deployment

Deploy PostgreSQL with TimescaleDB for time-series data:

```bash
kubectl apply -f deployment/kubernetes/postgres-deployment.yaml
```

### 5. Application Deployment

Deploy the main SMC trading agent:

```bash
kubectl apply -f deployment/kubernetes/smc-agent-deployment.yaml
```

### 6. Service and Ingress Setup

```yaml
# deployment/kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: smc-agent-ingress
  namespace: smc-trading
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: smc-trading.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: smc-agent-service
            port:
              number: 8000
```

### 7. Horizontal Pod Autoscaler

```yaml
# deployment/kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: smc-agent-hpa
  namespace: smc-trading
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: smc-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Configuration Management

### Configuration Hierarchy

1. **Environment variables** (highest priority)
2. **CLI arguments**
3. **Configuration file** (config.yaml)
4. **Default values** (lowest priority)

### Main Configuration File

The main configuration is in `config.yaml`:

```yaml
# Application settings
app:
  name: "SMC Trading Agent"
  version: "1.0.0"
  environment: "production"
  mode: "paper"  # paper or live
  log_level: "INFO"

# Exchange configuration
exchanges:
  binance:
    enabled: true
    api_key: "${BINANCE_API_KEY}"  # Environment variable substitution
    api_secret: "${BINANCE_API_SECRET}"
    symbols:
      - "BTCUSDT"
      - "ETHUSDT"

# Risk management
risk_manager:
  max_position_size: 1000
  max_daily_loss: 500
  stop_loss_percent: 2.0

# ... more configuration
```

### Environment-Specific Configurations

**Development:** `config.dev.yaml`
**Staging:** `config.staging.yaml`
**Production:** `config.prod.yaml`

Load with environment variable:
```bash
export CONFIG_ENV=prod
python main.py
```

### Dynamic Configuration Updates

The application supports hot reloading of certain configurations:

```python
# Update configuration via API
curl -X POST http://localhost:8000/api/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"risk_manager.max_position_size": 1500}'
```

## Database Setup

### PostgreSQL Setup

**Installation:**
```bash
# Ubuntu/Debian
sudo apt install postgresql-13 postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql13-server postgresql13-contrib
sudo postgresql-setup initdb
```

**Database Creation:**
```bash
# Create database and user
sudo -u postgres createdb smc_trading
sudo -u postgres createuser smc_user
sudo -u postgres psql -c "ALTER USER smc_user PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE smc_trading TO smc_user;"
```

**TimescaleDB Extension (production):**
```sql
-- Connect to your database
\c smc_trading

-- Install TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

**Database Migrations:**
```bash
# Run all migrations
python -m alembic upgrade head

# Create new migration
python -m alembic revision --autogenerate -m "Add new feature"

# Downgrade to specific version
python -m alembic downgrade -1
```

### Redis Setup

**Installation:**
```bash
# Ubuntu/Debian
sudo apt install redis-server

# CentOS/RHEL
sudo yum install redis
```

**Configuration:**
```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Key settings
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

**Start Redis:**
```bash
sudo systemctl start redis
sudo systemctl enable redis

# Test connection
redis-cli ping
```

### Database Backup and Recovery

**Automated Backups:**
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/postgres"

# Create backup
pg_dump -h localhost -U smc_user smc_trading > $BACKUP_DIR/smc_trading_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/smc_trading_$DATE.sql

# Remove old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

**Restore from Backup:**
```bash
# Decompress backup
gunzip smc_trading_20241201_120000.sql.gz

# Restore database
psql -h localhost -U smc_user -d smc_trading < smc_trading_20241201_120000.sql
```

## Security Configuration

### API Security

**JWT Configuration:**
```bash
# Generate secure JWT secret
openssl rand -base64 64

# Set in environment
export JWT_SECRET="your_secure_jwt_secret_here"
export JWT_EXPIRATION="3600"  # 1 hour
```

**API Rate Limiting:**
```yaml
api:
  rate_limit:
    requests_per_minute: 100
    burst_size: 20
```

### SSL/TLS Configuration

**Nginx SSL Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name smc-trading.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://smc-agent:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Kubernetes TLS Secrets:**
```bash
# Create TLS secret
kubectl create secret tls smc-tls-secret \
  --namespace=smc-trading \
  --key=path/to/tls.key \
  --cert=path/to/tls.crt
```

### Firewall Configuration

```bash
# Ubuntu UFW
sudo ufw enable
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 5432/tcp     # PostgreSQL (internal only)
sudo ufw deny 6379/tcp     # Redis (internal only)
```

### Security Hardening Checklist

- [ ] Use strong, unique API keys for exchanges
- [ ] Enable two-factor authentication on exchange accounts
- [ ] Use environment variables for sensitive configuration
- [ ] Enable SSL/TLS for all communications
- [ ] Regularly update dependencies
- [ ] Implement proper access controls
- [ ] Use read-only database credentials for monitoring
- [ ] Regular security audits and penetration testing

## Monitoring and Logging

### Prometheus Metrics

**Key Metrics:**
- System performance (CPU, memory, network)
- Trading performance (P&L, win rate, trades per hour)
- Application health (response times, error rates)
- Exchange connectivity (latency, success rate)

**Metrics Configuration:**
```yaml
monitoring:
  prometheus:
    enabled: true
    port: 9090
    scrape_interval: 15s
    metrics_retention: 200h
```

### Grafana Dashboards

Pre-built dashboards include:

- **System Overview**: CPU, memory, network, disk usage
- **Trading Performance**: P&L, trades, win rate, drawdown
- **Risk Management**: Position sizes, stop losses, exposure
- **Application Health**: Response times, error rates, uptime

**Access Grafana:**
- URL: `http://your-domain:3000`
- Default credentials: `admin/admin` (change on first login)

### Structured Logging

**Log Configuration:**
```yaml
logging:
  level: INFO
  format: json
  output:
    - stdout
    - file:/app/logs/smc-agent.log
  rotation:
    max_size: 100MB
    max_files: 10
```

**Log Levels:**
- `DEBUG`: Detailed debugging information
- `INFO`: General information messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical system failures

### Health Checks

**Application Health Endpoint:**
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "exchanges": {
      "binance": "healthy"
    },
    "execution_engine": "healthy"
  }
}
```

## Performance Tuning

### System Optimization

**Linux Kernel Parameters:**
```bash
# Add to /etc/sysctl.conf
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 65536 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000

# Apply changes
sudo sysctl -p
```

**Python Optimization:**
```bash
# Environment variables for maximum performance
export PYTHONUNBUFFERED=1
export PYTHONOPTIMIZE=2
export UVLOOP_ENABLED=1
```

### Database Performance

**PostgreSQL Tuning:**
```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

**Redis Optimization:**
```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Application Performance

**Async Configuration:**
```yaml
performance:
  max_concurrent_requests: 1000
  connection_pool_size: 100
  request_timeout: 30
  retry_attempts: 3
```

**Memory Management:**
```yaml
memory:
  max_heap_size: 2GB
  gc_threshold: 0.8
  enable_memory_profiling: false
```

## Validation and Testing

### Pre-deployment Checklist

**System Validation:**
- [ ] All required ports are open and accessible
- [ ] Database connectivity is working
- [ ] Redis connection is established
- [ ] Exchange API keys are valid and have required permissions
- [ ] SSL certificates are valid and properly configured
- [ ] Monitoring endpoints are accessible

**Application Validation:**
- [ ] Configuration file is valid
- [ ] Database migrations are applied
- [ ] All microservices start successfully
- [ ] Health checks are passing
- [ ] API endpoints are responding correctly

### Integration Testing

**Health Check Script:**
```bash
#!/bin/bash
# health_check.sh

API_URL="http://localhost:8000"
MAX_RETRIES=30
RETRY_INTERVAL=5

echo "Performing health checks..."

# Check API endpoint
for i in $(seq 1 $MAX_RETRIES); do
    if curl -f "$API_URL/health" > /dev/null 2>&1; then
        echo "✓ API health check passed"
        break
    else
        echo "API health check failed (attempt $i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    fi
done

# Check database connectivity
python -c "
import psycopg2
try:
    conn = psycopg2.connect('$DATABASE_URL')
    conn.close()
    print('✓ Database connectivity check passed')
except Exception as e:
    print(f'✗ Database check failed: {e}')
    exit(1)
"

# Check Redis connectivity
python -c "
import redis
try:
    r = redis.from_url('$REDIS_URL')
    r.ping()
    print('✓ Redis connectivity check passed')
except Exception as e:
    print(f'✗ Redis check failed: {e}')
    exit(1)
"

echo "Health checks completed"
```

### Load Testing

**API Load Test:**
```python
# load_test.py
import asyncio
import aiohttp
import time

async def load_test():
    url = "http://localhost:8000/api/trades"
    concurrent_requests = 100
    total_requests = 1000

    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(concurrent_requests):
            task = asyncio.create_task(send_request(session, url))
            tasks.append(task)

        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()

        duration = end_time - start_time
        rps = total_requests / duration
        print(f"Requests per second: {rps:.2f}")

async def send_request(session, url):
    try:
        async with session.get(url) as response:
            await response.text()
            return response.status == 200
    except:
        return False

if __name__ == "__main__":
    asyncio.run(load_test())
```

## Troubleshooting

### Common Issues and Solutions

**1. Application Won't Start**

**Symptoms:**
- Container exits immediately
- Health checks failing
- Application logs show errors

**Solutions:**
```bash
# Check container logs
docker logs smc-agent

# Check configuration
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Verify environment variables
printenv | grep -E "(DATABASE|REDIS|API)"
```

**2. Database Connection Issues**

**Symptoms:**
- Connection timeout errors
- Authentication failures

**Solutions:**
```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check database status
sudo systemctl status postgresql

# Verify network connectivity
nc -zv localhost 5432
```

**3. Exchange API Errors**

**Symptoms:**
- API rate limit exceeded
- Invalid API credentials
- Permission denied errors

**Solutions:**
```bash
# Test API credentials
python -c "
import ccxt
exchange = ccxt.binance({
    'apiKey': '$BINANCE_API_KEY',
    'secret': '$BINANCE_API_SECRET',
    'sandbox': True
})
print(exchange.fetch_balance())
"

# Check API permissions on exchange dashboard
# Verify IP whitelist includes your server IP
```

**4. High Memory Usage**

**Symptoms:**
- Container getting OOMKilled
- System swapping

**Solutions:**
```bash
# Monitor memory usage
docker stats smc-agent

# Check for memory leaks
python -m memory_profiler main.py

# Adjust memory limits
docker update --memory=4g smc-agent
```

**5. Performance Issues**

**Symptoms:**
- Slow API response times
- High latency on trade execution

**Solutions:**
```bash
# Profile application performance
python -m cProfile -o profile.stats main.py

# Check system resources
htop
iotop

# Optimize database queries
EXPLAIN ANALYZE SELECT * FROM trades WHERE symbol='BTCUSDT';
```

### Emergency Procedures

**1. Emergency Stop**

```bash
# Stop trading immediately
curl -X POST http://localhost:8000/api/emergency/stop \
  -H "Authorization: Bearer $TOKEN"

# Or shutdown all services
docker-compose down
```

**2. Database Recovery**

```bash
# Stop application
docker-compose stop smc-agent

# Restore from backup
psql -h localhost -U smc_user -d smc_trading < backup.sql

# Start application
docker-compose start smc-agent
```

**3. Service Restart**

```bash
# Graceful restart
curl -X POST http://localhost:8000/api/admin/restart \
  -H "Authorization: Bearer $TOKEN"

# Force restart
docker-compose restart smc-agent
```

### Support and Maintenance

**Log Analysis:**
```bash
# Search for errors in logs
grep -i "error\|exception\|failed" /app/logs/*.log

# Monitor real-time logs
tail -f /app/logs/smc-agent.log | grep ERROR
```

**Performance Monitoring:**
```bash
# Check system metrics
top
iostat -x 1

# Application-specific metrics
curl http://localhost:8000/metrics
```

**Regular Maintenance Tasks:**
- Review logs daily
- Monitor system resources
- Check API rate limits
- Update dependencies regularly
- Test backup/restore procedures
- Verify security configurations

---

## Support

For additional support:

1. **Documentation**: Check this guide and inline code documentation
2. **Logs**: Review application logs for detailed error messages
3. **Health Checks**: Use `/health` endpoint for status information
4. **Community**: Join our Discord/Slack community for peer support
5. **Issues**: Report bugs and request features via GitHub issues

Remember to never share API keys, secrets, or sensitive configuration information in public forums or issue trackers.