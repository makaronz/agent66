#!/bin/bash

# API Documentation Generation Script
# Generates comprehensive OpenAPI documentation for both Express.js and FastAPI

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EXPRESS_PORT=${EXPRESS_PORT:-3000}
FASTAPI_PORT=${FASTAPI_PORT:-8000}
DOCS_DIR="docs"
API_DOCS_DIR="$DOCS_DIR/api"
TIMEOUT=30

echo -e "${BLUE}🚀 Starting API Documentation Generation${NC}"

# Create directories
mkdir -p "$DOCS_DIR"
mkdir -p "$API_DOCS_DIR"

# Function to check if server is running
check_server() {
    local url=$1
    local name=$2
    local timeout=$3
    
    echo -e "${YELLOW}⏳ Waiting for $name to be ready...${NC}"
    
    for i in $(seq 1 $timeout); do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name is ready${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}❌ $name failed to start within $timeout seconds${NC}"
    return 1
}

# Function to start server in background
start_server() {
    local command=$1
    local name=$2
    local health_url=$3
    
    echo -e "${BLUE}🔄 Starting $name...${NC}"
    eval "$command" &
    local pid=$!
    
    # Wait for server to be ready
    if check_server "$health_url" "$name" $TIMEOUT; then
        echo "$pid"
        return 0
    else
        kill $pid 2>/dev/null || true
        return 1
    fi
}

# Function to cleanup background processes
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up background processes...${NC}"
    if [ ! -z "$EXPRESS_PID" ]; then
        kill $EXPRESS_PID 2>/dev/null || true
    fi
    if [ ! -z "$FASTAPI_PID" ]; then
        kill $FASTAPI_PID 2>/dev/null || true
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Check if required tools are installed
echo -e "${BLUE}🔍 Checking required tools...${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not installed${NC}"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required tools are available${NC}"

# Install Node.js dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Installing Node.js dependencies...${NC}"
    npm install
fi

# Install Python dependencies if needed
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
pip install -q fastapi uvicorn

# Start Express.js server
echo -e "${BLUE}🚀 Starting Express.js API server...${NC}"
EXPRESS_PID=$(start_server "NODE_ENV=development npm run server:dev" "Express.js API" "http://localhost:$EXPRESS_PORT/api/health")

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start Express.js server${NC}"
    exit 1
fi

# Start FastAPI server
echo -e "${BLUE}🚀 Starting FastAPI server...${NC}"
FASTAPI_PID=$(start_server "python -m uvicorn api_fastapi:app --host 0.0.0.0 --port $FASTAPI_PORT" "FastAPI" "http://localhost:$FASTAPI_PORT/health")

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start FastAPI server${NC}"
    exit 1
fi

# Generate OpenAPI specifications
echo -e "${BLUE}📄 Generating OpenAPI specifications...${NC}"

# Express.js OpenAPI spec
echo -e "${YELLOW}📋 Fetching Express.js OpenAPI spec...${NC}"
if curl -f -s "http://localhost:$EXPRESS_PORT/api/docs/openapi.json" -o "$DOCS_DIR/openapi-express.json"; then
    echo -e "${GREEN}✅ Express.js OpenAPI spec generated${NC}"
else
    echo -e "${RED}❌ Failed to fetch Express.js OpenAPI spec${NC}"
    exit 1
fi

# FastAPI OpenAPI spec
echo -e "${YELLOW}📋 Fetching FastAPI OpenAPI spec...${NC}"
if curl -f -s "http://localhost:$FASTAPI_PORT/api/v1/openapi.json" -o "$DOCS_DIR/openapi-fastapi.json"; then
    echo -e "${GREEN}✅ FastAPI OpenAPI spec generated${NC}"
else
    echo -e "${RED}❌ Failed to fetch FastAPI OpenAPI spec${NC}"
    exit 1
fi

# Install documentation generation tools
echo -e "${BLUE}🛠️ Installing documentation generation tools...${NC}"
npm install -g @apidevtools/swagger-cli redoc-cli 2>/dev/null || {
    echo -e "${YELLOW}⚠️ Global npm install failed, trying local install...${NC}"
    npm install @apidevtools/swagger-cli redoc-cli
    export PATH="$PATH:./node_modules/.bin"
}

# Validate OpenAPI specifications
echo -e "${BLUE}✅ Validating OpenAPI specifications...${NC}"

echo -e "${YELLOW}🔍 Validating Express.js spec...${NC}"
if swagger-cli validate "$DOCS_DIR/openapi-express.json"; then
    echo -e "${GREEN}✅ Express.js OpenAPI spec is valid${NC}"
else
    echo -e "${RED}❌ Express.js OpenAPI spec validation failed${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Validating FastAPI spec...${NC}"
if swagger-cli validate "$DOCS_DIR/openapi-fastapi.json"; then
    echo -e "${GREEN}✅ FastAPI OpenAPI spec is valid${NC}"
else
    echo -e "${RED}❌ FastAPI OpenAPI spec validation failed${NC}"
    exit 1
fi

# Generate HTML documentation
echo -e "${BLUE}📚 Generating HTML documentation...${NC}"

# Express.js documentation
echo -e "${YELLOW}📖 Generating Express.js documentation...${NC}"
if redoc-cli build "$DOCS_DIR/openapi-express.json" --output "$API_DOCS_DIR/express-api.html" --title "SMC Trading Agent Express API"; then
    echo -e "${GREEN}✅ Express.js documentation generated${NC}"
else
    echo -e "${RED}❌ Failed to generate Express.js documentation${NC}"
    exit 1
fi

# FastAPI documentation
echo -e "${YELLOW}📖 Generating FastAPI documentation...${NC}"
if redoc-cli build "$DOCS_DIR/openapi-fastapi.json" --output "$API_DOCS_DIR/fastapi-api.html" --title "SMC Trading Agent FastAPI"; then
    echo -e "${GREEN}✅ FastAPI documentation generated${NC}"
else
    echo -e "${RED}❌ Failed to generate FastAPI documentation${NC}"
    exit 1
fi

# Generate combined documentation index
echo -e "${BLUE}📑 Generating combined documentation index...${NC}"

cat > "$API_DOCS_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMC Trading Agent API Documentation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8fafc;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .api-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .api-card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .api-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        
        .api-card h2 {
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 1.5rem;
        }
        
        .api-card p {
            color: #718096;
            margin-bottom: 20px;
        }
        
        .api-links {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .api-link {
            display: inline-block;
            padding: 10px 20px;
            background: #4299e1;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: background 0.2s;
        }
        
        .api-link:hover {
            background: #3182ce;
        }
        
        .api-link.secondary {
            background: #718096;
        }
        
        .api-link.secondary:hover {
            background: #4a5568;
        }
        
        .specs-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 40px;
        }
        
        .specs-section h2 {
            color: #2d3748;
            margin-bottom: 15px;
        }
        
        .specs-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #718096;
            border-top: 1px solid #e2e8f0;
            margin-top: 40px;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            background: #48bb78;
            color: white;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
            margin-left: 10px;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .api-grid {
                grid-template-columns: 1fr;
            }
            
            .api-links {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SMC Trading Agent API Documentation</h1>
            <p>Comprehensive API documentation for algorithmic trading with Smart Money Concepts</p>
        </div>
        
        <div class="api-grid">
            <div class="api-card">
                <h2>Express.js API <span class="badge">Gateway</span></h2>
                <p>
                    Handles user authentication, exchange integrations, API gateway functionality, 
                    and user management. This is the main entry point for client applications.
                </p>
                <div class="api-links">
                    <a href="express-api.html" class="api-link">📚 View Documentation</a>
                    <a href="http://localhost:3000/api/docs" class="api-link secondary">🔧 Interactive UI</a>
                </div>
            </div>
            
            <div class="api-card">
                <h2>FastAPI <span class="badge">Trading Engine</span></h2>
                <p>
                    Core trading engine with SMC pattern detection, risk management, strategy execution, 
                    and real-time market data processing.
                </p>
                <div class="api-links">
                    <a href="fastapi-api.html" class="api-link">📚 View Documentation</a>
                    <a href="http://localhost:8000/api/v1/docs" class="api-link secondary">🔧 Interactive UI</a>
                </div>
            </div>
        </div>
        
        <div class="specs-section">
            <h2>📋 OpenAPI Specifications</h2>
            <p>Download the machine-readable OpenAPI specifications for integration and development.</p>
            <div class="specs-grid">
                <a href="../openapi-express.json" class="api-link">📄 Express.js OpenAPI JSON</a>
                <a href="../openapi-fastapi.json" class="api-link">📄 FastAPI OpenAPI JSON</a>
            </div>
        </div>
        
        <div class="specs-section">
            <h2>🚀 Quick Start Guide</h2>
            <ol style="margin-left: 20px; color: #4a5568;">
                <li><strong>Authentication:</strong> Use <code>/api/v1/auth/login</code> to get JWT token</li>
                <li><strong>Exchange Setup:</strong> Configure API keys via <code>/api/v1/users/api-keys</code></li>
                <li><strong>Market Data:</strong> Fetch real-time data from <code>/api/v1/market-data</code></li>
                <li><strong>Trading Signals:</strong> Get SMC signals from <code>/api/v1/signals</code></li>
                <li><strong>Place Orders:</strong> Execute trades via <code>/api/v1/orders</code></li>
            </ol>
        </div>
        
        <div class="specs-section">
            <h2>🔗 Additional Resources</h2>
            <div class="api-links">
                <a href="https://github.com/smc-trading-agent" class="api-link">📦 GitHub Repository</a>
                <a href="https://docs.smctradingagent.com" class="api-link">📖 Full Documentation</a>
                <a href="mailto:support@smctradingagent.com" class="api-link secondary">📧 Support</a>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated on <strong>$(date)</strong> | SMC Trading Agent v1.0.0</p>
        </div>
    </div>
</body>
</html>
EOF

echo -e "${GREEN}✅ Combined documentation index generated${NC}"

# Generate API summary report
echo -e "${BLUE}📊 Generating API summary report...${NC}"

cat > "$DOCS_DIR/api-summary.md" << EOF
# API Documentation Summary

Generated on: $(date)

## Overview

The SMC Trading Agent provides two complementary APIs:

1. **Express.js API** (Port $EXPRESS_PORT): Authentication, user management, exchange integrations
2. **FastAPI** (Port $FASTAPI_PORT): Core trading engine with SMC pattern detection

## Generated Files

### Documentation
- \`docs/api/index.html\` - Combined documentation index
- \`docs/api/express-api.html\` - Express.js API documentation
- \`docs/api/fastapi-api.html\` - FastAPI documentation

### OpenAPI Specifications
- \`docs/openapi-express.json\` - Express.js OpenAPI spec
- \`docs/openapi-fastapi.json\` - FastAPI OpenAPI spec

## Validation Results

✅ Express.js OpenAPI specification is valid
✅ FastAPI OpenAPI specification is valid

## Access URLs

### Development Environment
- Express.js Swagger UI: http://localhost:$EXPRESS_PORT/api/docs
- FastAPI Swagger UI: http://localhost:$FASTAPI_PORT/api/v1/docs
- Combined Documentation: file://$(pwd)/$API_DOCS_DIR/index.html

### Production Environment
- Express.js Swagger UI: https://api.smctradingagent.com/api/docs
- FastAPI Swagger UI: https://api.smctradingagent.com/api/v1/docs

## Next Steps

1. Review the generated documentation
2. Test API endpoints using interactive Swagger UI
3. Update client SDKs if needed
4. Deploy documentation to production

## Support

- GitHub: https://github.com/smc-trading-agent
- Email: support@smctradingagent.com
- Documentation: https://docs.smctradingagent.com
EOF

echo -e "${GREEN}✅ API summary report generated${NC}"

# Display summary
echo -e "${GREEN}🎉 API Documentation Generation Complete!${NC}"
echo -e "${BLUE}📁 Generated files:${NC}"
echo -e "  📄 $DOCS_DIR/openapi-express.json"
echo -e "  📄 $DOCS_DIR/openapi-fastapi.json"
echo -e "  📚 $API_DOCS_DIR/express-api.html"
echo -e "  📚 $API_DOCS_DIR/fastapi-api.html"
echo -e "  🏠 $API_DOCS_DIR/index.html"
echo -e "  📊 $DOCS_DIR/api-summary.md"

echo -e "${BLUE}🔗 Access documentation:${NC}"
echo -e "  🌐 Combined docs: file://$(pwd)/$API_DOCS_DIR/index.html"
echo -e "  🔧 Express.js UI: http://localhost:$EXPRESS_PORT/api/docs"
echo -e "  🔧 FastAPI UI: http://localhost:$FASTAPI_PORT/api/v1/docs"

echo -e "${GREEN}✨ Documentation is ready for review and deployment!${NC}"