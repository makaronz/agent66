import React from 'react';

const SimpleApp: React.FC = () => {
  console.log('SimpleApp rendering');
  
  return (
    <div style={{ 
      padding: '20px', 
      backgroundColor: '#f0f8ff', 
      minHeight: '100vh',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h1 style={{ color: '#333', marginBottom: '20px' }}>Simple App Test</h1>
      <p>If you can see this, React is working correctly!</p>
      <p>Current time: {new Date().toLocaleString()}</p>
      
      <div style={{ 
        marginTop: '20px', 
        padding: '15px', 
        backgroundColor: '#e8f5e8', 
        border: '1px solid #4caf50',
        borderRadius: '4px'
      }}>
        <h3>Debug Information:</h3>
        <ul>
          <li>React version: {React.version}</li>
          <li>Environment: {import.meta.env.MODE}</li>
          <li>Supabase URL: {import.meta.env.VITE_SUPABASE_URL ? 'Configured' : 'Not configured'}</li>
        </ul>
      </div>
      
      <button 
        onClick={() => alert('Button clicked! JavaScript is working.')}
        style={{
          marginTop: '20px',
          padding: '10px 20px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Test Button
      </button>
    </div>
  );
};

export default SimpleApp;