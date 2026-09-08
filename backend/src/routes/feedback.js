import { Router } from 'express';
import {
  addSttCorrection,
  addTtsSubstitution,
  getStats,
  getAllCorrections,
  deleteSttCorrection,
  deleteTtsSubstitution,
} from '../utils/correctionStore.js';

export const feedbackRouter = Router();

/**
 * POST /api/feedback/stt
 * Body: { original: "what deepgram said", corrected: "what user fixed it to" }
 * Diffs the two transcripts word-by-word, learns each substitution.
 */
feedbackRouter.post('/stt', (req, res) => {
  const { original, corrected } = req.body || {};
  if (!original || !corrected) {
    return res.status(400).json({ error: 'MISSING_FIELDS', message: 'Provide original and corrected.' });
  }

  const learned = diffAndLearn(original, corrected);
  res.json({ learned, stats: getStats() });
});

/**
 * POST /api/feedback/tts
 * Body: { word: "Bengaluru", substitute: "Bengalooru" }
 * Stores a text-substitution so future TTS calls replace `word` with `substitute`.
 */
feedbackRouter.post('/tts', (req, res) => {
  const { word, substitute } = req.body || {};
  if (!word || !substitute) {
    return res.status(400).json({ error: 'MISSING_FIELDS', message: 'Provide word and substitute.' });
  }
  addTtsSubstitution(word.trim(), substitute.trim());
  res.json({ learned: { from: word, to: substitute }, stats: getStats() });
});

/** GET /api/feedback/stats — how many corrections have been learned */
feedbackRouter.get('/stats', (req, res) => res.json(getStats()));

/** GET /api/feedback/all — full correction store (for the review panel) */
feedbackRouter.get('/all', (req, res) => res.json(getAllCorrections()));

/** DELETE /api/feedback/stt/:word — remove one STT correction */
feedbackRouter.delete('/stt/:word', (req, res) => {
  deleteSttCorrection(decodeURIComponent(req.params.word));
  res.json({ ok: true, stats: getStats() });
});

/** DELETE /api/feedback/tts/:word — remove one TTS substitution */
feedbackRouter.delete('/tts/:word', (req, res) => {
  deleteTtsSubstitution(decodeURIComponent(req.params.word));
  res.json({ ok: true, stats: getStats() });
});

/**
 * Word-by-word diff between original and corrected transcript.
 * Handles the most common case: same word count, one or more words
 * changed. Also handles simple additions/deletions via LCS alignment.
 */
function diffAndLearn(original, corrected) {
  const origTokens = tokenize(original);
  const corrTokens = tokenize(corrected);
  const learned = [];

  // Use longest-common-subsequence to align tokens so we catch
  // substitutions even when words are inserted or deleted around them.
  const lcs = computeLCS(origTokens, corrTokens);
  const aligned = alignFromLCS(origTokens, corrTokens, lcs);

  for (const [o, c] of aligned) {
    if (o && c && o.toLowerCase() !== c.toLowerCase()) {
      addSttCorrection(o, c);
      learned.push({ from: o, to: c });
    }
  }
  return learned;
}

function tokenize(text) {
  return text.trim().split(/\s+/).filter(Boolean);
}

function computeLCS(a, b) {
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = a[i - 1].toLowerCase() === b[j - 1].toLowerCase()
        ? dp[i - 1][j - 1] + 1
        : Math.max(dp[i - 1][j], dp[i][j - 1]);
  return dp;
}

function alignFromLCS(a, b, dp) {
  const pairs = [];
  let i = a.length, j = b.length;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1].toLowerCase() === b[j - 1].toLowerCase()) {
      // Matched — no correction needed
      i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      // Word inserted in corrected — skip (added word, nothing to learn for STT)
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      // Word in original not in corrected — substitution
      pairs.unshift([a[i - 1], b[j] || null]);
      i--;
    }
  }
  return pairs;
}
