#!/usr/bin/env node

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Supabase configuration
const supabaseUrl = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('❌ Missing Supabase configuration:');
  console.error('   SUPABASE_URL:', supabaseUrl ? '✓' : '❌');
  console.error('   SUPABASE_ANON_KEY:', supabaseAnonKey ? '✓' : '❌');
  process.exit(1);
}

// Create Supabase client with anon key (safer for testing)
const supabase = createClient(supabaseUrl, supabaseAnonKey);

async function checkSchema() {
  console.log('🔍 Checking database schema...');
  console.log('📍 Supabase URL:', supabaseUrl);
  
  // Test tables that should exist
  const tablesToCheck = ['users', 'user_api_keys', 'user_configurations', 'trading_sessions', 'trades', 'smc_signals'];
  
  for (const table of tablesToCheck) {
    try {
      console.log(`\n🔍 Checking table: ${table}`);
      
      const { data, error, count } = await supabase
        .from(table)
        .select('*', { count: 'exact', head: true })
        .limit(1);
      
      if (error) {
        console.log(`   ❌ Table ${table}: ${error.message}`);
        if (error.code) {
          console.log(`   📋 Error code: ${error.code}`);
        }
      } else {
        console.log(`   ✅ Table ${table}: exists (${count || 0} rows)`);
      }
    } catch (err) {
      console.log(`   💥 Table ${table}: unexpected error - ${err.message}`);
    }
  }
  
  // Test authentication
  console.log('\n🔐 Testing authentication...');
  try {
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error) {
      console.log('   ℹ️  No authenticated user (expected for anon key)');
    } else {
      console.log('   ✅ User authenticated:', user?.id);
    }
  } catch (err) {
    console.log('   ⚠️  Auth check failed:', err.message);
  }
  
  // Test a simple RPC call
  console.log('\n🔧 Testing RPC functionality...');
  try {
    const { data, error } = await supabase.rpc('version');
    if (error) {
      console.log('   ❌ RPC test failed:', error.message);
    } else {
      console.log('   ✅ RPC working, PostgreSQL version:', data);
    }
  } catch (err) {
    console.log('   ⚠️  RPC test error:', err.message);
  }
}

// Run schema check
checkSchema().catch(error => {
  console.error('💥 Schema check failed:', error);
  process.exit(1);
});