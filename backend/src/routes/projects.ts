import { Router, Request, Response } from 'express';
import { getPrismaClient } from '../database/connection';
import { CreateProjectSchema, UpdateProjectSchema } from '../models/Project';
import { logger } from '../utils/logger';
import { validateRequest } from '../middleware/validation';

const router = Router();
const prisma = getPrismaClient();

// Get all projects with filtering and pagination
router.get('/', async (req: Request, res: Response) => {
  try {
    const {
      page = 1,
      limit = 20,
      status,
      type,
      search,
      sortBy = 'createdAt',
      sortOrder = 'desc',
    } = req.query;

    const skip = (Number(page) - 1) * Number(limit);
    const where: any = {};

    if (status) where.status = status;
    if (type) where.type = type;
    if (search) {
      where.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { description: { contains: search, mode: 'insensitive' } },
        { location: { contains: search, mode: 'insensitive' } },
      ];
    }

    const [projects, total] = await Promise.all([
      prisma.project.findMany({
        where,
        skip,
        take: Number(limit),
        orderBy: { [sortBy as string]: sortOrder as 'asc' | 'desc' },
        include: {
          creator: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              email: true,
            },
          },
          _count: {
            select: {
              members: true,
              timeEntries: true,
            },
          },
        },
      }),
      prisma.project.count({ where }),
    ]);

    res.json({
      projects,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total,
        pages: Math.ceil(total / Number(limit)),
      },
    });
  } catch (error) {
    logger.error('Error fetching projects:', error);
    res.status(500).json({ error: 'Failed to fetch projects' });
  }
});

// Get single project by ID
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const project = await prisma.project.findUnique({
      where: { id },
      include: {
        creator: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
            email: true,
          },
        },
        members: {
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
          },
        },
        phases: {
          orderBy: { startDate: 'asc' },
        },
        timeEntries: {
          include: {
            user: {
              select: {
                id: true,
                firstName: true,
                lastName: true,
              },
            },
          },
          orderBy: { date: 'desc' },
          take: 50,
        },
      },
    });

    if (!project) {
      return res.status(404).json({ error: 'Project not found' });
    }

    res.json(project);
  } catch (error) {
    logger.error('Error fetching project:', error);
    res.status(500).json({ error: 'Failed to fetch project' });
  }
});

// Create new project
router.post('/', validateRequest(CreateProjectSchema), async (req: Request, res: Response) => {
  try {
    const projectData = CreateProjectSchema.parse(req.body);

    const project = await prisma.project.create({
      data: projectData,
      include: {
        creator: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
            email: true,
          },
        },
      },
    });

    logger.info(`Project created: ${project.id} by user: ${project.createdBy}`);
    res.status(201).json(project);
  } catch (error) {
    logger.error('Error creating project:', error);
    res.status(500).json({ error: 'Failed to create project' });
  }
});

// Update project
router.put('/:id', validateRequest(UpdateProjectSchema), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const updateData = UpdateProjectSchema.parse(req.body);

    const project = await prisma.project.update({
      where: { id },
      data: updateData,
      include: {
        creator: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
            email: true,
          },
        },
      },
    });

    logger.info(`Project updated: ${project.id}`);
    res.json(project);
  } catch (error) {
    logger.error('Error updating project:', error);
    res.status(500).json({ error: 'Failed to update project' });
  }
});

// Delete project
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    await prisma.project.delete({
      where: { id },
    });

    logger.info(`Project deleted: ${id}`);
    res.status(204).send();
  } catch (error) {
    logger.error('Error deleting project:', error);
    res.status(500).json({ error: 'Failed to delete project' });
  }
});

// Add crew member to project
router.post('/:id/members', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { userId, role, department, rate, overtimeRate } = req.body;

    const existingMember = await prisma.projectMember.findUnique({
      where: {
        projectId_userId: {
          projectId: id,
          userId,
        },
      },
    });

    if (existingMember) {
      return res.status(400).json({ error: 'User is already a member of this project' });
    }

    const member = await prisma.projectMember.create({
      data: {
        projectId: id,
        userId,
        role,
        department,
        rate,
        overtimeRate,
      },
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
      },
    });

    logger.info(`Crew member added to project: ${userId} to ${id}`);
    res.status(201).json(member);
  } catch (error) {
    logger.error('Error adding crew member:', error);
    res.status(500).json({ error: 'Failed to add crew member' });
  }
});

// Remove crew member from project
router.delete('/:id/members/:memberId', async (req: Request, res: Response) => {
  try {
    const { id, memberId } = req.params;

    await prisma.projectMember.delete({
      where: { id: memberId },
    });

    logger.info(`Crew member removed from project: ${memberId} from ${id}`);
    res.status(204).send();
  } catch (error) {
    logger.error('Error removing crew member:', error);
    res.status(500).json({ error: 'Failed to remove crew member' });
  }
});

// Get project statistics
router.get('/:id/stats', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const [
      totalMembers,
      activeMembers,
      totalHours,
      totalCost,
      phasesCount,
      activePhases,
    ] = await Promise.all([
      prisma.projectMember.count({ where: { projectId: id } }),
      prisma.projectMember.count({ where: { projectId: id, isActive: true } }),
      prisma.timeEntry.aggregate({
        where: { projectId: id, status: 'APPROVED' },
        _sum: { totalHours: true },
      }),
      prisma.timeEntry.aggregate({
        where: { projectId: id, status: 'APPROVED' },
        _sum: { totalPay: true },
      }),
      prisma.productionPhase.count({ where: { projectId: id } }),
      prisma.productionPhase.count({ where: { projectId: id, status: 'ACTIVE' } }),
    ]);

    res.json({
      members: {
        total: totalMembers,
        active: activeMembers,
      },
      hours: {
        total: totalHours._sum.totalHours || 0,
      },
      cost: {
        total: totalCost._sum.totalPay || 0,
      },
      phases: {
        total: phasesCount,
        active: activePhases,
      },
    });
  } catch (error) {
    logger.error('Error fetching project stats:', error);
    res.status(500).json({ error: 'Failed to fetch project statistics' });
  }
});

export default router;