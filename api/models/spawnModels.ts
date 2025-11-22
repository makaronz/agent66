/**
 * Spawn Data Models and Types
 * Defines data structures for spawn functionality with in-memory storage
 */

// In-memory storage for development (replace with real database in production)
class InMemoryStore<T> {
  private data: Map<string, T> = new Map();

  async create(item: T & { id: string }): Promise<T> {
    this.data.set(item.id, item);
    return item;
  }

  async findById(id: string): Promise<T | null> {
    return this.data.get(id) || null;
  }

  async find(filter: (item: T) => boolean): Promise<T[]> {
    return Array.from(this.data.values()).filter(filter);
  }

  async update(id: string, updates: Partial<T>): Promise<T | null> {
    const item = this.data.get(id);
    if (!item) return null;
    const updated = { ...item, ...updates };
    this.data.set(id, updated);
    return updated;
  }

  async delete(id: string): Promise<boolean> {
    return this.data.delete(id);
  }

  async findAll(): Promise<T[]> {
    return Array.from(this.data.values());
  }

  async updateOne(filter: Partial<T>, updates: Partial<T>): Promise<{ modifiedCount: number }> {
    let modifiedCount = 0;
    for (const [id, item] of this.data.entries()) {
      let matches = true;
      for (const [key, value] of Object.entries(filter)) {
        if ((item as any)[key] !== value) {
          matches = false;
          break;
        }
      }
      if (matches) {
        this.data.set(id, { ...item, ...updates });
        modifiedCount++;
      }
    }
    return { modifiedCount };
  }

  async deleteMany(filter: Partial<T>): Promise<{ deletedCount: number }> {
    let deletedCount = 0;
    for (const [id, item] of this.data.entries()) {
      let matches = true;
      for (const [key, value] of Object.entries(filter)) {
        if ((item as any)[key] !== value) {
          matches = false;
          break;
        }
      }
      if (matches) {
        this.data.delete(id);
        deletedCount++;
      }
    }
    return { deletedCount };
  }
}

// Process Configuration Interface
export interface ISpawnConfigDocument {
  id: string;
  name: string;
  type: 'trading_agent' | 'strategy' | 'data_pipeline' | 'ml_model' | 'monitor';
  command: string;
  args: string[];
  cwd?: string;
  env: Record<string, string>;
  resources?: {
    cpu: number;
    memory: number;
    disk: number;
  };
  autoRestart: boolean;
  healthCheck?: {
    endpoint?: string;
    interval: number;
    timeout: number;
  };
  dependencies: string[];
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
  createdBy?: string;
  version: number;
  active: boolean;
}

// Process Status Interface
export interface ISpawnStatusDocument {
  processId: string;
  configId: string;
  status: 'stopped' | 'starting' | 'running' | 'stopping' | 'error' | 'restarting';
  pid?: number;
  startTime?: Date;
  endTime?: Date;
  lastHealthCheck?: Date;
  exitCode?: number;
  restartCount: number;
  resourceUsage?: {
    cpu: number;
    memory: number;
    disk: number;
  };
  logs: Array<{
    timestamp: Date;
    level: 'info' | 'warn' | 'error' | 'debug';
    message: string;
  }>;
  metrics: {
    totalUptime: number;
    averageCpuUsage: number;
    peakMemoryUsage: number;
    totalRestarts: number;
  };
  createdAt: Date;
  updatedAt: Date;
}

// Spawn Event Interface
export interface ISpawnEventDocument {
  eventId: string;
  processId: string;
  configId?: string;
  eventType: 'spawned' | 'stopped' | 'restarted' | 'error' | 'unhealthy' | 'health_check_passed' | 'health_check_failed';
  data: any;
  timestamp: Date;
  severity: 'info' | 'warning' | 'error' | 'critical';
  source: string;
  metadata?: {
    [key: string]: any;
  };
}

// Performance Metrics Interface
export interface IPerformanceMetricsDocument {
  processId: string;
  timestamp: Date;
  metrics: {
    cpu: number;
    memory: number;
    disk: number;
    networkIO: {
      bytesIn: number;
      bytesOut: number;
    };
    processMetrics: {
      uptime: number;
      responseTime: number;
      throughput: number;
    };
  };
  systemMetrics: {
    loadAverage: number[];
    memoryUsage: number;
    diskUsage: number;
  };
}

// Template Interface
export interface ISpawnTemplateDocument {
  templateId: string;
  name: string;
  description: string;
  category: string;
  type: 'trading_agent' | 'strategy' | 'data_pipeline' | 'ml_model' | 'monitor';
  config: {
    command: string;
    args: string[];
    env: Record<string, string>;
    resources: {
      cpu: number;
      memory: number;
      disk: number;
    };
    autoRestart: boolean;
    healthCheck?: {
      endpoint?: string;
      interval: number;
      timeout: number;
    };
    tags: string[];
  };
  variables: Array<{
    name: string;
    type: 'string' | 'number' | 'boolean' | 'array';
    description: string;
    required: boolean;
    defaultValue?: any;
  }>;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
  version: number;
  public: boolean;
  usageCount: number;
}

// Data Access Layer classes
export class SpawnConfigRepository {
  private store = new InMemoryStore<ISpawnConfigDocument>();

  async create(config: Partial<ISpawnConfigDocument>): Promise<ISpawnConfigDocument> {
    const now = new Date();
    const newConfig: ISpawnConfigDocument = {
      id: config.id!,
      name: config.name!,
      type: config.type!,
      command: config.command!,
      args: config.args || [],
      cwd: config.cwd,
      env: config.env || {},
      resources: config.resources,
      autoRestart: config.autoRestart ?? false,
      healthCheck: config.healthCheck,
      dependencies: config.dependencies || [],
      tags: config.tags || [],
      createdAt: config.createdAt || now,
      updatedAt: now,
      createdBy: config.createdBy,
      version: config.version || 1,
      active: config.active ?? true
    };

    return await this.store.create(newConfig);
  }

  async findById(id: string): Promise<ISpawnConfigDocument | null> {
    return await this.store.findById(id);
  }

  async findByType(type: string): Promise<ISpawnConfigDocument[]> {
    return await this.store.find(item => item.type === type && item.active);
  }

  async findByTags(tags: string[]): Promise<ISpawnConfigDocument[]> {
    return await this.store.find(item =>
      item.active && tags.some(tag => item.tags.includes(tag))
    );
  }

  async update(id: string, updates: Partial<ISpawnConfigDocument>): Promise<ISpawnConfigDocument | null> {
    const updateData = {
      ...updates,
      updatedAt: new Date(),
      version: ((await this.findById(id))?.version || 0) + 1
    };
    return await this.store.update(id, updateData);
  }

  async softDelete(id: string): Promise<boolean> {
    return !!(await this.store.update(id, { active: false }));
  }

  async findAll(activeOnly: boolean = true): Promise<ISpawnConfigDocument[]> {
    if (activeOnly) {
      return await this.store.find(item => item.active);
    }
    return await this.store.findAll();
  }
}

export class SpawnStatusRepository {
  private store = new InMemoryStore<ISpawnStatusDocument>();

  async create(status: Partial<ISpawnStatusDocument>): Promise<ISpawnStatusDocument> {
    const now = new Date();
    const newStatus: ISpawnStatusDocument = {
      processId: status.processId!,
      configId: status.configId!,
      status: status.status!,
      pid: status.pid,
      startTime: status.startTime,
      endTime: status.endTime,
      lastHealthCheck: status.lastHealthCheck,
      exitCode: status.exitCode,
      restartCount: status.restartCount || 0,
      resourceUsage: status.resourceUsage,
      logs: status.logs || [],
      metrics: status.metrics || {
        totalUptime: 0,
        averageCpuUsage: 0,
        peakMemoryUsage: 0,
        totalRestarts: 0
      },
      createdAt: status.createdAt || now,
      updatedAt: now
    };

    return await this.store.create(newStatus);
  }

  async findByProcessId(processId: string): Promise<ISpawnStatusDocument | null> {
    return await this.store.findById(processId);
  }

  async findByStatus(status: string): Promise<ISpawnStatusDocument[]> {
    return await this.store.find(item => item.status === status);
  }

  async findByConfigId(configId: string): Promise<ISpawnStatusDocument[]> {
    return await this.store.find(item => item.configId === configId);
  }

  async update(processId: string, updates: Partial<ISpawnStatusDocument>): Promise<ISpawnStatusDocument | null> {
    const updateData = {
      ...updates,
      updatedAt: new Date()
    };
    return await this.store.update(processId, updateData);
  }

  async addLog(processId: string, level: string, message: string): Promise<void> {
    const status = await this.findByProcessId(processId);
    if (status) {
      const updatedLogs = [
        ...status.logs,
        {
          timestamp: new Date(),
          level: level as any,
          message
        }
      ].slice(-1000); // Keep only last 1000 logs

      await this.update(processId, { logs: updatedLogs });
    }
  }

  async delete(processId: string): Promise<boolean> {
    return await this.store.delete(processId);
  }
}

export class SpawnEventRepository {
  private store = new InMemoryStore<ISpawnEventDocument>();

  async create(event: Partial<ISpawnEventDocument>): Promise<ISpawnEventDocument> {
    const newEvent: ISpawnEventDocument = {
      eventId: event.eventId!,
      processId: event.processId!,
      configId: event.configId,
      eventType: event.eventType!,
      data: event.data,
      timestamp: event.timestamp || new Date(),
      severity: event.severity!,
      source: event.source!,
      metadata: event.metadata
    };

    return await this.store.create(newEvent);
  }

  async findByProcessId(processId: string, limit: number = 100): Promise<ISpawnEventDocument[]> {
    const events = await this.store.find(item => item.processId === processId);
    return events
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, limit);
  }

  async findByEventType(eventType: string, limit: number = 100): Promise<ISpawnEventDocument[]> {
    const events = await this.store.find(item => item.eventType === eventType);
    return events
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, limit);
  }

  async findBySeverity(severity: string, limit: number = 100): Promise<ISpawnEventDocument[]> {
    const events = await this.store.find(item => item.severity === severity);
    return events
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, limit);
  }

  async findByTimeRange(startDate: Date, endDate: Date): Promise<ISpawnEventDocument[]> {
    const events = await this.store.find(item =>
      item.timestamp >= startDate && item.timestamp <= endDate
    );
    return events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  async deleteOldEvents(olderThanDays: number = 30): Promise<number> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

    const result = await this.store.deleteMany({
      timestamp: { $lt: cutoffDate } as any
    });

    return result.deletedCount;
  }
}

export class PerformanceMetricsRepository {
  private store = new InMemoryStore<IPerformanceMetricsDocument>();

  async create(metrics: Partial<IPerformanceMetricsDocument>): Promise<IPerformanceMetricsDocument> {
    const newMetrics: IPerformanceMetricsDocument = {
      processId: metrics.processId!,
      timestamp: metrics.timestamp || new Date(),
      metrics: metrics.metrics!,
      systemMetrics: metrics.systemMetrics!
    };

    return await this.store.create(newMetrics);
  }

  async findByProcessId(processId: string, timeRange?: { start: Date; end: Date }): Promise<IPerformanceMetricsDocument[]> {
    const allMetrics = await this.store.findAll();
    let filtered = allMetrics.filter(item => item.processId === processId);

    if (timeRange) {
      filtered = filtered.filter(item =>
        item.timestamp >= timeRange.start && item.timestamp <= timeRange.end
      );
    }

    return filtered.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  async deleteOldMetrics(olderThanDays: number = 30): Promise<number> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

    const result = await this.store.deleteMany({
      timestamp: { $lt: cutoffDate } as any
    });

    return result.deletedCount;
  }
}

export class SpawnTemplateRepository {
  private store = new InMemoryStore<ISpawnTemplateDocument>();

  async create(template: Partial<ISpawnTemplateDocument>): Promise<ISpawnTemplateDocument> {
    const now = new Date();
    const newTemplate: ISpawnTemplateDocument = {
      templateId: template.templateId!,
      name: template.name!,
      description: template.description!,
      category: template.category!,
      type: template.type!,
      config: template.config!,
      variables: template.variables || [],
      createdBy: template.createdBy!,
      createdAt: template.createdAt || now,
      updatedAt: now,
      version: template.version || 1,
      public: template.public ?? false,
      usageCount: template.usageCount || 0
    };

    return await this.store.create(newTemplate);
  }

  async findById(templateId: string): Promise<ISpawnTemplateDocument | null> {
    return await this.store.findById(templateId);
  }

  async findByType(type: string): Promise<ISpawnTemplateDocument[]> {
    return await this.store.find(item => item.type === type);
  }

  async findPublic(): Promise<ISpawnTemplateDocument[]> {
    return await this.store.find(item => item.public);
  }

  async update(templateId: string, updates: Partial<ISpawnTemplateDocument>): Promise<ISpawnTemplateDocument | null> {
    const updateData = {
      ...updates,
      updatedAt: new Date()
    };
    return await this.store.update(templateId, updateData);
  }

  async incrementUsage(templateId: string): Promise<boolean> {
    const template = await this.findById(templateId);
    if (template) {
      await this.update(templateId, { usageCount: template.usageCount + 1 });
      return true;
    }
    return false;
  }

  async findAll(): Promise<ISpawnTemplateDocument[]> {
    return await this.store.findAll();
  }
}