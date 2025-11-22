# SMC Trading Agent - Activity Log

1 2025-01-27 12:00:00 Replaced all mock data in Monitoring page with real live data from API endpoints
2 2025-01-27 12:30:00 Added tooltips with explanations for all error/issue fields in Monitoring page (system metrics, services status, alerts, error messages)
3 2025-01-27 13:00:00 Fixed TypeError in Dashboard.tsx - added safe checks for undefined performance properties before calling toFixed()
4 2025-01-27 13:30:00 Removed all mock data from RiskManagement.tsx and connected to real API endpoints (risk metrics, positions, performance)
5 2025-01-27 13:30:00 Added comprehensive tooltips with explanations for all titles, headers, concepts, and risk management terms in RiskManagement.tsx
6 2025-01-27 14:00:00 Fixed Total Portfolio Value calculation - now uses real equity from account summary (balance + unrealized P&L) instead of incorrect formula
7 2025-01-27 15:00:00 Fixed Configuration page - Binance now shows disconnected when no API key is set, added endpoint /exchange-config to get real connection status from backend
8 2025-11-20 14:51:07 Fixed web-eval-agent MCP server configuration - created Python wrapper to redirect log messages to stderr, fixed nested mcpServers JSON structure issue
9 2025-11-21 01:36:18 Created comprehensive CONTRIBUTING.md guide with code of conduct, development setup, coding standards, commit guidelines, and PR process
10 2025-11-21 01:36:18 Created comprehensive DEVELOPER_GUIDE.md with architecture deep dive, development environment setup, code organization, key components, data flow, and debugging guide
11 2025-11-21 01:36:18 Updated README.md and DOCUMENTATION_INDEX.md with links to new contributing and developer documentation
12 2025-11-21 01:44:51 Fixed SyntaxError in training/deploy_models.py line 629 - simplified complex expression by splitting into separate variables (pth_files and pkl_files)
13 2025-11-21 01:46:32 Fixed ModuleNotFoundError in training/deploy_models.py - changed imports from relative to absolute package imports (from training.smc_training_pipeline and training.smc_feature_engineer)
14 2025-11-21 01:52:27 Fixed AttributeError in quick_start_training.py - changed config from dict to TrainingConfig dataclass object using create_training_config(), fixed date handling to use datetime objects instead of ISO strings
15 2025-11-22 10:47:24 Completed repository reorganization - moved all content from smc_trading_agent/ to root directory, archived old files, updated all hardcoded paths and imports, merged .gitignore files, updated documentation
