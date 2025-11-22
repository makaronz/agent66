import '@testing-library/jest-dom';
import 'jest-axe/extend-expect';

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock getComputedStyle
Object.defineProperty(window, 'getComputedStyle', {
  value: () => ({
    getPropertyValue: () => '',
    zIndex: '0',
  }),
});

// Mock HTMLCanvasElement
HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
  fillRect: jest.fn(),
  clearRect: jest.fn(),
  getImageData: jest.fn(() => ({ data: new Array(4) })),
  putImageData: jest.fn(),
  createImageData: jest.fn(() => ({ data: new Array(4) })),
  setTransform: jest.fn(),
  drawImage: jest.fn(),
  save: jest.fn(),
  fillText: jest.fn(),
  restore: jest.fn(),
  beginPath: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  closePath: jest.fn(),
  stroke: jest.fn(),
  translate: jest.fn(),
  scale: jest.fn(),
  rotate: jest.fn(),
  arc: jest.fn(),
  fill: jest.fn(),
  measureText: jest.fn(() => ({ width: 0 })),
  transform: jest.fn(),
  rect: jest.fn(),
  clip: jest.fn(),
}));

// Mock HTMLVideoElement
HTMLVideoElement.prototype.play = jest.fn(() => Promise.resolve());
HTMLVideoElement.prototype.pause = jest.fn();
HTMLVideoElement.prototype.load = jest.fn();

// Mock scrollTo
window.scrollTo = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock fetch if not already defined
if (!global.fetch) {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
      headers: new Headers(),
      redirected: false,
      statusText: 'OK',
      type: 'basic' as ResponseType,
      url: '',
      clone: jest.fn(),
      body: null,
      bodyUsed: false,
      arrayBuffer: jest.fn(),
      blob: jest.fn(),
      formData: jest.fn(),
      text: () => Promise.resolve('{}'),
    })
  );
}

// Mock requestAnimationFrame
global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 0));
global.cancelAnimationFrame = jest.fn(id => clearTimeout(id));

// Mock pointer events
Object.defineProperty(window, 'PointerEvent', {
  value: jest.fn(() => ({
    clientX: 0,
    clientY: 0,
    preventDefault: jest.fn(),
    stopPropagation: jest.fn(),
  })),
});

// Suppress console warnings in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is no longer supported')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Clean up after each test
afterEach(() => {
  jest.clearAllTimers();
  jest.clearAllMocks();
  document.body.innerHTML = '';
});

// Global test utilities
global.testUtils = {
  // Helper to wait for component updates
  waitFor: (ms: number = 0) => new Promise(resolve => setTimeout(resolve, ms)),

  // Helper to create mock user data
  createUser: (overrides = {}) => ({
    id: '1',
    email: 'test@example.com',
    name: 'Test User',
    firstName: 'Test',
    lastName: 'User',
    ...overrides,
  }),

  // Helper to create mock project data
  createProject: (overrides = {}) => ({
    id: '1',
    title: 'Test Project',
    status: 'PLANNING',
    type: 'FEATURE_FILM',
    _count: { members: 5, timeEntries: 10 },
    ...overrides,
  }),

  // Helper to create mock time entry data
  createTimeEntry: (overrides = {}) => ({
    id: '1',
    clockIn: '2024-01-15T08:00:00Z',
    clockOut: '2024-01-15T16:00:00Z',
    totalHours: 8,
    status: 'COMPLETED',
    project: {
      id: '1',
      title: 'Test Project',
    },
    ...overrides,
  }),
};

declare global {
  namespace NodeJS {
    interface Global {
      testUtils: {
        waitFor: (ms?: number) => Promise<void>;
        createUser: (overrides?: any) => any;
        createProject: (overrides?: any) => any;
        createTimeEntry: (overrides?: any) => any;
      };
    }
  }
}