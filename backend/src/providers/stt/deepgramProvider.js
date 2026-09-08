import WebSocket from 'ws';
import fetch from 'node-fetch';
import { SttProvider } from './SttProvider.js';
import { markLowConfidenceWords } from '../../utils/confidence.js';

const DG_BASE = 'https://api.deepgram.com/v1/listen';
const DG_WS = 'wss://api.deepgram.com/v1/listen';

/**
 * Deepgram is the primary provider here because it:
 *  - has a dedicated en-IN acoustic model trained on Indian English,
 *  - supports true low-latency streaming (needed for the live waveform +
 *    real-time transcript UI),
 *  - returns per-word confidence, so we can flag uncertain audio instead
 *    of guessing,
 *  - has a "smart_format" / punctuation pass built in,
 *  - supports multi-language detection which helps flag code-switched
 *    segments (e.g. Tamil/Hindi words inside an English sentence) without
 *    translating them.
 */
export class DeepgramProvider extends SttProvider {
  constructor({ apiKey, model, language }) {
    super();
    if (!apiKey) throw new Error('DEEPGRAM_API_KEY is required for DeepgramProvider');
    this.apiKey = apiKey;
    this.model = model || 'nova-2';
    this.language = language || 'en-IN';
  }

  _queryParams(extra = {}) {
    const params = new URLSearchParams({
      model: this.model,
      language: this.language,
      punctuate: 'true',
      smart_format: 'true',
      diarize: 'false',
      // Keep filler words / disfluencies in the transcript by default —
      // "um", "actually", repeated words are the speaker's actual words.
      filler_words: 'true',
      numerals: 'true',
      ...extra,
    });
    return params;
  }

  async transcribeBatch(audioBuffer, opts = {}) {
    // IMPORTANT: Deepgram's `detect_language=true` silently overrides
    // `language` if both are sent. Since the accent-aware layer always
    // supplies a languageHint (en-IN by default), we must NOT also set
    // detect_language here, or every request would quietly discard the
    // Indian-English model adaptation. Auto-detect only kicks in when the
    // caller explicitly did not provide a hint.
    const params = this._queryParams(
      opts.languageHint ? { language: opts.languageHint } : { detect_language: 'true' }
    );

    // Inject learned keywords — boosts words the user has corrected at the
    // acoustic-decoder level (Deepgram processes these before text is emitted).
    // Boost factor 3 = strong preference without completely ignoring acoustics.
    for (const kw of (opts.keywords || []).slice(0, 100)) {
      params.append('keywords', `${kw}:3`);
    }

    const res = await fetch(`${DG_BASE}?${params.toString()}`, {
      method: 'POST',
      headers: {
        Authorization: `Token ${this.apiKey}`,
        'Content-Type': opts.mimeType || 'audio/webm',
      },
      body: audioBuffer,
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Deepgram error ${res.status}: ${errText}`);
    }
    const json = await res.json();
    return this._normalize(json);
  }

  _normalize(json) {
    const channel = json?.results?.channels?.[0];
    const alt = channel?.alternatives?.[0];
    const words = (alt?.words || []).map((w) => ({
      text: w.punctuated_word || w.word,
      start: w.start,
      end: w.end,
      confidence: w.confidence,
      uncertain: false, // set below
    }));
    markLowConfidenceWords(words);

    return {
      text: alt?.transcript || '',
      words,
      detectedLanguage: channel?.detected_language || this.language,
      provider: 'deepgram',
      raw: json,
    };
  }

  /**
   * Live streaming session over Deepgram's websocket API. The frontend
   * sends raw audio chunks (webm/opus or linear16) over our own
   * WebSocket, and wsServer.js pipes them straight through here.
   */
  async openStream({ mimeType = 'audio/webm', onOpen } = {}) {
    // Same fix as transcribeBatch: don't send detect_language alongside
    // the constructor's `language` (en-IN) — it would silently override
    // the Indian-English model adaptation on every streaming session too.
    const params = this._queryParams({
      interim_results: 'true',
      endpointing: '300',
      encoding: mimeType.includes('webm') ? undefined : 'linear16',
      sample_rate: mimeType.includes('webm') ? undefined : '16000',
    });
    // Drop undefined values
    for (const [k, v] of [...params]) if (v === 'undefined') params.delete(k);

    const dgSocket = new WebSocket(`${DG_WS}?${params.toString()}`, {
      headers: { Authorization: `Token ${this.apiKey}` },
    });

    const listeners = [];
    dgSocket.on('open', () => onOpen && onOpen());
    dgSocket.on('message', (data) => {
      try {
        const json = JSON.parse(data.toString());
        if (json.type !== 'Results') return;
        const alt = json.channel?.alternatives?.[0];
        if (!alt) return;
        const words = (alt.words || []).map((w) => ({
          text: w.punctuated_word || w.word,
          start: w.start,
          end: w.end,
          confidence: w.confidence,
          uncertain: false,
        }));
        markLowConfidenceWords(words);
        const result = {
          isFinal: !!json.is_final,
          text: alt.transcript || '',
          words,
          detectedLanguage: json.channel?.detected_language,
        };
        listeners.forEach((cb) => cb(result));
      } catch {
        // Ignore malformed frames rather than crashing the session
      }
    });

    return {
      sendAudio: (chunk) => {
        if (dgSocket.readyState === WebSocket.OPEN) dgSocket.send(chunk);
      },
      onResult: (cb) => listeners.push(cb),
      onClose: (cb) => dgSocket.on('close', cb),
      onError: (cb) => dgSocket.on('error', cb),
      close: () => {
        try {
          dgSocket.send(JSON.stringify({ type: 'CloseStream' }));
        } catch {
          /* socket may already be closed */
        }
        dgSocket.close();
      },
    };
  }
}
