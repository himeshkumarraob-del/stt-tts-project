/**
 * Voice Learning AI - Shared State & Navigation Helper
 */
(function(window) {
  'use strict';

  const STORAGE_KEYS = {
    LATEST_RESULT: 'voice_ai_latest_result',
    TARGET_TEXT: 'voice_ai_target_text',
    AUDIO_DATA_URL: 'voice_ai_audio_data_url'
  };

  const VoiceState = {
    setLatestResult(result) {
      try {
        sessionStorage.setItem(STORAGE_KEYS.LATEST_RESULT, JSON.stringify(result));
      } catch (e) {
        console.warn('Failed to save latest result to sessionStorage:', e);
      }
    },

    getLatestResult() {
      try {
        const raw = sessionStorage.getItem(STORAGE_KEYS.LATEST_RESULT);
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        return null;
      }
    },

    setTargetText(text) {
      sessionStorage.setItem(STORAGE_KEYS.TARGET_TEXT, text || '');
    },

    getTargetText() {
      return sessionStorage.getItem(STORAGE_KEYS.TARGET_TEXT) || 'And so my fellow Americans ask not what your country can do for you ask what you can do for your country';
    },

    async saveAudioBlob(blob) {
      return new Promise((resolve) => {
        if (!blob) {
          sessionStorage.removeItem(STORAGE_KEYS.AUDIO_DATA_URL);
          resolve(null);
          return;
        }
        const reader = new FileReader();
        reader.onloadend = () => {
          try {
            sessionStorage.setItem(STORAGE_KEYS.AUDIO_DATA_URL, reader.result);
          } catch (e) {
            console.warn('Audio data URL too large for sessionStorage:', e);
          }
          resolve(reader.result);
        };
        reader.readAsDataURL(blob);
      });
    },

    getAudioDataUrl() {
      return sessionStorage.getItem(STORAGE_KEYS.AUDIO_DATA_URL) || null;
    },

    /**
     * Wire standard navigation links in sidebar / headers across all screens
     */
    initNavigation() {
      const isLight = window.location.pathname.includes('_light');
      const getHrefForPath = (target) => {
        if (target === 'practice-&-record' || target === 'practice') {
          return isLight ? '../practice_live_recording_light/code.html' : '../practice_live_recording/code.html';
        } else if (target === 'analysis-&-results' || target === 'results') {
          return isLight ? '../analysis_results_feedback_light/code.html' : '../analysis_results_feedback/code.html';
        } else if (target === 'learned-corrections' || target === 'corrections') {
          return isLight ? '../learned_corrections_history_light/code.html' : '../learned_corrections_history/code.html';
        } else if (target === 'pipeline-progress' || target === 'pipeline') {
          return isLight ? '../pipeline_analysis_progress_light/code.html' : '../pipeline_analysis_progress/code.html';
        } else if (target === 'session-history') {
          return isLight ? '../learned_corrections_history_light/code.html' : '../learned_corrections_history/code.html';
        }
        return null;
      };

      const navLinks = document.querySelectorAll('nav a[data-path], header a[data-path], a[data-path]');
      navLinks.forEach(link => {
        const target = link.getAttribute('data-path');
        const href = getHrefForPath(target);
        if (href) {
          link.setAttribute('href', href);
          link.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = href;
          });
        }
      });
    }
  };

  window.VoiceState = VoiceState;
})(window);
