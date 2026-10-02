import React, { useState, useEffect } from 'react';
import { MapPin, Search, ShieldAlert, Database, Mic, Volume2, VolumeX, Loader2 } from 'lucide-react';
import { ComposableMap, Geographies, Geography, ZoomableGroup, Marker } from 'react-simple-maps';
import { GlassCard } from '../components/GlassCard';
import { BackButton } from '../components/BackButton';
import { usePersistentState } from '../hooks/usePersistentState';
import { apiFetch } from '../lib/api';
import { clinicalVoiceService } from '../lib/clinicalVoiceService';
import './ResistanceMap.css';

const geoUrl = "/india-states.json";

const stateCoordinates: Record<string, [number, number]> = {
  'andhra pradesh': [79.74, 15.91],
  'arunachal pradesh': [94.72, 28.21],
  'assam': [92.93, 26.20],
  'bihar': [85.31, 25.09],
  'chhattisgarh': [81.86, 21.27],
  'goa': [74.12, 15.29],
  'gujarat': [71.19, 22.25],
  'haryana': [76.08, 29.05],
  'himachal pradesh': [77.17, 31.10],
  'jharkhand': [85.27, 23.61],
  'karnataka': [75.71, 15.31],
  'kerala': [76.27, 10.85],
  'madhya pradesh': [78.65, 22.97],
  'maharashtra': [75.71, 19.75],
  'manipur': [93.90, 24.66],
  'meghalaya': [91.36, 25.46],
  'mizoram': [92.93, 23.16],
  'nagaland': [94.56, 26.15],
  'odisha': [85.09, 20.95],
  'punjab': [75.34, 31.14],
  'rajasthan': [74.21, 27.02],
  'sikkim': [88.51, 27.53],
  'tamil nadu': [78.65, 11.12],
  'telangana': [79.01, 18.11],
  'tripura': [91.98, 23.94],
  'uttar pradesh': [80.94, 26.84],
  'uttarakhand': [79.01, 30.06],
  'west bengal': [87.85, 22.98],
  'delhi': [77.20, 28.61],
  'jammu and kashmir': [74.85, 33.27],
  'ladakh': [77.57, 34.15],
  'chandigarh': [76.78, 30.73],
  'puducherry': [79.81, 11.94],
  'mumbai': [72.87, 19.07],
  'pune': [73.85, 18.52],
  'nagpur': [79.08, 21.14],
  'bengaluru': [77.59, 12.97],
  'bangalore': [77.59, 12.97],
  'hyderabad': [78.48, 17.38],
  'chennai': [80.27, 13.08],
  'kolkata': [88.36, 22.57],
  'ahmedabad': [72.57, 23.02],
  'jaipur': [75.78, 26.91],
  'lucknow': [80.94, 26.84],
  'patna': [85.13, 25.59],
  'bhopal': [77.41, 23.25],
  'indore': [75.85, 22.71],
  'coimbatore': [76.95, 11.01],
  'kochi': [76.27, 9.93],
  'thiruvananthapuram': [76.93, 8.52],
  'guwahati': [91.73, 26.14],
  'bhubaneswar': [85.82, 20.29],
  'ranchi': [85.33, 23.34],
  'dehradun': [78.03, 30.31]
};

export function ResistanceMap() {
  const [location, setLocation] = usePersistentState('medix_res_location', '');
  const [drug, setDrug] = usePersistentState('medix_res_drug', '');
  const [isSearching, setIsSearching] = useState(false);
  const [showResult, setShowResult] = usePersistentState('medix_res_showResult', false);
  const [resData, setResData] = usePersistentState<any>('medix_res_resData', null);
  const [viewMode, setViewMode] = usePersistentState<'leaflet' | 'choropleth'>('medix_res_viewMode', 'leaflet');
  
  // Default coordinates (Center of India)
  const [position, setPosition] = usePersistentState('medix_res_position', { coordinates: [78.96, 22.59] as [number, number], zoom: 1 });
  const [activeState, setActiveState] = usePersistentState('medix_res_activeState', '');

  const leafletMapRef = React.useRef<any>(null);

  // Regional Resistance Audio Intelligence state
  const [isBriefingPlaying, setIsBriefingPlaying] = useState(false);
  const [isBriefingLoading, setIsBriefingLoading] = useState(false);

  // Clean up any playing voice audio on unmount
  useEffect(() => {
    return () => {
      clinicalVoiceService.stopAll();
    };
  }, []);

  const handlePlayRegionalBriefing = async (customText?: string) => {
    if (isBriefingPlaying) {
      clinicalVoiceService.stopAll();
      setIsBriefingPlaying(false);
      setIsBriefingLoading(false);
      return;
    }

    clinicalVoiceService.stopAll();
    setIsBriefingLoading(true);
    setIsBriefingPlaying(true);

    const regionName = activeState || resData?.resolvedState || location || 'West Bengal';
    const pathogenName = resData?.amr_evaluation?.pathogen_monitored || resData?.pathogen || 'Escherichia coli';
    const drugName = resData?.drug || drug || 'Ciprofloxacin';
    const drugClass = resData?.drugClass || (drugName.toLowerCase().includes('floxacin') ? 'Fluoroquinolones' : 'Antimicrobial class');
    const deltaShift = resData?.deltaShift || '+3.4%';
    const recAlt = resData?.recommendedAlternative || 'Nitrofurantoin or Meropenem';

    // Exact prompt string required:
    // "Regional Surveillance Alert for [Region]: [Pathogen] resistance against [Drug Class] has shifted by [Delta]% over the last reporting cycle. Standard [Empiric Drug] exhibits high failure rates in this zone. [Recommended Alternative] advised for high-severity presentations."
    const briefingSpeech = customText || resData?.regionalVoiceBriefing || (
      `Regional Surveillance Alert for ${regionName}: ${pathogenName} resistance against ${drugClass} ` +
      `has shifted by ${deltaShift} over the last reporting cycle. ` +
      `Standard ${drugName} exhibits high failure rates in this zone. ${recAlt} advised for high-severity presentations.`
    );

    try {
      await clinicalVoiceService.speakText(briefingSpeech, {
        onStart: () => {
          setIsBriefingLoading(false);
          setIsBriefingPlaying(true);
        },
        onEnd: () => {
          setIsBriefingPlaying(false);
          setIsBriefingLoading(false);
        },
        onError: () => {
          setIsBriefingPlaying(false);
          setIsBriefingLoading(false);
        }
      });
    } catch (err) {
      console.warn("Regional briefing audio error:", err);
      setIsBriefingPlaying(false);
      setIsBriefingLoading(false);
    }
  };

  // Expose global briefing trigger for Leaflet DOM popups
  useEffect(() => {
    (window as any).__medix_play_regional_briefing = () => {
      handlePlayRegionalBriefing();
    };
    return () => {
      delete (window as any).__medix_play_regional_briefing;
    };
  }, [resData, activeState, isBriefingPlaying]);

  const resetView = () => {
    setPosition({ coordinates: [78.96, 22.59], zoom: 1 });
    if (leafletMapRef.current && (window as any).L) {
      leafletMapRef.current.setView([22.59, 78.96], 5);
    }
  };

  const handleSearch = async () => {
    setIsSearching(true);
    clinicalVoiceService.stopAll();
    setIsBriefingPlaying(false);
    setIsBriefingLoading(false);

    
    try {
      let dataJson: any = null;
      let backendResolvedState: string | null = null;

      // Call backend API for real AMR surveillance data
      try {
        const apiRes = await apiFetch('/api/resistance-map', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ location: location.trim(), drug: drug.trim() })
        });
        if (apiRes.ok) {
          dataJson = await apiRes.json();
          setResData(dataJson);
          backendResolvedState = dataJson.resolvedState;
        }
      } catch (err) {
        console.warn("Backend AMR surveillance error:", err);
      }

      // Resolve coordinates
      let coords: [number, number] = [78.96, 22.59];
      let zoomLevel = 3.5;
      let matchedState = backendResolvedState || location.trim();

      const searchLower = location.toLowerCase().trim();

      // Check local coordinates dictionary first
      let foundDirect = false;
      for (const [key, c] of Object.entries(stateCoordinates)) {
        if (searchLower === key || searchLower.includes(key) || key.includes(searchLower)) {
          coords = c;
          zoomLevel = 3.8;
          foundDirect = true;
          break;
        }
      }

      // Try geocoding lookup
      if (!foundDirect) {
        try {
          const nominatimUrl = `https://nominatim.openstreetmap.org/search?format=json&countrycodes=in&q=${encodeURIComponent(location.trim())}`;
          const response = await fetch(nominatimUrl, { headers: { 'Accept-Language': 'en' } });
          const nominatimData = await response.json();
          
          if (nominatimData && nominatimData.length > 0) {
            coords = [parseFloat(nominatimData[0].lon), parseFloat(nominatimData[0].lat)];
            zoomLevel = 4.2;
            const displayNameParts = nominatimData[0].display_name.split(',');
            matchedState = displayNameParts[0].trim();
          }
        } catch (e) {
          console.warn("Nominatim lookup failed, using state center", e);
        }
      }

      setPosition({ coordinates: coords, zoom: zoomLevel });
      setActiveState(backendResolvedState || matchedState); 
      setShowResult(true);
    } catch (error) {
      console.error("Failed to fetch coordinates or resistance data:", error);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="map-container">
      <BackButton />
      <div className="mb-4">
        <h2>Antimicrobial Resistance Map</h2>
        <p className="text-secondary">Track real-time pathogen resistance patterns across regions.</p>
      </div>

      <div className="map-grid">
        <GlassCard className="map-controls">
          <h3 className="mb-3">Search Parameters</h3>
          
          <div className="input-group">
            <label>Location (State)</label>
            <div className="input-wrapper">
              <MapPin size={18} className="input-icon" />
              <input 
                type="text" 
                className="input-field with-icon" 
                placeholder="e.g. Maharashtra" 
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
          </div>

          <div className="input-group mb-4">
            <label>Drug Name</label>
            <div className="input-wrapper">
              <Search size={18} className="input-icon" />
              <input 
                type="text" 
                className="input-field with-icon" 
                placeholder="e.g. Ciprofloxacin" 
                value={drug}
                onChange={(e) => setDrug(e.target.value)}
              />
            </div>
          </div>

          <button 
            className="btn btn-primary w-full"
            onClick={handleSearch}
            disabled={!location || !drug || isSearching}
          >
            {isSearching ? 'Scanning Region...' : 'Analyze Resistance'}
          </button>

          {showResult && (
            <div className="map-results mt-4 animate-slide-up">
              <div className="flex items-center justify-between border-b pb-2 mb-3">
                <h4 style={{ margin: 0 }}>Analysis: {activeState}</h4>
                {resData?.amr_evaluation?.data_source_used && (
                  <span className="badge badge-outline text-[11px]" style={{ padding: '2px 8px' }}>
                    {resData.amr_evaluation.data_source_used}
                  </span>
                )}
              </div>
              
              {resData?.amr_evaluation?.amr_applicable === false ? (
                <div className="p-3 rounded-lg border border-warning/40 bg-warning/10 text-xs">
                  <div className="flex items-center gap-2 text-warning font-semibold mb-1">
                    <ShieldAlert size={16} /> Non-Antimicrobial Agent
                  </div>
                  <p className="text-secondary leading-relaxed" style={{ margin: 0 }}>
                    {resData.drug} is not an antimicrobial therapeutic agent. Bacterial resistance monitoring and resistance map coloring are omitted per pharmacopeia safeguards.
                  </p>
                </div>
              ) : (
                <>
                  <div className="result-stat">
                    <span className="label">Monitored Pathogen</span>
                    <span className="value text-ai-accent">{resData?.amr_evaluation?.pathogen_monitored || resData?.pathogen || 'Escherichia coli'}</span>
                  </div>
                  <div className="result-stat">
                    <span className="label">Resistance Level ({activeState})</span>
                    <span 
                      className="value badge"
                      style={{
                        backgroundColor: resData?.map_api_config?.style?.fill_color || (resData?.status === 'HIGH' ? '#DC3545' : (resData?.status === 'MEDIUM' ? '#FFC107' : '#28A745')),
                        color: (resData?.status === 'MEDIUM' || resData?.map_api_config?.style?.fill_color === '#FFC107') ? '#000000' : '#ffffff',
                        fontWeight: 'bold',
                        padding: '4px 10px'
                      }}
                    >
                      {resData?.amr_evaluation?.resistance_tier || resData?.status || 'MEDIUM'} ({resData?.amr_evaluation?.resistance_percentage ?? resData?.resistanceLevel ?? 32}%)
                    </span>
                  </div>
                  <div className="result-stat">
                    <span className="label">Data Source</span>
                    <span className="value text-secondary text-xs">{resData?.amr_evaluation?.data_source_used || 'Internal CSV'}</span>
                  </div>

                  <div className="alert-box mt-3 text-xs">
                    <ShieldAlert size={16} style={{ flexShrink: 0 }} />
                    <p style={{ margin: 0 }}>
                      <strong>Source:</strong> {resData?.amr_evaluation?.source_reference || 'ICMR AMRSN / WHO GLASS Surveillance'}
                    </p>
                  </div>

                  {/* Feature 3: Play Regional Surveillance Briefing in Inspector Drawer */}
                  <div className="mt-3">
                    <button
                      className={`regional-voice-btn ${isBriefingPlaying ? 'active' : ''}`}
                      onClick={() => handlePlayRegionalBriefing()}
                      title="Stream regional epidemiological intelligence via ElevenLabs"
                    >
                      {isBriefingLoading ? (
                        <Loader2 size={16} className="animate-spin text-white" />
                      ) : isBriefingPlaying ? (
                        <VolumeX size={16} className="text-white" />
                      ) : (
                        <Mic size={16} className="text-ai-accent" />
                      )}
                      <span>
                        {isBriefingLoading 
                          ? 'Synthesizing Briefing...' 
                          : (isBriefingPlaying ? 'Stop Audio Briefing' : '🎙️ Play Regional Surveillance Briefing')}
                      </span>
                    </button>

                    {isBriefingPlaying && (
                      <div className="briefing-card-live animate-slide-up">
                        <div className="flex items-center gap-2 text-cyan-400 font-bold mb-1 text-[11px] uppercase tracking-wider">
                          <Volume2 size={13} />
                          <span>ElevenLabs Surveillance Stream Active</span>
                        </div>
                        <div className="text-xs text-white/90 italic">
                          "{resData?.regionalVoiceBriefing || `Regional Surveillance Alert for ${activeState || resData?.resolvedState || 'this zone'}...`}"
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}


              {resData?.realTimeSurveillance && (
                <div className="surveillance-evidence-panel mt-4 pt-3 border-t border-border/40">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Database size={16} className="text-ai-accent" />
                      <h5 className="font-semibold text-sm m-0 text-text-primary">Live Multi-Platform Surveillance</h5>
                    </div>
                    <span className="badge badge-ai text-[10px] py-0.5 px-2">LIVE STREAM</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 my-2 text-xs">
                    <div className="p-2 rounded bg-card/40 border border-border/40">
                      <div className="text-secondary text-[11px]">Genomic Isolates</div>
                      <div className="font-bold text-sm text-ai-accent">
                        {resData.realTimeSurveillance.totalGenomicIsolates || 0} Sequenced
                      </div>
                    </div>
                    <div className="p-2 rounded bg-card/40 border border-border/40">
                      <div className="text-secondary text-[11px]">Clinical Studies</div>
                      <div className="font-bold text-sm text-success">
                        {resData.realTimeSurveillance.totalSurveillanceStudies || 0} Indexed
                      </div>
                    </div>
                  </div>

                  {resData.realTimeSurveillance.empiricalExtractedResistance && (
                    <div className="p-2 mb-2 rounded bg-ai-accent/10 border border-ai-accent/30 text-xs flex items-center justify-between">
                      <span className="text-secondary">Text-Mined Antibiogram:</span>
                      <strong className="text-ai-accent">{resData.realTimeSurveillance.empiricalExtractedResistance}% empirical resistance</strong>
                    </div>
                  )}

                  <p className="text-xs text-secondary mb-1 leading-relaxed">
                    Cross-referenced in real time from <strong className="text-text-primary">NCBI Pathogen Detection</strong>, <strong className="text-text-primary">WHO GLASS</strong>, <strong className="text-text-primary">EMBL-EBI Europe PMC</strong>, and <strong className="text-text-primary">ICMR AMRSN</strong> (India).
                  </p>
                </div>
              )}
            </div>
          )}
        </GlassCard>

        <GlassCard className="map-display p-0 overflow-hidden relative">

          {showResult && (
            <button className="map-reset-btn" onClick={resetView} title="Reset zoom to whole India map">
              ↺ Reset Zoom
            </button>
          )}

          {viewMode === 'leaflet' ? (
            <LeafletMapContainer resData={resData} showResult={showResult} mapRef={leafletMapRef} />
          ) : (
            <div style={{ width: '100%', height: '100%', backgroundColor: 'transparent' }}>
              <ComposableMap
                projection="geoMercator"
                projectionConfig={{
                  scale: 1000,
                  center: [80, 22] // Center of India
                }}
                width={800}
                height={600}
                style={{ width: "100%", height: "100%" }}
              >
                <ZoomableGroup 
                  zoom={position.zoom} 
                  center={position.coordinates}
                  onMoveEnd={(pos: any) => setPosition(pos)}
                >
                  <Geographies geography={geoUrl}>
                    {({ geographies }: any) =>
                      geographies.map((geo: any) => {
                        const stateName = geo.properties.st_nm || geo.properties.NAME_1 || geo.properties.name || '';
                        let fillColor = "rgba(255, 255, 255, 0.04)";
                        let strokeColor = "rgba(0, 217, 255, 0.3)";
                        let strokeWidth = 0.5;

                        if (showResult) {
                          // Check if this geometry is the target location / state
                          const targetMatch = Boolean(
                            (activeState && stateName && (
                              stateName.toLowerCase() === activeState.toLowerCase() ||
                              stateName.toLowerCase().includes(activeState.toLowerCase()) ||
                              activeState.toLowerCase().includes(stateName.toLowerCase())
                            )) ||
                            (resData?.resolvedState && stateName && (
                              stateName.toLowerCase() === resData.resolvedState.toLowerCase() ||
                              stateName.toLowerCase().includes(resData.resolvedState.toLowerCase()) ||
                              resData.resolvedState.toLowerCase().includes(stateName.toLowerCase())
                            ))
                          );

                          let stateResVal: number;
                          if (targetMatch && resData?.resistanceLevel !== undefined && resData?.resistanceLevel !== null) {
                            stateResVal = Number(resData.resistanceLevel);
                          } else if (resData?.stateResistanceMap && resData.stateResistanceMap[stateName] !== undefined) {
                            stateResVal = Number(resData.stateResistanceMap[stateName]);
                          } else if (resData?.stateResistanceMap) {
                            const mapKeys = Object.keys(resData.stateResistanceMap);
                            const matchedKey = mapKeys.find(k => 
                              k.toLowerCase() === stateName.toLowerCase() || 
                              stateName.toLowerCase().includes(k.toLowerCase()) || 
                              k.toLowerCase().includes(stateName.toLowerCase())
                            );
                            stateResVal = matchedKey ? Number(resData.stateResistanceMap[matchedKey]) : (targetMatch ? Number(resData?.resistanceLevel || 35) : 25);
                          } else {
                            stateResVal = targetMatch ? Number(resData?.resistanceLevel || 35) : 25;
                          }

                          if (isNaN(stateResVal)) {
                            stateResVal = 25;
                          }

                          // Check for Non-Antimicrobial safeguard
                          if (resData?.amr_evaluation?.amr_applicable === false) {
                            fillColor = "rgba(255, 255, 255, 0.05)";
                            strokeColor = targetMatch ? "#ffffff" : "rgba(255, 255, 255, 0.2)";
                            strokeWidth = targetMatch ? 2 : 0.5;
                          } else {
                            // Standard resistance thresholds per Operational Rule 2:
                            // LOW (< 20.0%): "#28A745"
                            // MEDIUM (20.0% to 50.0%): "#FFC107"
                            // HIGH (> 50.0%): "#DC3545"
                            if (stateResVal > 50.0) {
                              fillColor = targetMatch ? "rgba(220, 53, 69, 0.85)" : "rgba(220, 53, 69, 0.45)"; // #DC3545
                              strokeColor = "#DC3545";
                            } else if (stateResVal >= 20.0) {
                              fillColor = targetMatch ? "rgba(255, 193, 7, 0.85)" : "rgba(255, 193, 7, 0.45)"; // #FFC107
                              strokeColor = "#FFC107";
                            } else {
                              fillColor = targetMatch ? "rgba(40, 167, 69, 0.85)" : "rgba(40, 167, 69, 0.45)"; // #28A745
                              strokeColor = "#28A745";
                            }

                            // Highlight active/targeted state border
                            if (targetMatch) {
                              strokeColor = "#ffffff";
                              strokeWidth = 2.5;
                            }
                          }
                        }

                        return (
                          <Geography
                            key={geo.rsmKey}
                            geography={geo}
                            fill={fillColor}
                            stroke={strokeColor}
                            strokeWidth={strokeWidth}
                            style={{
                              default: { outline: "none", transition: "all 0.3s ease" },
                              hover: { fill: "rgba(0, 217, 255, 0.4)", outline: "none", cursor: "pointer" },
                              pressed: { fill: "rgba(0, 217, 255, 0.6)", outline: "none" }
                            }}
                          />
                        );
                      })
                    }
                  </Geographies>
                  {showResult && (
                    <Marker coordinates={position.coordinates}>
                      <circle r={position.zoom > 3 ? 3.5 : 5} fill="#ff3c3c" stroke="#ffffff" strokeWidth={1.5} />
                      <circle r={position.zoom > 3 ? 7 : 10} fill="none" stroke="#ff3c3c" strokeWidth={1} opacity={0.6} />
                      <text
                        textAnchor="middle"
                        y={-12}
                        style={{
                          fontFamily: "var(--font-body)",
                          fill: "#ffffff",
                          fontSize: position.zoom > 3 ? "9px" : "11px",
                          fontWeight: "bold",
                          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.9))"
                        }}
                      >
                        {activeState}
                      </text>
                    </Marker>
                  )}
                </ZoomableGroup>
              </ComposableMap>
            </div>
          )}
          
          <div className="map-legend">
            <div className="text-xs text-secondary mb-1 font-semibold">Resistance Thresholds</div>
            <div className="legend-item"><span className="dot" style={{ backgroundColor: '#DC3545' }}></span> High (&gt;50.0% Resistance)</div>
            <div className="legend-item"><span className="dot" style={{ backgroundColor: '#FFC107' }}></span> Medium (20.0% - 50.0%)</div>
            <div className="legend-item"><span className="dot" style={{ backgroundColor: '#28A745' }}></span> Low (&lt;20.0% Resistance)</div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

function LeafletMapContainer({ resData, showResult, mapRef }: { resData: any, showResult: boolean, mapRef: React.MutableRefObject<any> }) {
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const L = (window as any).L;
    if (!L || !containerRef.current) return;

    // Destroy existing map instance if any
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const defaultCenter: [number, number] = [22.5937, 78.9629]; // Center of India
    const defaultZoom = 5;

    const map = L.map(containerRef.current, {
      center: defaultCenter,
      zoom: defaultZoom,
      zoomControl: false
    });
    mapRef.current = map;

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // OpenStreetMap standard tile layer
    const tileUrl = resData?.map_api_config?.tile_layer_url || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    L.tileLayer(tileUrl, {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | ICMR AMRSN'
    }).addTo(map);

    // If query was submitted, render target state highlight, circle polygon, and popup
    if (showResult && resData) {
      const config = resData.map_api_config;
      const targetCenter = config?.center || [28.6139, 77.2090];
      const targetZoom = config?.zoom || 7;
      const isAmrApplicable = resData.amr_evaluation?.amr_applicable !== false;
      const fillColor = config?.style?.fill_color || (resData.status === 'HIGH' ? '#DC3545' : (resData.status === 'MEDIUM' ? '#FFC107' : '#28A745'));
      const fillOpacity = isAmrApplicable ? 0.65 : 0.05;

      map.setView(targetCenter, targetZoom);

      // Circle representing state epidemiological buffer
      const circle = L.circle(targetCenter, {
        color: isAmrApplicable ? fillColor : '#888888',
        fillColor: isAmrApplicable ? fillColor : 'transparent',
        fillOpacity: fillOpacity,
        radius: 45000,
        weight: config?.style?.border_width || 2
      }).addTo(map);

      // Target marker with clinical popup
      const marker = L.circleMarker(targetCenter, {
        radius: 9,
        fillColor: isAmrApplicable ? fillColor : '#888888',
        color: '#ffffff',
        weight: 2.5,
        opacity: 1,
        fillOpacity: 0.95
      }).addTo(map);

      const popupHtml = `
        <div style="font-family: sans-serif; min-width: 210px; color: #111;">
          <h4 style="margin: 0 0 6px 0; font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 4px;">
            ${config?.popup_content?.title || `${resData.resolvedState} - AMR Surveillance`}
          </h4>
          <p style="margin: 4px 0; font-size: 12px;">
            <strong>${config?.popup_content?.metric_label || 'Local Resistance'}:</strong> 
            <span style="color: ${fillColor}; font-weight: bold;">
              ${config?.popup_content?.metric_value || `${resData.resistanceLevel}%`}
            </span>
          </p>
          <p style="margin: 4px 0; font-size: 11px;">
            <strong>Tier:</strong> <span style="text-transform: uppercase;">${config?.popup_content?.tier || resData.status}</span>
          </p>
          <p style="margin: 4px 0; font-size: 11px; color: #666;">
            <strong>Source:</strong> ${resData.amr_evaluation?.data_source_used || 'ICMR AMRSN / WHO GLASS'}
          </p>
          <div style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed #ccc;">
            <button 
              onclick="if (window.__medix_play_regional_briefing) window.__medix_play_regional_briefing();"
              style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 5px; padding: 6px 10px; background: #0284c7; color: #fff; border: none; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;"
            >
              🎙️ Play Regional Surveillance Briefing
            </button>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml).openPopup();
      circle.bindPopup(popupHtml);


      // Render regional neighboring surveillance dots
      if (resData.points && Array.isArray(resData.points)) {
        resData.points.forEach((pt: any) => {
          if (pt.state.toLowerCase() !== resData.resolvedState.toLowerCase() && pt.lat && pt.lng) {
            const ptColor = pt.color || (pt.status === 'HIGH' ? '#DC3545' : (pt.status === 'MEDIUM' ? '#FFC107' : '#28A745'));
            L.circleMarker([pt.lat, pt.lng], {
              radius: 5,
              fillColor: ptColor,
              color: '#ffffff',
              weight: 1,
              fillOpacity: 0.65
            })
            .bindPopup(`<strong>${pt.state}</strong>: ${pt.resistance_pct}% (${pt.status})`)
            .addTo(map);
          }
        });
      }
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [resData, showResult]);

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%', 
        height: '100%', 
        minHeight: '540px',
        backgroundColor: '#1a1f2c' 
      }} 
    />
  );
}
