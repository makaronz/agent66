# SMC Trading Agent - Terraform Infrastructure

This directory contains the Terraform configuration for deploying the SMC Trading Agent infrastructure on AWS.

## Overview

The infrastructure includes:
- **EKS Kubernetes Cluster** - Container orchestration
- **VPC with Multi-AZ** - Network isolation and high availability
- **RDS PostgreSQL** - Primary database with TimescaleDB extension
- **ElastiCache Redis** - Caching and session storage
- **Security Groups** - Network access control
- **IAM Roles** - Service permissions
- **CloudWatch** - Monitoring and logging
- **S3 Buckets** - Storage for backups and artifacts

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Load Balancer                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    VPC (10.0.0.0/16)                       │
│  ┌─────────────────┬─────────────────┬─────────────────┐    │
│  │   Public AZ-A   │   Public AZ-B   │   Public AZ-C   │    │
│  │  10.0.101.0/24  │  10.0.102.0/24  │  10.0.103.0/24  │    │
│  └─────────────────┼─────────────────┼─────────────────┘    │
│  ┌─────────────────▼─────────────────▼─────────────────┐    │
│  │              EKS Cluster Nodes                      │    │
│  │   Private AZ-A  │   Private AZ-B  │   Private AZ-C  │    │
│  │  10.0.1.0/24    │  10.0.2.0/24    │  10.0.3.0/24    │    │
│  └─────────────────┼─────────────────┼─────────────────┘    │
│  ┌─────────────────▼─────────────────▼─────────────────┐    │
│  │               Database Tier                         │    │
│  │     RDS         │     Redis       │    Backups      │    │
│  │  10.0.201.0/24  │  10.0.202.0/24  │  10.0.203.0/24  │    │
│  └─────────────────┴─────────────────┴─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.6.0
3. **kubectl** for Kubernetes management
4. **Helm** for Kubernetes package management

Optional tools for enhanced validation:
- **tflint** - Terraform linting
- **checkov** - Security scanning
- **terraform-docs** - Documentation generation

## Quick Start

### 1. Initialize Infrastructure

```bash
# Run the initialization script
./scripts/init-terraform.sh

# Or manually:
cd terraform
terraform init
terraform workspace new production  # or dev/staging
```

### 2. Configure Variables

```bash
# Copy and customize the variables file
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

### 3. Plan and Apply

```bash
# Validate configuration
./scripts/validate-terraform.sh

# Plan infrastructure
terraform plan -out=tfplan

# Apply changes
terraform apply tfplan
```

### 4. Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name smc-trading-production

# Verify connection
kubectl get nodes
```

## Configuration

### Environment Variables

```bash
export AWS_REGION="us-west-2"
export PROJECT_NAME="smc-trading"
export ENVIRONMENT="production"
```

### Key Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `aws_region` | AWS region | `us-west-2` | Yes |
| `environment` | Environment name | - | Yes |
| `project_name` | Project name | `smc-trading` | Yes |
| `vpc_cidr` | VPC CIDR block | `10.0.0.0/16` | No |
| `kubernetes_version` | EKS version | `1.28` | No |
| `db_instance_class` | RDS instance type | `db.t3.micro` | No |
| `redis_node_type` | Redis node type | `cache.t3.micro` | No |

### Node Groups

The configuration supports multiple node groups:

```hcl
node_groups = {
  main = {
    instance_types = ["t3.medium"]
    capacity_type  = "ON_DEMAND"
    min_size      = 2
    max_size      = 10
    desired_size  = 3
  }
  
  spot = {
    instance_types = ["t3.medium", "t3.large"]
    capacity_type  = "SPOT"
    min_size      = 0
    max_size      = 20
    desired_size  = 2
  }
}
```

## Environments

### Development
- Minimal resources for cost optimization
- Single AZ deployment acceptable
- Smaller instance types

```bash
terraform workspace select dev
terraform apply -var="environment=dev" -var="db_instance_class=db.t3.micro"
```

### Staging
- Production-like setup
- Multi-AZ for testing
- Moderate resource allocation

```bash
terraform workspace select staging
terraform apply -var="environment=staging" -var="enable_multi_az=true"
```

### Production
- Full high-availability setup
- Multi-AZ deployment
- Enhanced monitoring and backup

```bash
terraform workspace select production
terraform apply -var="environment=production" -var="enable_multi_az=true"
```

## Security

### Network Security
- Private subnets for application workloads
- Public subnets only for load balancers
- Security groups with least privilege access
- VPC Flow Logs enabled

### Data Security
- Encryption at rest for all storage
- Encryption in transit with TLS 1.3
- Secrets managed via AWS Secrets Manager
- Regular automated backups

### Access Control
- IAM roles with minimal required permissions
- Kubernetes RBAC integration
- Network policies for pod-to-pod communication

## Monitoring

### CloudWatch Integration
- EKS cluster logging
- Application log aggregation
- Custom metrics and alarms
- Cost monitoring and alerts

### Prometheus & Grafana
- Deployed via Helm charts
- Custom dashboards for trading metrics
- Alert manager integration
- Long-term metrics storage

## Backup and Recovery

### Automated Backups
- RDS automated backups (7-day retention)
- EBS snapshot lifecycle policies
- S3 cross-region replication
- Kubernetes persistent volume backups

### Disaster Recovery
- Multi-AZ deployment
- Cross-region backup replication
- Infrastructure as Code for rapid rebuild
- Documented recovery procedures

## Cost Optimization

### Estimated Monthly Costs (USD)

| Component | Development | Staging | Production |
|-----------|-------------|---------|------------|
| EKS Cluster | $73 | $73 | $73 |
| EC2 Instances | $50 | $150 | $300 |
| RDS Database | $15 | $50 | $100 |
| ElastiCache | $12 | $25 | $50 |
| NAT Gateway | $32 | $32 | $96 |
| Data Transfer | $20 | $50 | $100 |
| **Total** | **$202** | **$380** | **$719** |

### Cost Optimization Strategies
- Use Spot instances for non-critical workloads
- Right-size instances based on actual usage
- Enable auto-scaling for dynamic workloads
- Use Reserved Instances for predictable workloads

## Troubleshooting

### Common Issues

1. **Terraform State Lock**
   ```bash
   terraform force-unlock <lock-id>
   ```

2. **EKS Node Group Issues**
   ```bash
   # Check node group status
   aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <nodegroup>
   
   # Update node group
   terraform apply -target=module.eks.aws_eks_node_group.main
   ```

3. **Database Connection Issues**
   ```bash
   # Test database connectivity
   kubectl run -it --rm debug --image=postgres:15 --restart=Never -- psql -h <endpoint> -U <username> -d <database>
   ```

### Validation Scripts

```bash
# Validate Terraform configuration
./scripts/validate-terraform.sh

# Check security compliance
checkov -d . --framework terraform

# Format code
terraform fmt -recursive
```

## Maintenance

### Regular Tasks
- Update Terraform provider versions
- Review and rotate secrets
- Update EKS cluster version
- Review security group rules
- Monitor costs and optimize

### Upgrade Procedures
1. Test changes in development environment
2. Apply to staging environment
3. Validate functionality
4. Apply to production during maintenance window
5. Monitor for issues

## Support

### Documentation
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

### Monitoring and Alerts
- CloudWatch dashboards: AWS Console → CloudWatch
- Grafana dashboards: https://monitoring.smc-trading.com/grafana
- Slack alerts: #infrastructure-alerts channel

### Emergency Contacts
- Infrastructure Team: infrastructure@smc-trading.com
- On-call Engineer: +1-XXX-XXX-XXXX
- Escalation: CTO@smc-trading.com

## Contributing

1. Create feature branch
2. Make changes and test locally
3. Run validation scripts
4. Submit pull request
5. Deploy to staging for testing
6. Deploy to production after approval

## License

This infrastructure code is proprietary to SMC Trading Agent project.