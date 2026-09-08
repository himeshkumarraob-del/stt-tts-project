import { Router } from 'express';

export const healthRouter = Router();

healthRouter.get('/', (req, res) => {
  res.json({
    ok: true,
    sttProvider: process.env.STT_PROVIDER || 'deepgram',
    ttsProvider: process.env.TTS_PROVIDER || 'azure',
    time: new Date().toISOString(),
  });
});
