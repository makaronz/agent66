I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

### Observations

The SMC Trading Agent repository is a sophisticated multi-language trading system with no existing SBOM generation or systematic vulnerability scanning. The project has a well-established tools/ directory with existing security scripts, uses npm for package management despite having pnpm-lock.yaml, and has comprehensive Dockerfile configurations for containerized deployments. The existing maintenance runbooks reference Trivy scanning but lack implementation. The project structure supports easy integration of new security tooling without disrupting existing workflows.

### Approach

I will implement a comprehensive SBOM generation and vulnerability scanning system using CycloneDX for both Python and Node.js components, integrated with Trivy security scanning. The solution will create automated scripts for SBOM generation, configure Trivy for filesystem and SBOM analysis, establish vulnerability reporting with critical CVE blocking policies, and integrate seamlessly with the existing development workflow. The implementation will leverage the existing tools/ directory structure and npm scripts, ensuring minimal disruption to current development practices while providing robust security scanning capabilities.

### Reasoning

I explored the repository structure to understand the multi-language codebase with Python backend, Node.js API, and React frontend components. I examined the dependency files (`requirements.txt`, `package.json`, `pnpm-lock.yaml`) to understand the current dependency landscape. I searched for existing SBOM and security scanning implementations and found references to Trivy in maintenance runbooks but no existing SBOM generation. I reviewed the existing security tooling in the tools/ directory, examined Dockerfiles for build context understanding, and confirmed the project uses npm scripts for workflow automation despite having pnpm-lock.yaml present.

## Mermaid Diagram

sequenceDiagram
    participant Dev as Developer
    participant Scripts as SBOM/Security Scripts
    participant CycloneDX as CycloneDX Tools
    participant Trivy as Trivy Scanner
    participant Policy as Security Policy Engine
    participant Reports as Report Generator

    Dev->>Scripts: npm run sbom:generate
    Scripts->>CycloneDX: Generate Python SBOM (cyclonedx-bom)
    CycloneDX-->>Scripts: python.sbom.json
    Scripts->>CycloneDX: Generate Node.js SBOM (@cyclonedx/cdxgen)
    CycloneDX-->>Scripts: node.sbom.json
    
    Dev->>Scripts: npm run security:scan
    Scripts->>Trivy: Filesystem scan
    Trivy-->>Scripts: filesystem_vulnerabilities.json
    Scripts->>Trivy: SBOM scan (Python)
    Trivy-->>Scripts: python_sbom_vulnerabilities.json
    Scripts->>Trivy: SBOM scan (Node.js)
    Trivy-->>Scripts: node_sbom_vulnerabilities.json
    
    Scripts->>Policy: Apply security policies
    Policy->>Policy: Check critical CVE threshold
    Policy->>Policy: Evaluate severity levels
    Policy-->>Scripts: Policy enforcement result
    
    alt Critical vulnerabilities found
        Policy-->>Dev: Build BLOCKED - Critical CVEs detected
        Scripts->>Reports: Generate failure report
    else No critical vulnerabilities
        Policy-->>Dev: Build PASSED - Security check OK
        Scripts->>Reports: Generate success report
    end
    
    Scripts->>Reports: Consolidate all scan results
    Reports-->>Dev: Comprehensive security report

## Proposed File Changes

### smc_trading_agent/tools/generate_sbom.py(NEW)

References: 

- smc_trading_agent/requirements.txt(MODIFY)
- smc_trading_agent/package.json(MODIFY)
- smc_trading_agent/tools/security_test.py

Create comprehensive Python script for generating CycloneDX SBOMs for both Python and Node.js components. The script should use `cyclonedx-bom` for Python dependencies from `requirements.txt` and `@cyclonedx/cdxgen` for Node.js dependencies from `package.json`. Include functionality to detect package manager (npm vs pnpm), handle different output formats (JSON, XML), validate generated SBOMs, and provide detailed logging. Support command-line arguments for output directory, format selection, and component filtering. Integrate with existing project structure by reading from standard dependency files and outputting to `docs/sbom/` directory.

### smc_trading_agent/tools/scan_vulnerabilities.py(NEW)

References: 

- smc_trading_agent/tools/security_test.py
- smc_trading_agent/smc_agent.Dockerfile(MODIFY)
- smc_trading_agent/data_pipeline.Dockerfile(MODIFY)

Create Python script for comprehensive vulnerability scanning using Trivy. Implement filesystem scanning for the entire codebase, SBOM-based scanning for generated SBOMs, and container image scanning for Docker builds. Include functionality to parse Trivy JSON output, categorize vulnerabilities by severity, generate human-readable reports, and implement critical CVE blocking logic. Support multiple output formats (JSON, table, SARIF) and integrate with existing security reporting patterns from `tools/security_test.py`. Include configuration for severity thresholds, allowlists for known false positives, and integration with CI/CD pipeline requirements.

### smc_trading_agent/tools/security_policy.py(NEW)

References: 

- smc_trading_agent/tools/security_test.py

Create security policy enforcement script that implements critical CVE blocking policies and vulnerability reporting standards. Define severity thresholds for build failures (CRITICAL vulnerabilities block builds, HIGH vulnerabilities generate warnings), implement allowlist management for accepted risks, and create standardized reporting formats. Include functionality to parse vulnerability scan results, apply policy rules, generate compliance reports, and integrate with existing development workflow. Support configuration via YAML files and environment variables for different deployment environments (development, staging, production).

### smc_trading_agent/tools/sbom_workflow.sh(NEW)

References: 

- smc_trading_agent/package.json(MODIFY)

Create comprehensive bash script that orchestrates the complete SBOM generation and vulnerability scanning workflow. The script should execute SBOM generation for both Python and Node.js components, run Trivy scans on filesystem and generated SBOMs, apply security policies, generate consolidated reports, and handle error conditions gracefully. Include functionality for cleanup of temporary files, logging of all operations, and integration with existing npm scripts. Support command-line flags for different scan types (quick, full, container-only) and output verbosity levels.

### smc_trading_agent/config/trivy.yaml(NEW)

References: 

- smc_trading_agent/smc_agent.Dockerfile(MODIFY)
- smc_trading_agent/data_pipeline.Dockerfile(MODIFY)

Create Trivy configuration file defining scanning policies, severity thresholds, and output formats. Configure filesystem scanning to exclude test files and build artifacts, set up SBOM scanning parameters, define container scanning policies for Docker images, and specify vulnerability database update settings. Include configuration for custom security policies, allowlists for known false positives, and integration with different scanning modes (CI/CD, local development, production). Set up output formatting for JSON, table, and SARIF formats to support different use cases.

### smc_trading_agent/config/security_policy.yaml(NEW)

Create security policy configuration file defining vulnerability handling rules, severity thresholds, and compliance requirements. Specify critical CVE blocking policies (any CRITICAL severity vulnerability fails the build), define warning thresholds for HIGH and MEDIUM vulnerabilities, configure allowlists for accepted risks, and set up reporting requirements. Include configuration for different environments (development allows more warnings, production has stricter policies), define SLA requirements for vulnerability remediation, and specify integration points with existing security tools and processes.

### smc_trading_agent/docs/sbom(NEW)

Create directory structure for SBOM artifacts and vulnerability reports. This directory will contain generated SBOM files (python.sbom.json, node.sbom.json), vulnerability scan results (filesystem_scan.json, sbom_scan_results.json), and consolidated security reports. Include subdirectories for different artifact types and implement proper .gitignore patterns to handle sensitive security information appropriately.

### smc_trading_agent/docs/sbom/README.md(NEW)

References: 

- smc_trading_agent/tools/security_test.py

Create comprehensive documentation for SBOM generation and vulnerability scanning processes. Document the complete workflow from SBOM generation through vulnerability scanning to policy enforcement, provide usage examples for all scripts and tools, explain security policy configuration, and include troubleshooting guides. Cover integration with development workflow, CI/CD pipeline requirements, and compliance reporting. Include examples of interpreting scan results, managing allowlists, and responding to critical vulnerabilities.

### smc_trading_agent/package.json(MODIFY)

Add new npm scripts for SBOM generation and vulnerability scanning to integrate with existing development workflow. Add scripts for `sbom:generate` (generate SBOMs for all components), `security:scan` (run complete vulnerability scanning), `security:check` (quick security check for development), and `security:report` (generate comprehensive security reports). Integrate these scripts with existing build and development workflows, ensuring they can be run independently or as part of larger processes. Add dependencies for `@cyclonedx/cdxgen` in devDependencies section to support Node.js SBOM generation.

### smc_trading_agent/requirements.txt(MODIFY)

Add `cyclonedx-bom` package to requirements.txt to support Python SBOM generation. Include the package in the development tools section with appropriate version pinning to ensure consistent SBOM generation across different environments. Add comments explaining the purpose of the package and its role in the security scanning workflow.

### smc_trading_agent/.gitignore(MODIFY)

Add appropriate .gitignore entries for SBOM and security scanning artifacts. Include patterns for generated SBOM files (*.sbom.json, *.sbom.xml), vulnerability scan results (vuln_*.json, scan_results_*), temporary security files, and Trivy cache directories. Ensure sensitive security information is not accidentally committed while allowing important reports to be tracked when appropriate. Add comments explaining the security-related ignore patterns.

### smc_trading_agent/smc_agent.Dockerfile(MODIFY)

References: 

- smc_trading_agent/requirements.txt(MODIFY)

Enhance Dockerfile to support SBOM generation during container builds. Add installation of `cyclonedx-bom` package during the pip install phase, include Trivy installation for container-based scanning, and add labels with SBOM metadata for container image identification. Create multi-stage build support where SBOM generation can be performed in a separate stage, and add health checks that include security scanning status. Ensure the container can generate its own SBOM and perform self-scanning when required.

### smc_trading_agent/data_pipeline.Dockerfile(MODIFY)

References: 

- smc_trading_agent/requirements.txt(MODIFY)

Enhance data pipeline Dockerfile to support SBOM generation and vulnerability scanning. Add installation of security scanning tools (`cyclonedx-bom`, Trivy), include SBOM generation capabilities, and add container labels for security metadata. Implement multi-stage build pattern where security scanning can be performed during build process, and add health checks that include security posture validation. Ensure the data pipeline container can generate and validate its own security artifacts.

### smc_trading_agent/tools/install_security_tools.sh(NEW)

Create installation script for all required security scanning tools including Trivy, CycloneDX tools, and supporting utilities. The script should detect the operating system (Linux, macOS, Windows), install Trivy using appropriate package managers or direct downloads, install Python and Node.js SBOM generation tools, and verify all installations. Include functionality to update existing tools, check for required dependencies, and provide detailed installation logs. Support both system-wide and local installation modes for different development environments.

### smc_trading_agent/docs/security/vulnerability_response_playbook.md(NEW)

References: 

- smc_trading_agent/docs/operations/runbooks/maintenance.md

Create comprehensive playbook for responding to vulnerability scan results and critical CVE discoveries. Document step-by-step procedures for handling different severity levels of vulnerabilities, define escalation paths for critical issues, provide templates for vulnerability assessment reports, and include remediation timelines and SLA requirements. Cover communication protocols for security incidents, integration with existing incident response procedures from `docs/operations/runbooks/`, and compliance reporting requirements. Include examples of vulnerability triage, risk assessment, and remediation tracking.