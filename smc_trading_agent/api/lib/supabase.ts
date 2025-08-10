import { createClient } from '@supabase/supabase-js';
import { Database } from '../types/database.types';

const supabaseUrl = process.env.SUPABASE_URL || 'https://fqhuoszrysapxrvyaqao.supabase.co';
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxaHVvc3pyeXNhcHhydnlhcWFvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDgyMzAxMiwiZXhwIjoyMDcwMzk5MDEyfQ.jKJuos3KqupDwVSswUbDE-xZMiCDAFgz6vnth-ZhA7Q';

// Service role client for backend operations (full access)
export const supabaseAdmin = createClient<Database>(supabaseUrl, supabaseServiceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
});

// Helper function to get user from JWT token
export const getUserFromToken = async (token: string) => {
  try {
    const { data: { user }, error } = await supabaseAdmin.auth.getUser(token);
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

export default supabaseAdmin;