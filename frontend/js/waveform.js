/**
 * Draws a live amplitude waveform (VU-meter style bars) from a Web Audio
 * AnalyserNode onto a canvas. Falls back to a flat idle line when no
 * analyser is attached (before/after recording).
 */
class WaveformRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.analyser = null;
    this.dataArray = null;
    this._raf = null;
    this._resize();
    window.addEventListener('resize', () => this._resize());
    this._drawIdle();
  }

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * dpr;
    this.canvas.height = 140 * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  attach(analyser) {
    this.analyser = analyser;
    this.dataArray = new Uint8Array(analyser.frequencyBinCount);
    this._loop();
  }

  detach() {
    this.analyser = null;
    cancelAnimationFrame(this._raf);
    this._drawIdle();
  }

  _loop() {
    if (!this.analyser) return;
    this.analyser.getByteTimeDomainData(this.dataArray);
    this._drawBars(this.dataArray);
    this._raf = requestAnimationFrame(() => this._loop());
  }

  _drawBars(data) {
    const w = this.canvas.getBoundingClientRect().width;
    const h = 140;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, w, h);

    const barCount = 64;
    const step = Math.floor(data.length / barCount);
    const barWidth = w / barCount;
    const mid = h / 2;

    for (let i = 0; i < barCount; i++) {
      const sample = data[i * step] / 128 - 1; // -1..1
      const amplitude = Math.max(2, Math.abs(sample) * (h / 2) * 1.4);
      const x = i * barWidth;
      ctx.fillStyle = i % 2 === 0 ? '#F2A93B' : '#E8A752';
      ctx.fillRect(x + 1, mid - amplitude, Math.max(1, barWidth - 2), amplitude * 2);
    }
  }

  _drawIdle() {
    const w = this.canvas.getBoundingClientRect().width || 640;
    const h = 140;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = '#2C3A48';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();
  }
}

window.WaveformRenderer = WaveformRenderer;
