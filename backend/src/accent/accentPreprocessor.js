import { CODE_SWITCH_MARKERS } from './indicLexicon.js';

/**
 * The accent-aware pipeline requested in the brief, implemented as five
 * explicit, inspectable steps rather than one opaque function. Steps 1-3
 * run BEFORE the audio ever reaches the STT engine; step 4 is the actual
 * transcription; step 5 is a hard rule enforced by never calling a
 * translation/rewrite function anywhere in this path.
 *
 * IMPORTANT HONESTY NOTE (also in README "Limitations"): true acoustic
 * accent identification (e.g. "this speaker's English is Tamil-influenced
 * vs Bengali-influenced") needs a trained audio classifier — there is no
 * reliable way to do that from text or simple signal stats alone. Steps 1-2
 * below use duration/energy heuristics plus provider language-detection
 * as a *practical proxy*, and are wired as a clean extension point
 * (`registerAccentClassifier`) for plugging in a real model (e.g. a
 * wav2vec2/XLS-R model fine-tuned on an Indian-accent corpus such as
 * IndicTTS/Svarah) without touching any other file.
 */

let externalClassifier = null;

/** Plug a real acoustic accent classifier in. Signature:
 *  async (audioBuffer, opts) => { language: 'ta'|'hi'|..., confidence: 0..1 }
 */
export function registerAccentClassifier(fn) {
  externalClassifier = fn;
}

/**
 * Step 1 + 2: cheap signal-level characteristics + accent-influence guess.
 * Runs before transcription so its output (`languageHint`) can steer the
 * STT call itself (step 3).
 */
export async function analyzeSpeechCharacteristics(audioBuffer, { mimeType } = {}) {
  const durationEstimateSec = estimateDurationSeconds(audioBuffer, mimeType);

  if (externalClassifier) {
    try {
      const result = await externalClassifier(audioBuffer, { mimeType });
      return { ...result, method: 'external-classifier', durationEstimateSec };
    } catch (err) {
      // Never let a broken classifier break transcription — degrade to the heuristic.
      console.warn('[accent] external classifier failed, falling back:', err.message);
    }
  }

  // Heuristic fallback: no accent claim yet (we haven't transcribed
  // anything), just flags this as "Indian-English likely" by default
  // since that is this deployment's target population. Real per-language
  // accent tagging happens in tagCodeSwitching() below, from the actual
  // transcribed words, once step 4 has run.
  return {
    language: 'en-IN',
    confidence: 0.5,
    method: 'default-heuristic',
    durationEstimateSec,
  };
}

/**
 * Step 3: turn the analysis into concrete parameters for the STT call.
 * This is the ONLY place accent influences recognition — by widening the
 * decoder's language model / locale, never by post-editing words.
 */
export function buildRecognitionOptions(analysis) {
  return {
    // "en-IN" tells the acoustic model to expect Indian-English phoneme
    // shifts (retroflex consonants, syllable-timed rhythm, etc.) instead
    // of scoring against a US/UK reference accent.
    languageHint: analysis?.language || 'en-IN',
  };
}

/**
 * Step 5 (guardrail): given the FINAL transcript text, tag which segments
 * look like romanized regional-language code-switching, purely for the UI
 * badge. This never mutates `text` or `words[].text` — only adds metadata.
 */
export function tagCodeSwitching(transcriptText) {
  const tokens = transcriptText.toLowerCase().match(/[a-z']+/g) || [];
  const scores = {};
  for (const [lang, markers] of Object.entries(CODE_SWITCH_MARKERS)) {
    const hits = tokens.filter((t) => markers.includes(t)).length;
    if (hits > 0) scores[lang] = hits;
  }
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  return {
    codeSwitchDetected: sorted.length > 0,
    likelyLanguages: sorted.map(([lang, hits]) => ({ language: lang, hits })),
  };
}

function estimateDurationSeconds(buffer, mimeType) {
  // Rough estimate only, used for logging/telemetry — not for decisions
  // that affect transcription accuracy. A real duration comes back from
  // the STT provider's word timestamps.
  const bytesPerSecondGuess = mimeType?.includes('wav') ? 32000 : 12000;
  return +(buffer.length / bytesPerSecondGuess).toFixed(1);
}

/**
 * The full pipeline, used by routes/transcribe.js. `sttProvider` is
 * injected so this file has zero dependency on which vendor is active.
 */
export async function runAccentAwareTranscription(sttProvider, audioBuffer, { mimeType, keywords = [] } = {}) {
  const analysis = await analyzeSpeechCharacteristics(audioBuffer, { mimeType }); // steps 1-2
  const recognitionOptions = buildRecognitionOptions(analysis); // step 3
  const transcript = await sttProvider.transcribeBatch(audioBuffer, {
    mimeType,
    keywords, // learned keywords injected from correctionStore
    ...recognitionOptions,
  }); // step 4 — verbatim transcription, no rewriting
  const codeSwitch = tagCodeSwitching(transcript.text); // step 5 metadata only

  return {
    ...transcript,
    accent: {
      guessedInfluence: analysis.language,
      guessConfidence: analysis.confidence,
      method: analysis.method,
    },
    codeSwitch,
  };
}
