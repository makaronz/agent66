import { supabaseAdmin } from '../lib/supabase';
import { EncryptionService } from '../lib/encryption';
import { Database } from '../types/database.types';

type User = Database['public']['Tables']['users']['Row'];
type UserInsert = Database['public']['Tables']['users']['Insert'];
type UserUpdate = Database['public']['Tables']['users']['Update'];
type UserApiKey = Database['public']['Tables']['user_api_keys']['Row'];
type UserApiKeyInsert = Database['public']['Tables']['user_api_keys']['Insert'];
type UserConfiguration = Database['public']['Tables']['user_configurations']['Row'];
type UserConfigurationInsert = Database['public']['Tables']['user_configurations']['Insert'];

export class UserService {
  /**
   * Create or update user profile
   */
  static async upsertUser(userData: UserInsert): Promise<User> {
    const { data, error } = await supabaseAdmin
      .from('users')
      .upsert(userData, { onConflict: 'id' })
      .select()
      .single();

    if (error) {
      console.error('Error upserting user:', error);
      throw new Error('Failed to create/update user');
    }

    return data;
  }

  /**
   * Get user by ID
   */
  static async getUserById(userId: string): Promise<User | null> {
    const { data, error } = await supabaseAdmin
      .from('users')
      .select('*')
      .eq('id', userId)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        return null; // User not found
      }
      console.error('Error getting user:', error);
      throw new Error('Failed to get user');
    }

    return data;
  }

  /**
   * Update user profile
   */
  static async updateUser(userId: string, updates: UserUpdate): Promise<User> {
    const { data, error } = await supabaseAdmin
      .from('users')
      .update(updates)
      .eq('id', userId)
      .select()
      .single();

    if (error) {
      console.error('Error updating user:', error);
      throw new Error('Failed to update user');
    }

    return data;
  }

  /**
   * Store encrypted API keys for user
   */
  static async storeApiKeys(
    userId: string,
    exchange: 'binance' | 'bybit' | 'oanda',
    apiKey: string,
    secret: string,
    isTestnet: boolean = true
  ): Promise<UserApiKey> {
    try {
      const encryptedApiKey = EncryptionService.encrypt(apiKey);
      const encryptedSecret = EncryptionService.encrypt(secret);

      const apiKeyData: UserApiKeyInsert = {
        user_id: userId,
        exchange,
        encrypted_api_key: encryptedApiKey,
        encrypted_secret: encryptedSecret,
        is_testnet: isTestnet,
        is_active: true
      };

      const { data, error } = await supabaseAdmin
        .from('user_api_keys')
        .upsert(apiKeyData, { onConflict: 'user_id,exchange' })
        .select()
        .single();

      if (error) {
        console.error('Error storing API keys:', error);
        throw new Error('Failed to store API keys');
      }

      return data;
    } catch (error) {
      console.error('Error in storeApiKeys:', error);
      throw new Error('Failed to encrypt and store API keys');
    }
  }

  /**
   * Get decrypted API keys for user
   */
  static async getApiKeys(
    userId: string,
    exchange?: 'binance' | 'bybit' | 'oanda'
  ): Promise<Array<UserApiKey & { decrypted_api_key: string; decrypted_secret: string }>> {
    try {
      let query = supabaseAdmin
        .from('user_api_keys')
        .select('*')
        .eq('user_id', userId)
        .eq('is_active', true);

      if (exchange) {
        query = query.eq('exchange', exchange);
      }

      const { data, error } = await query;

      if (error) {
        console.error('Error getting API keys:', error);
        throw new Error('Failed to get API keys');
      }

      if (!data) {
        return [];
      }

      // Decrypt the keys
      const decryptedKeys = data.map(key => ({
        ...key,
        decrypted_api_key: EncryptionService.decrypt(key.encrypted_api_key),
        decrypted_secret: EncryptionService.decrypt(key.encrypted_secret)
      }));

      return decryptedKeys;
    } catch (error) {
      console.error('Error in getApiKeys:', error);
      throw new Error('Failed to decrypt API keys');
    }
  }

  /**
   * Delete API keys for user
   */
  static async deleteApiKeys(
    userId: string,
    exchange: 'binance' | 'bybit' | 'oanda'
  ): Promise<void> {
    const { error } = await supabaseAdmin
      .from('user_api_keys')
      .delete()
      .eq('user_id', userId)
      .eq('exchange', exchange);

    if (error) {
      console.error('Error deleting API keys:', error);
      throw new Error('Failed to delete API keys');
    }
  }

  /**
   * Store user configuration
   */
  static async storeConfiguration(
    userId: string,
    configName: string,
    config: any
  ): Promise<UserConfiguration> {
    const configData: UserConfigurationInsert = {
      user_id: userId,
      config_name: configName,
      config_json: config,
      is_active: true
    };

    const { data, error } = await supabaseAdmin
      .from('user_configurations')
      .upsert(configData, { onConflict: 'user_id,config_name' })
      .select()
      .single();

    if (error) {
      console.error('Error storing configuration:', error);
      throw new Error('Failed to store configuration');
    }

    return data;
  }

  /**
   * Get user configurations
   */
  static async getConfigurations(userId: string): Promise<UserConfiguration[]> {
    const { data, error } = await supabaseAdmin
      .from('user_configurations')
      .select('*')
      .eq('user_id', userId)
      .eq('is_active', true)
      .order('updated_at', { ascending: false });

    if (error) {
      console.error('Error getting configurations:', error);
      throw new Error('Failed to get configurations');
    }

    return data || [];
  }

  /**
   * Get active configuration for user
   */
  static async getActiveConfiguration(
    userId: string,
    configName: string = 'default'
  ): Promise<UserConfiguration | null> {
    const { data, error } = await supabaseAdmin
      .from('user_configurations')
      .select('*')
      .eq('user_id', userId)
      .eq('config_name', configName)
      .eq('is_active', true)
      .single();

    if (error) {
      if (error.code === 'PGRST116') {
        return null; // Configuration not found
      }
      console.error('Error getting active configuration:', error);
      throw new Error('Failed to get active configuration');
    }

    return data;
  }
}

export default UserService;