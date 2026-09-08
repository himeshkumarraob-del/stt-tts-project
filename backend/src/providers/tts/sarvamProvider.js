import fetch from 'node-fetch';
import { TtsProvider } from './TtsProvider.js';

const SARVAM_TTS_URL = 'https://api.sarvam.ai/text-to-speech';

/**
 * Sarvam AI's Bulbul v3 model is trained natively on Indian speech data
 * (not an English model retrofitted with an accent), and its free tier
 * issues API keys instantly with no card required — which is why this is
 * the easiest provider to get running for this project.
 *
 * Unlike Azure, Sarvam separates "speaker" (the voice actor) from
 * "language_code" (what language it speaks) — the same speaker can
 * usually speak any supported language. To keep this compatible with the
 * app's single voice-picker dropdown, each entry in listVoices() encodes
 * both as `speakerId:languageCode` (e.g. "priya:ta-IN"), which
 * synthesize() splits back apart.
 *
 * API reference: https://docs.sarvam.ai/api-reference/text-to-speech/convert
 */
export class SarvamProvider extends TtsProvider {
  constructor({ apiKey, model }) {
    super();
    if (!apiKey) throw new Error('SARVAM_API_KEY is required for SarvamProvider');
    this.apiKey = apiKey;
    this.model = model || 'bulbul:v3';
  }

  async listVoices() {
    // A curated cross-section of bulbul:v3's 30+ speakers across the
    // languages this app targets. Extend freely — any speaker name from
    // Sarvam's docs works with any of their supported language codes.
    const speakers = [
      { id: 'shubh', label: 'Shubh', gender: 'male' },
      { id: 'priya', label: 'Priya', gender: 'female' },
    ];
    const languages = [
      { code: 'en-IN', label: 'Indian English' },
      { code: 'hi-IN', label: 'Hindi' },
      { code: 'ta-IN', label: 'Tamil' },
      { code: 'te-IN', label: 'Telugu' },
      { code: 'kn-IN', label: 'Kannada' },
      { code: 'ml-IN', label: 'Malayalam' },
      { code: 'bn-IN', label: 'Bengali' },
    ];

    const voices = [];
    for (const lang of languages) {
      for (const sp of speakers) {
        voices.push({
          id: `${sp.id}:${lang.code}`,
          label: `${sp.label} — ${lang.label} (${sp.gender})`,
          language: lang.code,
          gender: sp.gender,
        });
      }
    }
    return voices;
  }

  async synthesize(text, opts = {}) {
    const voiceId = opts.voiceId || 'shubh:en-IN';
    const [speaker, languageCode] = voiceId.includes(':') ? voiceId.split(':') : [voiceId, 'en-IN'];

    // bulbul:v3 pace range is 0.5-2.0, which matches this app's global
    // rate clamp in routes/tts.js, so no extra clamping needed here.
    const body = {
      text,
      language_code: languageCode || 'en-IN',
      speaker: speaker || 'shubh',
      model: this.model,
      pace: opts.rate ?? 1.0,
      speech_sample_rate: 24000,
    };
    // NOTE: bulbul:v3 does not support the `pitch` parameter at all
    // (Sarvam docs: "NOT supported for bulbul:v3") — opts.pitch is
    // silently ignored for this provider rather than sent and rejected.

    const res = await fetch(SARVAM_TTS_URL, {
      method: 'POST',
      headers: {
        'api-subscription-key': this.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Sarvam TTS error ${res.status}: ${errText}`);
    }

    const json = await res.json();
    const combinedBase64 = (json.audios || []).join('');
    if (!combinedBase64) throw new Error('Sarvam TTS returned no audio');

    return { audio: Buffer.from(combinedBase64, 'base64'), mimeType: 'audio/wav' };
  }
}
