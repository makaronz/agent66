#!/bin/bash

# Setup script for comprehensive audit logging system
# Configures ELK stack, log rotation, and GDPR compliance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOGGING_DIR="$PROJECT_ROOT/deployment/logging"
LOGS_DIR="$PROJECT_ROOT/logs"

# Configuration
ELASTIC_PASSWORD=${ELASTIC_PASSWORD:-$(openssl rand -base64 32)}
KIBANA_ENCRYPTION_KEY=${KIBANA_ENCRYPTION_KEY:-$(openssl rand -base64 32)}
GRAFANA_PASSWORD=${GRAFANA_PASSWORD:-$(openssl rand -base64 16)}

echo "🔧 Setting up comprehensive audit logging system..."

# Create necessary directories
echo "📁 Creating log directories..."
mkdir -p "$LOGS_DIR"/{audit,app,security,compliance}
mkdir -p "$LOGGING_DIR"/{grafana/provisioning/{datasources,dashboards},grafana/dashboards}

# Set proper permissions
chmod 755 "$LOGS_DIR"
chmod 755 "$LOGS_DIR"/{audit,app,security,compliance}

# Create Elasticsearch configuration
echo "⚙️  Creating Elasticsearch configuration..."
cat > "$LOGGING_DIR/elasticsearch.yml" << EOF
cluster.name: smc-trading-cluster
node.name: smc-elasticsearch
path.data: /usr/share/elasticsearch/data
path.logs: /usr/share/elasticsearch/logs
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node

# Security settings
xpack.security.enabled: true
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: false

# Performance settings
bootstrap.memory_lock: true
indices.memory.index_buffer_size: 20%
indices.memory.min_index_buffer_size: 96mb

# Audit logging
xpack.security.audit.enabled: true
xpack.security.audit.logfile.events.include: [
  "access_denied", "access_granted", "anonymous_access_denied",
  "authentication_failed", "authentication_success",
  "change_password", "connection_denied", "connection_granted"
]
EOF

# Create Kibana configuration
echo "⚙️  Creating Kibana configuration..."
cat > "$LOGGING_DIR/kibana.yml" << EOF
server.name: smc-kibana
server.host: 0.0.0.0
server.port: 5601

elasticsearch.hosts: ["http://elasticsearch:9200"]
elasticsearch.username: elastic
elasticsearch.password: ${ELASTIC_PASSWORD}

# Security settings
xpack.security.enabled: true
xpack.encryptedSavedObjects.encryptionKey: ${KIBANA_ENCRYPTION_KEY}

# Logging
logging.appenders:
  file:
    type: file
    fileName: /usr/share/kibana/logs/kibana.log
    layout:
      type: json
logging.root:
  appenders:
    - default
    - file
  level: info

# Monitoring
monitoring.ui.container.elasticsearch.enabled: true
EOF

# Create Filebeat configuration
echo "⚙️  Creating Filebeat configuration..."
cat > "$LOGGING_DIR/filebeat.yml" << EOF
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/smc-trading/audit/*.jsonl
  fields:
    log_type: audit
    service: smc-trading-agent
  fields_under_root: true
  json.keys_under_root: true
  json.add_error_key: true
  multiline.pattern: '^\{'
  multiline.negate: true
  multiline.match: after

- type: log
  enabled: true
  paths:
    - /var/log/smc-trading/app/*.log
  fields:
    log_type: application
    service: smc-trading-agent
  fields_under_root: true
  multiline.pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
  multiline.negate: true
  multiline.match: after

- type: docker
  containers.ids:
    - "*"
  processors:
    - add_docker_metadata:
        host: "unix:///var/run/docker.sock"

output.logstash:
  hosts: ["logstash:5044"]

processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
EOF

# Create Grafana datasource configuration
echo "⚙️  Creating Grafana configuration..."
cat > "$LOGGING_DIR/grafana/provisioning/datasources/elasticsearch.yml" << EOF
apiVersion: 1

datasources:
  - name: Elasticsearch-Audit
    type: elasticsearch
    access: proxy
    url: http://elasticsearch:9200
    database: "smc-trading-audit-*"
    basicAuth: true
    basicAuthUser: elastic
    basicAuthPassword: ${ELASTIC_PASSWORD}
    jsonData:
      interval: Daily
      timeField: "@timestamp"
      esVersion: "8.0.0"
      maxConcurrentShardRequests: 5
      logMessageField: message
      logLevelField: severity
    isDefault: false

  - name: Elasticsearch-Security
    type: elasticsearch
    access: proxy
    url: http://elasticsearch:9200
    database: "smc-trading-security-alerts-*"
    basicAuth: true
    basicAuthUser: elastic
    basicAuthPassword: ${ELASTIC_PASSWORD}
    jsonData:
      interval: Daily
      timeField: "@timestamp"
      esVersion: "8.0.0"
      maxConcurrentShardRequests: 5
      logMessageField: message
      logLevelField: severity
    isDefault: false

  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# Create Grafana dashboard configuration
cat > "$LOGGING_DIR/grafana/provisioning/dashboards/dashboards.yml" << EOF
apiVersion: 1

providers:
  - name: 'SMC Trading Dashboards'
    orgId: 1
    folder: 'SMC Trading'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

# Create basic security dashboard
cat > "$LOGGING_DIR/grafana/dashboards/security-overview.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "SMC Trading - Security Overview",
    "tags": ["security", "audit"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Security Events Over Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(audit_events_total{event_type=~\".*SECURITY.*|.*UNAUTHORIZED.*|.*SUSPICIOUS.*\"}[5m])",
            "legendFormat": "{{event_type}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Failed Login Attempts",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(audit_events_total{event_type=\"LOGIN_FAILURE\"}[1h]))",
            "legendFormat": "Failed Logins"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "High Risk Events",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(audit_events_total{risk_score>=8}[1h]))",
            "legendFormat": "High Risk Events"
          }
        ],
        "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0}
      }
    ],
    "time": {"from": "now-24h", "to": "now"},
    "refresh": "30s"
  }
}
EOF

# Create environment file for ELK stack
echo "🔐 Creating environment configuration..."
cat > "$LOGGING_DIR/.env" << EOF
# Elasticsearch Configuration
ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
ELASTICSEARCH_HOST=elasticsearch:9200
ELASTICSEARCH_USERNAME=elastic

# Kibana Configuration
KIBANA_ENCRYPTION_KEY=${KIBANA_ENCRYPTION_KEY}

# Grafana Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}

# Application Configuration
ENVIRONMENT=${ENVIRONMENT:-production}
APP_VERSION=${APP_VERSION:-1.0.0}
DEBUG_OUTPUT=false

# Alerting Configuration (configure these with actual values)
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}
COMPLIANCE_WEBHOOK_URL=${COMPLIANCE_WEBHOOK_URL:-}
COMPLIANCE_API_TOKEN=${COMPLIANCE_API_TOKEN:-}

# Log Retention
LOG_RETENTION_DAYS=2555  # 7 years for financial compliance
MAX_LOG_SIZE=104857600   # 100MB
EOF

# Create log rotation configuration
echo "📋 Creating log rotation configuration..."
cat > "$LOGS_DIR/logrotate.conf" << EOF
# Log rotation configuration for SMC Trading Agent
# Ensures GDPR compliance and manages disk space

/var/log/smc-trading/audit/*.jsonl {
    daily
    rotate 2555  # 7 years retention
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        # Signal application to reopen log files
        pkill -USR1 -f "smc-trading"
    endscript
}

/var/log/smc-trading/app/*.log {
    daily
    rotate 90  # 90 days retention
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        pkill -USR1 -f "smc-trading"
    endscript
}

/var/log/smc-trading/security/*.log {
    daily
    rotate 730  # 2 years retention
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        pkill -USR1 -f "smc-trading"
    endscript
}
EOF

# Create systemd service for log rotation
if command -v systemctl &> /dev/null; then
    echo "⚙️  Creating systemd service for log rotation..."
    sudo tee /etc/systemd/system/smc-logrotate.service > /dev/null << EOF
[Unit]
Description=SMC Trading Log Rotation
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/sbin/logrotate -f $LOGS_DIR/logrotate.conf
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

    sudo tee /etc/systemd/system/smc-logrotate.timer > /dev/null << EOF
[Unit]
Description=Run SMC Trading log rotation daily
Requires=smc-logrotate.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable smc-logrotate.timer
    sudo systemctl start smc-logrotate.timer
fi

# Create monitoring script
echo "📊 Creating monitoring script..."
cat > "$SCRIPT_DIR/monitor-audit-logs.sh" << 'EOF'
#!/bin/bash

# Monitor audit logs for security events and compliance

LOGS_DIR="${LOGS_DIR:-./logs}"
ALERT_THRESHOLD=10
TIMEFRAME="1 hour ago"

echo "🔍 Monitoring audit logs for security events..."

# Check for failed login attempts
FAILED_LOGINS=$(find "$LOGS_DIR/audit" -name "*.jsonl" -newermt "$TIMEFRAME" -exec grep -l "LOGIN_FAILURE" {} \; | wc -l)
if [ "$FAILED_LOGINS" -gt "$ALERT_THRESHOLD" ]; then
    echo "⚠️  ALERT: $FAILED_LOGINS failed login attempts in the last hour"
fi

# Check for high-risk events
HIGH_RISK=$(find "$LOGS_DIR/audit" -name "*.jsonl" -newermt "$TIMEFRAME" -exec grep -l '"risk_score":[8-9]' {} \; | wc -l)
if [ "$HIGH_RISK" -gt 0 ]; then
    echo "🚨 ALERT: $HIGH_RISK high-risk security events in the last hour"
fi

# Check for unauthorized access attempts
UNAUTHORIZED=$(find "$LOGS_DIR/audit" -name "*.jsonl" -newermt "$TIMEFRAME" -exec grep -l "UNAUTHORIZED_ACCESS" {} \; | wc -l)
if [ "$UNAUTHORIZED" -gt 0 ]; then
    echo "🔒 ALERT: $UNAUTHORIZED unauthorized access attempts in the last hour"
fi

# Check log file sizes
for log_dir in "$LOGS_DIR"/{audit,app,security,compliance}; do
    if [ -d "$log_dir" ]; then
        SIZE=$(du -sh "$log_dir" | cut -f1)
        echo "📁 $log_dir: $SIZE"
    fi
done

echo "✅ Audit log monitoring completed"
EOF

chmod +x "$SCRIPT_DIR/monitor-audit-logs.sh"

# Create backup script
echo "💾 Creating backup script..."
cat > "$SCRIPT_DIR/backup-audit-logs.sh" << 'EOF'
#!/bin/bash

# Backup audit logs for compliance and disaster recovery

LOGS_DIR="${LOGS_DIR:-./logs}"
BACKUP_DIR="${BACKUP_DIR:-./backups/logs}"
RETENTION_DAYS=2555  # 7 years

echo "💾 Creating audit log backups..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/audit-logs-$TIMESTAMP.tar.gz"

# Compress and backup audit logs
tar -czf "$BACKUP_FILE" -C "$LOGS_DIR" audit/

# Encrypt backup (optional - requires GPG key)
if command -v gpg &> /dev/null && [ -n "$GPG_RECIPIENT" ]; then
    gpg --trust-model always --encrypt -r "$GPG_RECIPIENT" "$BACKUP_FILE"
    rm "$BACKUP_FILE"
    BACKUP_FILE="$BACKUP_FILE.gpg"
fi

echo "✅ Backup created: $BACKUP_FILE"

# Clean up old backups
find "$BACKUP_DIR" -name "audit-logs-*.tar.gz*" -mtime +$RETENTION_DAYS -delete

echo "🧹 Old backups cleaned up (retention: $RETENTION_DAYS days)"
EOF

chmod +x "$SCRIPT_DIR/backup-audit-logs.sh"

# Set up cron job for backups
echo "⏰ Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * $SCRIPT_DIR/backup-audit-logs.sh") | crontab -

echo ""
echo "✅ Audit logging system setup completed!"
echo ""
echo "📋 Configuration Summary:"
echo "   - Elasticsearch password: $ELASTIC_PASSWORD"
echo "   - Kibana encryption key: $KIBANA_ENCRYPTION_KEY"
echo "   - Grafana password: $GRAFANA_PASSWORD"
echo "   - Log directory: $LOGS_DIR"
echo "   - Backup directory: $BACKUP_DIR"
echo ""
echo "🚀 Next steps:"
echo "   1. Start the ELK stack: cd $LOGGING_DIR && docker-compose -f docker-compose.elk.yml up -d"
echo "   2. Access Kibana: http://localhost:5601 (elastic/$ELASTIC_PASSWORD)"
echo "   3. Access Grafana: http://localhost:3000 (admin/$GRAFANA_PASSWORD)"
echo "   4. Configure alerting webhooks in $LOGGING_DIR/.env"
echo "   5. Test log monitoring: $SCRIPT_DIR/monitor-audit-logs.sh"
echo ""
echo "🔐 Security Notes:"
echo "   - Store passwords securely (consider using a password manager)"
echo "   - Configure firewall rules for Elasticsearch and Kibana"
echo "   - Set up SSL/TLS certificates for production"
echo "   - Configure backup encryption with GPG keys"
echo "   - Review and customize retention policies"
EOF

chmod +x deployment/scripts/setup-audit-logging.sh