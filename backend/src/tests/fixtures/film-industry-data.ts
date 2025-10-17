import { faker } from '@faker-js/faker';
import { User, UserRole } from '../../models/User';

export interface FilmProductionData {
  projects: any[];
  crew: any[];
  departments: any[];
  equipment: any[];
  locations: any[];
  unions: any[];
  rateStructures: any[];
  shootingSchedules: any[];
  timesheetEntries: any[];
}

export const FilmIndustryFixtures = {
  /**
   * Generate realistic film industry projects
   */
  generateProjects(count: number = 5) {
    const projectTypes = ['FEATURE_FILM', 'TV_EPISODE', 'COMMERCIAL', 'MUSIC_VIDEO', 'DOCUMENTARY'];
    const statuses = ['PRE_PRODUCTION', 'ACTIVE', 'WRAPPING', 'POST_PRODUCTION', 'COMPLETED'];

    return Array.from({ length: count }, (_, i) => ({
      id: `proj-${String(i + 1).padStart(3, '0')}`,
      name: this.generateProjectName(),
      code: this.generateProjectCode(i),
      type: faker.helpers.arrayElement(projectTypes),
      status: faker.helpers.arrayElement(statuses),
      startDate: faker.date.between({ from: '2025-01-01', to: '2025-12-31' }),
      endDate: faker.date.between({ from: '2025-06-01', to: '2026-06-01' }),
      budget: faker.number.int({ min: 1000000, max: 50000000 }),
      locations: this.generateLocations(faker.number.int({ min: 1, max: 5 })),
      departments: this.generateDepartments(faker.number.int({ min: 3, max: 8 })),
      productionCompany: faker.company.name(),
      director: faker.person.fullName(),
      producer: faker.person.fullName(),
      lineProducer: faker.person.fullName(),
      upm: faker.person.fullName(),
      description: faker.lorem.paragraphs(2),
      genre: faker.helpers.arrayElement(['Action', 'Drama', 'Comedy', 'Horror', 'Sci-Fi', 'Romance']),
      rating: faker.helpers.arrayElement(['G', 'PG', 'PG-13', 'R', 'NC-17']),
      runtime: faker.number.int({ min: 80, max: 180 }),
      estimatedShootingDays: faker.number.int({ min: 30, max: 120 }),
      actualShootingDays: faker.number.int({ min: 25, max: 130 })
    }));
  },

  /**
   * Generate realistic crew members with film industry roles
   */
  generateCrew(count: number = 50) {
    const filmRoles = [
      { department: 'Camera', roles: ['Director of Photography', 'Camera Operator', '1st AC', '2nd AC', 'Digital Imaging Technician', 'Steadicam Operator', 'Drone Operator'] },
      { department: 'Lighting', roles: ['Gaffer', 'Best Boy Electric', 'Key Grip', 'Dolly Grip', 'Lighting Technician', 'Rigging Grip'] },
      { department: 'Sound', roles: ['Production Sound Mixer', 'Boom Operator', 'Sound Utility', 'Playback Engineer'] },
      { department: 'Art', roles: ['Production Designer', 'Art Director', 'Set Decorator', 'Props Master', 'Lead Carpenter', 'Scenic Artist'] },
      { department: 'Hair & Makeup', roles: ['Department Head', 'Key Makeup Artist', 'Key Hair Stylist', 'Special Effects Makeup', 'Hair Stylist'] },
      { department: 'Wardrobe', roles: ['Costume Designer', 'Costume Supervisor', 'Key Costumer', 'Tailor', 'Dresser'] },
      { department: 'Production', roles: ['Production Manager', 'Assistant Director', '2nd AD', 'Production Coordinator', 'Script Supervisor', 'PA'] },
      { department: 'Special Effects', roles: ['VFX Supervisor', 'Special Effects Coordinator', 'Practical Effects', 'Pyrotechnician'] },
      { department: 'Transportation', roles: ['Transportation Captain', 'Teamster', 'Truck Driver', 'Mechanic'] },
      { department: 'Catering', roles: ['Catering Manager', 'Head Chef', 'Kitchen Assistant'] }
    ];

    const unions = ['IATSE', 'DGA', 'SAG-AFTRA', 'Teamsters', 'IBEW', 'Local 600', 'Local 728', 'Local 44'];
    const departments = filmRoles.map(fr => fr.department);

    return Array.from({ length: count }, (_, i) => {
      const deptInfo = faker.helpers.arrayElement(filmRoles);
      const role = faker.helpers.arrayElement(deptInfo.roles);

      return {
        id: `crew-${String(i + 1).padStart(4, '0')}`,
        firstName: faker.person.firstName(),
        lastName: faker.person.lastName(),
        email: faker.internet.email(),
        phone: faker.phone.number('##########'),
        role: role,
        department: deptInfo.department,
        union: faker.helpers.arrayElement(unions),
        unionNumber: `${faker.helpers.arrayElement(['IATSE', 'DGA', 'SAG'])}-${faker.number.int({ min: 100, max: 9999 })}`,
        experience: faker.number.int({ min: 1, max: 30 }),
        specialties: this.generateSpecialties(deptInfo.department),
        certifications: this.generateCertifications(role),
        rate: this.generateRateForRole(role),
        location: faker.helpers.arrayElement(['Los Angeles', 'New York', 'Atlanta', 'Vancouver', 'London']),
        availability: faker.helpers.arrayElement(['Available', 'On Project', 'Unavailable']),
        bio: faker.lorem.sentences(3),
        profileImage: faker.image.avatar(),
        equipment: this.generatePersonalEquipment(deptInfo.department),
        skills: this.generateSkills(deptInfo.department),
        references: this.generateReferences(),
        emergencyContact: {
          name: faker.person.fullName(),
          relationship: faker.helpers.arrayElement(['Spouse', 'Parent', 'Sibling', 'Friend']),
          phone: faker.phone.number('##########')
        }
      };
    });
  },

  /**
   * Generate departments for film production
   */
  generateDepartments(count: number = 8) {
    const departmentNames = [
      'Camera', 'Lighting', 'Sound', 'Art', 'Hair & Makeup',
      'Wardrobe', 'Production', 'Special Effects', 'Transportation', 'Catering'
    ];

    return Array.from({ length: Math.min(count, departmentNames.length) }, (_, i) => ({
      id: `dept-${String(i + 1).padStart(2, '0')}`,
      name: departmentNames[i],
      head: faker.person.fullName(),
      supervisor: faker.person.fullName(),
      budget: faker.number.int({ min: 50000, max: 500000 }),
      crewCount: faker.number.int({ min: 5, max: 25 }),
      equipmentCount: faker.number.int({ min: 10, max: 100 }),
      description: `${departmentNames[i]} department for film production`,
      responsibilities: this.generateDepartmentResponsibilities(departmentNames[i])
    }));
  },

  /**
   * Generate film industry equipment
   */
  generateEquipment(count: number = 50) {
    const cameraEquipment = [
      'ARRI Alexa 65', 'RED Monstro 8K', 'Sony Venice', 'Canon C300', 'Sony FX9',
      'Zeiss Supreme Primes', 'Cooke S7 Primes', 'Angenieux Optimo Lenses',
      'DJI Ronin 4D', 'MoVI Pro', 'Easyrig Mini', 'Steadicam M1'
    ];

    const lightingEquipment = [
      'Arri SkyPanel S60', 'Arri SkyPanel S120', 'Kino Flo Celeb', 'Aputure Light Storm',
      'M18 HMI', 'Joker Bug', 'Dedolights', 'Kino Flo Select', 'LED Panel Banks',
      '12K Fresnel', '6K Fresnel', '2K Baby', 'Tweenie', 'Inkie'
    ];

    const soundEquipment = [
      'Zaxcom Nomad 12', 'Sound Devices 688', 'Aaton Cantar Mini', 'Sony PCM-M10',
      'Sennheiser MKH 416', 'Sennheiser G4 Wireless', 'Lectroson Wireless',
      'Boom Pole', 'Windshield', 'Dead Cat', 'Sound Devices MixPre'
    ];

    const allEquipment = [...cameraEquipment, ...lightingEquipment, ...soundEquipment];

    return Array.from({ length: Math.min(count, allEquipment.length) }, (_, i) => ({
      id: `eq-${String(i + 1).padStart(3, '0')}`,
      name: allEquipment[i],
      category: this.getEquipmentCategory(allEquipment[i]),
      serialNumber: faker.string.alphanumeric(10),
      purchaseDate: faker.date.past({ years: 5 }),
      purchasePrice: faker.number.int({ min: 1000, max: 100000 }),
      currentValue: faker.number.int({ min: 500, max: 80000 }),
      condition: faker.helpers.arrayElement(['Excellent', 'Good', 'Fair', 'Poor']),
      location: faker.helpers.arrayElement(['Main Storage', 'Location Truck', 'Set', 'Studio']),
      assignedTo: faker.person.fullName(),
      maintenanceDate: faker.date.between({ from: '2025-01-01', to: '2025-12-31' }),
      warranty: faker.datatype.boolean(),
      accessories: this.generateAccessories(allEquipment[i]),
      notes: faker.lorem.sentences(2)
    }));
  },

  /**
   * Generate shooting locations
   */
  generateLocations(count: number = 15) {
    const locationTypes = ['Studio', 'Location', 'Exterior', 'Interior', 'Mixed'];

    return Array.from({ length: count }, (_, i) => ({
      id: `loc-${String(i + 1).padStart(3, '0')}`,
      name: this.generateLocationName(),
      type: faker.helpers.arrayElement(locationTypes),
      address: faker.location.streetAddress(),
      city: faker.helpers.arrayElement(['Los Angeles', 'New York', 'Atlanta', 'Vancouver', 'Chicago']),
      state: faker.helpers.arrayElement(['CA', 'NY', 'GA', 'BC', 'IL']),
      zipCode: faker.location.zipCode(),
      country: 'USA',
      coordinates: {
        latitude: faker.location.latitude(),
        longitude: faker.location.longitude()
      },
      contact: {
        name: faker.person.fullName(),
        phone: faker.phone.number('##########'),
        email: faker.internet.email()
      },
      capacity: faker.number.int({ min: 10, max: 500 }),
      parkingSpaces: faker.number.int({ min: 5, max: 100 }),
      powerAvailable: faker.datatype.boolean(),
      wifiAvailable: faker.datatype.boolean(),
      restrooms: faker.number.int({ min: 1, max: 10 }),
      dressingRooms: faker.number.int({ min: 0, max: 20 }),
      cateringFacilities: faker.datatype.boolean(),
      permitsRequired: this.generatePermits(),
      rates: {
        hourly: faker.number.int({ min: 500, max: 5000 }),
        daily: faker.number.int({ min: 2000, max: 20000 }),
        weekly: faker.number.int({ min: 10000, max: 100000 })
      },
      notes: faker.lorem.sentences(3)
    }));
  },

  /**
   * Generate timesheet entries
   */
  generateTimesheetEntries(count: number = 100, crew: any[] = [], projects: any[] = []) {
    return Array.from({ length: count }, (_, i) => {
      const crewMember = faker.helpers.arrayElement(crew.length > 0 ? crew : this.generateCrew(10));
      const project = faker.helpers.arrayElement(projects.length > 0 ? projects : this.generateProjects(3));

      const date = faker.date.between({ from: '2025-10-01', to: '2025-10-31' });
      const clockIn = faker.date.between({ from: date, to: new Date(date.getTime() + 4 * 60 * 60 * 1000) });
      const clockOut = faker.date.between({
        from: new Date(clockIn.getTime() + 4 * 60 * 60 * 1000),
        to: new Date(clockIn.getTime() + 16 * 60 * 60 * 1000)
      });

      const totalMinutes = Math.floor((clockOut.getTime() - clockIn.getTime()) / (1000 * 60));
      const breakDuration = faker.helpers.arrayElement([30, 45, 60, 90]);
      const workMinutes = totalMinutes - breakDuration;

      return {
        id: `ts-${String(i + 1).padStart(4, '0')}`,
        crewId: crewMember.id,
        crewName: `${crewMember.firstName} ${crewMember.lastName}`,
        crewRole: crewMember.role,
        crewDepartment: crewMember.department,
        projectId: project.id,
        projectName: project.name,
        date: date.toISOString().split('T')[0],
        clockIn: clockIn.toTimeString().split(' ')[0].substring(0, 5),
        clockOut: clockOut.toTimeString().split(' ')[0].substring(0, 5),
        breakDuration: breakDuration,
        totalMinutes: totalMinutes,
        regularMinutes: Math.min(workMinutes, 480),
        overtimeMinutes: Math.max(0, workMinutes - 480),
        doubleOvertimeMinutes: Math.max(0, workMinutes - 600),
        location: faker.helpers.arrayElement(['Studio A', 'Studio B', 'Location A', 'Location B', 'Set 1']),
        scenesShot: this.generateScenesShot(),
        equipmentUsed: this.generateEquipmentUsed(crewMember.department),
        notes: faker.lorem.sentences(2),
        status: faker.helpers.arrayElement(['PENDING', 'APPROVED', 'REJECTED']),
        submittedAt: date.toISOString(),
        approvedBy: faker.datatype.boolean() ? faker.person.fullName() : null,
        approvedAt: faker.datatype.boolean() ? faker.date.between({ from: date, to: new Date() }).toISOString() : null,
        weatherConditions: faker.helpers.arrayElement(['Clear', 'Cloudy', 'Rainy', 'Windy', 'Hot', 'Cold']),
        temperature: faker.number.int({ min: -10, max: 110 }),
        callTime: faker.date.between({ from: new Date(clockIn.getTime() - 2 * 60 * 60 * 1000), to: clockIn }).toTimeString().split(' ')[0].substring(0, 5),
        wrapTime: faker.date.between({ from: clockOut, to: new Date(clockOut.getTime() + 2 * 60 * 60 * 1000) }).toTimeString().split(' ')[0].substring(0, 5),
        rateApplied: crewMember.rate?.hourly || faker.number.int({ min: 25, max: 150 }),
        overtimeRate: (crewMember.rate?.hourly || faker.number.int({ min: 25, max: 150 })) * 1.5,
        doubleOvertimeRate: (crewMember.rate?.hourly || faker.number.int({ min: 25, max: 150 })) * 2,
        totalEarnings: this.calculateEarnings(workMinutes, crewMember.rate?.hourly || 50),
        clientTimestamp: faker.date.between({ from: date, to: clockOut }).toISOString(),
        deviceId: faker.string.alphanumeric(10),
        gpsCoordinates: {
          latitude: faker.location.latitude(),
          longitude: faker.location.longitude()
        }
      };
    });
  },

  /**
   * Generate rate structures for different roles
   */
  generateRateStructures() {
    return {
      hourlyRates: {
        'Director of Photography': { min: 75, max: 200, average: 125 },
        'Camera Operator': { min: 45, max: 85, average: 65 },
        '1st AC': { min: 35, max: 65, average: 50 },
        '2nd AC': { min: 25, max: 45, average: 35 },
        'Gaffer': { min: 50, max: 120, average: 85 },
        'Key Grip': { min: 45, max: 100, average: 72 },
        'Production Sound Mixer': { min: 40, max: 90, average: 65 },
        'Production Manager': { min: 60, max: 150, average: 105 }
      },
      dailyRates: {
        'Director of Photography': { min: 600, max: 1600, average: 1000 },
        'Camera Operator': { min: 360, max: 680, average: 520 },
        '1st AC': { min: 280, max: 520, average: 400 },
        '2nd AC': { min: 200, max: 360, average: 280 },
        'Gaffer': { min: 400, max: 960, average: 680 },
        'Key Grip': { min: 360, max: 800, average: 576 },
        'Production Sound Mixer': { min: 320, max: 720, average: 520 }
      },
      weeklyRates: {
        'Director of Photography': { min: 3000, max: 8000, average: 5000 },
        'Camera Operator': { min: 1800, max: 3400, average: 2600 },
        '1st AC': { min: 1400, max: 2600, average: 2000 },
        '2nd AC': { min: 1000, max: 1800, average: 1400 },
        'Gaffer': { min: 2000, max: 4800, average: 3400 },
        'Key Grip': { min: 1800, max: 4000, average: 2880 },
        'Production Sound Mixer': { min: 1600, max: 3600, average: 2600 }
      }
    };
  },

  /**
   * Generate shooting schedules
   */
  generateShootingSchedules(count: number = 30) {
    const scheduleTypes = ['DAY', 'NIGHT', 'SPLIT', 'SWING'];

    return Array.from({ length: count }, (_, i) => ({
      id: `schedule-${String(i + 1).padStart(3, '0')}`,
      date: faker.date.between({ from: '2025-10-01', to: '2025-10-31' }),
      dayNumber: faker.number.int({ min: 1, max: 30 }),
      shootingDate: faker.date.between({ from: '2025-10-01', to: '2025-10-31' }).toISOString().split('T')[0],
      callTime: faker.date.between({ from: '2025-10-01T05:00:00', to: '2025-10-31T09:00:00' }).toTimeString().split(' ')[0].substring(0, 5),
      wrapTime: faker.date.between({ from: '2025-10-01T18:00:00', to: '2025-10-31T23:00:00' }).toTimeString().split(' ')[0].substring(0, 5),
      scheduleType: faker.helpers.arrayElement(scheduleTypes),
      location: faker.helpers.arrayElement(['Studio A', 'Studio B', 'Location A', 'Location B']),
      scenes: this.generateDayScenes(),
      crewRequired: this.generateCrewRequirements(),
      equipmentRequired: this.generateEquipmentRequirements(),
      cateringRequired: faker.datatype.boolean(),
      transportationRequired: faker.datatype.boolean(),
      permitsRequired: this.generateRequiredPermits(),
      weatherContingency: faker.datatype.boolean(),
      notes: faker.lorem.sentences(2),
      status: faker.helpers.arrayElement(['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'])
    }));
  },

  // Helper methods
  generateProjectName() {
    const adjectives = ['Epic', 'Incredible', 'Amazing', 'Fantastic', 'Legendary', 'Ultimate'];
    const nouns = ['Adventure', 'Journey', 'Odyssey', 'Quest', 'Story', 'Tale'];
    const genres = ['Action', 'Drama', 'Comedy', 'Horror', 'Sci-Fi', 'Romance'];

    return `${faker.helpers.arrayElement(adjectives)} ${faker.helpers.arrayElement(nouns)}: A ${faker.helpers.arrayElement(genres)} Film`;
  },

  generateProjectCode(index: number) {
    const year = '2025';
    const projectTypes = ['SB', 'TV', 'DOC', 'MV', 'ADV'];
    const type = faker.helpers.arrayElement(projectTypes);
    return `${year}-${type}-${String(index + 1).padStart(3, '0')}`;
  },

  generateLocationName() {
    const placeTypes = ['Studio', 'Location', 'Set', 'Venue', 'Space'];
    const descriptors = ['Main', 'Secondary', 'Primary', 'Auxiliary', 'Support'];
    const numbers = ['I', 'II', 'III', 'IV', 'V', 'A', 'B', 'C'];

    return `${faker.helpers.arrayElement(placeTypes)} ${faker.helpers.arrayElement(descriptors)} ${faker.helpers.arrayElement(numbers)}`;
  },

  generateSpecialties(department: string) {
    const specialties = {
      'Camera': ['Documentary', 'Commercial', 'Feature Film', 'Television', 'Music Video', 'Sports', 'Live Events'],
      'Lighting': ['Theatrical', 'Concert', 'Film Noir', 'High Key', 'Low Key', 'Natural Light', 'Special Effects'],
      'Sound': ['Location Recording', 'Studio Recording', 'Live Sound', 'Post-Production', 'Mixer', 'Boom Operator'],
      'Art': ['Set Design', 'Production Design', 'Scenic Art', 'Props', 'Construction', 'Greenscreen'],
      'Hair & Makeup': ['Character', 'Period', 'Special Effects', 'Beauty', 'Prosthetic', 'Airbrushing'],
      'Wardrobe': ['Period Costumes', 'Contemporary Fashion', 'Special Effects Costumes', 'Tailoring', 'Alterations'],
      'Production': ['Scheduling', 'Budgeting', 'Logistics', 'Coordination', 'Management', 'Safety'],
      'Special Effects': ['Pyrotechnics', 'Practical Effects', 'VFX', 'Creature Effects', 'Weather Effects']
    };

    return faker.helpers.arrayElements(specialties[department] || ['General'], { min: 1, max: 3 });
  },

  generateCertifications(role: string) {
    const certifications = {
      'Director of Photography': ['Cinematography Degree', 'IATSE Membership', 'Camera Certification'],
      'Gaffer': ['Electrical License', 'IATSE Membership', 'Lighting Certification'],
      'Production Sound Mixer': ['Audio Engineering Degree', 'IATSE Membership', 'Mixing Certification'],
      'Special Effects Coordinator': ['Pyrotechnics License', 'Safety Certification', 'IATSE Membership']
    };

    return certifications[role] || ['OSHA Certification', 'Film Production Certificate', 'IATSE Membership'];
  },

  generateRateForRole(role: string) {
    const rateStructures = this.generateRateStructures();
    const hourlyRates = rateStructures.hourlyRates[role];

    if (hourlyRates) {
      return {
        hourly: faker.number.int({ min: hourlyRates.min, max: hourlyRates.max }),
        daily: faker.number.int({ min: hourlyRates.min * 8, max: hourlyRates.max * 8 }),
        weekly: faker.number.int({ min: hourlyRates.min * 40, max: hourlyRates.max * 40 }),
        overtime: 1.5,
        doubleOvertime: 2,
        holiday: 2,
        nightDifferential: 0.1,
        weekendDifferential: 0.15
      };
    }

    return {
      hourly: faker.number.int({ min: 25, max: 150 }),
      daily: faker.number.int({ min: 200, max: 1200 }),
      weekly: faker.number.int({ min: 1000, max: 6000 }),
      overtime: 1.5,
      doubleOvertime: 2,
      holiday: 2,
      nightDifferential: 0.1,
      weekendDifferential: 0.15
    };
  },

  generatePersonalEquipment(department: string) {
    const equipment = {
      'Camera': ['Personal camera body', 'Lens kit', 'Light meter', 'Monitor'],
      'Lighting': ['Personal light kit', 'Gel kit', 'Extension cords'],
      'Sound': ['Personal microphone kit', 'Headphones', 'Audio recorder'],
      'Art': ['Personal tool kit', 'Sketchbook', 'Measuring tape'],
      'Hair & Makeup': ['Personal makeup kit', 'Brushes', 'Tools'],
      'Wardrobe': ['Sewing kit', 'Steamer', 'Personal tools']
    };

    return faker.helpers.arrayElements(equipment[department] || ['Personal tools'], { min: 1, max: 3 });
  },

  generateSkills(department: string) {
    const skills = {
      'Camera': ['Cinematography', 'Lighting', 'Color Theory', 'Composition', 'Technical Camera Operation'],
      'Lighting': ['Electrical work', 'Lighting design', 'Color theory', 'Power distribution', 'Safety protocols'],
      'Sound': ['Audio engineering', 'Microphone placement', 'Sound mixing', 'Wireless systems', 'Audio post-production'],
      'Art': ['Set construction', 'Painting', 'Design', 'Carpentry', 'Prop fabrication'],
      'Hair & Makeup': ['Hair styling', 'Makeup application', 'Special effects makeup', 'Airbrushing', 'Period styles'],
      'Wardrobe': ['Sewing', 'Alterations', 'Fashion design', 'Costume history', 'Fabric knowledge']
    };

    return faker.helpers.arrayElements(skills[department] || ['Communication', 'Teamwork', 'Problem solving'], { min: 3, max: 6 });
  },

  generateReferences() {
    return Array.from({ length: faker.number.int({ min: 2, max: 4 }) }, () => ({
      name: faker.person.fullName(),
      company: faker.company.name(),
      title: faker.helpers.arrayElement(['Director', 'Producer', 'Production Manager', 'Supervisor']),
      email: faker.internet.email(),
      phone: faker.phone.number('##########'),
      relationship: faker.helpers.arrayElement(['Former Supervisor', 'Colleague', 'Client', 'Director'])
    }));
  },

  generateDepartmentResponsibilities(department: string) {
    const responsibilities = {
      'Camera': ['Cinematography', 'Camera operation', 'Lighting design', 'Equipment management'],
      'Lighting': ['Lighting design', 'Power distribution', 'Equipment setup', 'Safety protocols'],
      'Sound': ['Audio recording', 'Microphone placement', 'Sound mixing', 'Equipment management'],
      'Art': ['Set design', 'Construction', 'Painting', 'Prop management', 'Budget tracking']
    };

    return responsibilities[department] || ['Team management', 'Quality control', 'Safety compliance', 'Communication'];
  },

  getEquipmentCategory(equipment: string) {
    if (equipment.includes('Camera') || equipment.includes('RED') || equipment.includes('Sony') || equipment.includes('ARRI')) {
      return 'Camera';
    } else if (equipment.includes('SkyPanel') || equipment.includes('HMI') || equipment.includes('Fresnel')) {
      return 'Lighting';
    } else if (equipment.includes('Zaxcom') || equipment.includes('Sennheiser') || equipment.includes('Aaton')) {
      return 'Sound';
    }
    return 'Other';
  },

  generateAccessories(equipment: string) {
    const accessories = {
      'Camera': ['Batteries', 'Memory Cards', 'Cables', 'Lens Filters'],
      'Lighting': ['Bulbs', 'Gels', 'Stands', 'Cables'],
      'Sound': ['Microphones', 'Cables', 'Windshields', 'Batteries']
    };

    const category = this.getEquipmentCategory(equipment);
    return faker.helpers.arrayElements(accessories[category] || ['Cables', 'Cases', 'Manuals'], { min: 1, max: 3 });
  },

  generatePermits() {
    const permitTypes = ['Film Permit', 'Location Permit', 'Parking Permit', 'Noise Permit', 'Special Effects Permit'];
    return faker.helpers.arrayElements(permitTypes, { min: 1, max: 3 });
  },

  generateScenesShot() {
    const sceneCount = faker.number.int({ min: 1, max: 8 });
    return Array.from({ length: sceneCount }, (_, i) => ({
      sceneNumber: `Scene ${faker.number.int({ min: 1, max: 150 })}`,
      description: faker.lorem.sentence(),
      takes: faker.number.int({ min: 1, max: 5 }),
      status: faker.helpers.arrayElement(['COMPLETED', 'IN_PROGRESS', 'READY'])
    }));
  },

  generateEquipmentUsed(department: string) {
    const equipment = {
      'Camera': ['Primary Camera A', 'Camera B', 'Steadicam', 'Drone', 'Gimbal'],
      'Lighting': ['Key Light', 'Fill Light', 'Back Light', 'Practicals', 'LED Panels'],
      'Sound': ['Boom Mic', 'Wireless Mics', 'Recorder', 'Headphones', 'Comms'],
      'Art': ['Props', 'Set Pieces', 'Decorations', 'Tools', 'Supplies']
    };

    return faker.helpers.arrayElements(equipment[department] || ['Tools', 'Equipment'], { min: 1, max: 5 });
  },

  calculateEarnings(workMinutes: number, hourlyRate: number) {
    const regularMinutes = Math.min(workMinutes, 480);
    const overtimeMinutes = Math.max(0, Math.min(workMinutes - 480, 120));
    const doubleOvertimeMinutes = Math.max(0, workMinutes - 600);

    return (
      (regularMinutes / 60) * hourlyRate +
      (overtimeMinutes / 60) * hourlyRate * 1.5 +
      (doubleOvertimeMinutes / 60) * hourlyRate * 2
    );
  },

  generateRequiredPermits() {
    const permits = ['Film Permit', 'Location Permit', 'Noise Permit', 'Parking Permit', 'Street Closure'];
    return faker.helpers.arrayElements(permits, { min: 1, max: 3 });
  },

  generateDayScenes() {
    const sceneCount = faker.number.int({ min: 5, max: 12 });
    return Array.from({ length: sceneCount }, (_, i) => ({
      sceneNumber: faker.number.int({ min: 1, max: 200 }),
      location: faker.helpers.arrayElement(['Studio A', 'Studio B', 'Location A', 'Location B']),
      cast: faker.number.int({ min: 1, max: 10 }),
      pages: faker.number.int({ min: 1, max: 8 }),
      estimatedTime: faker.number.int({ min: 30, max: 180 }),
      description: faker.lorem.sentence()
    }));
  },

  generateCrewRequirements() {
    const departments = ['Camera', 'Lighting', 'Sound', 'Art', 'Hair & Makeup', 'Wardrobe'];
    return departments.map(dept => ({
      department: dept,
      required: faker.number.int({ min: 1, max: 10 }),
      positions: this.generateDepartmentPositions(dept)
    }));
  },

  generateDepartmentPositions(department: string) {
    const positions = {
      'Camera': ['DP', 'Operator', '1st AC', '2nd AC', 'Loader'],
      'Lighting': ['Gaffer', 'Best Boy', 'Electrics', 'Key Grip', 'Grips'],
      'Sound': ['Mixer', 'Boom Op', 'Sound Utility', 'Playback'],
      'Art': ['Art Director', 'Set Decorator', 'Props', 'Construction'],
      'Hair & Makeup': ['Department Head', 'Key Artist', 'Artists'],
      'Wardrobe': ['Supervisor', 'Key Costumer', 'Costumers']
    };

    return faker.helpers.arrayElements(positions[department] || ['Crew'], { min: 2, max: 5 });
  },

  generateEquipmentRequirements() {
    return {
      camera: ['Main Camera', 'B Camera', 'Lenses', 'Support Equipment'],
      lighting: ['Key Lights', 'Fill Lights', 'Practicals', 'Power Distribution'],
      sound: ['Audio Recorder', 'Microphones', 'Boom Pole', 'Headphones'],
      grip: ['Dolly', 'Track', 'Stands', 'Rigging Equipment']
    };
  }
};