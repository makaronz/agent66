# SMC Trading Agent Helm Chart

This Helm chart deploys the SMC Trading Agent on a Kubernetes cluster using the Helm package manager.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure
- HashiCorp Vault (if vault integration is enabled)
- Prometheus Operator (if monitoring is enabled)

## Installing the Chart

To install the chart with the release name `smc-trading-agent`:

```bash
helm install smc-trading-agent ./smc-trading-agent
```

To install with custom values:

```bash
helm install smc-trading-agent ./smc-trading-agent -f values-production.yaml
```

## Uninstalling the Chart

To uninstall/delete the `smc-trading-agent` deployment:

```bash
helm delete smc-trading-agent
```

## Configuration

The following table lists the configurable parameters of the SMC Trading Agent chart and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `""` |
| `global.imagePullSecrets` | Global Docker registry secret names as an array | `[]` |
| `global.storageClass` | Global StorageClass for Persistent Volume(s) | `""` |

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.registry` | SMC Trading Agent image registry | `docker.io` |
| `image.repository` | SMC Trading Agent image repository | `smc-agent` |
| `image.tag` | SMC Trading Agent image tag | `v1.0.0` |
| `image.pullPolicy` | SMC Trading Agent image pull policy | `Always` |
| `image.pullSecrets` | SMC Trading Agent image pull secrets | `[]` |

### Deployment Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of SMC Trading Agent replicas | `3` |
| `strategy.type` | Deployment strategy type | `RollingUpdate` |
| `strategy.rollingUpdate.maxSurge` | Maximum number of pods that can be created above the desired number | `1` |
| `strategy.rollingUpdate.maxUnavailable` | Maximum number of pods that can be unavailable | `0` |

### Resource Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.requests.memory` | Memory request | `2Gi` |
| `resources.requests.cpu` | CPU request | `1000m` |
| `resources.requests.ephemeralStorage` | Ephemeral storage request | `1Gi` |
| `resources.limits.memory` | Memory limit | `4Gi` |
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.ephemeralStorage` | Ephemeral storage limit | `2Gi` |

### Autoscaling Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `autoscaling.enabled` | Enable Horizontal Pod Autoscaler | `true` |
| `autoscaling.minReplicas` | Minimum number of replicas | `3` |
| `autoscaling.maxReplicas` | Maximum number of replicas | `15` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization percentage | `60` |
| `autoscaling.targetMemoryUtilizationPercentage` | Target memory utilization percentage | `70` |

### Service Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `service.type` | Kubernetes Service type | `ClusterIP` |
| `service.ports.http.port` | HTTP service port | `80` |
| `service.ports.http.targetPort` | HTTP container port | `8080` |
| `service.ports.metrics.port` | Metrics service port | `9090` |
| `service.ports.metrics.targetPort` | Metrics container port | `9090` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress record generation | `false` |
| `ingress.className` | IngressClass that will be used | `nginx` |
| `ingress.annotations` | Additional annotations for the Ingress resource | `{}` |
| `ingress.hosts` | An array with hosts and paths | See values.yaml |
| `ingress.tls` | TLS configuration for additional hostnames | `[]` |

### Persistence Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.data.enabled` | Enable persistence for data | `true` |
| `persistence.data.storageClass` | StorageClass for data volume | `fast-ssd` |
| `persistence.data.accessMode` | Access mode for data volume | `ReadWriteOnce` |
| `persistence.data.size` | Size of data volume | `50Gi` |
| `persistence.logs.enabled` | Enable persistence for logs | `true` |
| `persistence.logs.storageClass` | StorageClass for logs volume | `standard` |
| `persistence.logs.size` | Size of logs volume | `20Gi` |

### Vault Integration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `vault.enabled` | Enable Vault integration | `true` |
| `vault.address` | Vault server address | `http://vault.vault.svc.cluster.local:8200` |
| `vault.role` | Vault role for authentication | `smc-trading-role` |

### Security Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `securityContext.runAsNonRoot` | Run as non-root user | `true` |
| `securityContext.runAsUser` | User ID to run the container | `1000` |
| `securityContext.runAsGroup` | Group ID to run the container | `1000` |
| `securityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
| `securityContext.readOnlyRootFilesystem` | Mount root filesystem as read-only | `true` |

### Network Policy Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `networkPolicy.enabled` | Enable network policy | `true` |
| `networkPolicy.policyTypes` | Policy types | `["Ingress", "Egress"]` |

### Monitoring Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.prometheus.enabled` | Enable Prometheus monitoring | `true` |
| `monitoring.prometheus.scrape` | Enable Prometheus scraping | `true` |
| `monitoring.grafana.enabled` | Enable Grafana dashboards | `true` |

## Examples

### Production Deployment

```yaml
# values-production.yaml
replicaCount: 5

resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
  targetCPUUtilizationPercentage: 50
  targetMemoryUtilizationPercentage: 60

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: smc-trading.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: smc-trading-tls
      hosts:
        - smc-trading.yourdomain.com

persistence:
  data:
    size: 200Gi
    storageClass: "fast-ssd"
  logs:
    size: 100Gi
    storageClass: "standard"

vault:
  enabled: true
  address: "https://vault.yourdomain.com"

monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: true
```

### Development Deployment

```yaml
# values-development.yaml
replicaCount: 1

resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

autoscaling:
  enabled: false

persistence:
  data:
    size: 10Gi
  logs:
    size: 5Gi

vault:
  enabled: false

networkPolicy:
  enabled: false
```

## Upgrading

To upgrade the chart:

```bash
helm upgrade smc-trading-agent ./smc-trading-agent -f values-production.yaml
```

## Troubleshooting

### Common Issues

1. **Pods not starting**: Check if Vault is accessible and secrets are properly configured
2. **Storage issues**: Verify that the specified StorageClass exists and has available capacity
3. **Network connectivity**: Ensure network policies allow required traffic
4. **Resource constraints**: Check if the cluster has sufficient CPU and memory resources

### Debugging Commands

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=smc-trading-agent

# View pod logs
kubectl logs -l app.kubernetes.io/name=smc-trading-agent -f

# Describe pod for events
kubectl describe pod <pod-name>

# Check HPA status
kubectl get hpa

# Check PVC status
kubectl get pvc

# Check network policies
kubectl get networkpolicy
```

## Security Considerations

- Always use non-root containers in production
- Enable network policies to restrict traffic
- Use Vault or similar secret management solutions
- Regularly update container images
- Monitor for security vulnerabilities
- Use TLS for all external communications

## Contributing

Please read the contributing guidelines before submitting pull requests.

## License

This chart is licensed under the MIT License.