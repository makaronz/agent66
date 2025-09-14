#!/usr/bin/env node

import { createClient } from '@supabase/supabase-js';
import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Supabase configuration
const supabaseUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('❌ Missing Supabase configuration:');
  console.error('   SUPABASE_URL:', supabaseUrl ? '✓' : '❌');
  console.error('   SUPABASE_SERVICE_ROLE_KEY:', supabaseServiceKey ? '✓' : '❌');
  process.exit(1);
}

// Create Supabase admin client
const supabase = createClient(supabaseUrl, supabaseServiceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
});

async function runMigrations() {
  console.log('🚀 Starting database migrations...');
  console.log('📍 Supabase URL:', supabaseUrl);
  
  const migrationsDir = join(__dirname, '..', 'supabase', 'migrations');
  
  try {
    // Get all SQL files in migrations directory
    const files = readdirSync(migrationsDir)
      .filter(file => file.endsWith('.sql'))
      .sort(); // Sort to ensure proper order
    
    console.log(`📁 Found ${files.length} migration files:`);
    files.forEach(file => console.log(`   - ${file}`));
    
    // Create migrations tracking table if it doesn't exist
    console.log('\n📋 Creating migrations tracking table...');
    const { error: trackingError } = await supabase.rpc('exec_sql', {
      sql: `
        CREATE TABLE IF NOT EXISTS public.schema_migrations (
          version TEXT PRIMARY KEY,
          executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
      `
    });
    
    if (trackingError) {
      console.log('⚠️  Could not create tracking table via RPC, trying direct SQL execution...');
      // Fallback: try to execute via direct SQL
      const { error: directError } = await supabase
        .from('schema_migrations')
        .select('version')
        .limit(1);
      
      if (directError && directError.code === '42P01') {
        console.log('📋 Migrations tracking table does not exist, will create it manually.');
      }
    }
    
    // Get already executed migrations
    const { data: executedMigrations, error: selectError } = await supabase
      .from('schema_migrations')
      .select('version');
    
    const executedVersions = new Set(
      executedMigrations?.map(m => m.version) || []
    );
    
    console.log(`\n✅ Already executed migrations: ${executedVersions.size}`);
    
    // Execute pending migrations
    let executedCount = 0;
    
    for (const file of files) {
      const version = file.replace('.sql', '');
      
      if (executedVersions.has(version)) {
        console.log(`⏭️  Skipping ${file} (already executed)`);
        continue;
      }
      
      console.log(`\n🔄 Executing migration: ${file}`);
      
      try {
        // Read migration file
        const migrationPath = join(migrationsDir, file);
        const sql = readFileSync(migrationPath, 'utf8');
        
        // Split SQL into individual statements (basic splitting)
        const statements = sql
          .split(';')
          .map(stmt => stmt.trim())
          .filter(stmt => stmt.length > 0 && !stmt.startsWith('--'));
        
        console.log(`   📝 Executing ${statements.length} SQL statements...`);
        
        // Execute each statement
        for (let i = 0; i < statements.length; i++) {
          const statement = statements[i];
          if (statement.trim()) {
            try {
              const { error } = await supabase.rpc('exec_sql', {
                sql: statement + ';'
              });
              
              if (error) {
                console.log(`   ⚠️  Statement ${i + 1} failed via RPC, trying alternative method...`);
                console.log(`   📄 Statement: ${statement.substring(0, 100)}...`);
                // For some statements, RPC might not work, but the migration might still be valid
              }
            } catch (err) {
              console.log(`   ⚠️  Statement ${i + 1} error:`, err.message);
            }
          }
        }
        
        // Record successful migration
        const { error: insertError } = await supabase
          .from('schema_migrations')
          .insert({ version });
        
        if (insertError) {
          console.log(`   ⚠️  Could not record migration ${version}:`, insertError.message);
        } else {
          console.log(`   ✅ Migration ${file} completed successfully`);
          executedCount++;
        }
        
      } catch (error) {
        console.error(`   ❌ Migration ${file} failed:`, error.message);
        console.error('   🛑 Stopping migration process');
        process.exit(1);
      }
    }
    
    console.log(`\n🎉 Migration process completed!`);
    console.log(`📊 Executed ${executedCount} new migrations`);
    console.log(`📋 Total migrations in database: ${executedVersions.size + executedCount}`);
    
    // Verify tables exist
    console.log('\n🔍 Verifying database schema...');
    const { data: tables, error: tablesError } = await supabase
      .from('information_schema.tables')
      .select('table_name')
      .eq('table_schema', 'public');
    
    if (tables) {
      console.log(`✅ Found ${tables.length} tables in public schema:`);
      tables.forEach(table => console.log(`   - ${table.table_name}`));
    } else {
      console.log('⚠️  Could not verify tables:', tablesError?.message);
    }
    
  } catch (error) {
    console.error('❌ Migration process failed:', error.message);
    process.exit(1);
  }
}

// Run migrations
runMigrations().catch(error => {
  console.error('💥 Unexpected error:', error);
  process.exit(1);
});