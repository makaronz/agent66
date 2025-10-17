import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['../../test/setup.ts'],
    include: [
      'src/**/*.{test,spec}.{js,ts}',
    ],
    exclude: [
      'node_modules/**',
      'dist/**',
      '**/*.d.ts',
    ],
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
          branches: 85,
          functions: 85,
          lines: 85,
          statements: 85,
        },
      },
    },
    testTimeout: 30000,
    hookTimeout: 30000,
    maxConcurrency: 3,
    isolate: true,
    threads: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@config': resolve(__dirname, './src/config'),
      '@utils': resolve(__dirname, './src/utils'),
      '@types': resolve(__dirname, './src/types'),
      '@middleware': resolve(__dirname, './src/middleware'),
      '@services': resolve(__dirname, './src/services'),
      '@controllers': resolve(__dirname, './src/controllers'),
      '@models': resolve(__dirname, './src/models'),
    },
  },
});