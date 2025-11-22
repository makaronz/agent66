#!/usr/bin/env python3
"""
Enhanced Monitoring Setup Script for SMC Trading Agent

This script sets up the complete enhanced monitoring and analytics dashboard
with all dependencies, configurations, and required services.

Features:
- Installs all required dependencies
- Configures monitoring system
- Sets up WebSocket server
- Initializes dashboards
- Creates configuration files
- Starts all services
"""

import os
import sys
import json
import subprocess
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringSetup:
    """Enhanced monitoring setup and installation manager"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.monitoring_dir = self.project_root / "monitoring"
        self.frontend_dir = self.project_root / "src"

        # Required Python packages
        self.python_packages = [
            "websockets>=10.0",
            "fastapi>=0.68.0",
            "uvicorn>=0.15.0",
            "prometheus-client>=0.11.0",
            "plotly>=5.0.0",
            "psutil>=5.8.0",
            "GPUtil>=1.4.0",
            "aiohttp>=3.7.0",
            "aiohttp-cors>=0.7.0",
            "numpy>=1.21.0",
            "pandas>=1.3.0",
            "scipy>=1.7.0"
        ]

        # Required Node.js packages
        self.node_packages = [
            "recharts@^2.0.0",
            "lucide-react@^0.263.0",
            "tailwindcss@^3.0.0",
            "@headlessui/react@^1.4.0",
            "react-router-dom@^6.0.0"
        ]

    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            logger.error(f"Python 3.8+ required, found {version.major}.{version.minor}")
            return False
        logger.info(f"Python version {version.major}.{version.minor} is compatible")
        return True

    def install_python_dependencies(self) -> bool:
        """Install required Python packages"""
        logger.info("Installing Python dependencies...")

        try:
            # Upgrade pip
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                         check=True)

            # Install packages
            for package in self.python_packages:
                logger.info(f"Installing {package}...")
                subprocess.run([sys.executable, "-m", "pip", "install", package],
                             check=True)

            logger.info("Python dependencies installed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Python dependencies: {e}")
            return False

    def check_node_version(self) -> bool:
        """Check if Node.js is available"""
        try:
            result = subprocess.run(["node", "--version"],
                                  capture_output=True, text=True, check=True)
            version = result.stdout.strip()
            logger.info(f"Node.js version: {version}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Node.js not found. Please install Node.js 16+")
            return False

    def install_node_dependencies(self) -> bool:
        """Install required Node.js packages"""
        logger.info("Installing Node.js dependencies...")

        try:
            # Check if package.json exists
            package_json_path = self.project_root / "package.json"
            if not package_json_path.exists():
                logger.warning("package.json not found, creating basic one...")
                self.create_package_json()

            # Install packages
            subprocess.run(["npm", "install"], cwd=self.project_root, check=True)

            logger.info("Node.js dependencies installed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Node.js dependencies: {e}")
            return False

    def create_package_json(self):
        """Create basic package.json if it doesn't exist"""
        package_json = {
            "name": "smc-trading-dashboard",
            "version": "1.0.0",
            "description": "Enhanced monitoring dashboard for SMC Trading Agent",
            "main": "index.js",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
                "server:dev": "python api/websocket_server.py",
                "monitoring:dev": "python monitoring/real_time_dashboard.py"
            },
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0",
                "recharts": "^2.0.0",
                "lucide-react": "^0.263.0",
                "react-router-dom": "^6.0.0",
                "@headlessui/react": "^1.4.0",
                "tailwindcss": "^3.0.0"
            },
            "devDependencies": {
                "@types/react": "^18.0.0",
                "@types/react-dom": "^18.0.0",
                "@vitejs/plugin-react": "^1.0.0",
                "vite": "^2.0.0",
                "typescript": "^4.0.0"
            }
        }

        package_json_path = self.project_root / "package.json"
        with open(package_json_path, 'w') as f:
            json.dump(package_json, f, indent=2)

    def create_monitoring_config(self):
        """Create monitoring configuration files"""
        logger.info("Creating monitoring configuration...")

        # Create config directory
        self.config_dir.mkdir(exist_ok=True)

        # Create main monitoring config
        monitoring_config = {
            "system": {
                "metrics_collection_interval": 30,
                "health_check_interval": 60,
                "prometheus_port": 8000,
                "websocket_port": 8765
            },
            "alerts": {
                "enable_email": False,
                "enable_slack": False,
                "enable_webhook": True,
                "webhook_url": "http://localhost:3000/api/alerts",
                "severity_thresholds": {
                    "cpu_warning": 70,
                    "cpu_critical": 90,
                    "memory_warning": 80,
                    "memory_critical": 95,
                    "latency_warning": 100,
                    "latency_critical": 500
                }
            },
            "dashboard": {
                "refresh_interval": 2000,
                "max_data_points": 1000,
                "enable_real_time": True,
                "enable_historical": True
            },
            "trading": {
                "monitor_positions": True,
                "monitor_orders": True,
                "monitor_pnl": True,
                "risk_thresholds": {
                    "max_drawdown": 15.0,
                    "max_position_size": 100000,
                    "var_limit": 5000
                }
            }
        }

        config_path = self.config_dir / "monitoring.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(monitoring_config, f, default_flow_style=False)

        logger.info(f"Monitoring config created at {config_path}")

    def create_environment_file(self):
        """Create environment configuration file"""
        logger.info("Creating environment configuration...")

        env_file = self.project_root / ".env.monitoring"

        env_content = """# Enhanced Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_PORT=8765
MONITORING_HOST=localhost

# Prometheus Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8000

# WebSocket Configuration
WEBSOCKET_PORT=8765
WEBSOCKET_HOST=localhost

# Alert Configuration
ALERT_EMAIL_ENABLED=false
ALERT_SLACK_ENABLED=false
ALERT_WEBHOOK_ENABLED=true

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=smc_monitoring
DB_USER=monitoring_user
DB_PASSWORD=secure_password

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# API Configuration
API_HOST=localhost
API_PORT=3000
API_TIMEOUT=30
"""

        with open(env_file, 'w') as f:
            f.write(env_content)

        logger.info(f"Environment file created at {env_file}")

    def create_startup_scripts(self):
        """Create startup scripts for monitoring services"""
        logger.info("Creating startup scripts...")

        # Create startup directory
        startup_dir = self.project_root / "scripts"
        startup_dir.mkdir(exist_ok=True)

        # Create WebSocket server startup script
        websocket_script = startup_dir / "start_websocket.sh"
        websocket_content = """#!/bin/bash
# WebSocket Server Startup Script

echo "Starting WebSocket server for monitoring..."
cd "$(dirname "$0")/.."
source .env.monitoring

python api/websocket_server.py --host $WEBSOCKET_HOST --port $WEBSOCKET_PORT
"""

        with open(websocket_script, 'w') as f:
            f.write(websocket_content)

        # Make script executable
        os.chmod(websocket_script, 0o755)

        # Create monitoring startup script
        monitoring_script = startup_dir / "start_monitoring.sh"
        monitoring_content = """#!/bin/bash
# Enhanced Monitoring Startup Script

echo "Starting enhanced monitoring system..."
cd "$(dirname "$0")/.."
source .env.monitoring

# Start WebSocket server in background
python api/websocket_server.py --host $WEBSOCKET_HOST --port $WEBSOCKET_PORT &
WEBSOCKET_PID=$!

echo "WebSocket server started with PID: $WEBSOCKET_PID"

# Save PID for cleanup
echo $WEBSOCKET_PID > scripts/websocket.pid

echo "Enhanced monitoring system started successfully"
echo "WebSocket server: ws://$WEBSOCKET_HOST:$WEBSOCKET_PORT"
echo "Dashboard: http://localhost:3000"

# Wait for interrupt signal
trap 'kill $WEBSOCKET_PID; rm -f scripts/websocket.pid; echo "Monitoring stopped"; exit' INT
wait $WEBSOCKET_PID
"""

        with open(monitoring_script, 'w') as f:
            f.write(monitoring_content)

        # Make script executable
        os.chmod(monitoring_script, 0o755)

        # Create stop script
        stop_script = startup_dir / "stop_monitoring.sh"
        stop_content = """#!/bin/bash
# Monitoring Stop Script

echo "Stopping enhanced monitoring system..."

if [ -f scripts/websocket.pid ]; then
    PID=$(cat scripts/websocket.pid)
    echo "Stopping WebSocket server (PID: $PID)..."
    kill $PID 2>/dev/null
    rm -f scripts/websocket.pid
    echo "WebSocket server stopped"
else
    echo "No WebSocket server PID file found"
fi

echo "Enhanced monitoring system stopped"
"""

        with open(stop_script, 'w') as f:
            f.write(stop_content)

        # Make script executable
        os.chmod(stop_script, 0o755)

        logger.info("Startup scripts created in scripts/ directory")

    def setup_database_schema(self):
        """Create database schema for monitoring"""
        logger.info("Setting up database schema...")

        # Create SQL schema file
        schema_dir = self.project_root / "database"
        schema_dir.mkdir(exist_ok=True)

        schema_sql = """
-- Enhanced Monitoring Database Schema

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    component VARCHAR(100),
    acknowledged BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    resolved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);

-- Metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit VARCHAR(20),
    tags JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trading signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    entry_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);

-- System health table
CREATE TABLE IF NOT EXISTS system_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    latency_ms DOUBLE PRECISION,
    error_message TEXT,
    last_check TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- Performance history table
CREATE TABLE IF NOT EXISTS performance_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_value DOUBLE PRECISION,
    daily_return DOUBLE PRECISION,
    drawdown DOUBLE PRECISION,
    sharpe_ratio DOUBLE PRECISION,
    win_rate DOUBLE PRECISION,
    total_trades INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_signals_created_at ON trading_signals(created_at);
CREATE INDEX IF NOT EXISTS idx_health_component ON system_health(component);
CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_history(timestamp);
"""

        schema_file = schema_dir / "monitoring_schema.sql"
        with open(schema_file, 'w') as f:
            f.write(schema_sql)

        logger.info(f"Database schema created at {schema_file}")

    def run_system_checks(self) -> bool:
        """Run system compatibility checks"""
        logger.info("Running system compatibility checks...")

        checks = [
            ("Python version", self.check_python_version),
            ("Node.js availability", self.check_node_version)
        ]

        all_passed = True
        for check_name, check_func in checks:
            logger.info(f"Checking {check_name}...")
            if not check_func():
                all_passed = False
                logger.error(f"{check_name} check failed")
            else:
                logger.info(f"{check_name} check passed")

        return all_passed

    def setup_services(self) -> bool:
        """Setup and configure all monitoring services"""
        logger.info("Setting up enhanced monitoring services...")

        steps = [
            ("Installing Python dependencies", self.install_python_dependencies),
            ("Installing Node.js dependencies", self.install_node_dependencies),
            ("Creating monitoring configuration", self.create_monitoring_config),
            ("Creating environment file", self.create_environment_file),
            ("Creating startup scripts", self.create_startup_scripts),
            ("Setting up database schema", self.setup_database_schema)
        ]

        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            if not step_func():
                logger.error(f"Failed to complete: {step_name}")
                return False
            logger.info(f"Completed: {step_name}")

        return True

    def start_services(self):
        """Start all monitoring services"""
        logger.info("Starting enhanced monitoring services...")

        # Start WebSocket server
        try:
            websocket_script = self.project_root / "scripts" / "start_monitoring.sh"
            subprocess.Popen([str(websocket_script)], cwd=self.project_root)
            logger.info("WebSocket server started")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")

    def create_readme(self):
        """Create README with setup instructions"""
        logger.info("Creating documentation...")

        readme_content = """# Enhanced Monitoring Dashboard for SMC Trading Agent

A comprehensive real-time monitoring and analytics dashboard for the Smart Money Concepts (SMC) Trading Agent.

## Features

### Real-Time Performance Dashboard
- Live trading metrics and performance indicators
- System resource monitoring (CPU, memory, latency)
- Trading signal quality metrics
- P&L tracking and risk metrics
- Interactive visualizations with Plotly

### Business Intelligence Analytics
- Trading performance analytics
- Pattern detection effectiveness metrics
- ML model performance tracking
- Risk management analytics
- Portfolio performance dashboard

### Alerting System
- Multi-severity alert configuration
- Real-time notification system
- Circuit breaker status monitoring
- Performance degradation alerts
- Regulatory compliance alerts

### Historical Analysis Tools
- Long-term performance trending
- Backtest result visualization
- Market regime analysis
- Risk metric historical tracking
- Strategy effectiveness analytics

## Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL (optional, for persistent storage)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
# Working directory is now the project root
```

2. Run the setup script:
```bash
python setup_enhanced_monitoring.py
```

This will:
- Install all required dependencies
- Create configuration files
- Set up the database schema
- Create startup scripts

### Configuration

Edit `.env.monitoring` to configure:
- WebSocket server settings
- Alert thresholds
- Database connections
- API endpoints

### Starting the Services

#### Option 1: Using the startup script
```bash
./scripts/start_monitoring.sh
```

#### Option 2: Manual startup
```bash
# Start WebSocket server
python api/websocket_server.py

# Start frontend development server
npm run dev
```

### Accessing the Dashboard

- Real-Time Dashboard: http://localhost:3000/
- Business Intelligence: http://localhost:3000/analytics
- Alerts Center: http://localhost:3000/alerts
- Historical Analysis: http://localhost:3000/historical

## Architecture

### Backend Components

- **WebSocket Server** (`api/websocket_server.py`): Real-time data streaming
- **Enhanced Monitoring** (`monitoring/enhanced_monitoring.py`): Metrics collection
- **Real-Time Dashboard** (`monitoring/real_time_dashboard.py`): Data management
- **Grafana Integration** (`monitoring/grafana_dashboards.py`): Dashboard management

### Frontend Components

- **Enhanced Dashboard** (`src/components/EnhancedDashboard.tsx`): Main real-time view
- **Business Intelligence** (`src/components/BusinessIntelligence.tsx`): Analytics and BI
- **Real-Time Alerts** (`src/components/RealTimeAlerts.tsx`): Alert management
- **Historical Analysis** (`src/components/HistoricalAnalysis.tsx`): Historical data analysis
- **Monitoring Dashboard** (`src/components/MonitoringDashboard.tsx`): Main orchestrator

### Data Flow

1. **Metrics Collection**: System and trading metrics are collected continuously
2. **WebSocket Streaming**: Real-time data is streamed to connected clients
3. **Frontend Visualization**: React components display data in real-time
4. **Alert Processing**: Alerts are generated and distributed based on thresholds
5. **Historical Storage**: Data is stored for historical analysis

## Configuration

### Alert Thresholds

Configure alert thresholds in `config/monitoring.yaml`:

```yaml
alerts:
  severity_thresholds:
    cpu_warning: 70
    cpu_critical: 90
    memory_warning: 80
    memory_critical: 95
    latency_warning: 100
    latency_critical: 500
```

### WebSocket Settings

Configure WebSocket server:

```yaml
system:
  websocket_port: 8765
  websocket_host: localhost
  metrics_collection_interval: 30
```

### Dashboard Settings

Configure dashboard behavior:

```yaml
dashboard:
  refresh_interval: 2000
  max_data_points: 1000
  enable_real_time: true
  enable_historical: true
```

## API Endpoints

### WebSocket Endpoints

- `ws://localhost:8765/` - Main WebSocket connection
- Subscriptions: `metrics`, `alerts`, `signals`, `health`, `market_data`

### REST API Endpoints

- `GET /api/metrics` - Get current metrics
- `GET /api/alerts` - Get active alerts
- `GET /api/health` - Get system health
- `POST /api/alerts/{id}/acknowledge` - Acknowledge alert

## Monitoring

### System Health

The dashboard monitors:
- CPU and memory usage
- Database connectivity
- API response times
- WebSocket connection status

### Trading Metrics

- Portfolio performance
- Trade execution statistics
- Signal quality metrics
- Risk management indicators

### Alert Management

- Real-time alert notifications
- Alert acknowledgment and resolution
- Historical alert tracking
- Multi-channel alert delivery

## Development

### Running in Development Mode

```bash
# Backend
python api/websocket_server.py

# Frontend
npm run dev
```

### Building for Production

```bash
# Frontend
npm run build

# Backend
export NODE_ENV=production
python api/websocket_server.py
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test suites
python -m pytest tests/test_monitoring.py
python -m pytest tests/test_websocket_server.py
```

## Troubleshooting

### Common Issues

1. **WebSocket connection failed**
   - Check if the WebSocket server is running
   - Verify port configuration in `.env.monitoring`

2. **No data displaying**
   - Check system health status
   - Verify monitoring system is enabled

3. **Alerts not working**
   - Check alert thresholds in configuration
   - Verify alert notification settings

### Logs

Check logs for debugging:
- WebSocket server: Check console output
- Frontend: Check browser console
- System: Check monitoring logs

## Security

### Authentication

Configure JWT authentication in `.env.monitoring`:

```bash
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
```

### Access Control

Restrict access to sensitive endpoints:
- Configure user permissions
- Set up role-based access control
- Enable HTTPS in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the troubleshooting section
- Review the documentation
- Open an issue on GitHub
"""

        readme_path = self.project_root / "ENHANCED_MONITORING_README.md"
        with open(readme_path, 'w') as f:
            f.write(readme_content)

        logger.info(f"Documentation created at {readme_path}")

    def run_setup(self):
        """Run complete setup process"""
        logger.info("Starting enhanced monitoring setup...")

        # Print banner
        self.print_banner()

        # Run system checks
        if not self.run_system_checks():
            logger.error("System compatibility checks failed. Please fix issues and retry.")
            return False

        # Setup services
        if not self.setup_services():
            logger.error("Service setup failed. Please check logs for details.")
            return False

        # Create documentation
        self.create_readme()

        # Print completion message
        self.print_completion_message()

        return True

    def print_banner(self):
        """Print setup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║           Enhanced Monitoring Setup for SMC Trading Agent        ║
╠══════════════════════════════════════════════════════════════╣
║  This script will install and configure:                        ║
║  • Real-time WebSocket server                                   ║
║  • Enhanced monitoring dashboard                                ║
║  • Business intelligence analytics                               ║
║  • Alerting system                                              ║
║  • Historical analysis tools                                   ║
║  • All required dependencies                                   ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)

    def print_completion_message(self):
        """Print completion message"""
        message = f"""
╔══════════════════════════════════════════════════════════════╗
║                     Setup Complete!                            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Enhanced monitoring has been successfully installed!          ║
║                                                              ║
║  Next steps:                                                 ║
║  1. Review configuration in .env.monitoring                   ║
║  2. Start the services:                                      ║
║     ./scripts/start_monitoring.sh                            ║
║  3. Access the dashboard:                                     ║
║     http://localhost:3000                                    ║
║                                                              ║
║  Services:                                                   ║
║  • WebSocket Server: ws://localhost:8765                     ║
║  • Real-Time Dashboard: http://localhost:3000                ║
║  • Business Intelligence: http://localhost:3000/analytics   ║
║  • Alerts Center: http://localhost:3000/alerts              ║
║  • Historical Analysis: http://localhost:3000/historical     ║
║                                                              ║
║  Documentation:                                              ║
║  See ENHANCED_MONITORING_README.md for detailed usage         ║
║                                                              ║
║  To stop services:                                           ║
║  ./scripts/stop_monitoring.sh                                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(message)


def main():
    """Main setup function"""
    setup = MonitoringSetup()

    try:
        success = setup.run_setup()
        if success:
            logger.info("Setup completed successfully!")
            sys.exit(0)
        else:
            logger.error("Setup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()