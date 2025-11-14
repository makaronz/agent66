#!/bin/bash

# SMC Trading Agent - Kubernetes Cluster Setup Script
# This script sets up a production-ready Kubernetes cluster with all necessary components

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="${CLUSTER_NAME:-smc-trading-cluster}"
REGION="${REGION:-us-west-2}"
NODE_COUNT="${NODE_COUNT:-3}"
NODE_TYPE="${NODE_TYPE:-t3.medium}"
KUBERNETES_VERSION="${KUBERNETES_VERSION:-1.28}"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed. Please install kubectl first."
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        error "helm is not installed. Please install helm first."
    fi
    
    # Check cloud provider CLI
    if command -v aws &> /dev/null; then
        CLOUD_PROVIDER="aws"
        if ! command -v eksctl &> /dev/null; then
            error "eksctl is not installed. Please install eksctl for AWS EKS."
        fi
    elif command -v gcloud &> /dev/null; then
        CLOUD_PROVIDER="gcp"
    elif command -v az &> /dev/null; then
        CLOUD_PROVIDER="azure"
    else
        error "No supported cloud provider CLI found (aws, gcloud, or az)"
    fi
    
    log "Prerequisites check passed. Using ${CLOUD_PROVIDER} as cloud provider."
}

# Create Kubernetes cluster
create_cluster() {
    log "Creating Kubernetes cluster: ${CLUSTER_NAME}"
    
    case $CLOUD_PROVIDER in
        "aws")
            create_eks_cluster
            ;;
        "gcp")
            create_gke_cluster
            ;;
        "azure")
            create_aks_cluster
            ;;
        *)
            error "Unsupported cloud provider: ${CLOUD_PROVIDER}"
            ;;
    esac
}

create_eks_cluster() {
    log "Creating EKS cluster..."
    
    # Create cluster configuration
    cat > cluster-config.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: ${CLUSTER_NAME}
  region: ${REGION}
  version: "${KUBERNETES_VERSION}"

# Enable logging
cloudWatch:
  clusterLogging:
    enableTypes: ["*"]

# VPC configuration for multi-AZ
vpc:
  enableDnsHostnames: true
  enableDnsSupport: true

# Node groups
nodeGroups:
  - name: smc-trading-nodes
    instanceType: ${NODE_TYPE}
    desiredCapacity: ${NODE_COUNT}
    minSize: 2
    maxSize: 10
    volumeSize: 100
    volumeType: gp3
    amiFamily: AmazonLinux2
    ssh:
      allow: false
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        certManager: true
        efs: true
        ebs: true
        albIngress: true
        cloudWatch: true
    labels:
      role: worker
      environment: production
    tags:
      Environment: production
      Project: smc-trading-agent
    availabilityZones: ["${REGION}a", "${REGION}b", "${REGION}c"]

# Add-ons
addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
EOF

    eksctl create cluster -f cluster-config.yaml
    
    # Update kubeconfig
    aws eks update-kubeconfig --region ${REGION} --name ${CLUSTER_NAME}
}

create_gke_cluster() {
    log "Creating GKE cluster..."
    
    gcloud container clusters create ${CLUSTER_NAME} \
        --zone=${REGION} \
        --machine-type=${NODE_TYPE} \
        --num-nodes=${NODE_COUNT} \
        --enable-autoscaling \
        --min-nodes=2 \
        --max-nodes=10 \
        --enable-autorepair \
        --enable-autoupgrade \
        --enable-network-policy \
        --enable-ip-alias \
        --cluster-version=${KUBERNETES_VERSION} \
        --disk-size=100GB \
        --disk-type=pd-ssd \
        --labels=environment=production,project=smc-trading-agent
    
    # Get credentials
    gcloud container clusters get-credentials ${CLUSTER_NAME} --zone=${REGION}
}

create_aks_cluster() {
    log "Creating AKS cluster..."
    
    # Create resource group
    az group create --name ${CLUSTER_NAME}-rg --location ${REGION}
    
    # Create cluster
    az aks create \
        --resource-group ${CLUSTER_NAME}-rg \
        --name ${CLUSTER_NAME} \
        --node-count ${NODE_COUNT} \
        --node-vm-size ${NODE_TYPE} \
        --kubernetes-version ${KUBERNETES_VERSION} \
        --enable-cluster-autoscaler \
        --min-count 2 \
        --max-count 10 \
        --enable-addons monitoring \
        --network-plugin azure \
        --network-policy azure \
        --generate-ssh-keys \
        --tags Environment=production Project=smc-trading-agent
    
    # Get credentials
    az aks get-credentials --resource-group ${CLUSTER_NAME}-rg --name ${CLUSTER_NAME}
}

# Install essential components
install_components() {
    log "Installing essential Kubernetes components..."
    
    # Add Helm repositories
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo add jetstack https://charts.jetstack.io
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install NGINX Ingress Controller
    log "Installing NGINX Ingress Controller..."
    helm install ingress-nginx ingress-nginx/ingress-nginx \
        --namespace ingress-nginx \
        --create-namespace \
        --set controller.replicaCount=2 \
        --set controller.nodeSelector."kubernetes\.io/os"=linux \
        --set defaultBackend.nodeSelector."kubernetes\.io/os"=linux \
        --set controller.service.type=LoadBalancer \
        --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb" \
        --set controller.metrics.enabled=true \
        --set controller.podAnnotations."prometheus\.io/scrape"="true" \
        --set controller.podAnnotations."prometheus\.io/port"="10254"
    
    # Install cert-manager
    log "Installing cert-manager..."
    helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --version v1.13.0 \
        --set installCRDs=true \
        --set global.leaderElection.namespace=cert-manager
    
    # Wait for cert-manager to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=300s
    
    log "Essential components installed successfully."
}

# Apply Kubernetes manifests
apply_manifests() {
    log "Applying Kubernetes manifests..."
    
    # Apply in order
    kubectl apply -f namespace.yaml
    kubectl apply -f rbac.yaml
    kubectl apply -f network-policies.yaml
    kubectl apply -f ingress-controller.yaml
    
    log "Kubernetes manifests applied successfully."
}

# Verify cluster setup
verify_cluster() {
    log "Verifying cluster setup..."
    
    # Check nodes
    log "Cluster nodes:"
    kubectl get nodes -o wide
    
    # Check namespaces
    log "Namespaces:"
    kubectl get namespaces
    
    # Check ingress controller
    log "Ingress controller status:"
    kubectl get pods -n ingress-nginx
    
    # Check cert-manager
    log "Cert-manager status:"
    kubectl get pods -n cert-manager
    
    # Check network policies
    log "Network policies:"
    kubectl get networkpolicies -n smc-trading
    
    log "Cluster verification completed."
}

# Main execution
main() {
    log "Starting SMC Trading Agent Kubernetes cluster setup..."
    
    check_prerequisites
    create_cluster
    install_components
    apply_manifests
    verify_cluster
    
    log "Kubernetes cluster setup completed successfully!"
    log "Cluster name: ${CLUSTER_NAME}"
    log "Region: ${REGION}"
    log "Nodes: ${NODE_COUNT}"
    
    warn "Next steps:"
    warn "1. Update DNS records to point to the LoadBalancer IP"
    warn "2. Configure monitoring authentication secrets"
    warn "3. Deploy the SMC Trading Agent applications"
    warn "4. Test SSL certificates and ingress routing"
}

# Run main function
main "$@"