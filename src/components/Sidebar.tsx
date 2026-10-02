import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, Activity, Map, FileStack, Settings, Stethoscope, LogOut } from 'lucide-react';
import { clearAuth } from '../lib/api';
import './Sidebar.css';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/new-case', label: 'New patient case', icon: FileText },
  { path: '/drug-interaction', label: 'Drug Interaction Checker', icon: Activity },
  { path: '/resistance-map', label: 'Resistance Map', icon: Map },
  { path: '/reports', label: 'Reports', icon: FileStack },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-header">
        <img src="/src/assets/logo.png" alt="Medix AI Logo" className="logo-icon" style={{ height: '32px', width: 'auto', marginRight: '4px' }} />
        <h2 className="hero-heading">MEDIX AI</h2>
      </div>
      
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon size={20} className="nav-icon" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      
      <div className="sidebar-footer">
        <div className="system-status mb-3">
          <div className="status-dot"></div>
          <span>Systems Normal</span>
        </div>
        <button 
          onClick={handleLogout} 
          className="flex items-center gap-2 text-sm text-secondary hover:text-red-400 transition-colors py-2 px-3 w-full rounded-lg bg-white/5 hover:bg-red-500/10 border border-white/5"
          style={{ cursor: 'pointer', border: 'none', background: 'transparent', display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', width: '100%', color: 'var(--text-secondary)' }}
          title="Sign out of Medix AI"
        >
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
