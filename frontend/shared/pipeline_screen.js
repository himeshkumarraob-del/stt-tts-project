/**
 * Voice Learning AI - Pipeline Analysis Progress Controller
 * Orchestrates live FastAPI execution and updates stages in real-time
 */
(function() {
  'use strict';

  const cancelBtn = document.getElementById('cancel-pipeline-btn');
  const retryBtn = document.getElementById('retry-btn');
  const timerCountdown = document.getElementById('timer-countdown');
  const progressPercent = document.getElementById('progress-percent');
  const masterProgressFill = document.getElementById('master-progress-fill');
  const rawPayloadToggle = document.getElementById('raw-payload-toggle');
  const logViewContainer = document.getElementById('log-view-container');
  const rawJsonContainer = document.getElementById('raw-json-container');

  let timerStartTime = Date.now();
  let timerInterval = null;

  // Toggle raw payload inspector
  if (rawPayloadToggle && logViewContainer && rawJsonContainer) {
    rawPayloadToggle.addEventListener('change', function() {
      if (this.checked) {
        logViewContainer.classList.add('hidden');
        rawJsonContainer.classList.remove('hidden');
      } else {
        logViewContainer.classList.remove('hidden');
        rawJsonContainer.classList.add('hidden');
      }
    });
  }

  function startTimer() {
    timerStartTime = Date.now();
    timerInterval = setInterval(() => {
      const elapsed = ((Date.now() - timerStartTime) / 1000).toFixed(2);
      if (timerCountdown) timerCountdown.textContent = `${elapsed}s`;
    }, 50);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  async function convertDataUrlToBlob(dataUrl) {
    const res = await fetch(dataUrl);
    return await res.blob();
  }

  async function executePipeline() {
    startTimer();
    const isLight = window.location.pathname.includes('_light');
    const targetText = VoiceState.getTargetText();
    const userId = VoiceApiClient.getUserId();
    const audioDataUrl = VoiceState.getAudioDataUrl();

    let audioBlob = null;
    if (audioDataUrl) {
      audioBlob = await convertDataUrlToBlob(audioDataUrl);
    } else {
      // Fallback sample audio if direct navigation occurred
      console.warn('No recorded audio blob found in session storage.');
    }

    if (!audioBlob) {
      if (logViewContainer) {
        logViewContainer.innerHTML = `
          <div class="p-4 rounded-xl bg-error-container/20 border border-error/40 text-on-surface">
            <h4 class="font-bold text-error flex items-center gap-2">
              <span class="material-symbols-outlined">error</span> No Audio Found
            </h4>
            <p class="text-sm mt-1 text-on-surface-variant">Please return to the Practice screen and record your speech.</p>
            <a href="${isLight ? '../practice_live_recording_light/code.html' : '../practice_live_recording/code.html'}" class="inline-block mt-3 px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold">Back to Practice</a>
          </div>
        `;
      }
      stopTimer();
      return;
    }

    // Update progress bar
    if (masterProgressFill) masterProgressFill.style.width = '30%';
    if (progressPercent) progressPercent.textContent = '30%';

    try {
      if (masterProgressFill) masterProgressFill.style.width = '60%';
      if (progressPercent) progressPercent.textContent = '60%';

      const result = await VoiceApiClient.processVoiceLearning(
        audioBlob,
        targetText,
        userId,
        true
      );

      if (masterProgressFill) masterProgressFill.style.width = '100%';
      if (progressPercent) progressPercent.textContent = '100%';
      stopTimer();

      // Store results
      VoiceState.setLatestResult(result);

      // Populate raw json view
      if (rawJsonContainer) {
        const pre = rawJsonContainer.querySelector('pre') || rawJsonContainer;
        pre.textContent = JSON.stringify(result, null, 2);
      }

      // Transition to results screen
      setTimeout(() => {
        const resultsUrl = isLight ? '../analysis_results_feedback_light/code.html' : '../analysis_results_feedback/code.html';
        window.location.href = resultsUrl;
      }, 700);

    } catch (err) {
      stopTimer();
      console.error('Pipeline processing error:', err);
      if (logViewContainer) {
        logViewContainer.innerHTML = `
          <div class="p-4 rounded-xl bg-error-container/20 border border-error/40 text-on-surface">
            <h4 class="font-bold text-error flex items-center gap-2">
              <span class="material-symbols-outlined">warning</span> Analysis Failed
            </h4>
            <p class="text-sm mt-1 text-on-surface-variant">${err.message || 'An error occurred while analyzing speech.'}</p>
            <div class="mt-4 flex gap-3">
              <button id="retry-action-btn" class="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold flex items-center gap-1.5">
                <span class="material-symbols-outlined text-sm">refresh</span> Retry
              </button>
              <a href="${isLight ? '../practice_live_recording_light/code.html' : '../practice_live_recording/code.html'}" class="px-4 py-2 bg-surface-container-high text-on-surface rounded-lg text-sm font-semibold">Back to Practice</a>
            </div>
          </div>
        `;
        const retryAction = document.getElementById('retry-action-btn');
        if (retryAction) retryAction.addEventListener('click', executePipeline);
      }
    }
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      const isLight = window.location.pathname.includes('_light');
      window.location.href = isLight ? '../practice_live_recording_light/code.html' : '../practice_live_recording/code.html';
    });
  }

  if (retryBtn) {
    retryBtn.addEventListener('click', executePipeline);
  }

  VoiceState.initNavigation();
  executePipeline();
})();
