# SMC Trading Agent Security Guide

This comprehensive security guide covers all aspects of securing your SMC Trading Agent deployment, from API key management to production hardening.

## Table of Contents

1. [Security Overview](#security-overview)
2. [API Key Security](#api-key-security)
3. [System Security](#system-security)
4. [Network Security](#network-security)
5. [Data Protection](#data-protection)
6. [Access Control](#access-control)
7. [Monitoring and Auditing](#monitoring-and-auditing)
8. [Security Best Practices](#security-best-practices)
9. [Incident Response](#incident-response)
10. [Compliance Requirements](#compliance-requirements)

## Security Overview

### Threat Model

The SMC Trading Agent faces several security threats:

**External Threats:**
- API key compromise
- Man-in-the-middle attacks
- DDoS attacks
- Phishing attacks
- Exchange breaches

**Internal Threats:**
- Unauthorized access
- Configuration errors
- Insider threats
- Accidental data exposure

**System Threats:**
- Software vulnerabilities
- Infrastructure compromises
- Supply chain attacks
- Zero-day exploits

### Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Security Layers                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │   Network   │ │  Application│ │     Data        │   │
│  │  Security   │ │   Security  │ │   Security      │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│   Firewall  │ │  AuthN/Z    │ │   Encryption    │
│   WAF/IDS   │ │   RBAC      │ │   Access Log    │
└─────────────┘ └─────────────┘ └─────────────────┘
```

## API Key Security

### Exchange API Key Management

**1. Principle of Least Privilege**

For **Paper Trading**:
- Read-only permissions sufficient
- No withdrawal or trading permissions needed

For **Live Trading**:
- Enable only necessary permissions
- Spot trading only (initially)
- No withdrawal permissions
- IP whitelist enabled

**2. API Key Generation**

```bash
# Secure API key generation
openssl rand -base64 32

# Store keys in secure environment
export BINANCE_API_KEY="generated_key_here"
export BINANCE_API_SECRET="generated_secret_here"
```

**3. API Key Storage**

**✅ Secure Methods:**
- Environment variables
- Encrypted configuration files
- Secret management systems (HashiCorp Vault, AWS Secrets Manager)
- Hardware security modules (HSMs)

**❌ Insecure Methods:**
- Plain text in code
- Unencrypted configuration files
- Version control systems
- Shared documents

### API Key Rotation

**Automated Rotation Script:**
```bash
#!/bin/bash
# rotate_api_keys.sh

# Generate new keys
NEW_API_KEY=$(openssl rand -base64 32)
NEW_API_SECRET=$(openssl rand -base64 48)

# Update exchange API
# This requires exchange-specific API calls

# Update application configuration
sed -i "s/OLD_API_KEY/$NEW_API_KEY/g" .env
sed -i "s/OLD_API_SECRET/$NEW_API_SECRET/g" .env

# Restart services with new keys
docker-compose restart

# Log rotation
echo "$(date): API keys rotated" >> /var/log/api-key-rotation.log
```

**Rotation Schedule:**
- **Critical environments**: Every 30 days
- **Production environments**: Every 60-90 days
- **Development environments**: Every 90 days

### API Key Access Controls

**IP Whitelisting:**
```bash
# Add your server IP to exchange whitelist
YOUR_SERVER_IP=$(curl -s ifconfig.me)
echo "Add $YOUR_SERVER_IP to API key IP whitelist"
```

**Rate Limiting:**
```yaml
# config.yaml
api:
  rate_limit:
    requests_per_minute: 60
    burst_size: 10
    ip_whitelist:
      - "your_server_ip"
```

## System Security

### Operating System Hardening

**1. System Updates**
```bash
# Regular security updates
sudo apt update && sudo apt upgrade -y

# Automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

**2. User Management**
```bash
# Create dedicated trading user
sudo useradd -m -s /bin/bash smc-trader
sudo usermod -L smc-trader  # Lock password login

# Use SSH keys only
sudo nano /etc/ssh/sshd_config
# Add: PasswordAuthentication no
sudo systemctl restart ssh
```

**3. File Permissions**
```bash
# Secure configuration files
chmod 600 .env config.yaml
chown smc-trader:smc-trader .env config.yaml

# Secure logs directory
chmod 750 /var/log/smc-agent/
chown smc-trader:adm /var/log/smc-agent/
```

### Container Security

**Docker Security Configuration:**
```yaml
# docker-compose.security.yml
version: '3.8'

services:
  smc-agent:
    build:
      context: .
      dockerfile: Dockerfile.security
    user: "1000:1000"  # Non-root user
    read_only: true  # Read-only filesystem
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
      - /var/log:noexec,nosuid,size=100m
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    security_opt:
      - no-new-privileges:true
    ulimits:
      nproc: 65535
      nofile:
        soft: 20000
        hard: 40000
```

**Secure Dockerfile:**
```dockerfile
# Dockerfile.security
FROM python:3.11-slim as base

# Create non-root user
RUN groupadd -r smc && useradd -r -g smc smc

# Install only necessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set secure working directory
WORKDIR /app
COPY --chown=smc:smc requirements.txt .

# Install dependencies as non-root
USER smc
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=smc:smc . .

# Expose only necessary ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run as non-root user
USER smc
CMD ["python", "main.py"]
```

### Kubernetes Security

**Pod Security Policy:**
```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: smc-agent-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

**Network Policy:**
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: smc-agent-netpol
  namespace: smc-trading
spec:
  podSelector:
    matchLabels:
      app: smc-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS to exchanges
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
```

## Network Security

### Firewall Configuration

**UFW (Uncomplicated Firewall):**
```bash
# Enable firewall
sudo ufw enable

# Default deny all incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (with rate limiting)
sudo ufw limit ssh

# Allow application ports
sudo ufw allow 8000/tcp  # API
sudo ufw allow 3000/tcp  # Frontend
sudo ufw allow from 10.0.0.0/8 to any port 5432  # Database access

# Block known malicious IPs
sudo ufw deny from 192.168.100.0/24
sudo ufw deny from 10.0.0.100
```

**iptables Rules:**
```bash
#!/bin/bash
# iptables-security.sh

# Clear existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH (with rate limiting)
iptables -A INPUT -p tcp --dport 22 -m limit --limit 3/min --limit-burst 3 -j ACCEPT

# Allow application ports
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
iptables -A INPUT -p tcp --dport 3000 -j ACCEPT

# Block suspicious patterns
iptables -A INPUT -p tcp --dport 8000 -m string --string "malicious" --algo bm -j DROP

# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "DROPPED: " --log-level 4

# Save rules
iptables-save > /etc/iptables/rules.v4
```

### SSL/TLS Configuration

**Nginx SSL Configuration:**
```nginx
# nginx-ssl.conf
server {
    listen 443 ssl http2;
    server api.smc-trading.com;

    # SSL certificates
    ssl_certificate /etc/ssl/certs/smc-trading.crt;
    ssl_certificate_key /etc/ssl/private/smc-trading.key;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Other security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name api.smc-trading.com;
    return 301 https://$server_name$request_uri;
}
```

### DDoS Protection

**Rate Limiting Configuration:**
```nginx
# nginx-rate-limit.conf
http {
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

    # Connection limiting
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;

    server {
        # Apply rate limiting to API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_conn conn_limit_per_ip 10;
            proxy_pass http://localhost:8000;
        }

        # Stricter rate limiting for auth
        location /api/auth/ {
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://localhost:8000;
        }
    }
}
```

## Data Protection

### Encryption at Rest

**Database Encryption:**
```sql
-- Enable transparent data encryption (PostgreSQL)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt sensitive data
CREATE TABLE encrypted_api_keys (
    id SERIAL PRIMARY KEY,
    exchange_name VARCHAR(50),
    encrypted_key BYTEA,
    encrypted_secret BYTEA,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Encryption function
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql;
```

**File System Encryption:**
```bash
# Encrypt sensitive configuration files
gpg --symmetric --cipher-algo AES256 .env

# Decrypt when needed
gpg --decrypt .env.gpg > .env
```

### Data in Transit Encryption

**Application TLS Configuration:**
```python
# tls_config.py
import ssl
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Force HTTPS in production
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# SSL context for external API calls
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
```

**Database Connection Security:**
```yaml
# config.yaml
database:
  url: "postgresql://user:pass@localhost:5432/smc_trading?sslmode=require"
  ssl:
    enabled: true
    cert_file: "/etc/ssl/certs/client.crt"
    key_file: "/etc/ssl/private/client.key"
    ca_file: "/etc/ssl/certs/ca.crt"
```

### Data Retention and Deletion

**Data Retention Policy:**
```bash
#!/bin/bash
# data_retention.sh

# Trade data retention (7 years for compliance)
psql -d smc_trading -c "
DELETE FROM trades
WHERE timestamp < NOW() - INTERVAL '7 years';
"

# Log retention (90 days)
find /var/log/smc-agent/ -name "*.log" -mtime +90 -delete

# Temporary data cleanup (24 hours)
find /tmp/ -name "smc-*" -mtime +1 -delete
```

**Secure Data Deletion:**
```bash
# Secure file deletion
shred -vf -n 3 -z sensitive_file.txt

# Database cleanup with secure logging
psql -d smc_trading -c "
DELETE FROM sensitive_data WHERE id = $1;
INSERT INTO audit_log (action, table_name, record_id, timestamp)
VALUES ('DELETE', 'sensitive_data', $1, NOW());
"
```

## Access Control

### Authentication Mechanisms

**JWT Token Configuration:**
```python
# auth.py
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.token_expire_minutes = 30

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token expired")
        except jwt.JWTError:
            raise Exception("Invalid token")
```

**Multi-Factor Authentication:**
```python
# mfa.py
import pyotp
import qrcode
from io import BytesIO

class MFAManager:
    def __init__(self):
        self.issuer = "SMC Trading Agent"

    def generate_secret(self, username: str):
        return pyotp.random_base32()

    def generate_qr_code(self, username: str, secret: str):
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name=self.issuer
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def verify_otp(self, secret: str, token: str):
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
```

### Role-Based Access Control (RBAC)

**RBAC Configuration:**
```yaml
# rbac.yaml
roles:
  admin:
    permissions:
      - "read:*"
      - "write:*"
      - "delete:*"
      - "admin:*"

  trader:
    permissions:
      - "read:trades"
      - "read:positions"
      - "write:trades"
      - "read:market_data"

  analyst:
    permissions:
      - "read:*"
      - "read:analytics"
      - "read:reports"

  viewer:
    permissions:
      - "read:dashboard"
      - "read:positions"
```

**RBAC Implementation:**
```python
# rbac.py
from functools import wraps
from fastapi import HTTPException, Depends

class RBACManager:
    def __init__(self):
        self.roles = self.load_roles()

    def has_permission(self, user_role: str, required_permission: str):
        role_permissions = self.roles.get(user_role, {}).get('permissions', [])
        return required_permission in role_permissions

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not rbac_manager.has_permission(current_user.role, permission):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@require_permission("write:trades")
async def execute_trade(trade_request: TradeRequest):
    # Trade execution logic
    pass
```

### API Rate Limiting

**Redis-based Rate Limiting:**
```python
# rate_limiter.py
import redis
import time
from fastapi import HTTPException

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        current_time = int(time.time())
        window_start = current_time - window

        # Remove old entries
        self.redis.zremrangebyscore(key, 0, window_start)

        # Count current requests
        current_requests = self.redis.zcard(key)

        if current_requests >= limit:
            return False

        # Add current request
        self.redis.zadd(key, {str(current_time): current_time})
        self.redis.expire(key, window)

        return True

    def check_rate_limit(self, key: str, limit: int, window: int):
        if not self.is_allowed(key, limit, window):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(window)}
            )
```

## Monitoring and Auditing

### Security Logging

**Comprehensive Logging Configuration:**
```python
# security_logging.py
import logging
import json
from datetime import datetime

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)

        # Create file handler
        handler = logging.FileHandler('/var/log/smc-agent/security.log')
        handler.setLevel(logging.INFO)

        # Create JSON formatter
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def log_security_event(self, event_type: str, details: dict):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details,
            'source': 'smc-trading-agent'
        }

        self.logger.info(json.dumps(log_entry))

    def log_authentication_attempt(self, username: str, success: bool, ip: str):
        self.log_security_event('authentication', {
            'username': username,
            'success': success,
            'ip_address': ip
        })

    def log_api_access(self, endpoint: str, user_id: str, ip: str, status_code: int):
        self.log_security_event('api_access', {
            'endpoint': endpoint,
            'user_id': user_id,
            'ip_address': ip,
            'status_code': status_code
        })

    def log_trade_execution(self, user_id: str, symbol: str, amount: float):
        self.log_security_event('trade_execution', {
            'user_id': user_id,
            'symbol': symbol,
            'amount': amount
        })
```

**Security Event Monitoring:**
```python
# security_monitor.py
from collections import defaultdict
from datetime import datetime, timedelta

class SecurityMonitor:
    def __init__(self):
        self.failed_login_attempts = defaultdict(list)
        self.api_requests = defaultdict(list)
        self.suspicious_activities = []

    def check_failed_logins(self, username: str, ip: str):
        now = datetime.utcnow()
        self.failed_login_attempts[username].append((now, ip))

        # Clean old attempts (older than 1 hour)
        self.failed_login_attempts[username] = [
            (time, ip_addr) for time, ip_addr in self.failed_login_attempts[username]
            if now - time < timedelta(hours=1)
        ]

        # Check for brute force
        if len(self.failed_login_attempts[username]) >= 5:
            self.trigger_security_alert('brute_force_attempt', {
                'username': username,
                'attempts': len(self.failed_login_attempts[username]),
                'time_window': '1 hour'
            })

    def check_api_abuse(self, user_id: str, endpoint: str):
        now = datetime.utcnow()
        key = f"{user_id}:{endpoint}"
        self.api_requests[key].append(now)

        # Clean old requests (older than 1 minute)
        self.api_requests[key] = [
            time for time in self.api_requests[key]
            if now - time < timedelta(minutes=1)
        ]

        # Check for API abuse
        if len(self.api_requests[key]) >= 100:
            self.trigger_security_alert('api_abuse', {
                'user_id': user_id,
                'endpoint': endpoint,
                'requests_per_minute': len(self.api_requests[key])
            })

    def trigger_security_alert(self, alert_type: str, details: dict):
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': alert_type,
            'details': details,
            'severity': 'high'
        }

        self.suspicious_activities.append(alert)

        # Send notification
        self.send_security_notification(alert)

    def send_security_notification(self, alert: dict):
        # Implement notification logic (email, Slack, etc.)
        pass
```

### Intrusion Detection

**File Integrity Monitoring:**
```bash
#!/bin/bash
# file_integrity_monitor.sh

CONFIG_FILES="/app/config.yaml /app/.env"
HASH_FILE="/var/lib/smc-agent/file_hashes.txt"

# Calculate file hashes
calculate_hashes() {
    for file in $CONFIG_FILES; do
        if [ -f "$file" ]; then
            sha256sum "$file"
        fi
    done
}

# Initialize hash file
if [ ! -f "$HASH_FILE" ]; then
    calculate_hashes > "$HASH_FILE"
    echo "$(date): File integrity baseline created" >> /var/log/smc-agent/security.log
    exit 0
fi

# Check for changes
current_hashes=$(calculate_hashes)
if [ "$current_hashes" != "$(cat "$HASH_FILE")" ]; then
    echo "$(date): FILE INTEGRITY VIOLATION DETECTED" >> /var/log/smc-agent/security.log
    echo "$(date): Current hashes:" >> /var/log/smc-agent/security.log
    echo "$current_hashes" >> /var/log/smc-agent/security.log
    echo "$(date): Expected hashes:" >> /var/log/smc-agent/security.log
    cat "$HASH_FILE" >> /var/log/smc-agent/security.log

    # Send alert
    curl -X POST https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK \
      -H 'Content-type: application/json' \
      --data "{\"text\":\"🚨 File integrity violation detected on SMC Trading Agent\"}"
fi
```

### Audit Trail

**Audit Logging Implementation:**
```python
# audit_trail.py
import json
from datetime import datetime
from typing import Any, Dict

class AuditLogger:
    def __init__(self):
        self.log_file = "/var/log/smc-agent/audit.log"

    def log_action(self, user_id: str, action: str, resource: str, details: Dict[str, Any]):
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'details': details,
            'session_id': self.get_session_id()
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')

    def log_configuration_change(self, user_id: str, config_key: str, old_value: Any, new_value: Any):
        self.log_action(user_id, 'CONFIG_CHANGE', 'system_config', {
            'config_key': config_key,
            'old_value': str(old_value),
            'new_value': str(new_value)
        })

    def log_api_key_access(self, user_id: str, action: str, exchange: str):
        self.log_action(user_id, 'API_KEY_ACCESS', 'exchange_credentials', {
            'action': action,
            'exchange': exchange
        })

    def get_session_id(self):
        # Implement session ID retrieval
        return "session_placeholder"
```

## Security Best Practices

### Development Security

**Secure Coding Practices:**
```python
# secure_coding.py
import hashlib
import secrets
from typing import Optional

class SecurityUtils:
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
        if salt is None:
            salt = secrets.token_hex(16)

        return hashlib.pbkdf2_hex(
            data.encode(),
            salt.encode(),
            100000  # iterations
        )

    @staticmethod
    def sanitize_input(user_input: str) -> str:
        # Basic input sanitization
        import re
        # Remove potentially dangerous characters
        cleaned = re.sub(r'[<>"\']', '', user_input)
        return cleaned.strip()

    @staticmethod
    def validate_sql_input(user_input: str) -> bool:
        # Basic SQL injection protection
        dangerous_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)',
            r'(--|\#|\/\*)',
            r'(\b(OR|AND)\s+\w+\s*=\s*\w+\s*(OR|AND)\s*\w+\s*=\s*\w+)',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return False
        return True
```

**Dependency Security:**
```bash
#!/bin/bash
# dependency_security.sh

# Check for known vulnerabilities
pip-audit

# Check for outdated packages
pip list --outdated

# Run security scanner
bandit -r . -f json -o security-report.json

# Check Docker images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image smc-trading-agent:latest

# Requirements file security check
safety check -r requirements.txt
```

### Operational Security

**Secrets Management:**
```python
# secrets_manager.py
import os
from typing import Optional

class SecretsManager:
    def __init__(self):
        self.vault_url = os.getenv('VAULT_URL')
        self.vault_token = os.getenv('VAULT_TOKEN')

    def get_secret(self, secret_path: str) -> Optional[str]:
        """Retrieve secret from vault or environment"""
        # Try environment variable first
        env_value = os.getenv(secret_path.upper())
        if env_value:
            return env_value

        # Try vault (if configured)
        if self.vault_url and self.vault_token:
            return self.get_from_vault(secret_path)

        return None

    def get_from_vault(self, secret_path: str) -> Optional[str]:
        """Retrieve secret from HashiCorp Vault"""
        import hvac

        client = hvac.Client(url=self.vault_url, token=self.vault_token)
        secret = client.secrets.kv.v2.read_secret_version(path=secret_path)

        if secret and 'data' in secret['data']:
            return secret['data']['data']['value']

        return None

    def rotate_secret(self, secret_path: str) -> str:
        """Rotate secret and update all references"""
        new_secret = self.generate_secure_secret()
        self.store_secret(secret_path, new_secret)
        self.update_applications(secret_path, new_secret)
        return new_secret
```

**Backup Security:**
```bash
#!/bin/bash
# secure_backup.sh

BACKUP_DIR="/secure-backups"
ENCRYPTION_KEY_FILE="/etc/backup/key"

# Create encrypted backup
create_encrypted_backup() {
    local source=$1
    local backup_name=$2

    # Create backup
    tar -czf - "$source" | \
    gpg --symmetric --cipher-algo AES256 \
        --compress-algo 1 \
        --s2k-mode 3 \
        --s2k-digest-algo SHA512 \
        --s2k-count 65536 \
        --passphrase-file "$ENCRYPTION_KEY_FILE" \
        --output "$BACKUP_DIR/$backup_name.gpg"

    echo "$(date): Encrypted backup created: $backup_name.gpg" >> /var/log/backup.log
}

# Verify backup integrity
verify_backup() {
    local backup_file=$1

    if gpg --decrypt --passphrase-file "$ENCRYPTION_KEY_FILE" \
           --output /dev/null "$backup_file" 2>/dev/null; then
        echo "$(date): Backup integrity verified: $backup_file" >> /var/log/backup.log
        return 0
    else
        echo "$(date): Backup integrity FAILED: $backup_file" >> /var/log/backup.log
        return 1
    fi
}

# Daily backup routine
create_encrypted_backup "/app/config" "config_$(date +%Y%m%d)"
create_encrypted_backup "/var/lib/postgresql" "database_$(date +%Y%m%d)"
```

## Incident Response

### Security Incident Response Plan

**Incident Classification:**
- **Critical**: System compromise, data breach, financial loss
- **High**: Service disruption, security control bypass
- **Medium**: Suspicious activity, policy violations
- **Low**: Configuration errors, minor anomalies

**Response Procedures:**
```bash
#!/bin/bash
# incident_response.sh

INCIDENT_TYPE=$1
SEVERITY=$2

case $INCIDENT_TYPE in
    "unauthorized_access")
        echo "🚨 CRITICAL: Unauthorized access detected"

        # Disable compromised accounts
        ./disable_user_accounts.sh

        # Rotate API keys
        ./rotate_all_api_keys.sh

        # Block malicious IPs
        ./block_malicious_ips.sh

        # Enable enhanced monitoring
        ./enable_enhanced_monitoring.sh
        ;;

    "data_breach")
        echo "🚨 CRITICAL: Data breach detected"

        # Isolate affected systems
        ./isolate_systems.sh

        # Preserve evidence
        ./preserve_forensics.sh

        # Notify stakeholders
        ./notify_stakeholders.sh

        # Initiate legal response
        ./initiate_legal_response.sh
        ;;

    "suspicious_activity")
        echo "⚠️ MEDIUM: Suspicious activity detected"

        # Increase monitoring
        ./increase_monitoring.sh

        # Investigate activity
        ./investigate_activity.sh

        # Document findings
        ./document_incident.sh
        ;;
esac
```

### Forensics and Investigation

**Forensic Data Collection:**
```python
# forensics.py
import os
import hashlib
import json
from datetime import datetime

class ForensicCollector:
    def __init__(self):
        self.evidence_dir = "/forensic-evidence"

    def collect_system_state(self, incident_id: str):
        """Collect current system state for forensic analysis"""
        evidence_path = f"{self.evidence_dir}/{incident_id}"
        os.makedirs(evidence_path, exist_ok=True)

        # Collect system information
        self.collect_process_info(evidence_path)
        self.collect_network_connections(evidence_path)
        self.collect_file_hashes(evidence_path)
        self.collect_logs(evidence_path)
        self.collect_memory_dump(evidence_path)

    def collect_process_info(self, evidence_path: str):
        """Collect running process information"""
        with open(f"{evidence_path}/processes.txt", 'w') as f:
            os.system("ps aux >> {}".format(f.name))

    def collect_network_connections(self, evidence_path: str):
        """Collect network connection information"""
        with open(f"{evidence_path}/network_connections.txt", 'w') as f:
            os.system("netstat -tuln >> {}".format(f.name))
            os.system("ss -tuln >> {}".format(f.name))

    def collect_file_hashes(self, evidence_path: str):
        """Collect file hashes for integrity checking"""
        critical_files = [
            "/app/config.yaml",
            "/app/.env",
            "/app/main.py"
        ]

        hash_data = {}
        for file_path in critical_files:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    hash_data[file_path] = file_hash

        with open(f"{evidence_path}/file_hashes.json", 'w') as f:
            json.dump(hash_data, f, indent=2)

    def create_evidence_chain(self, incident_id: str):
        """Create chain of custody for evidence"""
        chain_entry = {
            'incident_id': incident_id,
            'timestamp': datetime.utcnow().isoformat(),
            'collector': os.getenv('USER'),
            'evidence_collected': self.list_evidence(incident_id),
            'hash': self.calculate_evidence_hash(incident_id)
        }

        with open(f"{self.evidence_dir}/{incident_id}/chain_of_custody.json", 'w') as f:
            json.dump(chain_entry, f, indent=2)
```

## Compliance Requirements

### Financial Regulations

**MiFID II Compliance:**
```python
# mifid_compliance.py
from datetime import datetime, timedelta

class MIFIDCompliance:
    def __init__(self):
        self.record_retention_years = 7
        self.transaction_reporting_enabled = True

    def record_trade_execution(self, trade_details: dict):
        """Record trade execution for regulatory reporting"""
        compliant_record = {
            'trade_id': trade_details['trade_id'],
            'timestamp': trade_details['execution_time'],
            'instrument': trade_details['symbol'],
            'venue': trade_details['exchange'],
            'price': trade_details['price'],
            'quantity': trade_details['quantity'],
            'client_id': trade_details['client_id'],
            'execution_algorithm': trade_details.get('algorithm', 'manual'),
            'decision_maker': trade_details.get('decision_maker', 'system'),
            'record_timestamp': datetime.utcnow().isoformat()
        }

        self.store_compliant_record(compliant_record)

    def generate_regulatory_report(self, start_date: datetime, end_date: datetime):
        """Generate MiFID II compliant transaction report"""
        trades = self.get_trades_in_period(start_date, end_date)

        report = {
            'reporting_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_trades': len(trades),
            'total_volume': sum(trade['quantity'] for trade in trades),
            'total_value': sum(trade['price'] * trade['quantity'] for trade in trades),
            'trade_details': trades
        }

        return report

    def ensure_data_retention(self):
        """Ensure compliance with data retention requirements"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.record_retention_years * 365)

        # Archive old data but don't delete
        self.archive_data_before(cutoff_date)
```

### Data Privacy (GDPR)

**Privacy Compliance Implementation:**
```python
# gdpr_compliance.py
from datetime import datetime, timedelta
import hashlib

class GDPRCompliance:
    def __init__(self):
        self.data_retention_days = 2555  # 7 years
        self.anonymization_enabled = True

    def anonymize_user_data(self, user_id: str):
        """Anonymize user data in compliance with GDPR"""
        # Generate anonymous identifier
        anonymous_id = hashlib.sha256(f"{user_id}{datetime.utcnow()}".encode()).hexdigest()[:16]

        # Update all user references
        self.anonymize_trading_records(user_id, anonymous_id)
        self.anonymize_login_records(user_id, anonymous_id)
        self.anonymize_audit_logs(user_id, anonymous_id)

        return anonymous_id

    def handle_data_subject_request(self, user_id: str, request_type: str):
        """Handle GDPR data subject requests"""
        if request_type == "access":
            return self.export_user_data(user_id)
        elif request_type == "deletion":
            return self.delete_user_data(user_id)
        elif request_type == "rectification":
            return self.rectify_user_data(user_id)
        else:
            raise ValueError("Invalid request type")

    def export_user_data(self, user_id: str):
        """Export all user data in machine-readable format"""
        user_data = {
            'personal_information': self.get_user_personal_info(user_id),
            'trading_history': self.get_user_trades(user_id),
            'account_activity': self.get_user_activity_log(user_id),
            'communications': self.get_user_communications(user_id),
            'export_timestamp': datetime.utcnow().isoformat()
        }

        return user_data

    def delete_user_data(self, user_id: str):
        """Delete user data in compliance with right to be forgotten"""
        # Check for legal holds
        if self.has_legal_hold(user_id):
            raise Exception("Cannot delete data due to legal hold")

        # Anonymize instead of delete where required by law
        self.anonymize_user_data(user_id)

        # Delete non-essential data
        self.delete_user_preferences(user_id)
        self.delete_user_sessions(user_id)
```

---

This security guide provides comprehensive coverage of security considerations for the SMC Trading Agent. Regular security audits, updates, and training are essential to maintain a secure trading environment. Remember that security is an ongoing process, not a one-time implementation.