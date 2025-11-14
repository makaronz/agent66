# ADR 0002: Standardize Package Management with pnpm

## Status
Accepted

## Context
The project currently has inconsistent package management:
- Root package.json specifies pnpm@8.15.4 as packageManager
- But many scripts still use 'npm' commands instead of 'pnpm'
- Backend and frontend directories don't specify package managers
- This creates confusion and potential dependency resolution issues

## Decision
Standardize on pnpm across the entire project:
1. Update all package.json scripts to use pnpm commands
2. Add packageManager specification to backend and frontend package.json
3. Create .npmrc with pnpm configuration
4. Update development documentation to reflect pnpm usage

## Consequences
- Consistent dependency management across all projects
- Faster installs and reduced disk usage with pnpm
- Better dependency resolution with pnpm's strict node_modules structure
- Teams need to be familiar with pnpm commands and differences from npm
