# Trading App v2

Modern full-stack trading application with real-time market data, user authentication, and MongoDB persistence.

## 🏗️ Architecture

### Backend
- **Location:** `/backend`
- **Stack:** Node.js + Express + TypeScript + MongoDB
- **Port:** 5001
- **Features:**
  - JWT Authentication
  - RESTful API
  - Swagger Documentation (`/api-docs`)
  - Weather integration (OpenWeatherMap)
  - MongoDB with Mongoose ODM

### Frontend  
- **Location:** `/frontend`
- **Stack:** React 18 + Redux Toolkit + TypeScript
- **Port:** 3000
- **Features:**
  - Modern UI with Tailwind CSS
  - Redux state management
  - Protected routes
  - Form validation with Zod
  - React Hook Form

---

## 🚀 Quick Start

### Prerequisites
- Node.js 22.x
- MongoDB 8.x running locally
- npm or pnpm

### Backend Setup
```bash
cd backend
npm install
cp .env.example .env
# Edit .env with your configuration
npm run dev  # Starts on http://localhost:5001
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with backend API URL
npm start  # Starts on http://localhost:3000
```

---

## 📖 API Documentation

Once backend is running, visit:
- **Swagger UI:** http://localhost:5001/api-docs
- **API Base:** http://localhost:5001/api

### Main Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/posts` - Get all posts
- `POST /api/posts` - Create post (requires auth)
- `GET /api/weather?city=Warsaw` - Get weather (requires auth)

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

---

## 📁 Project Structure

```
/
├── backend/          # Express API server
│   ├── src/
│   │   ├── server.ts
│   │   ├── routes/   # API routes
│   │   ├── models/   # Mongoose models
│   │   ├── middleware/
│   │   └── config/
│   └── package.json
│
├── frontend/         # React application
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── store/    # Redux store
│   │   └── ...
│   └── package.json
│
└── app_old/          # Legacy trading system (archived)
    ├── Python trading system
    ├── Rust execution engine
    └── ... (archived code)
```

---

## 🌍 Environment Variables

### Backend (.env)
```
PORT=5001
NODE_ENV=development
MONGO_URI=mongodb://localhost:27017/trading-app
JWT_SECRET=your-secret-key
JWT_EXPIRES_IN=1d
OPENWEATHERMAP_API_KEY=optional
```

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:5001/api
```

---

## 🔐 Security

- JWT-based authentication
- bcrypt password hashing
- Helmet.js security headers
- CORS configuration
- Zod input validation
- Rate limiting on API endpoints

---

## 🧪 Testing

```bash
# Backend tests
cd backend && npm test

# Frontend tests
cd frontend && npm test
```

---

## 📦 Deployment

### Backend
- **Platform:** Heroku, AWS, or similar
- **Database:** MongoDB Atlas (production)
- **Env:** Configure production environment variables

### Frontend
- **Platform:** Vercel, Netlify
- **Build:** `npm run build` creates optimized production build
- **API URL:** Update `REACT_APP_API_URL` to production backend

---

## 📚 Legacy Code

Previous Python/Rust trading system has been archived to `/app_old` folder.  
See `app_old/README.md` for legacy system documentation.

**Migration Date:** October 3, 2025  
**Backup Location:** `../agent66_backup_20251003_133207`

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 License

This project is proprietary and confidential.

---

## 🔗 Links

- [Backend README](./backend/README.md)
- [Frontend README](./frontend/README.md)
- [Migration Plan](./MIGRATION_PLAN_APP_V2.md)
- [Backup Location](../agent66_backup_20251003_133207)

---

**Last Updated:** October 3, 2025
