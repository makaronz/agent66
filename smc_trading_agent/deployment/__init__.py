"""
Deployment Module - Infrastructure and Deployment Configuration

Contains comprehensive deployment configurations and infrastructure setup for the SMC Trading Agent.
Includes Docker configurations, Kubernetes manifests, deployment scripts, and infrastructure automation.

Key Features:
- Docker containerization and image management
- Kubernetes deployment manifests and configurations
- Infrastructure as Code (IaC) automation
- Environment-specific deployment configurations
- CI/CD pipeline integration and automation
- Monitoring and logging infrastructure setup
- Scalability and high-availability configurations

Deployment Options:
- Docker Compose for local development and testing
- Kubernetes for production deployment and scaling
- Cloud-native deployment patterns and best practices
- Multi-environment deployment strategies

Usage:
    # Docker deployment
    docker-compose -f deployment/docker-compose.yml up
    
    # Kubernetes deployment
    kubectl apply -f deployment/kubernetes/
"""

__version__ = "1.0.0"
__description__ = "Deployment configurations and infrastructure setup"
__keywords__ = ["deployment", "docker", "kubernetes", "infrastructure", "ci-cd"]

# Package-level exports
__all__ = [
    '__version__',
    '__description__'
]

# Note: This module contains deployment configurations and infrastructure files
# No Python code implementation - configuration files only
