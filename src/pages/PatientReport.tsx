import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Printer, Stethoscope, User, Activity, Loader2, AlertTriangle, Heart, Thermometer, Wind, ShieldAlert, Pill } from 'lucide-react';
import { GlassCard } from '../components/GlassCard';
import { BackButton } from '../components/BackButton';
import { VoiceAssistantController } from '../components/VoiceAssistantController';
import { usePersistentState } from '../hooks/usePersistentState';
import { apiFetch } from '../lib/api';
import './PatientReport.css';

interface VitalItem {
  label: string;
  value: string;
}

function parseList(val: any): string[] {
  if (!val) return [];
  if (Array.isArray(val)) {
    return val.map(item => (typeof item === 'string' ? item : JSON.stringify(item))).filter(Boolean);
  }
  if (typeof val === 'string') {
    const trimmed = val.trim();
    if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
      try {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed.filter(Boolean);
      } catch (e) {}
    }
    return trimmed.split(',').map(s => s.trim()).filter(Boolean);
  }
  return [];
}

export function PatientReport() {
  const [searchParams] = useSearchParams();
  const caseIdFromUrl = searchParams.get('caseId');
  
  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [notes, setNotes] = usePersistentState(
    'medix_pr_notes',
    'Patient evaluated with Medix AI. Recommendations reviewed and validated according to local AMR patterns.'
  );

  useEffect(() => {
    async function loadReport() {
      setLoading(true);
      setError(null);
      try {
        const targetCaseId = caseIdFromUrl || localStorage.getItem('medix_latest_case_id');
        let endpoint = targetCaseId ? `/api/cases/${targetCaseId}` : '/api/cases?limit=1';
        
        let res = await apiFetch(endpoint);
        
        // If specific ID fetch failed, fallback to latest case in DB
        if (!res.ok && targetCaseId) {
          res = await apiFetch('/api/cases?limit=1');
        }

        if (res.ok) {
          const data = await res.json();
          const targetCase = targetCaseId && !data.cases ? data : (data.cases && data.cases.length > 0 ? data.cases[0] : null);
          setCaseData(targetCase);
        } else {
          setError("Could not find the requested patient report.");
        }
      } catch (err: any) {
        console.error("Failed to load patient report:", err);
        setError("Error connecting to server to load patient report.");
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [caseIdFromUrl]);

  if (loading) {
    return (
      <div className="flex-col gap-4 items-center justify-center" style={{ minHeight: '400px' }}>
        <BackButton />
        <Loader2 className="animate-spin text-ai-accent" size={36} />
        <p className="text-secondary">Loading patient report from Supabase...</p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="flex-col gap-4">
        <BackButton />
        <GlassCard className="text-center p-4">
          <AlertTriangle size={32} className="text-warning mx-auto mb-2" />
          <h3>No Patient Report Found</h3>
          <p className="text-secondary">
            {error || "There are no patient cases available yet. Please evaluate a case from the 'New Patient Case' page."}
          </p>
          <button className="btn btn-primary mt-3" onClick={() => window.location.href = '/new-case'}>
            Evaluate New Case
          </button>
        </GlassCard>
      </div>
    );
  }

  const aiAnalysis = caseData.ai_analysis && caseData.ai_analysis.length > 0 ? caseData.ai_analysis[0] : null;
  const rawInfection = aiAnalysis ? aiAnalysis.predicted_infection : 'Clinical Evaluation Pending';
  const infectionName = rawInfection.includes('(') ? rawInfection.split('(')[0].trim() : rawInfection;
  const confidenceStr = rawInfection.includes('(') 
    ? rawInfection.split('(')[1].replace(')', '').trim() 
    : 'Clinical Assessment';

  const recommendations = aiAnalysis && Array.isArray(aiAnalysis.recommended_antibiotics) 
    ? aiAnalysis.recommended_antibiotics 
    : [];

  // Parse raw patient data
  const rawSymptoms = parseList(caseData.symptoms);
  const rawHistory = parseList(caseData.medical_history);
  const allergiesList = parseList(caseData.allergies);
  const previousAntibioticsList = parseList(caseData.previous_antibiotics);

  // Extract dynamically entered vitals, physical measurements, and conditions
  const recordedVitals: VitalItem[] = [];
  const chronicConditions: string[] = [];
  let recordedHeight = '';
  let recordedWeight = '';
  let recordedLocation = '';

  rawHistory.forEach((item: string) => {
    const colonIndex = item.indexOf(':');
    if (colonIndex !== -1) {
      const key = item.substring(0, colonIndex).trim();
      const val = item.substring(colonIndex + 1).trim();
      const lower = key.toLowerCase();

      if (lower === 'height') {
        recordedHeight = val.includes('cm') ? val : `${val} cm`;
      } else if (lower === 'weight') {
        recordedWeight = val.includes('kg') ? val : `${val} kg`;
      } else if (lower.includes('location')) {
        recordedLocation = val;
      } else if (val) {
        recordedVitals.push({ label: key, value: val });
      }
    } else {
      chronicConditions.push(item);
    }
  });

  // If vitals were entered in NewPatientCase during the active session and not in DB history, load them dynamically
  if (recordedVitals.length === 0) {
    try {
      const localVitalsStr = localStorage.getItem('medix_npc_vitals');
      if (localVitalsStr) {
        const parsed = JSON.parse(localVitalsStr);
        if (Array.isArray(parsed)) {
          parsed.forEach((v: any) => {
            if (v && v.value && String(v.value).trim()) {
              recordedVitals.push({ label: v.name, value: String(v.value).trim() });
            }
          });
        }
      }
    } catch (e) {}
  }

  // Same dynamic fallback for height/weight/location
  const cleanStored = (val: string | null) => {
    if (!val) return '';
    try {
      const parsed = JSON.parse(val);
      if (typeof parsed === 'string') return parsed.trim();
      return String(parsed).trim();
    } catch {
      return val.replace(/^["']|["']$/g, '').trim();
    }
  };

  if (!recordedHeight) {
    const h = cleanStored(localStorage.getItem('medix_npc_patientHeight'));
    if (h) recordedHeight = h.includes('cm') ? h : `${h} cm`;
  } else {
    recordedHeight = recordedHeight.replace(/["']/g, '').trim();
  }

  if (!recordedWeight) {
    const w = cleanStored(localStorage.getItem('medix_npc_patientWeight'));
    if (w) recordedWeight = w.includes('kg') ? w : `${w} kg`;
  } else {
    recordedWeight = recordedWeight.replace(/["']/g, '').trim();
  }

  if (!recordedLocation) {
    const loc = cleanStored(localStorage.getItem('medix_npc_patientLocation'));
    if (loc) recordedLocation = loc;
    else recordedLocation = 'Kolkata';
  } else {
    recordedLocation = recordedLocation.replace(/["']/g, '').trim();
  }

  // Dynamic gender
  let patientGender = caseData.patient_gender;
  if (!patientGender || patientGender === 'Unspecified') {
    const storedGender = localStorage.getItem('medix_npc_patientGender');
    if (storedGender && storedGender.trim()) {
      patientGender = storedGender.trim();
    } else {
      patientGender = 'Unspecified';
    }
  }

  const formattedDate = caseData.created_at 
    ? new Date(caseData.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'Recent';

  const caseCode = `CASE-${caseData.id ? caseData.id.toString().substring(0, 8).toUpperCase() : 'PENDING'}`;

  const getVitalIcon = (name: string) => {
    const l = name.toLowerCase();
    if ((l.includes('blood') || /\bbp\b/.test(l)) && !l.includes('pulse') && !l.includes('bpm')) return <Heart size={13} className="text-danger" />;
    if (l.includes('pulse') || l.includes('heart rate') || l.includes('bpm')) return <Activity size={13} className="text-ai-accent" />;
    if (l.includes('spo2') || l.includes('oxygen')) return <Wind size={13} className="text-info" />;
    if (l.includes('temp')) return <Thermometer size={13} className="text-warning" />;
    return <Activity size={13} className="text-secondary" />;
  };

  // Assemble complete voice payload targeting the strict clinical schema
  const voicePayload = {
    patient_name: caseData.patient_name || 'Patient',
    age_gender: `${caseData.patient_age || 'N/A'} Yrs / ${patientGender}`,
    case_reference: caseCode,
    registered_date: formattedDate,
    physical_measurements: [recordedHeight, recordedWeight].filter(Boolean).join(' • ') || undefined,
    hospital_location: recordedLocation || undefined,
    primary_condition: infectionName,
    diagnosis_confidence: confidenceStr,
    prescribed_antibiotics: recommendations.map((r: any) => ({
      drug_name: r.name,
      dosage_details: `${r.dosage || 'Standard dose'} • ${r.frequency || 'As advised'}`,
      duration: r.duration || 'Full course',
      local_resistance_pct: r.localResistance !== undefined ? `${r.localResistance}% Local Resistance` : undefined
    })),
    vitals: {
      blood_pressure: recordedVitals.find(v => {
        const l = v.label.toLowerCase();
        return (l.includes('blood') || /\bbp\b/.test(l)) && !l.includes('pulse') && !l.includes('bpm');
      })?.value,
      pulse_bpm: recordedVitals.find(v => {
        const l = v.label.toLowerCase();
        return (l.includes('pulse') || l.includes('heart') || l.includes('bpm')) && !l.includes('blood');
      })?.value,
      spo2_pct: recordedVitals.find(v => {
        const l = v.label.toLowerCase();
        return l.includes('spo2') || l.includes('oxygen');
      })?.value,
      temperature_f: recordedVitals.find(v => {
        const l = v.label.toLowerCase();
        return l.includes('temp');
      })?.value,
      respiratory_rate: recordedVitals.find(v => {
        const l = v.label.toLowerCase();
        return l.includes('resp');
      })?.value
    },
    symptoms: rawSymptoms,
    comorbidities: chronicConditions,
    allergies: allergiesList,
    previous_antibiotic_exposure: previousAntibioticsList.length > 0 ? previousAntibioticsList.join(', ') : 'No previous antibiotic treatments recorded',
    physician_notes: notes || undefined
  };

  return (
    <div className="flex-col gap-4 animate-fade-in printable-report-area">
      {/* Top action header - strictly hidden during printing */}
      <div className="no-print">
        <BackButton />
        <div className="flex justify-between items-center mb-3 mt-2 flex-wrap gap-2">
          <div>
            <h2 className="m-0">Patient Report</h2>
            <p className="text-secondary m-0">Case #{caseCode} - Real-time AI Analysis & AMR Surveillance</p>
          </div>
          <div className="flex gap-3">
            <button className="btn btn-outline flex items-center gap-2" onClick={() => window.print()}>
              <Printer size={18} /> Print Report
            </button>
          </div>
        </div>

        {/* ElevenLabs Multilingual Clinical Voice Assistant */}
        <VoiceAssistantController payload={voicePayload} />
      </div>

      {/* Official Medical Header - Visible ONLY at top of Page 1 in Print */}
      <div className="print-report-header">
        <div className="print-header-top">
          <div>
            <h1 className="print-header-title">MEDIX AI CLINICAL DECISION REPORT</h1>
            <p className="print-header-subtitle">Regional AMR Surveillance & AI Antimicrobial Stewardship</p>
          </div>
          <div className="print-header-meta">
            <div><strong>Case Ref:</strong> {caseCode}</div>
            <div><strong>Date:</strong> {formattedDate}</div>
            <div><strong>Location:</strong> {recordedLocation || 'Clinical Center'}</div>
          </div>
        </div>
      </div>

      {/* SECTIONS 1 & 2: PATIENT PROFILE & AI DIAGNOSIS */}
      <div className="grid-2-col gap-4">
        {/* SECTION 1: PATIENT PROFILE */}
        <GlassCard className="flex-col gap-4 printable-section-card">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <User className="text-accent-primary" size={20} />
              <h3 className="m-0">Patient Profile</h3>
            </div>
            <span className="badge badge-success capitalize">
              {caseData.status || 'Active'}
            </span>
          </div>
          
          {/* Real Patient Demographics */}
          <div className="grid-2-col gap-3">
            <div className="flex flex-col gap-1">
              <span className="text-secondary text-sm">Patient Name</span>
              <strong className="text-base text-white">{caseData.patient_name || 'Patient'}</strong>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-secondary text-sm">Age / Gender</span>
              <strong className="text-base text-white">
                {caseData.patient_age || 'N/A'} Yrs / {patientGender}
              </strong>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-secondary text-sm">Case Reference</span>
              <strong className="text-base text-white">{caseCode}</strong>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-secondary text-sm">Registered Date</span>
              <strong className="text-base text-white">{formattedDate}</strong>
            </div>
            {(recordedHeight || recordedWeight) && (
              <div className="flex flex-col gap-1">
                <span className="text-secondary text-sm">Physical Measurements</span>
                <strong className="text-base text-white">
                  {[recordedHeight, recordedWeight].filter(Boolean).join(' • ')}
                </strong>
              </div>
            )}
            {recordedLocation && (
              <div className="flex flex-col gap-1">
                <span className="text-secondary text-sm">Hospital Location</span>
                <strong className="text-base text-white">{recordedLocation}</strong>
              </div>
            )}
          </div>

          {/* Dynamic Vital Signs - Only displays entered vitals */}
          <div className="pt-2 border-t border-white/10">
            <div className="profile-section-title">
              <Activity size={14} className="text-ai-accent" />
              <span>Vital Signs {recordedVitals.length > 0 ? `(${recordedVitals.length} Recorded)` : ''}</span>
            </div>
            {recordedVitals.length > 0 ? (
              <div className="profile-vitals-grid">
                {recordedVitals.map((v, i) => (
                  <div key={i} className="vital-metric-card">
                    <span className="vital-metric-label flex items-center gap-1">
                      {getVitalIcon(v.label)}
                      {v.label}
                    </span>
                    <span className="vital-metric-val">{v.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-secondary text-sm italic m-0">No vital signs were recorded for this case intake.</p>
            )}
          </div>

          {/* Dynamic Reported Symptoms */}
          <div className="pt-2 border-t border-white/10">
            <div className="profile-section-title">
              <Activity size={14} className="text-warning" />
              <span>Reported Symptoms ({rawSymptoms.length})</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {rawSymptoms.length > 0 ? (
                rawSymptoms.map((s: string) => (
                  <span key={s} className="badge" style={{ background: 'rgba(255,255,255,0.1)' }}>
                    {s.replace(/_/g, ' ')}
                  </span>
                ))
              ) : (
                <span className="text-secondary text-sm italic">None recorded</span>
              )}
            </div>
          </div>

          {/* Dynamic Medical History */}
          <div className="pt-2 border-t border-white/10">
            <div className="profile-section-title">
              <Stethoscope size={14} className="text-purple-400" />
              <span>Medical History & Comorbidities</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {chronicConditions.length > 0 ? (
                chronicConditions.map((item: string) => (
                  <span key={item} className="badge badge-history">
                    {item}
                  </span>
                ))
              ) : (
                <span className="text-secondary text-sm italic">No prior medical history recorded</span>
              )}
            </div>
          </div>

          {/* Dynamic Allergies */}
          <div className="pt-2 border-t border-white/10">
            <div className="profile-section-title">
              <ShieldAlert size={14} className="text-danger" />
              <span>Documented Allergies</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {allergiesList.length > 0 ? (
                allergiesList.map((allergy: string) => (
                  <span key={allergy} className="badge badge-allergy">
                    ⚠️ {allergy}
                  </span>
                ))
              ) : (
                <span className="text-secondary text-sm italic">No known drug allergies recorded</span>
              )}
            </div>
          </div>

          {/* Dynamic Previous Antibiotics */}
          <div className="pt-2 border-t border-white/10">
            <div className="profile-section-title">
              <Pill size={14} className="text-info" />
              <span>Previous Antibiotics Exposure</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {previousAntibioticsList.length > 0 ? (
                previousAntibioticsList.map((ab: string) => (
                  <span key={ab} className="badge badge-antibiotic">
                    💊 {ab}
                  </span>
                ))
              ) : (
                <span className="text-secondary text-sm italic">No previous antibiotic treatments recorded</span>
              )}
            </div>
          </div>
        </GlassCard>

        {/* SECTION 2: AI DIAGNOSIS & RECOMMENDATIONS */}
        <GlassCard className="flex-col gap-4 printable-section-card">
          <div className="flex items-center gap-3 border-b border-white/10 pb-3">
            <Activity className="text-ai-accent" size={20} />
            <h3 className="m-0">AI Diagnosis & Recommendations</h3>
          </div>

          <div>
            <span className="text-secondary text-sm block">Primary Infection Classifier</span>
            <div className="text-lg font-bold text-ai-accent mt-1">
              {infectionName} ({confidenceStr})
            </div>
          </div>

          <div className="mt-2">
            <span className="text-secondary text-sm block mb-2">Prescribed / Recommended Antibiotics</span>
            {recommendations.length > 0 ? (
              <div className="flex-col gap-2">
                {recommendations.map((rec: any, idx: number) => (
                  <div key={idx} className="bg-white/5 p-3 rounded-lg border border-white/10 mb-2 rec-card-print">
                    <div className="flex justify-between items-center mb-1">
                      <strong className="text-base">{rec.name}</strong>
                      <span className={`badge ${rec.localResistance >= 40 ? 'badge-danger' : rec.localResistance >= 20 ? 'badge-warning' : 'badge-success'}`}>
                        {rec.localResistance}% Local Resistance
                      </span>
                    </div>
                    <p className="text-sm m-0 text-secondary">
                      {rec.dosage || 'Standard clinical dose'} • {rec.frequency || 'As advised'} • {rec.duration || 'Full course'}
                    </p>
                    {rec.interactionWarning && (
                      <p className="text-xs text-warning mt-1" style={{ margin: 0 }}>
                        ⚠️ {rec.interactionWarning}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-secondary text-sm italic">No specific antibiotics prescribed for this diagnostic category.</p>
            )}
          </div>
        </GlassCard>
      </div>

      {/* SECTION 3: PHYSICIAN NOTES */}
      <GlassCard className="printable-section-card mt-2">
        <div className="flex items-center gap-3 border-b border-white/10 pb-3 mb-3">
          <Stethoscope className="text-accent-primary" size={20} />
          <h3 className="m-0">Physician Notes</h3>
        </div>
        
        {/* Interactive Textarea for Screen Usage */}
        <div className="no-print">
          <textarea 
            className="input-field w-full" 
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            style={{ resize: 'vertical' }}
            placeholder="Enter clinical observations, treatment modifications, or patient instructions..."
          ></textarea>
          
          <div className="flex justify-end mt-2">
            <button className="btn btn-glass" onClick={() => alert('Physician notes saved for this session.')}>
              Save Notes
            </button>
          </div>
        </div>

        {/* Clean Static Block for Print */}
        <div className="print-notes-view">
          {notes || "Patient evaluated with Medix AI. Recommendations reviewed and validated according to local AMR patterns."}
        </div>

        {/* Official Medical Sign-off for Print */}
        <div className="print-signature-block">
          <div>
            <p style={{ margin: 0, fontWeight: 600 }}>Medix AI Clinical Decision Support System</p>
            <p style={{ margin: 0, fontSize: '8pt', color: '#64748b' }}>Verified against Regional AMR Surveillance Dataset</p>
          </div>
          <div className="signature-line">
            Attending Physician Signature
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
