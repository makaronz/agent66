import { connectDB, closeDB, clearDB } from '../helpers/database';
import { FilmIndustryFixtures } from './film-industry-data';
import User from '../../models/User';

export class TestDatabaseManager {
  private static instance: TestDatabaseManager;
  private isConnected = false;

  static getInstance(): TestDatabaseManager {
    if (!TestDatabaseManager.instance) {
      TestDatabaseManager.instance = new TestDatabaseManager();
    }
    return TestDatabaseManager.instance;
  }

  async setupTestDatabase(): Promise<void> {
    if (!this.isConnected) {
      await connectDB();
      this.isConnected = true;
    }
    await clearDB();
  }

  async cleanupTestDatabase(): Promise<void> {
    if (this.isConnected) {
      await clearDB();
      await closeDB();
      this.isConnected = false;
    }
  }

  async createTestData(options: {
    userCount?: number;
    projectCount?: number;
    timesheetCount?: number;
    crewCount?: number;
  } = {}): Promise<any> {
    const {
      userCount = 10,
      projectCount = 3,
      timesheetCount = 50,
      crewCount = 25
    } = options;

    // Create test users
    const users = await this.createTestUsers(userCount);

    // Create film industry data
    const projects = FilmIndustryFixtures.generateProjects(projectCount);
    const crew = FilmIndustryFixtures.generateCrew(crewCount);
    const departments = FilmIndustryFixtures.generateDepartments(6);
    const equipment = FilmIndustryFixtures.generateEquipment(30);
    const locations = FilmIndustryFixtures.generateLocations(8);
    const timesheets = FilmIndustryFixtures.generateTimesheetEntries(timesheetCount, crew, projects);

    return {
      users,
      projects,
      crew,
      departments,
      equipment,
      locations,
      timesheets
    };
  }

  private async createTestUsers(count: number): Promise<any[]> {
    const users = [];
    const roles = ['ADMIN', 'SUPERVISOR', 'SUPERVISOR_USER', 'CREW', 'CLIENT', 'GUEST'];
    const departments = ['Camera', 'Lighting', 'Sound', 'Art', 'Production', 'Hair & Makeup'];

    for (let i = 0; i < count; i++) {
      const userData = {
        email: `testuser${i + 1}@filmcrew.com`,
        firstName: faker.person.firstName(),
        lastName: faker.person.lastName(),
        role: faker.helpers.arrayElement(roles),
        department: faker.helpers.arrayElement(departments),
        phone: faker.phone.number('##########'),
        avatar: faker.image.avatar(),
        createdAt: new Date(),
        updatedAt: new Date()
      };

      const user = new User(userData);
      await user.save();
      users.push(user.toObject());
    }

    return users;
  }

  async createProductionEnvironment(): Promise<any> {
    // Create comprehensive production environment
    const testData = await this.createTestData({
      userCount: 20,
      projectCount: 2,
      timesheetCount: 200,
      crewCount: 40
    });

    // Create supervisor and crew relationships
    const supervisors = testData.users.filter(u => u.role === 'SUPERVISOR');
    const crewMembers = testData.users.filter(u => u.role === 'CREW');

    // Create shooting schedules
    const schedules = FilmIndustryFixtures.generateShootingSchedules(30);

    return {
      ...testData,
      schedules,
      supervisors,
      crewMembers,
      rateStructures: FilmIndustryFixtures.generateRateStructures()
    };
  }

  async createHighVolumeTestData(): Promise<any> {
    // Create large dataset for performance testing
    const largeTestData = await this.createTestData({
      userCount: 100,
      projectCount: 10,
      timesheetCount: 1000,
      crewCount: 80
    });

    // Add additional stress data
    const additionalEquipment = FilmIndustryFixtures.generateEquipment(100);
    const additionalLocations = FilmIndustryFixtures.generateLocations(20);
    const additionalTimesheets = FilmIndustryFixtures.generateTimesheetEntries(
      500,
      largeTestData.crew,
      largeTestData.projects
    );

    return {
      ...largeTestData,
      additionalEquipment,
      additionalLocations,
      additionalTimesheets,
      totalTimesheets: largeTestData.timesheets.length + additionalTimesheets.length
    };
  }

  async createOfflineTestData(): Promise<any> {
    // Create data for offline testing scenarios
    const offlineData = await this.createTestData({
      userCount: 5,
      projectCount: 1,
      timesheetCount: 10,
      crewCount: 3
    });

    // Create mobile-specific test data
    const mobileUsers = offlineData.users.slice(0, 3);
    const mobileTimesheets = offlineData.timesheets.slice(0, 10);

    return {
      users: mobileUsers,
      timesheets: mobileTimesheets,
      projects: offlineData.projects.slice(0, 1),
      equipment: offlineData.equipment.slice(0, 10),
      locations: offlineData.locations.slice(0, 3)
    };
  }

  async createComplianceTestData(): Promise<any> {
    // Create data specifically for compliance testing
    const complianceData = await this.createTestData({
      userCount: 15,
      projectCount: 3,
      timesheetCount: 100,
      crewCount: 25
    });

    // Create compliance-specific scenarios
    const overtimeScenarios = FilmIndustryFixtures.generateTimesheetEntries(
      20,
      complianceData.crew.filter(c => ['Camera Operator', 'Gaffer', 'Key Grip'].includes(c.role)),
      complianceData.projects
    ).map(entry => ({
      ...entry,
      clockIn: '06:00',
      clockOut: '22:00',
      breakDuration: 60,
      totalMinutes: 960, // 16 hours
      regularMinutes: 480,
      overtimeMinutes: 120,
      doubleOvertimeMinutes: 360
    }));

    const californiaCompliance = FilmIndustryFixtures.generateTimesheetEntries(
      20,
      complianceData.crew,
      complianceData.projects
    ).map(entry => ({
      ...entry,
      location: 'Los Angeles Studio',
      state: 'CA',
      complianceRules: ['CALIFORNIA_DAILY_OVERTIME', 'CALIFORNIA_MEAL_BREAKS']
    }));

    return {
      ...complianceData,
      overtimeScenarios,
      californiaCompliance
    };
  }

  async createEdgeCaseTestData(): Promise<any> {
    // Create data for edge case testing
    const edgeCaseData = await this.createTestData({
      userCount: 8,
      projectCount: 2,
      timesheetCount: 30,
      crewCount: 12
    });

    // Create edge case scenarios
    const edgeCases = {
      midnightCrossover: FilmIndustryFixtures.generateTimesheetEntries(
        5,
        edgeCaseData.crew,
        edgeCaseData.projects
      ).map(entry => ({
        ...entry,
        clockIn: '22:00',
        clockOut: '06:00',
        breakDuration: 60,
        crossDayEntry: true
      })),

      splitShift: FilmIndustryFixtures.generateTimesheetEntries(
        5,
        edgeCaseData.crew,
        edgeCaseData.projects
      ).map(entry => ({
        ...entry,
        shiftType: 'SPLIT',
        firstShift: { in: '08:00', out: '12:00' },
        secondShift: { in: '18:00', out: '22:00' },
        breakDuration: 120
      })),

      extendedBreak: FilmIndustryFixtures.generateTimesheetEntries(
        5,
        edgeCaseData.crew,
        edgeCaseData.projects
      ).map(entry => ({
        ...entry,
        clockIn: '08:00',
        clockOut: '19:00',
        breakDuration: 180, // 3-hour break
        extendedBreak: true
      })),

      minimumHours: FilmIndustryFixtures.generateTimesheetEntries(
        5,
        edgeCaseData.crew,
        edgeCaseData.projects
      ).map(entry => ({
        ...entry,
        clockIn: '14:00',
        clockOut: '18:00',
        breakDuration: 0,
        totalMinutes: 240 // 4 hours only
      })),

      noBreak: FilmIndustryFixtures.generateTimesheetEntries(
        5,
        edgeCaseData.crew,
        edgeCaseData.projects
      ).map(entry => ({
        ...entry,
        clockIn: '08:00',
        clockOut: '12:00',
        breakDuration: 0,
        noBreak: true
      }))
    };

    return {
      ...edgeCaseData,
      edgeCases
    };
  }

  async seedDatabaseWithSampleData(): Promise<void> {
    await this.setupTestDatabase();

    // Create sample production environment
    await this.createProductionEnvironment();

    console.log('Test database seeded with sample data');
  }

  async resetDatabase(): Promise<void> {
    await clearDB();
    console.log('Test database reset');
  }

  async getDatabaseStats(): Promise<any> {
    const stats = {
      users: 0,
      projects: 0,
      timesheets: 0,
      crew: 0,
      equipment: 0,
      locations: 0
    };

    // In a real implementation, you would query the actual database
    // For now, return mock stats
    return stats;
  }

  async createTestScenario(scenario: string): Promise<any> {
    switch (scenario) {
      case 'basic':
        return this.createTestData();

      case 'production':
        return this.createProductionEnvironment();

      case 'high-volume':
        return this.createHighVolumeTestData();

      case 'offline':
        return this.createOfflineTestData();

      case 'compliance':
        return this.createComplianceTestData();

      case 'edge-cases':
        return this.createEdgeCaseTestData();

      default:
        throw new Error(`Unknown test scenario: ${scenario}`);
    }
  }

  async createCustomTestData(config: any): Promise<any> {
    const {
      users = [],
      projects = [],
      crew = [],
      departments = [],
      equipment = [],
      locations = [],
      timesheets = [],
      schedules = [],
      ...config
    } = config;

    // Create custom test data based on configuration
    const customData = await this.createTestData({
      userCount: users.length || 0,
      projectCount: projects.length || 0,
      timesheetCount: timesheets.length || 0,
      crewCount: crew.length || 0
    });

    // Merge with provided custom data
    return {
      users: users.length > 0 ? users : customData.users,
      projects: projects.length > 0 ? projects : customData.projects,
      crew: crew.length > 0 ? crew : customData.crew,
      departments: departments.length > 0 ? departments : customData.departments,
      equipment: equipment.length > 0 ? equipment : customData.equipment,
      locations: locations.length > 0 ? locations : customData.locations,
      timesheets: timesheets.length > 0 ? timesheets : customData.timesheets,
      schedules: schedules.length > 0 ? schedules : FilmIndustryFixtures.generateShootingSchedules(10)
    };
  }
}