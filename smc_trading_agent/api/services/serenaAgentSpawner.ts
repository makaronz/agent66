/**
 * Serena Agent Spawner Service
 * Specialized spawner for Serena MCP agents with project integration
 */

import { spawnManager, SpawnConfig, SpawnStatus } from './spawnManager';
import { spawnMemoryIntegration } from './spawnMemoryIntegration';
import { SpawnConfigRepository, SpawnStatusRepository } from '../models/spawnModels';
import * as path from 'path';
import * as fs from 'fs/promises';
import * as os from 'os';

export interface SerenaAgentConfig {
  projectId?: string;
  projectPath?: string;
  agentName: string;
  agentType: 'project_analyzer' | 'code_editor' | 'symbol_operator' | 'workflow_manager';
  modes?: string[];
  context?: string;
  tools?: string[];
  languageServers?: string[];
  memoryEnabled?: boolean;
  dashboardEnabled?: boolean;
  customConfig?: Record<string, any>;
}

export interface SerenaProjectInfo {
  id: string;
  name: string;
  path: string;
  type: string;
  languages: string[];
  lastActive: Date;
  agentStatus?: 'active' | 'inactive' | 'error';
}

export class SerenaAgentSpawner {
  private configRepo: SpawnConfigRepository;
  private statusRepo: SpawnStatusRepository;

  constructor() {
    this.configRepo = new SpawnConfigRepository();
    this.statusRepo = new SpawnStatusRepository();
  }

  /**
   * Spawn a Serena agent with project-specific configuration
   */
  async spawnSerenaAgent(config: SerenaAgentConfig): Promise<SpawnStatus> {
    const agentId = `serena-${config.agentType}-${config.agentName.toLowerCase().replace(/\s+/g, '-')}`;

    // Detect project information
    const projectInfo = await this.detectProjectInfo(config);

    // Build agent command and arguments
    const { command, args, env } = await this.buildAgentCommand(agentId, config, projectInfo);

    // Create spawn configuration
    const spawnConfig: SpawnConfig = {
      id: agentId,
      name: `Serena ${config.agentType}: ${config.agentName}`,
      type: 'monitor', // Serena agents are monitoring/code analysis processes
      command,
      args,
      cwd: projectInfo?.path || config.projectPath || process.cwd(),
      env: {
        ...process.env,
        SERENA_AGENT_ID: agentId,
        SERENA_AGENT_NAME: config.agentName,
        SERENA_AGENT_TYPE: config.agentType,
        SERENA_PROJECT_PATH: projectInfo?.path || '',
        SERENA_PROJECT_ID: projectInfo?.id || '',
        SERENA_MODES: (config.modes || []).join(','),
        SERENA_CONTEXT: config.context || 'default',
        SERENA_TOOLS: (config.tools || []).join(','),
        SERENA_MEMORY_ENABLED: String(config.memoryEnabled ?? true),
        SERENA_DASHBOARD_ENABLED: String(config.dashboardEnabled ?? false),
        ...env
      },
      resources: {
        cpu: this.getResourceRequirements(config.agentType).cpu,
        memory: this.getResourceRequirements(config.agentType).memory,
        disk: this.getResourceRequirements(config.agentType).disk
      },
      autoRestart: true,
      healthCheck: {
        endpoint: `http://localhost:${8000 + Math.floor(Math.random() * 1000)}/health`,
        interval: 30000,
        timeout: 10000
      },
      dependencies: await this.getAgentDependencies(config),
      tags: ['serena', config.agentType, 'mcp', ...(config.modes || [])]
    };

    // Save configuration to memory and database
    await Promise.all([
      spawnMemoryIntegration.saveProcessConfig(spawnConfig),
      this.configRepo.create({
        id: spawnConfig.id,
        name: spawnConfig.name,
        type: spawnConfig.type,
        command: spawnConfig.command,
        args: spawnConfig.args,
        cwd: spawnConfig.cwd,
        env: spawnConfig.env,
        resources: spawnConfig.resources,
        autoRestart: spawnConfig.autoRestart,
        healthCheck: spawnConfig.healthCheck,
        dependencies: spawnConfig.dependencies || [],
        tags: spawnConfig.tags || [],
        createdBy: 'serena_spawner',
        version: 1
      })
    ]);

    // Spawn the process
    const status = await spawnManager.spawnProcess(spawnConfig);

    // Save status to database
    await this.statusRepo.create({
      processId: status.id,
      configId: spawnConfig.id,
      status: status.status,
      pid: status.pid,
      startTime: status.startTime,
      restartCount: status.restartCount,
      logs: status.logs.map(log => ({
        timestamp: log.timestamp,
        level: log.level,
        message: log.message
      })),
      metrics: {
        totalUptime: 0,
        averageCpuUsage: 0,
        peakMemoryUsage: 0,
        totalRestarts: 0
      }
    });

    return status;
  }

  /**
   * Get list of available Serena projects
   */
  async getAvailableProjects(): Promise<SerenaProjectInfo[]> {
    const projects: SerenaProjectInfo[] = [];

    try {
      // Look for .serena directories in common project locations
      const searchPaths = [
        process.cwd(),
        path.join(process.cwd(), '..'),
        path.join(process.cwd(), '..', '..'),
        path.join((os as any).homedir(), 'Projects'),
        path.join((os as any).homedir(), 'Development')
      ];

      for (const searchPath of searchPaths) {
        try {
          const entries = await fs.readdir(searchPath, { withFileTypes: true });

          for (const entry of entries) {
            if (entry.isDirectory()) {
              const projectPath = path.join(searchPath, entry.name);
              const serenaPath = path.join(projectPath, '.serena');

              try {
                await fs.access(serenaPath);
                const projectInfo = await this.extractProjectInfo(projectPath);
                if (projectInfo) {
                  projects.push(projectInfo);
                }
              } catch {
                // No .serena directory, skip
              }
            }
          }
        } catch (error) {
          // Can't read directory, skip
        }
      }

      // Sort by last active
      projects.sort((a, b) => b.lastActive.getTime() - a.lastActive.getTime());

    } catch (error) {
      console.error('Error scanning for Serena projects:', error);
    }

    return projects;
  }

  /**
   * Get spawned Serena agents
   */
  async getSerenaAgents(): Promise<Array<SpawnStatus & { config?: any }>> {
    const allStatuses = spawnManager.getAllStatus();
    const serenaAgents = allStatuses.filter(status =>
      status.name.toLowerCase().includes('serena')
    );

    // Enrich with database configuration
    for (const agent of serenaAgents) {
      const dbStatus = await this.statusRepo.findByProcessId(agent.id);
      if (dbStatus) {
        const config = await this.configRepo.findById(dbStatus.configId);
        (agent as any).config = config;
      }
    }

    return serenaAgents;
  }

  /**
   * Spawn Serena agent for specific project
   */
  async spawnProjectAgent(projectPath: string, agentType: SerenaAgentConfig['agentType'] = 'project_analyzer'): Promise<SpawnStatus> {
    const projectInfo = await this.extractProjectInfo(projectPath);
    if (!projectInfo) {
      throw new Error(`No Serena project found at path: ${projectPath}`);
    }

    return await this.spawnSerenaAgent({
      projectId: projectInfo.id,
      projectPath,
      agentName: `${projectInfo.name} Agent`,
      agentType,
      modes: this.getRecommendedModes(projectInfo.type, agentType),
      tools: this.getRecommendedTools(projectInfo.languages, agentType),
      languageServers: projectInfo.languages,
      memoryEnabled: true,
      dashboardEnabled: true
    });
  }

  /**
   * Stop Serena agent and clean up resources
   */
  async stopSerenaAgent(agentId: string): Promise<void> {
    await spawnManager.stopProcess(agentId);

    // Update database status
    await this.statusRepo.update(agentId, {
      status: 'stopped',
      endTime: new Date()
    });
  }

  /**
   * Restart Serena agent with updated configuration
   */
  async restartSerenaAgent(agentId: string, configUpdates?: Partial<SerenaAgentConfig>): Promise<SpawnStatus> {
    // Get current configuration
    const dbStatus = await this.statusRepo.findByProcessId(agentId);
    if (!dbStatus) {
      throw new Error(`Agent ${agentId} not found in database`);
    }

    const currentConfig = await this.configRepo.findById(dbStatus.configId);
    if (!currentConfig) {
      throw new Error(`Configuration for agent ${agentId} not found`);
    }

    // Apply updates if provided
    let updatedSpawnConfig: SpawnConfig;
    if (configUpdates) {
      updatedSpawnConfig = await this.updateSpawnConfig(currentConfig, configUpdates);

      // Update database
      await this.configRepo.update(currentConfig.id, updatedSpawnConfig);
      await spawnManager.updateConfig(agentId, updatedSpawnConfig);
    }

    // Restart the process
    return await spawnManager.restartProcess(agentId);
  }

  private async detectProjectInfo(config: SerenaAgentConfig): Promise<SerenaProjectInfo | null> {
    if (config.projectId || config.projectPath) {
      return await this.extractProjectInfo(config.projectPath || process.cwd());
    }

    // Auto-detect current directory as project
    return await this.extractProjectInfo(process.cwd());
  }

  private async extractProjectInfo(projectPath: string): Promise<SerenaProjectInfo | null> {
    try {
      const serenaPath = path.join(projectPath, '.serena');
      await fs.access(serenaPath);

      // Read project configuration
      const configPath = path.join(serenaPath, 'project.yml');
      let config: any = {};

      try {
        const configContent = await fs.readFile(configPath, 'utf-8');
        // Simple YAML parsing (in production, use a proper YAML parser)
        config = this.parseSimpleYaml(configContent);
      } catch {
        // Config file not found or invalid, use defaults
      }

      // Detect project type and languages
      const projectType = await this.detectProjectType(projectPath);
      const languages = await this.detectLanguages(projectPath);

      return {
        id: config.name || path.basename(projectPath),
        name: config.name || path.basename(projectPath),
        path: projectPath,
        type: projectType,
        languages,
        lastActive: new Date(),
        agentStatus: 'inactive'
      };

    } catch {
      return null;
    }
  }

  private async buildAgentCommand(agentId: string, config: SerenaAgentConfig, projectInfo?: SerenaProjectInfo | null): Promise<{ command: string; args: string[]; env: Record<string, string> }> {
    const serenaScript = path.join(__dirname, '../../../serena/scripts/mcp_server.py');
    const uvCommand = 'uv';

    const args = [
      'run',
      'python',
      serenaScript,
      '--agent-id', agentId,
      '--agent-name', config.agentName,
      '--agent-type', config.agentType
    ];

    if (projectInfo) {
      args.push('--project-path', projectInfo.path);
      args.push('--project-id', projectInfo.id);
    }

    if (config.modes && config.modes.length > 0) {
      args.push('--modes', config.modes.join(','));
    }

    if (config.context) {
      args.push('--context', config.context);
    }

    if (config.tools && config.tools.length > 0) {
      args.push('--tools', config.tools.join(','));
    }

    if (config.languageServers && config.languageServers.length > 0) {
      args.push('--language-servers', config.languageServers.join(','));
    }

    if (config.dashboardEnabled) {
      args.push('--enable-dashboard');
    }

    // Custom configuration
    if (config.customConfig) {
      for (const [key, value] of Object.entries(config.customConfig)) {
        args.push(`--${key}`, String(value));
      }
    }

    return {
      command: uvCommand,
      args,
      env: {
        PYTHONPATH: path.join(__dirname, '../../../serena/src'),
        SERENA_LOG_LEVEL: 'INFO'
      }
    };
  }

  private getResourceRequirements(agentType: SerenaAgentConfig['agentType']): { cpu: number; memory: number; disk: number } {
    const requirements = {
      project_analyzer: { cpu: 40, memory: 2048, disk: 1024 },
      code_editor: { cpu: 30, memory: 1536, disk: 512 },
      symbol_operator: { cpu: 35, memory: 1792, disk: 768 },
      workflow_manager: { cpu: 25, memory: 1024, disk: 256 }
    };

    return requirements[agentType];
  }

  private async getAgentDependencies(config: SerenaAgentConfig): Promise<string[]> {
    const dependencies: string[] = [];

    // Language server dependencies
    if (config.languageServers) {
      for (const lang of config.languageServers) {
        dependencies.push(`language-server-${lang}`);
      }
    }

    // Project dependencies
    if (config.projectPath) {
      dependencies.push(`project-${path.basename(config.projectPath)}`);
    }

    return dependencies;
  }

  private getRecommendedModes(projectType: string, agentType: SerenaAgentConfig['agentType']): string[] {
    const modeMap: Record<string, string[]> = {
      'web': ['planning', 'editing'],
      'mobile': ['planning', 'editing'],
      'backend': ['planning', 'editing', 'interactive'],
      'ml': ['planning', 'editing', 'interactive'],
      'data': ['planning', 'editing']
    };

    return modeMap[projectType] || ['planning', 'editing'];
  }

  private getRecommendedTools(languages: string[], agentType: SerenaAgentConfig['agentType']): string[] {
    const tools = ['memory_tools', 'config_tools'];

    // Add language-specific tools
    if (languages.includes('python')) {
      tools.push('file_tools', 'symbol_tools');
    }
    if (languages.includes('javascript') || languages.includes('typescript')) {
      tools.push('file_tools', 'symbol_tools');
    }
    if (languages.includes('rust')) {
      tools.push('file_tools', 'symbol_tools');
    }

    // Add agent-type specific tools
    if (agentType === 'symbol_operator') {
      tools.push('symbol_tools');
    }
    if (agentType === 'workflow_manager') {
      tools.push('workflow_tools');
    }

    return tools;
  }

  private async detectProjectType(projectPath: string): Promise<string> {
    try {
      const packageJson = path.join(projectPath, 'package.json');
      await fs.access(packageJson);
      const content = await fs.readFile(packageJson, 'utf-8');
      const pkg = JSON.parse(content);

      if (pkg.dependencies?.react || pkg.dependencies?.vue) {
        return 'web';
      }
      if (pkg.dependencies?.react-native) {
        return 'mobile';
      }
      if (pkg.dependencies?.express || pkg.dependencies?.fastify) {
        return 'backend';
      }

      return 'web';
    } catch {
      // Check for Python projects
      try {
        const requirementsTxt = path.join(projectPath, 'requirements.txt');
        const setupPy = path.join(projectPath, 'setup.py');
        const pyprojectToml = path.join(projectPath, 'pyproject.toml');

        if (await this.fileExists(requirementsTxt) || await this.fileExists(setupPy) || await this.fileExists(pyprojectToml)) {
          // Check for ML indicators
          const pyFiles = await fs.readdir(projectPath);
          const hasML = pyFiles.some(file =>
            file.includes('ml') || file.includes('model') || file.includes('train')
          );

          return hasML ? 'ml' : 'backend';
        }
      } catch {
        // Not a Python project
      }

      // Check for Rust projects
      try {
        const cargoToml = path.join(projectPath, 'Cargo.toml');
        if (await this.fileExists(cargoToml)) {
          return 'backend';
        }
      } catch {
        // Not a Rust project
      }

      return 'unknown';
    }
  }

  private async detectLanguages(projectPath: string): Promise<string[]> {
    const languages: string[] = [];

    try {
      const files = await fs.readdir(projectPath, { recursive: true });

      const languageMap: Record<string, RegExp[]> = {
        javascript: [/.js$/],
        typescript: [/.ts$/, /.tsx$/],
        python: [/\.py$/],
        rust: [/\.rs$/],
        go: [/\.go$/],
        java: [/\.java$/],
        cpp: [/\.cpp$/, /\.cc$/, /\.cxx$/, /\.hpp$/],
        csharp: [/\.cs$/],
        php: [/\.php$/]
      };

      for (const [language, patterns] of Object.entries(languageMap)) {
        if (files.some(file => patterns.some(pattern => pattern.test(file)))) {
          languages.push(language);
        }
      }

    } catch {
      // Error reading directory, return empty array
    }

    return languages;
  }

  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  private parseSimpleYaml(yamlContent: string): Record<string, any> {
    // Very simple YAML parser - in production, use a proper YAML library
    const lines = yamlContent.split('\n');
    const result: Record<string, any> = {};

    for (const line of lines) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        const key = line.substring(0, colonIndex).trim();
        const value = line.substring(colonIndex + 1).trim();
        result[key] = value.replace(/^['"]|['"]$/g, ''); // Remove quotes
      }
    }

    return result;
  }

  private async updateSpawnConfig(currentConfig: any, updates: Partial<SerenaAgentConfig>): Promise<SpawnConfig> {
    // This would convert the database config back to SpawnConfig format
    // and apply the updates
    const baseConfig: SpawnConfig = {
      id: currentConfig.id,
      name: currentConfig.name,
      type: currentConfig.type,
      command: currentConfig.command,
      args: currentConfig.args,
      cwd: currentConfig.cwd,
      env: currentConfig.env,
      resources: currentConfig.resources,
      autoRestart: currentConfig.autoRestart,
      healthCheck: currentConfig.healthCheck,
      dependencies: currentConfig.dependencies,
      tags: currentConfig.tags
    };

    // Apply updates (this is a simplified version)
    if (updates.modes) {
      baseConfig.env!.SERENA_MODES = updates.modes.join(',');
    }
    if (updates.context) {
      baseConfig.env!.SERENA_CONTEXT = updates.context;
    }
    if (updates.memoryEnabled !== undefined) {
      baseConfig.env!.SERENA_MEMORY_ENABLED = String(updates.memoryEnabled);
    }

    return baseConfig;
  }
}

// Singleton instance
export const serenaAgentSpawner = new SerenaAgentSpawner();