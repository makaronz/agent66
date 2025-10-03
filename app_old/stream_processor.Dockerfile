# Multi-stage build for Kafka Streams processor
FROM python:3.10-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.10-slim

# Create non-root user
RUN groupadd -r streamprocessor && useradd -r -g streamprocessor streamprocessor

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/streamprocessor/.local

# Copy application code
COPY data_pipeline/ ./data_pipeline/
COPY config_loader.py ./
COPY config_validator.py ./
COPY error_handlers.py ./
COPY service_manager.py ./
COPY health_monitor.py ./

# Copy stream processor specific files
COPY stream_processor_main.py ./

# Create necessary directories
RUN mkdir -p /app/logs /app/config && \
    chown -R streamprocessor:streamprocessor /app

# Switch to non-root user
USER streamprocessor

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/home/streamprocessor/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Expose ports
EXPOSE 8080 8081

# Run the stream processor
CMD ["python", "stream_processor_main.py"]