import { createClient } from '@supabase/supabase-js';
import { Database } from './types/database.types';
import { getVaultClient } from './lib/vault-client.js';

// Initialize Supabase client with Vault secrets
let supabaseAdmin: any = null;

async function initializeSupabaseClient() {
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
  }
}

// Initialize on module load
initializeSupabaseClient();

// Getter function to ensure client is initialized
export function getSupabaseAdmin() {
  if (!supabaseAdmin) {
    throw new Error('Supabase client not initialized');
  }
  return supabaseAdmin;
}

// Helper function to get user from JWT token
export const getUserFromToken = async (token: string) => {
  try {
    const client = getSupabaseAdmin();
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

export default getSupabaseAdmin();