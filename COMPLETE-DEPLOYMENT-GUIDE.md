# Complete Deployment Guide: GLM 4.6 + Claude Code + Claude-Flow Enterprise Setup

> **Universal Implementation Manual**  
> From Zero to Production-Ready AI Development Environment  
> Version: 2.0 | Last Updated: October 2025

---

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [System Requirements](#system-requirements)
4. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
5. [Phase 2: GLM 4.6 Configuration](#phase-2-glm-46-configuration)
6. [Phase 3: Claude Code Router](#phase-3-claude-code-router)
7. [Phase 4: Claude-Flow Installation](#phase-4-claude-flow-installation)
8. [Phase 5: Integration & Testing](#phase-5-integration--testing)
9. [Phase 6: Production Deployment](#phase-6-production-deployment)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Configuration](#advanced-configuration)
12. [Best Practices](#best-practices)
13. [Maintenance & Updates](#maintenance--updates)

---

## Introduction

### What This Guide Covers

This comprehensive manual will guide you through implementing an enterprise-grade AI development environment combining:

- **GLM 4.6** - Powerful LLM alternative to Claude via Z.AI
- **Claude Code** - Terminal-based AI coding assistant
- **Claude Code Router** - Multi-provider model routing system
- **Claude-Flow** - Enterprise agent orchestration platform

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Project / Cursor IDE                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────▼──────────────┐
        │      Claude Code CLI       │
        │   (Terminal Interface)     │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │   Claude Code Router       │
        │  (Port 3456 - Optional)    │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │     Environment Config     │
        │  ANTHROPIC_BASE_URL →      │
        │  https://api.z.ai/...      │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │       Z.AI API Gateway     │
        │        (GLM 4.6)           │
        └────────────────────────────┘
```

### Benefits of This Setup

✅ **Cost Efficiency** - GLM 4.6 costs fraction of Claude  
✅ **No Limits** - Bypass weekly usage restrictions  
✅ **Enterprise Features** - Swarm orchestration, 100+ agents  
✅ **Flexibility** - Multi-model routing capabilities  
✅ **Production Ready** - Monitoring, logging, persistence  

---

## Prerequisites

### Required Knowledge

- Basic terminal/command-line skills
- Understanding of environment variables
- Git basics (clone, commit, push)
- JSON configuration file editing

### Required Accounts

1. **Z.AI Account** (for GLM 4.6 API)
   - Sign up: https://z.ai/model-api
   - Free tier available
   - Credit card for paid tier

2. **GitHub Account** (optional, for version control)
   - Sign up: https://github.com

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Node.js | 18.0+ | Claude Code runtime |
| npm | 8.0+ | Package management |
| Python | 3.8+ | Optional, for scripts |
| Git | 2.0+ | Version control |
| curl | Any | API testing |
| jq | Any | JSON processing |

---

## System Requirements

### macOS

```bash
# Check versions
node --version    # Should be >= 18.0
npm --version     # Should be >= 8.0
python3 --version # Should be >= 3.8
git --version     # Should be >= 2.0
```

**Minimum Specs:**
- macOS 11.0 (Big Sur) or later
- 8GB RAM (16GB recommended)
- 2GB free disk space
- Internet connection

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nodejs npm python3 git curl jq -y

# Fedora/RHEL
sudo dnf install nodejs npm python3 git curl jq -y

# Arch
sudo pacman -S nodejs npm python3 git curl jq
```

### Windows

**Option 1: WSL2 (Recommended)**
```powershell
# Install WSL2
wsl --install

# Then follow Linux instructions
```

**Option 2: Native Windows**
- Install Node.js from: https://nodejs.org
- Install Git from: https://git-scm.com
- Install Python from: https://python.org
- Use PowerShell for commands

---

## Phase 1: Foundation Setup

### Step 1.1: Verify Node.js Installation

```bash
# Check Node.js version
node --version

# If not installed or version < 18:
# macOS (using Homebrew)
brew install node

# Or download from: https://nodejs.org/
```

### Step 1.2: Install Claude Code Globally

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version

# Expected output: 2.0.14 or newer
```

**Troubleshooting Permission Issues:**

```bash
# macOS/Linux - if permission denied
sudo npm install -g @anthropic-ai/claude-code

# Alternative: Use nvm (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
npm install -g @anthropic-ai/claude-code
```

### Step 1.3: Verify Claude Code Installation

```bash
# Check if claude command is available
which claude

# Expected: /usr/local/bin/claude or similar path

# Test help command
claude --help
```

### Step 1.4: Create Project Directory Structure

```bash
# Navigate to your projects folder
cd ~/projects  # or your preferred location

# Create project directory
mkdir my-ai-project
cd my-ai-project

# Initialize git (optional but recommended)
git init
git branch -M main

# Create basic structure
mkdir -p {src,tests,docs,config}
touch README.md .gitignore

# Add to .gitignore
cat << 'EOF' > .gitignore
# Node modules
node_modules/
.npm/

# Environment files
.env
.env.local

# Claude Code
.claude/
.claude-flow/
.swarm/
.hive-mind/

# Logs
*.log
logs/

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
EOF
```

---

## Phase 2: GLM 4.6 Configuration

### Step 2.1: Obtain Z.AI API Key

1. **Register Account:**
   - Visit: https://z.ai/model-api
   - Click "Sign Up" or "Register"
   - Complete registration form
   - Verify email address

2. **Create API Key:**
   - Login to Z.AI platform
   - Navigate to: https://z.ai/manage-apikey/apikey-list
   - Click "Create API Key"
   - Copy and save your API key securely
   - Format: `aca218b0...6.fBgrI4PYSgRpIOH5` (example)

3. **Check Balance:**
   - Verify account balance/credits
   - Add credits if needed for production use

### Step 2.2: Configure Claude Code Settings

**Option A: Automatic Configuration Script (Recommended)**

```bash
# Download and run official Z.AI configuration script
curl -fsSL "https://cdn.bigmodel.cn/install/claude_code_zai_env.sh" | bash

# Script will prompt for API key
# Enter your key when prompted
```

**Option B: Manual Configuration**

```bash
# Create Claude settings directory
mkdir -p ~/.claude

# Create settings.json
cat << 'EOF' > ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "YOUR_ZAI_API_KEY_HERE",
    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "GLM-4.6",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "GLM-4.6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "GLM-4.5-Air"
  },
  "model": "sonnet",
  "permissions": {
    "allow": ["bash"],
    "deny": []
  },
  "verbose": true
}
EOF

# Replace YOUR_ZAI_API_KEY_HERE with your actual key
sed -i '' 's/YOUR_ZAI_API_KEY_HERE/your_actual_api_key_here/g' ~/.claude/settings.json
```

### Step 2.3: Export Environment Variables

**For Current Session (Temporary):**

```bash
# Export variables to current shell
export ANTHROPIC_AUTH_TOKEN="your_zai_api_key_here"
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_DEFAULT_SONNET_MODEL="GLM-4.6"
export API_TIMEOUT_MS="300000"

# Verify exports
echo $ANTHROPIC_AUTH_TOKEN
echo $ANTHROPIC_BASE_URL
```

**For Persistent Configuration:**

**macOS/Linux (bash):**
```bash
# Add to ~/.bashrc or ~/.bash_profile
cat << 'EOF' >> ~/.bashrc
# GLM 4.6 Configuration
export ANTHROPIC_AUTH_TOKEN="your_zai_api_key_here"
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_DEFAULT_SONNET_MODEL="GLM-4.6"
export API_TIMEOUT_MS="300000"
EOF

# Reload configuration
source ~/.bashrc
```

**macOS/Linux (zsh):**
```zsh
# Add to ~/.zshrc
cat << 'EOF' >> ~/.zshrc
# GLM 4.6 Configuration
export ANTHROPIC_AUTH_TOKEN="your_zai_api_key_here"
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_DEFAULT_SONNET_MODEL="GLM-4.6"
export API_TIMEOUT_MS="300000"
EOF

# Reload configuration
source ~/.zshrc
```

**Windows (PowerShell):**
```powershell
# Set user environment variables
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_AUTH_TOKEN', 'your_zai_api_key_here', 'User')
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_BASE_URL', 'https://api.z.ai/api/anthropic', 'User')
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_DEFAULT_SONNET_MODEL', 'GLM-4.6', 'User')

# Restart PowerShell for changes to take effect
```

### Step 2.4: Verify GLM 4.6 Configuration

```bash
# Test API connectivity
curl -s -o /dev/null -w "%{http_code}" \
  -H "x-api-key: your_zai_api_key_here" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"GLM-4.6","max_tokens":10,"messages":[{"role":"user","content":"test"}]}' \
  https://api.z.ai/api/anthropic/v1/messages

# Expected: 200 (success)

# Test Claude Code with GLM
cd ~/my-ai-project
echo "What model are you? Answer in one word." | claude

# Expected output: "GLM" or "GLM-4.6"
```

### Step 2.5: Validate Configuration

```bash
# Check settings file
cat ~/.claude/settings.json | jq '.env | {ANTHROPIC_BASE_URL, ANTHROPIC_DEFAULT_SONNET_MODEL}'

# Expected output:
# {
#   "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
#   "ANTHROPIC_DEFAULT_SONNET_MODEL": "GLM-4.6"
# }

# Test interactive session
claude
# Type: /status
# Should show GLM-4.6 as active model
# Type: /exit to quit
```

---

## Phase 3: Claude Code Router

### Step 3.1: Install Claude Code Router

```bash
# Install globally
npm install -g @musistudio/claude-code-router

# Verify installation
ccr --version

# Check if ccr command is available
which ccr
```

### Step 3.2: Create Router Configuration

```bash
# Create router configuration directory
mkdir -p ~/.claude-code-router

# Create configuration file
cat << 'EOF' > ~/.claude-code-router/config.json
{
  "LOG": true,
  "HOST": "127.0.0.1",
  "PORT": 3456,
  "API_TIMEOUT_MS": 600000,
  "NON_INTERACTIVE_MODE": false,
  "Providers": [
    {
      "name": "glm",
      "api_base_url": "https://api.z.ai/api/anthropic/v1/messages",
      "api_key": "YOUR_ZAI_API_KEY_HERE",
      "models": ["GLM-4.6", "GLM-4.5-Air"],
      "transformer": { "use": ["anthropic"] }
    },
    {
      "name": "openai",
      "api_base_url": "https://api.openai.com/v1/chat/completions",
      "api_key": "$OPENAI_API_KEY",
      "models": ["gpt-4o", "gpt-4o-mini"]
    },
    {
      "name": "anthropic",
      "api_base_url": "https://api.anthropic.com/v1/messages",
      "api_key": "$ANTHROPIC_API_KEY",
      "models": ["claude-3-5-sonnet-20241022"],
      "transformer": { "use": ["anthropic"] }
    }
  ],
  "Router": {
    "default": "glm,GLM-4.6",
    "background": "glm,GLM-4.5-Air",
    "think": "glm,GLM-4.6",
    "longContext": "glm,GLM-4.6",
    "webSearch": "glm,GLM-4.6"
  }
}
EOF

# Replace YOUR_ZAI_API_KEY_HERE with your actual key
sed -i '' 's/YOUR_ZAI_API_KEY_HERE/your_actual_api_key_here/g' ~/.claude-code-router/config.json
```

### Step 3.3: Start Router Service

```bash
# Start router
ccr start

# Expected output:
# ✅ Router started on port 3456
# 🆔 Process ID: XXXXX

# Verify router status
ccr status

# Expected:
# ✅ Status: Running
# 🆔 Process ID: XXXXX
# 🌐 Port: 3456
# 📡 API Endpoint: http://127.0.0.1:3456
```

### Step 3.4: Test Router

```bash
# Check router health
curl -s http://127.0.0.1:3456/health | jq

# Expected:
# {
#   "status": "ok",
#   "timestamp": "2025-10-14T..."
# }

# Open Web UI (optional)
ccr ui
# Opens http://127.0.0.1:3456/ui/ in browser
```

### Step 3.5: Configure Router Auto-Start

**macOS (LaunchAgent):**
```bash
# Create launch agent
mkdir -p ~/Library/LaunchAgents

cat << 'EOF' > ~/Library/LaunchAgents/com.claude-code-router.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude-code-router</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ccr</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load launch agent
launchctl load ~/Library/LaunchAgents/com.claude-code-router.plist
```

**Linux (systemd):**
```bash
# Create systemd service
sudo cat << 'EOF' > /etc/systemd/system/claude-code-router.service
[Unit]
Description=Claude Code Router
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/ccr start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable claude-code-router
sudo systemctl start claude-code-router
sudo systemctl status claude-code-router
```

---

## Phase 4: Claude-Flow Installation

### Step 4.1: Install Claude-Flow

```bash
# Navigate to your project
cd ~/my-ai-project

# Initialize Claude-Flow with monitoring
npx claude-flow@alpha init --monitoring

# This will:
# ✅ Create .claude/ directory structure
# ✅ Install 90+ MCP tools
# ✅ Set up Hive Mind system
# ✅ Create 68 specialized agents
# ✅ Initialize SQLite memory database
# ✅ Configure hooks and automation
```

### Step 4.2: Verify Claude-Flow Installation

```bash
# Check created structure
ls -la .claude/
ls -la .hive-mind/
ls -la .swarm/

# Verify agent count
ls .claude/agents/ | wc -l
# Expected: 68 agents

# Check local executable
./claude-flow --version
# Expected: 2.0.0 or newer
```

### Step 4.3: Configure Claude-Flow MCP Servers

The initialization script automatically adds MCP servers to `~/.claude.json`. Verify:

```bash
# Check MCP configuration
cat ~/.claude.json | jq '.mcpServers | keys'

# Expected servers:
# - claude-flow
# - ruv-swarm  
# - flow-nexus
# - agentic-payments
```

### Step 4.4: Initialize Hive Mind System

```bash
# Initialize Hive Mind (if not done automatically)
./claude-flow hive-mind init

# Expected output:
# 🧠 Hive Mind System initialized successfully
# ✅ Collective memory database created
# ✅ Queen and worker configurations ready
```

### Step 4.5: Test Claude-Flow Basic Functionality

```bash
# Test with simple task
./claude-flow swarm "Create a hello world script" --max-agents 2

# Monitor swarm status
./claude-flow hive-mind status

# Check memory usage
./claude-flow memory usage
```

---

## Phase 5: Integration & Testing

### Step 5.1: End-to-End Test Suite

Create a test script to verify all components:

```bash
# Create test script
cat << 'EOF' > test-integration.sh
#!/bin/bash

echo "🧪 Integration Test Suite"
echo "========================="

# Test 1: Node.js
echo ""
echo "Test 1: Node.js Version"
node --version || echo "❌ Node.js not found"

# Test 2: Claude Code
echo ""
echo "Test 2: Claude Code"
claude --version || echo "❌ Claude Code not found"

# Test 3: GLM 4.6 API
echo ""
echo "Test 3: GLM 4.6 API Connection"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "x-api-key: $ANTHROPIC_AUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"GLM-4.6","max_tokens":10,"messages":[{"role":"user","content":"test"}]}' \
  https://api.z.ai/api/anthropic/v1/messages)
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ API responding correctly"
else
  echo "❌ API returned code: $HTTP_CODE"
fi

# Test 4: Claude Code Router
echo ""
echo "Test 4: Claude Code Router"
ccr status | grep -q "Running" && echo "✅ Router running" || echo "⚠️  Router not running"

# Test 5: Claude-Flow
echo ""
echo "Test 5: Claude-Flow"
./claude-flow --version || echo "❌ Claude-Flow not found"

# Test 6: Model Verification
echo ""
echo "Test 6: Model Verification"
echo "What model are you? One word." | claude | grep -qi "glm" && echo "✅ Using GLM" || echo "❌ Not using GLM"

echo ""
echo "========================="
echo "Integration Test Complete"
EOF

# Make executable
chmod +x test-integration.sh

# Run tests
./test-integration.sh
```

### Step 5.2: Performance Benchmarks

```bash
# Create benchmark script
cat << 'EOF' > benchmark.sh
#!/bin/bash

echo "⚡ Performance Benchmarks"
echo "========================"

# Benchmark 1: Simple prompt response time
echo ""
echo "Benchmark 1: Simple Prompt (10 tokens)"
time echo "Say hello" | claude > /dev/null

# Benchmark 2: Code generation
echo ""
echo "Benchmark 2: Code Generation"
time echo "Create a Python function to add two numbers" | claude > /dev/null

# Benchmark 3: Swarm orchestration
echo ""
echo "Benchmark 3: Swarm with 2 agents"
time ./claude-flow swarm "Simple task" --max-agents 2 > /dev/null

echo ""
echo "Benchmarks Complete"
EOF

chmod +x benchmark.sh
./benchmark.sh
```

### Step 5.3: Feature Validation

```bash
# Test all major features
cat << 'EOF' > validate-features.sh
#!/bin/bash

echo "✨ Feature Validation"
echo "===================="

# Feature 1: Basic Claude Code
echo ""
echo "Feature 1: Basic Claude Code Interaction"
echo "print('Hello from GLM')" | claude --output-format json | jq '.result' > /dev/null && echo "✅ PASS" || echo "❌ FAIL"

# Feature 2: Router model switching
echo ""
echo "Feature 2: Router Model Selection"
curl -s http://127.0.0.1:3456/api/config | jq '.Router.default' | grep -q "GLM" && echo "✅ PASS" || echo "❌ FAIL"

# Feature 3: Hive Mind status
echo ""
echo "Feature 3: Hive Mind System"
./claude-flow hive-mind status > /dev/null 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

# Feature 4: Memory persistence
echo ""
echo "Feature 4: Memory Persistence"
[ -f .swarm/memory.db ] && echo "✅ PASS" || echo "❌ FAIL"

# Feature 5: Agent count
echo ""
echo "Feature 5: Agent System (should be 68)"
AGENT_COUNT=$(ls .claude/agents/*/*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$AGENT_COUNT" -ge 60 ]; then
  echo "✅ PASS ($AGENT_COUNT agents)"
else
  echo "❌ FAIL ($AGENT_COUNT agents)"
fi

echo ""
echo "===================="
echo "Validation Complete"
EOF

chmod +x validate-features.sh
./validate-features.sh
```

### Step 5.4: Cost Monitoring Setup

```bash
# Create cost tracking script
cat << 'EOF' > monitor-costs.sh
#!/bin/bash

echo "💰 Cost Monitoring"
echo "=================="

# Check token usage
if [ -f .claude-flow@alpha/token-usage.json ]; then
  echo ""
  echo "Token Usage:"
  cat .claude-flow@alpha/token-usage.json | jq '{
    total_tokens: .total_tokens,
    estimated_cost: .estimated_cost_usd
  }'
else
  echo "⚠️  Token tracking file not found"
fi

# Check API balance (if available)
echo ""
echo "Checking Z.AI balance..."
# Add API call to check balance if available

echo ""
echo "=================="
EOF

chmod +x monitor-costs.sh
```

---

## Phase 6: Production Deployment

### Step 6.1: Production Configuration

```bash
# Create production settings
mkdir -p ~/my-ai-project/config

cat << 'EOF' > ~/my-ai-project/config/production.json
{
  "environment": "production",
  "glm": {
    "model": "GLM-4.6",
    "fallback_model": "GLM-4.5-Air",
    "max_tokens": 4096,
    "temperature": 0.7
  },
  "router": {
    "enabled": true,
    "port": 3456,
    "log_level": "info"
  },
  "claude_flow": {
    "max_agents": 10,
    "swarm_strategy": "auto",
    "memory_enabled": true,
    "monitoring_enabled": true
  },
  "security": {
    "api_key_rotation_days": 90,
    "rate_limiting": true,
    "max_requests_per_minute": 60
  }
}
EOF
```

### Step 6.2: Environment Management

```bash
# Create .env template
cat << 'EOF' > ~/my-ai-project/.env.template
# Z.AI Configuration
ANTHROPIC_AUTH_TOKEN=your_zai_api_key
ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
ANTHROPIC_DEFAULT_SONNET_MODEL=GLM-4.6

# Optional: Other Provider Keys
OPENAI_API_KEY=optional_openai_key
GEMINI_API_KEY=optional_gemini_key

# Router Configuration
ROUTER_PORT=3456
ROUTER_HOST=127.0.0.1

# Claude-Flow Configuration
CLAUDE_FLOW_MAX_AGENTS=10
CLAUDE_FLOW_LOG_LEVEL=info

# Project Settings
NODE_ENV=production
LOG_LEVEL=info
EOF

# Copy for actual use (never commit .env!)
cp .env.template .env

# Edit .env with real values
# Use your preferred editor: nano, vim, code, etc.
nano .env
```

### Step 6.3: Logging Configuration

```bash
# Create logging setup
mkdir -p ~/my-ai-project/logs

cat << 'EOF' > ~/my-ai-project/config/logging.json
{
  "version": 1,
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "INFO",
      "formatter": "detailed"
    },
    "file": {
      "class": "logging.FileHandler",
      "level": "DEBUG",
      "filename": "logs/application.log",
      "formatter": "detailed"
    }
  },
  "formatters": {
    "detailed": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
  },
  "root": {
    "level": "DEBUG",
    "handlers": ["console", "file"]
  }
}
EOF
```

### Step 6.4: Monitoring Setup

```bash
# Create monitoring dashboard
cat << 'EOF' > ~/my-ai-project/monitor-dashboard.sh
#!/bin/bash

watch -n 2 '
echo "🔍 System Monitor"
echo "================"
echo ""
echo "Claude Code Router:"
ccr status | grep -E "Status|Port|Process"
echo ""
echo "Claude-Flow Swarms:"
cd ~/my-ai-project && ./claude-flow hive-mind status 2>/dev/null | head -5
echo ""
echo "Memory Usage:"
du -sh ~/.claude-code-router/ .swarm/ .hive-mind/ 2>/dev/null
echo ""
echo "API Calls (last 5):"
tail -5 ~/.claude-code-router/logs/ccr-*.log 2>/dev/null | grep -E "request completed"
'
EOF

chmod +x ~/my-ai-project/monitor-dashboard.sh
```

### Step 6.5: Backup Strategy

```bash
# Create backup script
cat << 'EOF' > ~/my-ai-project/backup.sh
#!/bin/bash

BACKUP_DIR=~/backups/ai-setup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📦 Creating Backup: $TIMESTAMP"
mkdir -p $BACKUP_DIR/$TIMESTAMP

# Backup configurations
echo "Backing up configurations..."
cp -r ~/.claude $BACKUP_DIR/$TIMESTAMP/
cp -r ~/.claude-code-router $BACKUP_DIR/$TIMESTAMP/
cp -r ~/my-ai-project/.claude $BACKUP_DIR/$TIMESTAMP/
cp -r ~/my-ai-project/.hive-mind $BACKUP_DIR/$TIMESTAMP/
cp -r ~/my-ai-project/.swarm $BACKUP_DIR/$TIMESTAMP/

# Backup project files
echo "Backing up project files..."
cp ~/my-ai-project/.env.template $BACKUP_DIR/$TIMESTAMP/
cp ~/my-ai-project/config/*.json $BACKUP_DIR/$TIMESTAMP/ 2>/dev/null

# Create archive
echo "Creating archive..."
cd $BACKUP_DIR
tar -czf backup_$TIMESTAMP.tar.gz $TIMESTAMP/
rm -rf $TIMESTAMP/

echo "✅ Backup complete: backup_$TIMESTAMP.tar.gz"
echo "Location: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
EOF

chmod +x ~/my-ai-project/backup.sh

# Schedule daily backups (cron)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/my-ai-project/backup.sh") | crontab -
```

### Step 6.6: Health Check Endpoint

```bash
# Create health check script
cat << 'EOF' > ~/my-ai-project/healthcheck.sh
#!/bin/bash

# Returns: 0 = healthy, 1 = unhealthy

echo "🏥 Health Check"

# Check 1: Router
curl -sf http://127.0.0.1:3456/health > /dev/null || {
  echo "❌ Router unhealthy"
  exit 1
}

# Check 2: API
curl -sf -H "x-api-key: $ANTHROPIC_AUTH_TOKEN" \
  https://api.z.ai/api/anthropic/v1/messages \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"GLM-4.6","max_tokens":1,"messages":[{"role":"user","content":"test"}]}' \
  > /dev/null || {
  echo "❌ API unhealthy"
  exit 1
}

# Check 3: Memory DB
[ -f ~/my-ai-project/.swarm/memory.db ] || {
  echo "❌ Memory DB missing"
  exit 1
}

echo "✅ All systems healthy"
exit 0
EOF

chmod +x ~/my-ai-project/healthcheck.sh
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Weekly limit reached" Error

**Symptom:** Claude Code shows "Weekly limit reached"

**Cause:** Environment variables not exported, still using Anthropic API

**Solution:**
```bash
# Export variables in current shell
export ANTHROPIC_AUTH_TOKEN="your_zai_api_key"
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"

# Test
echo "What model?" | claude
# Should respond with "GLM"
```

#### Issue 2: Router Not Starting

**Symptom:** `ccr start` fails or hangs

**Solution:**
```bash
# Check if port 3456 is already in use
lsof -i :3456

# Kill conflicting process
kill -9 <PID>

# Or use different port
# Edit ~/.claude-code-router/config.json
# Change "PORT": 3456 to "PORT": 3457
```

#### Issue 3: Claude-Flow Initialization Fails

**Symptom:** `npx claude-flow@alpha init` errors

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Remove existing .claude directory
rm -rf .claude .claude-flow .hive-mind .swarm

# Retry with --force flag
npx claude-flow@alpha init --monitoring --force
```

#### Issue 4: API Key Invalid

**Symptom:** 401 Unauthorized errors

**Solution:**
```bash
# Verify API key format
echo $ANTHROPIC_AUTH_TOKEN
# Should be: aca...6.fBg...H5 (about 60 chars)

# Test API key directly
curl -H "x-api-key: $ANTHROPIC_AUTH_TOKEN" \
  https://api.z.ai/api/anthropic/v1/messages \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"GLM-4.6","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}'

# If fails, regenerate key at https://z.ai/manage-apikey/apikey-list
```

#### Issue 5: Memory Database Corruption

**Symptom:** Claude-Flow crashes with SQLite errors

**Solution:**
```bash
# Backup existing database
cp .swarm/memory.db .swarm/memory.db.backup

# Rebuild database
rm .swarm/memory.db
./claude-flow hive-mind init

# If data recovery needed, use SQLite tools
sqlite3 .swarm/memory.db.backup .dump | sqlite3 .swarm/memory.db
```

#### Issue 6: High Token Usage / Costs

**Symptom:** Unexpected high costs

**Solution:**
```bash
# Check token usage
cat .claude-flow@alpha/token-usage.json | jq

# Optimize by using GLM-4.5-Air for background tasks
# Edit ~/.claude-code-router/config.json
# Set: "background": "glm,GLM-4.5-Air"

# Restart router
ccr restart
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Enable debug mode in Claude Code
echo '{"verbose": true, "env": {...}}' > ~/.claude/settings.json

# Enable router debug logs
# Edit ~/.claude-code-router/config.json
# Set: "LOG_LEVEL": "debug"

# View live logs
tail -f ~/.claude-code-router/logs/ccr-*.log

# View Claude-Flow logs
tail -f .claude-flow@alpha/logs/*.log
```

---

## Advanced Configuration

### Multi-Model Routing Strategies

```json
// ~/.claude-code-router/config.json
{
  "Router": {
    "default": "glm,GLM-4.6",
    "background": "glm,GLM-4.5-Air",
    "think": "glm,GLM-4.6",
    "longContext": "glm,GLM-4.6",
    "webSearch": "glm,GLM-4.6",
    "codeReview": "glm,GLM-4.6",
    "documentation": "glm,GLM-4.5-Air"
  }
}
```

### Custom Agent Configuration

```bash
# Create custom agent
cat << 'EOF' > ~/my-ai-project/.claude/agents/custom/my-specialist.md
# My Specialist Agent

## Role
Custom specialist for specific domain tasks

## Capabilities
- Domain-specific expertise
- Custom workflows
- Integration with external tools

## Configuration
- Model: GLM-4.6
- Temperature: 0.7
- Max tokens: 2048
EOF
```

### API Rate Limiting

```javascript
// config/rate-limiter.js
const rateLimit = {
  glm: {
    requestsPerMinute: 60,
    tokensPerMinute: 100000,
    burstAllowance: 10
  }
};
```

### Webhook Integration

```bash
# Setup webhook for notifications
cat << 'EOF' > config/webhooks.json
{
  "webhooks": [
    {
      "event": "swarm.completed",
      "url": "https://your-domain.com/api/notify",
      "method": "POST",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  ]
}
EOF
```

---

## Best Practices

### 1. Security

✅ **DO:**
- Store API keys in environment variables
- Use `.gitignore` for sensitive files
- Rotate API keys every 90 days
- Limit API key permissions
- Use HTTPS for all API calls

❌ **DON'T:**
- Commit `.env` files to git
- Share API keys in chat/email
- Use root user for installations
- Disable SSL verification

### 2. Performance Optimization

```bash
# Use GLM-4.5-Air for simple tasks
Router: {
  "background": "glm,GLM-4.5-Air",  // Faster, cheaper
  "think": "glm,GLM-4.6"            // More powerful
}

# Enable caching
"env": {
  "CACHE_ENABLED": "true",
  "CACHE_TTL": "3600"
}

# Optimize token usage
"max_tokens": 2048,  // Adjust based on needs
"temperature": 0.7   // Lower = more focused
```

### 3. Cost Management

```bash
# Set budget alerts
cat << 'EOF' > config/budget.json
{
  "daily_limit_usd": 10.0,
  "monthly_limit_usd": 200.0,
  "alert_threshold": 0.8
}
EOF

# Monitor costs daily
./monitor-costs.sh

# Use cheaper models for background tasks
```

### 4. Team Collaboration

```bash
# Share configuration template
cp .env .env.template
git add .env.template

# Document setup process
echo "# Team Setup
1. Copy .env.template to .env
2. Add your Z.AI API key
3. Run ./setup.sh
" > TEAM_SETUP.md
```

### 5. Version Control

```bash
# Commit structure, not secrets
git add .gitignore
git add .env.template
git add config/*.json
git add *.sh
git commit -m "feat: add AI setup configuration"

# Never commit:
# - .env (actual secrets)
# - .claude/ (generated)
# - .swarm/ (runtime data)
```

---

## Maintenance & Updates

### Weekly Maintenance

```bash
# 1. Check for updates
npm outdated -g @anthropic-ai/claude-code
npm outdated -g @musistudio/claude-code-router

# 2. Update packages
npm update -g @anthropic-ai/claude-code
npm update -g @musistudio/claude-code-router

# 3. Update Claude-Flow
cd ~/my-ai-project
npx claude-flow@alpha init --force

# 4. Clean logs
rm -f ~/.claude-code-router/logs/ccr-*.log.old
rm -f .claude-flow@alpha/logs/*.log.old

# 5. Backup
./backup.sh
```

### Monthly Maintenance

```bash
# 1. Review token usage
cat .claude-flow@alpha/token-usage.json | jq

# 2. Optimize configuration
# Review and adjust model routing

# 3. Security audit
# Rotate API keys
# Update dependencies

# 4. Performance review
./benchmark.sh > benchmarks/$(date +%Y%m).txt

# 5. Database optimization
cd ~/my-ai-project
sqlite3 .swarm/memory.db "VACUUM;"
```

### Update Checklist

- [ ] Backup current configuration
- [ ] Update Node.js if needed
- [ ] Update Claude Code
- [ ] Update Claude Code Router
- [ ] Update Claude-Flow
- [ ] Test integration
- [ ] Update documentation
- [ ] Notify team members

---

## Appendix

### A. Quick Reference Commands

```bash
# Claude Code
claude                          # Start interactive session
claude --version                # Check version
claude --help                   # Show help

# Claude Code Router
ccr start                       # Start router
ccr stop                        # Stop router
ccr restart                     # Restart router
ccr status                      # Check status
ccr ui                          # Open web UI

# Claude-Flow
./claude-flow --help            # Show help
./claude-flow swarm "task"      # Run swarm
./claude-flow hive-mind status  # Check status
./claude-flow memory usage      # Memory info
```

### B. Configuration Files Reference

| File | Purpose | Location |
|------|---------|----------|
| settings.json | Claude Code config | ~/.claude/ |
| config.json | Router config | ~/.claude-code-router/ |
| .env | Environment vars | Project root |
| memory.db | Persistent storage | .swarm/ |
| agents/*.md | Agent definitions | .claude/agents/ |

### C. API Endpoints

```
Z.AI API:
- Base URL: https://api.z.ai/api/anthropic
- Models: GLM-4.6, GLM-4.5-Air
- Docs: https://z.ai/model-api

Router API:
- Health: http://localhost:3456/health
- Config: http://localhost:3456/api/config
- UI: http://localhost:3456/ui/
```

### D. Resource Links

- **Z.AI Platform**: https://z.ai/model-api
- **Claude Code Docs**: https://docs.anthropic.com/en/docs/claude-code/
- **Claude-Flow GitHub**: https://github.com/ruvnet/claude-flow
- **Router GitHub**: https://github.com/musistudio/claude-code-router

### E. Support & Community

- **Issues**: Report on respective GitHub repos
- **Community**: Discord servers (links in repos)
- **Updates**: Watch GitHub repos for releases

---

## Conclusion

You now have a complete, production-ready AI development environment featuring:

✅ **GLM 4.6** - Cost-effective LLM alternative  
✅ **Claude Code** - Powerful terminal AI assistant  
✅ **Multi-Model Router** - Flexible provider switching  
✅ **Claude-Flow** - Enterprise orchestration platform  
✅ **Swarm Intelligence** - Multi-agent coordination  
✅ **Persistent Memory** - SQLite-backed knowledge base  
✅ **Monitoring & Logging** - Production observability  

### Next Steps

1. **Explore Features**: Try different swarm strategies
2. **Optimize Costs**: Fine-tune model routing
3. **Customize Agents**: Create domain-specific agents
4. **Scale Up**: Increase agent counts for complex projects
5. **Share Knowledge**: Document learnings for your team

### Getting Help

If you encounter issues not covered in this guide:

1. Check the troubleshooting section
2. Enable debug logging
3. Review logs in detail
4. Search GitHub issues
5. Ask in community Discord
6. Create detailed bug report

---

**Version**: 2.0  
**Last Updated**: October 2025  
**Maintained By**: Community Contributors  
**License**: MIT  

**Happy Coding with AI!** 🚀

