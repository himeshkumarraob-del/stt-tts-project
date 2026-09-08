const DEFAULT_THRESHOLD = 0.55;

/**
 * Mutates a words[] array in place, setting `uncertain: true` on any word
 * below the confidence threshold. This is how the "don't hallucinate,
 * flag it instead" requirement surfaces all the way to the UI: the
 * frontend renders uncertain words with a dashed underline instead of
 * silently accepting or dropping them.
 */
export function markLowConfidenceWords(words, threshold = Number(process.env.LOW_CONFIDENCE_THRESHOLD) || DEFAULT_THRESHOLD) {
  for (const w of words) {
    w.uncertain = typeof w.confidence === 'number' && w.confidence < threshold;
  }
  return words;
}

/** Overall transcript confidence, used for the top-level UI confidence meter. */
export function overallConfidence(words) {
  if (!words.length) return 0;
  const sum = words.reduce((acc, w) => acc + (w.confidence ?? 0), 0);
  return sum / words.length;
}
