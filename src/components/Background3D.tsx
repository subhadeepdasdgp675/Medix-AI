import React from 'react';

export function Background3D() {
  return (
    <div 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: -1,
        pointerEvents: 'none', // Allow clicks to pass through to the UI
        opacity: 0.5, // Adjust opacity so it doesn't overpower the UI
        filter: 'blur(8px)', // Blur the background to keep UI elements clearly visible
      }}
    >
      <iframe 
        src="https://my.spline.design/pillanddnaanimation-GVixS2hZ4lY6etrwDgfFJMFz/" 
        frameBorder="0" 
        width="100%" 
        height="100%"
        style={{ width: '100%', height: '100%' }}
      ></iframe>
    </div>
  );
}

