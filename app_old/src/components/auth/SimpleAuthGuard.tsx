import React from 'react';

interface SimpleAuthGuardProps {
  children: React.ReactNode;
}

const SimpleAuthGuard: React.FC<SimpleAuthGuardProps> = ({ children }) => {
  console.log('🛡️ SimpleAuthGuard rendering...');
  
  // For testing purposes, always show children without authentication
  return (
    <div>
      <div style={{
        position: 'fixed',
        top: '10px',
        left: '10px',
        background: 'rgba(0,255,0,0.8)',
        color: 'black',
        padding: '5px 10px',
        borderRadius: '4px',
        fontSize: '12px',
        zIndex: 9999
      }}>
        SimpleAuthGuard Active
      </div>
      {children}
    </div>
  );
};

export default SimpleAuthGuard;

console.log('✅ SimpleAuthGuard component defined successfully');