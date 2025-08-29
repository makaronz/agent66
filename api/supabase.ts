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
  console.log('[supabase] VAULT_ENABLED value:', process.env.VAULT_ENABLED);
  if (process.env.VAULT_ENABLED === 'false') {
    console.warn('[supabase] Vault disabled, using environment variables for Supabase config');
    
    // Use environment variables directly
    const supabaseUrl = process.env.SUPABASE_URL || 'https://fqhuoszrysapxrvyaqao.supabase.co';
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxaHVvc3pyeXNhcHhydnlhcWFvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDgyMzAxMiwiZXhwIjoyMDcwMzk5MDEyfQ.jKJuos3KqupDwVSswUbDE-xZMiCDAFgz6vnth-ZhA7Q';
    
    supabaseAdmin = createClient<Database>(supabaseUrl, supabaseServiceKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    });
    
    console.log('Supabase client initialized with environment variables (Vault disabled)');
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
    
    console.log('Supabase client initialized with Vault secrets');
  } catch (error) {
    console.warn('Failed to initialize Supabase with Vault, using environment fallback:', error);
    
    // Fallback to environment variables
    const supabaseUrl = process.env.SUPABASE_URL || 'https://fqhuoszrysapxrvyaqao.supabase.co';
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxaHVvc3pyeXNhcHhydnlhcWFvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDgyMzAxMiwiZXhwIjoyMDcwMzk5MDEyfQ.jKJuos3KqupDwVSswUbDE-xZMiCDAFgz6vnth-ZhA7Q';
    
    supabaseAdmin = createClient<Database>(supabaseUrl, supabaseServiceKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    });
    
    
    console.log('Supabase client initialized with environment variables');
  }
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