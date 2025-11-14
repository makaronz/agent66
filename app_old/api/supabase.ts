import { createClient } from '@supabase/supabase-js';
import { Database } from './types/database.types';
import { getVaultClient } from './lib/vault-client';

// Initialize Supabase client with Vault secrets
let supabaseAdmin: any = null;
let initializationPromise: Promise<void> | null = null;

async function initializeSupabaseClient(): Promise<void> {
  if (supabaseAdmin) {
    return; // Already initialized
  }

  // Check if Vault is disabled in development
  if (process.env.VAULT_ENABLED === 'false') {
  if (process.env.VAULT_ENABLED === 'false') {
    // Use environment variables directly (no hard-coded fallbacks)
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !supabaseServiceKey) {
      throw new Error('[supabase] Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY when VAULT_ENABLED=false');
    }

    supabaseAdmin = createClient<Database>(supabaseUrl, supabaseServiceKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    });
    return;
  }

  // Use Vault for configuration
  try {
    const vaultClient = getVaultClient();
    const supabaseConfig = await vaultClient.getSupabaseConfig();
    
    supabaseAdmin = createClient<Database>(
      supabaseConfig.SUPABASE_URL,
      supabaseConfig.SUPABASE_SERVICE_ROLE_KEY,
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    );
    
  } catch (error) {
    console.warn('Failed to initialize Supabase with Vault, using environment fallback:', error);
    // Fallback to environment variables (no hard-coded defaults)
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !supabaseServiceKey) {
      throw new Error('[supabase] Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment');
    }

    supabaseAdmin = createClient<Database>(supabaseUrl, supabaseServiceKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    });
  }

// Initialize lazily - will be called when getSupabaseAdmin() is first used
// This ensures dotenv has loaded environment variables first
initializationPromise = null;

// Getter function to ensure client is initialized
export async function getSupabaseAdmin() {
  if (!supabaseAdmin) {
    if (!initializationPromise) {
      initializationPromise = initializeSupabaseClient();
    }
    await initializationPromise;
  }
  
  if (!supabaseAdmin) {
    throw new Error('Supabase client not initialized');
  }
  
  return supabaseAdmin;
}

// Helper function to get user from JWT token
export const getUserFromToken = async (token: string) => {
  try {
    const client = await getSupabaseAdmin();
    const { data: { user }, error } = await client.auth.getUser(token);
    if (error) throw error;
    return user;
  } catch (error) {
    console.error('Error getting user from token:', error);
    return null;
  }
};

// Helper function to verify user session
export const verifyUserSession = async (authHeader: string) => {
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  
  const token = authHeader.substring(7);
  return await getUserFromToken(token);
};

// Note: Use getSupabaseAdmin() function instead of default export
// export default getSupabaseAdmin();
