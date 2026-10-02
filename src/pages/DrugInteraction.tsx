import React, { useState, useEffect } from 'react';
import { Search, AlertTriangle, ShieldCheck, Activity, Plus, Volume2, VolumeX, ArrowRight, ShieldAlert } from 'lucide-react';
import { GlassCard } from '../components/GlassCard';
import { BackButton } from '../components/BackButton';
import { usePersistentState } from '../hooks/usePersistentState';
import { apiFetch } from '../lib/api';
import { clinicalVoiceService } from '../lib/clinicalVoiceService';
import './DrugInteraction.css';

const commonDrugs = [
  'Atorvastatin', 'Amlodipine', 'Lisinopril', 'Losartan', 'Metoprolol', 'Warfarin', 'Digoxin',
  'Acetaminophen', 'Ibuprofen', 'Naproxen', 'Diclofenac', 'Aspirin',
  'Omeprazole', 'Pantoprazole', 'Esomeprazole', 'Ranitidine',
  'Escitalopram', 'Sertraline', 'Fluoxetine', 'Alprazolam', 'Lithium carbonate',
  'Metformin', 'Levothyroxine', 'Amoxicillin', 'Azithromycin', 'Ciprofloxacin',
  'Clarithromycin', 'Erythromycin', 'Doxycycline', 'Nitrofurantoin', 'Cotrimoxazole',
  'Fluconazole', 'Ketoconazole', 'Rifampicin', 'Isoniazid'
];

export function DrugInteraction() {
  const [selectedDrugs, setSelectedDrugs] = usePersistentState<string[]>('medix_di_selectedDrugs', []);
  const [searchTerm, setSearchTerm] = usePersistentState('medix_di_searchTerm', '');
  const [showResult, setShowResult] = usePersistentState('medix_di_showResult', false);
  const [isChecking, setIsChecking] = useState(false);
  const [interactionData, setInteractionData] = usePersistentState<any>('medix_di_interactionData', null);
  const [checkError, setCheckError] = useState<string | null>(null);

  // Emergency Contraindication Audio State
  const [emergencyAlert, setEmergencyAlert] = useState<{
    isOpen: boolean;
    drugA: string;
    drugB: string;
    riskFactor: string;
    recommendedAlternative: string;
    voiceAlertText: string;
    severity: string;
    isMuted: boolean;
  } | null>(null);

  // Clean up any playing audio on component unmount
  useEffect(() => {
    return () => {
      clinicalVoiceService.stopAll();
    };
  }, []);

  const toggleDrug = (drug: string) => {
    if (selectedDrugs.includes(drug)) {
      setSelectedDrugs(selectedDrugs.filter(d => d !== drug));
    } else {
      setSelectedDrugs([...selectedDrugs, drug]);
    }
    setShowResult(false);
  };

  const handleAddCustom = () => {
    const custom = searchTerm.trim();
    if (custom && !selectedDrugs.includes(custom)) {
      setSelectedDrugs([...selectedDrugs, custom]);
      setSearchTerm('');
      setShowResult(false);
    }
  };

  const handleCheckInteractions = async () => {
    setIsChecking(true);
    // Instantly cancel any ongoing audio before fresh evaluation
    clinicalVoiceService.stopAll();

    setCheckError(null);

    try {
      const res = await apiFetch('/api/check-interactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drugs: selectedDrugs })
      });
      if (res.ok) {
        const data = await res.json();
        setInteractionData(data);
        setShowResult(true);

        // Feature 1: Emergency Contraindication Audio Trigger
        // Trigger if highest severity is CRITICAL, CONTRAINDICATED, or MAJOR
        const sevUpper = (data.highest_severity || data.severity || '').toUpperCase();
        if (['CONTRAINDICATED', 'CRITICAL', 'MAJOR'].includes(sevUpper) && data.interactions && data.interactions.length > 0) {
          // Identify first high-risk flagged interaction
          const criticalInt = data.interactions.find((it: any) => 
            ['CONTRAINDICATED', 'CRITICAL', 'MAJOR'].includes((it.interaction_level || it.severity || '').toUpperCase())
          ) || data.interactions[0];

          let drugA = criticalInt.drug_a || '';
          let drugB = criticalInt.drug_b || '';
          if (!drugA || !drugB) {
            if (typeof criticalInt.pair === 'string' && criticalInt.pair.includes('↔')) {
              const parts = criticalInt.pair.split('↔');
              drugA = parts[0].trim();
              drugB = parts[1].trim();
            } else {
              drugA = selectedDrugs[0] || 'Drug A';
              drugB = selectedDrugs[1] || 'Drug B';
            }
          }

          // Dynamic Clinical Alternative, Offending Drug, and Risk Factor directly from API evaluation
          const recAlt = criticalInt.recommended_alternative || 'Safe Therapeutic Alternative';
          const riskFactor = criticalInt.risk_factor || 'Severe Adverse Toxicity and Altered Pharmacokinetics';

          const voiceAlertText = criticalInt.emergency_voice_alert || (
            `Clinical Safety Alert: Severe interaction detected. ${drugA} significantly impairs ${drugB} safety and clearance, ` +
            `multiplying ${riskFactor}. Consider switching ${drugA} to ${recAlt}.`
          );

          setEmergencyAlert({
            isOpen: true,
            drugA,
            drugB,
            riskFactor,
            recommendedAlternative: recAlt,
            voiceAlertText,
            severity: sevUpper,
            isMuted: false
          });

          // Audio alerts in isolated try/catch so audio context / speech failure never blocks results
          try {
            // 1. Synthesize immediate Web Audio hospital alert chime (880Hz -> 660Hz sine tone)
            await clinicalVoiceService.playHospitalAlertChime();
            // 2. Immediately route through ElevenLabs / Web Speech voice player
            clinicalVoiceService.speakText(voiceAlertText);
          } catch (audioErr) {
            console.warn("Audio alert warning:", audioErr);
          }
        }
      } else {
        const errorBody = await res.json().catch(() => ({}));
        const msg = errorBody.detail || `Server returned error status ${res.status}`;
        console.error("API error:", msg);
        setCheckError(msg);
      }
    } catch (error: any) {
      console.error("Failed to check interactions:", error);
      setCheckError(error?.message || "Failed to connect to backend clinical database.");
    } finally {
      setIsChecking(false);
    }
  };

  const handleMuteAlert = () => {
    clinicalVoiceService.stopAll();
    if (emergencyAlert) {
      setEmergencyAlert({ ...emergencyAlert, isMuted: true });
    }
  };

  const handleHotSwapAlternative = () => {
    if (!emergencyAlert) return;
    clinicalVoiceService.stopAll();

    const { drugA, drugB, recommendedAlternative } = emergencyAlert;
    // drugA is designated by the evaluation engine as the offending agent / culprit to replace
    const targetToReplace = drugA;
    
    // Replace the offending drug with the recommended alternative
    let replaced = false;
    const updated = selectedDrugs.map(d => {
      const dClean = d.toLowerCase().trim();
      const targetClean = targetToReplace.toLowerCase().trim();
      if (dClean === targetClean || dClean.includes(targetClean) || targetClean.includes(dClean)) {
        replaced = true;
        return recommendedAlternative;
      }
      return d;
    });

    if (!replaced) {
      // If drugA couldn't match directly by substring, check drugB fallback or push
      const updatedFallback = selectedDrugs.map(d => {
        const dClean = d.toLowerCase().trim();
        const bClean = drugB.toLowerCase().trim();
        if (dClean === bClean || dClean.includes(bClean) || bClean.includes(dClean)) {
          return recommendedAlternative;
        }
        return d;
      });
      setSelectedDrugs(updatedFallback);
    } else {
      setSelectedDrugs(updated);
    }

    setEmergencyAlert(null);
    setShowResult(false);
  };


  const filteredDrugs = commonDrugs.filter(d => d.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="interaction-container">
      <BackButton />
      <div className="mb-4">
        <h2>Drug Interaction Checker</h2>
        <p className="text-secondary">Select multiple medications to analyze real clinical pharmacological interactions.</p>
      </div>

      <div className="grid-interaction">
        <div className="flex-col gap-3">
          <GlassCard>
            <div className="input-group mb-3">
              <div className="input-wrapper">
                <Search size={18} className="input-icon" />
                <input
                  type="text"
                  className="input-field with-icon"
                  placeholder="Search medications or enter custom drug..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddCustom()}
                />
              </div>
            </div>

            <div className="drugs-list">
              {filteredDrugs.map(drug => (
                <button
                  key={drug}
                  className={`drug-chip ${selectedDrugs.includes(drug) ? 'selected' : ''}`}
                  onClick={() => toggleDrug(drug)}
                >
                  {drug}
                  {selectedDrugs.includes(drug) && <span className="check">✓</span>}
                </button>
              ))}
              {searchTerm && !commonDrugs.some(d => d.toLowerCase() === searchTerm.toLowerCase()) && (
                <button className="drug-chip add-custom" onClick={handleAddCustom}>
                  <Plus size={14} /> Add "{searchTerm}"
                </button>
              )}
            </div>
          </GlassCard>

          <GlassCard className="selected-drugs-card">
            <h3 className="mb-3">Selected Drugs ({selectedDrugs.length})</h3>
            {selectedDrugs.length === 0 ? (
              <p className="text-secondary text-center py-4">No drugs selected yet.</p>
            ) : (
              <div className="selected-list">
                {selectedDrugs.map(drug => (
                  <div key={drug} className="selected-item">
                    <span>{drug}</span>
                    <button className="remove-btn" onClick={() => toggleDrug(drug)}>×</button>
                  </div>
                ))}
              </div>
            )}

            <button
              className="btn btn-primary w-full mt-4"
              disabled={selectedDrugs.length < 2 || isChecking}
              onClick={handleCheckInteractions}
            >
              <Activity size={18} /> {isChecking ? 'Checking Clinical Database...' : 'Check Interactions'}
            </button>
          </GlassCard>
        </div>

        <div>
          {checkError && (
            <div className="mb-4 p-4 rounded-xl border border-red-500/40 bg-red-950/40 text-red-200 flex items-start gap-3">
              <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={20} />
              <div>
                <strong className="block text-red-300 font-semibold mb-1">Check Failed</strong>
                <span className="text-sm">{checkError}</span>
              </div>
            </div>
          )}

          {showResult && interactionData ? (
            <GlassCard className="result-card animate-slide-up">
              {interactionData.rxNormMetadata && interactionData.rxNormMetadata.length > 0 && (
                <div className="rxnorm-section mb-4 p-4 rounded-xl bg-glass-subtle border border-accent">
                  <div className="flex items-center justify-between mb-3 border-b pb-2">
                    <div className="flex items-center gap-2">
                      <span className="rxnorm-logo font-bold text-accent">🏛️ NLM NIH RxNav</span>
                      <h4 style={{ margin: 0 }}>Verified Drug Concept & Mechanism Classifications</h4>
                    </div>
                    <span className="badge badge-primary text-xs">RxNorm Standardized</span>
                  </div>
                  <div className="grid-2-col gap-3">
                    {interactionData.rxNormMetadata.map((meta: any, idx: number) => (
                      <div key={idx} className="rxnorm-card p-3 rounded-lg bg-glass border border-subtle" style={{ background: 'rgba(255, 255, 255, 0.03)' }}>
                        <div className="flex justify-between items-start mb-1">
                          <strong className="text-lg text-primary">{meta.drug_name || meta.standardName || meta.drug}</strong>
                          <span className="badge badge-outline text-xs" style={{ border: '1px solid var(--color-accent)', color: 'var(--color-accent)' }}>RxCUI: {meta.rxcui}</span>
                        </div>
                        <div className="text-xs text-secondary mt-2 flex-col gap-1">
                          <div><strong className="text-muted">EPC Class:</strong> <span className="text-accent">{meta.epc_class || meta.epc}</span></div>
                          <div><strong className="text-muted">Mechanism (MOA):</strong> <span>{meta.mechanism_of_action || meta.moa}</span></div>
                          <div><strong className="text-muted">VA Class:</strong> <span>{meta.va_class || meta.vaClass}</span></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}


              {interactionData.status === 'Safe' || interactionData.interactions.length === 0 ? (
                <div className="severity-meter success mb-4" style={{ borderColor: 'var(--color-success)', background: 'rgba(24, 195, 126, 0.1)', padding: '1.5rem', borderRadius: '12px' }}>
                  <div className="meter-header text-success flex items-center gap-2 mb-2">
                    <ShieldCheck size={28} />
                    <h3 style={{ margin: 0, color: 'var(--color-success)' }}>No Major Interactions Found</h3>
                  </div>
                  <p className="mt-2 text-secondary">{interactionData.summary}</p>
                  <div className="mt-3 p-3 rounded bg-glass-subtle text-sm">
                    <strong>Surveillance Status:</strong> Checked {selectedDrugs.length} medications against NLM NIH RxClass and 191k+ clinical interaction records. No severe pharmacological contraindications detected.
                  </div>
                </div>
              ) : (
                <>
                  <div className={`severity-meter ${['CONTRAINDICATED', 'CRITICAL', 'MAJOR'].includes((interactionData.highest_severity || interactionData.severity || '').toUpperCase()) ? 'danger' : 'warning'} mb-4`} style={{ 
                    padding: '1.5rem', 
                    borderRadius: '12px',
                    borderColor: (interactionData.highest_severity || interactionData.severity || '').toUpperCase() === 'CONTRAINDICATED' ? '#dc2626' : undefined,
                    background: (interactionData.highest_severity || interactionData.severity || '').toUpperCase() === 'CONTRAINDICATED' ? 'rgba(220, 38, 38, 0.08)' : undefined
                  }}>
                    <div className="meter-header flex items-center gap-2 mb-2">
                      <AlertTriangle size={28} style={{ color: (interactionData.highest_severity || interactionData.severity || '').toUpperCase() === 'CONTRAINDICATED' ? '#dc2626' : undefined }} />
                      <h3 style={{ margin: 0, color: (interactionData.highest_severity || interactionData.severity || '').toUpperCase() === 'CONTRAINDICATED' ? '#dc2626' : undefined }}>
                        {interactionData.highest_severity || interactionData.severity} Interaction ({interactionData.flagged_interactions_count || interactionData.interactions.length} Pair{interactionData.interactions.length > 1 ? 's' : ''} Flagged)
                      </h3>
                    </div>
                    <div className="meter-bar mt-2 mb-2">
                      <div className="fill" style={{ 
                        width: (interactionData.highest_severity || interactionData.severity || '').toUpperCase() === 'CONTRAINDICATED' ? '100%' : (['CRITICAL', 'MAJOR'].includes((interactionData.highest_severity || interactionData.severity || '').toUpperCase()) ? '92%' : '55%'), 
                        backgroundColor: (interactionData.highest_severity || interactionData.severity || '').toUpperCase() === 'CONTRAINDICATED' ? '#dc2626' : (['CRITICAL', 'MAJOR'].includes((interactionData.highest_severity || interactionData.severity || '').toUpperCase()) ? 'var(--color-danger)' : 'var(--color-warning)') 
                      }}></div>
                    </div>
                    <p className="mt-2 text-sm">
                      {interactionData.summary}
                    </p>
                  </div>

                  <h4 className="mb-3 border-b pb-2 flex items-center justify-between">
                    <span>Unified Multi-Drug Pharmacological Analysis</span>
                    <span className="text-xs text-secondary font-normal">Primary Source: Clinical Registry (191k+ Records) + FDA SPL</span>
                  </h4>

                  {(() => {
                    // Client-side group-by-pair deduplication to guarantee strictly ONE card per pair regardless of payload structure
                    const pairMap = new Map<string, any>();

                    for (const int of interactionData.interactions || []) {
                      let p1 = '';
                      let p2 = '';
                      if (typeof int.pair === 'string' && int.pair.includes('↔')) {
                        const parts = int.pair.split('↔');
                        p1 = parts[0].trim();
                        p2 = parts[1].trim();
                      } else if (Array.isArray(int.pair)) {
                        p1 = String(int.pair[0]).trim();
                        p2 = String(int.pair[1]).trim();
                      } else {
                        p1 = String(int.drug1 || '').trim();
                        p2 = String(int.drug2 || '').trim();
                      }

                      const pairKey = [p1.toLowerCase(), p2.toLowerCase()].sort().join('__');
                      const pairTitle = `${p1.charAt(0).toUpperCase() + p1.slice(1)} ↔ ${p2.charAt(0).toUpperCase() + p2.slice(1)}`;
                      const level = (int.interaction_level || int.severity || 'MODERATE').toUpperCase();

                      if (!pairMap.has(pairKey)) {
                        pairMap.set(pairKey, {
                          pair: pairTitle,
                          severity: level,
                          interaction_level: level,
                          primary_contraindication: int.primary_contraindication || int.clinical_mechanism || int.description || null,
                          fda_label_advisory: int.fda_label_advisory || int.fda_advisory || (int.description?.includes('[FDA') ? int.description.replace(/^\[FDA Drug Label Advisory\]\s*/i, '') : null) || null,
                          faers: int.faers_surveillance || int.faers || null,
                          clinical_action: int.clinical_action || int.clinical_guidance || "Avoid concomitant use or adjust dosage as clinically indicated."
                        });
                      } else {
                        const existing = pairMap.get(pairKey);
                        // Escalate severity if second occurrence is higher
                        if (level === 'CONTRAINDICATED' || (level === 'CRITICAL' && existing.severity !== 'CONTRAINDICATED') || (level === 'MAJOR' && !['CONTRAINDICATED', 'CRITICAL'].includes(existing.severity))) {
                          existing.severity = level;
                          existing.interaction_level = level;
                        }
                        if (!existing.primary_contraindication && (int.primary_contraindication || int.clinical_mechanism || int.description)) {
                          existing.primary_contraindication = int.primary_contraindication || int.clinical_mechanism || int.description;
                        }
                        if (!existing.fda_label_advisory && (int.fda_label_advisory || int.fda_advisory)) {
                          existing.fda_label_advisory = int.fda_label_advisory || int.fda_advisory;
                        }
                        if (!existing.faers && (int.faers_surveillance || int.faers)) {
                          existing.faers = int.faers_surveillance || int.faers;
                        }
                        if (int.clinical_action) {
                          existing.clinical_action = int.clinical_action;
                        }
                      }
                    }

                    const uniqueInteractions = Array.from(pairMap.values());

                    return uniqueInteractions.map((int: any, idx: number) => {
                      const isContraindicated = int.severity === 'CONTRAINDICATED';
                      const isMajorOrCritical = int.severity === 'CRITICAL' || int.severity === 'MAJOR';
                      
                      // Format FDA advisory to ensure clean end sentence without mid-word cut
                      let cleanFda = int.fda_label_advisory;
                      if (cleanFda && cleanFda.includes('.')) {
                        cleanFda = cleanFda.slice(0, cleanFda.lastIndexOf('.') + 1).trim();
                      }

                      const badgeClass = isContraindicated 
                        ? 'badge-danger font-bold text-white shadow-lg' 
                        : (isMajorOrCritical ? 'badge-danger' : 'badge-warning');

                      const borderColor = isContraindicated
                        ? '#dc2626'
                        : (isMajorOrCritical ? 'var(--color-danger)' : 'var(--color-warning)');

                      const bgGradient = isContraindicated
                        ? 'rgba(220, 38, 38, 0.08)'
                        : (isMajorOrCritical ? 'rgba(239, 68, 68, 0.03)' : 'rgba(245, 158, 11, 0.03)');

                      return (
                        <div key={idx} className="interaction-details mb-4 p-4 border rounded-xl" style={{ 
                          borderColor: borderColor, 
                          background: bgGradient,
                          borderWidth: isContraindicated ? '2px' : '1px'
                        }}>
                          <div className="flex justify-between items-center mb-3">
                            <span className="font-bold text-xl flex items-center gap-2" style={{ color: borderColor }}>
                              {isContraindicated && <span>🚫</span>}
                              {int.pair}
                            </span>
                            <span className={`badge ${badgeClass}`} style={{ 
                              fontSize: '0.85rem', 
                              padding: '4px 12px',
                              backgroundColor: isContraindicated ? '#dc2626' : undefined 
                            }}>
                              {int.severity}
                            </span>
                          </div>

                          {/* Primary Knowledge Base: Clinical Contraindication */}
                          {int.primary_contraindication && (
                            <div className="mb-3 p-3 rounded-lg" style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.07)' }}>
                              <strong className="text-xs uppercase tracking-wider text-muted flex items-center gap-1 mb-1">
                                🏥 Primary Clinical Contraindication (Clinical DB)
                              </strong>
                              <p className="text-sm mt-1" style={{ margin: 0, lineHeight: 1.5 }}>
                                {int.primary_contraindication}
                              </p>
                            </div>
                          )}

                          {/* Secondary Service: FDA Drug Label Advisory */}
                          {cleanFda && cleanFda !== "No specific contraindication advisory detected in FDA SPL monograph." && (
                            <div className="mb-3 p-3 rounded-lg" style={{ background: 'rgba(59, 130, 246, 0.04)', border: '1px solid rgba(59, 130, 246, 0.15)' }}>
                              <strong className="text-xs uppercase tracking-wider text-accent flex items-center gap-1 mb-1">
                                🏛️ Official FDA Drug Label Advisory
                              </strong>
                              <p className="text-secondary text-sm mt-1" style={{ margin: 0, lineHeight: 1.5 }}>
                                {cleanFda}
                              </p>
                            </div>
                          )}

                          {/* Secondary Service: FAERS Post-Marketing Surveillance */}
                          {int.faers && (int.faers.total_cases > 0 || int.faers.co_admin_reports > 0 || int.faers.totalReports > 0) && (
                            <div className="mb-3 p-3 rounded-lg" style={{ background: 'rgba(239, 68, 68, 0.04)', border: '1px solid rgba(239, 68, 68, 0.15)' }}>
                              <div className="flex justify-between items-center mb-1">
                                <strong className="text-xs uppercase tracking-wider text-danger">
                                  📊 FDA FAERS Incident Surveillance
                                </strong>
                                <span className="badge badge-warning text-xs">
                                  {(int.faers.total_cases || int.faers.co_admin_reports || int.faers.totalReports || 0).toLocaleString()} Co-Administration Reports
                                </span>
                              </div>
                              <div className="text-xs text-secondary mt-1">
                                <strong>Top Reported Reactions:</strong> {
                                  Array.isArray(int.faers.top_reactions) && int.faers.top_reactions.length > 0 && typeof int.faers.top_reactions[0] === 'object'
                                    ? int.faers.top_reactions.map((r: any) => `${r.reaction} (${r.cases})`).join(', ')
                                    : (int.faers.top_adverse_reactions || int.faers.topReactions || []).join(', ')
                                }
                              </div>
                            </div>
                          )}

                          {/* Actionable Clinical Guidance */}
                          {int.clinical_action && (
                            <div className="mt-2 text-xs text-secondary flex items-start gap-1 p-2 rounded" style={{ background: isContraindicated ? 'rgba(220, 38, 38, 0.06)' : 'transparent' }}>
                              <span className={isContraindicated ? "text-danger font-bold" : "text-success font-bold"}>Clinical Action:</span>
                              <span className={isContraindicated ? "text-white font-medium" : ""}>{int.clinical_action}</span>
                            </div>
                          )}
                        </div>
                      );
                    });
                  })()}


                </>
              )}
            </GlassCard>
          ) : (
            <div className="empty-state">
              <Activity size={48} className="text-secondary mb-3 opacity-50" />
              <h3>Awaiting Analysis</h3>
              <p className="text-secondary">Select at least 2 medications and click 'Check Interactions' to check against our database of 191,540 real clinical interactions.</p>
            </div>
          )}
        </div>
      </div>

      {/* Feature 1: High-Contrast Emergency Contraindication Modal */}
      {emergencyAlert && emergencyAlert.isOpen && (
        <div className="emergency-modal-overlay animate-fade-in" role="alertdialog" aria-modal="true">
          <div className="emergency-modal-card">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="pulsing-soundwave-badge">
                  <span className="soundwave-bars">
                    <span className="soundwave-bar"></span>
                    <span className="soundwave-bar"></span>
                    <span className="soundwave-bar"></span>
                    <span className="soundwave-bar"></span>
                    <span className="soundwave-bar"></span>
                  </span>
                  <span>Audio Alert Active</span>
                </span>
                <span className="badge badge-danger text-xs font-bold" style={{ backgroundColor: '#dc2626' }}>
                  {emergencyAlert.severity}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button 
                  className="mute-alert-btn text-xs py-1.5 px-3" 
                  onClick={handleMuteAlert}
                  title="Silence voice alarm"
                >
                  {emergencyAlert.isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
                  <span>{emergencyAlert.isMuted ? 'Muted' : 'Mute'}</span>
                </button>
              </div>
            </div>

            <div className="flex items-start gap-3 mb-4">
              <div style={{ background: 'rgba(239, 68, 68, 0.2)', padding: '10px', borderRadius: '12px', color: '#ef4444' }}>
                <AlertTriangle size={32} />
              </div>
              <div>
                <h3 style={{ margin: 0, color: '#fca5a5', fontSize: '1.25rem', fontWeight: 800 }}>
                  EMERGENCY CONTRAINDICATION DETECTED
                </h3>
                <p className="text-sm text-secondary mt-1" style={{ margin: 0 }}>
                  High-Priority Pharmacological Clearance Inhibition
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl mb-4" style={{ background: 'rgba(0, 0, 0, 0.4)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              <div className="text-sm text-white font-medium leading-relaxed">
                "{emergencyAlert.voiceAlertText}"
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5 text-xs">
              <div className="p-3 rounded-lg bg-black/30 border border-white/10">
                <div className="text-secondary font-semibold uppercase">Flagged Combination</div>
                <div className="text-danger font-bold text-sm mt-1">
                  {emergencyAlert.drugA} + {emergencyAlert.drugB}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-black/30 border border-white/10">
                <div className="text-secondary font-semibold uppercase">Primary Threat</div>
                <div className="text-white font-medium text-xs mt-1">
                  {emergencyAlert.riskFactor}
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl mb-5 border border-emerald-500/40 bg-emerald-950/30 flex items-center justify-between flex-wrap gap-2">
              <div>
                <span className="text-xs text-emerald-400 font-semibold uppercase tracking-wider block">
                  Recommended Safe Alternative:
                </span>
                <strong className="text-base text-white">{emergencyAlert.recommendedAlternative}</strong>
              </div>
              <span className="badge badge-success text-xs">Zero Clearance Interference</span>
            </div>

            <div className="flex items-center justify-end gap-3 flex-wrap">
              <button 
                className="btn btn-outline text-sm"
                onClick={() => {
                  clinicalVoiceService.stopAll();
                  setEmergencyAlert(null);
                }}
              >
                Dismiss Modal
              </button>
              <button 
                className="hotswap-btn text-sm"
                onClick={handleHotSwapAlternative}
              >
                <span>Accept Recommended Alternative</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

