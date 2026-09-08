import fetch from 'node-fetch';
import FormData from 'form-data';
import { SttProvider } from './SttProvider.js';
import { markLowConfidenceWords } from '../../utils/confidence.js';

const OPENAI_TRANSCRIBE_URL = 'https://api.openai.com/v1/audio/transcriptions';

/**
 * Whisper (via OpenAI's API) is strong on code-switched, noisy and
 * heavily-accented audio because it was trained on very diverse multilingual
 * data. It has no public real-time streaming endpoint, so we use it as:
 *   1. the batch "finalize" transcription after recording stops, and
 *   2. an optional fallback for openStream() via short buffered windows
 *      when no streaming-capable provider (Deepgram) is configured.
 *
 * We deliberately do NOT pass a `prompt` that biases Whisper toward
 * "corrected" standard English — that would violate the "preserve actual
 * words" requirement. The only prompt bias we add is a short list of
 * proper nouns (Indian names/places) so Whisper spells them consistently,
 * never to change what was said.
 */
export class WhisperProvider extends SttProvider {
  constructor({ apiKey, model }) {
    super();
    if (!apiKey) throw new Error('OPENAI_API_KEY is required for WhisperProvider');
    this.apiKey = apiKey;
    this.model = model || 'whisper-1';
  }

  async transcribeBatch(audioBuffer, opts = {}) {
    const form = new FormData();
    form.append('file', audioBuffer, {
      filename: `audio.${(opts.mimeType || 'audio/webm').split('/')[1] || 'webm'}`,
      contentType: opts.mimeType || 'audio/webm',
    });
    form.append('model', this.model);
    form.append('response_format', 'verbose_json');
    form.append('timestamp_granularities[]', 'word');
    // No forced language: let Whisper detect it so code-switched audio
    // isn't forced into a single-language grammar.
    if (opts.languageHint) form.append('language', opts.languageHint);
    // Biasing vocabulary only, never rewriting instructions:
    if (opts.vocabularyHint) form.append('prompt', opts.vocabularyHint);

    const res = await fetch(OPENAI_TRANSCRIBE_URL, {
      method: 'POST',
      headers: { Authorization: `Bearer ${this.apiKey}`, ...form.getHeaders() },
      body: form,
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`Whisper error ${res.status}: ${errText}`);
    }
    const json = await res.json();
    return this._normalize(json);
  }

  _normalize(json) {
    // verbose_json word timestamps don't include a confidence score
    // directly, but expose avg_logprob per segment; we convert that to an
    // approximate 0..1 confidence so the UI can still flag uncertain spans.
    const words = [];
    for (const seg of json.segments || []) {
      const segConfidence = logprobToConfidence(seg.avg_logprob);
      const segWords = seg.words || [];
      if (segWords.length) {
        for (const w of segWords) {
          words.push({
            text: w.word.trim(),
            start: w.start,
            end: w.end,
            confidence: segConfidence,
            uncertain: false,
          });
        }
      } else {
        // Some responses omit word-level detail for very short/garbled segments
        words.push({
          text: seg.text.trim(),
          start: seg.start,
          end: seg.end,
          confidence: segConfidence,
          uncertain: false,
        });
      }
    }
    markLowConfidenceWords(words);

    return {
      text: json.text || '',
      words,
      detectedLanguage: json.language || 'unknown',
      provider: 'whisper',
      raw: json,
    };
  }
}

function logprobToConfidence(avgLogprob) {
  if (typeof avgLogprob !== 'number') return 0.7;
  // avg_logprob is typically in [-1, 0] for confident speech and drops
  // sharply (e.g. below -1) for noisy/garbled audio. Clamp + rescale.
  const clamped = Math.max(-2, Math.min(0, avgLogprob));
  return 1 + clamped / 2; // -2 -> 0.0, 0 -> 1.0
}
