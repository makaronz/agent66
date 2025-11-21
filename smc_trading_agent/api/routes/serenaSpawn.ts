/**
 * Serena Spawn Routes
 * Specialized routes for spawning Serena MCP agents
 */

import { Router, type Request, type Response } from 'express';
import { serenaAgentSpawner, SerenaAgentConfig } from '../services/serenaAgentSpawner';
import { spawnMemoryIntegration } from '../services/spawnMemoryIntegration';
import { CircuitBreakerRegistry } from '../utils/circuitBreaker';
import { z } from 'zod';

const router = Router();

// Initialize circuit breaker
const circuitBreakerRegistry = CircuitBreakerRegistry.getInstance();
const serenaSpawnCircuitBreaker = circuitBreakerRegistry.create('serena_spawn_api', {
  failureThreshold: 3,
  resetTimeout: 60000,
  monitoringPeriod: 15000,
  halfOpenMaxCalls: 2
}, 'serena_spawn_api');

// Validation schemas
const serenaAgentConfigSchema = z.object({
  projectId: z.string().optional(),
  projectPath: z.string().optional(),
  agentName: z.string().min(1).max(200),
  agentType: z.enum(['project_analyzer', 'code_editor', 'symbol_operator', 'workflow_manager']),
  modes: z.array(z.string()).optional(),
  context: z.string().optional(),
  tools: z.array(z.string()).optional(),
  languageServers: z.array(z.string()).optional(),
  memoryEnabled: z.boolean().default(true),
  dashboardEnabled: z.boolean().default(true),
  customConfig: z.record(z.any()).optional()
});

/**
 * GET /api/serena-spawn/projects
 * Get available Serena projects
 */
router.get('/projects', async (req: Request, res: Response) => {
  try {
    const projects = await serenaSpawnCircuitBreaker.execute(async () => {
      return await serenaAgentSpawner.getAvailableProjects();
    });

    res.json({
      success: true,
      data: projects,
      count: projects.length,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting Serena projects:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get Serena projects'
    });
  }
});

/**
 * POST /api/serena-spawn/agent
 * Spawn a new Serena agent
 */
router.post('/agent', async (req: Request, res: Response) => {
  try {
    const validatedConfig = serenaAgentConfigSchema.parse(req.body);

    const result = await serenaSpawnCircuitBreaker.execute(async () => {
      return await serenaAgentSpawner.spawnSerenaAgent(validatedConfig);
    }, 'spawn_serena_agent');

    res.json({
      success: true,
      data: result,
      message: `Serena agent "${validatedConfig.agentName}" spawned successfully`,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error spawning Serena agent:', error);

    if (error.name === 'ZodError') {
      return res.status(400).json({
        success: false,
        error: 'Invalid configuration',
        details: error.errors
      });
    }

    res.status(500).json({
      success: false,
      error: error.message || 'Failed to spawn Serena agent'
    });
  }
});

/**
 * POST /api/serena-spawn/project-agent
 * Spawn Serena agent for specific project
 */
router.post('/project-agent', async (req: Request, res: Response) => {
  try {
    const { projectPath, agentType = 'project_analyzer' } = req.body;

    if (!projectPath) {
      return res.status(400).json({
        success: false,
        error: 'projectPath is required'
      });
    }

    const result = await serenaSpawnCircuitBreaker.execute(async () => {
      return await serenaAgentSpawner.spawnProjectAgent(projectPath, agentType);
    });

    res.json({
      success: true,
      data: result,
      message: `Serena agent spawned for project at ${projectPath}`,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error spawning project agent:', error);
    res.status(500).json({
      success: false,
      error: error.message || 'Failed to spawn project agent'
    });
  }
});

/**
 * GET /api/serena-spawn/agents
 * Get all spawned Serena agents
 */
router.get('/agents', async (req: Request, res: Response) => {
  try {
    const { status, type } = req.query;

    let agents = await serenaSpawnCircuitBreaker.execute(async () => {
      return await serenaAgentSpawner.getSerenaAgents();
    });

    // Apply filters
    if (status) {
      agents = agents.filter(agent => agent.status === status);
    }

    if (type) {
      agents = agents.filter(agent =>
        agent.name.toLowerCase().includes(type.toString().toLowerCase())
      );
    }

    res.json({
      success: true,
      data: agents,
      count: agents.length,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting Serena agents:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get Serena agents'
    });
  }
});

/**
 * POST /api/serena-spawn/agent/:id/stop
 * Stop a Serena agent
 */
router.post('/agent/:id/stop', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    await serenaSpawnCircuitBreaker.execute(async () => {
      return await serenaAgentSpawner.stopSerenaAgent(id);
    });

    res.json({
      success: true,
      message: 'Serena agent stopped successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error stopping Serena agent:', error);

    if (error.message.includes('not found')) {
      return res.status(404).json({
        success: false,
        error: 'Serena agent not found'
      });
    }

    res.status(500).json({
      success: false,
      error: 'Failed to stop Serena agent'
    });
  }
});

/**
 * POST /api/serena-spawn/agent/:id/restart
 * Restart a Serena agent with optional configuration updates
 */
router.post('/agent/:id/restart', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const configUpdates = req.body;

    const result = await serenaSpawnCircuitBreaker.execute(async () => {
      return await serenaAgentSpawner.restartSerenaAgent(id, configUpdates);
    });

    res.json({
      success: true,
      data: result,
      message: 'Serena agent restarted successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error restarting Serena agent:', error);

    if (error.message.includes('not found')) {
      return res.status(404).json({
        success: false,
        error: 'Serena agent not found'
      });
    }

    res.status(500).json({
      success: false,
      error: 'Failed to restart Serena agent'
    });
  }
});

/**
 * GET /api/serena-spawn/agent/:id/memory
 * Get memory for a specific Serena agent
 */
router.get('/agent/:id/memory', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const memory = await serenaSpawnCircuitBreaker.execute(async () => {
      return await spawnMemoryIntegration.getProcessMemory(id);
    });

    if (!memory) {
      return res.status(404).json({
        success: false,
        error: 'Agent memory not found'
      });
    }

    res.json({
      success: true,
      data: memory,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting agent memory:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get agent memory'
    });
  }
});

/**
 * GET /api/serena-spawn/agent/:id/events
 * Get events for a specific Serena agent
 */
router.get('/agent/:id/events', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { limit = 50 } = req.query;

    const events = await serenaSpawnCircuitBreaker.execute(async () => {
      return await spawnMemoryIntegration.getProcessEvents(id, parseInt(limit as string));
    });

    res.json({
      success: true,
      data: events,
      count: events.length,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting agent events:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get agent events'
    });
  }
});

/**
 * GET /api/serena-spawn/agent/:id/metrics
 * Get performance metrics for a specific Serena agent
 */
router.get('/agent/:id/metrics', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { timeRange = '1h' } = req.query;

    const metrics = await serenaSpawnCircuitBreaker.execute(async () => {
      return await spawnMemoryIntegration.getProcessMetrics(id, timeRange as string);
    });

    res.json({
      success: true,
      data: metrics,
      count: metrics.length,
      timeRange,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting agent metrics:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get agent metrics'
    });
  }
});

/**
 * GET /api/serena-spawn/search
 * Search Serena agent memories
 */
router.get('/search', async (req: Request, res: Response) => {
  try {
    const { q: query, type, tags, timeRange } = req.query;

    if (!query) {
      return res.status(400).json({
        success: false,
        error: 'Search query is required'
      });
    }

    const filters: any = {};
    if (type) filters.type = type;
    if (tags) filters.tags = Array.isArray(tags) ? tags : [tags];
    if (timeRange) filters.timeRange = timeRange;

    const results = await serenaSpawnCircuitBreaker.execute(async () => {
      return await spawnMemoryIntegration.searchMemories(query as string, filters);
    });

    res.json({
      success: true,
      data: results,
      count: results.length,
      query,
      filters,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error searching memories:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to search memories'
    });
  }
});

/**
 * GET /api/serena-spawn/templates
 * Get Serena agent templates
 */
router.get('/templates', async (req: Request, res: Response) => {
  try {
    const templates = [
      {
        id: 'project-analyzer-template',
        name: 'Project Analyzer Template',
        description: 'Analyze project structure, dependencies, and code patterns',
        agentType: 'project_analyzer',
        recommendedModes: ['planning', 'introspection'],
        recommendedTools: ['file_tools', 'symbol_tools', 'memory_tools'],
        resourceRequirements: {
          cpu: 40,
          memory: 2048,
          disk: 1024
        }
      },
      {
        id: 'code-editor-template',
        name: 'Code Editor Template',
        description: 'Edit and refactor code with symbol-aware operations',
        agentType: 'code_editor',
        recommendedModes: ['editing', 'task-management'],
        recommendedTools: ['file_tools', 'symbol_tools', 'memory_tools'],
        resourceRequirements: {
          cpu: 30,
          memory: 1536,
          disk: 512
        }
      },
      {
        id: 'symbol-operator-template',
        name: 'Symbol Operator Template',
        description: 'Perform advanced symbol operations and code analysis',
        agentType: 'symbol_operator',
        recommendedModes: ['editing', 'orchestration'],
        recommendedTools: ['symbol_tools', 'memory_tools', 'workflow_tools'],
        resourceRequirements: {
          cpu: 35,
          memory: 1792,
          disk: 768
        }
      },
      {
        id: 'workflow-manager-template',
        name: 'Workflow Manager Template',
        description: 'Manage complex development workflows and task orchestration',
        agentType: 'workflow_manager',
        recommendedModes: ['task-management', 'orchestration'],
        recommendedTools: ['workflow_tools', 'memory_tools', 'config_tools'],
        resourceRequirements: {
          cpu: 25,
          memory: 1024,
          disk: 256
        }
      }
    ];

    res.json({
      success: true,
      data: templates,
      count: templates.length,
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
 * POST /api/serena-spawn/from-template
 * Spawn Serena agent from template
 */
router.post('/from-template', async (req: Request, res: Response) => {
  try {
    const { templateId, agentName, projectPath, overrides } = req.body;

    if (!templateId || !agentName) {
      return res.status(400).json({
        success: false,
        error: 'templateId and agentName are required'
      });
    }

    // Get template details
    const templatesResponse = await fetch(`${req.protocol}://${req.get('host')}/api/serena-spawn/templates`);
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

    // Build agent config from template
    const agentConfig: SerenaAgentConfig = {
      projectPath,
      agentName,
      agentType: template.agentType,
      modes: overrides?.modes || template.recommendedModes,
      tools: overrides?.tools || template.recommendedTools,
      memoryEnabled: overrides?.memoryEnabled ?? true,
      dashboardEnabled: overrides?.dashboardEnabled ?? true,
      ...overrides
    };

    const result = await serenaSpawnCircuitBreaker.execute(async () => {
      return await serenaAgentSpawner.spawnSerenaAgent(agentConfig);
    });

    res.json({
      success: true,
      data: result,
      message: `Serena agent "${agentName}" spawned from template "${template.name}"`,
      template: template.name,
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
 * POST /api/serena-spawn/agent/:id/export
 * Export Serena agent data for migration
 */
router.post('/agent/:id/export', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const exportData = await serenaSpawnCircuitBreaker.execute(async () => {
      return await spawnMemoryIntegration.exportProcessData(id);
    });

    if (!exportData) {
      return res.status(404).json({
        success: false,
        error: 'Agent data not found for export'
      });
    }

    res.json({
      success: true,
      data: exportData,
      filename: `serena-agent-${id}-export-${Date.now()}.json`,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error exporting agent data:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to export agent data'
    });
  }
});

/**
 * POST /api/serena-spawn/import
 * Import Serena agent data
 */
router.post('/import', async (req: Request, res: Response) => {
  try {
    const { exportData } = req.body;

    if (!exportData) {
      return res.status(400).json({
        success: false,
        error: 'exportData is required'
      });
    }

    await serenaSpawnCircuitBreaker.execute(async () => {
      return await spawnMemoryIntegration.importProcessData(exportData);
    });

    res.json({
      success: true,
      message: 'Agent data imported successfully',
      processId: exportData.processId,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error importing agent data:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to import agent data'
    });
  }
});

/**
 * POST /api/serena-spawn/cleanup
 * Cleanup old memory data
 */
router.post('/cleanup', async (req: Request, res: Response) => {
  try {
    const { retentionDays = 30 } = req.body;

    await serenaSpawnCircuitBreaker.execute(async () => {
      return await spawnMemoryIntegration.cleanup(retentionDays);
    });

    res.json({
      success: true,
      message: `Cleanup completed. Removed data older than ${retentionDays} days`,
      retentionDays,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error during cleanup:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to perform cleanup'
    });
  }
});

export default router;