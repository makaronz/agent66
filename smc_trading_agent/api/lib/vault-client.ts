/**
 * Production-ready HashiCorp Vault client for Node.js/TypeScript
 * Handles secret retrieval, caching, and automatic token renewal
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import fs from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

interface VaultConfig {
  vaultUrl?: string;
  vaultToken?: string;
  kubernetesRole?: string;
  tokenFilePath?: string;
  cacheTtl?: number;
  maxRetries?: number;
}

interface VaultSecret {
  [key: string]: any;
}

interface CacheEntry {
  data: VaultSecret;
  timestamp: Date;
}

interface VaultHealth {
  vaultUrl: string;
  authenticated: boolean;
  sealed?: boolean;
  standby?: boolean;
  cacheSize: number;
  lastAuthMethod: string;
  error?: string;
}

export class VaultClientError extends Error {
  constructor(message: string, public readonly cause?: Error) {
    super(message);
    this.name = 'VaultClientError';
  }
}

export class VaultClient {
  private client: AxiosInstance;
  private vaultUrl: string;
  private vaultToken?: string;
  private kubernetesRole: string;
  private tokenFilePath: string;
  private cacheTtl: number;
  private maxRetries: number;
  private secretCache: Map<string, CacheEntry> = new Map();
  private tokenRenewalInterval?: NodeJS.Timeout;

  constructor(config: VaultConfig = {}) {
    this.vaultUrl = config.vaultUrl || process.env.VAULT_ADDR || 'http://vault.vault.svc.cluster.local:8200';
    this.vaultToken = config.vaultToken;
    this.kubernetesRole = config.kubernetesRole || process.env.VAULT_ROLE || 'smc-trading-role';
    this.tokenFilePath = config.tokenFilePath || '/vault/secrets/token';
    this.cacheTtl = config.cacheTtl || 300000; // 5 minutes in ms
    this.maxRetries = config.maxRetries || 3;

    this.client = axios.create({
      baseURL: this.vaultUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Initialize authentication
    this.authenticate().catch(error => {
      console.error('Failed to authenticate with Vault:', error);
    });

    // Start token renewal
    this.startTokenRenewal();

    // Cleanup on process exit
    process.on('SIGTERM', () => this.close());
    process.on('SIGINT', () => this.close());
  }

  private async authenticate(): Promise<void> {
    try {
      // Try token from file (Vault Agent)
      if (existsSync(this.tokenFilePath)) {
        const token = await fs.readFile(this.tokenFilePath, 'utf8');
        this.vaultToken = token.trim();
        this.client.defaults.headers.common['X-Vault-Token'] = this.vaultToken;
        console.log('Authenticated with Vault using token from file');
        return;
      }

      // Try direct token
      if (this.vaultToken) {
        this.client.defaults.headers.common['X-Vault-Token'] = this.vaultToken;
        console.log('Authenticated with Vault using provided token');
        return;
      }

      // Try Kubernetes authentication
      if (await this.authenticateKubernetes()) {
        console.log('Authenticated with Vault using Kubernetes service account');
        return;
      }

      // Try environment token as fallback
      const envToken = process.env.VAULT_TOKEN;
      if (envToken) {
        this.vaultToken = envToken;
        this.client.defaults.headers.common['X-Vault-Token'] = this.vaultToken;
        console.log('Authenticated with Vault using environment token');
        return;
      }

      throw new VaultClientError('No valid authentication method found');
    } catch (error) {
      console.error('Failed to authenticate with Vault:', error);
      throw new VaultClientError(`Authentication failed: ${error}`);
    }
  }

  private async authenticateKubernetes(): Promise<boolean> {
    try {
      const jwtPath = '/var/run/secrets/kubernetes.io/serviceaccount/token';
      if (!existsSync(jwtPath)) {
        return false;
      }

      const jwt = await fs.readFile(jwtPath, 'utf8');
      const response = await this.client.post('/v1/auth/kubernetes/login', {
        role: this.kubernetesRole,
        jwt: jwt.trim()
      });

      this.vaultToken = response.data.auth.client_token;
      this.client.defaults.headers.common['X-Vault-Token'] = this.vaultToken;
      return true;
    } catch (error) {
      console.warn('Kubernetes authentication failed:', error);
      return false;
    }
  }

  private startTokenRenewal(): void {
    // Renew token every 30 minutes
    this.tokenRenewalInterval = setInterval(async () => {
      try {
        if (await this.isAuthenticated()) {
          // Check token TTL
          const tokenInfo = await this.client.get('/v1/auth/token/lookup-self');
          const ttl = tokenInfo.data.data.ttl;

          if (ttl < 300) { // Less than 5 minutes
            await this.client.post('/v1/auth/token/renew-self');
            console.log('Vault token renewed successfully');
          }
        } else {
          console.warn('Vault token invalid, re-authenticating');
          await this.authenticate();
        }
      } catch (error) {
        console.error('Token renewal failed:', error);
      }
    }, 30 * 60 * 1000); // 30 minutes
  }

  private async isAuthenticated(): Promise<boolean> {
    try {
      await this.client.get('/v1/auth/token/lookup-self');
      return true;
    } catch {
      return false;
    }
  }

  private isCacheValid(key: string): boolean {
    const entry = this.secretCache.get(key);
    if (!entry) return false;

    const now = new Date();
    return now.getTime() - entry.timestamp.getTime() < this.cacheTtl;
  }

  private async retryOperation<T>(operation: () => Promise<T>): Promise<T> {
    let lastError: Error;

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        if (attempt < this.maxRetries) {
          const waitTime = Math.pow(2, attempt - 1) * 1000; // Exponential backoff
          console.warn(`Vault operation failed (attempt ${attempt}), retrying in ${waitTime}ms:`, error);
          await new Promise(resolve => setTimeout(resolve, waitTime));

          // Try to re-authenticate on auth errors
          if (axios.isAxiosError(error) && error.response?.status === 403) {
            await this.authenticate();
          }
        }
      }
    }

    throw new VaultClientError(`Operation failed after ${this.maxRetries} attempts: ${lastError.message}`, lastError);
  }

  async getSecret(path: string, useCache: boolean = true): Promise<VaultSecret> {
    // Check cache first
    if (useCache && this.isCacheValid(path)) {
      console.debug(`Returning cached secret for path: ${path}`);
      return this.secretCache.get(path)!.data;
    }

    return this.retryOperation(async () => {
      try {
        const response = await this.client.get(`/v1/${path}`);
        const secretData = response.data.data.data || response.data.data;

        // Cache the result
        this.secretCache.set(path, {
          data: secretData,
          timestamp: new Date()
        });

        console.debug(`Retrieved secret from Vault: ${path}`);
        return secretData;
      } catch (error) {
        if (axios.isAxiosError(error)) {
          if (error.response?.status === 404) {
            throw new VaultClientError(`Secret not found: ${path}`);
          }
          throw new VaultClientError(`Failed to retrieve secret: ${error.response?.data?.errors?.[0] || error.message}`);
        }
        throw new VaultClientError(`Failed to retrieve secret: ${error}`);
      }
    });
  }

  async getDatabaseConfig(): Promise<{ DATABASE_URL: string; DATABASE_PASSWORD: string }> {
    try {
      const secret = await this.getSecret('secret/data/smc-trading/database');
      return {
        DATABASE_URL: secret.url,
        DATABASE_PASSWORD: secret.password
      };
    } catch (error) {
      console.error('Failed to get database config:', error);
      throw error;
    }
  }

  async getExchangeConfig(exchange: string): Promise<Record<string, string>> {
    try {
      const secret = await this.getSecret(`secret/data/smc-trading/exchanges/${exchange}`);

      switch (exchange) {
        case 'binance':
          return {
            BINANCE_API_KEY: secret.api_key,
            BINANCE_API_SECRET: secret.api_secret
          };
        case 'bybit':
          return {
            BYBIT_API_KEY: secret.api_key,
            BYBIT_API_SECRET: secret.api_secret
          };
        case 'oanda':
          return {
            OANDA_API_KEY: secret.api_key,
            OANDA_ACCOUNT_ID: secret.account_id
          };
        default:
          throw new VaultClientError(`Unsupported exchange: ${exchange}`);
      }
    } catch (error) {
      console.error(`Failed to get ${exchange} config:`, error);
      throw error;
    }
  }

  async getJwtConfig(): Promise<{ JWT_SECRET: string; ENCRYPTION_KEY: string }> {
    try {
      const secret = await this.getSecret('secret/data/smc-trading/jwt');
      return {
        JWT_SECRET: secret.secret,
        ENCRYPTION_KEY: secret.encryption_key
      };
    } catch (error) {
      console.error('Failed to get JWT config:', error);
      throw error;
    }
  }

  async getRedisConfig(): Promise<{ REDIS_PASSWORD: string }> {
    try {
      const secret = await this.getSecret('secret/data/smc-trading/redis');
      return {
        REDIS_PASSWORD: secret.password
      };
    } catch (error) {
      console.error('Failed to get Redis config:', error);
      throw error;
    }
  }

  async getSupabaseConfig(): Promise<{ SUPABASE_URL: string; SUPABASE_SERVICE_ROLE_KEY: string; SUPABASE_ANON_KEY: string }> {
    try {
      const secret = await this.getSecret('secret/data/smc-trading/supabase');
      return {
        SUPABASE_URL: secret.url,
        SUPABASE_SERVICE_ROLE_KEY: secret.service_role_key,
        SUPABASE_ANON_KEY: secret.anon_key
      };
    } catch (error) {
      console.error('Failed to get Supabase config:', error);
      throw error;
    }
  }

  async encryptData(plaintext: string, keyName: string = 'smc-trading'): Promise<string> {
    return this.retryOperation(async () => {
      try {
        const response = await this.client.post(`/v1/transit/encrypt/${keyName}`, {
          plaintext: Buffer.from(plaintext).toString('base64')
        });
        return response.data.data.ciphertext;
      } catch (error) {
        throw new VaultClientError(`Encryption failed: ${error}`);
      }
    });
  }

  async decryptData(ciphertext: string, keyName: string = 'smc-trading'): Promise<string> {
    return this.retryOperation(async () => {
      try {
        const response = await this.client.post(`/v1/transit/decrypt/${keyName}`, {
          ciphertext
        });
        return Buffer.from(response.data.data.plaintext, 'base64').toString();
      } catch (error) {
        throw new VaultClientError(`Decryption failed: ${error}`);
      }
    });
  }

  invalidateCache(path?: string): void {
    if (path) {
      this.secretCache.delete(path);
      console.debug(`Invalidated cache for path: ${path}`);
    } else {
      this.secretCache.clear();
      console.debug('Invalidated entire secret cache');
    }
  }

  async healthCheck(): Promise<VaultHealth> {
    try {
      const healthResponse = await this.client.get('/v1/sys/health');
      const authenticated = await this.isAuthenticated();

      return {
        vaultUrl: this.vaultUrl,
        authenticated,
        sealed: healthResponse.data.sealed,
        standby: healthResponse.data.standby,
        cacheSize: this.secretCache.size,
        lastAuthMethod: existsSync('/var/run/secrets/kubernetes.io/serviceaccount/token') ? 'kubernetes' : 'token'
      };
    } catch (error) {
      console.error('Vault health check failed:', error);
      return {
        vaultUrl: this.vaultUrl,
        authenticated: false,
        cacheSize: this.secretCache.size,
        lastAuthMethod: 'unknown',
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  close(): void {
    if (this.tokenRenewalInterval) {
      clearInterval(this.tokenRenewalInterval);
    }
    this.invalidateCache();
    console.log('Vault client closed');
  }
}

// Global Vault client instance
let vaultClient: VaultClient | null = null;

export function getVaultClient(): VaultClient {
  if (!vaultClient) {
    vaultClient = new VaultClient();
  }
  return vaultClient;
}

export async function getSecretFromVault(path: string): Promise<VaultSecret> {
  const client = getVaultClient();
  return client.getSecret(path);
}

export function getConfigValue(key: string, defaultValue?: any, vaultPath?: string): any {
  // Try environment variable first
  const envValue = process.env[key];
  if (envValue !== undefined) {
    return envValue;
  }

  // For Vault secrets, we'll need to handle this asynchronously
  // This is a synchronous fallback that returns the default
  return defaultValue;
}

// Async configuration helpers
export async function getDatabaseUrl(): Promise<string> {
  try {
    const client = getVaultClient();
    const config = await client.getDatabaseConfig();
    return config.DATABASE_URL;
  } catch (error) {
    console.warn('Failed to get database URL from Vault, using environment fallback');
    return process.env.DATABASE_URL || 'postgresql://localhost:5432/smc_trading_agent';
  }
}

export async function getExchangeCredentials(exchange: string): Promise<Record<string, string>> {
  try {
    const client = getVaultClient();
    return await client.getExchangeConfig(exchange);
  } catch (error) {
    console.warn(`Failed to get ${exchange} credentials from Vault, using environment fallback`);

    // Fallback to environment variables
    switch (exchange) {
      case 'binance':
        return {
          BINANCE_API_KEY: process.env.BINANCE_API_KEY || '',
          BINANCE_API_SECRET: process.env.BINANCE_API_SECRET || ''
        };
      case 'bybit':
        return {
          BYBIT_API_KEY: process.env.BYBIT_API_KEY || '',
          BYBIT_API_SECRET: process.env.BYBIT_API_SECRET || ''
        };
      case 'oanda':
        return {
          OANDA_API_KEY: process.env.OANDA_API_KEY || '',
          OANDA_ACCOUNT_ID: process.env.OANDA_ACCOUNT_ID || ''
        };
      default:
        return {};
    }
  }
}

export async function getJwtSecret(): Promise<string> {
  try {
    const client = getVaultClient();
    const config = await client.getJwtConfig();
    return config.JWT_SECRET;
  } catch (error) {
    console.warn('Failed to get JWT secret from Vault, using environment fallback');
    return process.env.JWT_SECRET || 'fallback-secret-change-in-production';
  }
}

export async function getEncryptionKey(): Promise<string> {
  try {
    const client = getVaultClient();
    const config = await client.getJwtConfig();
    return config.ENCRYPTION_KEY;
  } catch (error) {
    console.warn('Failed to get encryption key from Vault, using environment fallback');
    return process.env.ENCRYPTION_KEY || 'fallback-key-change-in-production';
  }
}