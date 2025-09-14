import express, { Express, Request, Response, NextFunction } from 'express';
import dotenv from 'dotenv';
import cors from 'cors';
import helmet from 'helmet';
import mongoose from 'mongoose';
import authRoutes from './routes/auth';
import postRoutes from './routes/posts';
import weatherRoutes from './routes/weather';
import swaggerUi from 'swagger-ui-express';
import swaggerSpec from './config/swagger';

dotenv.config();

const app: Express = express();
const port = process.env.PORT || 5000;

// Middlewares
app.use(cors());
app.use(helmet());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database connection
const mongoUri = process.env.MONGO_URI;

if (!mongoUri) {
  console.error("FATAL ERROR: MONGO_URI is not defined.");
  process.exit(1);
}

mongoose.connect(mongoUri)
  .then(() => console.log("MongoDB connected successfully."))
  .catch(err => {
    console.error("MongoDB connection error:", err);
    process.exit(1);
  });

// Routes
app.get('/api', (req: Request, res: Response) => {
  res.send('Trading App API is running...');
});

app.use('/api/auth', authRoutes);
app.use('/api/posts', postRoutes);
app.use('/api/weather', weatherRoutes);

// Swagger Docs
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// Global Error Handler
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(err.stack);
  res.status(500).send('Something broke!');
});

app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});

export default app;