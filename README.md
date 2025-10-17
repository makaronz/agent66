# Film Industry Time Tracking System

A comprehensive time tracking solution designed specifically for the film and television industry, enabling crew members to track hours, manage projects, and generate reports from any device.

## 🎬 Features

- **Time Clock Interface**: Easy clock-in/clock-out with GPS location tracking
- **Project Management**: Create and manage film productions with phases and crew assignments
- **Crew Management**: Role-based access control for different film industry positions
- **Real-time Dashboard**: Overview of active projects, crew status, and time tracking
- **Reporting & Analytics**: Comprehensive reports on time, costs, and project progress
- **Mobile Optimized**: Responsive design perfect for on-set use
- **Offline Support**: Continue tracking time even without internet connection
- **Automatic Overtime**: Calculates overtime at 1.5x rate after 8 hours daily

## 🏗️ Architecture

### Backend
- **Location**: `/backend`
- **Stack**: Node.js + Express + TypeScript + Prisma + PostgreSQL
- **Port**: 5000
- **Features**:
  - JWT Authentication with role-based access
  - RESTful API with Zod validation
  - Film industry specific data models
  - GPS location tracking
  - Automatic overtime calculation
  - PDF report generation

### Frontend
- **Location**: `/frontend`
- **Stack**: React 18 + TypeScript + React Query + Tailwind CSS
- **Port**: 3000
- **Features**:
  - Modern UI optimized for mobile devices
  - Real-time updates with WebSocket support
  - Offline data persistence
  - Interactive charts and reports
  - Responsive design for on-set use

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL 14+
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agent66
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.template .env
   # Edit .env with your database credentials and JWT secret
   ```

4. **Set up the database**
   ```bash
   npm run db:push
   npm run db:generate
   ```

5. **Start the development servers**
   ```bash
   # Start backend (port 5000)
   npm run dev:backend

   # Start frontend (port 3000) - in a new terminal
   npm run dev:frontend
   ```

6. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - Database Studio: `npm run db:studio`

---

## 📖 API Documentation

### Main Endpoints
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `POST /api/time-entries/clock` - Clock in/out
- `GET /api/time-entries/active/:userId` - Get active time entry
- `GET /api/crew` - List all crew members
- `GET /api/reports/time-summary` - Generate time summary report

---

## 👥 User Roles

The system supports film industry specific roles:

- **ADMIN**: Full system access and user management
- **SUPERVISOR**: Project oversight and crew management
- **SUPERVISOR_USER**: Limited supervisory access
- **CREW**: Time tracking and project participation
- **CLIENT**: View-only access to project progress
- **GUEST**: Limited access to specific projects

## 🎭 Project Types

Support for various film production types:

- **FEATURE**: Full-length feature films
- **SHORT**: Short films
- **DOCUMENTARY**: Documentary productions
- **COMMERCIAL**: Commercial advertisements
- **MUSIC_VIDEO**: Music video productions
- **TV_EPISODE**: Television episodes
- **WEB_SERIES**: Web series content
- **CORPORATE**: Corporate videos
- **OTHER**: Other production types

---

## 🔧 Development

### Backend Development
```bash
cd backend
npm run dev    # Start with tsx watch
npm run build  # Build TypeScript
npm test       # Run tests
```

### Frontend Development
```bash
cd frontend
npm start      # Development server
npm run build  # Production build
npm test       # Run tests
```

### Database Management
```bash
npm run db:generate    # Generate Prisma client
npm run db:push        # Push schema to database
npm run db:migrate     # Run migrations
npm run db:studio      # Open Prisma Studio
```

---

## 📁 Project Structure

```
agent66/
├── backend/          # Express API server
│   └── src/
│       ├── database/ # Database connection and models
│       ├── routes/   # API routes
│       ├── middleware/ # Auth and error handling
│       ├── utils/    # Utility functions
│       └── server.ts # Express server setup
├── frontend/         # React application
│   └── src/
│       ├── components/ # React components
│       ├── pages/     # Page components
│       ├── store/     # Redux store
│       ├── types/     # TypeScript types
│       └── utils/     # Utility functions
├── prisma/           # Database schema and migrations
└── docs/             # Documentation
```

---

## 🌍 Environment Variables

### Backend (.env)
```
DATABASE_URL="postgresql://username:password@localhost:5432/film_time_tracker"
JWT_SECRET="your-super-secret-jwt-key"
JWT_EXPIRES_IN="7d"
PORT=5000
NODE_ENV="development"
```

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:5000/api
```

---

## 📱 Mobile Features

### On-Set Optimization

- **Large Touch Targets**: Easy clock-in/out with gloves
- **High Contrast**: Visible in bright outdoor conditions
- **Quick Actions**: One-tap time tracking
- **Offline Mode**: Continue working without internet
- **GPS Integration**: Automatic location tracking
- **Real-time Updates**: Live time tracking display

### Offline Support

- Automatic data synchronization when connection restored
- Local storage for time entries
- Queue operations for later sync
- Conflict resolution for overlapping entries

---

## 📊 Reports

### Available Reports

- **Time Summary**: Hours worked by user, project, or date range
- **Cost Analysis**: Labor costs and overtime analysis
- **Project Progress**: Time tracking against project phases
- **Payroll**: Detailed payroll reports with calculations

### Export Options

- PDF reports with company branding
- CSV data export for spreadsheet analysis
- Email reports directly to stakeholders
- Scheduled report generation

---

## 🧪 Testing

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run backend tests
npm run test:backend

# Run frontend tests
npm run test:frontend
```

---

## 📦 Deployment

### Production Build

1. **Build the frontend**
   ```bash
   npm run build:frontend
   ```

2. **Set up production database**
   ```bash
   npm run db:migrate
   ```

3. **Start production server**
   ```bash
   npm run start
   ```

### Docker Deployment

```dockerfile
# Dockerfile example
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build
RUN npm run db:generate

EXPOSE 5000
CMD ["npm", "start"]
```

---

## 🎬 Film Industry Specific Features

### Production Phases

- **PLANNING**: Pre-production planning
- **PRE_PRODUCTION**: Pre-production work
- **PRODUCTION**: Principal photography
- **POST_PRODUCTION**: Post-production work
- **COMPLETED**: Project finished

### Time Tracking Features

- **Automatic Overtime**: 1.5x rate after 8 hours daily
- **GPS Location Tracking**: Verify on-set presence
- **Break Duration Tracking**: Automatic break time calculation
- **Multi-project Support**: Work on multiple productions
- **Approval Workflow**: Supervisor approval for time entries

### Reporting for Film Production

- **Department-wise Cost Analysis**: Track costs by production department
- **Crew Performance Reports**: Individual and team productivity
- **Project Budget vs Actual**: Compare planned vs actual time costs
- **Union Compliance**: Ensure compliance with union regulations

---

## 📚 Legacy Code

Previous trading system has been archived to `/app_old` folder.
See `app_old/README.md` for legacy system documentation.

**Migration Date**: October 15, 2025
**Film Time Tracker Launch**: v1.0.0

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🔗 Links

- [Backend README](./backend/README.md)
- [Frontend README](./frontend/README.md)
- [Prisma Schema](./prisma/schema.prisma)

---

**Last Updated**: October 15, 2025