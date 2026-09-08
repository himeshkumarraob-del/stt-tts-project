/**
 * SttProvider — the contract every speech-to-text backend must satisfy.
 *
 * The rest of the app (routes, accent layer, websocket bridge) only ever
 * talks to this interface, never to a vendor SDK directly. That is what
 * lets you swap Deepgram <-> Whisper <-> Google <-> a self-hosted model
 * by writing one new file and one line in providers/stt/index.js.
 *
 * Every provider must return its result normalized to this shape:
 *
 * {
 *   text: string,                 // full transcript, verbatim (no "correction")
 *   words: [{
 *     text: string,
 *     start: number,              // seconds
 *     end: number,                // seconds
 *     confidence: number,         // 0..1
 *     uncertain: boolean          // confidence < LOW_CONFIDENCE_THRESHOLD
 *   }],
 *   detectedLanguage: string,     // BCP-47, e.g. "en-IN", "hi-IN", or "en+hi" for code-switch
 *   provider: string,
 *   raw: object                  // original provider payload, for debugging only
 * }
 */
export class SttProvider {
  /**
   * Transcribe a complete audio buffer (used for file upload / "finalize" flow).
   * @param {Buffer} audioBuffer
   * @param {{mimeType: string, languageHint?: string}} opts
   * @returns {Promise<NormalizedTranscript>}
   */
  // eslint-disable-next-line no-unused-vars
  async transcribeBatch(audioBuffer, opts) {
    throw new Error('transcribeBatch() not implemented');
  }

  /**
   * Open a live/streaming session. Used by the WebSocket bridge for
   * real-time partial transcripts while the user is still talking.
   * Providers without native streaming (e.g. Whisper via REST) may
   * implement this with short-buffered pseudo-streaming, or throw
   * SttProvider.NOT_SUPPORTED and let the caller fall back to batch mode.
   * @returns {Promise<StreamingSttSession>}
   */
  async openStream(_opts) {
    throw new Error('openStream() not implemented');
  }
}

export const NOT_SUPPORTED = Symbol('stt-streaming-not-supported');

/**
 * StreamingSttSession — returned by openStream().
 * {
 *   sendAudio(chunk: Buffer): void,
 *   onResult(cb: (result: PartialOrFinalResult) => void): void,
 *   close(): void
 * }
 * PartialOrFinalResult: { isFinal: boolean, text, words, detectedLanguage }
 */
