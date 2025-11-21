/**
 * Spawn API Routes
 * REST API for managing spawned processes and agents
 */

import { Router, type Request, type Response } from 'express';
import { spawnManager, SpawnConfig } from '../services/spawnManager';
import { CircuitBreakerRegistry } from '../utils/circuitBreaker';
import { z } from 'zod';

const router = Router();

// Initialize circuit breaker for spawn operations
const circuitBreakerRegistry = CircuitBreakerRegistry.getInstance();
const spawnCircuitBreaker = circuitBreakerRegistry.create('spawn_api', {
  failureThreshold: 3,
  resetTimeout: 60000,
  monitoringPeriod: 15000,
  halfOpenMaxCalls: 2
}, 'spawn_api');

// Validation schemas
const spawnConfigSchema = z.object({
  id: z.string().min(1).max(100),
  name: z.string().min(1).max(200),
  type: z.enum(['trading_agent', 'strategy', 'data_pipeline', 'ml_model', 'monitor']),
  command: z.string().min(1),
  args: z.array(z.string()).default([]),
  cwd: z.string().optional(),
  env: z.record(z.string()).optional(),
  resources: z.object({
    cpu: z.number().min(0).max(100),
    memory: z.number().min(0),
    disk: z.number().min(0)
  }).optional(),
  autoRestart: z.boolean().default(false),
  healthCheck: z.object({
    endpoint: z.string().url().optional(),
    interval: z.number().min(1000),
    timeout: z.number().min(100)
  }).optional(),
  dependencies: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional()
});

const updateConfigSchema = spawnConfigSchema.partial().omit(['id', 'name']);

/**
 * POST /api/spawn/process
 * Spawn a new process
 */
router.post('/process', async (req: Request, res: Response) => {
  try {
    const validatedConfig = spawnConfigSchema.parse(req.body);

    const result = await spawnCircuitBreaker.execute(async () => {
      return await spawnManager.spawnProcess(validatedConfig);
    }, 'spawn_process');

    res.json({
      success: true,
      data: result,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error spawning process:', error);

    if (error.name === 'ZodError') {
      return res.status(400).json({
        success: false,
        error: 'Invalid configuration',
        details: error.errors
      });
    }

    res.status(500).json({
      success: false,
      error: error.message || 'Failed to spawn process'
    });
  }
});

/**
 * GET /api/spawn/processes
 * Get status of all processes
 */
router.get('/processes', async (req: Request, res: Response) => {
  try {
    const result = await spawnCircuitBreaker.execute(async () => {
      return spawnManager.getAllStatus();
    });

    // Add filtering and pagination
    const { status, type, tags, limit = 50, offset = 0 } = req.query;

    let filtered = result;

    if (status) {
      filtered = filtered.filter(p => p.status === status);
    }

    if (type) {
      const configs = Array.from(spawnManager['configs'].values());
      const ids = configs
        .filter(c => c.type === type)
        .map(c => c.id);
      filtered = filtered.filter(p => ids.includes(p.id));
    }

    if (tags) {
      const tagArray = Array.isArray(tags) ? tags : [tags];
      const configs = Array.from(spawnManager['configs'].values());
      const ids = configs
        .filter(c => tagArray.some(tag => c.tags?.includes(tag)))
        .map(c => c.id);
      filtered = filtered.filter(p => ids.includes(p.id));
    }

    const paginated = filtered.slice(parseInt(offset as string), parseInt(offset as string) + parseInt(limit as string));

    res.json({
      success: true,
      data: {
        processes: paginated,
        total: filtered.length,
        limit: parseInt(limit as string),
        offset: parseInt(offset as string)
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting processes:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get processes'
    });
  }
});

/**
 * GET /api/spawn/process/:id
 * Get status of specific process
 */
router.get('/process/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const result = await spawnCircuitBreaker.execute(async () => {
      return spawnManager.getStatus(id);
    });

    if (!result) {
      return res.status(404).json({
        success: false,
        error: 'Process not found'
      });
    }

    // Include configuration in response
    const config = spawnManager['configs'].get(id);

    res.json({
      success: true,
      data: {
        ...result,
        config: config || null
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting process status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get process status'
    });
  }
});

/**
 * POST /api/spawn/process/:id/stop
 * Stop a process
 */
router.post('/process/:id/stop', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { graceful = true } = req.body;

    await spawnCircuitBreaker.execute(async () => {
      return await spawnManager.stopProcess(id, graceful);
    });

    res.json({
      success: true,
      message: 'Process stopped successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error stopping process:', error);

    if (error.message.includes('not found')) {
      return res.status(404).json({
        success: false,
        error: 'Process not found'
      });
    }

    res.status(500).json({
      success: false,
      error: 'Failed to stop process'
    });
  }
});

/**
 * POST /api/spawn/process/:id/restart
 * Restart a process
 */
router.post('/process/:id/restart', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const result = await spawnCircuitBreaker.execute(async () => {
      return await spawnManager.restartProcess(id);
    });

    res.json({
      success: true,
      data: result,
      message: 'Process restarted successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error restarting process:', error);

    if (error.message.includes('not found')) {
      return res.status(404).json({
        success: false,
        error: 'Process not found'
      });
    }

    res.status(500).json({
      success: false,
      error: 'Failed to restart process'
    });
  }
});

/**
 * PUT /api/spawn/process/:id/config
 * Update process configuration
 */
router.put('/process/:id/config', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const validatedUpdates = updateConfigSchema.parse(req.body);

    await spawnCircuitBreaker.execute(async () => {
      return await spawnManager.updateConfig(id, validatedUpdates);
    });

    res.json({
      success: true,
      message: 'Configuration updated successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error updating config:', error);

    if (error.name === 'ZodError') {
      return res.status(400).json({
        success: false,
        error: 'Invalid configuration',
        details: error.errors
      });
    }

    if (error.message.includes('not found')) {
      return res.status(404).json({
        success: false,
        error: 'Process not found'
      });
    }

    res.status(500).json({
      success: false,
      error: 'Failed to update configuration'
    });
  }
});

/**
 * GET /api/spawn/process/:id/logs
 * Get process logs
 */
router.get('/process/:id/logs', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { lines = 100, level } = req.query;

    const logs = await spawnCircuitBreaker.execute(async () => {
      return await spawnManager.getLogs(id, parseInt(lines as string));
    });

    const status = spawnManager.getStatus(id);

    // Filter by level if specified
    let filteredLogs = logs;
    if (level && status) {
      filteredLogs = status.logs
        .filter(log => log.level === level)
        .slice(-parseInt(lines as string))
        .map(log => `[${log.timestamp.toISOString()}] ${log.level.toUpperCase()}: ${log.message}`);
    }

    res.json({
      success: true,
      data: {
        logs: filteredLogs,
        count: filteredLogs.length,
        totalLines: logs.length
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting logs:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get logs'
    });
  }
});

/**
 * GET /api/spawn/templates
 * Get predefined process templates
 */
router.get('/templates', async (req: Request, res: Response) => {
  try {
    const templates = [
      {
        id: 'trading-agent-template',
        name: 'Trading Agent Template',
        type: 'trading_agent',
        description: 'Standard SMC trading agent configuration',
        command: 'python',
        args: ['run_smc_agent.py'],
        env: {
          PYTHONPATH: '.',
          LOG_LEVEL: 'INFO'
        },
        resources: {
          cpu: 50,
          memory: 2048,
          disk: 1024
        },
        autoRestart: true,
        healthCheck: {
          interval: 30000,
          timeout: 5000
        },
        tags: ['trading', 'smc', 'agent']
      },
      {
        id: 'data-pipeline-template',
        name: 'Data Pipeline Template',
        type: 'data_pipeline',
        description: 'Market data ingestion pipeline',
        command: 'python',
        args: ['data_pipeline/main.py'],
        env: {
          PYTHONPATH: '.',
          LOG_LEVEL: 'INFO'
        },
        resources: {
          cpu: 30,
          memory: 1024,
          disk: 512
        },
        autoRestart: true,
        healthCheck: {
          interval: 15000,
          timeout: 3000
        },
        tags: ['data', 'pipeline', 'ingestion']
      },
      {
        id: 'strategy-runner-template',
        name: 'Strategy Runner Template',
        type: 'strategy',
        description: 'Individual strategy execution environment',
        command: 'python',
        args: ['run_strategy.py'],
        env: {
          PYTHONPATH: '.',
          LOG_LEVEL: 'INFO'
        },
        resources: {
          cpu: 25,
          memory: 512,
          disk: 256
        },
        autoRestart: false,
        healthCheck: {
          interval: 60000,
          timeout: 10000
        },
        tags: ['strategy', 'trading']
      },
      {
        id: 'ml-model-template',
        name: 'ML Model Template',
        type: 'ml_model',
        description: 'Machine learning model serving',
        command: 'python',
        args: ['-m', 'ml.serve_model'],
        env: {
          PYTHONPATH: '.',
          LOG_LEVEL: 'INFO'
        },
        resources: {
          cpu: 70,
          memory: 4096,
          disk: 2048
        },
        autoRestart: true,
        healthCheck: {
          endpoint: 'http://localhost:8080/health',
          interval: 10000,
          timeout: 3000
        },
        tags: ['ml', 'model', 'prediction']
      }
    ];

    res.json({
      success: true,
      data: templates,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting templates:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get templates'
    });
  }
});

/**
 * POST /api/spawn/from-template
 * Spawn process from template
 */
router.post('/from-template', async (req: Request, res: Response) => {
  try {
    const { templateId, overrides } = req.body;

    if (!templateId) {
      return res.status(400).json({
        success: false,
        error: 'Template ID is required'
      });
    }

    // Get templates and find the requested one
    const templatesResponse = await fetch(`${req.protocol}://${req.get('host')}/api/spawn/templates`);
    const templatesData = await templatesResponse.json();

    if (!templatesData.success) {
      throw new Error('Failed to get templates');
    }

    const template = templatesData.data.find((t: any) => t.id === templateId);
    if (!template) {
      return res.status(404).json({
        success: false,
        error: 'Template not found'
      });
    }

    // Create config from template with overrides
    const config: SpawnConfig = {
      id: overrides?.id || `${template.type}-${Date.now()}`,
      name: overrides?.name || `${template.name} - ${new Date().toISOString()}`,
      type: template.type,
      command: template.command,
      args: template.args,
      env: { ...template.env, ...overrides?.env },
      resources: { ...template.resources, ...overrides?.resources },
      autoRestart: overrides?.autoRestart ?? template.autoRestart,
      healthCheck: { ...template.healthCheck, ...overrides?.healthCheck },
      tags: template.tags,
      ...overrides
    };

    const result = await spawnCircuitBreaker.execute(async () => {
      return await spawnManager.spawnProcess(config);
    });

    res.json({
      success: true,
      data: result,
      message: `Process spawned from template ${templateId}`,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error spawning from template:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to spawn from template'
    });
  }
});

/**
 * GET /api/spawn/metrics
 * Get system metrics for spawned processes
 */
router.get('/metrics', async (req: Request, res: Response) => {
  try {
    const processes = spawnManager.getAllStatus();

    const metrics = {
      total: processes.length,
      running: processes.filter(p => p.status === 'running').length,
      stopped: processes.filter(p => p.status === 'stopped').length,
      error: processes.filter(p => p.status === 'error').length,
      starting: processes.filter(p => p.status === 'starting').length,
      restarting: processes.filter(p => p.status === 'restarting').length,

      resourceUsage: {
        totalCpu: processes.reduce((sum, p) => sum + (p.resourceUsage?.cpu || 0), 0),
        totalMemory: processes.reduce((sum, p) => sum + (p.resourceUsage?.memory || 0), 0),
        totalDisk: processes.reduce((sum, p) => sum + (p.resourceUsage?.disk || 0), 0)
      },

      uptime: {
        longestRunningProcess: processes
          .filter(p => p.startTime && p.status === 'running')
          .sort((a, b) => (a.startTime?.getTime() || 0) - (b.startTime?.getTime() || 0))[0]?.startTime,
        averageUptime: 0 // Would need more complex calculation
      }
    };

    res.json({
      success: true,
      data: metrics,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get metrics'
    });
  }
});

// Event handlers for real-time updates
router.get('/events', (req: Request, res: Response) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*'
  });

  // Send initial connection message
  res.write('data: {"type": "connected", "timestamp": "' + new Date().toISOString() + '"}\n\n');

  // Setup event listeners
  const handlers = {
    'process:spawned': (data: any) => {
      res.write(`data: ${JSON.stringify({ type: 'spawned', data })}\n\n`);
    },
    'process:stopped': (data: any) => {
      res.write(`data: ${JSON.stringify({ type: 'stopped', data })}\n\n`);
    },
    'process:restarted': (data: any) => {
      res.write(`data: ${JSON.stringify({ type: 'restarted', data })}\n\n`);
    },
    'process:error': (data: any) => {
      res.write(`data: ${JSON.stringify({ type: 'error', data })}\n\n`);
    },
    'process:unhealthy': (data: any) => {
      res.write(`data: ${JSON.stringify({ type: 'unhealthy', data })}\n\n`);
    }
  };

  // Register event listeners
  Object.entries(handlers).forEach(([event, handler]) => {
    spawnManager.on(event, handler);
  });

  // Cleanup on client disconnect
  req.on('close', () => {
    Object.entries(handlers).forEach(([event, handler]) => {
      spawnManager.off(event, handler);
    });
  });
});

export default router;