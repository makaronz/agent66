# SMC Trading Agent Deployment

This directory contains all deployment configurations and automation scripts for the SMC Trading Agent.

## Overview

The SMC Trading Agent supports multiple deployment methods:

- **Docker Compose**: For local development and testing
- **Kubernetes**: For production deployments with high availability
- **Helm Charts**: For templated Kubernetes deployments with environment-specific configurations

## Directory Structure

```
deployment/
├── docker/                     # Docker configurations
│   ├── Dockerfile             # Production Docker image
│   ├── Dockerfile.dev         # Development Docker image
│   └── docker-compose.yml     # Local development stack
├── kubernetes/                # Raw Kubernetes manifests
│   └── production/            # Production-ready manifests
│       └── smc-agent-production.yaml
├── helm/                      # Helm chart for templated deployments
│   ├── smc-trading-agent/     # Main Helm chart
│   │   ├── Chart.yaml         # Chart metadata
│   │   ├── values.yaml        # Default values
│   │   ├── values-production.yaml   # Production overrides
│   │   ├── values-development.yaml  # Development overrides
│   │   ├── templates/         # Kubernetes templates
│   │   └── README.md          # Chart documentation
│   └── install.sh             # Helm installation script
├── Makefile                   # Deployment automation
└── README.md                  # This file
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Kubernetes cluster (for K8s deployments)
- kubectl configured
- Helm 3.x (for Helm deployments)

### Local Development with Docker Compose

```bash
# Start all services
cd deployment/docker
docker-compose up -d

# View logs
docker-compose logs -f smc-agent

# Stop services
docker-compose down
```

### Kubernetes Deployment

#### Option 1: Using Raw Manifests

```bash
# Apply production manifests
kubectl apply -f kubernetes/production/

# Check deployment status
kubectl get pods -n smc-trading-prod
```

#### Option 2: Using Helm (Recommended)

```bash
# Development environment
cd deployment
make deploy-dev

# Production environment
make deploy-prod

# Check status
make status-all
```

## Deployment Methods

### 1. Docker Compose (Development)

**Use Case**: Local development, testing, and prototyping

**Features**:
- Single-command setup
- Includes PostgreSQL and Redis
- Hot-reload support
- Debug-friendly configuration

**Commands**:
```bash
cd deployment/docker
docker-compose up -d          # Start services
docker-compose logs -f         # View logs
docker-compose down            # Stop services
docker-compose pull            # Update images
```

### 2. Raw Kubernetes Manifests

**Use Case**: Simple production deployments, CI/CD pipelines

**Features**:
- Production-ready configuration
- Multi-zone deployment
- Vault integration
- Network policies
- Resource limits and requests

**Commands**:
```bash
# Deploy
kubectl apply -f kubernetes/production/

# Monitor
kubectl get pods -n smc-trading-prod -w

# Cleanup
kubectl delete -f kubernetes/production/
```

### 3. Helm Charts (Recommended)

**Use Case**: Multi-environment deployments, configuration management

**Features**:
- Environment-specific configurations
- Templated manifests
- Dependency management
- Easy upgrades and rollbacks
- Values validation

**Commands**:
```bash
# Install development
./helm/install.sh install -e development

# Install production
./helm/install.sh install -e production

# Upgrade
./helm/install.sh upgrade -e production

# Rollback
./helm/install.sh rollback
```

## Environment Configurations

### Development Environment

- **Namespace**: `smc-trading-dev`
- **Replicas**: 1
- **Resources**: Minimal (512Mi RAM, 250m CPU)
- **Storage**: 10Gi data, 5Gi logs
- **Dependencies**: Included (PostgreSQL, Redis)
- **Security**: Relaxed for debugging
- **Monitoring**: Basic Prometheus scraping

### Staging Environment

- **Namespace**: `smc-trading-staging`
- **Replicas**: 2
- **Resources**: Medium (2Gi RAM, 1000m CPU)
- **Storage**: 100Gi data, 50Gi logs
- **Dependencies**: External managed services
- **Security**: Production-like
- **Monitoring**: Full observability stack

### Production Environment

- **Namespace**: `smc-trading-prod`
- **Replicas**: 5 (auto-scaling 5-25)
- **Resources**: High (8Gi RAM, 4000m CPU)
- **Storage**: 500Gi data, 200Gi logs
- **Dependencies**: External managed services
- **Security**: Strict network policies, Vault integration
- **Monitoring**: Full observability with alerting

## Configuration Management

### Environment Variables

Key environment variables for configuration:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
RUST_LOG=info

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_MAX_CONNECTIONS=100

# Redis
REDIS_URL=redis://host:6379

# Exchange APIs (from Vault)
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
OANDA_API_KEY=...
OANDA_ACCOUNT_ID=...

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:14268
OTEL_SERVICE_NAME=smc-trading-agent
```

### Secrets Management

#### Development
- Kubernetes Secrets
- ConfigMaps for non-sensitive data

#### Production
- HashiCorp Vault integration
- Vault Agent for secret injection
- Automatic secret rotation

### Vault Configuration

```yaml
vault:
  enabled: true
  address: "https://vault.yourdomain.com"
  role: "smc-trading-prod-role"
  secrets:
    database:
      path: "secret/data/smc-trading/prod/database"
    exchanges:
      path: "secret/data/smc-trading/prod/exchanges"
```

## Monitoring and Observability

### Metrics

- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Custom metrics**: Trading performance, API latency, error rates

### Logging

- **Structured logging**: JSON format
- **Log aggregation**: ELK stack or similar
- **Log levels**: DEBUG (dev), INFO (prod)

### Tracing

- **OpenTelemetry**: Distributed tracing
- **Jaeger**: Trace visualization
- **Sampling**: 100% (dev), 10% (prod)

### Health Checks

- **Liveness**: `/health` endpoint
- **Readiness**: `/ready` endpoint
- **Startup**: Extended timeout for initialization

## Security

### Network Security

- **Network Policies**: Restrict pod-to-pod communication
- **Ingress**: TLS termination, rate limiting
- **Service Mesh**: Optional Istio integration

### Pod Security

- **Security Context**: Non-root user, read-only filesystem
- **Pod Security Standards**: Restricted profile
- **Resource Limits**: CPU, memory, ephemeral storage

### Secrets

- **Vault Integration**: Production secret management
- **Secret Rotation**: Automated credential updates
- **Least Privilege**: Minimal required permissions

## Scaling and Performance

### Horizontal Pod Autoscaler (HPA)

```yaml
autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 25
  targetCPUUtilizationPercentage: 50
  targetMemoryUtilizationPercentage: 60
```

### Vertical Pod Autoscaler (VPA)

- **Recommendation Mode**: Analyze resource usage
- **Auto Mode**: Automatic resource adjustment
- **Initial Resources**: Conservative starting point

### Pod Disruption Budget (PDB)

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 3  # Always keep 3 pods running
```

## Disaster Recovery

### Backup Strategy

- **Database**: Automated daily backups
- **Persistent Volumes**: Snapshot-based backups
- **Configuration**: GitOps with version control

### Multi-Zone Deployment

- **Pod Anti-Affinity**: Spread pods across zones
- **Persistent Volumes**: Zone-aware storage
- **Load Balancing**: Cross-zone traffic distribution

### Rollback Procedures

```bash
# Helm rollback
helm rollback smc-agent --namespace smc-trading-prod

# Or using Makefile
make rollback-prod
```

## Troubleshooting

### Common Issues

#### Pod Startup Issues

```bash
# Check pod status
kubectl get pods -n smc-trading-prod

# Describe pod for events
kubectl describe pod <pod-name> -n smc-trading-prod

# Check logs
kubectl logs <pod-name> -n smc-trading-prod
```

#### Vault Connection Issues

```bash
# Check Vault agent logs
kubectl logs <pod-name> -c vault-agent -n smc-trading-prod

# Verify Vault role
vault read auth/kubernetes/role/smc-trading-prod-role
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it <pod-name> -n smc-trading-prod -- psql $DATABASE_URL

# Check database secrets
kubectl get secret smc-trading-db-secret -n smc-trading-prod -o yaml
```

### Debug Commands

```bash
# Port forward for local access
kubectl port-forward svc/smc-trading-agent 8080:80 -n smc-trading-prod

# Execute shell in pod
kubectl exec -it <pod-name> -n smc-trading-prod -- /bin/bash

# Check resource usage
kubectl top pods -n smc-trading-prod
```

### Performance Debugging

```bash
# Check HPA status
kubectl get hpa -n smc-trading-prod

# View metrics
kubectl get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/smc-trading-prod/pods"

# Analyze resource requests vs limits
kubectl describe pod <pod-name> -n smc-trading-prod | grep -A 10 "Requests:"
```

## Makefile Commands

The included Makefile provides automation for common deployment tasks:

### Build and Push
```bash
make build          # Build Docker image
make push           # Build and push to registry
make build-dev      # Build development image
```

### Deploy
```bash
make deploy-dev     # Deploy to development
make deploy-staging # Deploy to staging
make deploy-prod    # Deploy to production
```

### Manage
```bash
make status-all     # Show all environment status
make logs-prod      # Show production logs
make rollback-prod  # Rollback production
```

### Validate
```bash
make validate       # Validate all configurations
make lint          # Lint configurations
make test-prod     # Run production tests
```

### Cleanup
```bash
make clean         # Clean local Docker images
make clean-all     # Clean everything
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy SMC Trading Agent

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and Push
        run: |
          cd deployment
          make ci-build
          make ci-push
      
      - name: Deploy to Staging
        run: |
          cd deployment
          make ci-deploy-staging
      
      - name: Deploy to Production
        if: github.ref == 'refs/heads/main'
        run: |
          cd deployment
          make ci-deploy-prod
```

### GitLab CI Example

```yaml
stages:
  - build
  - deploy-staging
  - deploy-production

build:
  stage: build
  script:
    - cd deployment
    - make ci-build
    - make ci-push

deploy-staging:
  stage: deploy-staging
  script:
    - cd deployment
    - make ci-deploy-staging
  environment:
    name: staging

deploy-production:
  stage: deploy-production
  script:
    - cd deployment
    - make ci-deploy-prod
  environment:
    name: production
  when: manual
  only:
    - main
```

## Best Practices

### Security

1. **Never commit secrets** to version control
2. **Use Vault** for production secret management
3. **Enable network policies** to restrict traffic
4. **Run as non-root** user in containers
5. **Use read-only filesystems** where possible

### Performance

1. **Set appropriate resource requests and limits**
2. **Use HPA** for automatic scaling
3. **Monitor key metrics** (CPU, memory, trading latency)
4. **Optimize container startup time**
5. **Use persistent volumes** for data that needs to survive pod restarts

### Reliability

1. **Deploy across multiple zones**
2. **Use pod disruption budgets**
3. **Implement proper health checks**
4. **Plan for graceful shutdowns**
5. **Test disaster recovery procedures**

### Operations

1. **Use GitOps** for configuration management
2. **Automate deployments** with CI/CD
3. **Monitor deployment health**
4. **Plan rollback procedures**
5. **Document operational procedures**

## Support

For deployment issues:

1. Check the troubleshooting section above
2. Review pod logs and events
3. Verify configuration values
4. Test connectivity to external services
5. Consult the application documentation

## Contributing

When contributing deployment configurations:

1. Test changes in development environment first
2. Update documentation for any new features
3. Follow security best practices
4. Validate configurations before submitting
5. Include appropriate resource limits

## License

This deployment configuration is part of the SMC Trading Agent project and follows the same license terms.