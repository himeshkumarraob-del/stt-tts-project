import { Router } from 'express';
import { getTtsProvider } from '../providers/tts/index.js';
import { applyTtsSubstitutions } from '../utils/correctionStore.js';

export const ttsRouter = Router();

ttsRouter.get('/voices', async (req, res) => {
  try {
    const provider = getTtsProvider(req.query.provider || undefined);
    const voices = await provider.listVoices();
    res.json({ voices });
  } catch (err) {
    console.error('[tts:voices]', err);
    res.status(502).json({ error: 'TTS_PROVIDER_ERROR', message: 'Could not load voice list.' });
  }
});

ttsRouter.post('/', async (req, res) => {
  const { text, voiceId, rate, pitch, format, language, provider: providerName } = req.body || {};

  if (!text || !text.trim()) {
    return res.status(400).json({ error: 'MISSING_TEXT', message: 'Provide non-empty "text".' });
  }
  if (text.length > 5000) {
    return res.status(400).json({ error: 'TEXT_TOO_LONG', message: 'Limit text to 5000 characters per request.' });
  }

  try {
    const provider = getTtsProvider(providerName || undefined);

    // Apply learned pronunciation substitutions BEFORE sending to the TTS
    // engine — this is where user corrections actually take effect.
    const processedText = applyTtsSubstitutions(text.trim());

    const { audio, mimeType } = await provider.synthesize(processedText, {
      voiceId,
      rate: clamp(Number(rate) || 1.0, 0.5, 2.0),
      pitch: clamp(Number(pitch) || 0, -6, 6),
      format,
      language,
    });

    res.setHeader('Content-Type', mimeType);
    res.setHeader('Content-Disposition', 'inline; filename="speech.mp3"');
    res.send(audio);
  } catch (err) {
    console.error('[tts:synthesize]', err);
    res.status(502).json({
      error: 'TTS_PROVIDER_ERROR',
      message: 'Speech synthesis failed. Please try again.',
      detail: process.env.NODE_ENV === 'production' ? undefined : String(err.message),
    });
  }
});

function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}
