import { Router, Request, Response } from 'express';
import { getPrismaClient } from '../database/connection';
import { logger } from '../utils/logger';
import { format, startOfMonth, endOfMonth, subMonths } from 'date-fns';

const router = Router();
const prisma = getPrismaClient();

// Generate time summary report
router.get('/time-summary', async (req: Request, res: Response) => {
  try {
    const {
      startDate,
      endDate,
      projectId,
      userId,
      groupBy = 'day', // day, week, month, user, project
    } = req.query;

    const where: any = {
      status: 'APPROVED',
    };

    if (startDate || endDate) {
      where.date = {};
      if (startDate) where.date.gte = new Date(startDate as string);
      if (endDate) where.date.lte = new Date(endDate as string);
    }

    if (projectId) where.projectId = projectId;
    if (userId) where.userId = userId;

    let groupByField = 'date';
    if (groupBy === 'week') {
      groupByField = prisma.$queryRaw`DATE_TRUNC('week', date)::date`.toString();
    } else if (groupBy === 'month') {
      groupByField = prisma.$queryRaw`DATE_TRUNC('month', date)::date`.toString();
    } else if (groupBy === 'user') {
      groupByField = 'userId';
    } else if (groupBy === 'project') {
      groupByField = 'projectId';
    }

    const summary = await prisma.timeEntry.groupBy({
      by: [groupByField as any],
      where,
      _sum: {
        totalHours: true,
        overtimeHours: true,
        totalPay: true,
      },
      _count: {
        id: true,
      },
    });

    // Get additional details for joined data
    const detailedSummary = await Promise.all(
      summary.map(async (item) => {
        let details = {};

        if (groupBy === 'user') {
          const user = await prisma.user.findUnique({
            where: { id: item[groupByField as string] },
            select: { id: true, firstName: true, lastName: true, email: true },
          });
          details = { user };
        } else if (groupBy === 'project') {
          const project = await prisma.project.findUnique({
            where: { id: item[groupByField as string] },
            select: { id: true, title: true, status: true },
          });
          details = { project };
        }

        return {
          ...item,
          ...details,
        };
      })
    );

    const totals = summary.reduce(
      (acc, item) => ({
        totalHours: acc.totalHours + (item._sum.totalHours || 0),
        overtimeHours: acc.overtimeHours + (item._sum.overtimeHours || 0),
        totalPay: acc.totalPay + (item._sum.totalPay || 0),
        totalEntries: acc.totalEntries + item._count.id,
      }),
      { totalHours: 0, overtimeHours: 0, totalPay: 0, totalEntries: 0 }
    );

    res.json({
      summary: detailedSummary,
      totals,
      filters: { startDate, endDate, projectId, userId, groupBy },
    });
  } catch (error) {
    logger.error('Error generating time summary report:', error);
    res.status(500).json({ error: 'Failed to generate time summary report' });
  }
});

// Generate cost analysis report
router.get('/cost-analysis', async (req: Request, res: Response) => {
  try {
    const {
      startDate,
      endDate,
      projectId,
    } = req.query;

    const where: any = {
      status: 'APPROVED',
    };

    if (startDate || endDate) {
      where.date = {};
      if (startDate) where.date.gte = new Date(startDate as string);
      if (endDate) where.date.lte = new Date(endDate as string);
    }

    if (projectId) where.projectId = projectId;

    const [
      totalCost,
      costByDepartment,
      costByRole,
      costByProject,
      overtimeCost,
    ] = await Promise.all([
      prisma.timeEntry.aggregate({
        where,
        _sum: { totalPay: true },
        _count: { id: true },
      }),
      prisma.timeEntry.groupBy({
        by: ['userId'],
        where,
        _sum: { totalPay: true },
      }).then(async (results) => {
        const users = await prisma.user.findMany({
          where: { id: { in: results.map(r => r.userId) } },
          select: { id: true, department: true, role: true },
        });

        const deptCost: { [key: string]: number } = {};
        const roleCost: { [key: string]: number } = {};

        results.forEach(result => {
          const user = users.find(u => u.id === result.userId);
          const cost = result._sum.totalPay || 0;

          if (user?.department) {
            deptCost[user.department] = (deptCost[user.department] || 0) + cost;
          }
          if (user?.role) {
            roleCost[user.role] = (roleCost[user.role] || 0) + cost;
          }
        });

        return { byDepartment: deptCost, byRole: roleCost };
      }),
      prisma.timeEntry.groupBy({
        by: ['projectId'],
        where,
        _sum: { totalPay: true },
      }).then(async (results) => {
        const projects = await prisma.project.findMany({
          where: { id: { in: results.map(r => r.projectId) } },
          select: { id: true, title: true },
        });

        return results.map(result => ({
          projectId: result.projectId,
          projectTitle: projects.find(p => p.id === result.projectId)?.title,
          cost: result._sum.totalPay || 0,
        }));
      }),
      prisma.timeEntry.aggregate({
        where: {
          ...where,
          overtimeHours: { gt: 0 },
        },
        _sum: { totalPay: true, overtimeHours: true },
      }),
    ]);

    res.json({
      totalCost: totalCost._sum.totalPay || 0,
      totalEntries: totalCost._count.id,
      costByDepartment: costByDepartment.byDepartment,
      costByRole: costByDepartment.byRole,
      costByProject,
      overtimeCost: {
        total: overtimeCost._sum.totalPay || 0,
        hours: overtimeCost._sum.overtimeHours || 0,
      },
      filters: { startDate, endDate, projectId },
    });
  } catch (error) {
    logger.error('Error generating cost analysis report:', error);
    res.status(500).json({ error: 'Failed to generate cost analysis report' });
  }
});

// Generate project progress report
router.get('/project-progress/:projectId', async (req: Request, res: Response) => {
  try {
    const { projectId } = req.params;

    const [
      project,
      phases,
      members,
      timeStats,
      recentActivity,
    ] = await Promise.all([
      prisma.project.findUnique({
        where: { id: projectId },
        include: {
          _count: {
            select: {
              members: true,
              timeEntries: true,
            },
          },
        },
      }),
      prisma.productionPhase.findMany({
        where: { projectId },
        orderBy: { startDate: 'asc' },
      }),
      prisma.projectMember.findMany({
        where: { projectId, isActive: true },
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              role: true,
            },
          },
        },
      }),
      prisma.timeEntry.aggregate({
        where: { projectId, status: 'APPROVED' },
        _sum: { totalHours: true, totalPay: true },
        _count: { id: true },
      }),
      prisma.timeEntry.findMany({
        where: { projectId },
        orderBy: { date: 'desc' },
        take: 10,
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
            },
          },
        },
      }),
    ]);

    if (!project) {
      return res.status(404).json({ error: 'Project not found' });
    }

    const phaseProgress = phases.map(phase => {
      const totalPhases = phases.length;
      const completedPhases = phases.filter(p => p.status === 'COMPLETED').length;
      const activePhases = phases.filter(p => p.status === 'ACTIVE').length;

      return {
        ...phase,
        progress: totalPhases > 0 ? (completedPhases / totalPhases) * 100 : 0,
      };
    });

    res.json({
      project,
      phases: phaseProgress,
      members,
      timeStats: {
        totalHours: timeStats._sum.totalHours || 0,
        totalCost: timeStats._sum.totalPay || 0,
        totalEntries: timeStats._count.id,
      },
      recentActivity,
    });
  } catch (error) {
    logger.error('Error generating project progress report:', error);
    res.status(500).json({ error: 'Failed to generate project progress report' });
  }
});

// Generate payroll report
router.get('/payroll', async (req: Request, res: Response) => {
  try {
    const {
      startDate,
      endDate,
      projectId,
      status = 'APPROVED', // APPROVED or PROCESSED
    } = req.query;

    const where: any = {
      status: status as string,
    };

    if (startDate || endDate) {
      where.date = {};
      if (startDate) where.date.gte = new Date(startDate as string);
      if (endDate) where.date.lte = new Date(endDate as string);
    }

    if (projectId) where.projectId = projectId;

    const payrollData = await prisma.timeEntry.groupBy({
      by: ['userId'],
      where,
      _sum: {
        totalHours: true,
        overtimeHours: true,
        totalPay: true,
      },
      _count: { id: true },
    });

    const payrollWithUsers = await Promise.all(
      payrollData.map(async (item) => {
        const user = await prisma.user.findUnique({
          where: { id: item.userId },
          select: {
            id: true,
            firstName: true,
            lastName: true,
            email: true,
            role: true,
            department: true,
            phone: true,
          },
        });

        return {
          userId: item.userId,
          user,
          totalHours: item._sum.totalHours || 0,
          overtimeHours: item._sum.overtimeHours || 0,
          totalPay: item._sum.totalPay || 0,
          totalEntries: item._count.id,
        };
      })
    );

    const totals = payrollData.reduce(
      (acc, item) => ({
        totalHours: acc.totalHours + (item._sum.totalHours || 0),
        overtimeHours: acc.overtimeHours + (item._sum.overtimeHours || 0),
        totalPay: acc.totalPay + (item._sum.totalPay || 0),
        totalEntries: acc.totalEntries + item._count.id,
      }),
      { totalHours: 0, overtimeHours: 0, totalPay: 0, totalEntries: 0 }
    );

    res.json({
      payroll: payrollWithUsers.sort((a, b) => a.user.lastName.localeCompare(b.user.lastName)),
      totals,
      filters: { startDate, endDate, projectId, status },
    });
  } catch (error) {
    logger.error('Error generating payroll report:', error);
    res.status(500).json({ error: 'Failed to generate payroll report' });
  }
});

// Save report
router.post('/save', async (req: Request, res: Response) => {
  try {
    const { type, title, description, data, filters } = req.body;
    const generatedBy = req.user?.id; // Assuming user is attached by auth middleware

    const report = await prisma.report.create({
      data: {
        type,
        title,
        description,
        data,
        filters,
        generatedBy,
      },
    });

    logger.info(`Report saved: ${report.id} by user: ${generatedBy}`);
    res.status(201).json(report);
  } catch (error) {
    logger.error('Error saving report:', error);
    res.status(500).json({ error: 'Failed to save report' });
  }
});

// Get saved reports
router.get('/saved', async (req: Request, res: Response) => {
  try {
    const { type, limit = 20 } = req.query;

    const where: any = {};
    if (type) where.type = type;

    const reports = await prisma.report.findMany({
      where,
      take: Number(limit),
      orderBy: { createdAt: 'desc' },
      include: {
        _count: { select: { id: true } },
      },
    });

    res.json(reports);
  } catch (error) {
    logger.error('Error fetching saved reports:', error);
    res.status(500).json({ error: 'Failed to fetch saved reports' });
  }
});

export default router;