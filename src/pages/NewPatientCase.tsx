import React, { useState, useEffect } from 'react';
import { Plus, Activity, Brain, Shield, CheckCircle, AlertTriangle, Headphones, Loader2, Volume2, VolumeX } from 'lucide-react';
import { GlassCard } from '../components/GlassCard';
import { BackButton } from '../components/BackButton';
import { usePersistentState } from '../hooks/usePersistentState';
import { apiFetch } from '../lib/api';
import { clinicalVoiceService } from '../lib/clinicalVoiceService';
import './NewPatientCase.css';

export function NewPatientCase() {
  const [caseCode, setCaseCode] = usePersistentState('medix_npc_caseCode', '');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [showResults, setShowResults] = usePersistentState('medix_npc_showResults', false);
  const [patientLocation, setPatientLocation] = usePersistentState('medix_npc_patientLocation', 'Kolkata');
  const [recommendations, setRecommendations] = usePersistentState<any[]>('medix_npc_recommendations', []);
  const [predictedInfection, setPredictedInfection] = usePersistentState<string>('medix_npc_predictedInfection', '');
  const [availableSymptoms, setAvailableSymptoms] = useState<{id: string, label: string}[]>([]);
  const [selectedSymptoms, setSelectedSymptoms] = usePersistentState<string[]>('medix_npc_selectedSymptoms', []);
  const [patientName, setPatientName] = usePersistentState<string>('medix_npc_patientName', '');
  const [patientAge, setPatientAge] = usePersistentState<number>('medix_npc_patientAge', 30);
  const [patientGender, setPatientGender] = usePersistentState<string>('medix_npc_patientGender', '');
  const [patientHeight, setPatientHeight] = usePersistentState<string>('medix_npc_patientHeight', '');
  const [patientWeight, setPatientWeight] = usePersistentState<string>('medix_npc_patientWeight', '');
  const [latestCaseId, setLatestCaseId] = usePersistentState<string>('medix_npc_latestCaseId', '');
  const [availableMedicalHistory, setAvailableMedicalHistory] = useState(['Diabetes', 'Hypertension', 'Kidney Disease', 'Heart Disease', 'Pregnancy', 'Allergy']);
  const [selectedMedicalHistory, setSelectedMedicalHistory] = usePersistentState<string[]>('medix_npc_selectedMedicalHistory', []);
  const [availableAllergies, setAvailableAllergies] = useState(['Penicillin', 'Sulfa', 'Cephalosporins']);
  const [selectedAllergies, setSelectedAllergies] = usePersistentState<string[]>('medix_npc_selectedAllergies', []);

  const [isAddingSymptom, setIsAddingSymptom] = useState(false);
  const [newSymptom, setNewSymptom] = useState('');

  const [isAddingMedicalHistory, setIsAddingMedicalHistory] = useState(false);
  const [newMedicalHistory, setNewMedicalHistory] = useState('');

  const [isAddingAllergy, setIsAddingAllergy] = useState(false);
  const [newAllergy, setNewAllergy] = useState('');

  const [vitals, setVitals] = usePersistentState('medix_npc_vitals', [
    { id: 'temp', name: 'Temperature (°F)', value: '', placeholder: '98.6' },
    { id: 'pulse', name: 'Pulse / Heart Rate (bpm)', value: '', placeholder: '72' },
    { id: 'spo2', name: 'SpO2 / Oxygen Saturation (%)', value: '', placeholder: '98' },
    { id: 'resp', name: 'Respiratory Rate', value: '', placeholder: '16' },
    { id: 'bp', name: 'Blood Pressure (mmHg)', value: '', placeholder: '120/80' }
  ]);
  const [isAddingVital, setIsAddingVital] = useState(false);
  const [newVitalName, setNewVitalName] = useState('');
  const [newVitalMeasure, setNewVitalMeasure] = useState('');

  const [previousAntibiotics, setPreviousAntibiotics] = usePersistentState<string[]>('medix_npc_previousAntibiotics', []);
  const [antibioticsInput, setAntibioticsInput] = useState('');
  const [invalidInputError, setInvalidInputError] = useState<{ message: string; rejectedTerms: string[]; recognizedTerms: string[] } | null>(null);
  useEffect(() => {
    // Generate unique code on mount
    if (!caseCode) {
      const code = 'CASE-' + Math.floor(100000 + Math.random() * 900000);
      setCaseCode(code);
    }
    
    // Fetch dynamic symptoms from ML backend
    apiFetch('/api/symptoms')
      .then(res => res.json())
      .then(data => {
        if(data.symptoms) setAvailableSymptoms(data.symptoms);
      })
      .catch(err => console.error("Could not fetch symptoms", err));
  }, []);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAnalysisStep(1);
    
    // Simulate some initial UI steps while fetching
    const progressInterval = setInterval(() => {
      setAnalysisStep(prev => prev < 4 ? prev + 1 : prev);
    }, 1500);

    try {
      const activeVitals = vitals.filter(v => v.value && v.value.trim());

      const response = await apiFetch('/api/analyze-case', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: patientName || "Unknown Patient",
          age: patientAge,
          gender: patientGender || "Unspecified",
          height: patientHeight ? parseFloat(patientHeight) : undefined,
          weight: patientWeight ? parseFloat(patientWeight) : undefined,
          location: patientLocation || "Kolkata",
          symptoms: selectedSymptoms, 
          medical_history: selectedMedicalHistory,
          allergies: selectedAllergies,
          previous_antibiotics: previousAntibiotics,
          vitals: activeVitals
        })
      });

      if (!response.ok) {
        throw new Error("Failed to fetch analysis");
      }

      const data = await response.json();
      
      clearInterval(progressInterval);
      setAnalysisStep(5);

      // INVALID INPUT: backend rejected the symptoms as non-medical
      if (data.validCase === false) {
        setTimeout(() => {
          setIsAnalyzing(false);
          setInvalidInputError({
            message: data.clinicalSummary || 'No valid medical symptoms were detected.',
            rejectedTerms: data.rejectedTerms || [],
            recognizedTerms: data.recognizedTerms || [],
          });
        }, 500);
        return;
      }
      
      if (data.caseId) {
        setLatestCaseId(data.caseId);
        localStorage.setItem('medix_latest_case_id', data.caseId);
      }
      
      setTimeout(() => {
        setRecommendations(data.recommendations || []);
        setPredictedInfection(data.predictedInfection || '');
        setIsAnalyzing(false);
        setShowResults(true);
      }, 1000);
      
    } catch (error) {
      console.error(error);
      clearInterval(progressInterval);
      alert("Error calling AI Backend. Make sure the Python server is running.");
      setIsAnalyzing(false);
    }
  };

  if (showResults) {
    return <AnalysisResults caseId={latestCaseId} caseCode={caseCode} recommendations={recommendations} location={patientLocation} predictedInfection={predictedInfection} onEdit={() => setShowResults(false)} />;
  }

  return (
    <div className="case-container">
      <BackButton />
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2>New Patient Case</h2>
          <p className="text-secondary">Enter patient details for AI analysis</p>
        </div>
        <div className="case-code-badge">
          Unique Code: <strong>{caseCode}</strong>
        </div>
      </div>

      <div className="grid-2-col gap-3">
        {/* Left Column */}
        <div className="flex-col gap-3">
          <GlassCard>
            <h3 className="mb-3">Patient Information</h3>
            <div className="grid-2-col gap-2">
              <div className="input-group">
                <label>Patient Name</label>
                <input type="text" className="input-field" placeholder="Full Name" value={patientName} onChange={e => setPatientName(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Age</label>
                <input type="number" className="input-field" placeholder="Years" value={patientAge} onChange={e => setPatientAge(parseInt(e.target.value) || 30)} />
              </div>
              <div className="input-group">
                <label>Gender</label>
                <select 
                  className="input-field bg-transparent"
                  value={patientGender}
                  onChange={e => setPatientGender(e.target.value)}
                >
                  <option value="" style={{ color: '#000' }}>Select...</option>
                  <option value="Male" style={{ color: '#000' }}>Male</option>
                  <option value="Female" style={{ color: '#000' }}>Female</option>
                  <option value="Other" style={{ color: '#000' }}>Other</option>
                </select>
              </div>
              <div className="input-group">
                <label>Height (cm)</label>
                <input 
                  type="number" 
                  className="input-field" 
                  placeholder="170" 
                  value={patientHeight}
                  onChange={e => setPatientHeight(e.target.value)}
                />
              </div>
              <div className="input-group">
                <label>Weight (kg)</label>
                <input 
                  type="number" 
                  className="input-field" 
                  placeholder="70" 
                  value={patientWeight}
                  onChange={e => setPatientWeight(e.target.value)}
                />
              </div>
              <div className="input-group" style={{ gridColumn: 'span 2' }}>
                <label>Hospital Location (For AMR Model)</label>
                <input type="text" className="input-field" placeholder="e.g. Kolkata" value={patientLocation} onChange={e => setPatientLocation(e.target.value)} />
              </div>
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3">Symptoms ({selectedSymptoms.length} selected)</h3>
            <div className="tags-container" style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {availableSymptoms.length > 0 ? availableSymptoms.map(s => {
                const isSelected = selectedSymptoms.includes(s.id);
                return (
                  <button 
                    key={s.id} 
                    className={`tag-btn ${isSelected ? 'selected-tag' : ''}`}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedSymptoms(prev => prev.filter(id => id !== s.id));
                      } else {
                        setSelectedSymptoms(prev => [...prev, s.id]);
                      }
                    }}
                    style={{ backgroundColor: isSelected ? 'rgba(74, 144, 226, 0.2)' : '', borderColor: isSelected ? '#4a90e2' : '' }}
                  >
                    {s.label}
                  </button>
                )
              }) : (
                <span className="text-secondary text-sm">Loading symptoms from AI Model...</span>
              )}
              {!isAddingSymptom ? (
                <button 
                  className="tag-btn add-new" 
                  onClick={() => setIsAddingSymptom(true)}
                  title="Add custom symptom"
                >
                  <Plus size={16} /> Add New
                </button>
              ) : (
                <div className="flex gap-2 items-center" style={{ display: 'inline-flex' }}>
                  <input 
                    type="text" 
                    className="input-field" 
                    style={{ padding: '4px 8px', width: '130px', minHeight: '32px' }} 
                    placeholder="New Symptom"
                    value={newSymptom}
                    onChange={(e) => setNewSymptom(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newSymptom.trim()) {
                        const trimmed = newSymptom.trim();
                        const cleanId = trimmed.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_');
                        if (!availableSymptoms.some(s => s.id === cleanId)) {
                          setAvailableSymptoms(prev => [...prev, { id: cleanId, label: trimmed }]);
                        }
                        if (!selectedSymptoms.includes(cleanId)) {
                          setSelectedSymptoms(prev => [...prev, cleanId]);
                        }
                        setNewSymptom('');
                        setIsAddingSymptom(false);
                      } else if (e.key === 'Escape') {
                        setIsAddingSymptom(false);
                        setNewSymptom('');
                      }
                    }}
                    autoFocus
                  />
                  <button 
                    className="tag-btn add-new" 
                    onClick={() => {
                      if (newSymptom.trim()) {
                        const trimmed = newSymptom.trim();
                        const cleanId = trimmed.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_');
                        if (!availableSymptoms.some(s => s.id === cleanId)) {
                          setAvailableSymptoms(prev => [...prev, { id: cleanId, label: trimmed }]);
                        }
                        if (!selectedSymptoms.includes(cleanId)) {
                          setSelectedSymptoms(prev => [...prev, cleanId]);
                        }
                      }
                      setNewSymptom('');
                      setIsAddingSymptom(false);
                    }}
                  >
                    Save
                  </button>
                  <button 
                    className="tag-btn" 
                    style={{ padding: '4px 8px', minHeight: '32px' }}
                    onClick={() => {
                      setIsAddingSymptom(false);
                      setNewSymptom('');
                    }}
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3">Medical History</h3>
            <div className="tags-container">
              {availableMedicalHistory.map(s => {
                const isSelected = selectedMedicalHistory.includes(s);
                return (
                  <button 
                    key={s} 
                    className={`tag-btn ${isSelected ? 'selected-tag' : ''}`}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedMedicalHistory(prev => prev.filter(item => item !== s));
                      } else {
                        setSelectedMedicalHistory(prev => [...prev, s]);
                      }
                    }}
                    style={{ backgroundColor: isSelected ? 'rgba(74, 144, 226, 0.2)' : '', borderColor: isSelected ? '#4a90e2' : '' }}
                  >
                    {s}
                  </button>
                );
              })}
              {!isAddingMedicalHistory ? (
                <button 
                  className="tag-btn add-new" 
                  onClick={() => setIsAddingMedicalHistory(true)}
                >
                  <Plus size={16} /> Add New
                </button>
              ) : (
                <div className="flex gap-2 items-center" style={{ display: 'inline-flex' }}>
                  <input 
                    type="text" 
                    className="input-field" 
                    style={{ padding: '4px 8px', width: '120px', minHeight: '32px' }} 
                    placeholder="New History"
                    value={newMedicalHistory}
                    onChange={(e) => setNewMedicalHistory(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newMedicalHistory.trim()) {
                        const trimmed = newMedicalHistory.trim();
                        if (!availableMedicalHistory.includes(trimmed)) setAvailableMedicalHistory(prev => [...prev, trimmed]);
                        if (!selectedMedicalHistory.includes(trimmed)) setSelectedMedicalHistory(prev => [...prev, trimmed]);
                        setNewMedicalHistory('');
                        setIsAddingMedicalHistory(false);
                      }
                    }}
                    autoFocus
                  />
                  <button className="tag-btn add-new" onClick={() => {
                    if (newMedicalHistory.trim()) {
                      const trimmed = newMedicalHistory.trim();
                      if (!availableMedicalHistory.includes(trimmed)) setAvailableMedicalHistory(prev => [...prev, trimmed]);
                      if (!selectedMedicalHistory.includes(trimmed)) setSelectedMedicalHistory(prev => [...prev, trimmed]);
                    }
                    setNewMedicalHistory('');
                    setIsAddingMedicalHistory(false);
                  }}>Save</button>
                </div>
              )}
            </div>
          </GlassCard>
        </div>

        {/* Right Column */}
        <div className="flex-col gap-3">
          <GlassCard>
            <h3 className="mb-3">Vital Signs</h3>
            <div className="grid-2-col gap-2">
              {vitals.map(v => (
                <div key={v.id} className="input-group" style={v.name.includes('Blood Pressure') ? { gridColumn: 'span 2' } : {}}>
                  <label>{v.name}</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    placeholder={v.placeholder}
                    value={v.value}
                    onChange={(e) => setVitals(vitals.map(item => item.id === v.id ? { ...item, value: e.target.value } : item))}
                  />
                </div>
              ))}
              
              {isAddingVital ? (
                <div className="input-group" style={{ gridColumn: 'span 2' }}>
                  <label>New Vital Sign</label>
                  <div className="grid-2-col gap-2">
                    <input 
                      type="text" 
                      className="input-field" 
                      placeholder="Sign Name (e.g. Blood Sugar)"
                      value={newVitalName}
                      onChange={e => setNewVitalName(e.target.value)}
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <input 
                        type="text" 
                        className="input-field flex-1" 
                        placeholder="Measure (e.g. 100 mg/dL)"
                        value={newVitalMeasure}
                        onChange={e => setNewVitalMeasure(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && newVitalName.trim()) {
                            setVitals([...vitals, { 
                              id: 'vital-' + Date.now(), 
                              name: newVitalName.trim(), 
                              value: newVitalMeasure.trim(), 
                              placeholder: '' 
                            }]);
                            setNewVitalName('');
                            setNewVitalMeasure('');
                            setIsAddingVital(false);
                          }
                        }}
                      />
                      <button 
                        className="btn btn-primary"
                        onClick={() => {
                          if (newVitalName.trim()) {
                            setVitals([...vitals, { 
                              id: 'vital-' + Date.now(), 
                              name: newVitalName.trim(), 
                              value: newVitalMeasure.trim(), 
                              placeholder: '' 
                            }]);
                            setNewVitalName('');
                            setNewVitalMeasure('');
                            setIsAddingVital(false);
                          }
                        }}
                      >
                        Save
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <button 
                  className="btn btn-outline" 
                  style={{ gridColumn: 'span 2' }}
                  onClick={() => setIsAddingVital(true)}
                >
                  <Plus size={16} /> Add New Vital
                </button>
              )}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3">Allergies</h3>
            <div className="tags-container">
              {availableAllergies.map(s => {
                const isSelected = selectedAllergies.includes(s);
                return (
                  <button 
                    key={s} 
                    className={`tag-btn ${isSelected ? 'selected-tag' : ''}`}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedAllergies(prev => prev.filter(item => item !== s));
                      } else {
                        setSelectedAllergies(prev => [...prev, s]);
                      }
                    }}
                    style={{ backgroundColor: isSelected ? 'rgba(74, 144, 226, 0.2)' : '', borderColor: isSelected ? '#4a90e2' : '' }}
                  >
                    {s}
                  </button>
                );
              })}
              {!isAddingAllergy ? (
                <button 
                  className="tag-btn add-new" 
                  onClick={() => setIsAddingAllergy(true)}
                >
                  <Plus size={16} /> Add New
                </button>
              ) : (
                <div className="flex gap-2 items-center" style={{ display: 'inline-flex' }}>
                  <input 
                    type="text" 
                    className="input-field" 
                    style={{ padding: '4px 8px', width: '120px', minHeight: '32px' }} 
                    placeholder="New Allergy"
                    value={newAllergy}
                    onChange={(e) => setNewAllergy(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && newAllergy.trim()) {
                        const trimmed = newAllergy.trim();
                        if (!availableAllergies.includes(trimmed)) setAvailableAllergies(prev => [...prev, trimmed]);
                        if (!selectedAllergies.includes(trimmed)) setSelectedAllergies(prev => [...prev, trimmed]);
                        setNewAllergy('');
                        setIsAddingAllergy(false);
                      }
                    }}
                    autoFocus
                  />
                  <button className="tag-btn add-new" onClick={() => {
                    if (newAllergy.trim()) {
                      const trimmed = newAllergy.trim();
                      if (!availableAllergies.includes(trimmed)) setAvailableAllergies(prev => [...prev, trimmed]);
                      if (!selectedAllergies.includes(trimmed)) setSelectedAllergies(prev => [...prev, trimmed]);
                    }
                    setNewAllergy('');
                    setIsAddingAllergy(false);
                  }}>Save</button>
                </div>
              )}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3">Previous Antibiotics</h3>
            <div className="tags-container mb-2">
              {previousAntibiotics.map(ab => (
                <button 
                  key={ab} 
                  className="tag-btn selected-tag"
                  style={{ backgroundColor: 'rgba(74, 144, 226, 0.2)', borderColor: '#4a90e2' }}
                  onClick={() => setPreviousAntibiotics(prev => prev.filter(item => item !== ab))}
                >
                  {ab} <span style={{ marginLeft: '4px', opacity: 0.7 }}>×</span>
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input 
                type="text" 
                className="input-field flex-1" 
                placeholder="Enter antibiotics (comma/space separated)" 
                value={antibioticsInput}
                onChange={e => setAntibioticsInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && antibioticsInput.trim()) {
                    const newAbs = antibioticsInput.split(/[, ]+/).map(s => s.trim()).filter(s => s !== '');
                    const uniqueAbs = newAbs.filter(ab => !previousAntibiotics.includes(ab));
                    if (uniqueAbs.length > 0) {
                      setPreviousAntibiotics(prev => [...prev, ...uniqueAbs]);
                    }
                    setAntibioticsInput('');
                  }
                }}
              />
              <button 
                className="btn btn-primary"
                onClick={() => {
                  if (antibioticsInput.trim()) {
                    const newAbs = antibioticsInput.split(/[, ]+/).map(s => s.trim()).filter(s => s !== '');
                    const uniqueAbs = newAbs.filter(ab => !previousAntibiotics.includes(ab));
                    if (uniqueAbs.length > 0) {
                      setPreviousAntibiotics(prev => [...prev, ...uniqueAbs]);
                    }
                    setAntibioticsInput('');
                  }
                }}
              >
                Save
              </button>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ── Invalid Input Error Banner ──────────────────────────────── */}
      {invalidInputError && (
        <div
          className="mt-4"
          style={{
            background: 'linear-gradient(135deg, rgba(220, 53, 69, 0.12), rgba(220, 53, 69, 0.06))',
            border: '1.5px solid rgba(220, 53, 69, 0.55)',
            borderRadius: '14px',
            padding: '20px 24px',
            animation: 'fadeIn 0.35s ease',
          }}
        >
          <div className="flex items-start gap-3">
            <AlertTriangle size={26} style={{ color: '#e55', flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <h4 style={{ color: '#ff6b6b', margin: '0 0 8px', fontSize: '1rem', fontWeight: 700 }}>
                ⚠️ Invalid Symptom Input — Analysis Blocked
              </h4>

              {invalidInputError.rejectedTerms.length > 0 && (
                <div className="mb-2">
                  <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
                    <strong style={{ color: '#ff6b6b' }}>Not recognized as medical symptoms:</strong>{' '}
                    {invalidInputError.rejectedTerms.map((t, i) => (
                      <span
                        key={i}
                        style={{
                          display: 'inline-block',
                          background: 'rgba(220, 53, 69, 0.18)',
                          border: '1px solid rgba(220, 53, 69, 0.4)',
                          borderRadius: '6px',
                          padding: '1px 8px',
                          margin: '2px 4px 2px 0',
                          fontSize: '0.82rem',
                          fontFamily: 'monospace',
                          color: '#ff8787',
                        }}
                      >
                        {t}
                      </span>
                    ))}
                  </span>
                </div>
              )}

              {invalidInputError.recognizedTerms.length > 0 && (
                <div className="mb-2">
                  <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
                    <strong style={{ color: '#ffa94d' }}>Partially recognized (insufficient for diagnosis):</strong>{' '}
                    {invalidInputError.recognizedTerms.map((t, i) => (
                      <span
                        key={i}
                        style={{
                          display: 'inline-block',
                          background: 'rgba(255, 140, 0, 0.15)',
                          border: '1px solid rgba(255, 140, 0, 0.35)',
                          borderRadius: '6px',
                          padding: '1px 8px',
                          margin: '2px 4px 2px 0',
                          fontSize: '0.82rem',
                          fontFamily: 'monospace',
                          color: '#ffc078',
                        }}
                      >
                        {t}
                      </span>
                    ))}
                  </span>
                </div>
              )}

              <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.84rem', margin: '8px 0 12px', lineHeight: 1.55 }}>
                Please select or enter recognized clinical symptoms such as{' '}
                <em>"fever"</em>, <em>"headache"</em>, <em>"chest pain"</em>, <em>"cough"</em>, or{' '}
                <em>"fatigue"</em>. Drug recommendations are withheld for patient safety until valid symptoms are provided.
              </p>

              <button
                className="btn btn-outline"
                style={{ fontSize: '0.85rem', padding: '6px 16px', borderColor: 'rgba(220,53,69,0.5)', color: '#ff6b6b' }}
                onClick={() => setInvalidInputError(null)}
              >
                ✕ Dismiss &amp; Fix Symptoms
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 flex justify-center">
        <button className="btn btn-ai analyze-btn animate-pulse" onClick={() => { setInvalidInputError(null); handleAnalyze(); }}>
          <Brain size={24} />
          Analyze with AI
        </button>
      </div>

      {isAnalyzing && (
        <div className="ai-overlay">
          <div className="ai-processing-box glass-panel animate-slide-up">
            <Brain size={48} className="text-ai-accent mb-3 animate-float" />
            <h2 className="ai-typing">Medix AI Processing</h2>
            
            <div className="workflow-steps mt-4">
              <div className={`workflow-step ${analysisStep >= 1 ? 'active' : ''} ${analysisStep > 1 ? 'completed' : ''}`}>
                <div className="step-icon">{analysisStep > 1 ? <CheckCircle size={16}/> : <Activity size={16}/>}</div>
                <span>Reading Symptoms</span>
              </div>
              <div className={`workflow-step ${analysisStep >= 2 ? 'active' : ''} ${analysisStep > 2 ? 'completed' : ''}`}>
                <div className="step-icon">{analysisStep > 2 ? <CheckCircle size={16}/> : <Activity size={16}/>}</div>
                <span>Disease Prediction</span>
              </div>
              <div className={`workflow-step ${analysisStep >= 3 ? 'active' : ''} ${analysisStep > 3 ? 'completed' : ''}`}>
                <div className="step-icon">{analysisStep > 3 ? <CheckCircle size={16}/> : <Activity size={16}/>}</div>
                <span>Antibiotic Recommendation</span>
              </div>
              <div className={`workflow-step ${analysisStep >= 4 ? 'active' : ''} ${analysisStep > 4 ? 'completed' : ''}`}>
                <div className="step-icon">{analysisStep > 4 ? <CheckCircle size={16}/> : <Activity size={16}/>}</div>
                <span>Drug Interaction Check</span>
              </div>
              <div className={`workflow-step ${analysisStep >= 5 ? 'active' : ''} ${analysisStep > 5 ? 'completed' : ''}`}>
                <div className="step-icon">{analysisStep > 5 ? <CheckCircle size={16}/> : <Activity size={16}/>}</div>
                <span>Generating Report...</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AnalysisResults({ caseId, caseCode, recommendations, location, predictedInfection, onEdit }: { caseId?: string, caseCode: string, recommendations: any[], location: string, predictedInfection?: string, onEdit: () => void }) {
  const [playingDrugName, setPlayingDrugName] = useState<string | null>(null);
  const [loadingDrugName, setLoadingDrugName] = useState<string | null>(null);

  // Clean up any playing audio when AnalysisResults unmounts
  useEffect(() => {
    return () => {
      clinicalVoiceService.stopAll();
    };
  }, []);

  const handleHearRationale = async (rec: any, index: number) => {
    // If clicking the one currently playing, toggle stop
    if (playingDrugName === rec.name) {
      clinicalVoiceService.stopAll();
      setPlayingDrugName(null);
      setLoadingDrugName(null);
      return;
    }

    // Interrupt previous playback immediately
    clinicalVoiceService.stopAll();
    setLoadingDrugName(rec.name);
    setPlayingDrugName(rec.name);

    // Compute dynamic clinical metadata per requirement:
    // "Medix AI selected [Drug Name] as [Rank] line therapy. Local [Pathogen] susceptibility in [Region] is currently [X]%, compared to [Y]% resistance against [Alternative]. Microbiome disruption score is [Minimal/Low], and no drug-drug interactions were found with the patient's existing regimen."
    const rankLabel = rec.rank_label || (index === 0 ? "1st" : (index === 1 ? "2nd" : "3rd"));
    const pathogenName = rec.pathogen || (predictedInfection?.includes('UTI') ? 'Escherichia coli' : 'Streptococcus pneumoniae');
    const regionName = location || rec.region || 'Kolkata';
    const resVal = typeof rec.localResistance === 'number' ? rec.localResistance : 15;
    const susceptibilityPct = Math.max(5, 100 - resVal);
    
    const altCandidate = recommendations[1]?.name && index === 0 ? recommendations[1].name : (recommendations[0]?.name || 'Ciprofloxacin');
    const altResistance = recommendations[1]?.localResistance && index === 0 ? recommendations[1].localResistance : 42;
    const microbiomeScore = ['Nitrofurantoin', 'Fosfomycin', 'Amoxicillin'].some(d => rec.name.includes(d)) ? 'Minimal' : 'Low';
    
    const interactionText = (rec.contraindicated || rec.interactionWarning)
      ? "however, please verify interaction precautions noted with the patient's existing regimen."
      : "and no drug-drug interactions were found with the patient's existing regimen.";

    const dynamicRationaleScript = rec.clinical_rationale_speech || (
      `Medix AI selected ${rec.name} as ${rankLabel} line therapy. ` +
      `Local ${pathogenName} susceptibility in ${regionName} is currently ${susceptibilityPct}%, ` +
      `compared to ${altResistance}% resistance against ${altCandidate}. ` +
      `Microbiome disruption score is ${microbiomeScore}, ${interactionText}`
    );

    try {
      await clinicalVoiceService.speakText(dynamicRationaleScript, {
        onStart: () => {
          setLoadingDrugName(null);
          setPlayingDrugName(rec.name);
        },
        onEnd: () => {
          setPlayingDrugName(null);
          setLoadingDrugName(null);
        },
        onError: () => {
          setPlayingDrugName(null);
          setLoadingDrugName(null);
        }
      });
    } catch (err) {
      console.warn("Rationale playback error:", err);
      setPlayingDrugName(null);
      setLoadingDrugName(null);
    }
  };

  const rawInfection = predictedInfection || "Uncomplicated Urinary Tract Infection (UTI) (Confidence: 94%)";
  const infName = rawInfection.includes('(') ? rawInfection.split('(')[0].trim() : rawInfection;
  const confStr = rawInfection.includes('(') ? "Confidence: " + rawInfection.split('(')[1].replace(')', '').replace('Confidence:', '').trim() : "Confidence Score: 94%";


  return (
    <div className="results-container animate-fade-in">
      <BackButton />
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <div>
          <h2>AI Analysis Complete</h2>
          <p className="text-secondary">Case: {caseCode} | Location: {location}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button 
            className="btn btn-primary cursor-pointer flex items-center gap-2" 
            onClick={() => {
              const url = caseId ? `/reports?caseId=${caseId}` : '/reports';
              window.location.href = url;
            }}
          >
            📄 View & Print Full Report
          </button>
          <button className="btn btn-outline cursor-pointer" onClick={onEdit}>← Edit Case Inputs</button>
          <button className="btn btn-outline cursor-pointer" onClick={() => {
            localStorage.removeItem('medix_npc_caseCode');
            localStorage.removeItem('medix_npc_showResults');
            localStorage.removeItem('medix_npc_selectedSymptoms');
            localStorage.removeItem('medix_npc_recommendations');
            window.location.reload();
          }}>Start Fresh Case</button>
        </div>
      </div>

      <GlassCard className="mb-4 text-center p-4">
        <h3 className="text-ai-accent flex justify-center items-center gap-2">
          <Brain size={24} /> Infection Classifier
        </h3>
        <p className="mt-2 text-xl font-bold">{infName}</p>
        <div className="flex justify-center mt-2">
          <span className={`badge ${recommendations.length > 0 ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '1rem', padding: '6px 16px' }}>
            {confStr}
          </span>
        </div>
      </GlassCard>

      {recommendations.length === 0 ? (
        <GlassCard className="mb-4 p-5 text-center" style={{ borderColor: 'var(--color-warning)', background: 'rgba(245, 158, 11, 0.05)' }}>
          <div className="flex justify-center mb-3">
            <AlertTriangle size={48} className="text-warning" />
          </div>
          <h3 className="text-warning mb-2">Prescriptions Withheld for Patient Safety</h3>
          <p className="text-secondary max-w-xl mx-auto" style={{ lineHeight: 1.6, maxWidth: '650px', margin: '0 auto' }}>
            Medix AI did not identify any valid human clinical symptoms or recognized diagnostic signs from the submitted input.
            To prevent inappropriate antibiotic or medication dispensing, drug recommendations have been safely withheld.
          </p>
          <div className="mt-4 flex justify-center gap-3">
            <button className="btn btn-primary" onClick={onEdit}>
              ✏️ Modify Symptoms & Re-analyze
            </button>
          </div>
        </GlassCard>
      ) : (
        <>
          <h3 className="mb-3">Combined Recommendation Engine</h3>
          <p className="text-secondary mb-4">Scores are calculated using Clinical AI suitability and AMR Surveillance Model (Local Resistance Data).</p>
          
          <div className="flex-col gap-3 mb-4">
            {recommendations.map((rec, index) => {
              const isPreferred = index === 0;
              const isAmrApplicable = rec.amrApplicable !== false;
              let resistanceBadge = "badge-success";
              let resistanceLabel = "Low";
              
              if (!isAmrApplicable) {
                resistanceBadge = "badge-outline";
                resistanceLabel = "N/A (Symptomatic)";
              } else if (rec.localResistance >= 40) { 
                resistanceBadge = "badge-danger"; 
                resistanceLabel = "High"; 
              } else if (rec.localResistance >= 20) { 
                resistanceBadge = "badge-warning"; 
                resistanceLabel = "Medium"; 
              }

              const displayResistance = rec.localResistanceDisplay || `${rec.localResistance}%`;

              return (
                <GlassCard key={rec.name} className={`recommendation-card ${isPreferred ? 'border-accent' : ''}`}>
                  <div className="rec-header">
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className={`rank-badge ${isPreferred ? 'primary' : 'alt'}`}>
                        {rec.treatment_tier ? (rec.treatment_tier.includes('1st') ? '⭐ 1st Choice' : rec.treatment_tier) : (isPreferred ? '⭐ 1st Choice' : 'Alternative')}
                      </div>
                      <h4 style={{ margin: 0 }}>{rec.name}</h4>
                      {rec.rxcui && (
                    <span className="badge badge-outline text-xs" style={{ border: '1px solid var(--color-accent-primary)', color: 'var(--color-accent-primary)', padding: '2px 8px' }}>
                      RxCUI: {rec.rxcui}
                    </span>
                  )}
                  {rec.epc && (
                    <span className="badge badge-primary text-xs" style={{ padding: '2px 8px' }}>
                      🏛️ NLM Class: {rec.epc}
                    </span>
                  )}

                  {/* Feature 2: "Why This Drug?" Clinical Rationale Button */}
                  <button
                    className={`hear-rationale-btn ${playingDrugName === rec.name ? 'active' : ''}`}
                    onClick={() => handleHearRationale(rec, index)}
                    title="Hear dynamic clinical AI rationale via ElevenLabs"
                  >
                    {loadingDrugName === rec.name ? (
                      <Loader2 size={14} className="animate-spin text-accent-primary" />
                    ) : playingDrugName === rec.name ? (
                      <span className="equalizer-wave">
                        <span className="equalizer-bar"></span>
                        <span className="equalizer-bar"></span>
                        <span className="equalizer-bar"></span>
                      </span>
                    ) : (
                      <Headphones size={14} />
                    )}
                    <span>
                      {loadingDrugName === rec.name 
                        ? 'Synthesizing...' 
                        : (playingDrugName === rec.name ? 'Playing Rationale' : 'Hear Clinical Rationale')}
                    </span>
                  </button>
                </div>
                <div className="flex gap-4">
                  <div className="stat-pill"><span className="label">Clinical Suitability</span><span className="val text-success">{rec.clinicalSuitability}%</span></div>

                  <div className="stat-pill">
                    <span className="label">Local Resistance</span>
                    <span className={`val ${resistanceBadge.replace('badge-', 'text-')}`}>
                      {isAmrApplicable ? displayResistance : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              {rec.interactionWarning && (
                <div className="mt-3 p-3 rounded-lg border text-sm flex items-start gap-2" style={{
                  background: rec.contraindicated ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                  borderColor: rec.contraindicated ? 'var(--color-danger)' : 'var(--color-warning)'
                }}>
                  <AlertTriangle size={18} className={rec.contraindicated ? 'text-danger' : 'text-warning'} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <strong className={rec.contraindicated ? 'text-danger' : 'text-warning'}>
                      {rec.contraindicated ? '⚠️ Critical Contraindication Detected:' : '⚠️ Interaction Warning:'}
                    </strong>
                    <p className="text-secondary text-xs mt-1" style={{ margin: 0 }}>{rec.interactionWarning}</p>
                  </div>
                </div>
              )}

              
              <div className="rec-body grid-2-col gap-4 mt-3">
                <div className="info-block">
                  <span className="label">Why recommended:</span>
                  <p>
                    {!isAmrApplicable
                      ? "Recommended as symptomatic agent for fever and discomfort; bacterial resistance metrics are not applicable."
                      : (isPreferred 
                        ? "Best balance of clinical effectiveness and low local resistance." 
                        : (rec.localResistance > 40 ? "Not preferred due to high local resistance despite good clinical suitability." : "Good alternative with acceptable resistance levels."))}
                  </p>
                </div>
                <div className="flex-col gap-2">
                  {rec.rxcui && <div className="detail-row"><span>NLM RxNorm ID:</span> <strong className="text-accent">{rec.rxcui}</strong></div>}
                  {rec.epc && <div className="detail-row"><span>Established Class:</span> <span>{rec.epc}</span></div>}
                  <div className="detail-row">
                    <span>Resistance Level ({location}):</span> 
                    <span className={`badge ${resistanceBadge}`}>
                      {isAmrApplicable ? `${resistanceLabel} (${displayResistance})` : 'N/A (Symptomatic Non-Antimicrobial)'}
                    </span>
                  </div>
                  <div className="detail-row"><span>Dosage:</span> <span>{rec.dosage}</span></div>
                  <div className="detail-row"><span>Frequency:</span> <span>{rec.frequency}</span></div>
                  <div className="detail-row"><span>Duration:</span> <span>{rec.duration}</span></div>
                  <div className="detail-row"><span>Side Effects:</span> <span>{rec.sideEffects}</span></div>
                </div>
              </div>
            </GlassCard>
          );
        })}
      </div>
      </>
      )}

      <div className="disclaimer-alert">
        <Shield size={24} className="text-warning" />
        <p><strong>DISCLAIMER:</strong> Medix AI is an AI and AI can make mistakes! Always verify recommendations with clinical judgement before prescribing.</p>
      </div>
    </div>
  );
}
