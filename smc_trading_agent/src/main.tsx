import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import TestApp from "./TestApp.tsx";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";

console.log('main.tsx is executing');
console.log('React version:', React.version);

console.log('🚀 Starting SMC Trading Agent application...');

try {
  const rootElement = document.getElementById("root");
  if (!rootElement) {
    throw new Error('Root element not found');
  }
  
  console.log('✅ Root element found, creating React root...');
  
  const root = createRoot(rootElement);
  
  console.log('✅ React root created, rendering app...');
  
  root.render(
    <StrictMode>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </StrictMode>
  );
  
  console.log('✅ App rendered successfully!');
} catch (error) {
  console.error('❌ Failed to initialize app:', error);
  document.body.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: system-ui;">
      <div style="text-align: center; padding: 2rem; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h1 style="color: #dc2626; margin-bottom: 1rem;">Błąd inicjalizacji aplikacji</h1>
        <p style="color: #6b7280; margin-bottom: 1rem;">Sprawdź konsolę przeglądarki, aby uzyskać więcej informacji.</p>
        <button onclick="window.location.reload()" style="background: #3b82f6; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer;">Odśwież stronę</button>
      </div>
    </div>
  `;
}

// Register a basic service worker only in production
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('Service worker registered', reg.scope))
      .catch(err => console.error('Service worker registration failed', err));
  });
}
