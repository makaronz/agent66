# 📋 App_v2 Migration Plan
**Date:** 2025-10-03  
**Objective:** Promote app_v2 to main application, archive legacy trading system code

---

## 🎯 Migration Strategy

### Phase 1: Backup
- Create timestamped backup: `../agent66_backup_20251003_HHMMSS/`
- Full repository copy (excluding node_modules, target, .venv)

### Phase 2: Archive Legacy Code
Move to `app_old/`:
```
OLD APPLICATION CODE:
- api/ (FastAPI backend)
- api_fastapi.py
- src/ (Rust code)
- data_pipeline/
- database/
- decision_engine/
- execution_engine/
- risk_manager/
- smc_detector/
- training/
- compliance/
- providers/
- supabase/
- deployment/ (old K8s configs)
- terraform/
- monitoring/
- scripts/ (old scripts)
- tests/ (old Python tests)
- tools/
- examples/
- binance_docs/

OLD CONFIG FILES:
- Cargo.toml, Cargo.lock (Rust)
- requirements.txt (Python)
- pytest.ini
- config.yaml
- config_loader.py
- config_validator.py
- validators.py
- interfaces.py
- service_manager.py
- health_monitor.py
- vault_client.py
- error_handlers.py
- stream_processor.py
- stream_processor_main.py
- integration_example.py
- isolated_test.py
- main.py
- *.Dockerfile files

OLD DOCUMENTATION:
- ARCHITECTURE.md (old)
- DEPLOYMENT.md (old)
- API.md (old)
- RUNBOOK.md (old)
- SECURITY_NOTES.md (old)
- SETUP.md (old)
- TESTS.md (old)
- V2_MIGRATION_PLAN.md
- app_v2_comprehensive_review.md
- refactorprompt.md

OLD BUILD ARTIFACTS/DATA:
- data/
- logs/
- htmlcov/
- dist/
- public/ (old)
```

### Phase 3: Keep in Root
```
GIT & VERSION CONTROL:
- .git/
- .github/
- .gitignore
- .vercel/
- .vercelignore

ESSENTIAL CONFIG:
- .env (DO NOT MOVE - git ignored)
- .env.example
- .env.production

ROOT DOCUMENTATION (UPDATE LATER):
- README.md (update to reflect new structure)

WORKSPACE CONFIGS:
- .cursor/
- .vscode/
- .claude/
- .todo2/
- .codacy/
- .kilocode/
- .kiro/
- .superdesign/
- .trae/

APP_V2 (TO BE PROMOTED):
- app_v2/ (will be moved to root)

SPECIAL FOLDERS (DISCUSS):
- LLP/ (appears to be a backup/test folder)

NODE ARTIFACTS (BUILD):
- node_modules (stays, regenerated)
- package.json (if exists at root)
- package-lock.json (if exists at root)
```

### Phase 4: Promote app_v2
```
app_v2/backend/ → backend/
app_v2/frontend/ → frontend/

Remove empty app_v2/ folder
```

### Phase 5: Update Documentation
- Update README.md with new structure
- Document backup location
- Update package.json scripts (if needed)

---

## ⚠️ Critical Considerations

### 1. Running Processes
**MUST STOP BEFORE MIGRATION:**
- Backend dev server (port 5001)
- Frontend dev server (port 3000)

### 2. Git History
- Use `git mv` for all moves to preserve history
- Commit in logical chunks or one big commit

### 3. Environment Files
- `.env` files stay in root (gitignored)
- Update paths if needed

### 4. Dependencies
- `node_modules` will need reinstall after move
- No changes to package.json content needed

### 5. Database
- MongoDB connection will still work (localhost)
- No migration needed for DB

---

## 📝 Execution Steps

1. **Stop all running processes**
   ```bash
   pkill -f "npm run dev"
   pkill -f "npm start"
   ```

2. **Create backup**
   ```bash
   cd /Users/arkadiuszfudali/Git
   cp -r agent66 agent66_backup_$(date +%Y%m%d_%H%M%S)
   ```

3. **Create app_old and move legacy code**
   ```bash
   cd /Users/arkadiuszfudali/Git/agent66
   mkdir app_old
   
   # Move directories
   git mv api app_old/
   git mv src app_old/
   git mv data_pipeline app_old/
   # ... (all listed folders)
   
   # Move files
   git mv api_fastapi.py app_old/
   git mv Cargo.toml app_old/
   # ... (all listed files)
   ```

4. **Promote app_v2**
   ```bash
   git mv app_v2/backend ./backend
   git mv app_v2/frontend ./frontend
   rmdir app_v2
   ```

5. **Update README.md**
   ```bash
   # Update documentation to reflect new structure
   ```

6. **Test applications**
   ```bash
   cd backend && npm install && npm run dev
   cd frontend && npm install && npm start
   ```

7. **Commit changes**
   ```bash
   git add -A
   git commit -m "refactor: promote app_v2 to root, archive legacy trading system
   
   - Moved legacy Python/Rust trading system to app_old/
   - Promoted app_v2/backend to root backend/
   - Promoted app_v2/frontend to root frontend/
   - Preserved git history with git mv
   - Backup created at: agent66_backup_TIMESTAMP
   - Updated documentation"
   ```

---

## ✅ Verification Checklist

- [ ] Backup created and verified
- [ ] app_old/ contains all legacy code
- [ ] backend/ exists in root with all files
- [ ] frontend/ exists in root with all files
- [ ] .git/ intact and unchanged
- [ ] Backend starts: `cd backend && npm run dev`
- [ ] Frontend starts: `cd frontend && npm start`
- [ ] MongoDB connection works
- [ ] API endpoints respond
- [ ] Git history preserved
- [ ] README.md updated
- [ ] Commit successful

---

## 🔙 Rollback Plan

If something goes wrong:
```bash
cd /Users/arkadiuszfudali/Git
rm -rf agent66
cp -r agent66_backup_TIMESTAMP agent66
cd agent66
```

---

## 📊 Impact Assessment

**Pros:**
- Cleaner repository structure
- app_v2 becomes the main application
- Legacy code archived but accessible
- Easier for new developers to understand

**Cons:**
- One-time disruption
- Need to update any CI/CD pipelines
- External documentation may be outdated
- Absolute paths in configs may break

**Risk Level:** Medium (mitigated by backup)

