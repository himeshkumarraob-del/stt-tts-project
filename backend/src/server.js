import 'dotenv/config';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';

import { transcribeRouter } from './routes/transcribe.js';
import { feedbackRouter } from './routes/feedback.js';
import { ttsRouter } from './routes/tts.js';
import { healthRouter } from './routes/health.js';
import { attachTranscriptionWebSocket } from './wsServer.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();

// ── Security / hygiene ──────────────────────────────────────────────────
// API keys never touch the client: every provider call happens here on
// the server, reading credentials only from process.env (see .env.example).
// Never log full request bodies containing audio or long text.
const allowedOrigins = (process.env.CORS_ORIGIN || '').split(',').map((s) => s.trim()).filter(Boolean);
app.use(
  cors({
    origin: allowedOrigins.length ? allowedOrigins : true,
  })
);
app.use(express.json({ limit: '1mb' }));

const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  limit: 30, // 30 requests/minute/IP across STT+TTS — tune per deployment
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'RATE_LIMITED', message: 'Too many requests. Please slow down.' },
});
app.use('/api/', apiLimiter);

// ── Routes ───────────────────────────────────────────────────────────────
app.use('/api/health', healthRouter);
app.use('/api/transcribe', transcribeRouter);
app.use('/api/feedback', feedbackRouter);
app.use('/api/tts', ttsRouter);

// Serve the static frontend (built as plain HTML/JS, no build step needed)
app.use(express.static(path.join(__dirname, '../../frontend')));

// ── Central error handler ───────────────────────────────────────────────
// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  console.error('[unhandled]', err);
  if (err?.type === 'entity.too.large' || err?.code === 'LIMIT_FILE_SIZE') {
    return res.status(413).json({ error: 'FILE_TOO_LARGE', message: 'Audio file exceeds the upload limit.' });
  }
  res.status(500).json({ error: 'INTERNAL_ERROR', message: 'Something went wrong on our end.' });
});

const server = http.createServer(app);
attachTranscriptionWebSocket(server);

const PORT = process.env.PORT || 8080;
server.listen(PORT, () => {
  console.log(`indic-voice backend listening on :${PORT}`);
  console.log(`  STT provider: ${process.env.STT_PROVIDER || 'deepgram'}`);
  console.log(`  TTS provider: ${process.env.TTS_PROVIDER || 'azure'}`);
});
