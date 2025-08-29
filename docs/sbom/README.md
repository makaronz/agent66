# SBOM & Security Scan Results

This directory contains Software Bill of Materials (SBOM) files and security scan results for the SMC Trading Agent project.

## Files Generated

- `python.sbom.json` - CycloneDX SBOM for Python dependencies
- `node.sbom.json` - CycloneDX SBOM for Node.js dependencies
- `trivy_scan.json` - Trivy vulnerability scan results
- `security_report_*.json` - Comprehensive security reports by date/time

## Usage

### Generate SBOM Files

```bash
npm run sbom:generate
```

### Security Scans

```bash
# Full security scan
npm run security:scan

# Quick security check
npm run security:check  

# Generate security report
npm run security:report
```

## Important Notes

- SBOM files should be regenerated after dependency updates
- Security scans should be run as part of CI/CD pipeline
- Critical vulnerabilities will block builds by default
- See `config/security_policy.yaml` for policy configuration