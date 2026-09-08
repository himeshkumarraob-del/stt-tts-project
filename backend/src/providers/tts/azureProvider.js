import fetch from 'node-fetch';
import { TtsProvider } from './TtsProvider.js';
import { buildSsml } from '../../utils/ssmlBuilder.js';

/**
 * Azure Cognitive Services Speech has, by a wide margin, the best public
 * coverage of Indian-English and Indian-regional-language neural voices,
 * which is why it's the default TTS provider for this app:
 *   en-IN: NeerjaNeural (f), PrabhatNeural (m)
 *   hi-IN: SwaraNeural (f), MadhurNeural (m)
 *   ta-IN: PallaviNeural (f), ValluvarNeural (m)
 *   te-IN: ShrutiNeural (f), MohanNeural (m)
 *   kn-IN: SapnaNeural (f), GaganNeural (m)
 *   ml-IN: SobhanaNeural (f), MidhunNeural (m)
 *   bn-IN: TanishaaNeural (f), BashkarNeural (m)
 *   mr-IN, gu-IN, pa-IN, ur-IN, or-IN also available.
 * (Voice list below is also fetchable live from Azure; see listVoices().)
 */
export class AzureTtsProvider extends TtsProvider {
  constructor({ apiKey, region }) {
    super();
    if (!apiKey || !region) throw new Error('AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required');
    this.apiKey = apiKey;
    this.region = region;
    this._tokenCache = { token: null, expiresAt: 0 };
  }

  async _getToken() {
    if (this._tokenCache.token && Date.now() < this._tokenCache.expiresAt) {
      return this._tokenCache.token;
    }
    const res = await fetch(`https://${this.region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken`, {
      method: 'POST',
      headers: { 'Ocp-Apim-Subscription-Key': this.apiKey },
    });
    if (!res.ok) throw new Error(`Azure token error ${res.status}`);
    const token = await res.text();
    // Tokens are valid 10 minutes; refresh a little early.
    this._tokenCache = { token, expiresAt: Date.now() + 8 * 60 * 1000 };
    return token;
  }

  async listVoices() {
    // Curated, hand-picked subset optimized for this app's use case
    // (full catalogue has 400+ voices across languages). Swap for a live
    // call to /cognitiveservices/voices/list if you want the full set.
    return [
      { id: 'en-IN-NeerjaNeural', label: 'Neerja — Indian English (female)', language: 'en-IN', gender: 'female' },
      { id: 'en-IN-PrabhatNeural', label: 'Prabhat — Indian English (male)', language: 'en-IN', gender: 'male' },
      { id: 'hi-IN-SwaraNeural', label: 'Swara — Hindi (female)', language: 'hi-IN', gender: 'female' },
      { id: 'hi-IN-MadhurNeural', label: 'Madhur — Hindi (male)', language: 'hi-IN', gender: 'male' },
      { id: 'ta-IN-PallaviNeural', label: 'Pallavi — Tamil (female)', language: 'ta-IN', gender: 'female' },
      { id: 'ta-IN-ValluvarNeural', label: 'Valluvar — Tamil (male)', language: 'ta-IN', gender: 'male' },
      { id: 'te-IN-ShrutiNeural', label: 'Shruti — Telugu (female)', language: 'te-IN', gender: 'female' },
      { id: 'te-IN-MohanNeural', label: 'Mohan — Telugu (male)', language: 'te-IN', gender: 'male' },
      { id: 'kn-IN-SapnaNeural', label: 'Sapna — Kannada (female)', language: 'kn-IN', gender: 'female' },
      { id: 'kn-IN-GaganNeural', label: 'Gagan — Kannada (male)', language: 'kn-IN', gender: 'male' },
      { id: 'ml-IN-SobhanaNeural', label: 'Sobhana — Malayalam (female)', language: 'ml-IN', gender: 'female' },
      { id: 'ml-IN-MidhunNeural', label: 'Midhun — Malayalam (male)', language: 'ml-IN', gender: 'male' },
      { id: 'bn-IN-TanishaaNeural', label: 'Tanishaa — Bengali (female)', language: 'bn-IN', gender: 'female' },
      { id: 'bn-IN-BashkarNeural', label: 'Bashkar — Bengali (male)', language: 'bn-IN', gender: 'male' },
    ];
  }

  async synthesize(text, opts = {}) {
    const token = await this._getToken();
    const voiceId = opts.voiceId || 'en-IN-NeerjaNeural';
    const lang = opts.language || voiceId.split('-').slice(0, 2).join('-');
    const ssml = buildSsml(text, {
      rate: opts.rate ?? 1.0,
      pitchSemitones: opts.pitch ?? 0,
      voiceId,
      lang,
    });

    const format =
      opts.format === 'wav' ? 'riff-24khz-16bit-mono-pcm' : 'audio-24khz-96kbitrate-mono-mp3';

    const res = await fetch(
      `https://${this.region}.tts.speech.microsoft.com/cognitiveservices/v1`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/ssml+xml',
          'X-Microsoft-OutputFormat': format,
          'User-Agent': 'indic-voice-app',
        },
        body: ssml,
      }
    );

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Azure TTS error ${res.status}: ${errText}`);
    }
    const audio = Buffer.from(await res.arrayBuffer());
    return { audio, mimeType: opts.format === 'wav' ? 'audio/wav' : 'audio/mpeg' };
  }
}
