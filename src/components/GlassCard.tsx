import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hoverEffect?: boolean;
  style?: React.CSSProperties;
}

export function GlassCard({ children, className = '', hoverEffect = false, style }: GlassCardProps) {
  return (
    <div className={`glass-panel ${hoverEffect ? 'card' : ''} ${className}`} style={{ padding: '24px', ...style }}>
      {children}
    </div>
  );
}
