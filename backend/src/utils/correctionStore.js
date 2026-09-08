import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '../../data');
const STORE_PATH = path.join(DATA_DIR, 'corrections.json');
const MAX_CORRECTIONS = 500; // cap so the file never grows unbounded

const DEFAULT = () => ({
  stt: {
    corrections: {},   // { "misheard": "actual" }
    keywords: [],      // boosted into Deepgram's keywords param
    history: [],       // last N corrections for the UI review panel
    count: 0,
  },
  tts: {
    substitutions: {}, // { "word": "phonetic-or-alternative" }
    history: [],
    count: 0,
  },
});

function load() {
  try {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    if (!fs.existsSync(STORE_PATH)) return DEFAULT();
    return JSON.parse(fs.readFileSync(STORE_PATH, 'utf8'));
  } catch {
    return DEFAULT();
  }
}

function save(data) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  // Write atomically via a temp file so a crash mid-write never corrupts data
  const tmp = STORE_PATH + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2), 'utf8');
  fs.renameSync(tmp, STORE_PATH);
}

// ── STT ─────────────────────────────────────────────────────────────────

/**
 * Learn from the diff between what Deepgram/Whisper heard vs what the
 * user actually said. Caller passes individual (wrong, correct) pairs —
 * the diff extraction happens in the feedback route.
 */
export function addSttCorrection(wrong, correct) {
  if (!wrong || !correct || wrong.toLowerCase() === correct.toLowerCase()) return;
  const data = load();
  data.stt.corrections[wrong.toLowerCase()] = correct;

  // Add the correct word to Deepgram keywords (boost it so the model
  // prefers it over acoustically-similar alternatives next time)
  if (!data.stt.keywords.includes(correct)) {
    data.stt.keywords.push(correct);
    if (data.stt.keywords.length > MAX_CORRECTIONS) data.stt.keywords.shift();
  }

  data.stt.history.unshift({ from: wrong, to: correct, at: new Date().toISOString() });
  if (data.stt.history.length > 50) data.stt.history.pop();
  data.stt.count++;
  save(data);
}

/**
 * Apply learned STT corrections as a post-processing pass on the final
 * transcript. This catches systematic misrecognitions (e.g. every time
 * the speaker says "Chennai" the model hears "Shennai") without ever
 * changing words the model got right.
 */
export function applySttCorrections(text) {
  const data = load();
  const map = data.stt.corrections;
  if (!Object.keys(map).length) return text;
  return text.replace(/\b[\w']+\b/g, (word) => {
    const fix = map[word.toLowerCase()];
    if (!fix) return word;
    // Preserve original capitalisation (Chennai not CHENNAI or chennai)
    if (word[0] === word[0].toUpperCase() && word[0] !== word[0].toLowerCase()) {
      return fix[0].toUpperCase() + fix.slice(1);
    }
    return fix;
  });
}

/** Returns the keyword list for injecting into Deepgram's query params. */
export function getSttKeywords() {
  return load().stt.keywords;
}

// ── TTS ─────────────────────────────────────────────────────────────────

/**
 * Learn a pronunciation fix. `word` is what the user typed; `substitute`
 * is what we should actually send to the TTS engine instead (could be a
 * phonetic respelling, a space-separated pronunciation, or a synonym that
 * the engine pronounces correctly).
 */
export function addTtsSubstitution(word, substitute) {
  if (!word || !substitute) return;
  const data = load();
  data.tts.substitutions[word.trim()] = substitute.trim();
  data.tts.history.unshift({ from: word, to: substitute, at: new Date().toISOString() });
  if (data.tts.history.length > 50) data.tts.history.pop();
  data.tts.count++;
  save(data);
}

/**
 * Preprocess TTS input text, replacing known mispronounced words with
 * the user-approved alternatives before the text ever reaches the TTS API.
 */
export function applyTtsSubstitutions(text) {
  const data = load();
  const subs = data.tts.substitutions;
  if (!Object.keys(subs).length) return text;
  let result = text;
  for (const [word, sub] of Object.entries(subs)) {
    // Case-insensitive whole-word match
    const re = new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
    result = result.replace(re, sub);
  }
  return result;
}

// ── Stats / admin ────────────────────────────────────────────────────────

export function getStats() {
  const data = load();
  return {
    sttCorrections: data.stt.count,
    ttsCorrections: data.tts.count,
    totalCorrections: data.stt.count + data.tts.count,
  };
}

export function getAllCorrections() {
  return load();
}

export function deleteSttCorrection(word) {
  const data = load();
  delete data.stt.corrections[word.toLowerCase()];
  data.stt.keywords = data.stt.keywords.filter((k) => k.toLowerCase() !== word.toLowerCase());
  save(data);
}

export function deleteTtsSubstitution(word) {
  const data = load();
  delete data.tts.substitutions[word];
  save(data);
}
