(() => {
  const $ = (id) => document.getElementById(id);

  // STT elements
  const recordBtn = $('recordBtn');
  const recIndicator = $('recIndicator');
  const waveformCanvas = $('waveform');
  const transcriptEl = $('transcript');
  const langBadge = $('langBadge');
  const accentBadge = $('accentBadge');
  const codeSwitchBadge = $('codeSwitchBadge');
  const confidenceRow = $('confidenceRow');
  const confidenceMeter = $('confidenceMeter');
  const confidenceValue = $('confidenceValue');
  const keywordsApplied = $('keywordsApplied');
  const statusBanner = $('statusBanner');
  const providerTag = $('providerTag');
  const clearBtn = $('clearBtn');
  const sendToTtsBtn = $('sendToTtsBtn');
  const sttCorrectionBar = $('sttCorrectionBar');
  const saveSttBtn = $('saveSttBtn');
  const discardSttBtn = $('discardSttBtn');
  const sttLearnedList = $('sttLearnedList');
  const sttCount = $('sttCount');
  const sttItems = $('sttItems');
  const clearSttBtn = $('clearSttBtn');

  // TTS elements
  const ttsText = $('ttsText');
  const voiceSelect = $('voiceSelect');
  const rateRange = $('rateRange');
  const pitchRange = $('pitchRange');
  const rateValue = $('rateValue');
  const pitchValue = $('pitchValue');
  const speakBtn = $('speakBtn');
  const downloadBtn = $('downloadBtn');
  const player = $('player');
  const ttsStatus = $('ttsStatus');
  const ttsCorrectionPanel = $('ttsCorrectionPanel');
  const wrongWordInput = $('wrongWord');
  const correctWordInput = $('correctWord');
  const saveTtsBtn = $('saveTtsBtn');
  const ttsLearnedList = $('ttsLearnedList');
  const ttsCount = $('ttsCount');
  const ttsItems = $('ttsItems');
  const clearTtsBtn = $('clearTtsBtn');
  const learnedCount = $('learnedCount');

  // ── State ──────────────────────────────────────────────────────────
  const waveform = new WaveformRenderer(waveformCanvas);
  let recorder = null;
  let socket = null;
  let isRecording = false;
  let lastAudioBlobUrl = null;
  let originalTranscript = '';  // saved before user edits, for diffing
  let transcriptDirty = false;  // true when user has edited after transcription

  // ── Helpers ────────────────────────────────────────────────────────
  function showStatus(el, message, kind = 'error') {
    el.textContent = message;
    el.hidden = false;
    el.className = `status-banner${kind === 'info' ? ' info' : ''}`;
  }
  function hideStatus(el) { el.hidden = true; }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  // ── Health check ───────────────────────────────────────────────────
  fetch('/api/health')
    .then((r) => r.json())
    .then((h) => {
      providerTag.textContent = `STT: ${h.sttProvider} · TTS: ${h.ttsProvider}`;
    })
    .catch(() => { providerTag.textContent = 'backend offline'; });

  // ── Load existing corrections from backend ─────────────────────────
  async function refreshStats() {
    try {
      const res = await fetch('/api/feedback/all');
      const data = await res.json();
      const total = (data.stt?.count || 0) + (data.tts?.count || 0);
      learnedCount.textContent = total;
      renderSttList(data.stt?.history || [], data.stt?.corrections || {});
      renderTtsList(data.tts?.history || [], data.tts?.substitutions || {});
    } catch { /* silently ignore */ }
  }
  refreshStats();

  // ── Transcript rendering ───────────────────────────────────────────
  function renderTranscript(words, fallbackText) {
    if (!words || !words.length) {
      transcriptEl.textContent = fallbackText || '';
      return;
    }
    transcriptEl.innerHTML = words
      .map((w) => {
        const cls = w.uncertain ? ' class="uncertain"' : '';
        const title = w.uncertain ? ' title="Low confidence — check this word"' : '';
        return `<span${cls}${title}>${escapeHtml(w.text)}</span>`;
      })
      .join(' ');
  }

  function updateBadges({ detectedLanguage, accent, codeSwitch }) {
    if (detectedLanguage) {
      langBadge.textContent = `Language: ${detectedLanguage}`;
      langBadge.classList.replace('badge-muted', 'badge-active');
    }
    if (accent?.guessedInfluence) {
      const pct = Math.round((accent.guessConfidence || 0) * 100);
      accentBadge.textContent = `Accent: ${accent.guessedInfluence} (~${pct}%)`;
      accentBadge.classList.replace('badge-muted', 'badge-active');
    }
    if (codeSwitch?.codeSwitchDetected) {
      codeSwitchBadge.hidden = false;
      const langs = codeSwitch.likelyLanguages.map((l) => l.language).join(', ');
      codeSwitchBadge.textContent = `Code-switch: ${langs}`;
      codeSwitchBadge.classList.add('badge-warn');
    } else {
      codeSwitchBadge.hidden = true;
    }
  }

  function updateConfidence(value, kwCount) {
    confidenceRow.hidden = false;
    confidenceMeter.value = value;
    confidenceValue.textContent = `${Math.round(value * 100)}%`;
    if (kwCount > 0) {
      keywordsApplied.textContent = `+${kwCount} learned keywords`;
      keywordsApplied.hidden = false;
    } else {
      keywordsApplied.hidden = true;
    }
  }

  // ── STT correction detection ───────────────────────────────────────
  // Watch for user edits to the transcript after transcription
  transcriptEl.addEventListener('input', () => {
    if (!originalTranscript) return; // nothing transcribed yet
    const current = transcriptEl.innerText.trim();
    const isDifferent = current !== originalTranscript;
    if (isDifferent && !transcriptDirty) {
      transcriptDirty = true;
      sttCorrectionBar.hidden = false;
    } else if (!isDifferent) {
      transcriptDirty = false;
      sttCorrectionBar.hidden = true;
    }
  });

  saveSttBtn.addEventListener('click', async () => {
    const corrected = transcriptEl.innerText.trim();
    if (!corrected || !originalTranscript) return;

    saveSttBtn.disabled = true;
    saveSttBtn.textContent = 'Saving…';
    try {
      const res = await fetch('/api/feedback/stt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ original: originalTranscript, corrected }),
      });
      const json = await res.json();
      originalTranscript = corrected; // update baseline
      transcriptDirty = false;
      sttCorrectionBar.hidden = true;
      saveSttBtn.textContent = `Saved ${json.learned?.length || 0} correction(s) ✓`;
      setTimeout(() => { saveSttBtn.textContent = 'Save corrections'; saveSttBtn.disabled = false; }, 2000);
      await refreshStats();
    } catch {
      saveSttBtn.textContent = 'Save corrections';
      saveSttBtn.disabled = false;
    }
  });

  discardSttBtn.addEventListener('click', () => {
    // Revert transcript to original
    transcriptEl.innerText = originalTranscript;
    transcriptDirty = false;
    sttCorrectionBar.hidden = true;
  });

  // ── STT corrections list rendering ────────────────────────────────
  function renderSttList(history, corrections) {
    const entries = Object.entries(corrections);
    if (!entries.length) { sttLearnedList.hidden = true; return; }
    sttLearnedList.hidden = false;
    sttCount.textContent = entries.length;
    sttItems.innerHTML = entries.map(([from, to]) => `
      <li class="correction-chip">
        <span class="from">${escapeHtml(from)}</span>
        <span class="arrow">→</span>
        <span class="to">${escapeHtml(to)}</span>
        <button onclick="deleteSttCorrection('${escapeHtml(from)}')" title="Remove">✕</button>
      </li>
    `).join('');
  }

  window.deleteSttCorrection = async (word) => {
    await fetch(`/api/feedback/stt/${encodeURIComponent(word)}`, { method: 'DELETE' });
    await refreshStats();
  };

  clearSttBtn.addEventListener('click', async () => {
    if (!confirm('Remove all STT corrections?')) return;
    const data = await fetch('/api/feedback/all').then(r => r.json());
    const words = Object.keys(data.stt?.corrections || {});
    await Promise.all(words.map(w => fetch(`/api/feedback/stt/${encodeURIComponent(w)}`, { method: 'DELETE' })));
    await refreshStats();
  });

  // ── Recording ──────────────────────────────────────────────────────
  recordBtn.addEventListener('click', async () => {
    if (isRecording) await stopRecording();
    else await startRecording();
  });

  async function startRecording() {
    hideStatus(statusBanner);
    try {
      recorder = new VoiceRecorder({ onChunk: handleChunk });
      const { mimeType } = await recorder.start();
      waveform.attach(recorder.getAnalyser());

      isRecording = true;
      recordBtn.setAttribute('aria-pressed', 'true');
      recordBtn.querySelector('.label').textContent = 'Stop';
      recIndicator.hidden = false;
      transcriptEl.innerHTML = '';
      originalTranscript = '';
      transcriptDirty = false;
      sttCorrectionBar.hidden = true;
      langBadge.textContent = 'Language: —';
      accentBadge.textContent = 'Accent: —';
      langBadge.className = 'badge badge-muted';
      accentBadge.className = 'badge badge-muted';
      codeSwitchBadge.hidden = true;

      openStreamingSocket(mimeType);
    } catch (err) {
      const message = err.name === 'NotAllowedError'
        ? 'Microphone access was denied. Allow it in browser settings and try again.'
        : 'Could not start recording on this device/browser.';
      showStatus(statusBanner, message);
    }
  }

  async function stopRecording() {
    isRecording = false;
    recordBtn.setAttribute('aria-pressed', 'false');
    recordBtn.querySelector('.label').textContent = 'Record';
    recIndicator.hidden = true;
    waveform.detach();
    const blob = await recorder.stop();
    closeStreamingSocket();
    if (blob && blob.size > 0) await finalizeTranscription(blob);
  }

  // ── WebSocket streaming ────────────────────────────────────────────
  function openStreamingSocket(mimeType) {
    try {
      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      socket = new WebSocket(`${protocol}://${location.host}/ws/transcribe`);
      socket.binaryType = 'arraybuffer';
      socket.addEventListener('open', () => {
        socket.send(JSON.stringify({ type: 'start', mimeType }));
      });
      socket.addEventListener('message', (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'transcript') {
          renderTranscript(msg.words, msg.text);
          updateBadges(msg);
        }
      });
      socket.addEventListener('error', () => {
        console.warn('Live streaming unavailable — falling back to finalize-on-stop only.');
      });
    } catch { socket = null; }
  }

  function handleChunk(arrayBuffer) {
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(arrayBuffer);
  }

  function closeStreamingSocket() {
    if (socket) {
      try { socket.send(JSON.stringify({ type: 'stop' })); } catch { /* closing */ }
      socket.close(); socket = null;
    }
  }

  // ── Batch finalize ─────────────────────────────────────────────────
  async function finalizeTranscription(blob) {
    showStatus(statusBanner, 'Finalizing transcript…', 'info');
    const form = new FormData();
    form.append('audio', blob, 'recording.webm');

    try {
      const res = await fetch('/api/transcribe', { method: 'POST', body: form });
      const json = await res.json();
      if (!res.ok) throw new Error(json.message || 'Transcription failed.');

      renderTranscript(json.words, json.text);
      updateBadges(json);
      updateConfidence(json.confidence, json.keywordsApplied || 0);
      hideStatus(statusBanner);

      // Save the clean server-corrected text as the baseline for diffing
      originalTranscript = json.text;
      transcriptDirty = false;
      sttCorrectionBar.hidden = true;
    } catch (err) {
      showStatus(statusBanner, err.message || 'Could not reach the transcription service.');
    }
  }

  clearBtn.addEventListener('click', () => {
    transcriptEl.innerHTML = '';
    originalTranscript = '';
    transcriptDirty = false;
    sttCorrectionBar.hidden = true;
    confidenceRow.hidden = true;
    langBadge.textContent = 'Language: —';
    accentBadge.textContent = 'Accent: —';
    langBadge.className = 'badge badge-muted';
    accentBadge.className = 'badge badge-muted';
    codeSwitchBadge.hidden = true;
  });

  sendToTtsBtn.addEventListener('click', () => {
    ttsText.value = transcriptEl.innerText.trim();
    ttsText.focus();
  });

  // ── TTS ────────────────────────────────────────────────────────────
  async function loadVoices() {
    try {
      const res = await fetch('/api/tts/voices');
      const json = await res.json();
      voiceSelect.innerHTML = (json.voices || [])
        .map((v) => `<option value="${escapeHtml(v.id)}">${escapeHtml(v.label)}</option>`)
        .join('');
    } catch {
      voiceSelect.innerHTML = '<option value="">Voice list unavailable</option>';
    }
  }
  loadVoices();

  rateRange.addEventListener('input', () => {
    rateValue.textContent = `${Number(rateRange.value).toFixed(2)}×`;
  });
  pitchRange.addEventListener('input', () => {
    pitchValue.textContent = `${pitchRange.value} st`;
  });

  speakBtn.addEventListener('click', async () => {
    const text = ttsText.value.trim();
    if (!text) { showStatus(ttsStatus, 'Type some text first.'); return; }
    hideStatus(ttsStatus);
    speakBtn.disabled = true;
    speakBtn.querySelector('.icon').textContent = '⏳';
    ttsCorrectionPanel.hidden = true;

    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          voiceId: voiceSelect.value,
          rate: rateRange.value,
          pitch: pitchRange.value,
        }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.message || 'Speech synthesis failed.');
      }
      const blob = await res.blob();
      if (lastAudioBlobUrl) URL.revokeObjectURL(lastAudioBlobUrl);
      lastAudioBlobUrl = URL.createObjectURL(blob);
      player.src = lastAudioBlobUrl;
      player.hidden = false;
      await player.play();
      downloadBtn.disabled = false;

      // Show pronunciation correction panel after playback
      ttsCorrectionPanel.hidden = false;
      wrongWordInput.value = '';
      correctWordInput.value = '';

    } catch (err) {
      showStatus(ttsStatus, err.message);
    } finally {
      speakBtn.disabled = false;
      speakBtn.querySelector('.icon').textContent = '🔊';
    }
  });

  downloadBtn.addEventListener('click', () => {
    if (!lastAudioBlobUrl) return;
    const a = document.createElement('a');
    a.href = lastAudioBlobUrl;
    a.download = 'speech.mp3';
    a.click();
  });

  // ── TTS pronunciation fix ──────────────────────────────────────────
  saveTtsBtn.addEventListener('click', async () => {
    const word = wrongWordInput.value.trim();
    const substitute = correctWordInput.value.trim();
    if (!word || !substitute) {
      showStatus(ttsStatus, 'Fill in both the word and how it should be said.');
      return;
    }
    hideStatus(ttsStatus);
    saveTtsBtn.disabled = true;
    saveTtsBtn.textContent = 'Saving…';

    try {
      await fetch('/api/feedback/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word, substitute }),
      });
      saveTtsBtn.textContent = 'Saved ✓';
      wrongWordInput.value = '';
      correctWordInput.value = '';
      setTimeout(() => {
        saveTtsBtn.textContent = 'Save pronunciation fix';
        saveTtsBtn.disabled = false;
      }, 2000);
      await refreshStats();
      showStatus(ttsStatus, `"${word}" will now be spoken as "${substitute}" — click Speak again to hear it.`, 'info');
    } catch {
      saveTtsBtn.textContent = 'Save pronunciation fix';
      saveTtsBtn.disabled = false;
    }
  });

  // ── TTS corrections list ───────────────────────────────────────────
  function renderTtsList(history, substitutions) {
    const entries = Object.entries(substitutions);
    if (!entries.length) { ttsLearnedList.hidden = true; return; }
    ttsLearnedList.hidden = false;
    ttsCount.textContent = entries.length;
    ttsItems.innerHTML = entries.map(([from, to]) => `
      <li class="correction-chip">
        <span class="from">${escapeHtml(from)}</span>
        <span class="arrow">→</span>
        <span class="to">${escapeHtml(to)}</span>
        <button onclick="deleteTtsCorrection('${escapeHtml(from)}')" title="Remove">✕</button>
      </li>
    `).join('');
  }

  window.deleteTtsCorrection = async (word) => {
    await fetch(`/api/feedback/tts/${encodeURIComponent(word)}`, { method: 'DELETE' });
    await refreshStats();
  };

  clearTtsBtn.addEventListener('click', async () => {
    if (!confirm('Remove all TTS pronunciation fixes?')) return;
    const data = await fetch('/api/feedback/all').then(r => r.json());
    const words = Object.keys(data.tts?.substitutions || {});
    await Promise.all(words.map(w => fetch(`/api/feedback/tts/${encodeURIComponent(w)}`, { method: 'DELETE' })));
    await refreshStats();
  });

})();
