import { DeepgramProvider } from './deepgramProvider.js';
import { WhisperProvider } from './whisperProvider.js';

let cached = {};

/**
 * Returns a ready-to-use STT provider instance.
 * `role` lets the app request a specific one regardless of the default
 * (e.g. routes/transcribe.js always wants Whisper for the final
 * high-accuracy pass, while wsServer.js wants whichever provider supports
 * live streaming).
 */
export function getSttProvider(role = 'default') {
  const key = role === 'default' ? process.env.STT_PROVIDER || 'deepgram' : role;
  if (cached[key]) return cached[key];

  let instance;
  switch (key) {
    case 'deepgram':
      instance = new DeepgramProvider({
        apiKey: process.env.DEEPGRAM_API_KEY,
        model: process.env.DEEPGRAM_MODEL,
        language: process.env.DEEPGRAM_LANGUAGE,
      });
      break;
    case 'whisper':
      instance = new WhisperProvider({
        apiKey: process.env.OPENAI_API_KEY,
        model: process.env.OPENAI_STT_MODEL,
      });
      break;
    default:
      throw new Error(`Unknown STT provider "${key}". Add it in providers/stt/index.js`);
  }
  cached[key] = instance;
  return instance;
}

// Exposed for tests so a fresh env can be re-read between cases.
export function _resetSttProviderCache() {
  cached = {};
}
