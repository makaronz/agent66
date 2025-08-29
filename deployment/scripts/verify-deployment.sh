#!/bin/bash

# Comprehensive deployment verification script
# Verifies all components are working correctly in production

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
NAMESPACE=${NAMESPACE:-"smc-trading"}
VAULT_NAMESPACE=${VAULT_NAMESPACE:-"vault"}
TIMEOUT=${TIMEOUT:-300}

echo "🔍 Starting comprehensive deployment verification..."
echo "   Namespace: $NAMESPACE"
echo "   Vault Namespace: $VAULT_NAMESPACE"
echo "   Timeout: ${TIMEOUT}s"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "kubectl is available and connected to cluster"
}

# Check if namespaces exist
check_namespaces() {
    log_info "Checking namespaces..."
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_success "Namespace $NAMESPACE exists"
    else
        log_error "Namespace $NAMESPACE does not exist"
        return 1
    fi
    
    if kubectl get namespace "$VAULT_NAMESPACE" &> /dev/null; then
        log_success "Vault namespace $VAULT_NAMESPACE exists"
    else
        log_error "Vault namespace $VAULT_NAMESPACE does not exist"
        return 1
    fi
}

# Check Vault deployment
check_vault() {
    log_info "Checking Vault deployment..."
    
    # Check if Vault pods are running
    if ! kubectl get pods -n "$VAULT_NAMESPACE" -l app=vault --no-headers | grep -q "Running"; then
        log_error "Vault pods are not running"
        kubectl get pods -n "$VAULT_NAMESPACE" -l app=vault
        return 1
    fi
    
    log_success "Vault pods are running"
    
    # Check Vault service
    if ! kubectl get service -n "$VAULT_NAMESPACE" vault &> /dev/null; then
        log_error "Vault service not found"
        return 1
    fi
    
    log_success "Vault service exists"
    
    # Check Vault health (if accessible)
    VAULT_POD=$(kubectl get pods -n "$VAULT_NAMESPACE" -l app=vault -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$VAULT_POD" ]; then
        if kubectl exec -n "$VAULT_NAMESPACE" "$VAULT_POD" -- vault status &> /dev/null; then
            log_success "Vault is healthy and unsealed"
        else
            log_warning "Vault status check failed (may be sealed or initializing)"
        fi
    fi
}

# Check Consul deployment (Vault backend)
check_consul() {
    log_info "Checking Consul deployment..."
    
    if ! kubectl get pods -n "$VAULT_NAMESPACE" -l app=consul --no-headers | grep -q "Running"; then
        log_error "Consul pods are not running"
        kubectl get pods -n "$VAULT_NAMESPACE" -l app=consul
        return 1
    fi
    
    log_success "Consul pods are running"
    
    if ! kubectl get service -n "$VAULT_NAMESPACE" consul &> /dev/null; then
        log_error "Consul service not found"
        return 1
    fi
    
    log_success "Consul service exists"
}

# Check SMC Trading Agent deployment
check_smc_agent() {
    log_info "Checking SMC Trading Agent deployment..."
    
    # Check deployment exists
    if ! kubectl get deployment -n "$NAMESPACE" smc-trading-agent &> /dev/null; then
        log_error "SMC Trading Agent deployment not found"
        return 1
    fi
    
    log_success "SMC Trading Agent deployment exists"
    
    # Check if pods are running
    READY_REPLICAS=$(kubectl get deployment -n "$NAMESPACE" smc-trading-agent -o jsonpath='{.status.readyReplicas}')
    DESIRED_REPLICAS=$(kubectl get deployment -n "$NAMESPACE" smc-trading-agent -o jsonpath='{.spec.replicas}')
    
    if [ "$READY_REPLICAS" = "$DESIRED_REPLICAS" ] && [ "$READY_REPLICAS" -gt 0 ]; then
        log_success "SMC Trading Agent pods are ready ($READY_REPLICAS/$DESIRED_REPLICAS)"
    else
        log_error "SMC Trading Agent pods are not ready ($READY_REPLICAS/$DESIRED_REPLICAS)"
        kubectl get pods -n "$NAMESPACE" -l app=smc-trading-agent
        return 1
    fi
    
    # Check service
    if kubectl get service -n "$NAMESPACE" smc-trading-agent-service &> /dev/null; then
        log_success "SMC Trading Agent service exists"
    else
        log_warning "SMC Trading Agent service not found"
    fi
}

# Check persistent volumes
check_storage() {
    log_info "Checking persistent storage..."
    
    # Check Vault PVC
    if kubectl get pvc -n "$VAULT_NAMESPACE" vault-data-pvc &> /dev/null; then
        VAULT_PVC_STATUS=$(kubectl get pvc -n "$VAULT_NAMESPACE" vault-data-pvc -o jsonpath='{.status.phase}')
        if [ "$VAULT_PVC_STATUS" = "Bound" ]; then
            log_success "Vault PVC is bound"
        else
            log_error "Vault PVC is not bound (status: $VAULT_PVC_STATUS)"
            return 1
        fi
    else
        log_error "Vault PVC not found"
        return 1
    fi
    
    # Check Consul PVC
    if kubectl get pvc -n "$VAULT_NAMESPACE" consul-data-pvc &> /dev/null; then
        CONSUL_PVC_STATUS=$(kubectl get pvc -n "$VAULT_NAMESPACE" consul-data-pvc -o jsonpath='{.status.phase}')
        if [ "$CONSUL_PVC_STATUS" = "Bound" ]; then
            log_success "Consul PVC is bound"
        else
            log_error "Consul PVC is not bound (status: $CONSUL_PVC_STATUS)"
            return 1
        fi
    else
        log_error "Consul PVC not found"
        return 1
    fi
}

# Check ConfigMaps and Secrets
check_config() {
    log_info "Checking configuration..."
    
    # Check Vault ConfigMap
    if kubectl get configmap -n "$VAULT_NAMESPACE" vault-config &> /dev/null; then
        log_success "Vault ConfigMap exists"
    else
        log_error "Vault ConfigMap not found"
        return 1
    fi
    
    # Check Vault policies ConfigMap
    if kubectl get configmap -n "$VAULT_NAMESPACE" vault-policies &> /dev/null; then
        log_success "Vault policies ConfigMap exists"
    else
        log_error "Vault policies ConfigMap not found"
        return 1
    fi
    
    # Check ServiceAccounts
    if kubectl get serviceaccount -n "$NAMESPACE" smc-trading-agent &> /dev/null; then
        log_success "SMC Trading Agent ServiceAccount exists"
    else
        log_error "SMC Trading Agent ServiceAccount not found"
        return 1
    fi
}

# Test Vault connectivity from SMC Agent
test_vault_connectivity() {
    log_info "Testing Vault connectivity from SMC Trading Agent..."
    
    SMC_POD=$(kubectl get pods -n "$NAMESPACE" -l app=smc-trading-agent -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$SMC_POD" ]; then
        log_error "No SMC Trading Agent pods found"
        return 1
    fi
    
    # Test DNS resolution
    if kubectl exec -n "$NAMESPACE" "$SMC_POD" -- nslookup vault.vault.svc.cluster.local &> /dev/null; then
        log_success "Vault DNS resolution works from SMC Agent"
    else
        log_error "Vault DNS resolution failed from SMC Agent"
        return 1
    fi
    
    # Test HTTP connectivity
    if kubectl exec -n "$NAMESPACE" "$SMC_POD" -- curl -s -f http://vault.vault.svc.cluster.local:8200/v1/sys/health &> /dev/null; then
        log_success "Vault HTTP connectivity works from SMC Agent"
    else
        log_error "Vault HTTP connectivity failed from SMC Agent"
        return 1
    fi
}

# Test application health endpoints
test_health_endpoints() {
    log_info "Testing application health endpoints..."
    
    SMC_POD=$(kubectl get pods -n "$NAMESPACE" -l app=smc-trading-agent -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$SMC_POD" ]; then
        log_error "No SMC Trading Agent pods found"
        return 1
    fi
    
    # Test health endpoint
    if kubectl exec -n "$NAMESPACE" "$SMC_POD" -- curl -s -f http://localhost:8080/health &> /dev/null; then
        log_success "SMC Agent health endpoint is responding"
    else
        log_warning "SMC Agent health endpoint is not responding (may not be implemented yet)"
    fi
    
    # Test readiness endpoint
    if kubectl exec -n "$NAMESPACE" "$SMC_POD" -- curl -s -f http://localhost:8080/ready &> /dev/null; then
        log_success "SMC Agent readiness endpoint is responding"
    else
        log_warning "SMC Agent readiness endpoint is not responding (may not be implemented yet)"
    fi
}

# Check logs for errors
check_logs() {
    log_info "Checking application logs for errors..."
    
    # Check Vault logs
    VAULT_POD=$(kubectl get pods -n "$VAULT_NAMESPACE" -l app=vault -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$VAULT_POD" ]; then
        ERROR_COUNT=$(kubectl logs -n "$VAULT_NAMESPACE" "$VAULT_POD" --tail=100 | grep -i error | wc -l)
        if [ "$ERROR_COUNT" -eq 0 ]; then
            log_success "No errors found in Vault logs"
        else
            log_warning "Found $ERROR_COUNT error(s) in Vault logs"
        fi
    fi
    
    # Check SMC Agent logs
    SMC_POD=$(kubectl get pods -n "$NAMESPACE" -l app=smc-trading-agent -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$SMC_POD" ]; then
        ERROR_COUNT=$(kubectl logs -n "$NAMESPACE" "$SMC_POD" --tail=100 | grep -i error | wc -l)
        if [ "$ERROR_COUNT" -eq 0 ]; then
            log_success "No errors found in SMC Agent logs"
        else
            log_warning "Found $ERROR_COUNT error(s) in SMC Agent logs"
        fi
    fi
}

# Test secret retrieval (if Vault is initialized)
test_secret_retrieval() {
    log_info "Testing secret retrieval (if Vault is initialized)..."
    
    VAULT_POD=$(kubectl get pods -n "$VAULT_NAMESPACE" -l app=vault -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$VAULT_POD" ]; then
        log_error "No Vault pods found"
        return 1
    fi
    
    # Check if Vault is initialized
    if kubectl exec -n "$VAULT_NAMESPACE" "$VAULT_POD" -- vault status | grep -q "Initialized.*true"; then
        log_success "Vault is initialized"
        
        # Try to list secrets (this will fail if not authenticated, which is expected)
        if kubectl exec -n "$VAULT_NAMESPACE" "$VAULT_POD" -- vault kv list secret/ &> /dev/null; then
            log_success "Secret listing works (Vault is authenticated)"
        else
            log_warning "Secret listing failed (Vault may not be authenticated - this is normal)"
        fi
    else
        log_warning "Vault is not initialized yet"
    fi
}

# Generate deployment report
generate_report() {
    log_info "Generating deployment report..."
    
    REPORT_FILE="$PROJECT_ROOT/deployment-verification-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "SMC Trading Agent Deployment Verification Report"
        echo "Generated: $(date)"
        echo "Namespace: $NAMESPACE"
        echo "Vault Namespace: $VAULT_NAMESPACE"
        echo ""
        
        echo "=== Kubernetes Resources ==="
        echo "Deployments:"
        kubectl get deployments -n "$NAMESPACE" -o wide
        echo ""
        kubectl get deployments -n "$VAULT_NAMESPACE" -o wide
        echo ""
        
        echo "Pods:"
        kubectl get pods -n "$NAMESPACE" -o wide
        echo ""
        kubectl get pods -n "$VAULT_NAMESPACE" -o wide
        echo ""
        
        echo "Services:"
        kubectl get services -n "$NAMESPACE" -o wide
        echo ""
        kubectl get services -n "$VAULT_NAMESPACE" -o wide
        echo ""
        
        echo "PVCs:"
        kubectl get pvc -n "$VAULT_NAMESPACE" -o wide
        echo ""
        
        echo "=== Recent Logs ==="
        echo "SMC Agent Logs (last 20 lines):"
        SMC_POD=$(kubectl get pods -n "$NAMESPACE" -l app=smc-trading-agent -o jsonpath='{.items[0].metadata.name}')
        if [ -n "$SMC_POD" ]; then
            kubectl logs -n "$NAMESPACE" "$SMC_POD" --tail=20
        fi
        echo ""
        
        echo "Vault Logs (last 20 lines):"
        VAULT_POD=$(kubectl get pods -n "$VAULT_NAMESPACE" -l app=vault -o jsonpath='{.items[0].metadata.name}')
        if [ -n "$VAULT_POD" ]; then
            kubectl logs -n "$VAULT_NAMESPACE" "$VAULT_POD" --tail=20
        fi
        
    } > "$REPORT_FILE"
    
    log_success "Deployment report saved to: $REPORT_FILE"
}

# Main verification function
main() {
    local exit_code=0
    
    # Run all checks
    check_kubectl || exit_code=1
    check_namespaces || exit_code=1
    check_storage || exit_code=1
    check_config || exit_code=1
    check_consul || exit_code=1
    check_vault || exit_code=1
    check_smc_agent || exit_code=1
    test_vault_connectivity || exit_code=1
    test_health_endpoints || exit_code=1
    check_logs || exit_code=1
    test_secret_retrieval || exit_code=1
    
    # Generate report regardless of success/failure
    generate_report
    
    echo ""
    if [ $exit_code -eq 0 ]; then
        log_success "🎉 All deployment verification checks passed!"
        echo ""
        echo "Next steps:"
        echo "1. Initialize Vault with: kubectl exec -n $VAULT_NAMESPACE vault-0 -- vault operator init"
        echo "2. Unseal Vault with the unseal keys"
        echo "3. Run the Vault initialization script: deployment/scripts/vault-init.sh"
        echo "4. Migrate secrets to Vault: deployment/scripts/migrate-secrets-to-vault.sh"
        echo "5. Test the application functionality"
    else
        log_error "❌ Some deployment verification checks failed!"
        echo ""
        echo "Please review the errors above and check the deployment report for details."
        echo "Common issues:"
        echo "- Persistent volumes not available"
        echo "- Insufficient resources in cluster"
        echo "- Network policies blocking communication"
        echo "- Missing RBAC permissions"
    fi
    
    return $exit_code
}

# Run main function
main "$@"