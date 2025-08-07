"""
Kubernetes Deployment Module - Cloud-Native Deployment Configuration

Contains comprehensive Kubernetes manifests and deployment configurations for the SMC Trading Agent.
Includes deployment YAML files, service configurations, resource definitions, and cloud-native patterns.

Key Features:
- Kubernetes deployment manifests for all components
- Service configurations and load balancing
- Resource management and scaling policies
- ConfigMap and Secret management
- Persistent volume configurations
- Ingress and network policy definitions
- Monitoring and logging integration
- Horizontal Pod Autoscaling (HPA) configurations

Deployment Components:
- SMC Trading Agent main application deployment
- Data pipeline service deployment
- Monitoring and observability stack
- Database and storage configurations
- Network policies and security configurations

Usage:
    # Deploy to Kubernetes cluster
    kubectl apply -f smc_trading_agent/deployment/kubernetes/
    
    # Deploy specific component
    kubectl apply -f smc_trading_agent/deployment/kubernetes/smc-agent-deployment.yaml
    
    # Check deployment status
    kubectl get pods -n smc-trading
"""

__version__ = "1.0.0"
__description__ = "Kubernetes deployment configurations and manifests"
__keywords__ = ["kubernetes", "deployment", "cloud-native", "container-orchestration", "microservices"]

# Package-level exports
__all__ = [
    '__version__',
    '__description__'
]

# Note: This module contains Kubernetes manifests and deployment configurations
# No Python code implementation - YAML configuration files only
