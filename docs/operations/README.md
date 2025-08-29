# SMC Trading Agent - Operational Documentation

This directory contains comprehensive operational documentation for the SMC Trading Agent production system.

## Documentation Structure

### 📋 Runbooks

- [Deployment Runbook](./runbooks/deployment.md) - Step-by-step deployment procedures
- [Maintenance Runbook](./runbooks/maintenance.md) - Regular maintenance tasks and procedures
- [Backup and Recovery](./runbooks/backup-recovery.md) - Data backup and disaster recovery procedures

### 🚨 Incident Response

- [Incident Response Playbook](./incident-response/playbook.md) - Critical incident response procedures
- [Emergency Procedures](./incident-response/emergency.md) - Emergency shutdown and failover procedures
- [Escalation Matrix](./incident-response/escalation.md) - Contact information and escalation paths

### 🔧 Troubleshooting

- [Common Issues Guide](./troubleshooting/common-issues.md) - Frequently encountered problems and solutions
- [System Diagnostics](./troubleshooting/diagnostics.md) - Diagnostic commands and health checks
- [Performance Issues](./troubleshooting/performance.md) - Performance troubleshooting guide

### 📚 User Guides

- [User Onboarding Guide](./user-guides/onboarding.md) - New user setup and configuration
- [API Integration Guide](./user-guides/api-integration.md) - API usage examples and best practices
- [Trading Configuration](./user-guides/trading-config.md) - Trading strategy configuration guide

### 🏗️ System Architecture

- [Architecture Overview](./architecture/overview.md) - System architecture and component relationships
- [Data Flow Diagrams](./architecture/data-flow.md) - Data flow and processing pipelines
- [Security Architecture](./architecture/security.md) - Security controls and access patterns

## Quick Reference

### Emergency Contacts

- **On-Call Engineer**: +1-XXX-XXX-XXXX
- **System Administrator**: admin@smc-trading.com
- **Security Team**: security@smc-trading.com

### Critical System URLs

- **Production Dashboard**: https://dashboard.smc-trading.com
- **Monitoring (Grafana)**: https://monitoring.smc-trading.com
- **Status Page**: https://status.smc-trading.com
- **API Documentation**: https://api.smc-trading.com/docs

### Emergency Procedures

1. **System Down**: Follow [Emergency Procedures](./incident-response/emergency.md)
2. **Security Incident**: Contact security team immediately
3. **Data Loss**: Execute [Disaster Recovery](./runbooks/backup-recovery.md)
4. **Trading Halt**: Use emergency trading halt procedures

## Document Maintenance

This documentation is maintained by the DevOps team and should be updated:

- After each major system change
- Following incident post-mortems
- During quarterly documentation reviews
- When new procedures are established

Last Updated: $(date)
Version: 1.0.0
