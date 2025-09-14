import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';
export type ChartType = 'candlestick' | 'line' | 'area';
export type TimeFrame = '1m' | '5m' | '15m' | '1h' | '4h' | '1d' | '1w';

export interface NotificationSettings {
  priceAlerts: boolean;
  tradingSignals: boolean;
  systemUpdates: boolean;
  sound: boolean;
}

export interface ChartSettings {
  type: ChartType;
  timeFrame: TimeFrame;
  showVolume: boolean;
  showIndicators: boolean;
  gridLines: boolean;
  crosshair: boolean;
}

export interface LayoutSettings {
  sidebarCollapsed: boolean;
  chartHeight: number;
  showOrderBook: boolean;
  showTradeHistory: boolean;
  compactMode: boolean;
}

export interface UIState {
  // Theme and appearance
  theme: Theme;
  
  // Navigation and layout
  currentPage: string;
  layout: LayoutSettings;
  
  // Chart settings
  chart: ChartSettings;
  
  // Notifications
  notifications: NotificationSettings;
  
  // Modal and dialog state
  modals: {
    settings: boolean;
    profile: boolean;
    help: boolean;
    about: boolean;
  };
  
  // Loading and error states
  globalLoading: boolean;
  globalError: string | null;
  
  // Toast notifications
  toasts: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message?: string;
    duration?: number;
    timestamp: number;
  }>;
  
  // Actions
  setTheme: (theme: Theme) => void;
  setCurrentPage: (page: string) => void;
  updateLayout: (updates: Partial<LayoutSettings>) => void;
  updateChart: (updates: Partial<ChartSettings>) => void;
  updateNotifications: (updates: Partial<NotificationSettings>) => void;
  
  // Modal actions
  openModal: (modal: keyof UIState['modals']) => void;
  closeModal: (modal: keyof UIState['modals']) => void;
  closeAllModals: () => void;
  
  // Global state actions
  setGlobalLoading: (loading: boolean) => void;
  setGlobalError: (error: string | null) => void;
  
  // Toast actions
  addToast: (toast: Omit<UIState['toasts'][0], 'id' | 'timestamp'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
  
  // Utility actions
  reset: () => void;
}

const defaultLayoutSettings: LayoutSettings = {
  sidebarCollapsed: false,
  chartHeight: 400,
  showOrderBook: true,
  showTradeHistory: true,
  compactMode: false,
};

const defaultChartSettings: ChartSettings = {
  type: 'candlestick',
  timeFrame: '1h',
  showVolume: true,
  showIndicators: true,
  gridLines: true,
  crosshair: true,
};

const defaultNotificationSettings: NotificationSettings = {
  priceAlerts: true,
  tradingSignals: true,
  systemUpdates: true,
  sound: false,
};

const defaultModals = {
  settings: false,
  profile: false,
  help: false,
  about: false,
};

export const useUIStore = create<UIState>()(persist(immer((set, get) => ({
  // Initial state
  theme: 'system',
  currentPage: 'dashboard',
  layout: defaultLayoutSettings,
  chart: defaultChartSettings,
  notifications: defaultNotificationSettings,
  modals: defaultModals,
  globalLoading: false,
  globalError: null,
  toasts: [],

  // Theme actions
  setTheme: (theme) => set((state) => {
    state.theme = theme;
  }),

  // Navigation actions
  setCurrentPage: (page) => set((state) => {
    state.currentPage = page;
  }),

  // Layout actions
  updateLayout: (updates) => set((state) => {
    Object.assign(state.layout, updates);
  }),

  // Chart actions
  updateChart: (updates) => set((state) => {
    Object.assign(state.chart, updates);
  }),

  // Notification actions
  updateNotifications: (updates) => set((state) => {
    Object.assign(state.notifications, updates);
  }),

  // Modal actions
  openModal: (modal) => set((state) => {
    state.modals[modal] = true;
  }),

  closeModal: (modal) => set((state) => {
    state.modals[modal] = false;
  }),

  closeAllModals: () => set((state) => {
    Object.keys(state.modals).forEach(key => {
      state.modals[key as keyof typeof state.modals] = false;
    });
  }),

  // Global state actions
  setGlobalLoading: (loading) => set((state) => {
    state.globalLoading = loading;
  }),

  setGlobalError: (error) => set((state) => {
    state.globalError = error;
  }),

  // Toast actions
  addToast: (toast) => set((state) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast = {
      ...toast,
      id,
      timestamp: Date.now(),
      duration: toast.duration ?? 5000,
    };
    
    state.toasts.push(newToast);
    
    // Auto-remove toast after duration
    if (newToast.duration > 0) {
      setTimeout(() => {
        get().removeToast(id);
      }, newToast.duration);
    }
  }),

  removeToast: (id) => set((state) => {
    state.toasts = state.toasts.filter(toast => toast.id !== id);
  }),

  clearToasts: () => set((state) => {
    state.toasts = [];
  }),

  // Utility actions
  reset: () => set((state) => {
    state.theme = 'system';
    state.currentPage = 'dashboard';
    state.layout = { ...defaultLayoutSettings };
    state.chart = { ...defaultChartSettings };
    state.notifications = { ...defaultNotificationSettings };
    state.modals = { ...defaultModals };
    state.globalLoading = false;
    state.globalError = null;
    state.toasts = [];
  }),
})), {
  name: 'smc-ui-store',
  partialize: (state) => ({
    theme: state.theme,
    layout: state.layout,
    chart: state.chart,
    notifications: state.notifications,
  }),
}));

// Helper hooks for specific UI concerns
export const useTheme = () => useUIStore(state => state.theme);
export const useLayout = () => useUIStore(state => state.layout);
export const useChart = () => useUIStore(state => state.chart);
export const useNotifications = () => useUIStore(state => state.notifications);
export const useModals = () => useUIStore(state => state.modals);
export const useToasts = () => useUIStore(state => state.toasts);

// Theme detection helper
export const getEffectiveTheme = (): 'light' | 'dark' => {
  const theme = useUIStore.getState().theme;
  
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  
  return theme;
};

// System theme change listener
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  
  mediaQuery.addEventListener('change', () => {
    const { theme } = useUIStore.getState();
    if (theme === 'system') {
      // Force re-render by updating a dummy state
      useUIStore.setState(state => ({ ...state }));
    }
  });
}