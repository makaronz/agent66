# Multi-stage build for SBOM generation and security scanning
FROM python:3.10-slim AS build-stage

# Set the working directory in the container
WORKDIR /app

# Install system dependencies including Trivy
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Trivy security scanner
RUN wget -qO - https://aquasec.github.io/trivy-repo/deb/public.key | apt-key add - \
    && echo "deb https://aquasec.github.io/trivy-repo/deb generic main" | tee -a /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y trivy \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY ./requirements.txt /app/

# Install any needed packages specified in requirements.txt including cyclonedx-bom
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir cyclonedx-bom

# Copy the rest of the application's code into the container at /app
COPY . /app/

# Copy security configuration and tools
COPY config/ /app/config/
COPY tools/ /app/tools/

# Generate SBOM for Python dependencies during build
RUN mkdir -p /app/docs/sbom && \
    python tools/generate_sbom.py --output-dir /app/docs/sbom --format json

# Production stage
FROM python:3.10-slim

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup -m appuser

# Set the working directory in the container
WORKDIR /app

# Copy requirements file
COPY ./requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Copy security artifacts from build stage
COPY --from=build-stage /app/docs/sbom/ /app/docs/sbom/
COPY --from=build-stage /app/config/ /app/config/
COPY --from=build-stage /app/tools/ /app/tools/

# Set container labels for SBOM metadata
LABEL sbom.generator="cyclonedx-bom" \
      sbom.format="CycloneDX" \
      sbom.version="1.5" \
      security.scanner="trivy" \
      maintainer="SMC Trading Agent Team"

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check with security scanning status
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/docs/sbom/python.sbom.json') else 1)"

# Define the command to run the application
CMD ["python", "main.py"]

