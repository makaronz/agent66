import { Router, Request, Response } from 'express';
import { getPrismaClient } from '../database/connection';
import { logger } from '../utils/logger';

const router = Router();
const prisma = getPrismaClient();

// Get all crew members with filtering
router.get('/', async (req: Request, res: Response) => {
  try {
    const {
      page = 1,
      limit = 20,
      role,
      department,
      search,
      projectId,
      isActive,
      sortBy = 'firstName',
      sortOrder = 'asc',
    } = req.query;

    const skip = (Number(page) - 1) * Number(limit);
    const where: any = {};

    if (role) where.role = { contains: role, mode: 'insensitive' };
    if (department) where.department = { contains: department, mode: 'insensitive' };
    if (typeof isActive === 'string') where.isActive = isActive === 'true';

    if (search) {
      where.OR = [
        { firstName: { contains: search, mode: 'insensitive' } },
        { lastName: { contains: search, mode: 'insensitive' } },
        { email: { contains: search, mode: 'insensitive' } },
        { phone: { contains: search, mode: 'insensitive' } },
      ];
    }

    const [users, total] = await Promise.all([
      prisma.user.findMany({
        where,
        skip,
        take: Number(limit),
        orderBy: { [sortBy as string]: sortOrder as 'asc' | 'desc' },
        select: {
          id: true,
          firstName: true,
          lastName: true,
          email: true,
          role: true,
          department: true,
          phone: true,
          avatar: true,
          createdAt: true,
        },
      }),
      prisma.user.count({ where }),
    ]);

    res.json({
      users,
      pagination: {
        page: Number(page),
        limit: Number(limit),
        total,
        pages: Math.ceil(total / Number(limit)),
      },
    });
  } catch (error) {
    logger.error('Error fetching crew members:', error);
    res.status(500).json({ error: 'Failed to fetch crew members' });
  }
});

// Get crew member by ID with their project assignments
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const user = await prisma.user.findUnique({
      where: { id },
      include: {
        projectMembers: {
          include: {
            project: {
              select: {
                id: true,
                title: true,
                status: true,
                type: true,
                startDate: true,
                endDate: true,
              },
            },
          },
          orderBy: { joinedAt: 'desc' },
        },
        timeEntries: {
          include: {
            project: {
              select: {
                id: true,
                title: true,
              },
            },
          },
          orderBy: { date: 'desc' },
          take: 50,
        },
        _count: {
          select: {
            projectMembers: true,
            timeEntries: true,
          },
        },
      },
    });

    if (!user) {
      return res.status(404).json({ error: 'Crew member not found' });
    }

    res.json(user);
  } catch (error) {
    logger.error('Error fetching crew member:', error);
    res.status(500).json({ error: 'Failed to fetch crew member' });
  }
});

// Get crew member's time summary
router.get('/:id/summary', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { startDate, endDate, projectId } = req.query;

    const where: any = { userId: id };

    if (startDate || endDate) {
      where.date = {};
      if (startDate) where.date.gte = new Date(startDate as string);
      if (endDate) where.date.lte = new Date(endDate as string);
    }

    if (projectId) where.projectId = projectId;

    const [
      totalEntries,
      approvedEntries,
      totalHours,
      overtimeHours,
      totalPay,
      projectsWorked,
    ] = await Promise.all([
      prisma.timeEntry.count({ where }),
      prisma.timeEntry.count({ where: { ...where, status: 'APPROVED' } }),
      prisma.timeEntry.aggregate({
        where: { ...where, status: 'APPROVED' },
        _sum: { totalHours: true },
      }),
      prisma.timeEntry.aggregate({
        where: { ...where, status: 'APPROVED' },
        _sum: { overtimeHours: true },
      }),
      prisma.timeEntry.aggregate({
        where: { ...where, status: 'APPROVED' },
        _sum: { totalPay: true },
      }),
      prisma.timeEntry.groupBy({
        by: ['projectId'],
        where: { ...where, status: 'APPROVED' },
      }),
    ]);

    const projectIds = projectsWorked.map(p => p.projectId);
    const projects = await prisma.project.findMany({
      where: { id: { in: projectIds } },
      select: { id: true, title: true, status: true },
    });

    res.json({
      entries: {
        total: totalEntries,
        approved: approvedEntries,
      },
      hours: {
        total: totalHours._sum.totalHours || 0,
        overtime: overtimeHours._sum.overtimeHours || 0,
      },
      pay: {
        total: totalPay._sum.totalPay || 0,
      },
      projects: projects,
    });
  } catch (error) {
    logger.error('Error fetching crew member summary:', error);
    res.status(500).json({ error: 'Failed to fetch crew member summary' });
  }
});

// Get available crew for project (not already assigned)
router.get('/available/:projectId', async (req: Request, res: Response) => {
  try {
    const { projectId } = req.params;
    const { role, department } = req.query;

    // Get existing project member IDs
    const existingMembers = await prisma.projectMember.findMany({
      where: { projectId },
      select: { userId: true },
    });
    const existingUserIds = existingMembers.map(m => m.userId);

    const where: any = {
      id: { notIn: existingUserIds },
      role: { not: 'CLIENT' }, // Exclude clients from available crew
    };

    if (role) where.OR = [
      { role: { contains: role, mode: 'insensitive' } },
      { department: { contains: role, mode: 'insensitive' } },
    ];

    if (department) where.department = { contains: department, mode: 'insensitive' };

    const availableCrew = await prisma.user.findMany({
      where,
      select: {
        id: true,
        firstName: true,
        lastName: true,
        email: true,
        role: true,
        department: true,
        phone: true,
        avatar: true,
      },
      orderBy: { firstName: 'asc' },
    });

    res.json(availableCrew);
  } catch (error) {
    logger.error('Error fetching available crew:', error);
    res.status(500).json({ error: 'Failed to fetch available crew' });
  }
});

// Get crew statistics
router.get('/stats/dashboard', async (req: Request, res: Response) => {
  try {
    const [
      totalCrew,
      crewByRole,
      crewByDepartment,
      activeProjects,
      recentActivity,
    ] = await Promise.all([
      prisma.user.count({
        where: { role: { not: 'CLIENT' } }
      }),
      prisma.user.groupBy({
        by: ['role'],
        where: { role: { not: 'CLIENT' } },
        _count: { role: true },
      }),
      prisma.user.groupBy({
        by: ['department'],
        where: {
          role: { not: 'CLIENT' },
          department: { not: null }
        },
        _count: { department: true },
      }),
      prisma.project.count({
        where: { status: 'PRODUCTION' }
      }),
      prisma.timeEntry.findMany({
        take: 10,
        orderBy: { createdAt: 'desc' },
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
      }),
    ]);

    res.json({
      crew: {
        total: totalCrew,
        byRole: crewByRole,
        byDepartment: crewByDepartment,
      },
      projects: {
        active: activeProjects,
      },
      recentActivity,
    });
  } catch (error) {
    logger.error('Error fetching crew stats:', error);
    res.status(500).json({ error: 'Failed to fetch crew statistics' });
  }
});

// Update crew member role or department
router.patch('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { role, department, phone } = req.body;

    const updateData: any = {};
    if (role) updateData.role = role;
    if (department) updateData.department = department;
    if (phone) updateData.phone = phone;

    const user = await prisma.user.update({
      where: { id },
      data: updateData,
      select: {
        id: true,
        firstName: true,
        lastName: true,
        email: true,
        role: true,
        department: true,
        phone: true,
        avatar: true,
      },
    });

    logger.info(`Crew member updated: ${user.id}`);
    res.json(user);
  } catch (error) {
    logger.error('Error updating crew member:', error);
    res.status(500).json({ error: 'Failed to update crew member' });
  }
});

export default router;