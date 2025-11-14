import express, { Request, Response, NextFunction } from 'express';
import axios from 'axios';
import { z } from 'zod';
import { validateRequest } from '../middleware/validation';
import { authGuard } from '../middleware/auth';

const router = express.Router();

const weatherSchema = z.object({
  query: z.object({
    city: z.string().min(1),
  }),
});

/**
 * @swagger
 * /weather:
 *   get:
 *     summary: Get weather for a city
 *     tags: [Weather]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: query
 *         name: city
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Weather data
 *       401:
 *         description: Unauthorized
 *       500:
 *         description: Server error
 */
router.get('/', authGuard, validateRequest(weatherSchema), async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { city } = req.query;
    const apiKey = process.env.OPENWEATHERMAP_API_KEY;

    if (!apiKey) {
      return res.status(500).json({ message: 'OpenWeatherMap API key is not configured' });
    }

    const url = `https://api.openweathermap.org/data/2.5/weather?q=${city}&appid=${apiKey}&units=metric`;

    const response = await axios.get(url);

    res.json(response.data);
  } catch (error: any) {
    if (error.response) {
      return res.status(error.response.status).json({ message: error.response.data.message });
    }
    next(error);
  }
});

export default router;