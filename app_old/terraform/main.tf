# Main Terraform configuration for SMC Trading Agent infrastructure
terraform {
  required_version = ">= 1.6"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state configuration
  backend "s3" {
    bucket         = "smc-trading-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "smc-trading-terraform-locks"
    
    # Workspace-specific state files
    workspace_key_prefix = "env"
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "smc-trading-agent"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "smc-trading-team"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  cluster_name = "${var.project_name}-${var.environment}"
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = "smc-trading-team"
  }
  
  # Network configuration
  vpc_cidr = var.vpc_cidr
  azs      = slice(data.aws_availability_zones.available.names, 0, 3)
  
  private_subnets = [
    cidrsubnet(local.vpc_cidr, 8, 1),
    cidrsubnet(local.vpc_cidr, 8, 2),
    cidrsubnet(local.vpc_cidr, 8, 3),
  ]
  
  public_subnets = [
    cidrsubnet(local.vpc_cidr, 8, 101),
    cidrsubnet(local.vpc_cidr, 8, 102),
    cidrsubnet(local.vpc_cidr, 8, 103),
  ]
  
  database_subnets = [
    cidrsubnet(local.vpc_cidr, 8, 201),
    cidrsubnet(local.vpc_cidr, 8, 202),
    cidrsubnet(local.vpc_cidr, 8, 203),
  ]
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  name = local.cluster_name
  cidr = local.vpc_cidr
  
  azs              = local.azs
  private_subnets  = local.private_subnets
  public_subnets   = local.public_subnets
  database_subnets = local.database_subnets
  
  enable_nat_gateway   = true
  enable_vpn_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  # Enable VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  
  tags = local.common_tags
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"
  
  cluster_name    = local.cluster_name
  cluster_version = var.kubernetes_version
  
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets
  
  # Cluster endpoint configuration
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
  
  # Cluster logging
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  
  # Node groups
  node_groups = var.node_groups
  
  # Add-ons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
  
  tags = local.common_tags
}

# RDS Database Module
module "rds" {
  source = "./modules/rds"
  
  identifier = "${local.cluster_name}-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.db_instance_class
  
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_encrypted     = true
  
  db_name  = var.db_name
  username = var.db_username
  
  vpc_security_group_ids = [module.security_groups.rds_security_group_id]
  db_subnet_group_name   = module.vpc.database_subnet_group
  
  backup_retention_period = var.db_backup_retention_period
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  # Enable enhanced monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_enhanced_monitoring.arn
  
  # Enable performance insights
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  
  deletion_protection = var.environment == "production" ? true : false
  
  tags = local.common_tags
}

# ElastiCache Redis Module
module "redis" {
  source = "./modules/redis"
  
  cluster_id = "${local.cluster_name}-redis"
  
  node_type               = var.redis_node_type
  num_cache_nodes         = var.redis_num_cache_nodes
  parameter_group_name    = "default.redis7"
  port                    = 6379
  
  subnet_group_name       = module.vpc.elasticache_subnet_group_name
  security_group_ids      = [module.security_groups.redis_security_group_id]
  
  # Enable encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  # Backup configuration
  snapshot_retention_limit = 5
  snapshot_window         = "03:00-05:00"
  
  tags = local.common_tags
}

# Security Groups Module
module "security_groups" {
  source = "./modules/security-groups"
  
  name_prefix = local.cluster_name
  vpc_id      = module.vpc.vpc_id
  
  # CIDR blocks for access control
  vpc_cidr_block = module.vpc.vpc_cidr_block
  
  tags = local.common_tags
}

# IAM Roles and Policies
module "iam" {
  source = "./modules/iam"
  
  cluster_name = local.cluster_name
  
  tags = local.common_tags
}

# Monitoring and Logging
module "monitoring" {
  source = "./modules/monitoring"
  
  cluster_name = local.cluster_name
  vpc_id       = module.vpc.vpc_id
  
  # CloudWatch configuration
  log_retention_in_days = var.log_retention_in_days
  
  tags = local.common_tags
}

# S3 Buckets for storage
module "s3" {
  source = "./modules/s3"
  
  cluster_name = local.cluster_name
  environment  = var.environment
  
  tags = local.common_tags
}

# RDS Enhanced Monitoring Role
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${local.cluster_name}-rds-enhanced-monitoring"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# Kubernetes provider configuration
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

# Helm provider configuration
provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# Kubernetes resources
module "kubernetes" {
  source = "./modules/kubernetes"
  
  cluster_name = local.cluster_name
  environment  = var.environment
  
  # Dependencies
  depends_on = [
    module.eks,
    module.rds,
    module.redis
  ]
}