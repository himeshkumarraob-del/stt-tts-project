/**
 * Thin wrapper around getUserMedia + MediaRecorder.
 * Exposes:
 *   - an AnalyserNode for the live waveform
 *   - a callback fired with each audio chunk (for streaming over WS)
 *   - start()/stop() returning the full Blob for the "finalize" batch call
 */
class VoiceRecorder {
  constructor({ onChunk, timesliceMs = 250 } = {}) {
    this.onChunk = onChunk;
    this.timesliceMs = timesliceMs;
    this.mediaRecorder = null;
    this.stream = null;
    this.chunks = [];
    this.audioCtx = null;
    this.analyser = null;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = this.audioCtx.createMediaStreamSource(this.stream);
    this.analyser = this.audioCtx.createAnalyser();
    this.analyser.fftSize = 1024;
    source.connect(this.analyser);

    const mimeType = pickSupportedMimeType();
    this.mediaRecorder = new MediaRecorder(this.stream, mimeType ? { mimeType } : undefined);
    this.chunks = [];

    this.mediaRecorder.addEventListener('dataavailable', (e) => {
      if (e.data && e.data.size > 0) {
        this.chunks.push(e.data);
        if (this.onChunk) e.data.arrayBuffer().then((buf) => this.onChunk(buf));
      }
    });

    this.mediaRecorder.start(this.timesliceMs);
    return { mimeType: this.mediaRecorder.mimeType };
  }

  /** Resolves with the full recording as a Blob once MediaRecorder has flushed. */
  stop() {
    return new Promise((resolve) => {
      if (!this.mediaRecorder) return resolve(null);
      this.mediaRecorder.addEventListener(
        'stop',
        () => {
          const blob = new Blob(this.chunks, { type: this.mediaRecorder.mimeType });
          this._cleanup();
          resolve(blob);
        },
        { once: true }
      );
      this.mediaRecorder.stop();
    });
  }

  _cleanup() {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.audioCtx?.close();
  }

  getAnalyser() {
    return this.analyser;
  }
}

function pickSupportedMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  return candidates.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported?.(t)) || '';
}

window.VoiceRecorder = VoiceRecorder;
