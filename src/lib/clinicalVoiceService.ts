/**
 * Medix AI - Unified Clinical Audio & ElevenLabs Voice Intelligence Engine
 * Handles:
 * 1. Web Audio API hospital alert chimes (880Hz -> 660Hz two-tone alarm)
 * 2. ElevenLabs neural voice player with streaming audio/mpeg
 * 3. Graceful browser speech synthesis fallback
 * 4. Global single-source audio control (interrupting previous audio before starting new playback)
 */
import { API_BASE } from './api';

type AudioStateCallback = (isPlaying: boolean, status: string) => void;

class ClinicalVoiceService {
  private activeAudio: HTMLAudioElement | null = null;
  private activeObjectUrl: string | null = null;
  private audioContext: AudioContext | null = null;
  private currentPlayId: number = 0;
  private stateSubscribers: Set<AudioStateCallback> = new Set();

  /**
   * Immediately halts and cleans up ANY ongoing voice narration or synthesizers.
   */
  public stopAll(): void {
    this.currentPlayId++;

    if (this.activeAudio) {
      try {
        this.activeAudio.pause();
        this.activeAudio.currentTime = 0;
      } catch (e) {
        console.warn('Error pausing active audio:', e);
      }
      this.activeAudio = null;
    }

    if (this.activeObjectUrl) {
      try {
        URL.revokeObjectURL(this.activeObjectUrl);
      } catch (e) {
        console.warn('Error revoking object URL:', e);
      }
      this.activeObjectUrl = null;
    }

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    this.notifySubscribers(false, 'Idle');
  }

  /**
   * Synthesizes an immediate Web Audio hospital alert chime (880Hz -> 660Hz sine tone).
   * Two-step harmonic hospital chime sequence.
   */
  public async playHospitalAlertChime(): Promise<void> {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;

      if (!this.audioContext || this.audioContext.state === 'closed') {
        this.audioContext = new AudioCtx();
      }

      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      const ctx = this.audioContext;
      const now = ctx.currentTime;

      // Note 1: 880 Hz (A5 - urgent clinical high tone)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(880, now);

      gain1.gain.setValueAtTime(0, now);
      gain1.gain.linearRampToValueAtTime(0.35, now + 0.04);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.28);

      osc1.connect(gain1);
      gain1.connect(ctx.destination);

      osc1.start(now);
      osc1.stop(now + 0.3);

      // Note 2: 660 Hz (E5 - descending contraindication resolution tone)
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(660, now + 0.25);

      gain2.gain.setValueAtTime(0, now + 0.25);
      gain2.gain.linearRampToValueAtTime(0.4, now + 0.29);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.65);

      osc2.connect(gain2);
      gain2.connect(ctx.destination);

      osc2.start(now + 0.25);
      osc2.stop(now + 0.7);

      // Wait for chime completion
      await new Promise(res => setTimeout(res, 680));
    } catch (err) {
      console.warn('Hospital alert chime synthesis note:', err);
    }
  }

  /**
   * Routes speech text through ElevenLabs neural voice player.
   * Auto-cancels any other playing audio, handles streaming, and falls back to Web Speech API.
   */
  public async speakText(
    text: string, 
    options?: { 
      onStart?: () => void;
      onEnd?: () => void; 
      onError?: (err: any) => void;
    }
  ): Promise<void> {
    // 1. Immediately cancel any currently active playback
    this.stopAll();
    const playSessionId = ++this.currentPlayId;

    this.notifySubscribers(true, 'Synthesizing speech...');

    try {
      const response = await fetch(`${API_BASE}/api/voice/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      if (playSessionId !== this.currentPlayId) {
        return; // Superseded by a newer audio play request
      }

      const contentType = response.headers.get('Content-Type') || '';

      // Check if server returned streaming MP3 audio from ElevenLabs
      if (response.ok && (contentType.includes('audio/mpeg') || contentType.includes('audio/mp3') || contentType.includes('audio/'))) {
        const audioBlob = await response.blob();
        if (playSessionId !== this.currentPlayId) return;

        const audioUrl = URL.createObjectURL(audioBlob);
        this.activeObjectUrl = audioUrl;

        const audio = new Audio(audioUrl);
        this.activeAudio = audio;

        audio.onended = () => {
          if (this.currentPlayId === playSessionId) {
            this.stopAll();
            options?.onEnd?.();
          }
        };

        audio.onerror = (e) => {
          if (this.currentPlayId === playSessionId) {
            console.warn('Audio playback error, falling back to speech synthesis', e);
            this.fallbackSpeechSynthesis(text, playSessionId, options);
          }
        };

        options?.onStart?.();
        this.notifySubscribers(true, 'ElevenLabs Voice Active');
        await audio.play();
      } else {
        // Fallback to browser SpeechSynthesis
        const data = await response.json().catch(() => ({ script: text }));
        const scriptToSpeak = data.script || text;
        this.fallbackSpeechSynthesis(scriptToSpeak, playSessionId, options);
      }
    } catch (err) {
      if (playSessionId !== this.currentPlayId) return;
      console.warn('ElevenLabs API request failed, falling back to browser voice:', err);
      this.fallbackSpeechSynthesis(text, playSessionId, options);
    }
  }

  /**
   * Web Speech API fallback player.
   */
  private fallbackSpeechSynthesis(
    text: string, 
    playSessionId: number, 
    options?: { onStart?: () => void; onEnd?: () => void; onError?: (err: any) => void; }
  ) {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      this.notifySubscribers(false, 'Speech synthesis not supported');
      options?.onError?.(new Error('Speech synthesis not available'));
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Prefer high-clarity natural English voices if available
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha')));
    if (naturalVoice) {
      utterance.voice = naturalVoice;
    }

    utterance.onstart = () => {
      if (this.currentPlayId === playSessionId) {
        options?.onStart?.();
        this.notifySubscribers(true, 'Clinical Voice Active');
      }
    };

    utterance.onend = () => {
      if (this.currentPlayId === playSessionId) {
        this.notifySubscribers(false, 'Idle');
        options?.onEnd?.();
      }
    };

    utterance.onerror = (e) => {
      if (this.currentPlayId === playSessionId) {
        this.notifySubscribers(false, 'Playback error');
        options?.onError?.(e);
      }
    };

    window.speechSynthesis.speak(utterance);
  }

  public subscribe(cb: AudioStateCallback): () => void {
    this.stateSubscribers.add(cb);
    return () => this.stateSubscribers.delete(cb);
  }

  private notifySubscribers(isPlaying: boolean, status: string) {
    this.stateSubscribers.forEach(cb => cb(isPlaying, status));
  }
}

export const clinicalVoiceService = new ClinicalVoiceService();
