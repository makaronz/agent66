#!/usr/bin/env tsx

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';

// Configuration
const SECRETS_FILE = '.env.secrets';
const SECRETS_TEMPLATE_FILE = '.env.template';
const SECRETS_OUTPUT_FILE = '.env.local';

// Secret generation functions
function generateSecureSecret(length: number): string {
  return crypto.randomBytes(length).toString('base64').slice(0, length);
}

function generateJWTSecret(): string {
  return generateSecureSecret(64); // 48 bytes base64 encoded, trimmed to 64 chars
}

function generateEncryptionKey(): string {
  return crypto.randomBytes(16).toString('hex'); // 32 hex characters = 16 bytes
}

function generateSessionSecret(): string {
  return generateSecureSecret(64);
}

function generateUUID(): string {
  return crypto.randomUUID();
}

// Secrets configuration
const secretsConfig = {
  // JWT Secrets
  JWT_SECRET: generateJWTSecret(),
  JWT_ACCESS_SECRET: generateJWTSecret(),
  JWT_REFRESH_SECRET: generateJWTSecret(),

  // Encryption Key (32 characters for AES-256)
  ENCRYPTION_KEY: generateEncryptionKey(),

  // Session Secret
  SESSION_SECRET: generateSessionSecret(),

  // Development Database Credentials
  DB_PASSWORD: generateSecureSecret(32),
  REDIS_PASSWORD: generateSecureSecret(24),

  // Application IDs
  APP_INSTANCE_ID: generateUUID(),
  INSTALLATION_ID: generateUUID(),
};

// Generate secrets file content
function generateSecretsContent(): string {
  const timestamp = new Date().toISOString();
  const header = `# ═══════════════════════════════════════════════════════════════════════════════
# SMC Trading Agent - Generated Secrets
# ═══════════════════════════════════════════════════════════════════════════════
#
# ⚠️  SECURITY WARNING:
# This file contains sensitive information and should NEVER be committed to version control.
# Add this file to your .gitignore immediately.
#
# 📅 Generated: ${timestamp}
# 🔑 Algorithm: cryptographically secure random (node:crypto)
# ═══════════════════════════════════════════════════════════════════════════════

`;

  const secrets = Object.entries(secretsConfig)
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  const footer = `

# ═══════════════════════════════════════════════════════════════════════════════
# 📋 SECURITY CHECKLIST:
# ═══════════════════════════════════════════════════════════════════════════════
# ✅ Cryptographically secure secrets generated
# ✅ Unique values for each secret
# ✅ Proper length requirements met
# ✅ File added to .gitignore
#
# 🔄 ROTATION SCHEDULE:
# • JWT Secrets: Every 90 days
# • Encryption Key: Every 180 days
# • Session Secret: Every 60 days
# • Database Passwords: Every 90 days
# ═══════════════════════════════════════════════════════════════════════════════
`;

  return header + secrets + footer;
}

// Validate secrets
function validateSecrets(): boolean {
  console.log('🔍 Validating generated secrets...');

  let isValid = true;

  // Check JWT secrets
  if (secretsConfig.JWT_SECRET.length < 32) {
    console.error('❌ JWT_SECRET too short (minimum 32 characters)');
    isValid = false;
  }

  if (secretsConfig.JWT_ACCESS_SECRET.length < 32) {
    console.error('❌ JWT_ACCESS_SECRET too short (minimum 32 characters)');
    isValid = false;
  }

  if (secretsConfig.JWT_REFRESH_SECRET.length < 32) {
    console.error('❌ JWT_REFRESH_SECRET too short (minimum 32 characters)');
    isValid = false;
  }

  // Check encryption key
  if (secretsConfig.ENCRYPTION_KEY.length !== 32) {
    console.error('❌ ENCRYPTION_KEY must be exactly 32 characters');
    isValid = false;
  }

  // Check session secret
  if (secretsConfig.SESSION_SECRET.length < 32) {
    console.error('❌ SESSION_SECRET too short (minimum 32 characters)');
    isValid = false;
  }

  // Check for uniqueness
  const secretsArray = Object.values(secretsConfig);
  const uniqueSecrets = new Set(secretsArray);

  if (secretsArray.length !== uniqueSecrets.size) {
    console.error('❌ Duplicate secrets detected - all secrets must be unique');
    isValid = false;
  }

  if (isValid) {
    console.log('✅ All secrets validated successfully');
  }

  return isValid;
}

// Create .gitignore entry
function updateGitIgnore(): void {
  const gitignorePath = '.gitignore';
  let gitignoreContent = '';

  if (fs.existsSync(gitignorePath)) {
    gitignoreContent = fs.readFileSync(gitignorePath, 'utf-8');
  }

  const entriesToAdd = [
    '# Secrets',
    '.env.secrets',
    '.env.local',
    '.env.production',
    '',
  ];

  entriesToAdd.forEach(entry => {
    if (!gitignoreContent.includes(entry)) {
      gitignoreContent += entry + '\n';
    }
  });

  fs.writeFileSync(gitignorePath, gitignoreContent.trim());
  console.log('📝 Updated .gitignore with secrets entries');
}

// Save secrets file
function saveSecretsFile(): void {
  const content = generateSecretsContent();

  // Save secrets file
  fs.writeFileSync(SECRETS_FILE, content);
  console.log(`💾 Generated secrets file: ${SECRETS_FILE}`);

  // Save local environment file
  fs.writeFileSync(SECRETS_OUTPUT_FILE, content);
  console.log(`💾 Created local environment file: ${SECRETS_OUTPUT_FILE}`);
}

// Display security information
function displaySecurityInfo(): void {
  console.log('\n🔐 SECURITY INFORMATION:');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('✅ Cryptographically secure secrets generated');
  console.log('✅ All secrets meet minimum length requirements');
  console.log('✅ All secrets are unique');
  console.log('✅ Files added to .gitignore');
  console.log('');
  console.log('📋 NEXT STEPS:');
  console.log('1. Review the generated secrets in .env.local');
  console.log('2. Copy .env.template to .env for your environment');
  console.log('3. Update .env with your actual API keys and URLs');
  console.log('4. Start the application: npm run dev');
  console.log('');
  console.log('🔄 SECRET ROTATION:');
  console.log('• Re-run this script every 90 days for JWT secrets');
  console.log('• Re-run this script every 180 days for encryption key');
  console.log('• Keep a secure backup of old secrets for transition');
  console.log('═══════════════════════════════════════════════════════════════');
}

// Main execution
function main(): void {
  console.log('🔑 Generating secure secrets for SMC Trading Agent...');
  console.log('');

  try {
    // Validate secrets
    if (!validateSecrets()) {
      console.error('❌ Secret validation failed');
      process.exit(1);
    }

    // Update .gitignore
    updateGitIgnore();

    // Save secrets file
    saveSecretsFile();

    // Display security information
    displaySecurityInfo();

    console.log('✅ Secret generation completed successfully');

  } catch (error) {
    console.error('❌ Error generating secrets:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

export {
  generateJWTSecret,
  generateEncryptionKey,
  generateSessionSecret,
  generateSecureSecret,
  secretsConfig,
};