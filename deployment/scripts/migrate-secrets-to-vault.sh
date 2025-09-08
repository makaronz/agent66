#!/bin/bash

# Script to migrate existing secrets from environment variables to HashiCorp Vault
# This script reads from .env files and stores secrets in Vault

set -e

VAULT_ADDR=${VAULT_ADDR:-"http://localhost:8200"}
ENV_FILE=${1:-".env"}
API_ENV_FILE=${2:-"api/.env"}
PROJECT_ROOT=${3:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"}

if [ -z "$VAULT_TOKEN" ]; then
  echo "❌ VAULT_TOKEN not set. Please authenticate with Vault first."
  exit 1
fi

echo "🔄 Migrating secrets from environment files to Vault..."

# Function to extract value from env file
get_env_value() {
  local file=$1
  local key=$2
  local full_path="$PROJECT_ROOT/$file"
  
  if [ -f "$full_path" ]; then
    grep "^${key}=" "$full_path" | cut -d'=' -f2- | sed 's/^"//' | sed 's/"$//' | head -1
  fi
}

# Migrate Supabase secrets
echo "📦 Migrating Supabase secrets..."
SUPABASE_URL=$(get_env_value "$ENV_FILE" "VITE_SUPABASE_URL")
SUPABASE_ANON_KEY=$(get_env_value "$ENV_FILE" "VITE_SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY=$(get_env_value "$ENV_FILE" "SUPABASE_SERVICE_ROLE_KEY")

if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_SERVICE_ROLE_KEY" ]; then
  vault kv put secret/smc-trading/supabase \
    url="$SUPABASE_URL" \
    service_role_key="$SUPABASE_SERVICE_ROLE_KEY" \
    anon_key="$SUPABASE_ANON_KEY"
  echo "✅ Supabase secrets migrated"
fi

# Migrate JWT and encryption secrets
echo "🔐 Migrating JWT and encryption secrets..."
JWT_SECRET=$(get_env_value "$API_ENV_FILE" "JWT_SECRET")
ENCRYPTION_KEY=$(get_env_value "$API_ENV_FILE" "ENCRYPTION_KEY")

if [ -n "$JWT_SECRET" ] && [ -n "$ENCRYPTION_KEY" ]; then
  vault kv put secret/smc-trading/jwt \
    secret="$JWT_SECRET" \
    encryption_key="$ENCRYPTION_KEY"
  echo "✅ JWT and encryption secrets migrated"
fi

# Migrate exchange API keys (if they exist in environment)
echo "💱 Migrating exchange API keys..."

# Check for Binance keys
BINANCE_API_KEY=$(get_env_value "$API_ENV_FILE" "BINANCE_API_KEY")
BINANCE_SECRET_KEY=$(get_env_value "$API_ENV_FILE" "BINANCE_SECRET_KEY")

if [ -n "$BINANCE_API_KEY" ] && [ -n "$BINANCE_SECRET_KEY" ]; then
  vault kv put secret/smc-trading/exchanges/binance \
    api_key="$BINANCE_API_KEY" \
    api_secret="$BINANCE_SECRET_KEY"
  echo "✅ Binance API keys migrated"
else
  echo "⚠️  Binance API keys not found in environment files"
fi

# Check for Bybit keys
BYBIT_API_KEY=$(get_env_value "$API_ENV_FILE" "BYBIT_API_KEY")
BYBIT_SECRET_KEY=$(get_env_value "$API_ENV_FILE" "BYBIT_SECRET_KEY")

if [ -n "$BYBIT_API_KEY" ] && [ -n "$BYBIT_SECRET_KEY" ]; then
  vault kv put secret/smc-trading/exchanges/bybit \
    api_key="$BYBIT_API_KEY" \
    api_secret="$BYBIT_SECRET_KEY"
  echo "✅ Bybit API keys migrated"
else
  echo "⚠️  Bybit API keys not found in environment files"
fi

# Check for Oanda keys
OANDA_API_KEY=$(get_env_value "$API_ENV_FILE" "OANDA_API_KEY")
OANDA_ACCOUNT_ID=$(get_env_value "$API_ENV_FILE" "OANDA_ACCOUNT_ID")

if [ -n "$OANDA_API_KEY" ] && [ -n "$OANDA_ACCOUNT_ID" ]; then
  vault kv put secret/smc-trading/exchanges/oanda \
    api_key="$OANDA_API_KEY" \
    account_id="$OANDA_ACCOUNT_ID"
  echo "✅ Oanda API keys migrated"
else
  echo "⚠️  Oanda API keys not found in environment files"
fi

# Migrate database secrets
echo "🗄️  Migrating database secrets..."
DB_PASSWORD=$(get_env_value "$ENV_FILE" "DB_PASSWORD")
DATABASE_URL=$(get_env_value "$ENV_FILE" "DATABASE_URL")

if [ -n "$DATABASE_URL" ]; then
  vault kv put secret/smc-trading/database \
    url="$DATABASE_URL" \
    password="${DB_PASSWORD:-CHANGE_ME_DATABASE_PASSWORD}"
  echo "✅ Database secrets migrated"
fi

# Migrate Redis secrets
echo "📊 Migrating Redis secrets..."
REDIS_PASSWORD=$(get_env_value "$ENV_FILE" "REDIS_PASSWORD")

vault kv put secret/smc-trading/redis \
  password="${REDIS_PASSWORD:-CHANGE_ME_REDIS_PASSWORD}"
echo "✅ Redis secrets migrated"

echo ""
echo "✅ Secret migration completed!"
echo ""
echo "🔒 Security recommendations:"
echo "   1. Remove secrets from .env files after verification"
echo "   2. Add .env files to .gitignore if not already"
echo "   3. Rotate all API keys and passwords"
echo "   4. Enable Vault audit logging"
echo "   5. Set up proper backup for Vault data"
echo ""
echo "📋 Verify migration with:"
echo "   vault kv list secret/smc-trading/"
echo "   vault kv get secret/smc-trading/supabase"