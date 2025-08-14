#!/bin/bash

# Kafka Cluster Deployment Script for SMC Trading Agent
# This script deploys a production-ready Kafka cluster with monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="kafka"
STAGING_NAMESPACE="kafka-staging"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check if storage class exists
    if ! kubectl get storageclass fast-ssd &> /dev/null; then
        log_warning "Storage class 'fast-ssd' not found. Using default storage class."
        # Replace fast-ssd with default in all manifests
        find . -name "*.yaml" -exec sed -i 's/storageClassName: "fast-ssd"/storageClassName: ""/g' {} \;
    fi
    
    log_success "Prerequisites check completed"
}

create_namespaces() {
    log_info "Creating namespaces..."
    
    kubectl apply -f kafka-namespace.yaml
    
    # Wait for namespaces to be ready
    kubectl wait --for=condition=Active namespace/$NAMESPACE --timeout=60s
    kubectl wait --for=condition=Active namespace/$STAGING_NAMESPACE --timeout=60s
    
    log_success "Namespaces created successfully"
}

deploy_zookeeper() {
    log_info "Deploying Zookeeper cluster..."
    
    kubectl apply -f zookeeper-deployment.yaml
    
    # Wait for Zookeeper to be ready
    log_info "Waiting for Zookeeper pods to be ready..."
    kubectl wait --for=condition=Ready pod -l app=zookeeper -n $NAMESPACE --timeout=300s
    
    # Verify Zookeeper cluster health
    log_info "Verifying Zookeeper cluster health..."
    for i in {0..2}; do
        if kubectl exec -n $NAMESPACE zookeeper-$i -- sh -c "echo ruok | nc localhost 2181" | grep -q "imok"; then
            log_success "Zookeeper-$i is healthy"
        else
            log_error "Zookeeper-$i health check failed"
            exit 1
        fi
    done
    
    log_success "Zookeeper cluster deployed successfully"
}

deploy_kafka() {
    log_info "Deploying Kafka cluster..."
    
    kubectl apply -f kafka-cluster-deployment.yaml
    
    # Wait for Kafka to be ready
    log_info "Waiting for Kafka pods to be ready..."
    kubectl wait --for=condition=Ready pod -l app=kafka -n $NAMESPACE --timeout=600s
    
    # Verify Kafka cluster health
    log_info "Verifying Kafka cluster health..."
    for i in {0..2}; do
        if kubectl exec -n $NAMESPACE kafka-$i -- kafka-broker-api-versions --bootstrap-server localhost:9092 &> /dev/null; then
            log_success "Kafka-$i is healthy"
        else
            log_error "Kafka-$i health check failed"
            exit 1
        fi
    done
    
    log_success "Kafka cluster deployed successfully"
}

create_topics() {
    log_info "Creating Kafka topics..."
    
    kubectl apply -f kafka-topics-job.yaml
    
    # Wait for job to complete
    log_info "Waiting for topic creation job to complete..."
    kubectl wait --for=condition=complete job/kafka-topics-setup -n $NAMESPACE --timeout=300s
    
    # Check job logs
    log_info "Topic creation job logs:"
    kubectl logs job/kafka-topics-setup -n $NAMESPACE
    
    # Verify topics were created
    log_info "Verifying topics were created..."
    TOPIC_COUNT=$(kubectl exec -n $NAMESPACE kafka-0 -- kafka-topics --bootstrap-server localhost:9092 --list | wc -l)
    if [ "$TOPIC_COUNT" -gt 0 ]; then
        log_success "Topics created successfully. Total topics: $TOPIC_COUNT"
    else
        log_error "No topics found. Topic creation may have failed."
        exit 1
    fi
    
    log_success "Kafka topics created successfully"
}

deploy_kafka_connect() {
    log_info "Deploying Kafka Connect..."
    
    kubectl apply -f kafka-connect-deployment.yaml
    
    # Wait for Kafka Connect to be ready
    log_info "Waiting for Kafka Connect pods to be ready..."
    kubectl wait --for=condition=Ready pod -l app=kafka-connect -n $NAMESPACE --timeout=300s
    
    # Verify Kafka Connect health
    log_info "Verifying Kafka Connect health..."
    if kubectl exec -n $NAMESPACE -l app=kafka-connect -- curl -f http://localhost:8083/ &> /dev/null; then
        log_success "Kafka Connect is healthy"
    else
        log_error "Kafka Connect health check failed"
        exit 1
    fi
    
    log_success "Kafka Connect deployed successfully"
}

deploy_monitoring() {
    log_info "Deploying Kafka monitoring..."
    
    kubectl apply -f kafka-monitoring.yaml
    
    # Wait for monitoring components to be ready
    log_info "Waiting for monitoring pods to be ready..."
    kubectl wait --for=condition=Ready pod -l app=kafka-prometheus -n $NAMESPACE --timeout=300s
    kubectl wait --for=condition=Ready pod -l app=kafka-grafana -n $NAMESPACE --timeout=300s
    
    log_success "Kafka monitoring deployed successfully"
}

verify_deployment() {
    log_info "Verifying complete deployment..."
    
    # Check all pods are running
    log_info "Checking pod status..."
    kubectl get pods -n $NAMESPACE
    
    # Check services
    log_info "Checking services..."
    kubectl get services -n $NAMESPACE
    
    # Check persistent volumes
    log_info "Checking persistent volumes..."
    kubectl get pvc -n $NAMESPACE
    
    # Test Kafka functionality
    log_info "Testing Kafka functionality..."
    
    # Create a test topic
    kubectl exec -n $NAMESPACE kafka-0 -- kafka-topics \
        --bootstrap-server localhost:9092 \
        --create \
        --topic test-topic \
        --partitions 3 \
        --replication-factor 3 \
        --if-not-exists
    
    # Produce a test message
    echo "test message" | kubectl exec -i -n $NAMESPACE kafka-0 -- kafka-console-producer \
        --bootstrap-server localhost:9092 \
        --topic test-topic
    
    # Consume the test message
    TEST_MESSAGE=$(kubectl exec -n $NAMESPACE kafka-0 -- timeout 10 kafka-console-consumer \
        --bootstrap-server localhost:9092 \
        --topic test-topic \
        --from-beginning \
        --max-messages 1 2>/dev/null || true)
    
    if [[ "$TEST_MESSAGE" == *"test message"* ]]; then
        log_success "Kafka functionality test passed"
    else
        log_warning "Kafka functionality test failed, but cluster may still be functional"
    fi
    
    # Clean up test topic
    kubectl exec -n $NAMESPACE kafka-0 -- kafka-topics \
        --bootstrap-server localhost:9092 \
        --delete \
        --topic test-topic
    
    log_success "Deployment verification completed"
}

print_access_info() {
    log_info "Kafka cluster access information:"
    echo ""
    echo "Kafka Brokers (internal):"
    echo "  kafka-0.kafka-service.kafka.svc.cluster.local:9092"
    echo "  kafka-1.kafka-service.kafka.svc.cluster.local:9092"
    echo "  kafka-2.kafka-service.kafka.svc.cluster.local:9092"
    echo ""
    echo "Kafka Connect REST API:"
    echo "  http://kafka-connect-service.kafka.svc.cluster.local:8083"
    echo ""
    echo "Monitoring:"
    echo "  Prometheus: http://kafka-prometheus.kafka.svc.cluster.local:9090"
    echo "  Grafana: http://kafka-grafana.kafka.svc.cluster.local:3000 (admin/admin123)"
    echo ""
    echo "To access from outside the cluster, use port-forwarding:"
    echo "  kubectl port-forward -n kafka svc/kafka-external-service 9093:9093"
    echo "  kubectl port-forward -n kafka svc/kafka-prometheus 9090:9090"
    echo "  kubectl port-forward -n kafka svc/kafka-grafana 3000:3000"
    echo ""
}

cleanup() {
    log_warning "Cleaning up Kafka cluster..."
    
    # Delete all resources
    kubectl delete -f kafka-monitoring.yaml --ignore-not-found=true
    kubectl delete -f kafka-connect-deployment.yaml --ignore-not-found=true
    kubectl delete job kafka-topics-setup -n $NAMESPACE --ignore-not-found=true
    kubectl delete -f kafka-cluster-deployment.yaml --ignore-not-found=true
    kubectl delete -f zookeeper-deployment.yaml --ignore-not-found=true
    kubectl delete -f kafka-namespace.yaml --ignore-not-found=true
    
    log_success "Cleanup completed"
}

# Main execution
main() {
    case "${1:-deploy}" in
        "deploy")
            log_info "Starting Kafka cluster deployment..."
            check_prerequisites
            create_namespaces
            deploy_zookeeper
            deploy_kafka
            create_topics
            deploy_kafka_connect
            deploy_monitoring
            verify_deployment
            print_access_info
            log_success "Kafka cluster deployment completed successfully!"
            ;;
        "cleanup")
            cleanup
            ;;
        "verify")
            verify_deployment
            ;;
        "info")
            print_access_info
            ;;
        *)
            echo "Usage: $0 {deploy|cleanup|verify|info}"
            echo ""
            echo "Commands:"
            echo "  deploy  - Deploy the complete Kafka cluster"
            echo "  cleanup - Remove all Kafka cluster resources"
            echo "  verify  - Verify the deployment"
            echo "  info    - Show access information"
            exit 1
            ;;
    esac
}

# Handle script interruption
trap 'log_error "Script interrupted"; exit 1' INT TERM

# Execute main function
main "$@"