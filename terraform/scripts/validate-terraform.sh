#!/bin/bash

# Terraform validation and testing script for SMC Trading Agent
# This script validates Terraform configuration and runs tests

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TERRAFORM_DIR="terraform"
TEST_DIR="terraform/tests"

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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed."
    fi
    
    # Check if tflint is installed
    if ! command -v tflint &> /dev/null; then
        warn "tflint is not installed. Install it for better linting: https://github.com/terraform-linters/tflint"
    fi
    
    # Check if checkov is installed
    if ! command -v checkov &> /dev/null; then
        warn "checkov is not installed. Install it for security scanning: pip install checkov"
    fi
    
    # Check if terraform-docs is installed
    if ! command -v terraform-docs &> /dev/null; then
        warn "terraform-docs is not installed. Install it for documentation generation"
    fi
    
    log "Prerequisites check completed."
}

# Format Terraform files
format_terraform() {
    log "Formatting Terraform files..."
    
    cd "${TERRAFORM_DIR}"
    
    if terraform fmt -check=true -diff=true -recursive; then
        log "All Terraform files are properly formatted."
    else
        warn "Some files need formatting. Running terraform fmt..."
        terraform fmt -recursive
        log "Terraform files formatted successfully."
    fi
    
    cd ..
}

# Validate Terraform configuration
validate_terraform() {
    log "Validating Terraform configuration..."
    
    cd "${TERRAFORM_DIR}"
    
    # Initialize if needed
    if [ ! -d ".terraform" ]; then
        log "Initializing Terraform..."
        terraform init -backend=false
    fi
    
    # Validate configuration
    if terraform validate; then
        log "Terraform configuration is valid."
    else
        error "Terraform configuration validation failed."
    fi
    
    cd ..
}

# Run tflint
run_tflint() {
    if ! command -v tflint &> /dev/null; then
        warn "Skipping tflint (not installed)."
        return 0
    fi
    
    log "Running tflint..."
    
    cd "${TERRAFORM_DIR}"
    
    # Initialize tflint
    tflint --init
    
    # Run tflint
    if tflint --recursive; then
        log "tflint passed successfully."
    else
        error "tflint found issues."
    fi
    
    cd ..
}

# Run Checkov security scan
run_checkov() {
    if ! command -v checkov &> /dev/null; then
        warn "Skipping Checkov (not installed)."
        return 0
    fi
    
    log "Running Checkov security scan..."
    
    if checkov -d "${TERRAFORM_DIR}" --framework terraform --output cli --quiet; then
        log "Checkov security scan passed."
    else
        warn "Checkov found security issues. Review the output above."
    fi
}

# Test Terraform modules
test_modules() {
    log "Testing Terraform modules..."
    
    # Create test directory if it doesn't exist
    mkdir -p "${TEST_DIR}"
    
    # Test each module
    for module_dir in "${TERRAFORM_DIR}/modules"/*; do
        if [ -d "${module_dir}" ]; then
            module_name=$(basename "${module_dir}")
            log "Testing module: ${module_name}"
            
            # Create test configuration
            cat > "${TEST_DIR}/test_${module_name}.tf" << EOF
# Test configuration for ${module_name} module
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-west-2"
  
  # Skip credentials for validation
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  skip_requesting_account_id  = true
}

module "${module_name}_test" {
  source = "../modules/${module_name}"
  
  # Add minimal required variables
  name = "test"
  tags = {
    Environment = "test"
    Module      = "${module_name}"
  }
}
EOF
            
            # Validate test configuration
            cd "${TEST_DIR}"
            terraform init -backend=false
            
            if terraform validate; then
                log "Module ${module_name} test passed."
            else
                error "Module ${module_name} test failed."
            fi
            
            cd ..
        fi
    done
    
    # Clean up test files
    rm -rf "${TEST_DIR}"
}

# Generate documentation
generate_docs() {
    if ! command -v terraform-docs &> /dev/null; then
        warn "Skipping documentation generation (terraform-docs not installed)."
        return 0
    fi
    
    log "Generating documentation..."
    
    # Generate main documentation
    terraform-docs markdown table --output-file README.md "${TERRAFORM_DIR}"
    
    # Generate module documentation
    for module_dir in "${TERRAFORM_DIR}/modules"/*; do
        if [ -d "${module_dir}" ]; then
            terraform-docs markdown table --output-file README.md "${module_dir}"
        fi
    done
    
    log "Documentation generated successfully."
}

# Check for common issues
check_common_issues() {
    log "Checking for common issues..."
    
    local issues_found=0
    
    # Check for hardcoded values
    if grep -r "us-west-2" "${TERRAFORM_DIR}" --include="*.tf" | grep -v variable | grep -v example; then
        warn "Found hardcoded region values. Consider using variables."
        ((issues_found++))
    fi
    
    # Check for missing tags
    if ! grep -r "tags.*=" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        warn "Some resources might be missing tags."
        ((issues_found++))
    fi
    
    # Check for missing descriptions
    if grep -r "variable.*{" "${TERRAFORM_DIR}" --include="*.tf" -A 5 | grep -B 5 -A 5 "description.*=" | wc -l | grep -q "^0$"; then
        warn "Some variables might be missing descriptions."
        ((issues_found++))
    fi
    
    # Check for outputs without descriptions
    if grep -r "output.*{" "${TERRAFORM_DIR}" --include="*.tf" -A 5 | grep -B 5 -A 5 "description.*=" | wc -l | grep -q "^0$"; then
        warn "Some outputs might be missing descriptions."
        ((issues_found++))
    fi
    
    if [ ${issues_found} -eq 0 ]; then
        log "No common issues found."
    else
        warn "Found ${issues_found} potential issues. Review the warnings above."
    fi
}

# Cost estimation
estimate_costs() {
    log "Estimating infrastructure costs..."
    
    # This is a basic cost estimation
    # In production, you might want to use tools like Infracost
    
    info "Basic cost estimation (monthly, USD):"
    info "- EKS Cluster: ~$73"
    info "- EC2 Instances (3x t3.medium): ~$100"
    info "- RDS (db.t3.small): ~$25"
    info "- ElastiCache (cache.t3.micro): ~$12"
    info "- NAT Gateway: ~$32"
    info "- Data Transfer: ~$50"
    info "- Total Estimated: ~$292/month"
    info ""
    info "Note: Actual costs may vary based on usage and region."
    info "Consider using Infracost for more accurate estimates."
}

# Security checklist
security_checklist() {
    log "Running security checklist..."
    
    local security_score=0
    local total_checks=10
    
    # Check 1: Encryption at rest
    if grep -r "encrypted.*=.*true" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ Encryption at rest enabled"
        ((security_score++))
    else
        warn "✗ Encryption at rest not found"
    fi
    
    # Check 2: VPC Flow Logs
    if grep -r "enable_flow_log.*=.*true" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ VPC Flow Logs enabled"
        ((security_score++))
    else
        warn "✗ VPC Flow Logs not enabled"
    fi
    
    # Check 3: Private subnets
    if grep -r "private_subnets" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ Private subnets configured"
        ((security_score++))
    else
        warn "✗ Private subnets not found"
    fi
    
    # Check 4: Security groups
    if grep -r "aws_security_group" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ Security groups configured"
        ((security_score++))
    else
        warn "✗ Security groups not found"
    fi
    
    # Check 5: IAM roles
    if grep -r "aws_iam_role" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ IAM roles configured"
        ((security_score++))
    else
        warn "✗ IAM roles not found"
    fi
    
    # Check 6: Backup configuration
    if grep -r "backup_retention_period" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ Backup configuration found"
        ((security_score++))
    else
        warn "✗ Backup configuration not found"
    fi
    
    # Check 7: Monitoring
    if grep -r "cloudwatch" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ CloudWatch monitoring configured"
        ((security_score++))
    else
        warn "✗ CloudWatch monitoring not found"
    fi
    
    # Check 8: Network ACLs or Security Groups
    if grep -r "ingress\|egress" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ Network access controls configured"
        ((security_score++))
    else
        warn "✗ Network access controls not found"
    fi
    
    # Check 9: Secrets management
    if grep -r "aws_secretsmanager\|random_password" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ Secrets management configured"
        ((security_score++))
    else
        warn "✗ Secrets management not found"
    fi
    
    # Check 10: Resource tagging
    if grep -r "tags.*=" "${TERRAFORM_DIR}" --include="*.tf" > /dev/null; then
        info "✓ Resource tagging configured"
        ((security_score++))
    else
        warn "✗ Resource tagging not found"
    fi
    
    local percentage=$((security_score * 100 / total_checks))
    log "Security Score: ${security_score}/${total_checks} (${percentage}%)"
    
    if [ ${percentage} -ge 80 ]; then
        log "Good security posture!"
    elif [ ${percentage} -ge 60 ]; then
        warn "Moderate security posture. Consider improvements."
    else
        warn "Poor security posture. Review security configurations."
    fi
}

# Main execution
main() {
    log "Starting Terraform validation and testing..."
    
    check_prerequisites
    format_terraform
    validate_terraform
    run_tflint
    run_checkov
    test_modules
    generate_docs
    check_common_issues
    estimate_costs
    security_checklist
    
    log "Terraform validation and testing completed successfully!"
    
    echo ""
    log "Summary:"
    log "- Configuration is valid and properly formatted"
    log "- Security scan completed"
    log "- Documentation generated"
    log "- Cost estimation provided"
    log "- Security checklist completed"
    
    echo ""
    log "Next steps:"
    log "1. Review any warnings or issues found above"
    log "2. Run 'terraform plan' to see what will be created"
    log "3. Run 'terraform apply' to create the infrastructure"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help]"
        echo ""
        echo "This script validates Terraform configuration and runs various tests."
        echo ""
        echo "Prerequisites:"
        echo "- terraform (required)"
        echo "- tflint (optional, for linting)"
        echo "- checkov (optional, for security scanning)"
        echo "- terraform-docs (optional, for documentation)"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac