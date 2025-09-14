import React from 'react';

console.log('TestApp component loading...');

const TestApp: React.FC = () => {
  console.log('TestApp rendering...');
  
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#f3f4f6',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '2rem',
        borderRadius: '8px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        textAlign: 'center',
        maxWidth: '400px'
      }}>
        <h1 style={{ color: '#1f2937', marginBottom: '1rem' }}>
          ✅ React App is Working!
        </h1>
        <p style={{ color: '#6b7280', marginBottom: '1rem' }}>
          This is a minimal test component to verify React is rendering correctly.
        </p>
        <div style={{ 
          backgroundColor: '#f3f4f6', 
          padding: '1rem', 
          borderRadius: '4px',
          fontSize: '0.875rem',
          color: '#374151'
        }}>
          <p><strong>Timestamp:</strong> {new Date().toLocaleString()}</p>
          <p><strong>React Version:</strong> {React.version}</p>
          <p><strong>Environment:</strong> {import.meta.env.MODE}</p>
        </div>
        <button 
          onClick={() => {
            console.log('Test button clicked!');
            alert('Test button works!');
          }}
          style={{
            marginTop: '1rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            padding: '0.5rem 1rem',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Test Button
        </button>
      </div>
    </div>
  );
};

export default TestApp;

console.log('TestApp component defined successfully');