/**
 * Spawn Manager Service
 * Manages spawning and lifecycle of trading processes, agents, and strategies
 */

import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

export interface SpawnConfig {
  id: string;
  name: string;
  type: 'trading_agent' | 'strategy' | 'data_pipeline' | 'ml_model' | 'monitor';
  command: string;
  args: string[];
  cwd?: string;
  env?: Record<string, string>;
  resources?: {
    cpu: number;
    memory: number;
    disk: number;
  };
  autoRestart?: boolean;
  healthCheck?: {
    endpoint?: string;
    interval: number;
    timeout: number;
  };
  dependencies?: string[];
  tags?: string[];
}

export interface SpawnStatus {
  id: string;
  name: string;
  status: 'stopped' | 'starting' | 'running' | 'stopping' | 'error' | 'restarting';
  pid?: number;
  startTime?: Date;
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
}

export class SpawnManager extends EventEmitter {
  private processes: Map<string, ChildProcess> = new Map();
  private configs: Map<string, SpawnConfig> = new Map();
  private status: Map<string, SpawnStatus> = new Map();
  private healthCheckIntervals: Map<string, NodeJS.Timeout> = new Map();
  private logFiles: Map<string, string> = new Map();

  constructor(private logDir: string = path.join(os.tmpdir(), 'spawn-logs')) {
    super();
    this.initializeLogDirectory();
  }

  private async initializeLogDirectory(): Promise<void> {
    try {
      await fs.mkdir(this.logDir, { recursive: true });
    } catch (error) {
      console.error('Failed to create log directory:', error);
    }
  }

  /**
   * Spawn a new process with the given configuration
   */
  async spawnProcess(config: SpawnConfig): Promise<SpawnStatus> {
    // Validate configuration
    this.validateConfig(config);

    // Check if process already exists
    if (this.processes.has(config.id)) {
      throw new Error(`Process with id ${config.id} already exists`);
    }

    // Check dependencies
    if (config.dependencies) {
      await this.checkDependencies(config.dependencies);
    }

    // Initialize status
    const status: SpawnStatus = {
      id: config.id,
      name: config.name,
      status: 'starting',
      restartCount: 0,
      logs: []
    };

    this.status.set(config.id, status);
    this.configs.set(config.id, config);

    try {
      // Create log file
      const logFile = path.join(this.logDir, `${config.id}.log`);
      this.logFiles.set(config.id, logFile);

      // Spawn the process
      const childProcess = spawn(config.command, config.args, {
        cwd: config.cwd || process.cwd(),
        env: { ...process.env, ...config.env },
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: false
      });

      // Store process
      this.processes.set(config.id, childProcess);

      // Setup event handlers
      this.setupProcessHandlers(config.id, childProcess, logFile);

      // Setup health checks
      if (config.healthCheck) {
        this.setupHealthCheck(config.id, config.healthCheck);
      }

      // Update status
      status.pid = childProcess.pid;
      status.startTime = new Date();
      status.status = 'running';

      this.emit('process:spawned', { config, status });

      // Log spawn event
      await this.addLog(config.id, 'info', `Process spawned with PID ${childProcess.pid}`);

      return { ...status };

    } catch (error) {
      status.status = 'error';
      status.logs.push({
        timestamp: new Date(),
        level: 'error',
        message: `Failed to spawn: ${error.message}`
      });

      this.emit('process:error', { config, status, error });
      throw error;
    }
  }

  /**
   * Stop a running process
   */
  async stopProcess(id: string, graceful: boolean = true): Promise<void> {
    const process = this.processes.get(id);
    const status = this.status.get(id);

    if (!process || !status) {
      throw new Error(`Process with id ${id} not found`);
    }

    if (status.status === 'stopped' || status.status === 'stopping') {
      return;
    }

    status.status = 'stopping';

    try {
      // Clear health check
      const healthInterval = this.healthCheckIntervals.get(id);
      if (healthInterval) {
        clearInterval(healthInterval);
        this.healthCheckIntervals.delete(id);
      }

      if (graceful) {
        // Try graceful shutdown
        process.kill('SIGTERM');

        // Wait for graceful shutdown
        const timeout = setTimeout(() => {
          if (this.processes.has(id)) {
            process.kill('SIGKILL');
          }
        }, 5000);

        process.once('exit', () => {
          clearTimeout(timeout);
        });

      } else {
        // Force kill
        process.kill('SIGKILL');
      }

      await this.addLog(id, 'info', `Process stopped ${graceful ? 'gracefully' : 'forcefully'}`);

    } catch (error) {
      await this.addLog(id, 'error', `Error stopping process: ${error.message}`);
      throw error;
    }
  }

  /**
   * Restart a process
   */
  async restartProcess(id: string): Promise<SpawnStatus> {
    const config = this.configs.get(id);
    const status = this.status.get(id);

    if (!config) {
      throw new Error(`Process configuration for id ${id} not found`);
    }

    if (status) {
      status.status = 'restarting';
      status.restartCount++;
    }

    try {
      await this.stopProcess(id, true);
      await new Promise(resolve => setTimeout(resolve, 1000)); // Brief pause
      return await this.spawnProcess(config);
    } catch (error) {
      if (status) {
        status.status = 'error';
      }
      throw error;
    }
  }

  /**
   * Get status of all processes
   */
  getAllStatus(): SpawnStatus[] {
    return Array.from(this.status.values());
  }

  /**
   * Get status of specific process
   */
  getStatus(id: string): SpawnStatus | undefined {
    return this.status.get(id);
  }

  /**
   * Get process logs
   */
  async getLogs(id: string, lines: number = 100): Promise<string[]> {
    const logFile = this.logFiles.get(id);
    if (!logFile) {
      return [];
    }

    try {
      const content = await fs.readFile(logFile, 'utf-8');
      const logLines = content.split('\n').filter(line => line.trim());
      return logLines.slice(-lines);
    } catch (error) {
      return [];
    }
  }

  /**
   * Update process configuration
   */
  async updateConfig(id: string, updates: Partial<SpawnConfig>): Promise<void> {
    const config = this.configs.get(id);
    if (!config) {
      throw new Error(`Process configuration for id ${id} not found`);
    }

    const updatedConfig = { ...config, ...updates };
    this.configs.set(id, updatedConfig);

    // If health check changed, update it
    if (updates.healthCheck) {
      const healthInterval = this.healthCheckIntervals.get(id);
      if (healthInterval) {
        clearInterval(healthInterval);
      }
      this.setupHealthCheck(id, updates.healthCheck);
    }

    await this.addLog(id, 'info', 'Configuration updated');
  }

  /**
   * Cleanup resources and stop all processes
   */
  async cleanup(): Promise<void> {
    // Stop all health checks
    for (const [id, interval] of Array.from(this.healthCheckIntervals.entries())) {
      clearInterval(interval);
    }
    this.healthCheckIntervals.clear();

    // Stop all processes
    const stopPromises = Array.from(this.processes.keys()).map(id =>
      this.stopProcess(id, false).catch(error =>
        console.error(`Error stopping process ${id}:`, error)
      )
    );

    await Promise.allSettled(stopPromises);

    // Clear all data
    this.processes.clear();
    this.configs.clear();
    this.status.clear();
    this.logFiles.clear();
  }

  private validateConfig(config: SpawnConfig): void {
    if (!config.id || !config.name || !config.command) {
      throw new Error('Missing required configuration fields: id, name, command');
    }

    if (config.resources) {
      if (config.resources.cpu < 0 || config.resources.cpu > 100) {
        throw new Error('CPU usage must be between 0 and 100');
      }
      if (config.resources.memory < 0) {
        throw new Error('Memory usage must be positive');
      }
    }

    if (config.healthCheck && config.healthCheck.interval < 1000) {
      throw new Error('Health check interval must be at least 1000ms');
    }
  }

  private async checkDependencies(dependencies: string[]): Promise<void> {
    for (const depId of dependencies) {
      const depStatus = this.status.get(depId);
      if (!depStatus || depStatus.status !== 'running') {
        throw new Error(`Dependency ${depId} is not running`);
      }
    }
  }

  private setupProcessHandlers(id: string, process: ChildProcess, logFile: string): void {
    const status = this.status.get(id);
    if (!status) return;

    // Handle stdout
    if (process.stdout) {
      process.stdout.on('data', async (data) => {
        const message = data.toString().trim();
        await this.writeToLogFile(logFile, `OUT: ${message}`);
        status.logs.push({
          timestamp: new Date(),
          level: 'info',
          message
        });
      });
    }

    // Handle stderr
    if (process.stderr) {
      process.stderr.on('data', async (data) => {
        const message = data.toString().trim();
        await this.writeToLogFile(logFile, `ERR: ${message}`);
        status.logs.push({
          timestamp: new Date(),
          level: 'error',
          message
        });
      });
    }

    // Handle process exit
    process.on('exit', async (code, signal) => {
      status.status = 'stopped';
      status.exitCode = code;

      await this.addLog(id, 'info', `Process exited with code ${code} (signal: ${signal})`);
      await this.writeToLogFile(logFile, `Process exited with code ${code} (signal: ${signal})`);

      // Clear health check
      const healthInterval = this.healthCheckIntervals.get(id);
      if (healthInterval) {
        clearInterval(healthInterval);
        this.healthCheckIntervals.delete(id);
      }

      // Remove from processes map
      this.processes.delete(id);

      this.emit('process:exited', { id, code, signal });

      // Auto-restart if configured
      const config = this.configs.get(id);
      if (config?.autoRestart && code !== 0) {
        setTimeout(() => {
          this.restartProcess(id).catch(error => {
            console.error(`Failed to restart process ${id}:`, error);
          });
        }, 5000);
      }
    });

    // Handle process error
    process.on('error', async (error) => {
      status.status = 'error';
      status.logs.push({
        timestamp: new Date(),
        level: 'error',
        message: `Process error: ${error.message}`
      });

      await this.addLog(id, 'error', `Process error: ${error.message}`);
      await this.writeToLogFile(logFile, `Process error: ${error.message}`);

      this.emit('process:error', { id, error });
    });
  }

  private setupHealthCheck(id: string, healthCheck: NonNullable<SpawnConfig['healthCheck']>): void {
    const interval = setInterval(async () => {
      try {
        if (healthCheck.endpoint) {
          const response = await fetch(healthCheck.endpoint, {
            method: 'GET',
            signal: AbortSignal.timeout(healthCheck.timeout)
          });

          if (response.ok) {
            const status = this.status.get(id);
            if (status) {
              status.lastHealthCheck = new Date();
            }
            await this.addLog(id, 'debug', 'Health check passed');
          } else {
            throw new Error(`Health check failed: HTTP ${response.status}`);
          }
        } else {
          // Default health check - check if process is still running
          const process = this.processes.get(id);
          if (!process || process.killed) {
            throw new Error('Process is no longer running');
          }
        }
      } catch (error) {
        await this.addLog(id, 'warn', `Health check failed: ${error.message}`);

        const status = this.status.get(id);
        if (status && status.status === 'running') {
          this.emit('process:unhealthy', { id, error });

          // Try to restart if configured
          const config = this.configs.get(id);
          if (config?.autoRestart) {
            await this.restartProcess(id);
          }
        }
      }
    }, healthCheck.interval);

    this.healthCheckIntervals.set(id, interval);
  }

  private async writeToLogFile(logFile: string, message: string): Promise<void> {
    try {
      const timestamp = new Date().toISOString();
      const logLine = `[${timestamp}] ${message}\n`;
      await fs.appendFile(logFile, logLine);
    } catch (error) {
      console.error('Failed to write to log file:', error);
    }
  }

  private async addLog(id: string, level: 'info' | 'warn' | 'error' | 'debug', message: string): Promise<void> {
    const status = this.status.get(id);
    if (status) {
      status.logs.push({
        timestamp: new Date(),
        level,
        message
      });

      // Keep only last 1000 log entries in memory
      if (status.logs.length > 1000) {
        status.logs = status.logs.slice(-1000);
      }
    }
  }
}

// Singleton instance
export const spawnManager = new SpawnManager();