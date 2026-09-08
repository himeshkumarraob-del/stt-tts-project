import { PRONUNCIATION_HINTS } from '../accent/indicLexicon.js';

function escapeXml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/**
 * Builds SSML that:
 *  - applies the requested speaking rate/pitch,
 *  - adds short <break> pauses on sentence punctuation so speech doesn't
 *    sound flat/robotic,
 *  - emphasizes text the user wrapped in *asterisks* or CAPS, so intent
 *    ("I said NO") survives into the audio,
 *  - substitutes known Indian names/places with a phoneme hint so they
 *    aren't flattened into a US/UK pronunciation.
 */
export function buildSsml(text, { rate = 1.0, pitchSemitones = 0, voiceId, lang = 'en-IN' } = {}) {
  const ratePct = `${Math.round(rate * 100)}%`;
  const pitchStr = pitchSemitones === 0 ? '+0st' : `${pitchSemitones > 0 ? '+' : ''}${pitchSemitones}st`;

  const withEmphasis = escapeXml(text)
    // *word* -> emphasis
    .replace(/\*([^*]+)\*/g, '<emphasis level="strong">$1</emphasis>')
    // ALL-CAPS word (3+ letters) -> emphasis, but leave normal acronyms-in-context alone is out of scope for a simple pass
    .replace(/\b([A-Z]{3,})\b/g, '<emphasis level="moderate">$1</emphasis>');

  const withPauses = withEmphasis
    .replace(/\.\.\./g, '<break time="500ms"/>')
    .replace(/([.!?])(\s|$)/g, '$1<break time="350ms"/>$2')
    .replace(/([,;:])(\s|$)/g, '$1<break time="150ms"/>$2');

  const withPronunciation = Object.entries(PRONUNCIATION_HINTS).reduce((acc, [word, hint]) => {
    const re = new RegExp(`\\b${word}\\b`, 'ig');
    return acc.replace(re, (match) => `<phoneme alphabet="x-microsoft-sapi" ph="${hint}">${match}</phoneme>`);
  }, withPauses);

  return `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="${lang}">
  <voice name="${voiceId}">
    <prosody rate="${ratePct}" pitch="${pitchStr}">
      ${withPronunciation}
    </prosody>
  </voice>
</speak>`;
}
