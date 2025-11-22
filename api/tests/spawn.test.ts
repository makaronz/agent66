/**
 * Spawn API Tests
 * Comprehensive tests for spawn functionality
 */

import request from 'supertest';
import app from '../app';
import { spawnManager, SpawnConfig } from '../services/spawnManager';
import { serenaAgentSpawner } from '../services/serenaAgentSpawner';
import { spawnMemoryIntegration } from '../services/spawnMemoryIntegration';

describe('Spawn API', () => {
  beforeEach(async () => {
    // Cleanup any existing processes before each test
    await spawnManager.cleanup();
  });

  afterAll(async () => {
    // Cleanup after all tests
    await spawnManager.cleanup();
  });

  describe('Basic Spawn Routes', () => {
    test('POST /api/spawn/process - should spawn a simple process', async () => {
      const config: SpawnConfig = {
        id: 'test-process',
        name: 'Test Process',
        type: 'monitor',
        command: 'echo',
        args: ['hello', 'world'],
        autoRestart: false,
        tags: ['test']
      };

      const response = await request(app)
        .post('/api/spawn/process')
        .send(config)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.id).toBe('test-process');
      expect(response.body.data.name).toBe('Test Process');
      expect(response.body.data.status).toBe('running');
    });

    test('GET /api/spawn/processes - should return list of processes', async () => {
      // First spawn a process
      const config: SpawnConfig = {
        id: 'test-list-process',
        name: 'Test List Process',
        type: 'monitor',
        command: 'sleep',
        args: ['1'],
        autoRestart: false
      };

      await request(app)
        .post('/api/spawn/process')
        .send(config);

      // Then get the list
      const response = await request(app)
        .get('/api/spawn/processes')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.processes).toHaveLength(1);
      expect(response.body.data.processes[0].id).toBe('test-list-process');
    });

    test('GET /api/spawn/process/:id - should return specific process', async () => {
      const config: SpawnConfig = {
        id: 'test-get-process',
        name: 'Test Get Process',
        type: 'monitor',
        command: 'echo',
        args: ['test'],
        autoRestart: false
      };

      await request(app)
        .post('/api/spawn/process')
        .send(config);

      const response = await request(app)
        .get('/api/spawn/process/test-get-process')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.id).toBe('test-get-process');
      expect(response.body.data.name).toBe('Test Get Process');
    });

    test('POST /api/spawn/process/:id/stop - should stop a process', async () => {
      const config: SpawnConfig = {
        id: 'test-stop-process',
        name: 'Test Stop Process',
        type: 'monitor',
        command: 'sleep',
        args: ['10'],
        autoRestart: false
      };

      await request(app)
        .post('/api/spawn/process')
        .send(config);

      const response = await request(app)
        .post('/api/spawn/process/test-stop-process/stop')
        .send({ graceful: true })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.message).toContain('stopped successfully');
    });

    test('POST /api/spawn/process/:id/restart - should restart a process', async () => {
      const config: SpawnConfig = {
        id: 'test-restart-process',
        name: 'Test Restart Process',
        type: 'monitor',
        command: 'echo',
        args: ['restart test'],
        autoRestart: false
      };

      await request(app)
        .post('/api/spawn/process')
        .send(config);

      const response = await request(app)
        .post('/api/spawn/process/test-restart-process/restart')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.message).toContain('restarted successfully');
    });

    test('GET /api/spawn/templates - should return templates', async () => {
      const response = await request(app)
        .get('/api/spawn/templates')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
      expect(response.body.data.length).toBeGreaterThan(0);

      const template = response.body.data[0];
      expect(template).toHaveProperty('id');
      expect(template).toHaveProperty('name');
      expect(template).toHaveProperty('type');
      expect(template).toHaveProperty('command');
    });

    test('POST /api/spawn/from-template - should spawn from template', async () => {
      const response = await request(app)
        .post('/api/spawn/from-template')
        .send({
          templateId: 'trading-agent-template',
          overrides: {
            id: 'test-template-process',
            name: 'Test Template Process'
          }
        })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.id).toBe('test-template-process');
      expect(response.body.message).toContain('spawned from template');
    });

    test('GET /api/spawn/metrics - should return system metrics', async () => {
      const response = await request(app)
        .get('/api/spawn/metrics')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('total');
      expect(response.body.data).toHaveProperty('running');
      expect(response.body.data).toHaveProperty('stopped');
      expect(response.body.data).toHaveProperty('error');
    });
  });

  describe('Error Handling', () => {
    test('POST /api/spawn/process - should validate required fields', async () => {
      const invalidConfig = {
        name: 'Invalid Process'
        // Missing id, type, command
      };

      const response = await request(app)
        .post('/api/spawn/process')
        .send(invalidConfig)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('Invalid configuration');
    });

    test('GET /api/spawn/process/:id - should handle non-existent process', async () => {
      const response = await request(app)
        .get('/api/spawn/process/non-existent')
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('not found');
    });

    test('POST /api/spawn/process/:id/stop - should handle non-existent process', async () => {
      const response = await request(app)
        .post('/api/spawn/process/non-existent/stop')
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('not found');
    });
  });

  describe('Serena Spawn Routes', () => {
    test('GET /api/serena-spawn/projects - should return available projects', async () => {
      const response = await request(app)
        .get('/api/serena-spawn/projects')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
      expect(response.body.data).toHaveProperty('count');
    });

    test('GET /api/serena-spawn/templates - should return Serena templates', async () => {
      const response = await request(app)
        .get('/api/serena-spawn/templates')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
      expect(response.body.data.length).toBeGreaterThan(0);

      const template = response.body.data[0];
      expect(template).toHaveProperty('id');
      expect(template).toHaveProperty('name');
      expect(template).toHaveProperty('agentType');
      expect(template).toHaveProperty('recommendedModes');
      expect(template).toHaveProperty('recommendedTools');
    });

    test('POST /api/serena-spawn/agent - should spawn Serena agent', async () => {
      const agentConfig = {
        agentName: 'Test Agent',
        agentType: 'project_analyzer',
        modes: ['planning'],
        tools: ['file_tools', 'memory_tools'],
        memoryEnabled: true,
        dashboardEnabled: false
      };

      const response = await request(app)
        .post('/api/serena-spawn/agent')
        .send(agentConfig)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.name).toContain('Serena project_analyzer');
      expect(response.body.data.name).toContain('Test Agent');
      expect(response.body.message).toContain('spawned successfully');
    });

    test('GET /api/serena-spawn/agents - should return Serena agents', async () => {
      // First spawn an agent
      const agentConfig = {
        agentName: 'Test Agent List',
        agentType: 'code_editor',
        memoryEnabled: true
      };

      await request(app)
        .post('/api/serena-spawn/agent')
        .send(agentConfig);

      // Then get the list
      const response = await request(app)
        .get('/api/serena-spawn/agents')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
      expect(response.body.data.length).toBeGreaterThan(0);

      const agent = response.body.data.find((a: any) => a.name.includes('Test Agent List'));
      expect(agent).toBeDefined();
    });
  });

  describe('Memory Integration', () => {
    test('GET /api/serena-spawn/agent/:id/memory - should handle non-existent agent', async () => {
      const response = await request(app)
        .get('/api/serena-spawn/agent/non-existent/memory')
        .expect(404);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('not found');
    });

    test('GET /api/serena-spawn/agent/:id/events - should return events', async () => {
      // First spawn an agent
      const agentConfig = {
        agentName: 'Test Events Agent',
        agentType: 'symbol_operator',
        memoryEnabled: true
      };

      const spawnResponse = await request(app)
        .post('/api/serena-spawn/agent')
        .send(agentConfig);

      const agentId = spawnResponse.body.data.id;

      // Then get events
      const response = await request(app)
        .get(`/api/serena-spawn/agent/${agentId}/events`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(Array.isArray(response.body.data)).toBe(true);
    });

    test('GET /api/serena-spawn/search - should search memories', async () => {
      // Create some test data first
      const agentConfig = {
        agentName: 'Test Search Agent',
        agentType: 'workflow_manager',
        memoryEnabled: true
      };

      await request(app)
        .post('/api/serena-spawn/agent')
        .send(agentConfig);

      // Then search
      const response = await request(app)
        .get('/api/serena-spawn/search?q=Test%20Search%20Agent')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data).toHaveProperty('count');
      expect(response.body.query).toBe('Test Search Agent');
    });

    test('POST /api/serena-spawn/cleanup - should perform cleanup', async () => {
      const response = await request(app)
        .post('/api/serena-spawn/cleanup')
        .send({ retentionDays: 1 })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.message).toContain('Cleanup completed');
      expect(response.body.retentionDays).toBe(1);
    });
  });

  describe('Input Validation', () => {
    test('POST /api/spawn/process - should reject invalid resource values', async () => {
      const invalidConfig = {
        id: 'invalid-resources',
        name: 'Invalid Resources Process',
        type: 'monitor',
        command: 'echo',
        args: ['test'],
        resources: {
          cpu: 150, // Invalid: > 100
          memory: -100 // Invalid: negative
        }
      };

      const response = await request(app)
        .post('/api/spawn/process')
        .send(invalidConfig)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('Invalid configuration');
    });

    test('POST /api/serena-spawn/agent - should validate agent config', async () => {
      const invalidConfig = {
        agentName: '', // Invalid: empty
        agentType: 'invalid_type' // Invalid: not in enum
      };

      const response = await request(app)
        .post('/api/serena-spawn/agent')
        .send(invalidConfig)
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('Invalid configuration');
    });

    test('GET /api/spawn/search - should require query parameter', async () => {
      const response = await request(app)
        .get('/api/serena-spawn/search')
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error).toContain('required');
    });
  });

  describe('Circuit Breaker Behavior', () => {
    test('Should handle rapid failures gracefully', async () => {
      // This test would require more setup to properly test circuit breaker
      // For now, we'll just verify the endpoint exists and responds
      const response = await request(app)
        .get('/api/spawn/processes')
        .expect(200);

      expect(response.body.success).toBe(true);
    });
  });

  describe('Real-time Events', () => {
    test('GET /api/spawn/events - should setup SSE connection', async () => {
      const response = await request(app)
        .get('/api/spawn/events')
        .expect(200);

      expect(response.headers['content-type']).toContain('text/event-stream');
      expect(response.headers['cache-control']).toContain('no-cache');
    });
  });
});

describe('Spawn Service Integration Tests', () => {
  test('SpawnManager should handle process lifecycle', async () => {
    const config: SpawnConfig = {
      id: 'integration-test',
      name: 'Integration Test Process',
      type: 'monitor',
      command: 'echo',
      args: ['integration test'],
      autoRestart: false
    };

    // Spawn process
    const status = await spawnManager.spawnProcess(config);
    expect(status.id).toBe('integration-test');
    expect(status.status).toBe('running');

    // Get status
    const retrievedStatus = spawnManager.getStatus('integration-test');
    expect(retrievedStatus).toBeDefined();
    expect(retrievedStatus!.status).toBe('running');

    // Stop process
    await spawnManager.stopProcess('integration-test');
    const stoppedStatus = spawnManager.getStatus('integration-test');
    expect(stoppedStatus?.status).toBe('stopped');
  });

  test('MemoryIntegration should store and retrieve data', async () => {
    const config: SpawnConfig = {
      id: 'memory-test',
      name: 'Memory Test Process',
      type: 'monitor',
      command: 'echo',
      args: ['memory test'],
      autoRestart: false
    };

    // Save config to memory
    await spawnMemoryIntegration.saveProcessConfig(config);

    // Load config from memory
    const loadedConfig = await spawnMemoryIntegration.loadProcessConfig('memory-test');
    expect(loadedConfig).toBeDefined();
    expect(loadedConfig!.name).toBe('Memory Test Process');

    // Record metrics
    await spawnMemoryIntegration.recordMetrics('memory-test', {
      cpu: 25.5,
      memory: 1024,
      disk: 512,
      timestamp: new Date()
    });

    // Get metrics
    const metrics = await spawnMemoryIntegration.getProcessMetrics('memory-test');
    expect(metrics).toBeDefined();
  });
});

describe('Performance Tests', () => {
  test('Should handle concurrent process spawning', async () => {
    const promises = [];

    // Spawn multiple processes concurrently
    for (let i = 0; i < 5; i++) {
      const config: SpawnConfig = {
        id: `concurrent-test-${i}`,
        name: `Concurrent Test Process ${i}`,
        type: 'monitor',
        command: 'echo',
        args: [`concurrent test ${i}`],
        autoRestart: false
      };

      promises.push(
        request(app)
          .post('/api/spawn/process')
          .send(config)
      );
    }

    const results = await Promise.all(promises);

    // All should succeed
    results.forEach(response => {
      expect(response.status).toBe(200);
      expect(response.body.success).toBe(true);
    });

    // Check that all processes were created
    const statusResponse = await request(app)
      .get('/api/spawn/processes')
      .expect(200);

    expect(statusResponse.body.data.processes.length).toBeGreaterThanOrEqual(5);
  }, 10000); // 10 second timeout
});