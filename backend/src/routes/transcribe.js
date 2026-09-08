import { Router } from 'express';
import multer from 'multer';
import { getSttProvider } from '../providers/stt/index.js';
import { runAccentAwareTranscription } from '../accent/accentPreprocessor.js';
import { overallConfidence } from '../utils/confidence.js';
import { applySttCorrections, getSttKeywords } from '../utils/correctionStore.js';

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: (Number(process.env.MAX_UPLOAD_MB) || 25) * 1024 * 1024 },
});

export const transcribeRouter = Router();

transcribeRouter.post('/', upload.single('audio'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'MISSING_AUDIO', message: 'Attach an audio file under field name "audio".' });
  }

  try {
    const provider = getSttProvider(req.query.provider || undefined);

    // Inject learned keywords so Deepgram boosts words the user has
    // previously corrected — this improves recognition at the acoustic
    // model level, before text even comes back.
    const keywords = getSttKeywords();

    const result = await runAccentAwareTranscription(provider, req.file.buffer, {
      mimeType: req.file.mimetype,
      keywords,
    });

    // Apply learned post-processing corrections (systematic misrecognitions
    // that the model gets wrong regardless of keywords boosting).
    const correctedText = applySttCorrections(result.text);
    const correctedWords = result.words.map((w) => ({
      ...w,
      text: applySttCorrections(w.text),
    }));

    res.json({
      text: correctedText,
      originalText: result.text, // send original so frontend can compute diff for future corrections
      words: correctedWords,
      confidence: overallConfidence(correctedWords),
      detectedLanguage: result.detectedLanguage,
      accent: result.accent,
      codeSwitch: result.codeSwitch,
      provider: result.provider,
      keywordsApplied: keywords.length,
    });
  } catch (err) {
    console.error('[transcribe]', err);
    res.status(502).json({
      error: 'STT_PROVIDER_ERROR',
      message: 'The speech recognition service could not process this audio. Please try again.',
      detail: process.env.NODE_ENV === 'production' ? undefined : String(err.message),
    });
  }
});
