# Kiro Configuration & Specifications for App_v2 Project

## 📋 Overview

This directory contains comprehensive Kiro specifications and steering rules for the app_v2 full-stack trading application modernization project. The configuration ensures consistent development practices, security standards, and code quality across the entire project lifecycle.

## 🗂️ Directory Structure

```
.kiro/
├── specs/                          # Kiro Specifications
│   └── app-v2-modernization/       # Main modernization spec
│       ├── requirements.md         # EARS notation requirements
│       ├── design.md              # Technical architecture design
│       └── tasks.md               # Implementation task breakdown
├── steering/                       # Agent Steering Rules
│   ├── app-v2-best-practices.md   # Project-specific best practices
│   ├── typescript-standards.md    # TypeScript coding standards
│   ├── security-performance.md    # Security & performance guidelines
│   ├── testing-quality.md         # Testing & code quality standards
│   ├── todo2.md                   # Todo2 workflow requirements
│   └── SCAFFOLDING.md             # Template for new steering rules
├── settings/                       # Kiro Settings
│   └── mcp.json                   # MCP server configuration
└── README.md                      # This file
```

## 🎯 Specifications (Specs)

### App_v2 Modernization Spec

**Location**: `.kiro/specs/app-v2-modernization/`

A comprehensive specification for modernizing the existing app_v2 trading application to 2025 standards.

#### Requirements (`requirements.md`)
- **Format**: EARS (Easy Approach to Requirements Syntax) notation
- **Coverage**: 5 major epics with 14 user stories
- **Focus Areas**: TypeScript modernization, security hardening, performance optimization, architecture improvements, testing enhancement

#### Design (`design.md`)
- **Architecture**: Multi-layer system design with security, performance, and scalability considerations
- **Patterns**: Service layer, caching strategies, error handling, monitoring
- **Technologies**: React 18+, Node.js, TypeScript 5.3.3, MongoDB, Redis, JWT authentication

#### Tasks (`tasks.md`)
- **Structure**: 4-phase implementation plan (8 weeks total)
- **Breakdown**: 16 detailed tasks with dependencies, timelines, and acceptance criteria
- **Methodology**: Agile approach with continuous integration and testing

## 🧭 Steering Rules

### Core Development Standards

#### 1. App_v2 Best Practices (`app-v2-best-practices.md`)
- **Scope**: Project-wide development standards
- **Activation**: Applies to all files in `app_v2/**/*`
- **Coverage**: Architecture guidelines, security standards, performance patterns, code style

#### 2. TypeScript Standards (`typescript-standards.md`)
- **Scope**: All TypeScript files (`**/*.{ts,tsx}`)
- **Focus**: Type safety, interface design, runtime validation, React patterns
- **Standards**: Strict configuration, utility types, discriminated unions, testing patterns

#### 3. Security & Performance (`security-performance.md`)
- **Scope**: All app_v2 files
- **Standards**: OWASP 2025 compliance, rate limiting, caching strategies, monitoring
- **Targets**: Performance budgets, SLA definitions, health checks

#### 4. Testing & Quality (`testing-quality.md`)
- **Scope**: All test files (`**/*.{test,spec}.{ts,tsx,js,jsx}`)
- **Strategy**: Test pyramid (70% unit, 20% integration, 10% E2E)
- **Tools**: Vitest, Playwright, ESLint, Prettier, Husky

#### 5. Todo2 Workflow (`todo2.md`)
- **Scope**: All development activities
- **Methodology**: Task-driven development with research, implementation, and review phases
- **Enforcement**: Mandatory workflow for all user requests

## ⚙️ Configuration

### MCP Server Configuration (`settings/mcp.json`)

Model Context Protocol servers for enhanced development capabilities:

```json
{
  "mcpServers": {
    "todo2": {
      "command": "uvx",
      "args": ["todo2-mcp-server@latest"],
      "disabled": false,
      "autoApprove": ["create_todos", "list_todos", "update_todos"]
    },
    "memory": {
      "command": "uvx", 
      "args": ["mcp-memory@latest"],
      "disabled": false
    }
  }
}
```

## 🚀 Getting Started

### For Developers

1. **Review Project Context**
   ```bash
   # Read the comprehensive review
   cat app_v2_comprehensive_review.md
   
   # Understand the specifications
   ls .kiro/specs/app-v2-modernization/
   ```

2. **Start Development Session**
   ```bash
   # Kiro will automatically apply steering rules
   # based on file patterns and project context
   ```

3. **Follow Todo2 Workflow**
   - Every task starts with `create_todos`
   - Research phase with local and internet search
   - Implementation with proper testing
   - Review and validation

### For Kiro Agent

The steering rules are automatically applied based on file patterns:

- **TypeScript files**: Apply TypeScript standards + app_v2 best practices
- **Test files**: Apply testing standards + quality guidelines  
- **App_v2 files**: Apply security, performance, and architecture standards
- **All interactions**: Follow Todo2 workflow requirements

## 📊 Quality Gates & Standards

### Code Quality Targets
- **Test Coverage**: >80% statements, >75% branches
- **TypeScript**: Strict mode, zero `any` types
- **Security**: OWASP 2025 compliance, zero critical vulnerabilities
- **Performance**: <500ms API response, >90 Lighthouse score

### Development Workflow
1. **Research Phase**: Local codebase + internet research with verified links
2. **Implementation**: Following established patterns and standards
3. **Testing**: Unit, integration, and E2E tests as appropriate
4. **Review**: Human approval required for all changes
5. **Deployment**: Automated CI/CD with quality gates

## 🔧 Maintenance & Updates

### Adding New Steering Rules

1. Create new file in `.kiro/steering/`
2. Add frontmatter with inclusion criteria:
   ```yaml
   ---
   inclusion: fileMatch
   fileMatchPattern: 'pattern/**/*'
   ---
   ```
3. Document standards and examples
4. Test with representative files

### Updating Specifications

1. Modify requirements, design, or tasks as needed
2. Ensure consistency across all three files
3. Update task dependencies and timelines
4. Validate with stakeholders

### MCP Server Management

```bash
# List available servers
kiro mcp list

# Restart servers after config changes
kiro mcp restart

# Check server status
kiro mcp status
```

## 📚 Reference Documentation

### Key Files
- `app_v2_comprehensive_review.md` - Complete architecture analysis
- `.kiro/specs/app-v2-modernization/requirements.md` - Project requirements
- `.kiro/specs/app-v2-modernization/design.md` - Technical design
- `.kiro/specs/app-v2-modernization/tasks.md` - Implementation plan

### External Resources
- [Kiro Specs Documentation](https://docs.kiro.ai/specs)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [OWASP Top 10 2025](https://owasp.org/www-project-top-ten/)
- [React Best Practices](https://react.dev/learn)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)

## 🎯 Success Metrics

### Technical Metrics
- Zero critical security vulnerabilities
- >80% test coverage across all modules
- <500ms API response time (95th percentile)
- >90 Lighthouse performance score
- TypeScript strict mode compliance

### Business Metrics
- 30% reduction in development time
- 40% reduction in bug reports
- 25% improvement in Lighthouse scores
- 99.9% uptime SLA compliance

## 🤝 Contributing

When contributing to this project:

1. **Follow the Todo2 workflow** - All changes must go through proper task management
2. **Adhere to steering rules** - Kiro will enforce standards automatically
3. **Maintain documentation** - Update specs and steering rules as needed
4. **Test thoroughly** - Ensure all quality gates pass
5. **Security first** - Always consider security implications

## 📞 Support

For questions about:
- **Specifications**: Review `.kiro/specs/` documentation
- **Steering Rules**: Check `.kiro/steering/` guidelines  
- **MCP Configuration**: Verify `.kiro/settings/mcp.json`
- **Workflow Issues**: Consult `todo2.md` requirements

---

**Remember**: This configuration ensures consistent, secure, and high-quality development practices across the entire app_v2 modernization project. The combination of detailed specifications and automated steering rules provides both guidance and enforcement for development standards.