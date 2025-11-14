import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['./test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'test/**',
        'dist/**',
        'coverage/**',
        '**/*.config.js',
        '**/*.config.ts',
        'scripts/**',
        'docs/**',
        '.env*',
        '*.log',
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80,
        },
      },
    },
    include: [
      'backend/src/**/*.{test,spec}.{js,ts}',
      'frontend/src/**/*.{test,spec}.{js,ts}',
      'test/**/*.{test,spec}.{js,ts}',
    ],
    exclude: [
      'node_modules/**',
      'dist/**',
      '.next/**',
      'coverage/**',
      '**/*.d.ts',
    ],
    testTimeout: 30000,
    hookTimeout: 30000,
    maxConcurrency: 5,
    isolate: true,
    threads: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './backend/src'),
      '@frontend': resolve(__dirname, './frontend/src'),
      '@test': resolve(__dirname, './test'),
      '@config': resolve(__dirname, './backend/src/config'),
      '@utils': resolve(__dirname, './backend/src/utils'),
      '@types': resolve(__dirname, './backend/src/types'),
    },
  },
});