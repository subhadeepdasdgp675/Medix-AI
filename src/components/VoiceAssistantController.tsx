import React, { useState, useRef, useEffect } from 'react';
import {
  Volume2,
  VolumeX,
  Play,
  Pause,
  Square,
  Sparkles,
  Globe,
  Radio,
  FileText,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import { GlassCard } from './GlassCard';
import { API_BASE } from '../lib/api';
import { clinicalVoiceService } from '../lib/clinicalVoiceService';

export interface VoiceDrug {
  drug_name: string;
  dosage_details: string;
  duration: string;
  local_resistance_pct?: string;
}

export interface VoiceVitals {
  temperature_f?: string;
  pulse_bpm?: string;
  spo2_pct?: string;
  respiratory_rate?: string;
  blood_pressure?: string;
}

export interface VoiceAssistantProps {
  payload: {
    patient_name: string;
    age_gender: string;
    case_reference: string;
    registered_date: string;
    physical_measurements?: string;
    hospital_location?: string;
    primary_condition: string;
    diagnosis_confidence: string;
    prescribed_antibiotics: VoiceDrug[];
    vitals: VoiceVitals;
    symptoms: string[];
    comorbidities: string[];
    allergies: string[];
    previous_antibiotic_exposure?: string;
    physician_notes?: string;
  };
}

type LanguageCode = 'en' | 'hi' | 'bn';

interface LanguageOption {
  code: LanguageCode;
  label: string;
  native: string;
  flag: string;
}

const LANGUAGES: LanguageOption[] = [
  { code: 'en', label: 'English', native: 'English', flag: '🇬🇧' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी', flag: '🇮🇳' },
  { code: 'bn', label: 'Bengali', native: 'বাংলা', flag: '🇮🇳' }
];

export function VoiceAssistantController({ payload }: VoiceAssistantProps) {
  const [selectedLang, setSelectedLang] = useState<LanguageCode>('en');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('Ready to narrate clinical report');
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [showScript, setShowScript] = useState(false);
  const [activeScript, setActiveScript] = useState<string>('');
  const [provider, setProvider] = useState<'elevenlabs' | 'browser' | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const synthUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const pausedCharIndexRef = useRef<number>(0);
  const fullTextRef = useRef<string>('');

  // Clean up audio & speech on unmount
  useEffect(() => {
    return () => {
      stopPlayback();
    };
  }, []);

  const stopPlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setIsPlaying(false);
    setIsPaused(false);
    setIsLoading(false);
    setCurrentTime(0);
    pausedCharIndexRef.current = 0;
    setStatusMessage('Playback stopped');
  };

  const handleLanguageChange = (lang: LanguageCode) => {
    if (lang !== selectedLang) {
      stopPlayback();
      setSelectedLang(lang);
      setStatusMessage(`Language set to ${LANGUAGES.find(l => l.code === lang)?.label}. Click Play to narrate.`);
    }
  };

  // Dedicated Pause handler: captures exact point in audio or speech synthesis
  const handlePause = () => {
    if (!isPlaying) return;

    if (provider === 'elevenlabs' && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      setIsPaused(true);
      setStatusMessage(`Narration paused at ${formatTime(audioRef.current.currentTime)}`);
    } else if (provider === 'browser' && window.speechSynthesis) {
      // In Chromium / modern browsers, speech.pause() pauses at the exact word boundary
      window.speechSynthesis.pause();
      setIsPlaying(false);
      setIsPaused(true);
      setStatusMessage('Narration paused');
    } else {
      setIsPlaying(false);
      setIsPaused(true);
    }
  };

  // Dedicated Resume handler: continues immediately from paused point
  const handleResume = async () => {
    if (!isPaused) return;

    if (provider === 'elevenlabs' && audioRef.current) {
      try {
        await audioRef.current.play();
        setIsPlaying(true);
        setIsPaused(false);
        setStatusMessage(`Resumed narration (${selectedLang.toUpperCase()})`);
      } catch (err: any) {
        console.error('Failed to resume audio:', err);
        // If resume fails, generate anew
        handleStartNewPlayback();
      }
    } else if (provider === 'browser' && window.speechSynthesis) {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
        setIsPlaying(true);
        setIsPaused(false);
        setStatusMessage(`Resumed speech narration`);
      } else {
        // Fallback: resume from captured char index
        resumeBrowserSpeechFromIndex();
      }
    } else {
      handleStartNewPlayback();
    }
  };

  const resumeBrowserSpeechFromIndex = () => {
    if (!window.speechSynthesis || !fullTextRef.current) return;
    const remainingText = fullTextRef.current.slice(pausedCharIndexRef.current);
    if (!remainingText.trim()) {
      setIsPlaying(false);
      setIsPaused(false);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(remainingText);
    if (selectedLang === 'hi') {
      utterance.lang = 'hi-IN';
    } else if (selectedLang === 'bn') {
      utterance.lang = 'bn-IN';
    } else {
      utterance.lang = 'en-US';
    }
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    utterance.onboundary = (e) => {
      if (e.charIndex !== undefined) {
        pausedCharIndexRef.current += e.charIndex;
      }
    };
    utterance.onend = () => {
      setIsPlaying(false);
      setIsPaused(false);
      setStatusMessage('Narration completed');
    };
    utterance.onerror = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    synthUtteranceRef.current = utterance;
    setIsPlaying(true);
    setIsPaused(false);
    window.speechSynthesis.speak(utterance);
  };

  // Main start handler: synthesizes and starts playback
  const handleStartNewPlayback = async () => {
    // Immediately halt any emergency or clinical rationale audio
    clinicalVoiceService.stopAll();

    setIsLoading(true);
    setIsPaused(false);

    setStatusMessage(
      selectedLang === 'en'
        ? 'Synthesizing clinical script with crystal-clear medical diction...'
        : `Synthesizing in ${LANGUAGES.find(l => l.code === selectedLang)?.native} with high clarity...`
    );

    try {
      const fullPayload = {
        ...payload,
        language: selectedLang
      };

      const response = await fetch(`${API_BASE}/api/reports/voice-narration`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fullPayload)
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server error: ${response.status}`);
      }

      const contentType = response.headers.get('Content-Type') || '';

      // Check if server returned streaming MP3 audio
      if (contentType.includes('audio/mpeg') || contentType.includes('audio/mp3') || contentType.includes('audio/')) {
        setProvider('elevenlabs');
        const audioBlob = await response.blob();
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
        }
        const audioUrl = URL.createObjectURL(audioBlob);
        audioUrlRef.current = audioUrl;

        if (!audioRef.current) {
          audioRef.current = new Audio();
        }

        const audio = audioRef.current;
        audio.src = audioUrl;

        audio.onloadedmetadata = () => {
          setDuration(audio.duration || 0);
        };

        audio.ontimeupdate = () => {
          setCurrentTime(audio.currentTime || 0);
        };

        audio.onended = () => {
          setIsPlaying(false);
          setIsPaused(false);
          setCurrentTime(0);
          setStatusMessage('Narration completed');
        };

        audio.onerror = () => {
          setIsPlaying(false);
          setIsPaused(false);
          setIsLoading(false);
          setStatusMessage('Error during audio stream playback');
        };

        await audio.play();
        setIsPlaying(true);
        setIsPaused(false);
        setIsLoading(false);
        setStatusMessage(`Speaking via ElevenLabs v2 Neural (${selectedLang.toUpperCase()})`);
      } else {
        // Server returned JSON script for browser synthesis
        const data = await response.json();
        setProvider('browser');
        setActiveScript(data.script || '');
        fullTextRef.current = data.script || '';
        pausedCharIndexRef.current = 0;

        if (window.speechSynthesis) {
          setStatusMessage(`Speaking via Multilingual Engine (${LANGUAGES.find(l => l.code === selectedLang)?.native})`);
          
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(data.script);
          
          if (selectedLang === 'hi') {
            utterance.lang = 'hi-IN';
          } else if (selectedLang === 'bn') {
            utterance.lang = 'bn-IN';
          } else {
            utterance.lang = 'en-US';
          }

          utterance.rate = 0.95;
          utterance.pitch = 1.0;

          utterance.onboundary = (e) => {
            if (e.charIndex !== undefined) {
              pausedCharIndexRef.current = e.charIndex;
            }
          };

          utterance.onstart = () => {
            setIsPlaying(true);
            setIsPaused(false);
            setIsLoading(false);
          };

          utterance.onend = () => {
            setIsPlaying(false);
            setIsPaused(false);
            setCurrentTime(0);
            setStatusMessage('Narration completed');
          };

          utterance.onerror = (e) => {
            console.error('Speech synthesis error:', e);
            setIsPlaying(false);
            setIsPaused(false);
            setIsLoading(false);
            setStatusMessage('Narration ended');
          };

          synthUtteranceRef.current = utterance;
          window.speechSynthesis.speak(utterance);
        } else {
          setIsLoading(false);
          setStatusMessage(data.message || 'Narration ready');
        }
      }
    } catch (err: any) {
      console.error('Voice Assistant Error:', err);
      setIsLoading(false);
      setIsPlaying(false);
      setIsPaused(false);
      setStatusMessage(`Error: ${err.message || 'Could not connect to Voice Assistant'}`);
    }
  };

  const handlePlayButtonClick = () => {
    if (isPaused) {
      handleResume();
    } else {
      handleStartNewPlayback();
    }
  };

  const handleMuteToggle = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
    }
    setIsMuted(!isMuted);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current && provider === 'elevenlabs') {
      audioRef.current.currentTime = newTime;
    }
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainder = Math.floor(secs % 60);
    return `${mins}:${remainder < 10 ? '0' : ''}${remainder}`;
  };

  return (
    <GlassCard className="voice-assistant-panel no-print mb-4 border border-ai-accent/30 shadow-lg">
      <div className="flex items-center justify-between flex-wrap gap-3">
        {/* Left: Assistant Title & Status */}
        <div className="flex items-center gap-3">
          <div className={`voice-avatar-badge ${isPlaying ? 'animate-pulse ring-2 ring-ai-accent' : isPaused ? 'ring-2 ring-warning' : ''}`}>
            <Radio size={20} className={isPlaying ? 'text-ai-accent' : isPaused ? 'text-warning' : 'text-secondary'} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="m-0 font-bold text-base flex items-center gap-1.5 text-white">
                <Sparkles size={16} className="text-ai-accent" />
                Multilingual Clinical Voice Assistant
              </h4>
              <span className={`badge ${provider === 'elevenlabs' ? 'badge-success' : 'badge-outline'} text-xs`}>
                {provider === 'elevenlabs' ? 'ElevenLabs Studio' : 'Neural Voice'}
              </span>
              {isPaused && (
                <span className="badge badge-warning text-xs">Paused</span>
              )}
            </div>
            <p className="text-secondary text-xs m-0 mt-0.5">{statusMessage}</p>
          </div>
        </div>

        {/* Right: Language Selection Pills */}
        <div className="flex items-center gap-1.5 bg-black/30 p-1 rounded-lg border border-white/10">
          <Globe size={14} className="text-secondary ml-1 mr-0.5" />
          {LANGUAGES.map((lang) => {
            const isSelected = selectedLang === lang.code;
            return (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                disabled={isLoading}
                className={`btn-lang-pill ${isSelected ? 'active-lang' : ''}`}
                title={`Listen report in ${lang.label}`}
              >
                <span>{lang.flag}</span>
                <span className="font-semibold text-xs">{lang.native}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Controller Controls: Play/Pause/Resume/Stop, Waveform & Time */}
      <div className="flex items-center justify-between flex-wrap gap-4 mt-3 pt-3 border-t border-white/10">
        <div className="flex items-center gap-2">
          {/* Play / Restart / Start Button */}
          {!isPlaying && !isPaused && (
            <button
              onClick={handlePlayButtonClick}
              disabled={isLoading}
              className="btn btn-ai flex items-center gap-2 px-4 py-2 font-semibold shadow-md"
              title="Start voice narration"
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Synthesizing...</span>
                </>
              ) : (
                <>
                  <Play size={16} />
                  <span>Listen Report</span>
                </>
              )}
            </button>
          )}

          {/* Pause Button - Visible when playing */}
          {isPlaying && (
            <button
              onClick={handlePause}
              disabled={isLoading}
              className="btn btn-warning flex items-center gap-2 px-4 py-2 font-semibold shadow-md text-dark"
              title="Pause narration anytime"
            >
              <Pause size={16} />
              <span>Pause</span>
            </button>
          )}

          {/* Resume Button - Visible when paused */}
          {isPaused && (
            <button
              onClick={handleResume}
              disabled={isLoading}
              className="btn btn-success flex items-center gap-2 px-4 py-2 font-semibold shadow-md text-white animate-pulse"
              title="Resume from paused point"
            >
              <Play size={16} />
              <span>Resume</span>
            </button>
          )}

          {/* Stop Button */}
          <button
            onClick={stopPlayback}
            disabled={!isPlaying && !isPaused && !isLoading}
            className="btn btn-outline p-2"
            title="Stop narration completely"
          >
            <Square size={16} />
          </button>

          {/* Mute Button (for audio element) */}
          {provider === 'elevenlabs' && (
            <button
              onClick={handleMuteToggle}
              className="btn btn-outline p-2"
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? <VolumeX size={16} className="text-danger" /> : <Volume2 size={16} />}
            </button>
          )}
        </div>

        {/* Dynamic Waveform Visualizer & Scrubber */}
        <div className="flex items-center gap-2 flex-1 max-w-sm mx-2">
          {duration > 0 && provider === 'elevenlabs' ? (
            <input
              type="range"
              min={0}
              max={duration || 100}
              step={0.1}
              value={currentTime}
              onChange={handleSeek}
              className="w-full accent-emerald-400 cursor-pointer h-1.5 bg-white/20 rounded-lg"
              title="Seek narration timestamp"
            />
          ) : (
            <div className="flex items-center gap-1.5 w-full justify-center">
              {[35, 75, 25, 95, 60, 85, 45, 90, 30, 70, 50, 100, 65, 40, 80].map((heightPct, idx) => (
                <div
                  key={idx}
                  className={`waveform-bar ${isPlaying ? 'active' : isPaused ? 'opacity-40' : ''}`}
                  style={{
                    height: isPlaying ? `${Math.max(14, heightPct * 0.28)}px` : isPaused ? '8px' : '4px',
                    animationDelay: `${idx * 0.08}s`
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Time and Script Toggle */}
        <div className="flex items-center gap-3">
          {duration > 0 && provider === 'elevenlabs' && (
            <span className="text-xs text-secondary font-mono">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          )}
          <button
            onClick={() => setShowScript(!showScript)}
            className="btn btn-outline text-xs py-1 px-2.5 flex items-center gap-1 text-secondary"
            title="Inspect spoken clinical script"
          >
            <FileText size={13} />
            <span>{showScript ? 'Hide Script' : 'Clinical Script'}</span>
          </button>
        </div>
      </div>

      {/* Script Preview Drawer */}
      {showScript && (
        <div className="mt-3 p-3 bg-black/40 border border-white/10 rounded-lg text-xs leading-relaxed text-secondary animate-fade-in">
          <div className="flex items-center justify-between mb-1.5">
            <strong className="text-white flex items-center gap-1">
              <CheckCircle2 size={13} className="text-ai-accent" />
              Spoken Clinical Script ({LANGUAGES.find(l => l.code === selectedLang)?.native}):
            </strong>
            <span className="text-[11px] text-secondary">
              {selectedLang === 'en' ? 'Natural English phonetics' : selectedLang === 'hi' ? 'शुद्ध हिन्दी चिकित्सीय शब्दावली' : 'বিশুদ্ধ বাংলা চিকিৎসাবিজ্ঞান পরিভাষা'}
            </span>
          </div>
          <p className="m-0 select-text whitespace-pre-wrap leading-relaxed text-slate-300">
            {activeScript ||
              `Clinical Decision Summary for patient ${payload.patient_name}, ${payload.age_gender}. Case Reference: ${payload.case_reference}. Hospital location: ${payload.hospital_location || 'Kolkata'}. Primary assessment: ${payload.primary_condition} (${payload.diagnosis_confidence}).`}
          </p>
        </div>
      )}
    </GlassCard>
  );
}
