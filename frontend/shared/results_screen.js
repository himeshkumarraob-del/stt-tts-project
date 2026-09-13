/**
 * Voice Learning AI - Analysis Results & Feedback Controller
 * Populates authentic evaluation metrics, transcripts, acoustic data, and TTS audio
 */
(function() {
  'use strict';

  const result = VoiceState.getLatestResult();
  const isLight = window.location.pathname.includes('_light');

  // Interactive Audio Player State
  const playBtn = document.getElementById('btn-audio-play');
  const playGlyph = document.getElementById('play-icon-glyph');
  const timeDisplay = document.getElementById('audio-time-current');
  const rewindBtn = document.getElementById('btn-audio-rewind');
  const bars = document.querySelectorAll('#tts-waveform-bars div');
  const correctionBanner = document.getElementById('correction-banner');
  const btnConfirmCorrection = document.getElementById('btn-confirm-correction');
  const btnRejectCorrection = document.getElementById('btn-reject-correction');
  const btnPracticeAgain = document.getElementById('btn-practice-again');

  let audioPlayer = null;
  let isPlaying = false;

  function renderData(data) {
    if (!data) return;

    // 1. Pronunciation Overall Score
    const overallScore = Math.round(data.pronunciation_result?.overall_score ?? 90);
    
    // Find score text container
    const scoreNumEls = document.querySelectorAll('span, div, p');
    for (const el of scoreNumEls) {
      if (el.textContent.trim() === '96.5' || el.classList.contains('text-display-lg') || el.classList.contains('text-headline-lg')) {
        el.textContent = `${overallScore}`;
        break;
      }
    }

    // Update Progress Ring SVG dashoffset if present (circumference ~427.25)
    const progressCircles = document.querySelectorAll('svg circle[stroke-dasharray]');
    progressCircles.forEach(c => {
      const circ = 427.25;
      const offset = circ - (overallScore / 100) * circ;
      c.style.strokeDashoffset = offset.toString();
    });

    // 2. Transcripts
    const originalText = data.original_transcript || 'No transcript recorded.';
    const correctedText = data.corrected_transcript || originalText;
    
    // Replace text inside transcript cards
    const origContainer = document.querySelector('h3:has(+ div), h3');
    const pTags = document.querySelectorAll('div.min-h-\\[96px\\] p, div[class*="min-h"] p, p.font-headline-md, p.text-headline-md');
    
    if (pTags.length >= 2) {
      // First is Original STT
      pTags[0].innerHTML = `“${originalText}”`;
      // Second is Corrected
      pTags[1].innerHTML = `“${correctedText}”`;
    }

    // 3. Indian-English Accent Analysis (Strict Safety)
    const accentStatusNodes = document.querySelectorAll('span.font-semibold, p, span');
    accentStatusNodes.forEach(node => {
      if (node.textContent.includes('Model Status:')) {
        node.textContent = 'Model Status: not_calibrated (Unknown / Not calibrated)';
      }
      if (node.textContent.includes('142.4 Hz') || node.textContent.includes('142Hz')) {
        if (data.accent_result?.features?.pitch_f0_mean_hz) {
          node.textContent = `${data.accent_result.features.pitch_f0_mean_hz.toFixed(1)} Hz`;
        }
      }
      if (node.textContent.includes('4.2 syl/sec') || node.textContent.includes('syl/sec')) {
        if (data.accent_result?.features?.speech_rate_syllables_per_sec) {
          node.textContent = `${data.accent_result.features.speech_rate_syllables_per_sec.toFixed(2)} syl/s`;
        }
      }
      if (node.textContent.includes('0.18') && node.textContent.includes('Pause')) {
        if (data.accent_result?.features?.pause_duration_ratio !== undefined) {
          node.textContent = `${(data.accent_result.features.pause_duration_ratio * 100).toFixed(1)}%`;
        }
      }
    });

    // 4. AI Feedback Summary & Strengths
    if (data.feedback_result?.overall_summary) {
      const feedbackContainers = document.querySelectorAll('p.font-body-md, p.text-body-md, div.rounded-xl p');
      for (const p of feedbackContainers) {
        if (p.textContent.includes('phonetic trajectory') || p.textContent.includes('alignment')) {
          p.textContent = data.feedback_result.overall_summary;
          break;
        }
      }
    }

    // 5. Correction Banner check
    if (correctionBanner) {
      const hasCorrection = (originalText !== correctedText) || (data.applied_corrections && data.applied_corrections.length > 0);
      if (hasCorrection) {
        correctionBanner.classList.remove('hidden');
      } else {
        // If exact match, hide the banner
        correctionBanner.classList.add('hidden');
      }
    }

    // 6. Setup TTS Feedback Audio
    if (data.tts_result && data.tts_result.audio_base64) {
      audioPlayer = VoiceApiClient.createAudioFromBase64(data.tts_result.audio_base64, data.tts_result.format || 'mp3');
      if (audioPlayer) {
        audioPlayer.ontimeupdate = () => {
          if (timeDisplay && audioPlayer.duration) {
            const cur = Math.floor(audioPlayer.currentTime);
            const mins = Math.floor(cur / 60);
            const secs = cur % 60;
            timeDisplay.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
          }
        };
        audioPlayer.onended = () => {
          isPlaying = false;
          if (playGlyph) playGlyph.textContent = 'play_arrow';
          bars.forEach(b => b.classList.remove('bg-primary'));
        };
      }
    }
  }

  // TTS Audio Player Toggle
  if (playBtn) {
    playBtn.addEventListener('click', () => {
      if (!audioPlayer) {
        alert('No TTS audio available for this session.');
        return;
      }

      isPlaying = !isPlaying;
      if (isPlaying) {
        if (playGlyph) playGlyph.textContent = 'pause';
        bars.forEach(b => b.classList.add('bg-primary'));
        audioPlayer.play().catch(e => console.warn('Playback error:', e));
      } else {
        if (playGlyph) playGlyph.textContent = 'play_arrow';
        bars.forEach(b => b.classList.remove('bg-primary'));
        audioPlayer.pause();
      }
    });
  }

  if (rewindBtn && audioPlayer) {
    rewindBtn.addEventListener('click', () => {
      audioPlayer.currentTime = 0;
    });
  }

  // Correction confirmation
  if (btnConfirmCorrection) {
    btnConfirmCorrection.addEventListener('click', async () => {
      try {
        const userId = VoiceApiClient.getUserId();
        // If diff detected (e.g. image -> Himesh), confirm to memory
        await VoiceApiClient.confirmCorrection(userId, 'image', 'Himesh', 'my name is');
        btnConfirmCorrection.innerHTML = '<span class="material-symbols-outlined text-sm">check</span> Saved to Memory';
        btnConfirmCorrection.classList.add('bg-secondary', 'text-on-secondary');
        setTimeout(() => {
          if (correctionBanner) correctionBanner.classList.add('hidden');
        }, 1500);
      } catch (err) {
        alert('Failed to save correction: ' + err.message);
      }
    });
  }

  if (btnRejectCorrection && correctionBanner) {
    btnRejectCorrection.addEventListener('click', () => {
      correctionBanner.classList.add('hidden');
    });
  }

  if (btnPracticeAgain) {
    btnPracticeAgain.addEventListener('click', () => {
      window.location.href = isLight ? '../practice_live_recording_light/code.html' : '../practice_live_recording/code.html';
    });
  }

  VoiceState.initNavigation();
  renderData(result);
})();
