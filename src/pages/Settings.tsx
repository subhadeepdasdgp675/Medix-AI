import React, { useEffect, useState } from 'react';
import { 
  User, Bell, Globe, Shield, Moon, Lock, CreditCard, Sun, 
  Camera, Edit3, Check, X, AlertCircle, Volume2, Smartphone, 
  Monitor, LogOut, Trash2, UserX, Sparkles, CheckCircle2, 
  ShieldAlert, Award, Building2, Phone, Mail, FileText, 
  ChevronDown, Key, RefreshCw, Activity, VolumeX
} from 'lucide-react';
import { GlassCard } from '../components/GlassCard';
import { BackButton } from '../components/BackButton';
import { usePersistentState } from '../hooks/usePersistentState';
import './Settings.css';

export function Settings() {
  const [activeTab, setActiveTab] = usePersistentState('medix_set_activeTab', 'profile');
  const [darkMode, setDarkMode] = usePersistentState<boolean>('medix_set_darkMode', !document.body.classList.contains('light-mode'));

  // Form states & dirty tracking for sticky save bar
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Profile Form Data
  const [profileData, setProfileData] = useState(() => {
    try {
      const userStr = localStorage.getItem('medix_user');
      if (userStr) {
        const user = JSON.parse(userStr);
        return {
          fullName: user.fullName || user.full_name || 'Medical Professional',
          email: user.email || '',
          phone: '',
          hospital: user.role === 'hospital' ? (user.fullName || user.full_name || 'Hospital') : '',
          regNumber: user.reg_number || user.regNumber || '',
          specialization: ''
        };
      }
    } catch (e) {}
    
    return {
      fullName: 'Dr. Sarah Connor, MD',
      email: 'sarah.connor@hospital.org',
      phone: '+1 (555) 123-4567',
      hospital: 'Apollo General & Research Hospital',
      regNumber: 'MED-REG-2024-88912',
      specialization: 'Infectious Diseases & Antimicrobial Resistance'
    };
  });

  // Notifications state
  const [notifications, setNotifications] = useState(() => {
    try {
      const stored = localStorage.getItem('medix_notifications');
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {}
    return {
      newPatient: true,
      reportsGenerated: true,
      criticalAlerts: true,
      tone: 'Medical Chime (Default)',
      volume: 80
    };
  });

  // Language state
  const [language, setLanguage] = usePersistentState('medix_set_lang', 'en');

  // Security 2FA toggle state
  const [twoFactor, setTwoFactor] = useState(true);

  useEffect(() => {
    if (darkMode) {
      document.body.classList.remove('light-mode');
    } else {
      document.body.classList.add('light-mode');
    }
  }, [darkMode]);

  const tabs = [
    { id: 'profile', label: 'Profile Settings', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'language', label: 'Language', icon: Globe },
    { id: 'privacy', label: 'Privacy', icon: Shield },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'theme', label: 'Theme', icon: darkMode ? Moon : Sun },
    { id: 'account', label: 'Account', icon: CreditCard },
  ];

  const handleInputChange = (field: string, value: any) => {
    setIsDirty(true);
    setSaveSuccess(false);
    if (activeTab === 'profile') {
      setProfileData((prev: any) => ({ ...prev, [field]: value }));
    }
  };

  const handleNotificationChange = (field: string, value: any) => {
    setIsDirty(true);
    setSaveSuccess(false);
    setNotifications((prev: any) => ({ ...prev, [field]: value }));
  };

  const loadInitialProfile = () => {
    try {
      const userStr = localStorage.getItem('medix_user');
      if (userStr) {
        const user = JSON.parse(userStr);
        return {
          fullName: user.fullName || user.full_name || 'Medical Professional',
          email: user.email || '',
          phone: user.phone || '',
          hospital: user.hospital || (user.role === 'hospital' ? (user.fullName || user.full_name || 'Hospital') : ''),
          regNumber: user.regNumber || user.reg_number || '',
          specialization: user.specialization || ''
        };
      }
    } catch (e) {}
    
    return {
      fullName: 'Dr. Sarah Connor, MD',
      email: 'sarah.connor@hospital.org',
      phone: '+1 (555) 123-4567',
      hospital: 'Apollo General & Research Hospital',
      regNumber: 'MED-REG-2024-88912',
      specialization: 'Infectious Diseases & Antimicrobial Resistance'
    };
  };

  const handleSave = () => {
    setIsSaving(true);
    setTimeout(() => {
      // Save profile data to localStorage
      try {
        const userStr = localStorage.getItem('medix_user');
        const user = userStr ? JSON.parse(userStr) : {};
        const updatedUser = {
          ...user,
          fullName: profileData.fullName,
          full_name: profileData.fullName,
          email: profileData.email,
          phone: profileData.phone,
          hospital: profileData.hospital,
          regNumber: profileData.regNumber,
          specialization: profileData.specialization
        };
        localStorage.setItem('medix_user', JSON.stringify(updatedUser));
        
        // Dispatch custom event to trigger navbar update
        window.dispatchEvent(new Event('medix_user_updated'));
      } catch (e) {
        console.error("Failed to save profile", e);
      }

      // Save notification settings to localStorage
      localStorage.setItem('medix_notifications', JSON.stringify(notifications));

      setIsSaving(false);
      setIsDirty(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    }, 800);
  };

  const handleCancel = () => {
    setIsDirty(false);
    setSaveSuccess(false);
    
    // Reset to last saved states
    if (activeTab === 'profile') {
      setProfileData(loadInitialProfile());
    } else if (activeTab === 'notifications') {
      try {
        const stored = localStorage.getItem('medix_notifications');
        if (stored) {
          setNotifications(JSON.parse(stored));
        }
      } catch (e) {}
    }
  };

  return (
    <div className="flex-col gap-2 w-full">
      <BackButton />
      
      {saveSuccess && (
        <div className="animate-fade-in mb-3 p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 flex items-center gap-2 px-4 shadow-lg">
          <CheckCircle2 size={18} />
          <span>Settings saved successfully! Changes are now live across your clinical profile.</span>
        </div>
      )}

      <div className="flex gap-4" style={{ minHeight: 'calc(100vh - 120px)' }}>
        {/* Sidebar Tabs */}
        <GlassCard className="flex-col gap-2 no-blur" style={{ width: '280px', padding: '16px', background: 'var(--color-card-bg)' }}>
          <div className="flex items-center justify-between mb-3 px-2">
            <h3 className="m-0 font-bold text-lg">Settings</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">v3.2</span>
          </div>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setIsDirty(false);
              }}
              className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </GlassCard>

        {/* Content Area */}
        <div className="flex-1">
          <GlassCard className="h-full">
            
            {/* 1. PROFILE SETTINGS */}
            {activeTab === 'profile' && (
              <div className="animate-fade-in">
                <div className="settings-header">
                  <div>
                    <h3 className="m-0 text-xl font-bold">Profile Settings 👤</h3>
                    <p className="text-sm text-secondary m-0 mt-1">Manage your clinical profile, organization credentials, and public specialization.</p>
                  </div>
                  <button 
                    className="btn btn-outline flex items-center gap-2"
                    onClick={() => setIsDirty(true)}
                  >
                    <Edit3 size={16} />
                    Edit Profile
                  </button>
                </div>

                {/* Top Layout: Avatar + Name + Badge + Action */}
                <div className="profile-hero">
                  <div className="profile-avatar-large">
                    <span>SC</span>
                    <div className="avatar-camera-overlay">
                      <Camera size={22} />
                      <span>Change</span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-[220px]">
                    <h2 className="m-0 text-2xl font-bold tracking-tight">{profileData.fullName}</h2>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <span className="status-badge role">
                        <Award size={14} /> Doctor & Specialist
                      </span>
                      <span className="status-badge enabled">
                        <CheckCircle2 size={13} /> Verified Medical License
                      </span>
                    </div>
                    <p className="text-sm text-secondary m-0 mt-3 flex items-center gap-1.5">
                      <Building2 size={15} className="text-accent-primary" />
                      {profileData.hospital} • Clinical Staff ID: <strong className="text-primary font-mono">DOC-8891</strong>
                    </p>
                  </div>
                </div>

                {/* Below that, a two-column form */}
                <div className="settings-card">
                  <h4 className="m-0 mb-4 text-base font-bold flex items-center gap-2 border-b border-white/10 pb-3">
                    <User size={18} className="text-accent-primary" />
                    Personal Information
                  </h4>
                  <div className="settings-form-grid">
                    <div className="form-group">
                      <label><User size={15} /> Full Name</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={profileData.fullName} 
                        onChange={e => handleInputChange('fullName', e.target.value)} 
                      />
                    </div>
                    <div className="form-group">
                      <label><Mail size={15} /> Email</label>
                      <input 
                        type="email" 
                        className="form-input" 
                        value={profileData.email} 
                        onChange={e => handleInputChange('email', e.target.value)} 
                      />
                    </div>
                    <div className="form-group">
                      <label><Phone size={15} /> Phone Number</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={profileData.phone} 
                        onChange={e => handleInputChange('phone', e.target.value)} 
                      />
                    </div>
                    <div className="form-group">
                      <label><Building2 size={15} /> Hospital / Clinic</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={profileData.hospital} 
                        onChange={e => handleInputChange('hospital', e.target.value)} 
                      />
                    </div>
                    <div className="form-group">
                      <label><FileText size={15} /> Medical Registration Number</label>
                      <input 
                        type="text" 
                        className="form-input font-mono" 
                        value={profileData.regNumber} 
                        onChange={e => handleInputChange('regNumber', e.target.value)} 
                      />
                    </div>
                    <div className="form-group">
                      <label><Award size={15} /> Specialization</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={profileData.specialization} 
                        onChange={e => handleInputChange('specialization', e.target.value)} 
                      />
                    </div>
                  </div>
                </div>

                {/* Sticky Save Bar at Bottom */}
                {isDirty && (
                  <div className="sticky-save-bar">
                    <div className="flex items-center gap-2.5">
                      <AlertCircle className="text-amber-400" size={20} />
                      <span className="font-medium text-sm">You have unsaved edits in your profile. Don't forget to save!</span>
                    </div>
                    <div className="flex gap-3">
                      <button className="btn btn-outline px-5 py-2 text-sm" onClick={handleCancel}>
                        Cancel
                      </button>
                      <button className="btn btn-primary px-6 py-2 text-sm flex items-center gap-2" onClick={handleSave} disabled={isSaving}>
                        {isSaving ? (
                          <>
                            <RefreshCw size={14} className="animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Check size={16} />
                            Save Changes
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 2. NOTIFICATIONS */}
            {activeTab === 'notifications' && (
              <div className="animate-fade-in">
                <div className="settings-header">
                  <div>
                    <h3 className="m-0 text-xl font-bold">Notifications 🔔</h3>
                    <p className="text-sm text-secondary m-0 mt-1">Configure email alerts, clinical reports triggers, and acoustic audio tones.</p>
                  </div>
                </div>

                {/* Email Notifications Card */}
                <div className="settings-card">
                  <h4 className="m-0 mb-4 text-base font-bold flex items-center gap-2 border-b border-white/10 pb-3">
                    <Mail size={18} className="text-accent-primary" />
                    Email Notifications
                  </h4>

                  <div 
                    className="notification-item"
                    onClick={() => handleNotificationChange('newPatient', !notifications.newPatient)}
                  >
                    <div>
                      <h5 className="m-0 text-base font-semibold">New patient created</h5>
                      <p className="m-0 text-sm text-secondary mt-1">Receive automated email notification whenever a new patient case is registered in your AMR department.</p>
                    </div>
                    <div className={`custom-checkbox ${notifications.newPatient ? 'checked' : ''}`}>
                      {notifications.newPatient && <Check size={16} strokeWidth={3} />}
                    </div>
                  </div>

                  <div 
                    className="notification-item"
                    onClick={() => handleNotificationChange('reportsGenerated', !notifications.reportsGenerated)}
                  >
                    <div>
                      <h5 className="m-0 text-base font-semibold">Reports generated</h5>
                      <p className="m-0 text-sm text-secondary mt-1">Get notified immediately when AI resistance mapping and AST susceptibility reports are finalized.</p>
                    </div>
                    <div className={`custom-checkbox ${notifications.reportsGenerated ? 'checked' : ''}`}>
                      {notifications.reportsGenerated && <Check size={16} strokeWidth={3} />}
                    </div>
                  </div>

                  <div 
                    className="notification-item"
                    onClick={() => handleNotificationChange('criticalAlerts', !notifications.criticalAlerts)}
                  >
                    <div>
                      <h5 className="m-0 text-base font-semibold">Critical AMR resistance detected</h5>
                      <p className="m-0 text-sm text-secondary mt-1">High-priority alert triggered when a multi-drug resistant pathogen is identified in lab samples.</p>
                    </div>
                    <div className={`custom-checkbox ${notifications.criticalAlerts ? 'checked' : ''}`}>
                      {notifications.criticalAlerts && <Check size={16} strokeWidth={3} />}
                    </div>
                  </div>
                </div>

                {/* Sound Card */}
                <div className="settings-card">
                  <h4 className="m-0 mb-4 text-base font-bold flex items-center gap-2 border-b border-white/10 pb-3">
                    <Volume2 size={18} className="text-accent-primary" />
                    Sound & Acoustic Alerts
                  </h4>

                  <div className="form-group mb-5 max-w-md">
                    <label>Notification Tone</label>
                    <select 
                      className="form-select"
                      value={notifications.tone}
                      onChange={e => handleNotificationChange('tone', e.target.value)}
                    >
                      <option value="Medical Chime (Default)">Medical Chime (Default)</option>
                      <option value="Soft Pulse">Soft Pulse</option>
                      <option value="Urgent Clinical Bell">Urgent Clinical Bell</option>
                      <option value="Subtle Beep">Subtle Beep</option>
                      <option value="Silent">Silent (No Audio)</option>
                    </select>
                  </div>

                  <div className="form-group max-w-lg">
                    <div className="flex justify-between items-center">
                      <label><Volume2 size={15} /> Volume</label>
                      <span className="font-mono text-sm text-accent-primary font-bold">{notifications.volume}%</span>
                    </div>
                    <div className="volume-slider-container">
                      <VolumeX size={16} className="text-secondary" />
                      <input 
                        type="range" 
                        min="0" 
                        max="100" 
                        value={notifications.volume}
                        onChange={e => handleNotificationChange('volume', parseInt(e.target.value))}
                        className="volume-slider" 
                      />
                      <Volume2 size={18} className="text-accent-primary" />
                    </div>
                  </div>
                </div>

                {isDirty && (
                  <div className="sticky-save-bar">
                    <div className="flex items-center gap-2.5">
                      <AlertCircle className="text-amber-400" size={20} />
                      <span className="font-medium text-sm">You have unsaved notification preferences.</span>
                    </div>
                    <div className="flex gap-3">
                      <button className="btn btn-outline px-5 py-2 text-sm" onClick={handleCancel}>Cancel</button>
                      <button className="btn btn-primary px-6 py-2 text-sm flex items-center gap-2" onClick={handleSave} disabled={isSaving}>
                        {isSaving ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 3. LANGUAGE */}
            {activeTab === 'language' && (
              <div className="animate-fade-in">
                <div className="settings-header">
                  <div>
                    <h3 className="m-0 text-xl font-bold">Language 🌍</h3>
                    <p className="text-sm text-secondary m-0 mt-1">Select your preferred application language for clinical terminology and patient reports.</p>
                  </div>
                </div>

                <div className="settings-card max-w-2xl">
                  <div className="form-group mb-6">
                    <label className="mb-2">Application Language Dropdown</label>
                    <select 
                      className="form-select text-base py-3 font-medium"
                      value={language}
                      onChange={e => {
                        setLanguage(e.target.value);
                        setIsDirty(true);
                      }}
                    >
                      <option value="en">English (United States / Standard Medical)</option>
                      <option value="bn">বাংলা (Bengali - Clinical & Patient Interface)</option>
                      <option value="hi">हिन्दी (Hindi - Dashboard & Reports)</option>
                    </select>
                  </div>

                  <h5 className="text-sm uppercase tracking-wider text-secondary font-bold mb-3">Quick Visual Select</h5>
                  
                  <div 
                    className={`language-card ${language === 'en' ? 'selected' : ''}`}
                    onClick={() => { setLanguage('en'); setIsDirty(true); }}
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-2xl">🇬🇧</span>
                      <div>
                        <h4 className="m-0 text-base font-bold">English</h4>
                        <p className="m-0 text-xs text-secondary mt-0.5">International Clinical & Laboratory Standard</p>
                      </div>
                    </div>
                    {language === 'en' && <span className="status-badge active"><Check size={14} /> Selected</span>}
                  </div>

                  <div 
                    className={`language-card ${language === 'bn' ? 'selected' : ''}`}
                    onClick={() => { setLanguage('bn'); setIsDirty(true); }}
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-2xl">🇧🇩</span>
                      <div>
                        <h4 className="m-0 text-base font-bold">বাংলা</h4>
                        <p className="m-0 text-xs text-secondary mt-0.5">রোগী ও ক্লিনিক্যাল ড্যাশবোর্ড ইন্টারফেস</p>
                      </div>
                    </div>
                    {language === 'bn' && <span className="status-badge active"><Check size={14} /> Selected</span>}
                  </div>

                  <div 
                    className={`language-card ${language === 'hi' ? 'selected' : ''}`}
                    onClick={() => { setLanguage('hi'); setIsDirty(true); }}
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-2xl">🇮🇳</span>
                      <div>
                        <h4 className="m-0 text-base font-bold">हिन्दी</h4>
                        <p className="m-0 text-xs text-secondary mt-0.5">नैदानिक डैशबोर्ड और एएमआर रिपोर्टिंग</p>
                      </div>
                    </div>
                    {language === 'hi' && <span className="status-badge active"><Check size={14} /> Selected</span>}
                  </div>
                </div>

                {isDirty && (
                  <div className="sticky-save-bar">
                    <div className="flex items-center gap-2.5">
                      <AlertCircle className="text-amber-400" size={20} />
                      <span className="font-medium text-sm">Language settings modified. Apply changes?</span>
                    </div>
                    <div className="flex gap-3">
                      <button className="btn btn-outline px-5 py-2 text-sm" onClick={handleCancel}>Cancel</button>
                      <button className="btn btn-primary px-6 py-2 text-sm" onClick={handleSave}>Save Changes</button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 4. PRIVACY */}
            {activeTab === 'privacy' && (
              <div className="animate-fade-in">
                <div className="settings-header">
                  <div>
                    <h3 className="m-0 text-xl font-bold">Privacy & Compliance 🛡️</h3>
                    <p className="text-sm text-secondary m-0 mt-1">Manage patient data anonymization, telemetry, and medical data sharing protocols.</p>
                  </div>
                </div>

                <div className="security-card-grid">
                  <div className="settings-card">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="m-0 font-bold flex items-center gap-2"><Shield size={18} className="text-emerald-400" /> Patient Anonymization</h4>
                      <span className="status-badge enabled">🟢 Active</span>
                    </div>
                    <p className="text-sm text-secondary mb-4">All patient names and national IDs are automatically scrubbed via HIPAA/GDPR compliant hashing before AST AI model inference.</p>
                    <button className="btn btn-outline w-full text-sm">Review Privacy Log</button>
                  </div>

                  <div className="settings-card">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="m-0 font-bold flex items-center gap-2"><Sparkles size={18} className="text-cyan-400" /> AI Diagnostic Telemetry</h4>
                      <span className="status-badge active">🟢 Opted In</span>
                    </div>
                    <p className="text-sm text-secondary mb-4">Contribute de-identified regional resistance metrics to global WHO/CDC AMR surveillance networks.</p>
                    <button className="btn btn-outline w-full text-sm">Configure Telemetry</button>
                  </div>
                </div>
              </div>
            )}

            {/* 5. SECURITY */}
            {activeTab === 'security' && (
              <div className="animate-fade-in">
                <div className="settings-header">
                  <div>
                    <h3 className="m-0 text-xl font-bold">Security 🛡️</h3>
                    <p className="text-sm text-secondary m-0 mt-1">Protect your medical account with multi-factor authentication, session monitors, and password policies.</p>
                  </div>
                </div>

                {/* Divided into 4 premium cards */}
                <div className="security-card-grid">
                  
                  {/* Card 1: Password */}
                  <div className="settings-card flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="m-0 font-bold text-base flex items-center gap-2">
                          <Key size={18} className="text-amber-400" />
                          Password
                        </h4>
                        <span className="text-xs text-secondary font-mono">Last changed: 30 days ago</span>
                      </div>
                      <p className="text-sm text-secondary m-0 mb-6">We recommend rotating clinical passwords every 90 days to maintain hospital network security compliance.</p>
                    </div>
                    <div>
                      <button 
                        className="btn btn-outline w-full py-2.5 text-sm font-semibold flex items-center justify-center gap-2"
                        onClick={() => alert('Password update modal initiated.')}
                      >
                        <RefreshCw size={15} />
                        Change Password
                      </button>
                    </div>
                  </div>

                  {/* Card 2: Two Factor Authentication */}
                  <div className="settings-card flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="m-0 font-bold text-base flex items-center gap-2">
                          <Smartphone size={18} className="text-emerald-400" />
                          Two Factor Authentication
                        </h4>
                        <span className={`status-badge ${twoFactor ? 'enabled' : 'warning'}`}>
                          {twoFactor ? '🟢 Enabled' : '🟡 Disabled'}
                        </span>
                      </div>
                      <p className="text-sm text-secondary m-0 mb-6">Add an extra layer of biometric or TOTP authenticator protection when accessing patient medical records.</p>
                    </div>
                    <div>
                      <button 
                        className="btn btn-primary w-full py-2.5 text-sm font-semibold flex items-center justify-center gap-2"
                        onClick={() => setTwoFactor(!twoFactor)}
                      >
                        <Lock size={15} />
                        Configure
                      </button>
                    </div>
                  </div>

                  {/* Card 3: Login Activity */}
                  <div className="settings-card md:col-span-2">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="m-0 font-bold text-base flex items-center gap-2">
                        <Activity size={18} className="text-cyan-400" />
                        Login Activity
                      </h4>
                      <span className="text-xs text-secondary">Monitoring active device sessions</span>
                    </div>
                    <p className="text-sm text-secondary m-0 mb-4">Recent devices and locations where your Medix AI credentials have been utilized.</p>

                    <div className="flex flex-col gap-2">
                      <div className="device-item">
                        <div className="flex items-center gap-3">
                          <Monitor className="text-secondary" size={22} />
                          <div>
                            <h5 className="m-0 text-sm font-bold">Windows • Kolkata</h5>
                            <p className="m-0 text-xs text-secondary mt-0.5">IP: 192.168.1.42 • Yesterday at 4:15 PM • Apollo Lab Workstation</p>
                          </div>
                        </div>
                        <span className="text-xs text-secondary font-mono">Offline</span>
                      </div>

                      <div className="device-item border-cyan-500/30 bg-cyan-500/5">
                        <div className="flex items-center gap-3">
                          <Globe className="text-accent-primary" size={22} />
                          <div>
                            <h5 className="m-0 text-sm font-bold flex items-center gap-2">
                              Chrome • Today • Active
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-400/20 text-cyan-300 font-bold uppercase">This Device</span>
                            </h5>
                            <p className="m-0 text-xs text-secondary mt-0.5">IP: 192.168.1.108 • Kolkata, India • Active right now</p>
                          </div>
                        </div>
                        <span className="status-badge enabled py-1 px-2.5 text-xs">🟢 Active</span>
                      </div>
                    </div>
                  </div>

                  {/* Card 4: Session Protections & Auto-Lock */}
                  <div className="settings-card md:col-span-2">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="m-0 font-bold text-base flex items-center gap-2">
                        <ShieldAlert size={18} className="text-purple-400" />
                        Clinical Session Protections
                      </h4>
                      <span className="status-badge active">🟢 Protected (15m auto-lock)</span>
                    </div>
                    <p className="text-sm text-secondary m-0 mb-4">When left unattended, your session will automatically lock after 15 minutes of inactivity to protect sensitive patient diagnosis data.</p>
                    <div className="flex justify-end">
                      <button className="btn btn-outline text-sm py-2 px-4">Manage Auto-Lock Policies</button>
                    </div>
                  </div>

                </div>
              </div>
            )}

            {/* 6. THEME */}
            {activeTab === 'theme' && (
              <div className="animate-fade-in">
                <div className="settings-header">
                  <div>
                    <h3 className="m-0 text-xl font-bold">Theme 🎨</h3>
                    <p className="text-sm text-secondary m-0 mt-1">Show visual cards instead of text. Customize the dashboard visual atmosphere.</p>
                  </div>
                </div>

                <div className="theme-grid max-w-4xl">
                  {/* Light Theme Card */}
                  <div 
                    className={`theme-preview-card ${!darkMode ? 'selected' : ''}`}
                    onClick={() => setDarkMode(false)}
                  >
                    <div className="theme-preview-window theme-preview-light">
                      <div className="mini-navbar bg-slate-200 border border-slate-300">
                        <div className="w-3 h-3 rounded-full bg-cyan-500"></div>
                        <div className="w-16 h-2 rounded bg-slate-400"></div>
                      </div>
                      <div className="flex gap-2 flex-1">
                        <div className="mini-sidebar bg-slate-200 border border-slate-300"></div>
                        <div className="mini-content">
                          <div className="mini-box bg-white border border-slate-200 shadow-sm"></div>
                          <div className="mini-box bg-cyan-50 border border-cyan-200"></div>
                        </div>
                      </div>
                    </div>
                    <div className="p-5 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Sun className={!darkMode ? 'text-amber-500' : 'text-secondary'} size={24} />
                        <div>
                          <h4 className="m-0 text-base font-bold">☀️ Light</h4>
                          <p className="m-0 text-xs text-secondary mt-0.5">High contrast, clean daytime medical theme</p>
                        </div>
                      </div>
                      {!darkMode && <span className="status-badge active"><Check size={14} /> Active</span>}
                    </div>
                  </div>

                  {/* Dark Theme Card */}
                  <div 
                    className={`theme-preview-card ${darkMode ? 'selected-dark' : ''}`}
                    onClick={() => setDarkMode(true)}
                  >
                    <div className="theme-preview-window theme-preview-dark">
                      <div className="mini-navbar bg-slate-800 border border-slate-700">
                        <div className="w-3 h-3 rounded-full bg-cyan-400"></div>
                        <div className="w-16 h-2 rounded bg-slate-600"></div>
                      </div>
                      <div className="flex gap-2 flex-1">
                        <div className="mini-sidebar bg-slate-800 border border-slate-700"></div>
                        <div className="mini-content">
                          <div className="mini-box bg-slate-900 border border-slate-800"></div>
                          <div className="mini-box bg-cyan-950/40 border border-cyan-800/40"></div>
                        </div>
                      </div>
                    </div>
                    <div className="p-5 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Moon className={darkMode ? 'text-purple-400' : 'text-secondary'} size={24} />
                        <div>
                          <h4 className="m-0 text-base font-bold">🌙 Dark</h4>
                          <p className="m-0 text-xs text-secondary mt-0.5">Sleek, eye-soothing dark telemetry aesthetic</p>
                        </div>
                      </div>
                      {darkMode && <span className="status-badge role"><Check size={14} /> Active</span>}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 7. ACCOUNT */}
            {activeTab === 'account' && (
              <div className="animate-fade-in">
                <div className="settings-header">
                  <div>
                    <h3 className="m-0 text-xl font-bold">Account ⚙️</h3>
                    <p className="text-sm text-secondary m-0 mt-1">Manage subscription plans, license renewals, and danger zone actions.</p>
                  </div>
                </div>

                {/* Subscription Card */}
                <div className="settings-card">
                  <div className="flex items-center justify-between flex-wrap gap-4 mb-4 pb-4 border-b border-white/10">
                    <div>
                      <h4 className="m-0 text-lg font-bold flex items-center gap-2">
                        <CreditCard size={20} className="text-accent-primary" />
                        Subscription
                      </h4>
                      <p className="text-sm text-secondary m-0 mt-1">Hospital Enterprise & Clinical AI Research License</p>
                    </div>
                    <span className="status-badge role text-sm px-4 py-1.5 font-bold shadow-lg shadow-cyan-500/20">
                      ⚡ Plan: Professional
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 my-6">
                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-xs uppercase tracking-wider text-secondary font-bold">Status</span>
                      <div className="mt-1 flex items-center gap-2 font-bold text-emerald-400 text-lg">
                        <CheckCircle2 size={18} /> Active License
                      </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-xs uppercase tracking-wider text-secondary font-bold">Renewal Date</span>
                      <div className="mt-1 font-bold text-primary text-lg font-mono">December 31, 2026</div>
                    </div>
                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-xs uppercase tracking-wider text-secondary font-bold">AI Quota</span>
                      <div className="mt-1 font-bold text-cyan-400 text-lg">Unlimited AST Maps</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between flex-wrap gap-4 pt-2">
                    <p className="text-sm text-secondary m-0">Includes priority WHO AMR database sync and 24/7 dedicated medical support.</p>
                    <button 
                      className="btn btn-primary px-6 py-2.5 font-bold shadow-lg shadow-cyan-500/20 flex items-center gap-2"
                      onClick={() => alert('Redirecting to Medix AI Enterprise billing portal...')}
                    >
                      <Sparkles size={16} />
                      Upgrade Button
                    </button>
                  </div>
                </div>

                {/* Danger Zone Red Card */}
                <div className="danger-card mt-8">
                  <div className="flex items-center gap-3 mb-2">
                    <ShieldAlert size={24} className="text-red-500 animate-pulse" />
                    <h4 className="m-0 text-lg font-bold text-red-500">Danger Zone</h4>
                  </div>
                  <p className="text-sm text-secondary m-0 mb-6">
                    These actions are irreversible and will affect your access to patient medical records and diagnostic models. Please proceed with caution.
                  </p>

                  <div className="flex flex-col gap-2">
                    <div className="danger-item">
                      <div>
                        <h5 className="m-0 text-base font-bold text-primary">Logout Everywhere</h5>
                        <p className="m-0 text-sm text-secondary mt-1">Revoke access from all active clinical workstations, mobile devices, and browser sessions.</p>
                      </div>
                      <button 
                        className="btn-warning"
                        onClick={() => alert('Logged out from all remote devices.')}
                      >
                        <LogOut size={16} />
                        Logout Everywhere
                      </button>
                    </div>

                    <div className="danger-item">
                      <div>
                        <h5 className="m-0 text-base font-bold text-primary">Deactivate Account</h5>
                        <p className="m-0 text-sm text-secondary mt-1">Temporarily disable your clinical profile and suspend incoming AMR alerts without losing records.</p>
                      </div>
                      <button 
                        className="btn-danger-outline"
                        onClick={() => alert('Account deactivation requested.')}
                      >
                        <UserX size={16} />
                        Deactivate Account
                      </button>
                    </div>

                    <div className="danger-item">
                      <div>
                        <h5 className="m-0 text-base font-bold text-red-400">Delete Account</h5>
                        <p className="m-0 text-sm text-secondary mt-1">Permanently erase your account, medical presets, and personal data from Medix AI servers.</p>
                      </div>
                      <button 
                        className="btn-danger"
                        onClick={() => {
                          if (confirm('Are you absolutely sure you want to delete your clinical account? This cannot be undone.')) {
                            alert('Account marked for permanent deletion.');
                          }
                        }}
                      >
                        <Trash2 size={16} />
                        Delete Account
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </GlassCard>
        </div>
      </div>
    </div>
  );
}
