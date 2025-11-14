# Agent66 Frontend - Production Management System

A comprehensive production management system built with React 18, TypeScript, Redux Toolkit, and Tailwind CSS for film and commercial production tracking.

## 🚀 Features

- **Authentication**: Secure login/register flows with JWT tokens
- **Dashboard**: Real-time production overview with metrics
- **Time Tracking**: Advanced time clock with GPS location support
- **Project Management**: Complete production workflow management
- **Crew Management**: Team coordination and scheduling
- **Analytics**: Comprehensive reporting and insights
- **Responsive Design**: Mobile-first responsive UI

## 🛠️ Tech Stack

- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit + React Query
- **Routing**: React Router v6
- **Forms**: React Hook Form with Zod validation
- **Styling**: Tailwind CSS
- **Icons**: Heroicons
- **Notifications**: React Hot Toast
- **Testing**: Jest + React Testing Library + jest-axe

## 📦 Installation

1. Clone the repository
2. Navigate to the `frontend` directory
3. Create a `.env` file based on `.env.example`
   ```bash
   cp .env.example .env
   ```
4. Set your environment variables:
   ```env
   REACT_APP_API_URL=http://localhost:3001/api
   ```
5. Install dependencies:
   ```bash
   npm install
   ```

## 🏃‍♂️ Running the app

```bash
# Development
npm start

# Build for production
npm run build

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run accessibility tests
npm run test:a11y

# Run performance tests
npm run test:performance
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## 🧪 Testing

This application includes a comprehensive testing suite:

### Test Categories
- **Unit Tests**: Component and utility function testing
- **Integration Tests**: User workflow testing
- **Accessibility Tests**: WCAG compliance validation
- **Performance Tests**: Render and memory optimization testing

### Coverage
- **Target**: 70%+ coverage across all metrics
- **Tools**: Jest, React Testing Library, jest-axe
- **CI/CD**: Automated testing in GitHub Actions

### Running Tests
```bash
# All tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage

# Specific categories
npm run test:a11y        # Accessibility
npm run test:performance  # Performance
npm run test:integration  # Integration
```

## 🏗️ Project Structure

```
src/
├── components/          # React components
│   ├── auth/           # Authentication components
│   ├── layout/         # Layout components
│   ├── Dashboard.tsx   # Main dashboard
│   ├── TimeClock.tsx   # Time tracking
│   ├── Projects.tsx    # Project management
│   ├── Crew.tsx        # Crew management
│   └── Reports.tsx     # Analytics and reports
├── store/              # Redux store
│   ├── slices/         # Redux slices
│   ├── hooks.ts        # Typed hooks
│   └── store.ts        # Store configuration
├── __tests__/          # Test files
│   ├── components/     # Component tests
│   ├── integration/    # Integration tests
│   ├── accessibility/  # A11y tests
│   ├── performance/    # Performance tests
│   └── utils/          # Testing utilities
└── utils/              # Utility functions
```

## 🔧 Configuration

### Environment Variables
- `REACT_APP_API_URL`: Backend API URL
- `REACT_APP_ENV`: Application environment (development/production)

### Browser Support
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## 🚀 Deployment

### Production Build
```bash
npm run build
```

### Environment-Specific Builds
- **Development**: Local development with hot reload
- **Production**: Optimized build with minification
- **Staging**: Production-like environment for testing

### Deployment Platforms
- **Vercel**: Recommended for React applications
- **Netlify**: Static site hosting
- **AWS S3 + CloudFront**: Custom deployment
- **Docker**: Containerized deployment

## 📱 Accessibility

This application is built with accessibility in mind:

- **WCAG 2.1 AA Compliance**: Automated testing with jest-axe
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Color Contrast**: WCAG compliant color schemes
- **Focus Management**: Proper focus handling and indicators

## ⚡ Performance

### Optimization Features
- **Code Splitting**: Lazy loading for better initial load
- **Bundle Optimization**: Tree shaking and minification
- **Image Optimization**: Responsive images and lazy loading
- **Caching Strategy**: Efficient caching for API responses
- **Performance Monitoring**: Built-in performance metrics

### Performance Budgets
- **JavaScript Bundle**: < 100KB gzipped
- **Initial Load**: < 3 seconds on 3G
- **Interaction**: < 100ms response time
- **Accessibility**: 100% WCAG compliance

## 🔄 Development Workflow

### Code Quality
- **TypeScript**: Full type safety
- **ESLint**: Code linting and formatting
- **Prettier**: Code formatting
- **Husky**: Git hooks for pre-commit checks

### Testing Strategy
1. **Unit Tests**: Test individual components and functions
2. **Integration Tests**: Test component interactions
3. **E2E Tests**: Test complete user workflows
4. **Accessibility Tests**: Ensure WCAG compliance
5. **Performance Tests**: Validate performance budgets

### Git Workflow
- **Feature Branches**: Develop features in isolation
- **Pull Requests**: Code review and automated testing
- **Semantic Versioning**: Consistent version management
- **Release Notes**: Detailed changelog for each release

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the existing code style and conventions
- Write tests for new features and bug fixes
- Ensure all tests pass before submitting
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- **Documentation**: Check the `docs/` directory
- **Issues**: Open an issue on GitHub
- **Discussions**: Join the GitHub Discussions
- **Email**: Contact the development team

## 🗺️ Roadmap

### Upcoming Features
- [ ] Real-time collaboration with WebSockets
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)
- [ ] Offline functionality with service workers
- [ ] Integration with third-party production tools
- [ ] Advanced reporting and export features

### Technical Improvements
- [ ] Micro-frontend architecture
- [ ] Advanced caching strategies
- [ ] Performance monitoring and alerting
- [ ] Enhanced security features
- [ ] Internationalization support