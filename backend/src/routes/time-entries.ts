import { Router, Request, Response } from 'express';
import { getPrismaClient } from '../database/connection';
import {
  CreateTimeEntrySchema,
  UpdateTimeEntrySchema,
  ClockInOutSchema
} from '../models/TimeEntry';
import { logger } from '../utils/logger';
import { validateRequest } from '../middleware/validation';

const router = Router();
const prisma = getPrismaClient();

// Get time entries with filtering
router.get('/', async (req: Request, res: Response) => {
  try {
    const {
      page = 1,
      limit = 50,
      userId,
      projectId,
      status,
      startDate,
      endDate,
      sortBy = 'date',
      sortOrder = 'desc',
    } = req.query;

    const skip = (Number(page) - 1) * Number(limit);
    const where: any = {};

    if (userId) where.userId = userId;
    if (projectId) where.projectId = projectId;
    if (status) where.status = status;

    if (startDate || endDate) {
      where.date = {};
      if (startDate) where.date.gte = new Date(startDate as string);
      if (endDate) where.date.lte = new Date(endDate as string);
    }

    const [timeEntries, total] = await Promise.all([
      prisma.timeEntry.findMany({
        where,
        skip,
        take: Number(limit),
        orderBy: { [sortBy as string]: sortOrder as 'asc' | 'desc' },
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              email: true,
            },
          },
          project: {
            select: {
              id: true,
              title: true,
              status: true,
            },
          },
          projectMember: {
            include: {
              user: {
                select: {
                  id: true,
                  firstName: true,
                  lastName: true,
                },
              },
            },
          },
          phase: {
            select: {
              id: true,
              name: true,
              status: true,
            },
          },
          approvals: {
            include: {
              approver: {
                select: {
                  id: true,
                  firstName: true,
                  lastName: true,
                },
              },
            },
          },
        },
      }),
      prisma.timeEntry.count({ where }),
    ]);

    res.json({
      timeEntries,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total,
        pages: Math.ceil(total / Number(limit)),
      },
    });
  } catch (error) {
    logger.error('Error fetching time entries:', error);
    res.status(500).json({ error: 'Failed to fetch time entries' });
  }
});

// Get single time entry
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const timeEntry = await prisma.timeEntry.findUnique({
      where: { id },
      include: {
        user: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
            email: true,
            role: true,
          },
        },
        project: {
          select: {
            id: true,
            title: true,
            status: true,
            type: true,
          },
        },
        projectMember: {
          include: {
            user: {
              select: {
                id: true,
                firstName: true,
                lastName: true,
              },
            },
          },
        },
        phase: {
          select: {
            id: true,
            name: true,
            status: true,
            startDate: true,
            endDate: true,
          },
        },
        approvals: {
          include: {
            approver: {
              select: {
                id: true,
                firstName: true,
                lastName: true,
                role: true,
              },
            },
          },
        },
        attachments: true,
      },
    });

    if (!timeEntry) {
      return res.status(404).json({ error: 'Time entry not found' });
    }

    res.json(timeEntry);
  } catch (error) {
    logger.error('Error fetching time entry:', error);
    res.status(500).json({ error: 'Failed to fetch time entry' });
  }
});

// Create time entry
router.post('/', validateRequest(CreateTimeEntrySchema), async (req: Request, res: Response) => {
  try {
    const entryData = CreateTimeEntrySchema.parse(req.body);

    // Calculate total hours if clockOut is provided
    if (entryData.clockOut) {
      const diffMs = entryData.clockOut.getTime() - entryData.clockIn.getTime();
      const totalMinutes = diffMs / (1000 * 60);
      const breakMinutes = entryData.breakDuration || 0;
      entryData.totalHours = Math.max(0, (totalMinutes - breakMinutes) / 60);

      // Calculate overtime (hours over 8 per day)
      entryData.overtimeHours = Math.max(0, entryData.totalHours - 8);

      // Calculate total pay if rate is provided
      if (entryData.rate) {
        const overtimeRate = entryData.rate * 1.5; // 1.5x for overtime
        const regularHours = Math.min(entryData.totalHours, 8);
        entryData.totalPay = (regularHours * entryData.rate) + (entryData.overtimeHours * overtimeRate);
      }
    }

    const timeEntry = await prisma.timeEntry.create({
      data: entryData,
      include: {
        user: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
            email: true,
          },
        },
        project: {
          select: {
            id: true,
            title: true,
          },
        },
      },
    });

    logger.info(`Time entry created: ${timeEntry.id} by user: ${timeEntry.userId}`);
    res.status(201).json(timeEntry);
  } catch (error) {
    logger.error('Error creating time entry:', error);
    res.status(500).json({ error: 'Failed to create time entry' });
  }
});

// Clock in/out functionality
router.post('/clock', validateRequest(ClockInOutSchema), async (req: Request, res: Response) => {
  try {
    const { userId, projectId, clockIn, clockOut, breakDuration = 0, notes, location } = req.body;

    // Check if there's an active clock-in without clock-out
    const activeEntry = await prisma.timeEntry.findFirst({
      where: {
        userId,
        projectId,
        clockOut: null,
        status: 'DRAFT',
      },
      orderBy: { clockIn: 'desc' },
    });

    if (clockOut && activeEntry) {
      // Clock out existing entry
      const diffMs = new Date(clockOut).getTime() - activeEntry.clockIn.getTime();
      const totalMinutes = diffMs / (1000 * 60);
      const totalHours = Math.max(0, (totalMinutes - breakDuration) / 60);
      const overtimeHours = Math.max(0, totalHours - 8);

      const updatedEntry = await prisma.timeEntry.update({
        where: { id: activeEntry.id },
        data: {
          clockOut: new Date(clockOut),
          breakDuration,
          totalHours,
          overtimeHours,
          notes,
          location,
          status: 'SUBMITTED',
        },
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
            },
          },
          project: {
            select: {
              id: true,
              title: true,
            },
          },
        },
      });

      logger.info(`User ${userId} clocked out from project ${projectId}`);
      res.json(updatedEntry);
    } else if (clockIn && !activeEntry) {
      // Clock in new entry
      const newEntry = await prisma.timeEntry.create({
        data: {
          userId,
          projectId,
          date: new Date(clockIn),
          clockIn: new Date(clockIn),
          notes,
          location,
          status: 'DRAFT',
        },
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
            },
          },
          project: {
            select: {
              id: true,
              title: true,
            },
          },
        },
      });

      logger.info(`User ${userId} clocked in to project ${projectId}`);
      res.status(201).json(newEntry);
    } else {
      res.status(400).json({
        error: activeEntry ? 'Already clocked in. Please clock out first.' : 'Invalid clock operation.'
      });
    }
  } catch (error) {
    logger.error('Error clock operation:', error);
    res.status(500).json({ error: 'Failed to process clock operation' });
  }
});

// Update time entry
router.put('/:id', validateRequest(UpdateTimeEntrySchema), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const updateData = UpdateTimeEntrySchema.parse(req.body);

    // Recalculate hours and pay if clock times are updated
    if (updateData.clockIn || updateData.clockOut) {
      const currentEntry = await prisma.timeEntry.findUnique({ where: { id } });
      if (currentEntry && updateData.clockOut) {
        const clockIn = updateData.clockIn || currentEntry.clockIn;
        const clockOut = updateData.clockOut;

        const diffMs = clockOut.getTime() - clockIn.getTime();
        const totalMinutes = diffMs / (1000 * 60);
        const breakMinutes = updateData.breakDuration || currentEntry.breakDuration || 0;
        updateData.totalHours = Math.max(0, (totalMinutes - breakMinutes) / 60);
        updateData.overtimeHours = Math.max(0, updateData.totalHours - 8);

        // Recalculate pay if rate is available
        const rate = updateData.rate || currentEntry.rate;
        if (rate) {
          const overtimeRate = rate * 1.5;
          const regularHours = Math.min(updateData.totalHours, 8);
          updateData.totalPay = (regularHours * rate) + (updateData.overtimeHours * overtimeRate);
        }
      }
    }

    const timeEntry = await prisma.timeEntry.update({
      where: { id },
      data: updateData,
      include: {
        user: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
          },
        },
        project: {
          select: {
            id: true,
            title: true,
          },
        },
      },
    });

    logger.info(`Time entry updated: ${timeEntry.id}`);
    res.json(timeEntry);
  } catch (error) {
    logger.error('Error updating time entry:', error);
    res.status(500).json({ error: 'Failed to update time entry' });
  }
});

// Submit time entry for approval
router.post('/:id/submit', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const timeEntry = await prisma.timeEntry.update({
      where: { id },
      data: { status: 'SUBMITTED' },
      include: {
        user: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
          },
        },
        project: {
          select: {
            id: true,
            title: true,
          },
        },
      },
    });

    logger.info(`Time entry submitted for approval: ${timeEntry.id}`);
    res.json(timeEntry);
  } catch (error) {
    logger.error('Error submitting time entry:', error);
    res.status(500).json({ error: 'Failed to submit time entry' });
  }
});

// Approve/reject time entry
router.post('/:id/approve', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { status, notes } = req.body; // status: 'APPROVED' or 'REJECTED'
    const approvedBy = req.user?.id; // Assuming user is attached to request by auth middleware

    if (!['APPROVED', 'REJECTED'].includes(status)) {
      return res.status(400).json({ error: 'Invalid approval status' });
    }

    const [timeEntry] = await prisma.$transaction([
      prisma.timeEntry.update({
        where: { id },
        data: { status },
      }),
      prisma.timeEntryApproval.create({
        data: {
          timeEntryId: id,
          approvedBy,
          status,
          notes,
        },
      }),
    ]);

    logger.info(`Time entry ${status.toLowerCase()}: ${timeEntry.id} by ${approvedBy}`);
    res.json(timeEntry);
  } catch (error) {
    logger.error('Error approving time entry:', error);
    res.status(500).json({ error: 'Failed to approve time entry' });
  }
});

// Delete time entry
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    await prisma.timeEntry.delete({
      where: { id },
    });

    logger.info(`Time entry deleted: ${id}`);
    res.status(204).send();
  } catch (error) {
    logger.error('Error deleting time entry:', error);
    res.status(500).json({ error: 'Failed to delete time entry' });
  }
});

// Get user's active time entry (clocked in but not out)
router.get('/active/:userId', async (req: Request, res: Response) => {
  try {
    const { userId } = req.params;

    const activeEntry = await prisma.timeEntry.findFirst({
      where: {
        userId,
        clockOut: null,
        status: 'DRAFT',
      },
      include: {
        project: {
          select: {
            id: true,
            title: true,
            location: true,
          },
        },
      },
      orderBy: { clockIn: 'desc' },
    });

    res.json({ activeEntry });
  } catch (error) {
    logger.error('Error fetching active time entry:', error);
    res.status(500).json({ error: 'Failed to fetch active time entry' });
  }
});

export default router;