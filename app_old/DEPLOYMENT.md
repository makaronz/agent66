# SMC Trading Agent - Deployment Guide

## Production Deployment on Vercel

### Prerequisites
1. Vercel account
2. GitHub repository connected to Vercel
3. Supabase project configured
4. Environment variables configured

### Environment Variables for Production

Configure the following environment variables in Vercel dashboard:

#### Required Variables
```bash
# Supabase Configuration
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_URL=your_supabase_project_url

# Encryption & Security
ENCRYPTION_KEY=your-32-character-encryption-key-production
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Production Configuration
NODE_ENV=production
PORT=3002
LOG_LEVEL=ERROR

# Trading Configuration
DEFAULT_RISK_PERCENTAGE=2
MAX_CONCURRENT_TRADES=5
DEFAULT_STOP_LOSS_PERCENTAGE=1
DEFAULT_TAKE_PROFIT_PERCENTAGE=3

# Performance & Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
VITE_BINANCE_RATE_LIMIT_REQUESTS=1200
VITE_BINANCE_RATE_LIMIT_INTERVAL=60000
VITE_MARKET_DATA_THROTTLE_MS=60000

# Production Flags
VITE_ENABLE_STRICT_MODE=true
VITE_ENABLE_DEBUG_LOGS=false
VITE_ENABLE_PERFORMANCE_MONITORING=true
VITE_WEBSOCKET_RECONNECT_DELAY=5000
VITE_MAX_RECONNECT_ATTEMPTS=3
VITE_WEBSOCKET_PING_INTERVAL=30000
VITE_WEBSOCKET_PONG_TIMEOUT=10000

# External Services (Disabled for initial deployment)
VAULT_ENABLED=false
REDIS_ENABLED=false
```

### Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "feat: prepare for production deployment"
   git push origin main
   ```

2. **Configure Vercel Project**
   - Import project from GitHub
   - Set build command: `pnpm run build`
   - Set output directory: `dist`
   - Set install command: `pnpm install`

3. **Configure Environment Variables**
   - Add all required environment variables in Vercel dashboard
   - Ensure sensitive keys are properly secured

4. **Deploy**
   - Vercel will automatically deploy on push to main branch
   - Monitor build logs for any issues

### Post-Deployment Checklist

- [ ] Application loads without errors
- [ ] Authentication works with Supabase
- [ ] Market data connection is established
- [ ] Trading interface is functional
- [ ] All API endpoints respond correctly
- [ ] Performance monitoring is active
- [ ] Error logging is configured

### Rollback Plan

If deployment fails:
1. Check Vercel build logs for errors
2. Verify environment variables are correctly set
3. Use Vercel's rollback feature to previous deployment
4. Fix issues locally and redeploy

### Monitoring

- Monitor Vercel analytics for performance
- Check Supabase logs for database issues
- Monitor application logs for runtime errors
- Set up alerts for critical failures

### Security Considerations

- All API keys are stored as environment variables
- HTTPS is enforced by Vercel
- CSP headers are configured
- Rate limiting is enabled
- Input validation is implemented

### Performance Optimizations

- Bundle size optimized (~217KB gzipped)
- Code splitting implemented
- Lazy loading for components
- Image optimization enabled
- Caching strategies configured