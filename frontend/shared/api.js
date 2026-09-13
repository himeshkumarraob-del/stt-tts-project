/**
 * Voice Learning AI - Centralized Backend API Client
 * Connects the Stitch Frontend to the FastAPI Backend (http://127.0.0.1:8000)
 */
(function(window) {
  'use strict';

  const DEFAULT_API_BASE = 'http://127.0.0.1:8000';
  const DEFAULT_USER_ID = 'default_user';

  const ApiClient = {
    getBaseUrl() {
      return localStorage.getItem('voice_ai_api_base') || DEFAULT_API_BASE;
    },

    setBaseUrl(url) {
      if (!url) url = DEFAULT_API_BASE;
      url = url.replace(/\/+$/, '');
      localStorage.setItem('voice_ai_api_base', url);
    },

    getUserId() {
      return localStorage.getItem('voice_ai_user_id') || DEFAULT_USER_ID;
    },

    setUserId(id) {
      if (!id) id = DEFAULT_USER_ID;
      localStorage.setItem('voice_ai_user_id', id.trim());
    },

    /**
     * Check backend health
     */
    async checkHealth() {
      const base = this.getBaseUrl();
      const res = await fetch(`${base}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) throw new Error(`Health check failed with HTTP ${res.status}`);
      return await res.json();
    },

    /**
     * Synthesize speech via Text-to-Speech (TTS)
     * POST /api/v1/tts/synthesize
     */
    async synthesizeTTS(text, voice = 'alloy', format = 'mp3') {
      const base = this.getBaseUrl();
      const res = await fetch(`${base}/api/v1/tts/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          text: text,
          voice: voice,
          audio_format: format
        })
      });

      if (!res.ok) {
        let errDetail = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          errDetail = errJson.detail?.message || errJson.message || JSON.stringify(errJson);
        } catch (_) {}
        throw new Error(`TTS synthesis failed: ${errDetail}`);
      }

      return await res.json();
    },

    /**
     * Execute full 6-phase End-to-End Voice Learning loop
     * POST /api/v1/voice-learning/process
     */
    async processVoiceLearning(audioBlob, targetText, userId, synthesizeTts = true) {
      const base = this.getBaseUrl();
      const formData = new FormData();
      
      const ext = audioBlob.type.includes('wav') ? 'wav' : 'webm';
      const filename = `recording_${Date.now()}.${ext}`;
      
      formData.append('file', audioBlob, filename);
      formData.append('target_text', targetText);
      formData.append('user_id', userId || this.getUserId());
      formData.append('synthesize_tts', synthesizeTts ? 'true' : 'false');

      const res = await fetch(`${base}/api/v1/voice-learning/process`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        let errDetail = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          errDetail = errJson.detail?.message || errJson.message || JSON.stringify(errJson);
        } catch (_) {}
        throw new Error(`Voice learning processing failed: ${errDetail}`);
      }

      return await res.json();
    },

    /**
     * Confirm a user-specific STT correction
     * POST /api/v1/corrections/confirm
     */
    async confirmCorrection(userId, incorrectText, correctText, context = null) {
      const base = this.getBaseUrl();
      const res = await fetch(`${base}/api/v1/corrections/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId || this.getUserId(),
          incorrect_text: incorrectText,
          correct_text: correctText,
          context: context
        })
      });

      if (!res.ok) {
        let errDetail = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          errDetail = errJson.detail?.message || errJson.message || JSON.stringify(errJson);
        } catch (_) {}
        throw new Error(`Correction confirmation failed: ${errDetail}`);
      }

      return await res.json();
    },

    /**
     * Retrieve active corrections for a user
     * GET /api/v1/corrections/{user_id}
     */
    async getUserCorrections(userId) {
      const base = this.getBaseUrl();
      const uid = encodeURIComponent(userId || this.getUserId());
      const res = await fetch(`${base}/api/v1/corrections/${uid}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });

      if (!res.ok) {
        let errDetail = `HTTP ${res.status}`;
        try {
          const errJson = await res.json();
          errDetail = errJson.detail?.message || errJson.message || JSON.stringify(errJson);
        } catch (_) {}
        throw new Error(`Failed to fetch user corrections: ${errDetail}`);
      }

      return await res.json();
    },

    /**
     * Play base64 audio string via HTMLAudioElement
     */
    createAudioFromBase64(base64Str, format = 'mp3') {
      if (!base64Str) return null;
      const audioUrl = `data:audio/${format};base64,${base64Str}`;
      return new Audio(audioUrl);
    }
  };

  window.VoiceApiClient = ApiClient;
})(window);
