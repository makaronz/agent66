import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { traeBadgePlugin } from 'vite-plugin-trae-solo-badge';
import { visualizer } from 'rollup-plugin-visualizer';
import path from 'path';

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/lib': path.resolve(__dirname, './src/lib'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/pages': path.resolve(__dirname, './src/pages'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/utils': path.resolve(__dirname, './src/utils'),
    },
  },
  plugins: [
    react(),
    traeBadgePlugin({
      variant: 'dark',
      position: 'bottom-right',
      prodOnly: true,
      clickable: true,
      clickUrl: 'https://www.trae.ai/solo?showJoin=1',
      autoTheme: true,
      autoThemeTarget: '#root'
    }),
    visualizer({
      filename: 'dist/stats.html',
      open: true,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  build: {
    target: 'es2020',
    sourcemap: false,
    cssCodeSplit: true,
    assetsInlineLimit: 4096,
    chunkSizeWarningLimit: 1000,
    minify: 'terser',
    reportCompressedSize: true,
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info'],
        passes: 2,
      },
      mangle: {
        safari10: true,
      },
      format: {
        comments: false,
      },
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // React ecosystem
            if (id.includes('react') || id.includes('react-dom')) return 'react';
            // Icons - separate chunk for better caching
            if (id.includes('lucide-react')) return 'icons';
            // UI libraries
            if (id.includes('@headlessui') || id.includes('@heroicons') || id.includes('framer-motion')) return 'ui';
            // Charts and visualization
            if (id.includes('recharts') || id.includes('d3')) return 'charts';
            // State management
            if (id.includes('zustand') || id.includes('@tanstack/react-query')) return 'state';
            // Crypto and trading
            if (id.includes('ccxt') || id.includes('crypto-js')) return 'crypto';
            // Authentication
            if (id.includes('@simplewebauthn') || id.includes('bcryptjs')) return 'auth';
            // Routing
            if (id.includes('react-router')) return 'router';
            // Toast notifications
            if (id.includes('react-hot-toast') || id.includes('sonner')) return 'notifications';
            // Utilities
            if (id.includes('date-fns') || id.includes('clsx') || id.includes('axios')) return 'utils';
            return 'vendor';
          }
        }
      }
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3002',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
            proxy.on('error', (err) => {
              console.log('proxy error', err);
            });
            proxy.on('proxyReq', (proxyReq, req) => {
              console.log('Sending Request to the Target:', req.method, req.url);
            });
            proxy.on('proxyRes', (proxyRes, req) => {
              console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
            });
          },
      }
    }
  }
})
