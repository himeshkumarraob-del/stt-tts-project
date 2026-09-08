import fetch from 'node-fetch';
import { TtsProvider } from './TtsProvider.js';

/**
 * ElevenLabs alternate provider: extremely natural prosody in English,
 * useful when the output is mostly English with occasional Indian names,
 * but it has far fewer native Indian-regional-language voices than Azure.
 * Kept behind the same interface so it's a one-line swap (TTS_PROVIDER=elevenlabs).
 */
export class ElevenLabsProvider extends TtsProvider {
  constructor({ apiKey }) {
    super();
    if (!apiKey) throw new Error('ELEVENLABS_API_KEY is required for ElevenLabsProvider');
    this.apiKey = apiKey;
  }

  async listVoices() {
    const res = await fetch('https://api.elevenlabs.io/v1/voices', {
      headers: { 'xi-api-key': this.apiKey },
    });
    if (!res.ok) throw new Error(`ElevenLabs voices error ${res.status}`);
    const json = await res.json();
    return (json.voices || []).map((v) => ({
      id: v.voice_id,
      label: v.name,
      language: 'en', // ElevenLabs voices are largely language-agnostic multilingual models
      gender: v.labels?.gender || 'neutral',
    }));
  }

  async synthesize(text, opts = {}) {
    const voiceId = opts.voiceId || '21m00Tcm4TlvDq8ikWAM'; // default demo voice
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
      method: 'POST',
      headers: {
        'xi-api-key': this.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_multilingual_v2',
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
          // ElevenLabs doesn't take rate directly; speed is approximated
          // client-side via playbackRate, or by pre/post punctuation pacing.
          style: 0.3,
        },
      }),
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`ElevenLabs TTS error ${res.status}: ${errText}`);
    }
    const audio = Buffer.from(await res.arrayBuffer());
    return { audio, mimeType: 'audio/mpeg' };
  }
}
