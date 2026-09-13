/**
 * Voice Learning AI - Learned Corrections & Memory History Controller
 * Fetches user memory from backend and supports API Base/User ID configuration
 */
(function() {
  'use strict';

  const openConfigBtn = document.getElementById('open-config-btn');
  const closeConfigBtn = document.getElementById('close-config-btn');
  const cancelConfigBtn = document.getElementById('cancel-config-btn');
  const saveConfigBtn = document.getElementById('save-config-btn');
  const configModal = document.getElementById('config-modal');
  
  const toggleEmptyBtn = document.getElementById('toggle-empty-state-btn');
  const populatedView = document.getElementById('populated-history-view');
  const emptyView = document.getElementById('empty-history-view');
  const refreshMemoryBtn = document.getElementById('refresh-memory-btn');

  const apiBaseInput = document.getElementById('api-base-input');
  const apiUserInput = document.getElementById('api-user-input');

  function openModal() {
    if (configModal) {
      configModal.classList.remove('hidden');
      configModal.classList.add('flex');
    }
    if (apiBaseInput) apiBaseInput.value = VoiceApiClient.getBaseUrl();
    if (apiUserInput) apiUserInput.value = VoiceApiClient.getUserId();
  }

  function closeModal() {
    if (configModal) {
      configModal.classList.add('hidden');
      configModal.classList.remove('flex');
    }
  }

  if (openConfigBtn) openConfigBtn.addEventListener('click', openModal);
  if (closeConfigBtn) closeConfigBtn.addEventListener('click', closeModal);
  if (cancelConfigBtn) cancelConfigBtn.addEventListener('click', closeModal);
  
  if (saveConfigBtn) {
    saveConfigBtn.addEventListener('click', () => {
      if (apiBaseInput) VoiceApiClient.setBaseUrl(apiBaseInput.value.trim());
      if (apiUserInput) VoiceApiClient.setUserId(apiUserInput.value.trim());
      
      saveConfigBtn.innerHTML = '✓ Saved!';
      setTimeout(() => {
        saveConfigBtn.innerHTML = 'Save Changes';
        closeModal();
        loadCorrections();
      }, 600);
    });
  }

  async function loadCorrections() {
    const userId = VoiceApiClient.getUserId();
    try {
      const data = await VoiceApiClient.getUserCorrections(userId);
      if (data && data.corrections && data.corrections.length > 0) {
        if (populatedView) populatedView.classList.remove('hidden');
        if (emptyView) emptyView.classList.add('hidden');
        renderCorrectionList(data.corrections);
      } else {
        if (populatedView) populatedView.classList.add('hidden');
        if (emptyView) emptyView.classList.remove('hidden');
      }
    } catch (err) {
      console.warn('Failed to load user corrections:', err);
      // Keep existing static preview if backend unreachable
    }
  }

  function renderCorrectionList(corrections) {
    if (!populatedView) return;
    const cardsContainer = populatedView.querySelector('.space-y-3, .grid') || populatedView;
    
    // Clear dynamic cards if present
    const dynamicItems = cardsContainer.querySelectorAll('[data-dynamic-correction]');
    dynamicItems.forEach(item => item.remove());

    corrections.forEach(corr => {
      const card = document.createElement('div');
      card.setAttribute('data-dynamic-correction', 'true');
      card.className = 'p-space-md rounded-xl bg-surface-container-low border border-outline-variant/30 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all duration-150 hover:border-primary/40';
      card.innerHTML = `
        <div class="flex items-center gap-space-md">
          <div class="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold">
            ${corr.occurrence_count || 1}x
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="text-error font-mono line-through font-semibold text-sm">"${corr.incorrect_text}"</span>
              <span class="material-symbols-outlined text-xs text-outline">arrow_forward</span>
              <span class="text-secondary font-mono font-bold text-sm">"${corr.correct_text}"</span>
            </div>
            <div class="flex items-center gap-2 mt-1">
              <span class="px-2 py-0.5 rounded-md bg-surface-container-high text-on-surface-variant text-[11px] font-mono">
                Context: "${corr.context_phrase || 'any'}"
              </span>
              <span class="text-[11px] text-outline">Confidence: ${(corr.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 self-end md:self-auto">
          <span class="px-space-sm py-1 rounded-lg bg-secondary-container/30 text-secondary text-xs font-semibold">Active Memory</span>
        </div>
      `;
      cardsContainer.appendChild(card);
    });
  }

  if (refreshMemoryBtn) {
    refreshMemoryBtn.addEventListener('click', loadCorrections);
  }

  if (toggleEmptyBtn) {
    toggleEmptyBtn.addEventListener('click', () => {
      if (populatedView && emptyView) {
        populatedView.classList.toggle('hidden');
        emptyView.classList.toggle('hidden');
      }
    });
  }

  VoiceState.initNavigation();
  loadCorrections();
})();
