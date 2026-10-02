import React, { useState, useEffect } from 'react';
import { Users, Brain, Pill, AlertTriangle, ArrowUpRight, ArrowDownRight, Clock, FileText, Loader2 } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { GlassCard } from '../components/GlassCard';
import { BackButton } from '../components/BackButton';
import { apiFetch } from '../lib/api';
import './Dashboard.css';

interface DashboardStats {
  patientsToday: { value: number; change: string };
  aiAnalysisDone: { value: number; change: string };
  antibioticsPrescribed: { value: number; change: string };
  highResistanceAlerts: { value: number; change: string };
}

interface DashboardAlert {
  id: string;
  time: string;
  text: string;
  type: 'warning' | 'danger';
}

interface DashboardActivity {
  id: string;
  time: string;
  text: string;
  type: string;
}

interface DashboardReport {
  case_id: string;
  case_code: string;
  title: string;
  subtitle: string;
  date: string;
}

const recoveryData = [
  { name: 'Mon', rate: 85 }, { name: 'Tue', rate: 88 }, { name: 'Wed', rate: 92 },
  { name: 'Thu', rate: 90 }, { name: 'Fri', rate: 95 }, { name: 'Sat', rate: 96 }, { name: 'Sun', rate: 98 },
];

const accuracyData = [
  { name: 'Week 1', acc: 92 }, { name: 'Week 2', acc: 94 }, { name: 'Week 3', acc: 95 }, { name: 'Week 4', acc: 98 },
];

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    patientsToday: { value: 0, change: '0%' },
    aiAnalysisDone: { value: 0, change: '0' },
    antibioticsPrescribed: { value: 0, change: '0' },
    highResistanceAlerts: { value: 0, change: '0' }
  });
  const [alerts, setAlerts] = useState<DashboardAlert[]>([]);
  const [activities, setActivities] = useState<DashboardActivity[]>([]);
  const [reports, setReports] = useState<DashboardReport[]>([]);
  const [recentCases, setRecentCases] = useState<any[]>([]);
  const [loadingCases, setLoadingCases] = useState(true);
  const [caseLimit, setCaseLimit] = useState(10);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const statsRes = await apiFetch('/api/dashboard/stats');
        if (statsRes.ok) {
          const data = await statsRes.json();
          if (data.stats) setStats(data.stats);
          if (Array.isArray(data.alerts)) setAlerts(data.alerts);
          if (Array.isArray(data.activities)) setActivities(data.activities);
          if (Array.isArray(data.reports)) setReports(data.reports);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard stats:", err);
      }
    }
    fetchDashboardData();
  }, []);

  useEffect(() => {
    async function fetchCases() {
      try {
        const res = await apiFetch('/api/cases?limit=' + caseLimit);
        if (res.ok) {
          const data = await res.json();
          setRecentCases(data.cases || []);
        }
      } catch (err) {
        console.error("Failed to fetch recent cases:", err);
      } finally {
        setLoadingCases(false);
      }
    }
    fetchCases();
  }, [caseLimit]);

  const statCards = [
    { title: 'Patients Today', value: stats.patientsToday.value, change: stats.patientsToday.change, icon: Users, color: 'var(--color-accent-primary)' },
    { title: 'AI Analysis Done', value: stats.aiAnalysisDone.value, change: stats.aiAnalysisDone.change, icon: Brain, color: 'var(--color-ai-accent)' },
    { title: 'Antibiotics Prescribed', value: stats.antibioticsPrescribed.value, change: stats.antibioticsPrescribed.change, icon: Pill, color: 'var(--color-success)' },
    { title: 'High Resistance Alerts', value: stats.highResistanceAlerts.value, change: stats.highResistanceAlerts.change, icon: AlertTriangle, color: 'var(--color-danger)' },
  ];

  return (
    <div className="dashboard-container">
      <BackButton />
      <div className="dashboard-header mb-4">
        <h2>Dashboard Overview</h2>
        <p className="text-secondary">Welcome back, {(() => {
          try {
            const userStr = localStorage.getItem('medix_user');
            if (userStr) {
              const user = JSON.parse(userStr);
              return user.fullName || user.full_name || 'Doctor';
            }
          } catch (e) {}
          return 'Doctor';
        })()}. Here's what's happening today.</p>
      </div>

      <div className="stats-grid">
        {statCards.map((stat, idx) => (
          <GlassCard key={idx} hoverEffect className="stat-card animate-slide-up" style={{ animationDelay: `${idx * 100}ms` }}>
            <div className="stat-header">
              <span className="stat-title">{stat.title}</span>
              <div className="stat-icon-wrapper" style={{ backgroundColor: `${stat.color}20`, color: stat.color }}>
                <stat.icon size={20} />
              </div>
            </div>
            <div className="stat-body">
              <span className="stat-value">{stat.value}</span>
              <span className={`stat-change ${stat.change.startsWith('+') ? 'text-success' : 'text-danger'}`}>
                {stat.change.startsWith('+') ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                {stat.change}
              </span>
            </div>
          </GlassCard>
        ))}
      </div>

      <div className="dashboard-main-grid">
        <div className="main-left flex-col gap-3">
          <GlassCard className="table-card animate-slide-up" style={{ animationDelay: '400ms' }}>
            <div className="card-header justify-between items-center flex mb-3">
              <h3>Recent Cases</h3>
              {caseLimit > 0 && (
                <button 
                  className="btn btn-outline" 
                  style={{ padding: '6px 12px', fontSize: '0.8rem', cursor: 'pointer' }}
                  onClick={() => setCaseLimit(0)}
                >
                  View All
                </button>
              )}
            </div>
            <div className="table-responsive">
              <table className="premium-table">
                <thead>
                  <tr>
                    <th>Patient</th>
                    <th>Symptoms</th>
                    <th>Recommendations</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingCases ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                        <Loader2 className="animate-spin" style={{ margin: '0 auto', color: 'var(--color-primary)' }} />
                      </td>
                    </tr>
                  ) : recentCases.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-secondary)' }}>
                        No recent cases found. Evaluate a new case to see it here.
                      </td>
                    </tr>
                  ) : recentCases.map((c, i) => {
                    const aiAnalysis = c.ai_analysis && c.ai_analysis.length > 0 ? c.ai_analysis[0] : null;
                    const recommendations = aiAnalysis 
                      ? (Array.isArray(aiAnalysis.recommended_antibiotics) 
                          ? aiAnalysis.recommended_antibiotics.map((a: any) => a.name).join(', ') 
                          : 'See Analysis') 
                      : 'Awaiting AI';
                    const symptomsStr = Array.isArray(c.symptoms) ? c.symptoms.join(', ') : (c.symptoms || 'None');
                    
                    return (
                    <tr key={i}>
                      <td>
                        <div className="patient-cell">
                          <span className="patient-id">#{c.id.toString().substring(0,8).toUpperCase()}</span>
                          <span className="patient-name">{c.patient_name || 'Unknown Patient'}</span>
                        </div>
                      </td>
                      <td><span className="truncate-text">{symptomsStr}</span></td>
                      <td>{recommendations}</td>
                      <td>
                        <span className={`badge ${c.status === 'Resolved' ? 'badge-success' : c.status === 'open' ? 'badge-warning' : 'badge-ai'}`}>
                          {c.status || 'open'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            className="btn btn-outline" 
                            style={{ padding: '4px 10px', fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap' }}
                            onClick={() => {
                              localStorage.setItem('medix_npc_patientName', JSON.stringify(c.patient_name || ''));
                              localStorage.setItem('medix_npc_patientAge', JSON.stringify(c.patient_age || 30));
                              localStorage.setItem('medix_npc_patientGender', JSON.stringify(c.patient_gender || ''));
                              if (c.symptoms) {
                                localStorage.setItem('medix_npc_selectedSymptoms', JSON.stringify(c.symptoms));
                              }
                              if (c.medical_history) {
                                localStorage.setItem('medix_npc_selectedMedicalHistory', JSON.stringify(c.medical_history));
                              }
                              if (c.allergies) {
                                localStorage.setItem('medix_npc_selectedAllergies', JSON.stringify(c.allergies));
                              }
                              // Navigate to the form without showing results yet so the doctor can edit
                              localStorage.setItem('medix_npc_showResults', JSON.stringify(false));
                              window.location.href = '/new-case';
                            }}
                          >
                            Reopen Case
                          </button>
                          
                          {aiAnalysis && (
                            <button 
                              className="btn btn-primary" 
                              style={{ padding: '4px 10px', fontSize: '0.75rem', cursor: 'pointer', whiteSpace: 'nowrap' }}
                              onClick={() => {
                                window.location.href = `/reports?caseId=${c.id}`;
                              }}
                            >
                              View Report
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )})}
                </tbody>
              </table>
            </div>
          </GlassCard>

          <div className="charts-grid">
            <GlassCard className="chart-card animate-slide-up" style={{ animationDelay: '500ms' }}>
              <h3 className="mb-3">Recovery Rate</h3>
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={recoveryData}>
                    <defs>
                      <linearGradient id="colorRate" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--color-success)" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="var(--color-success)" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis dataKey="name" stroke="var(--color-text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--color-text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                    <Area type="monotone" dataKey="rate" stroke="var(--color-success)" fillOpacity={1} fill="url(#colorRate)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </GlassCard>

            <GlassCard className="chart-card animate-slide-up" style={{ animationDelay: '600ms' }}>
              <h3 className="mb-3">AI Recommendation Accuracy</h3>
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={accuracyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                    <XAxis dataKey="name" stroke="var(--color-text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: '8px' }} />
                    <Bar dataKey="acc" fill="var(--color-ai-accent)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </GlassCard>
          </div>
        </div>

        <div className="main-right flex-col gap-3">
          <GlassCard className="animate-slide-up" style={{ animationDelay: '500ms' }}>
            <h3 className="mb-3 flex items-center gap-2">
              <AlertTriangle size={18} className="text-warning" /> AI Alerts
            </h3>
            <div className="timeline-container">
              {alerts.length === 0 ? (
                <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', padding: '0.5rem 0' }}>
                  No active high resistance or critical drug interaction alerts.
                </div>
              ) : (
                alerts.map((alt) => (
                  <div key={alt.id} className="timeline-item">
                    <div className={`timeline-dot ${alt.type}`}></div>
                    <div className="timeline-content">
                      <span className="time">{alt.time}</span>
                      <p>{alt.text}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard className="animate-slide-up" style={{ animationDelay: '600ms' }}>
            <h3 className="mb-3 flex items-center gap-2">
              <Clock size={18} className="text-accent-primary" /> Recent Activity
            </h3>
            <div className="timeline-container">
              {activities.length === 0 ? (
                <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', padding: '0.5rem 0' }}>
                  No recorded activity yet. Evaluate a case to see live updates.
                </div>
              ) : (
                activities.map((act) => (
                  <div key={act.id} className="timeline-item">
                    <div className="timeline-dot primary"></div>
                    <div className="timeline-content">
                      <span className="time">{act.time}</span>
                      <p>{act.text}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </GlassCard>

          <GlassCard className="animate-slide-up flex-col gap-2" style={{ animationDelay: '700ms' }}>
            <h3 className="mb-2 flex items-center gap-2">
              <FileText size={18} className="text-ai-accent" /> Recent AI Reports
            </h3>
            {reports.length === 0 ? (
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', padding: '0.5rem 0' }}>
                No AI reports generated yet.
              </div>
            ) : (
              reports.map((rep) => (
                <button 
                  key={rep.case_id} 
                  className="btn btn-glass justify-between w-full" 
                  style={{ padding: '10px 12px', textAlign: 'left', display: 'flex', alignItems: 'center' }}
                  onClick={() => {
                    window.location.href = `/reports?caseId=${rep.case_id}`;
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'hidden' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {rep.title}
                    </span>
                    <span className="text-secondary" style={{ fontSize: '0.75rem' }}>
                      {rep.subtitle}
                    </span>
                  </div>
                  <ArrowUpRight size={16} className="text-secondary" style={{ flexShrink: 0, marginLeft: '8px' }} />
                </button>
              ))
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
