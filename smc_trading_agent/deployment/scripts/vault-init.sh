#!/bin/bash

# Vault Initialization and Configuration Script for SMC Trading Agent
# This script initializes Vault, creates policies, and sets up authentication

set -e

VAULT_ADDR=${VAULT_ADDR:-"http://localhost:8200"}
VAULT_NAMESPACE=${VAULT_NAMESPACE:-"vault"}
SMC_NAMESPACE=${SMC_NAMESPACE:-"smc-trading"}

echo "🔐 Initializing HashiCorp Vault for SMC Trading Agent..."

# Wait for Vault to be ready
echo "⏳ Waiting for Vault to be ready..."
until curl -s ${VAULT_ADDR}/v1/sys/health > /dev/null; do
  echo "Waiting for Vault..."
  sleep 5
done

# Initialize Vault if not already initialized
if ! vault status > /dev/null 2>&1; then
  echo "🚀 Initializing Vault..."
  vault operator init -key-shares=5 -key-threshold=3 -format=json > vault-keys.json
  
  echo "🔓 Unsealing Vault..."
  UNSEAL_KEY_1=$(cat vault-keys.json | jq -r '.unseal_keys_b64[0]')
  UNSEAL_KEY_2=$(cat vault-keys.json | jq -r '.unseal_keys_b64[1]')
  UNSEAL_KEY_3=$(cat vault-keys.json | jq -r '.unseal_keys_b64[2]')
  
  vault operator unseal $UNSEAL_KEY_1
  vault operator unseal $UNSEAL_KEY_2
  vault operator unseal $UNSEAL_KEY_3
  
  # Get root token
  ROOT_TOKEN=$(cat vault-keys.json | jq -r '.root_token')
  export VAULT_TOKEN=$ROOT_TOKEN
  
  echo "✅ Vault initialized and unsealed"
else
  echo "ℹ️  Vault already initialized"
fi

# Authenticate with Vault
if [ -z "$VAULT_TOKEN" ]; then
  echo "❌ VAULT_TOKEN not set. Please set it and run again."
  exit 1
fi

echo "🔧 Configuring Vault..."

# Enable secrets engines
echo "📦 Enabling secrets engines..."
vault secrets enable -path=secret kv-v2
vault secrets enable transit
vault secrets enable database

# Enable auth methods
echo "🔑 Enabling authentication methods..."
vault auth enable kubernetes

# Configure Kubernetes auth
echo "🎯 Configuring Kubernetes authentication..."
kubectl create serviceaccount vault-auth -n $VAULT_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Create ClusterRoleBinding for Vault to access Kubernetes API
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: role-tokenreview-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:auth-delegator
subjects:
- kind: ServiceAccount
  name: vault-auth
  namespace: $VAULT_NAMESPACE
EOF

# Get Kubernetes cluster info
VAULT_SA_NAME=$(kubectl get sa vault-auth -n $VAULT_NAMESPACE -o jsonpath="{.secrets[*]['name']}")
SA_JWT_TOKEN=$(kubectl get secret $VAULT_SA_NAME -n $VAULT_NAMESPACE -o jsonpath="{.data.token}" | base64 --decode)
SA_CA_CRT=$(kubectl get secret $VAULT_SA_NAME -n $VAULT_NAMESPACE -o jsonpath="{.data['ca\.crt']}" | base64 --decode)
K8S_HOST=$(kubectl config view --raw --minify --flatten -o jsonpath='{.clusters[].cluster.server}')

# Configure Kubernetes auth in Vault
vault write auth/kubernetes/config \
  token_reviewer_jwt="$SA_JWT_TOKEN" \
  kubernetes_host="$K8S_HOST" \
  kubernetes_ca_cert="$SA_CA_CRT"

# Create policies
echo "📋 Creating Vault policies..."

# SMC Trading Agent policy
vault policy write smc-trading-policy - <<EOF
# KV secrets for SMC Trading Agent
path "secret/data/smc-trading/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/smc-trading/*" {
  capabilities = ["list"]
}

# Database credentials
path "database/creds/smc-trading-role" {
  capabilities = ["read"]
}

# Transit engine for encryption
path "transit/encrypt/smc-trading" {
  capabilities = ["update"]
}

path "transit/decrypt/smc-trading" {
  capabilities = ["update"]
}

# Token management
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
EOF

# API Gateway policy
vault policy write api-gateway-policy - <<EOF
# API Gateway secrets
path "secret/data/api-gateway/*" {
  capabilities = ["read"]
}

path "secret/data/smc-trading/jwt" {
  capabilities = ["read"]
}

# Token management
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
EOF

# Execution Engine policy
vault policy write execution-engine-policy - <<EOF
# Execution Engine secrets
path "secret/data/execution-engine/*" {
  capabilities = ["read"]
}

path "secret/data/smc-trading/exchanges/*" {
  capabilities = ["read"]
}

# Transit engine for encryption
path "transit/encrypt/execution-engine" {
  capabilities = ["update"]
}

path "transit/decrypt/execution-engine" {
  capabilities = ["update"]
}

# Token management
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
EOF

# Create Kubernetes roles
echo "👥 Creating Kubernetes roles..."

vault write auth/kubernetes/role/smc-trading-role \
  bound_service_account_names=smc-trading-agent \
  bound_service_account_namespaces=$SMC_NAMESPACE \
  policies=smc-trading-policy \
  ttl=24h

vault write auth/kubernetes/role/api-gateway-role \
  bound_service_account_names=api-gateway \
  bound_service_account_namespaces=$SMC_NAMESPACE \
  policies=api-gateway-policy \
  ttl=24h

vault write auth/kubernetes/role/execution-engine-role \
  bound_service_account_names=execution-engine \
  bound_service_account_namespaces=$SMC_NAMESPACE \
  policies=execution-engine-policy \
  ttl=24h

# Configure transit engine
echo "🔐 Configuring transit encryption..."
vault write -f transit/keys/smc-trading
vault write -f transit/keys/execution-engine

# Store initial secrets (these should be replaced with actual values)
echo "🗝️  Storing initial secrets..."

# Database secrets
vault kv put secret/smc-trading/database \
  url="postgresql://smc_user:CHANGE_ME@timescaledb:5432/smc_db" \
  password="CHANGE_ME_DATABASE_PASSWORD"

# JWT secrets
vault kv put secret/smc-trading/jwt \
  secret="CHANGE_ME_JWT_SECRET_KEY_32_CHARS_MIN" \
  encryption_key="CHANGE_ME_ENCRYPTION_KEY_32_CHARS"

# Exchange API keys (placeholders - replace with actual keys)
vault kv put secret/smc-trading/exchanges/binance \
  api_key="CHANGE_ME_BINANCE_API_KEY" \
  api_secret="CHANGE_ME_BINANCE_API_SECRET"

vault kv put secret/smc-trading/exchanges/bybit \
  api_key="CHANGE_ME_BYBIT_API_KEY" \
  api_secret="CHANGE_ME_BYBIT_API_SECRET"

vault kv put secret/smc-trading/exchanges/oanda \
  api_key="CHANGE_ME_OANDA_API_KEY" \
  account_id="CHANGE_ME_OANDA_ACCOUNT_ID"

# Redis secrets
vault kv put secret/smc-trading/redis \
  password="CHANGE_ME_REDIS_PASSWORD"

# Supabase secrets
vault kv put secret/smc-trading/supabase \
  url="https://fqhuoszrysapxrvyaqao.supabase.co" \
  service_role_key="CHANGE_ME_SUPABASE_SERVICE_ROLE_KEY" \
  anon_key="CHANGE_ME_SUPABASE_ANON_KEY"

echo "✅ Vault configuration completed!"
echo ""
echo "🔑 Important: Save the vault-keys.json file securely!"
echo "📝 Next steps:"
echo "   1. Update the placeholder secrets with actual values"
echo "   2. Deploy the SMC Trading Agent with Vault integration"
echo "   3. Configure Vault Agent for automatic token renewal"
echo ""
echo "🌐 Vault UI available at: ${VAULT_ADDR}/ui"