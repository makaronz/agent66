# Spawn API Documentation

## Overview

The Spawn API provides comprehensive process management capabilities for the SMC Trading Agent system, with specialized support for Serena MCP agents. It enables spawning, monitoring, and lifecycle management of various processes including trading agents, data pipelines, ML models, and development tools.

## Architecture

### Core Components

- **SpawnManager**: Core process lifecycle management
- **SerenaAgentSpawner**: Specialized spawner for Serena MCP agents
- **SpawnMemoryIntegration**: Integration with Serena's memory system
- **Database Models**: Persistent storage for configurations and status

### Key Features

- Process spawning with health monitoring
- Automatic restart and recovery
- Memory integration with Serena MCP
- Template-based process creation
- Real-time event streaming
- Performance metrics collection
- Circuit breaker protection

## API Endpoints

### Basic Process Management

#### Spawn a Process
```http
POST /api/spawn/process
Content-Type: application/json

{
  "id": "trading-agent-1",
  "name": "Primary Trading Agent",
  "type": "trading_agent",
  "command": "python",
  "args": ["run_smc_agent.py", "--mode", "production"],
  "cwd": "/path/to/project",
  "env": {
    "PYTHONPATH": ".",
    "LOG_LEVEL": "INFO"
  },
  "resources": {
    "cpu": 50,
    "memory": 2048,
    "disk": 1024
  },
  "autoRestart": true,
  "healthCheck": {
    "endpoint": "http://localhost:8080/health",
    "interval": 30000,
    "timeout": 5000
  },
  "dependencies": ["data-pipeline-1"],
  "tags": ["trading", "production", "smc"]
}
```

#### Get All Processes
```http
GET /api/spawn/processes?status=running&type=trading_agent&limit=20&offset=0
```

#### Get Specific Process
```http
GET /api/spawn/process/{id}
```

#### Stop Process
```http
POST /api/spawn/process/{id}/stop
Content-Type: application/json

{
  "graceful": true
}
```

#### Restart Process
```http
POST /api/spawn/process/{id}/restart
```

#### Update Configuration
```http
PUT /api/spawn/process/{id}/config
Content-Type: application/json

{
  "autoRestart": false,
  "resources": {
    "cpu": 75,
    "memory": 4096
  }
}
```

### Templates

#### Get Templates
```http
GET /api/spawn/templates
```

#### Spawn from Template
```http
POST /api/spawn/from-template
Content-Type: application/json

{
  "templateId": "trading-agent-template",
  "overrides": {
    "id": "my-trading-agent",
    "name": "My Trading Agent",
    "env": {
      "CUSTOM_VAR": "value"
    }
  }
}
```

### Monitoring and Logs

#### Get Process Logs
```http
GET /api/spawn/process/{id}/logs?lines=100&level=error
```

#### Get System Metrics
```http
GET /api/spawn/metrics
```

#### Real-time Events (SSE)
```javascript
const eventSource = new EventSource('/api/spawn/events');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Spawn event:', data);
};
```

## Serena MCP Agent Management

### Project Management

#### Get Available Projects
```http
GET /api/serena-spawn/projects
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "smc-trading-agent",
      "name": "SMC Trading Agent",
      "path": "/path/to/project",
      "type": "ml",
      "languages": ["python", "rust", "typescript"],
      "lastActive": "2024-01-15T10:30:00Z",
      "agentStatus": "inactive"
    }
  ]
}
```

### Agent Management

#### Spawn Serena Agent
```http
POST /api/serena-spawn/agent
Content-Type: application/json

{
  "projectId": "smc-trading-agent",
  "agentName": "Code Analysis Agent",
  "agentType": "project_analyzer",
  "modes": ["planning", "introspection"],
  "tools": ["file_tools", "symbol_tools", "memory_tools"],
  "languageServers": ["python", "rust"],
  "memoryEnabled": true,
  "dashboardEnabled": true
}
```

#### Spawn Project Agent
```http
POST /api/serena-spawn/project-agent
Content-Type: application/json

{
  "projectPath": "/path/to/project",
  "agentType": "code_editor"
}
```

#### Get Serena Agents
```http
GET /api/serena-spawn/agents?status=running&type=project_analyzer
```

#### Stop/Restart Agent
```http
POST /api/serena-spawn/agent/{id}/stop
POST /api/serena-spawn/agent/{id}/restart
```

### Memory Integration

#### Get Agent Memory
```http
GET /api/serena-spawn/agent/{id}/memory
```

#### Get Agent Events
```http
GET /api/serena-spawn/agent/{id}/events?limit=50
```

#### Get Performance Metrics
```http
GET /api/serena-spawn/agent/{id}/metrics?timeRange=24h
```

#### Search Memories
```http
GET /api/serena-spawn/search?q=trading+strategy&type=spawn_event&tags=production
```

### Templates and Migration

#### Get Serena Templates
```http
GET /api/serena-spawn/templates
```

#### Spawn from Template
```http
POST /api/serena-spawn/from-template
Content-Type: application/json

{
  "templateId": "project-analyzer-template",
  "agentName": "My Project Analyzer",
  "projectPath": "/path/to/project",
  "overrides": {
    "modes": ["editing"],
    "memoryEnabled": false
  }
}
```

#### Export/Import Agent Data
```http
POST /api/serena-spawn/agent/{id}/export
POST /api/serena-spawn/import
```

#### Cleanup Old Data
```http
POST /api/serena-spawn/cleanup
Content-Type: application/json

{
  "retentionDays": 30
}
```

## Process Types

### Standard Types
- `trading_agent`: SMC trading strategy agents
- `strategy`: Individual trading strategy execution
- `data_pipeline`: Market data ingestion and processing
- `ml_model`: Machine learning model serving
- `monitor`: System monitoring and health checks

### Serena Agent Types
- `project_analyzer`: Code analysis and project structure understanding
- `code_editor`: Symbol-aware code editing and refactoring
- `symbol_operator`: Advanced symbol operations and navigation
- `workflow_manager`: Complex workflow orchestration

## Configuration Reference

### SpawnConfig Schema

```typescript
interface SpawnConfig {
  id: string;                    // Unique process identifier
  name: string;                  // Human-readable name
  type: ProcessType;            // Process type
  command: string;              // Command to execute
  args: string[];               // Command arguments
  cwd?: string;                 // Working directory
  env?: Record<string, string>; // Environment variables
  resources?: {                 // Resource limits
    cpu: number;        // CPU percentage (0-100)
    memory: number;     // Memory in MB
    disk: number;       // Disk space in MB
  };
  autoRestart?: boolean;        // Auto-restart on failure
  healthCheck?: {               // Health check configuration
    endpoint?: string;   // HTTP endpoint to check
    interval: number;    // Check interval in ms
    timeout: number;     // Check timeout in ms
  };
  dependencies?: string[];      // Required dependencies
  tags?: string[];              // Process tags
}
```

### SerenaAgentConfig Schema

```typescript
interface SerenaAgentConfig {
  projectId?: string;           // Project identifier
  projectPath?: string;         // Project file path
  agentName: string;            // Agent name
  agentType: AgentType;        // Agent type
  modes?: string[];             // Serena modes
  context?: string;             // Agent context
  tools?: string[];             // Enabled tools
  languageServers?: string[];   // Language servers
  memoryEnabled?: boolean;      // Enable memory system
  dashboardEnabled?: boolean;   // Enable web dashboard
  customConfig?: Record<string, any>; // Custom configuration
}
```

## Error Handling

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (validation error)
- `404`: Not Found
- `500`: Internal Server Error

### Error Response Format
```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional error details"
}
```

### Common Error Scenarios
1. **Invalid Configuration**: Missing required fields or invalid values
2. **Process Not Found**: Trying to operate on non-existent process
3. **Dependency Issues**: Required dependencies not available
4. **Resource Limits**: Insufficient system resources
5. **Permission Issues**: Insufficient permissions for operations

## Monitoring and Observability

### Health Checks
Processes are monitored through:
- HTTP endpoint polling (if specified)
- Process existence checking
- Resource usage monitoring

### Metrics Collection
- CPU and memory usage
- Process uptime and restarts
- Health check success/failure rates
- Log aggregation and filtering

### Event Types
- `spawned`: Process successfully started
- `stopped`: Process stopped (gracefully or forcefully)
- `restarted`: Process restarted
- `error`: Process error or crash
- `unhealthy`: Health check failure
- `health_check_passed`: Successful health check
- `health_check_failed`: Failed health check

## Security Considerations

### Process Isolation
- Each process runs in its own subprocess
- Environment variables are isolated per process
- Resource limits prevent resource exhaustion

### Access Control
- Process operations require proper authorization
- File system access is limited to specified directories
- Network access is controlled through firewall rules

### Data Protection
- Sensitive configuration data is encrypted at rest
- Process logs may contain sensitive information
- Memory data follows Serena's security model

## Performance Considerations

### Resource Management
- CPU limits prevent excessive CPU usage
- Memory limits prevent memory exhaustion
- Disk limits prevent storage overflow

### Scalability
- Circuit breakers prevent cascade failures
- Process pools manage concurrent operations
- Rate limiting prevents API abuse

### Optimization
- Process reuse where possible
- Efficient log rotation and cleanup
- Lazy loading of non-critical components

## Integration Examples

### Frontend Integration (React)
```typescript
// Spawn a new trading agent
const spawnAgent = async (config: SpawnConfig) => {
  try {
    const response = await fetch('/api/spawn/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    const result = await response.json();
    if (result.success) {
      return result.data;
    } else {
      throw new Error(result.error);
    }
  } catch (error) {
    console.error('Failed to spawn agent:', error);
    throw error;
  }
};

// Listen for real-time events
const eventSource = new EventSource('/api/spawn/events');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateProcessStatus(data);
};
```

### Python Backend Integration
```python
import requests
import asyncio

class SpawnClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    async def spawn_process(self, config: dict) -> dict:
        response = requests.post(
            f"{self.base_url}/api/spawn/process",
            json=config
        )
        response.raise_for_status()
        return response.json()

    async def get_process_status(self, process_id: str) -> dict:
        response = requests.get(
            f"{self.base_url}/api/spawn/process/{process_id}"
        )
        response.raise_for_status()
        return response.json()

# Usage
client = SpawnClient('http://localhost:3001')
config = {
    'id': 'my-agent',
    'name': 'My Agent',
    'type': 'trading_agent',
    'command': 'python',
    'args': ['agent.py'],
    'autoRestart': True
}
result = await client.spawn_process(config)
```

## Troubleshooting

### Common Issues

1. **Process Fails to Start**
   - Check command and arguments
   - Verify working directory exists
   - Check environment variables

2. **Health Check Failures**
   - Verify endpoint accessibility
   - Check timeout values
   - Review endpoint response format

3. **Memory Issues**
   - Monitor memory usage
   - Check for memory leaks
   - Adjust resource limits

4. **Performance Issues**
   - Review resource allocation
   - Check system load
   - Optimize process configuration

### Debugging Tools

- **Process Logs**: Check `/api/spawn/process/{id}/logs`
- **System Metrics**: Monitor `/api/spawn/metrics`
- **Event Stream**: Listen to `/api/spawn/events`
- **Health Status**: Check individual process health

### Log Analysis
```bash
# View process logs
curl "http://localhost:3001/api/spawn/process/my-agent/logs?lines=100"

# Monitor system metrics
curl "http://localhost:3001/api/spawn/metrics"

# Search specific events
curl "http://localhost:3001/api/serena-spawn/search?q=error"
```

## Future Enhancements

### Planned Features
- Container support (Docker/Kubernetes)
- Distributed process coordination
- Advanced resource scheduling
- Process templates marketplace
- Enhanced security features

### API Evolution
- Versioned API endpoints
- Backward compatibility guarantees
- Deprecation policies
- Migration guides

## Support

### Documentation
- API reference: Available at `/api/docs`
- Interactive examples: Available at `/api/examples`
- Troubleshooting guide: Available at `/docs/troubleshooting`

### Community
- GitHub Issues: Report bugs and feature requests
- Discord Server: Real-time support and discussions
- Stack Overflow: Tag questions with `smc-trading-agent`

### Contact
- Technical Support: support@example.com
- Security Issues: security@example.com
- General Inquiries: info@example.com