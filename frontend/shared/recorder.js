/**
 * Voice Learning AI - Real Browser Microphone Audio Recorder
 * Uses Web Audio API & MediaRecorder for high-fidelity audio capture
 */
(function(window) {
  'use strict';

  class AudioRecorder {
    constructor() {
      this.mediaStream = null;
      this.mediaRecorder = null;
      this.audioChunks = [];
      this.audioBlob = null;
      this.audioUrl = null;
      this.audioContext = null;
      this.analyser = null;
      this.sourceNode = null;
      this.animationFrameId = null;
      this.onVolumeCallback = null;
      this.isRecording = false;
      this.startTime = 0;
      this.timerInterval = null;
      this.onTimerTick = null;
    }

    /**
     * Request microphone permission & initialize stream
     */
    async initialize() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Your browser does not support microphone audio capture.');
      }

      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      return true;
    }

    /**
     * Start live recording
     */
    async startRecording(onTimerTick = null, onVolume = null) {
      if (!this.mediaStream) {
        await this.initialize();
      }

      this.audioChunks = [];
      this.audioBlob = null;
      if (this.audioUrl) {
        URL.revokeObjectURL(this.audioUrl);
        this.audioUrl = null;
      }

      // Determine best supported mime type
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/wav'
      ];
      let selectedMime = '';
      for (const m of mimeTypes) {
        if (MediaRecorder.isTypeSupported(m)) {
          selectedMime = m;
          break;
        }
      }

      const options = selectedMime ? { mimeType: selectedMime } : {};
      this.mediaRecorder = new MediaRecorder(this.mediaStream, options);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      // Setup Web Audio Analyser for live volume/waveform
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          this.audioContext = new AudioCtx();
          this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
          this.analyser = this.audioContext.createAnalyser();
          this.analyser.fftSize = 64;
          this.sourceNode.connect(this.analyser);

          const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
          const checkVolume = () => {
            if (!this.isRecording) return;
            this.analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length; // 0 to 255
            const norm = Math.min(1.0, avg / 128.0);
            if (this.onVolumeCallback) {
              this.onVolumeCallback(norm, dataArray);
            }
            this.animationFrameId = requestAnimationFrame(checkVolume);
          };
          this.onVolumeCallback = onVolume;
          this.animationFrameId = requestAnimationFrame(checkVolume);
        }
      } catch (err) {
        console.warn('Analyser setup non-fatal error:', err);
      }

      this.isRecording = true;
      this.startTime = Date.now();
      this.onTimerTick = onTimerTick;

      if (this.onTimerTick) {
        this.timerInterval = setInterval(() => {
          const elapsedSec = (Date.now() - this.startTime) / 1000;
          this.onTimerTick(elapsedSec);
        }, 100);
      }

      this.mediaRecorder.start(100); // 100ms slices
      return true;
    }

    /**
     * Stop recording and resolve the captured audio Blob
     */
    stopRecording() {
      return new Promise((resolve) => {
        if (!this.isRecording || !this.mediaRecorder) {
          resolve(this.audioBlob);
          return;
        }

        this.isRecording = false;
        if (this.timerInterval) {
          clearInterval(this.timerInterval);
          this.timerInterval = null;
        }
        if (this.animationFrameId) {
          cancelAnimationFrame(this.animationFrameId);
          this.animationFrameId = null;
        }
        if (this.audioContext && this.audioContext.state !== 'closed') {
          this.audioContext.close().catch(() => {});
        }

        this.mediaRecorder.onstop = () => {
          const mime = this.mediaRecorder.mimeType || 'audio/webm';
          this.audioBlob = new Blob(this.audioChunks, { type: mime });
          this.audioUrl = URL.createObjectURL(this.audioBlob);
          resolve(this.audioBlob);
        };

        this.mediaRecorder.stop();
      });
    }

    /**
     * Release microphone stream
     */
    cleanup() {
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }
      if (this.audioUrl) {
        URL.revokeObjectURL(this.audioUrl);
        this.audioUrl = null;
      }
    }
  }

  window.VoiceAudioRecorder = AudioRecorder;
})(window);
