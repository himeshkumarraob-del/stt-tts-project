/**
 * TtsProvider — contract every text-to-speech backend must satisfy.
 *
 * {
 *   listVoices(): Promise<Voice[]>,
 *   synthesize(text, opts): Promise<{ audio: Buffer, mimeType: string }>
 * }
 *
 * Voice: {
 *   id: string,            // provider-specific voice id, passed back in opts.voiceId
 *   label: string,         // human-readable, e.g. "Neerja (Indian English, Female)"
 *   language: string,      // BCP-47, e.g. "en-IN", "hi-IN", "ta-IN"
 *   gender: "female"|"male"|"neutral"
 * }
 *
 * opts: {
 *   voiceId: string,
 *   rate: number,     // 0.5 - 2.0, 1.0 = normal
 *   pitch: number,     // -1.0 - 1.0 semitone-ish offset, 0 = normal
 *   format: "mp3"|"wav"
 * }
 */
export class TtsProvider {
  async listVoices() {
    throw new Error('listVoices() not implemented');
  }
  // eslint-disable-next-line no-unused-vars
  async synthesize(text, opts) {
    throw new Error('synthesize() not implemented');
  }
}
