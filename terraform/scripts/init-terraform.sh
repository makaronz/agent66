#!/bin/bash

# Terraform initialization script for SMC Trading Agent
# This script sets up the Terraform backend and initializes the infrastructure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TERRAFORM_VERSION="1.6.0"
AWS_REGION="${AWS_REGION:-us-west-2}"
PROJECT_NAME="${PROJECT_NAME:-smc-trading}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

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
    
    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install AWS CLI first."
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS credentials not configured. Please run 'aws configure' first."
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        error "Terraform is not installed. Please install Terraform ${TERRAFORM_VERSION} or later."
    fi
    
    # Check Terraform version
    CURRENT_VERSION=$(terraform version -json | jq -r '.terraform_version')
    if ! printf '%s\n%s\n' "${TERRAFORM_VERSION}" "${CURRENT_VERSION}" | sort -V -C; then
        warn "Terraform version ${CURRENT_VERSION} is older than recommended ${TERRAFORM_VERSION}"
    fi
    
    log "Prerequisites check passed."
}

# Create S3 bucket for Terraform state
create_state_bucket() {
    local bucket_name="${PROJECT_NAME}-terraform-state"
    
    log "Creating S3 bucket for Terraform state: ${bucket_name}"
    
    # Check if bucket already exists
    if aws s3api head-bucket --bucket "${bucket_name}" 2>/dev/null; then
        log "S3 bucket ${bucket_name} already exists."
        return 0
    fi
    
    # Create bucket
    if [ "${AWS_REGION}" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "${bucket_name}"
    else
        aws s3api create-bucket \
            --bucket "${bucket_name}" \
            --region "${AWS_REGION}" \
            --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    fi
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "${bucket_name}" \
        --versioning-configuration Status=Enabled
    
    # Enable server-side encryption
    aws s3api put-bucket-encryption \
        --bucket "${bucket_name}" \
        --server-side-encryption-configuration '{
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    },
                    "BucketKeyEnabled": true
                }
            ]
        }'
    
    # Block public access
    aws s3api put-public-access-block \
        --bucket "${bucket_name}" \
        --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    
    log "S3 bucket ${bucket_name} created successfully."
}

# Create DynamoDB table for state locking
create_lock_table() {
    local table_name="${PROJECT_NAME}-terraform-locks"
    
    log "Creating DynamoDB table for Terraform state locking: ${table_name}"
    
    # Check if table already exists
    if aws dynamodb describe-table --table-name "${table_name}" &>/dev/null; then
        log "DynamoDB table ${table_name} already exists."
        return 0
    fi
    
    # Create table
    aws dynamodb create-table \
        --table-name "${table_name}" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region "${AWS_REGION}"
    
    # Wait for table to be active
    log "Waiting for DynamoDB table to be active..."
    aws dynamodb wait table-exists --table-name "${table_name}" --region "${AWS_REGION}"
    
    log "DynamoDB table ${table_name} created successfully."
}

# Initialize Terraform
init_terraform() {
    log "Initializing Terraform..."
    
    # Change to terraform directory
    cd terraform
    
    # Create terraform.tfvars if it doesn't exist
    if [ ! -f "terraform.tfvars" ]; then
        log "Creating terraform.tfvars from example..."
        cp terraform.tfvars.example terraform.tfvars
        
        # Update with current values
        sed -i.bak "s/aws_region   = \"us-west-2\"/aws_region   = \"${AWS_REGION}\"/" terraform.tfvars
        sed -i.bak "s/environment  = \"production\"/environment  = \"${ENVIRONMENT}\"/" terraform.tfvars
        sed -i.bak "s/project_name = \"smc-trading\"/project_name = \"${PROJECT_NAME}\"/" terraform.tfvars
        
        rm terraform.tfvars.bak
        
        warn "Please review and customize terraform.tfvars before proceeding."
    fi
    
    # Initialize Terraform
    terraform init \
        -backend-config="bucket=${PROJECT_NAME}-terraform-state" \
        -backend-config="key=infrastructure/terraform.tfstate" \
        -backend-config="region=${AWS_REGION}" \
        -backend-config="dynamodb_table=${PROJECT_NAME}-terraform-locks" \
        -backend-config="encrypt=true"
    
    log "Terraform initialized successfully."
}

# Create workspace
create_workspace() {
    log "Creating Terraform workspace: ${ENVIRONMENT}"
    
    cd terraform
    
    # List existing workspaces
    if terraform workspace list | grep -q "${ENVIRONMENT}"; then
        log "Workspace ${ENVIRONMENT} already exists."
        terraform workspace select "${ENVIRONMENT}"
    else
        terraform workspace new "${ENVIRONMENT}"
    fi
    
    log "Using workspace: ${ENVIRONMENT}"
}

# Validate Terraform configuration
validate_terraform() {
    log "Validating Terraform configuration..."
    
    cd terraform
    
    # Format check
    if ! terraform fmt -check=true -diff=true; then
        warn "Terraform files are not properly formatted. Run 'terraform fmt' to fix."
    fi
    
    # Validate configuration
    terraform validate
    
    log "Terraform configuration is valid."
}

# Plan infrastructure
plan_infrastructure() {
    log "Creating Terraform plan..."
    
    cd terraform
    
    terraform plan -out=tfplan
    
    log "Terraform plan created successfully."
    warn "Review the plan above before applying changes."
    warn "To apply: terraform apply tfplan"
    warn "To destroy: terraform destroy"
}

# Main execution
main() {
    log "Starting Terraform initialization for SMC Trading Agent..."
    log "Project: ${PROJECT_NAME}"
    log "Environment: ${ENVIRONMENT}"
    log "Region: ${AWS_REGION}"
    
    check_prerequisites
    create_state_bucket
    create_lock_table
    init_terraform
    create_workspace
    validate_terraform
    
    if [ "${1:-}" = "--plan" ]; then
        plan_infrastructure
    fi
    
    log "Terraform initialization completed successfully!"
    
    echo ""
    log "Next steps:"
    log "1. Review and customize terraform/terraform.tfvars"
    log "2. Run: cd terraform && terraform plan"
    log "3. Run: cd terraform && terraform apply"
    
    echo ""
    log "Useful commands:"
    log "- List workspaces: terraform workspace list"
    log "- Switch workspace: terraform workspace select <name>"
    log "- Show current state: terraform show"
    log "- Import existing resources: terraform import <resource> <id>"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--plan] [--help]"
        echo ""
        echo "Options:"
        echo "  --plan    Create a Terraform plan after initialization"
        echo "  --help    Show this help message"
        echo ""
        echo "Environment variables:"
        echo "  AWS_REGION     AWS region (default: us-west-2)"
        echo "  PROJECT_NAME   Project name (default: smc-trading)"
        echo "  ENVIRONMENT    Environment name (default: dev)"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac