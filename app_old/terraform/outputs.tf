# Outputs for SMC Trading Agent infrastructure

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "database_subnets" {
  description = "List of IDs of database subnets"
  value       = module.vpc.database_subnets
}

# EKS Outputs
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_version" {
  description = "The Kubernetes version for the EKS cluster"
  value       = module.eks.cluster_version
}

output "cluster_platform_version" {
  description = "Platform version for the EKS cluster"
  value       = module.eks.cluster_platform_version
}

output "cluster_status" {
  description = "Status of the EKS cluster"
  value       = module.eks.cluster_status
}

output "node_groups" {
  description = "EKS node groups"
  value       = module.eks.node_groups
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "The ARN of the OIDC Provider if enabled"
  value       = module.eks.oidc_provider_arn
}

# RDS Outputs
output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "db_instance_hosted_zone_id" {
  description = "The hosted zone ID of the DB instance"
  value       = module.rds.db_instance_hosted_zone_id
}

output "db_instance_id" {
  description = "RDS instance ID"
  value       = module.rds.db_instance_id
}

output "db_instance_resource_id" {
  description = "RDS instance resource ID"
  value       = module.rds.db_instance_resource_id
}

output "db_instance_status" {
  description = "RDS instance status"
  value       = module.rds.db_instance_status
}

output "db_instance_name" {
  description = "RDS instance name"
  value       = module.rds.db_instance_name
}

output "db_instance_username" {
  description = "RDS instance root username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "db_subnet_group_id" {
  description = "RDS subnet group ID"
  value       = module.rds.db_subnet_group_id
}

output "db_parameter_group_id" {
  description = "RDS parameter group ID"
  value       = module.rds.db_parameter_group_id
}

# Redis Outputs
output "redis_cluster_id" {
  description = "ElastiCache Redis cluster ID"
  value       = module.redis.cluster_id
}

output "redis_cluster_address" {
  description = "ElastiCache Redis cluster address"
  value       = module.redis.cluster_address
}

output "redis_cluster_configuration_endpoint" {
  description = "ElastiCache Redis cluster configuration endpoint"
  value       = module.redis.cluster_configuration_endpoint
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = module.redis.port
}

# Security Groups Outputs
output "eks_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.security_groups.eks_security_group_id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = module.security_groups.rds_security_group_id
}

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = module.security_groups.redis_security_group_id
}

# IAM Outputs
output "cluster_service_role_arn" {
  description = "EKS cluster service role ARN"
  value       = module.iam.cluster_service_role_arn
}

output "node_group_role_arn" {
  description = "EKS node group role ARN"
  value       = module.iam.node_group_role_arn
}

output "pod_execution_role_arn" {
  description = "Pod execution role ARN"
  value       = module.iam.pod_execution_role_arn
}

# S3 Outputs
output "s3_bucket_backups" {
  description = "S3 bucket for backups"
  value       = module.s3.bucket_backups
}

output "s3_bucket_logs" {
  description = "S3 bucket for logs"
  value       = module.s3.bucket_logs
}

output "s3_bucket_artifacts" {
  description = "S3 bucket for artifacts"
  value       = module.s3.bucket_artifacts
}

# Monitoring Outputs
output "cloudwatch_log_group_cluster" {
  description = "CloudWatch log group for EKS cluster"
  value       = module.monitoring.cloudwatch_log_group_cluster
}

output "cloudwatch_log_group_application" {
  description = "CloudWatch log group for applications"
  value       = module.monitoring.cloudwatch_log_group_application
}

# Connection Information
output "kubectl_config" {
  description = "kubectl config command to connect to the cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_id}"
}

output "database_connection_string" {
  description = "Database connection string (without password)"
  value       = "postgresql://${module.rds.db_instance_username}@${module.rds.db_instance_endpoint}:${module.rds.db_instance_port}/${module.rds.db_instance_name}"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://${module.redis.cluster_address}:${module.redis.port}"
}

# Environment Information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "cluster_name" {
  description = "EKS cluster name"
  value       = local.cluster_name
}

# Cost Information
output "estimated_monthly_cost" {
  description = "Estimated monthly cost (USD) - approximate"
  value = {
    eks_cluster = 73.00  # $0.10/hour
    node_groups = var.node_groups.main.desired_size * 30 * 24 * 0.0464  # t3.medium on-demand
    rds = var.db_instance_class == "db.t3.micro" ? 16.56 : 33.12  # approximate
    redis = var.redis_node_type == "cache.t3.micro" ? 11.52 : 23.04  # approximate
    nat_gateway = 32.40  # $0.045/hour
    data_transfer = 50.00  # estimated
    total_estimated = 73.00 + (var.node_groups.main.desired_size * 30 * 24 * 0.0464) + 16.56 + 11.52 + 32.40 + 50.00
  }
}

# Security Information
output "security_summary" {
  description = "Security configuration summary"
  value = {
    encryption_at_rest = var.enable_encryption
    vpc_flow_logs = var.enable_vpc_flow_logs
    private_subnets = length(module.vpc.private_subnets)
    security_groups = 3
    iam_roles = 3
  }
}