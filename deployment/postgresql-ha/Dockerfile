FROM postgres:15-alpine

# Install Patroni and dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    curl \
    jq \
    && pip3 install --no-cache-dir \
        patroni[etcd3] \
        psycopg2-binary \
    && apk del gcc musl-dev libffi-dev openssl-dev python3-dev

# Create patroni user and directories
RUN adduser -D -s /bin/sh patroni \
    && mkdir -p /var/lib/postgresql/data \
    && mkdir -p /var/log/postgresql \
    && mkdir -p /scripts \
    && chown -R patroni:patroni /var/lib/postgresql \
    && chown -R patroni:patroni /var/log/postgresql

# Copy configuration files
COPY patroni.yml /etc/patroni/patroni.yml
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

# Copy SSL certificates (these should be provided via secrets in production)
COPY ssl/ /etc/ssl/

# Health check script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Expose ports
EXPOSE 5432 8008

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Switch to patroni user
USER patroni

# Start Patroni
CMD ["patroni", "/etc/patroni/patroni.yml"]