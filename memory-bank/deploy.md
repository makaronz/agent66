# Deployment & Environments: SMC Trading Agent

## 1. Environments

- **`development`**: Local machine setup using Docker Compose. For active development and feature branching.
- **`staging`**: A production-like environment running on Kubernetes. Used for testing new features with live data (in paper trading mode) before deploying to production.
- **`production`**: The live trading environment, also on Kubernetes. This environment handles real capital and is subject to strict monitoring and change control.

## 2. CI/CD Pipeline

- **Provider:** GitHub Actions
- **Pipeline Triggers:** On push to `main` (deploys to staging) and on git tag (deploys to production).
- **Pipeline Stages:**
    1.  **Lint & Format:** Check code quality.
    2.  **Unit & Integration Tests:** Run the test suite.
    3.  **Build Docker Images:** Create and tag new images for each service.
    4.  **Push to Registry:** Push images to a container registry (e.g., Docker Hub, GCR).
    5.  **Deploy to Kubernetes:** Apply the updated Kubernetes manifests to the target environment.

## 3. Secrets Management

- **Strategy:** Use a dedicated secrets manager like HashiCorp Vault or AWS Secrets Manager.
- **Process:** Kubernetes pods will fetch secrets (API keys, database credentials) at runtime. Secrets are **never** stored in git. For local development, secrets are loaded from an untracked `.env` file.

