import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Stethoscope, Dna, Activity, Lock, Mail, User, Hash, CheckCircle, ShieldCheck, AlertCircle, RefreshCw, ArrowLeft, Key } from 'lucide-react';
import './Login.css';
import { GlassCard } from '../components/GlassCard';
import { setAuthToken, API_BASE } from '../lib/api';
import logoImg from '../assets/logo.png';

export function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [userType, setUserType] = useState<'doctor' | 'hospital'>('doctor');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [regNumber, setRegNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Verification step state for Signup
  const [signupStep, setSignupStep] = useState<'details' | 'otp'>('details');
  const [otpCode, setOtpCode] = useState('');

  const navigate = useNavigate();

  const handleToggleMode = (loginMode: boolean) => {
    setIsLogin(loginMode);
    setSignupStep('details');
    setAuthError(null);
    setOtpCode('');
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) {
      setAuthError("Password should be at least 6 characters.");
      return;
    }
    setLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          fullName,
          role: userType,
          regNumber
        })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.status === 'success') {
        setSignupStep('otp');
      } else {
        setAuthError(data.detail || 'Failed to send verification code. Please check your inputs.');
      }
    } catch (err) {
      console.error(err);
      setAuthError('Network or server error while connecting to verification service.');
    } finally {
      setLoading(false);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAuthError(null);
    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/signup';
      const bodyPayload = isLogin ? {
        email,
        password,
        userType
      } : {
        email,
        password,
        fullName,
        role: userType,
        regNumber,
        otpCode
      };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyPayload)
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.access_token) {
          setAuthToken(data.access_token);
          if (data.user) {
            localStorage.setItem('medix_user', JSON.stringify(data.user));
          }
        }
        navigate('/dashboard');
      } else {
        const err = await res.json().catch(() => ({}));
        setAuthError(err.detail || 'Invalid email or password. You can also use "⚡ One-Click Demo Login" below.');
      }
    } catch (err) {
      console.error(err);
      setAuthError('Connection error to backend server (http://localhost:8080). You can also click "⚡ One-Click Demo Login" below.');
    } finally {

      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-left">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <img src={logoImg} alt="Medix AI Logo" className="logo-icon" style={{ height: '48px', width: 'auto' }} />
          <h2 className="hero-heading" style={{ fontSize: '2rem', margin: 0 }}>MEDIX AI</h2>
        </div>
        
        <div className="illustration-container">
          <div className="dna-animation">
            <Dna size={320} strokeWidth={1} color="var(--color-ai-accent)" className="dna-large-animate" />
          </div>
          <div className="floating-icons">
            <Activity className="icon-pulse text-accent-primary" size={48} />
          </div>
          <h1 className="hero-heading" style={{ marginTop: '3rem', fontSize: '3.5rem' }}>
            The Future of Healthcare,<br />Powered by AI.
          </h1>
          <p className="text-secondary" style={{ marginTop: '1rem', fontSize: '1.2rem', maxWidth: '80%' }}>
            Enterprise-grade precision. World-class experience.
          </p>
        </div>
      </div>

      <div className="login-right">
        <GlassCard className="auth-card animate-slide-up">
          <div className="auth-toggle">
            <button 
              className={`toggle-btn ${isLogin ? 'active' : ''}`}
              onClick={() => handleToggleMode(true)}
              type="button"
            >
              Sign In
            </button>
            <button 
              className={`toggle-btn ${!isLogin ? 'active' : ''}`}
              onClick={() => handleToggleMode(false)}
              type="button"
            >
              Sign Up
            </button>
          </div>

          {authError && (
            <div className="auth-error-banner animate-slide-up">
              <AlertCircle size={18} className="error-icon" />
              <span>{authError}</span>
            </div>
          )}

          {!isLogin && signupStep === 'details' && (
            <div className="type-toggle">
              <button 
                className={`chip-btn ${userType === 'doctor' ? 'active' : ''}`}
                onClick={() => setUserType('doctor')}
                type="button"
              >
                Doctor
              </button>
              <button 
                className={`chip-btn ${userType === 'hospital' ? 'active' : ''}`}
                onClick={() => setUserType('hospital')}
                type="button"
              >
                Hospital
              </button>
            </div>
          )}

          {isLogin || signupStep === 'details' ? (
            <form onSubmit={isLogin ? handleAuth : handleSendOtp} className="auth-form">
              {!isLogin && userType === 'doctor' && (
                <>
                  <div className="input-group">
                    <label>Doctor Name</label>
                    <div className="input-wrapper">
                      <User size={18} className="input-icon" />
                      <input type="text" className="input-field with-icon" placeholder="Dr. John Doe" value={fullName} onChange={e => setFullName(e.target.value)} required />
                    </div>
                  </div>
                  <div className="input-group">
                    <label>Registration ID</label>
                    <div className="input-wrapper">
                      <Hash size={18} className="input-icon" />
                      <input type="text" className="input-field with-icon" placeholder="REG-12345" value={regNumber} onChange={e => setRegNumber(e.target.value)} required />
                    </div>
                  </div>
                </>
              )}

              {!isLogin && userType === 'hospital' && (
                <>
                  <div className="input-group">
                    <label>Hospital Name</label>
                    <div className="input-wrapper">
                      <User size={18} className="input-icon" />
                      <input type="text" className="input-field with-icon" placeholder="General Hospital" value={fullName} onChange={e => setFullName(e.target.value)} required />
                    </div>
                  </div>
                  <div className="input-group">
                    <label>Hospital ID</label>
                    <div className="input-wrapper">
                      <Hash size={18} className="input-icon" />
                      <input type="text" className="input-field with-icon" placeholder="HOSP-9876" value={regNumber} onChange={e => setRegNumber(e.target.value)} required />
                    </div>
                  </div>
                </>
              )}

              <div className="input-group">
                <label>{isLogin ? 'Email or UniqueID' : 'Institutional Email'}</label>
                <div className="input-wrapper">
                  <Mail size={18} className="input-icon" />
                  <input type="email" className="input-field with-icon" placeholder="enter@hospital.org" value={email} onChange={e => setEmail(e.target.value)} required />
                </div>
              </div>

              <div className="input-group">
                <label>Password</label>
                <div className="input-wrapper">
                  <Lock size={18} className="input-icon" />
                  <input type="password" className="input-field with-icon" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required />
                </div>
              </div>

              <button type="submit" className="btn btn-primary w-full" style={{ marginTop: '1rem' }} disabled={loading}>
                {loading ? 'Processing...' : (isLogin ? 'Login' : 'Verify Email & Continue')}
              </button>

              {isLogin && (
                <button
                  type="button"
                  className="btn btn-outline w-full"
                  style={{ marginTop: '0.5rem', borderColor: 'var(--color-accent-primary)', color: 'var(--color-accent-primary)' }}
                  onClick={() => {
                    const mockToken = "mock-dev-clinical-jwt-token";
                    const mockUser = {
                      id: "00000000-0000-0000-0000-000000000001",
                      email: email || "doctor@medix.ai",
                      role: userType,
                      fullName: "Dr. Clinical Reviewer",
                      regNumber: "MCI-2024-DEV"
                    };
                    setAuthToken(mockToken);
                    localStorage.setItem('medix_user', JSON.stringify(mockUser));
                    navigate('/dashboard');
                  }}
                >
                  ⚡ One-Click Demo Login
                </button>
              )}
            </form>

          ) : (
            /* Step 2: Verification Code Input */
            <form onSubmit={handleAuth} className="auth-form animate-slide-up">
              <div className="verify-header">
                <div className="verify-icon-wrapper">
                  <ShieldCheck size={36} className="text-accent-primary" />
                </div>
                <h3 className="verify-title">Verify Your Email</h3>
                <p className="verify-subtitle">
                  We sent a 6-digit code to <strong style={{ color: 'var(--color-accent-primary)' }}>{email}</strong>
                </p>
              </div>

              <div className="input-group" style={{ marginTop: '1.5rem' }}>
                <label>6-Digit Verification Code</label>
                <div className="input-wrapper">
                  <Key size={18} className="input-icon" />
                  <input
                    type="text"
                    className="input-field with-icon otp-input"
                    placeholder="123456"
                    maxLength={6}
                    value={otpCode}
                    onChange={e => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn btn-primary w-full" style={{ marginTop: '1.5rem' }} disabled={loading || otpCode.length < 6}>
                {loading ? 'Verifying...' : 'Verify & Create Account'}
              </button>

              <div className="verify-actions">
                <button
                  type="button"
                  className="btn-text-action"
                  onClick={handleSendOtp}
                  disabled={loading}
                >
                  <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                  <span>Resend Code</span>
                </button>
                <button
                  type="button"
                  className="btn-text-action"
                  onClick={() => { setSignupStep('details'); setAuthError(null); }}
                >
                  <ArrowLeft size={14} />
                  <span>Change Email</span>
                </button>
              </div>
            </form>
          )}
        </GlassCard>
      </div>
    </div>
  );
}


