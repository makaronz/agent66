# SMC Trading Agent Deployment Makefile
# This Makefile provides automation for deployment tasks

.PHONY: help build push deploy clean test lint validate
.DEFAULT_GOAL := help

# Configuration
IMAGE_NAME := smc-trading-agent
IMAGE_TAG := $(shell git rev-parse --short HEAD)
REGISTRY := your-registry.com
NAMESPACE := smc-trading
RELEASE_NAME := smc-agent
CHART_PATH := helm/smc-trading-agent
KUBECONFIG := ~/.kube/config

# Environment-specific configurations
DEV_NAMESPACE := smc-trading-dev
STAGING_NAMESPACE := smc-trading-staging
PROD_NAMESPACE := smc-trading-prod

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# Help target
help: ## Show this help message
	@echo "SMC Trading Agent Deployment Makefile"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment variables:"
	@echo "  IMAGE_NAME     = $(IMAGE_NAME)"
	@echo "  IMAGE_TAG      = $(IMAGE_TAG)"
	@echo "  REGISTRY       = $(REGISTRY)"
	@echo "  NAMESPACE      = $(NAMESPACE)"
	@echo "  RELEASE_NAME   = $(RELEASE_NAME)"

# Prerequisites check
check-prerequisites: ## Check if required tools are installed
	@echo "$(BLUE)[INFO]$(NC) Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) Docker is not installed"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) kubectl is not installed"; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) Helm is not installed"; exit 1; }
	@echo "$(GREEN)[SUCCESS]$(NC) All prerequisites are installed"

# Docker targets
build: ## Build Docker image
	@echo "$(BLUE)[INFO]$(NC) Building Docker image..."
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) -f docker/Dockerfile .
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(IMAGE_NAME):latest
	@echo "$(GREEN)[SUCCESS]$(NC) Docker image built successfully"

build-dev: ## Build Docker image for development
	@echo "$(BLUE)[INFO]$(NC) Building development Docker image..."
	docker build -t $(IMAGE_NAME):dev-latest -f docker/Dockerfile.dev .
	@echo "$(GREEN)[SUCCESS]$(NC) Development Docker image built successfully"

push: build ## Build and push Docker image to registry
	@echo "$(BLUE)[INFO]$(NC) Pushing Docker image to registry..."
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker tag $(IMAGE_NAME):latest $(REGISTRY)/$(IMAGE_NAME):latest
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):latest
	@echo "$(GREEN)[SUCCESS]$(NC) Docker image pushed successfully"

push-dev: build-dev ## Build and push development Docker image
	@echo "$(BLUE)[INFO]$(NC) Pushing development Docker image..."
	docker tag $(IMAGE_NAME):dev-latest localhost:5000/$(IMAGE_NAME):dev-latest
	docker push localhost:5000/$(IMAGE_NAME):dev-latest
	@echo "$(GREEN)[SUCCESS]$(NC) Development Docker image pushed successfully"

# Kubernetes targets
kubectl-check: ## Check kubectl connection
	@echo "$(BLUE)[INFO]$(NC) Checking kubectl connection..."
	@kubectl cluster-info >/dev/null 2>&1 || { echo "$(RED)[ERROR]$(NC) Cannot connect to Kubernetes cluster"; exit 1; }
	@echo "$(GREEN)[SUCCESS]$(NC) kubectl connection verified"

apply-k8s: kubectl-check ## Apply Kubernetes manifests
	@echo "$(BLUE)[INFO]$(NC) Applying Kubernetes manifests..."
	kubectl apply -f kubernetes/production/
	@echo "$(GREEN)[SUCCESS]$(NC) Kubernetes manifests applied"

delete-k8s: kubectl-check ## Delete Kubernetes resources
	@echo "$(YELLOW)[WARNING]$(NC) This will delete all Kubernetes resources"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	kubectl delete -f kubernetes/production/
	@echo "$(GREEN)[SUCCESS]$(NC) Kubernetes resources deleted"

# Helm targets
helm-lint: ## Lint Helm chart
	@echo "$(BLUE)[INFO]$(NC) Linting Helm chart..."
	helm lint $(CHART_PATH)
	@echo "$(GREEN)[SUCCESS]$(NC) Helm chart linted successfully"

helm-template: ## Generate Helm templates
	@echo "$(BLUE)[INFO]$(NC) Generating Helm templates..."
	helm template $(RELEASE_NAME) $(CHART_PATH) --namespace $(NAMESPACE)

helm-dependency: ## Update Helm dependencies
	@echo "$(BLUE)[INFO]$(NC) Updating Helm dependencies..."
	helm dependency update $(CHART_PATH)
	@echo "$(GREEN)[SUCCESS]$(NC) Helm dependencies updated"

helm-package: helm-lint ## Package Helm chart
	@echo "$(BLUE)[INFO]$(NC) Packaging Helm chart..."
	helm package $(CHART_PATH)
	@echo "$(GREEN)[SUCCESS]$(NC) Helm chart packaged"

# Development environment
deploy-dev: check-prerequisites helm-dependency ## Deploy to development environment
	@echo "$(BLUE)[INFO]$(NC) Deploying to development environment..."
	./helm/install.sh install -e development -n $(DEV_NAMESPACE) -r $(RELEASE_NAME)-dev --create-namespace --wait
	@echo "$(GREEN)[SUCCESS]$(NC) Deployed to development environment"

upgrade-dev: ## Upgrade development deployment
	@echo "$(BLUE)[INFO]$(NC) Upgrading development deployment..."
	./helm/install.sh upgrade -e development -n $(DEV_NAMESPACE) -r $(RELEASE_NAME)-dev --wait
	@echo "$(GREEN)[SUCCESS]$(NC) Development deployment upgraded"

undeploy-dev: ## Remove development deployment
	@echo "$(BLUE)[INFO]$(NC) Removing development deployment..."
	./helm/install.sh uninstall -n $(DEV_NAMESPACE) -r $(RELEASE_NAME)-dev
	@echo "$(GREEN)[SUCCESS]$(NC) Development deployment removed"

# Staging environment
deploy-staging: check-prerequisites helm-dependency push ## Deploy to staging environment
	@echo "$(BLUE)[INFO]$(NC) Deploying to staging environment..."
	./helm/install.sh install -e staging -n $(STAGING_NAMESPACE) -r $(RELEASE_NAME)-staging --create-namespace --wait --atomic
	@echo "$(GREEN)[SUCCESS]$(NC) Deployed to staging environment"

upgrade-staging: push ## Upgrade staging deployment
	@echo "$(BLUE)[INFO]$(NC) Upgrading staging deployment..."
	./helm/install.sh upgrade -e staging -n $(STAGING_NAMESPACE) -r $(RELEASE_NAME)-staging --wait --atomic
	@echo "$(GREEN)[SUCCESS]$(NC) Staging deployment upgraded"

undeploy-staging: ## Remove staging deployment
	@echo "$(BLUE)[INFO]$(NC) Removing staging deployment..."
	./helm/install.sh uninstall -n $(STAGING_NAMESPACE) -r $(RELEASE_NAME)-staging
	@echo "$(GREEN)[SUCCESS]$(NC) Staging deployment removed"

# Production environment
deploy-prod: check-prerequisites helm-dependency push ## Deploy to production environment
	@echo "$(YELLOW)[WARNING]$(NC) Deploying to PRODUCTION environment"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "$(BLUE)[INFO]$(NC) Deploying to production environment..."
	./helm/install.sh install -e production -n $(PROD_NAMESPACE) -r $(RELEASE_NAME) --create-namespace --wait --atomic
	@echo "$(GREEN)[SUCCESS]$(NC) Deployed to production environment"

upgrade-prod: push ## Upgrade production deployment
	@echo "$(YELLOW)[WARNING]$(NC) Upgrading PRODUCTION deployment"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "$(BLUE)[INFO]$(NC) Upgrading production deployment..."
	./helm/install.sh upgrade -e production -n $(PROD_NAMESPACE) -r $(RELEASE_NAME) --wait --atomic
	@echo "$(GREEN)[SUCCESS]$(NC) Production deployment upgraded"

undeploy-prod: ## Remove production deployment
	@echo "$(RED)[DANGER]$(NC) Removing PRODUCTION deployment"
	@read -p "Are you ABSOLUTELY sure? Type 'DELETE' to confirm: " confirm && [ "$$confirm" = "DELETE" ] || exit 1
	./helm/install.sh uninstall -n $(PROD_NAMESPACE) -r $(RELEASE_NAME)
	@echo "$(GREEN)[SUCCESS]$(NC) Production deployment removed"

# Status and monitoring
status-dev: ## Show development environment status
	@echo "$(BLUE)[INFO]$(NC) Development environment status:"
	./helm/install.sh status -n $(DEV_NAMESPACE) -r $(RELEASE_NAME)-dev

status-staging: ## Show staging environment status
	@echo "$(BLUE)[INFO]$(NC) Staging environment status:"
	./helm/install.sh status -n $(STAGING_NAMESPACE) -r $(RELEASE_NAME)-staging

status-prod: ## Show production environment status
	@echo "$(BLUE)[INFO]$(NC) Production environment status:"
	./helm/install.sh status -n $(PROD_NAMESPACE) -r $(RELEASE_NAME)

status-all: status-dev status-staging status-prod ## Show all environments status

logs-dev: ## Show development logs
	@echo "$(BLUE)[INFO]$(NC) Development logs:"
	kubectl logs -n $(DEV_NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME)-dev --tail=100 -f

logs-staging: ## Show staging logs
	@echo "$(BLUE)[INFO]$(NC) Staging logs:"
	kubectl logs -n $(STAGING_NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME)-staging --tail=100 -f

logs-prod: ## Show production logs
	@echo "$(BLUE)[INFO]$(NC) Production logs:"
	kubectl logs -n $(PROD_NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME) --tail=100 -f

# Testing
test-dev: ## Run tests in development environment
	@echo "$(BLUE)[INFO]$(NC) Running tests in development environment..."
	./helm/install.sh test -n $(DEV_NAMESPACE) -r $(RELEASE_NAME)-dev

test-staging: ## Run tests in staging environment
	@echo "$(BLUE)[INFO]$(NC) Running tests in staging environment..."
	./helm/install.sh test -n $(STAGING_NAMESPACE) -r $(RELEASE_NAME)-staging

test-prod: ## Run tests in production environment
	@echo "$(BLUE)[INFO]$(NC) Running tests in production environment..."
	./helm/install.sh test -n $(PROD_NAMESPACE) -r $(RELEASE_NAME)

# Validation and linting
validate: helm-lint ## Validate all configurations
	@echo "$(BLUE)[INFO]$(NC) Validating Kubernetes manifests..."
	kubectl apply --dry-run=client -f kubernetes/production/
	@echo "$(BLUE)[INFO]$(NC) Validating Helm templates..."
	helm template $(RELEASE_NAME) $(CHART_PATH) --namespace $(NAMESPACE) | kubectl apply --dry-run=client -f -
	@echo "$(GREEN)[SUCCESS]$(NC) All configurations validated"

lint: helm-lint ## Lint all configurations
	@echo "$(BLUE)[INFO]$(NC) Linting Docker files..."
	@command -v hadolint >/dev/null 2>&1 && hadolint docker/Dockerfile || echo "$(YELLOW)[WARNING]$(NC) hadolint not installed, skipping Dockerfile linting"
	@echo "$(GREEN)[SUCCESS]$(NC) Linting completed"

# Cleanup
clean: ## Clean up local Docker images
	@echo "$(BLUE)[INFO]$(NC) Cleaning up local Docker images..."
	docker rmi $(IMAGE_NAME):$(IMAGE_TAG) $(IMAGE_NAME):latest || true
	docker rmi $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):latest || true
	docker system prune -f
	@echo "$(GREEN)[SUCCESS]$(NC) Cleanup completed"

clean-all: clean ## Clean up everything including Helm releases
	@echo "$(YELLOW)[WARNING]$(NC) This will remove all deployments and clean Docker images"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	$(MAKE) undeploy-dev || true
	$(MAKE) undeploy-staging || true
	@echo "$(GREEN)[SUCCESS]$(NC) Full cleanup completed"

# Rollback
rollback-dev: ## Rollback development deployment
	@echo "$(BLUE)[INFO]$(NC) Rolling back development deployment..."
	./helm/install.sh rollback -n $(DEV_NAMESPACE) -r $(RELEASE_NAME)-dev

rollback-staging: ## Rollback staging deployment
	@echo "$(BLUE)[INFO]$(NC) Rolling back staging deployment..."
	./helm/install.sh rollback -n $(STAGING_NAMESPACE) -r $(RELEASE_NAME)-staging

rollback-prod: ## Rollback production deployment
	@echo "$(YELLOW)[WARNING]$(NC) Rolling back PRODUCTION deployment"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	./helm/install.sh rollback -n $(PROD_NAMESPACE) -r $(RELEASE_NAME)

# Port forwarding for local access
port-forward-dev: ## Port forward development service
	@echo "$(BLUE)[INFO]$(NC) Port forwarding development service to localhost:8080..."
	kubectl port-forward -n $(DEV_NAMESPACE) svc/$(RELEASE_NAME)-dev-smc-trading-agent 8080:80

port-forward-staging: ## Port forward staging service
	@echo "$(BLUE)[INFO]$(NC) Port forwarding staging service to localhost:8080..."
	kubectl port-forward -n $(STAGING_NAMESPACE) svc/$(RELEASE_NAME)-staging-smc-trading-agent 8080:80

port-forward-prod: ## Port forward production service
	@echo "$(BLUE)[INFO]$(NC) Port forwarding production service to localhost:8080..."
	kubectl port-forward -n $(PROD_NAMESPACE) svc/$(RELEASE_NAME)-smc-trading-agent 8080:80

# Quick deployment shortcuts
quick-dev: build-dev deploy-dev ## Quick development deployment (build + deploy)

quick-staging: build push deploy-staging ## Quick staging deployment (build + push + deploy)

quick-prod: build push deploy-prod ## Quick production deployment (build + push + deploy)

# CI/CD helpers
ci-build: ## CI build target
	@echo "$(BLUE)[INFO]$(NC) CI: Building Docker image..."
	docker build -t $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG) -f docker/Dockerfile .
	docker tag $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):latest

ci-push: ## CI push target
	@echo "$(BLUE)[INFO]$(NC) CI: Pushing Docker image..."
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):latest

ci-deploy-staging: ## CI staging deployment
	@echo "$(BLUE)[INFO]$(NC) CI: Deploying to staging..."
	./helm/install.sh upgrade -e staging -n $(STAGING_NAMESPACE) -r $(RELEASE_NAME)-staging --wait --atomic --create-namespace

ci-deploy-prod: ## CI production deployment
	@echo "$(BLUE)[INFO]$(NC) CI: Deploying to production..."
	./helm/install.sh upgrade -e production -n $(PROD_NAMESPACE) -r $(RELEASE_NAME) --wait --atomic --create-namespace

# Information targets
info: ## Show deployment information
	@echo "$(BLUE)SMC Trading Agent Deployment Information$(NC)"
	@echo ""
	@echo "Configuration:"
	@echo "  Image: $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"
	@echo "  Chart: $(CHART_PATH)"
	@echo ""
	@echo "Environments:"
	@echo "  Development: $(DEV_NAMESPACE)/$(RELEASE_NAME)-dev"
	@echo "  Staging:     $(STAGING_NAMESPACE)/$(RELEASE_NAME)-staging"
	@echo "  Production:  $(PROD_NAMESPACE)/$(RELEASE_NAME)"
	@echo ""
	@echo "Quick commands:"
	@echo "  make quick-dev      # Build and deploy to development"
	@echo "  make quick-staging  # Build, push and deploy to staging"
	@echo "  make status-all     # Show all environments status"
	@echo "  make logs-prod      # Show production logs"

version: ## Show version information
	@echo "SMC Trading Agent Deployment"
	@echo "Git commit: $(IMAGE_TAG)"
	@echo "Registry: $(REGISTRY)"
	@echo "Image: $(IMAGE_NAME):$(IMAGE_TAG)"