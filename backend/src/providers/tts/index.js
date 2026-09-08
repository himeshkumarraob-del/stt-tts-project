import { AzureTtsProvider } from './azureProvider.js';
import { ElevenLabsProvider } from './elevenLabsProvider.js';
import { SarvamProvider } from './sarvamProvider.js';

let cached = {};

export function getTtsProvider(role = 'default') {
  const key = role === 'default' ? process.env.TTS_PROVIDER || 'azure' : role;
  if (cached[key]) return cached[key];

  let instance;
  switch (key) {
    case 'azure':
      instance = new AzureTtsProvider({
        apiKey: process.env.AZURE_SPEECH_KEY,
        region: process.env.AZURE_SPEECH_REGION,
      });
      break;
    case 'elevenlabs':
      instance = new ElevenLabsProvider({ apiKey: process.env.ELEVENLABS_API_KEY });
      break;
    case 'sarvam':
      instance = new SarvamProvider({
        apiKey: process.env.SARVAM_API_KEY,
        model: process.env.SARVAM_TTS_MODEL,
      });
      break;
    default:
      throw new Error(`Unknown TTS provider "${key}". Add it in providers/tts/index.js`);
  }
  cached[key] = instance;
  return instance;
}

export function _resetTtsProviderCache() {
  cached = {};
}
