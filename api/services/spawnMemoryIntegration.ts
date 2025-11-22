/**
 * Spawn Memory Integration Service
 * Integrates spawn management with Serena's memory system
 */

import { spawnManager, SpawnConfig, SpawnStatus } from './spawnManager';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

export interface MemoryEntry {
  id: string;
  type: 'spawn_event' | 'process_config' | 'performance_metric' | 'error_log';
  timestamp: Date;
  processId?: string;
  data: any;
  metadata?: {
    tags?: string[];
    version?: string;
    source?: string;
  };
}

export class SpawnMemoryIntegration {
  private memoryDir: string;
  private processMemoriesDir: string;
  private eventsFile: string;
  private metricsFile: string;

  constructor(private projectRoot: string = process.cwd()) {
    const serenaDir = path.join(projectRoot, '.serena');
    this.memoryDir = path.join(serenaDir, 'memories');
    this.processMemoriesDir = path.join(this.memoryDir, 'spawn_processes');
    this.eventsFile = path.join(this.memoryDir, 'spawn_events.jsonl');
    this.metricsFile = path.join(this.memoryDir, 'spawn_metrics.jsonl');

    this.initializeMemoryStructure();
    this.setupEventListeners();
  }

  private async initializeMemoryStructure(): Promise<void> {
    try {
      await fs.mkdir(this.memoryDir, { recursive: true });
      await fs.mkdir(this.processMemoriesDir, { recursive: true });
    } catch (error) {
      console.error('Failed to initialize memory structure:', error);
    }
  }

  private setupEventListeners(): void {
    // Listen to spawn manager events
    spawnManager.on('process:spawned', async (data) => {
      await this.recordEvent('process_spawned', data.config.id, {
        config: data.config,
        status: data.status,
        timestamp: data.status.startTime
      });

      await this.updateProcessMemory(data.config.id, 'spawned', {
        config: data.config,
        status: data.status
      });
    });

    spawnManager.on('process:exited', async (data) => {
      await this.recordEvent('process_exited', data.id, {
        exitCode: data.code,
        signal: data.signal,
        timestamp: new Date()
      });

      await this.updateProcessMemory(data.id, 'exited', {
        exitCode: data.code,
        signal: data.signal
      });
    });

    spawnManager.on('process:error', async (data) => {
      await this.recordEvent('process_error', data.id, {
        error: data.error.message,
        timestamp: new Date()
      });

      await this.updateProcessMemory(data.id, 'error', {
        error: data.error.message,
        stack: data.error.stack
      });
    });

    spawnManager.on('process:unhealthy', async (data) => {
      await this.recordEvent('process_unhealthy', data.id, {
        error: data.error.message,
        timestamp: new Date()
      });

      await this.updateProcessMemory(data.id, 'unhealthy', {
        error: data.error.message
      });
    });
  }

  /**
   * Save process configuration to memory
   */
  async saveProcessConfig(config: SpawnConfig): Promise<void> {
    const memoryFile = path.join(this.processMemoriesDir, `${config.id}.json`);

    const memoryData = {
      id: config.id,
      type: 'process_config' as const,
      timestamp: new Date(),
      processId: config.id,
      data: config,
      metadata: {
        tags: config.tags,
        version: '1.0',
        source: 'spawn_manager'
      }
    };

    await fs.writeFile(memoryFile, JSON.stringify(memoryData, null, 2));
  }

  /**
   * Load process configuration from memory
   */
  async loadProcessConfig(processId: string): Promise<SpawnConfig | null> {
    try {
      const memoryFile = path.join(this.processMemoriesDir, `${processId}.json`);
      const content = await fs.readFile(memoryFile, 'utf-8');
      const memoryData = JSON.parse(content);

      if (memoryData.type === 'process_config') {
        return memoryData.data as SpawnConfig;
      }

      return null;
    } catch (error) {
      // File might not exist or be corrupted
      return null;
    }
  }

  /**
   * Update process memory with new state
   */
  private async updateProcessMemory(
    processId: string,
    eventType: string,
    data: any
  ): Promise<void> {
    const memoryFile = path.join(this.processMemoriesDir, `${processId}.json`);

    try {
      let memoryData: any = {
        id: processId,
        type: 'process_memory',
        events: [],
        lastUpdated: new Date()
      };

      // Try to load existing memory
      try {
        const existingContent = await fs.readFile(memoryFile, 'utf-8');
        memoryData = JSON.parse(existingContent);
      } catch (error) {
        // File doesn't exist, start fresh
      }

      // Add new event
      memoryData.events.push({
        type: eventType,
        timestamp: new Date(),
        data
      });

      // Keep only last 100 events
      if (memoryData.events.length > 100) {
        memoryData.events = memoryData.events.slice(-100);
      }

      memoryData.lastUpdated = new Date();

      await fs.writeFile(memoryFile, JSON.stringify(memoryData, null, 2));

    } catch (error) {
      console.error('Failed to update process memory:', error);
    }
  }

  /**
   * Record an event in the global events log
   */
  private async recordEvent(
    eventType: string,
    processId: string,
    data: any
  ): Promise<void> {
    const event: MemoryEntry = {
      id: `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: 'spawn_event',
      timestamp: new Date(),
      processId,
      data: {
        eventType,
        ...data
      },
      metadata: {
        source: 'spawn_manager'
      }
    };

    const eventLine = JSON.stringify(event) + '\n';
    await fs.appendFile(this.eventsFile, eventLine);
  }

  /**
   * Record performance metrics
   */
  async recordMetrics(processId: string, metrics: any): Promise<void> {
    const metricEntry: MemoryEntry = {
      id: `metric_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: 'performance_metric',
      timestamp: new Date(),
      processId,
      data: metrics,
      metadata: {
        source: 'spawn_manager'
      }
    };

    const metricLine = JSON.stringify(metricEntry) + '\n';
    await fs.appendFile(this.metricsFile, metricLine);
  }

  /**
   * Get process memory
   */
  async getProcessMemory(processId: string): Promise<any> {
    try {
      const memoryFile = path.join(this.processMemoriesDir, `${processId}.json`);
      const content = await fs.readFile(memoryFile, 'utf-8');
      return JSON.parse(content);
    } catch (error) {
      return null;
    }
  }

  /**
   * Get all process memories
   */
  async getAllProcessMemories(): Promise<any[]> {
    try {
      const files = await fs.readdir(this.processMemoriesDir);
      const memories = [];

      for (const file of files) {
        if (file.endsWith('.json')) {
          try {
            const content = await fs.readFile(path.join(this.processMemoriesDir, file), 'utf-8');
            memories.push(JSON.parse(content));
          } catch (error) {
            console.error(`Failed to read memory file ${file}:`, error);
          }
        }
      }

      return memories;
    } catch (error) {
      return [];
    }
  }

  /**
   * Get events for a process
   */
  async getProcessEvents(processId: string, limit: number = 50): Promise<any[]> {
    try {
      const content = await fs.readFile(this.eventsFile, 'utf-8');
      const lines = content.trim().split('\n').filter(line => line);

      const events = lines
        .map(line => JSON.parse(line))
        .filter((event: MemoryEntry) => event.processId === processId)
        .slice(-limit);

      return events;
    } catch (error) {
      return [];
    }
  }

  /**
   * Get metrics for a process
   */
  async getProcessMetrics(processId: string, timeRange: string = '1h'): Promise<any[]> {
    try {
      const content = await fs.readFile(this.metricsFile, 'utf-8');
      const lines = content.trim().split('\n').filter(line => line);

      const now = Date.now();
      let timeRangeMs: number;

      switch (timeRange) {
        case '1h':
          timeRangeMs = 60 * 60 * 1000;
          break;
        case '24h':
          timeRangeMs = 24 * 60 * 60 * 1000;
          break;
        case '7d':
          timeRangeMs = 7 * 24 * 60 * 60 * 1000;
          break;
        default:
          timeRangeMs = 60 * 60 * 1000;
      }

      const metrics = lines
        .map(line => JSON.parse(line))
        .filter((metric: MemoryEntry) => {
          const metricTime = new Date(metric.timestamp).getTime();
          return metric.processId === processId && (now - metricTime) <= timeRangeMs;
        });

      return metrics;
    } catch (error) {
      return [];
    }
  }

  /**
   * Search process memories
   */
  async searchMemories(query: string, filters?: {
    type?: string;
    tags?: string[];
    timeRange?: string;
  }): Promise<any[]> {
    try {
      const memories = await this.getAllProcessMemories();

      let filtered = memories;

      // Apply type filter
      if (filters?.type) {
        filtered = filtered.filter(memory =>
          memory.type === filters.type ||
          memory.data?.type === filters.type
        );
      }

      // Apply tags filter
      if (filters?.tags && filters.tags.length > 0) {
        filtered = filtered.filter(memory =>
          filters.tags!.some(tag =>
            memory.data?.tags?.includes(tag) ||
            memory.metadata?.tags?.includes(tag)
          )
        );
      }

      // Apply time range filter
      if (filters?.timeRange) {
        const now = Date.now();
        let timeRangeMs: number;

        switch (filters.timeRange) {
          case '1h':
            timeRangeMs = 60 * 60 * 1000;
            break;
          case '24h':
            timeRangeMs = 24 * 60 * 60 * 1000;
            break;
          case '7d':
            timeRangeMs = 7 * 24 * 60 * 60 * 1000;
            break;
          default:
            timeRangeMs = 24 * 60 * 60 * 1000;
        }

        filtered = filtered.filter(memory => {
          const memoryTime = new Date(memory.timestamp || memory.lastUpdated).getTime();
          return (now - memoryTime) <= timeRangeMs;
        });
      }

      // Apply text search
      if (query) {
        const searchTerms = query.toLowerCase().split(' ');
        filtered = filtered.filter(memory => {
          const text = JSON.stringify(memory).toLowerCase();
          return searchTerms.every(term => text.includes(term));
        });
      }

      return filtered;
    } catch (error) {
      console.error('Error searching memories:', error);
      return [];
    }
  }

  /**
   * Export process data for migration
   */
  async exportProcessData(processId: string): Promise<any> {
    try {
      const [config, memory, events, metrics] = await Promise.all([
        this.loadProcessConfig(processId),
        this.getProcessMemory(processId),
        this.getProcessEvents(processId),
        this.getProcessMetrics(processId)
      ]);

      return {
        processId,
        exportTime: new Date().toISOString(),
        config,
        memory,
        events,
        metrics
      };
    } catch (error) {
      console.error('Error exporting process data:', error);
      return null;
    }
  }

  /**
   * Import process data from migration
   */
  async importProcessData(exportData: any): Promise<void> {
    try {
      const { processId, config, memory, events, metrics } = exportData;

      // Import config
      if (config) {
        await this.saveProcessConfig(config);
      }

      // Import memory
      if (memory) {
        const memoryFile = path.join(this.processMemoriesDir, `${processId}.json`);
        await fs.writeFile(memoryFile, JSON.stringify(memory, null, 2));
      }

      // Import events
      if (events && events.length > 0) {
        for (const event of events) {
          const eventLine = JSON.stringify(event) + '\n';
          await fs.appendFile(this.eventsFile, eventLine);
        }
      }

      // Import metrics
      if (metrics && metrics.length > 0) {
        for (const metric of metrics) {
          const metricLine = JSON.stringify(metric) + '\n';
          await fs.appendFile(this.metricsFile, metricLine);
        }
      }

    } catch (error) {
      console.error('Error importing process data:', error);
      throw error;
    }
  }

  /**
   * Cleanup old memory data
   */
  async cleanup(retentionDays: number = 30): Promise<void> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

      // Clean up old events
      try {
        const eventsContent = await fs.readFile(this.eventsFile, 'utf-8');
        const eventsLines = eventsContent.trim().split('\n').filter(line => line);

        const validEvents = eventsLines.filter(line => {
          try {
            const event = JSON.parse(line);
            return new Date(event.timestamp) >= cutoffDate;
          } catch {
            return false;
          }
        });

        await fs.writeFile(this.eventsFile, validEvents.join('\n') + '\n');
      } catch (error) {
        // Events file might not exist yet
      }

      // Clean up old metrics
      try {
        const metricsContent = await fs.readFile(this.metricsFile, 'utf-8');
        const metricsLines = metricsContent.trim().split('\n').filter(line => line);

        const validMetrics = metricsLines.filter(line => {
          try {
            const metric = JSON.parse(line);
            return new Date(metric.timestamp) >= cutoffDate;
          } catch {
            return false;
          }
        });

        await fs.writeFile(this.metricsFile, validMetrics.join('\n') + '\n');
      } catch (error) {
        // Metrics file might not exist yet
      }

      console.log(`Cleanup completed. Removed data older than ${retentionDays} days`);

    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }
}

// Singleton instance
export const spawnMemoryIntegration = new SpawnMemoryIntegration();