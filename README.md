# Baat — STT + TTS for Indian English & regional accents

A modular speech-to-text / text-to-speech system built around one rule:
**an accent is not a different word.** The pipeline is designed to widen
what the recognizer expects (Indian-English phonetics, code-switching,
disfluencies) rather than "correct" a transcript after the fact.

```
indic-voice/
├── backend/                  Node/Express API — the only place API keys live
│   └── src/
│       ├── providers/stt/    Deepgram + Whisper, behind one interface
│       ├── providers/tts/    Azure + ElevenLabs, behind one interface
│       ├── accent/           accent-aware preprocessing pipeline
│       ├── utils/            confidence scoring, SSML building
│       ├── routes/           /api/transcribe, /api/tts, /api/health
│       ├── wsServer.js       real-time streaming bridge
│       └── server.js         entrypoint
└── frontend/                 Static HTML/CSS/JS — no build step required
    ├── index.html
    ├── css/style.css
    └── js/{app,recorder,waveform}.js
```

## Why these providers

| Concern | Choice | Why |
|---|---|---|
| Streaming STT | **Deepgram** (`nova-2`, `language=en-IN`) | Native Indian-English acoustic model, true low-latency streaming with interim results, per-word confidence, built-in punctuation |
| Batch/high-accuracy STT | **Whisper** (OpenAI) | Very strong on heavy code-switching, noise, and diverse accents; used as the "finalize" pass and as a pluggable alternative |
| TTS | **Azure Neural TTS** | By far the widest catalogue of Indian-English and Indian-regional-language neural voices (en-IN, hi-IN, ta-IN, te-IN, kn-IN, ml-IN, bn-IN, …) |
| TTS alternative | **ElevenLabs** | Very natural English prosody, one line to swap in via `TTS_PROVIDER=elevenlabs` |

Every provider implements a small interface (`SttProvider` / `TtsProvider`).
Swapping engines — including to a self-hosted model — means writing one
new file and registering it in `providers/*/index.js`. Nothing else in
the app changes.

## The accent-aware pipeline (`src/accent/accentPreprocessor.js`)

1. **Analyze speech characteristics** — signal-level stats plus (if you
   plug one in) an acoustic accent classifier.
2. **Identify likely accent influence** — a language/accent guess, used
   only to steer step 3 and to populate the UI badge.
3. **Adapt recognition** — sets the STT call's locale/language hint
   (`en-IN` by default) so the *acoustic model* — not a text filter —
   expects Indian-English phonetics.
4. **Transcribe** — the actual STT call. Verbatim output, no correction.
5. **Never translate/rewrite** — enforced structurally: nothing in this
   path calls a translation or paraphrase function. A separate,
   metadata-only step (`tagCodeSwitching`) flags likely Tamil/Hindi/
   Telugu/Kannada/Malayalam/Bengali function words for the UI's
   "code-switch detected" badge — it never changes `text` or `words[]`.

**Honesty about step 1–2:** real acoustic accent identification (e.g.
telling a Tamil-influenced accent apart from a Bengali-influenced one
from the audio itself) needs a trained classifier — there's no reliable
way to do that from text or simple signal stats. The shipped heuristic
defaults to "Indian English" and is wired as a clean extension point
(`registerAccentClassifier()`) for a real model such as a wav2vec2/XLS-R
model fine-tuned on an Indian-accent corpus (e.g. Svarah, IndicTTS). Until
you plug one in, the accent badge is a low-confidence hint, not a claim.

## Not hallucinating on unclear audio

Both providers return per-word confidence (Deepgram natively; Whisper via
an approximation from `avg_logprob`, documented in `whisperProvider.js`).
`utils/confidence.js` flags any word below `LOW_CONFIDENCE_THRESHOLD`
(default `0.55`) as `uncertain`. The frontend renders those with a dashed
underline instead of presenting them as equally reliable text — the
system never invents words to fill a gap; low-confidence audio surfaces
as a flagged, editable span instead.

## Setup

```bash
cd backend
cp .env.example .env      # fill in the keys you plan to use
npm install
npm start                  # serves API + static frontend on :8080
```

Open `http://localhost:8080`. You need at least one STT key
(`DEEPGRAM_API_KEY` or `OPENAI_API_KEY`) and one TTS key
(`AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION`, or `ELEVENLABS_API_KEY`).
Nothing about the architecture changes if you only have one provider's
key — just point `STT_PROVIDER` / `TTS_PROVIDER` at it.

**Security:** API keys are read from `process.env` only, server-side.
The browser never sees them — it only calls your own `/api/...` routes.
`.env` is gitignored; `.env.example` documents every variable.

## UI

- 🎙️ Record/Stop with a live VU-meter-style waveform (`waveform.js`,
  driven by an `AnalyserNode` — no dependency on the STT engine)
- Real-time partial transcript over a WebSocket bridge while recording,
  then a higher-accuracy "finalize" pass on stop
- Detected-language and accent-influence badges, plus a code-switch flag
- Editable transcript, with uncertain words dashed-underlined
- Confidence meter
- TTS panel: voice picker (populated from the active provider), speed
  and pitch sliders, playback, and a download button
- Responsive two-column layout that stacks on mobile; visible focus
  states; `prefers-reduced-motion` respected

## Testing this yourself

I validated the pieces I can validate without real credentials or a
microphone in this environment:
- every backend file passes a Node syntax check,
- the server boots cleanly and serves the frontend,
- calling `/api/transcribe` with no file returns a clean `400`,
- calling `/api/tts` with no provider key configured returns a clean
  `502` with a user-facing message instead of crashing the process,
- the error-handling and rate-limit middleware are wired end-to-end.

I could **not** run real accented audio through Deepgram/Whisper/Azure
from here — that needs live API keys and a microphone, neither of which
this sandbox has, and outbound network access here is restricted to
package registries. Before you rely on this in production, run the test
plan below with your own keys:

1. **Accent coverage** — record the same 5–6 sentences read by speakers
   with Tamil, Telugu, Hindi, Kannada, Malayalam, and Bengali-influenced
   English, plus one unaccented baseline. Compare word-error-rate.
2. **Speed** — same sentence read slow / normal / fast.
3. **Code-switching** — sentences that mix English with Tamil/Hindi/
   Telugu mid-sentence; confirm the transcript keeps the actual words
   (romanized or native-script, whichever the provider returns) rather
   than translating them, and that the code-switch badge fires.
4. **Noise** — repeat a subset with fan/traffic/crowd noise in the
   background; confirm uncertain spans get flagged rather than invented.
5. **Names/places** — send "Bengaluru", "Thiruvananthapuram",
   "Coimbatore" etc. through TTS and listen for correct pronunciation;
   extend `accent/indicLexicon.js` for any that still come out wrong.

If step 1 shows a particular accent underperforming, the fix belongs in
`accentPreprocessor.js` (tune the language hint or plug in a real
classifier) — never in a post-hoc find-and-replace on the transcript,
which would reintroduce the "accent → different word" problem this
system exists to avoid.

## Extending

- **New STT engine:** implement `SttProvider` in a new file under
  `providers/stt/`, register it in `providers/stt/index.js`.
- **New TTS engine:** same pattern under `providers/tts/`.
- **Real accent classifier:** call `registerAccentClassifier(fn)` from
  `accent/accentPreprocessor.js` at startup with your model's inference
  function.
- **More pronunciation fixes:** add entries to
  `accent/indicLexicon.js#PRONUNCIATION_HINTS`.
