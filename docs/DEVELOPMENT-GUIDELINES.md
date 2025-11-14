# Agent66 Development Guidelines

## Overview
This document outlines the development standards and best practices for the Agent66 project.

## Code Quality Standards

### TypeScript Configuration
- **Strict Mode**: All TypeScript code must compile with strict mode enabled
- **No Implicit Any**: Explicit types are required for all function parameters and return values
- **Unused Variables**: Zero tolerance for unused variables or imports
- **Null Safety**: Strict null checks are enforced

### Code Formatting
- **Package Manager**: Use `pnpm` consistently across all projects
- **Linting**: ESLint configuration enforces code quality standards
- **Formatting**: Prettier is used for consistent code formatting
- **Line Length**: Maximum 100 characters per line
- **Quotes**: Single quotes for strings, double quotes for JSX

### File Organization
- **Components**: Place in `src/components/` directory
- **Hooks**: Place in `src/hooks/` directory
- **Utilities**: Place in `src/utils/` directory
- **Types**: Place in `src/types/` directory
- **Services**: Place in `src/services/` directory

### Naming Conventions
- **Files**: kebab-case for files (e.g., `user-service.ts`)
- **Components**: PascalCase for React components (e.g., `UserProfile.tsx`)
- **Variables**: camelCase for variables and functions (e.g., `getUserData`)
- **Constants**: UPPER_SNAKE_CASE for constants (e.g., `API_BASE_URL`)
- **Types**: PascalCase for type definitions (e.g., `UserType`)

### Testing Standards
- **Coverage**: Minimum 80% test coverage required
- **Unit Tests**: All business logic must have unit tests
- **Integration Tests**: API endpoints must have integration tests
- **Test Files**: Place in `__tests__/` or `*.test.ts` alongside source files

### Security Standards
- **Authentication**: All API endpoints must require authentication unless explicitly public
- **Input Validation**: All user inputs must be validated using Zod schemas
- **Secrets Management**: No secrets in code - use environment variables
- **Error Handling**: Sanitize error messages to prevent information leakage

### Performance Standards
- **Bundle Size**: Monitor and optimize bundle sizes
- **Lazy Loading**: Implement code splitting for large components
- **Database Queries**: Optimize queries and implement proper indexing
- **Caching**: Implement appropriate caching strategies

## Development Workflow

### 1. Environment Setup
```bash
# Install dependencies
pnpm install

# Setup environment
pnpm run setup:dev
```

### 2. Development Server
```bash
# Start development servers
pnpm run dev

# Start backend only
pnpm run server:dev

# Start frontend only
pnpm run client:dev
```

### 3. Code Quality Checks
```bash
# Lint code
pnpm run lint

# Fix linting issues
pnpm run lint:fix

# Type checking
pnpm run check

# Run tests
pnpm run test

# Test coverage
pnpm run test:coverage
```

### 4. Pre-commit Requirements
- All tests must pass
- Zero linting errors
- TypeScript compilation with strict mode
- Security audit must pass

### 5. Git Workflow
- Create feature branches from `main`
- Use descriptive commit messages
- Create pull requests for all changes
- Code review is required for all changes

## API Development Standards

### REST API Design
- **HTTP Methods**: Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- **Status Codes**: Use proper HTTP status codes
- **Error Responses**: Consistent error response format
- **Versioning**: API versioning via URL path (`/api/v1/`)

### Documentation
- **OpenAPI**: All endpoints must be documented with OpenAPI/Swagger
- **Comments**: Complex functions must have JSDoc comments
- **README**: Update README for new features
- **ADRs**: Document architectural decisions using ADR format

## Security Guidelines

### Authentication & Authorization
- **JWT**: Use JSON Web Tokens for authentication
- **Roles**: Implement role-based access control
- **MFA**: Multi-factor authentication for sensitive operations
- **Sessions**: Secure session management

### Data Protection
- **Encryption**: Encrypt sensitive data at rest and in transit
- **Validation**: Validate all inputs and outputs
- **Sanitization**: Sanitize user inputs to prevent XSS
- **SQL Injection**: Use parameterized queries

### Security Testing
```bash
# Security audit
pnpm run security:audit

# Check for exposed secrets
pnpm run security:check-secrets

# Full security scan
pnpm run security:scan
```

## Performance Optimization

### Frontend Optimization
- **Code Splitting**: Implement lazy loading for routes
- **Bundle Analysis**: Regular bundle size analysis
- **Image Optimization**: Optimize images and assets
- **Caching**: Implement browser caching strategies

### Backend Optimization
- **Database Indexing**: Proper database indexes
- **Query Optimization**: Efficient database queries
- **Caching**: Redis caching for frequently accessed data
- **Rate Limiting**: Implement API rate limiting

## Monitoring & Logging

### Application Monitoring
- **Health Checks**: Implement health check endpoints
- **Metrics**: Collect application metrics
- **Error Tracking**: Comprehensive error logging
- **Performance**: Monitor response times

### Logging Standards
- **Structured Logging**: Use structured log formats
- **Log Levels**: Appropriate log levels (info, warn, error)
- **Security Events**: Log all security-relevant events
- **Audit Trail**: Maintain audit trail for sensitive operations

## Deployment Guidelines

### Environment Management
- **Development**: Local development environment
- **Staging**: Pre-production testing environment
- **Production**: Live production environment

### Deployment Process
- **CI/CD**: Automated testing and deployment
- **Rollbacks**: Ability to rollback deployments quickly
- **Health Checks**: Post-deployment health verification
- **Monitoring**: Monitor deployment success

## Contributing

### Before Contributing
1. Read these guidelines
2. Set up development environment
3. Run all tests and quality checks
4. Create issue for your proposed change

### Submitting Changes
1. Fork the repository
2. Create feature branch
3. Implement your changes
4. Add tests for your changes
5. Run quality checks
6. Submit pull request

### Code Review Process
1. Automated checks must pass
2. Manual code review by maintainers
3. Security review for sensitive changes
4. Approval required before merge
