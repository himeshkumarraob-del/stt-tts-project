/**
 * Voice Learning AI - Practice & Live Recording Screen Controller
 */
(function() {
  'use strict';

  const recorder = new VoiceAudioRecorder();
  let recordedAudioBlob = null;
  let previewAudio = null;
  let isTtsPlaying = false;
  let ttsAudio = null;

  // DOM Elements
  const activePromptText = document.getElementById('activePromptText');
  const promptSelector = document.getElementById('promptSelector');
  const ttsPlayBtn = document.getElementById('ttsPlayBtn');
  const ttsIcon = document.getElementById('ttsIcon');
  const ttsWave = document.getElementById('ttsWave');
  
  const stateBadge = document.getElementById('stateBadge');
  const stateDot = document.getElementById('stateDot');
  const stateText = document.getElementById('stateText');
  const timerDisplay = document.getElementById('recordingTimer');
  
  const masterRecordBtn = document.getElementById('masterRecordBtn');
  const micGlyph = document.getElementById('micGlyph');
  const micActionHint = document.getElementById('micActionHint');
  const pulseRingOuter = document.getElementById('pulseRingOuter');
  const pulseRingInner = document.getElementById('pulseRingInner');
  const ambientGlow = document.getElementById('ambientGlow');
  const waveformContainer = document.getElementById('waveformContainer');

  const btnStartRecord = document.getElementById('btnStartRecord');
  const btnStopRecord = document.getElementById('btnStopRecord');
  const btnPlayRecord = document.getElementById('btnPlayRecord');
  const btnRerecord = document.getElementById('btnRerecord');
  const quickSubmitBtn = document.getElementById('quickSubmitBtn');

  // Steps
  const stepIdle = document.getElementById('stepIdle');
  const stepRecording = document.getElementById('stepRecording');
  const stepRecorded = document.getElementById('stepRecorded');
  const stepAnalyzing = document.getElementById('stepAnalyzing');
  const stepComplete = document.getElementById('stepComplete');

  const PROMPT_PRESETS = {
    'jfk': 'And so my fellow Americans ask not what your country can do for you ask what you can do for your country',
    'himesh': 'My name is Himesh, and I am tuning neural speech.',
    'fox': 'The quick brown fox jumps over the lazy dog.',
    'tech': 'Acoustic neural architectures capture subtle formants.'
  };

  function updateState(state) {
    if (stateBadge) {
      if (state === 'RECORDING') {
        stateBadge.className = 'px-space-sm py-0.5 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm flex items-center gap-1.5 animate-pulse';
        if (stateDot) stateDot.className = 'w-1.5 h-1.5 rounded-full bg-error';
        if (stateText) stateText.textContent = 'RECORDING LIVE';
      } else if (state === 'RECORDED') {
        stateBadge.className = 'px-space-sm py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm flex items-center gap-1.5';
        if (stateDot) stateDot.className = 'w-1.5 h-1.5 rounded-full bg-secondary';
        if (stateText) stateText.textContent = 'AUDIO CAPTURED';
      } else if (state === 'ANALYZING') {
        stateBadge.className = 'px-space-sm py-0.5 rounded-full bg-tertiary-container text-on-tertiary-container font-label-sm text-label-sm flex items-center gap-1.5 animate-pulse';
        if (stateDot) stateDot.className = 'w-1.5 h-1.5 rounded-full bg-tertiary';
        if (stateText) stateText.textContent = 'PROCESSING';
      } else {
        stateBadge.className = 'px-space-sm py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm flex items-center gap-1.5';
        if (stateDot) stateDot.className = 'w-1.5 h-1.5 rounded-full bg-outline';
        if (stateText) stateText.textContent = 'STANDBY / IDLE';
      }
    }

    if (btnStartRecord) btnStartRecord.disabled = (state === 'RECORDING');
    if (btnStopRecord) btnStopRecord.disabled = (state !== 'RECORDING');
    if (btnPlayRecord) btnPlayRecord.disabled = (state !== 'RECORDED');
    if (quickSubmitBtn) quickSubmitBtn.disabled = (state !== 'RECORDED');

    if (stepIdle) stepIdle.className = state === 'IDLE' ? 'p-space-sm rounded-lg bg-surface-container-high/40 border border-primary/40' : 'p-space-sm rounded-lg bg-surface-container-low opacity-60';
    if (stepRecording) stepRecording.className = state === 'RECORDING' ? 'p-space-sm rounded-lg bg-error-container/20 border border-error/40 animate-pulse' : 'p-space-sm rounded-lg bg-surface-container-low opacity-60';
    if (stepRecorded) stepRecorded.className = state === 'RECORDED' ? 'p-space-sm rounded-lg bg-secondary-container/20 border border-secondary/40' : 'p-space-sm rounded-lg bg-surface-container-low opacity-60';
    if (stepAnalyzing) stepAnalyzing.className = state === 'ANALYZING' ? 'p-space-sm rounded-lg bg-tertiary-container/20 border border-tertiary/40' : 'p-space-sm rounded-lg bg-surface-container-low opacity-60';
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  // Target sentence prompt switching
  if (promptSelector) {
    promptSelector.addEventListener('change', () => {
      const selectedKey = promptSelector.value;
      const text = PROMPT_PRESETS[selectedKey] || PROMPT_PRESETS['jfk'];
      if (activePromptText) activePromptText.textContent = `“${text}”`;
      VoiceState.setTargetText(text);
    });
  }

  // Preset Buttons (Prompt 1, 2, 3)
  const presetButtons = document.querySelectorAll('button[data-prompt-key]');
  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.getAttribute('data-prompt-key');
      if (PROMPT_PRESETS[key]) {
        if (promptSelector) promptSelector.value = key;
        if (activePromptText) activePromptText.textContent = `“${PROMPT_PRESETS[key]}”`;
        VoiceState.setTargetText(PROMPT_PRESETS[key]);
      }
    });
  });

  // Native Reference TTS button
  if (ttsPlayBtn) {
    ttsPlayBtn.addEventListener('click', async () => {
      if (isTtsPlaying && ttsAudio) {
        ttsAudio.pause();
        ttsAudio = null;
        isTtsPlaying = false;
        if (ttsIcon) ttsIcon.textContent = 'volume_up';
        if (ttsWave) ttsWave.classList.add('hidden');
        return;
      }

      const text = VoiceState.getTargetText();
      if (ttsIcon) ttsIcon.textContent = 'hourglass_empty';
      try {
        const ttsRes = await VoiceApiClient.synthesizeTTS(text, 'alloy', 'mp3');
        if (ttsRes && ttsRes.audio_base64) {
          isTtsPlaying = true;
          if (ttsIcon) ttsIcon.textContent = 'stop';
          if (ttsWave) ttsWave.classList.remove('hidden');
          
          ttsAudio = VoiceApiClient.createAudioFromBase64(ttsRes.audio_base64, ttsRes.format || 'mp3');
          ttsAudio.onended = () => {
            isTtsPlaying = false;
            ttsAudio = null;
            if (ttsIcon) ttsIcon.textContent = 'volume_up';
            if (ttsWave) ttsWave.classList.add('hidden');
          };
          ttsAudio.play();
        }
      } catch (err) {
        console.warn('TTS preview failed:', err);
        if (ttsIcon) ttsIcon.textContent = 'volume_up';
        if (ttsWave) ttsWave.classList.add('hidden');
      }
    });
  }

  // Start recording
  async function startRecordingFlow() {
    try {
      updateState('RECORDING');
      if (micActionHint) micActionHint.textContent = 'Tap to Finish Capture';
      if (micGlyph) micGlyph.textContent = 'stop';
      if (pulseRingOuter) pulseRingOuter.classList.remove('opacity-0');
      if (pulseRingInner) pulseRingInner.classList.remove('opacity-0');
      if (ambientGlow) ambientGlow.className = 'absolute -inset-8 bg-error/30 rounded-full blur-2xl transition-all duration-300 pointer-events-none opacity-80';

      const waveformBars = waveformContainer ? waveformContainer.querySelectorAll('div') : [];

      await recorder.startRecording(
        (elapsedSec) => {
          if (timerDisplay) timerDisplay.textContent = formatTime(elapsedSec);
        },
        (normVol, freqData) => {
          // Animate waveform bars to real microphone audio
          if (waveformBars.length > 0 && freqData) {
            const step = Math.floor(freqData.length / waveformBars.length) || 1;
            waveformBars.forEach((bar, idx) => {
              const val = freqData[idx * step] || 0;
              const heightPct = Math.max(10, Math.min(100, (val / 255) * 100));
              bar.style.height = `${heightPct}%`;
              if (heightPct > 40) {
                bar.className = 'w-1.5 bg-error rounded-full transition-all duration-75';
              } else {
                bar.className = 'w-1.5 bg-primary rounded-full transition-all duration-75';
              }
            });
          }
        }
      );
    } catch (err) {
      alert('Microphone Access Notice: ' + (err.message || 'Could not access microphone. Please allow audio access.'));
      updateState('IDLE');
      if (micGlyph) micGlyph.textContent = 'mic';
      if (micActionHint) micActionHint.textContent = 'Tap to Speak Target Sentence';
    }
  }

  // Stop recording
  async function stopRecordingFlow() {
    recordedAudioBlob = await recorder.stopRecording();
    updateState('RECORDED');
    if (micActionHint) micActionHint.textContent = 'Ready to Analyze';
    if (micGlyph) micGlyph.textContent = 'check';
    if (pulseRingOuter) pulseRingOuter.classList.add('opacity-0');
    if (pulseRingInner) pulseRingInner.classList.add('opacity-0');
    if (ambientGlow) ambientGlow.className = 'absolute -inset-8 bg-secondary/30 rounded-full blur-2xl transition-all duration-300 pointer-events-none opacity-50';

    if (recordedAudioBlob) {
      await VoiceState.saveAudioBlob(recordedAudioBlob);
    }
  }

  // Master Record Button Click
  if (masterRecordBtn) {
    masterRecordBtn.addEventListener('click', async () => {
      if (recorder.isRecording) {
        await stopRecordingFlow();
      } else {
        await startRecordingFlow();
      }
    });
  }

  if (btnStartRecord) btnStartRecord.addEventListener('click', startRecordingFlow);
  if (btnStopRecord) btnStopRecord.addEventListener('click', stopRecordingFlow);

  // Playback Preview
  if (btnPlayRecord) {
    btnPlayRecord.addEventListener('click', () => {
      if (recorder.audioUrl || VoiceState.getAudioDataUrl()) {
        const audioSrc = recorder.audioUrl || VoiceState.getAudioDataUrl();
        if (previewAudio) {
          previewAudio.pause();
          previewAudio = null;
        }
        previewAudio = new Audio(audioSrc);
        previewAudio.play();
      }
    });
  }

  // Re-record
  if (btnRerecord) {
    btnRerecord.addEventListener('click', () => {
      recorder.cleanup();
      recordedAudioBlob = null;
      if (timerDisplay) timerDisplay.textContent = '00:00';
      if (micGlyph) micGlyph.textContent = 'mic';
      if (micActionHint) micActionHint.textContent = 'Tap to Speak Target Sentence';
      updateState('IDLE');
    });
  }

  // Submit flow -> Transition to Pipeline Progress Screen
  if (quickSubmitBtn) {
    quickSubmitBtn.addEventListener('click', async () => {
      if (!recordedAudioBlob && !VoiceState.getAudioDataUrl()) {
        alert('Please record your speech before submitting for analysis.');
        return;
      }
      
      updateState('ANALYZING');
      const isLight = window.location.pathname.includes('_light');
      const pipelineUrl = isLight ? '../pipeline_analysis_progress_light/code.html' : '../pipeline_analysis_progress/code.html';
      window.location.href = pipelineUrl;
    });
  }

  // Initialize
  VoiceState.initNavigation();
  updateState('IDLE');
  VoiceState.setTargetText(PROMPT_PRESETS['jfk']);
})();
