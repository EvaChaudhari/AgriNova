/**
 * Krishi Mitra (AgriNova) - Main Application Controller
 * Manages tabs, state synchronization, dashboard metrics, and vernacular re-rendering
 */

class AppController {
  constructor() {
    this.currentTab = 'dashboard';
    this.deviceId = localStorage.getItem('agrinova_device_id') || window.CONFIG?.DEFAULT_DEVICE_ID;
    this.currentLanguage = localStorage.getItem('agrinova_lang') || window.CONFIG?.DEFAULT_LANGUAGE || 'hi';
    this.activeData = null;
    this.plots = [];
    this.mapInstance = null;
    this.chatInstance = null;
    this.chartInstance = null;

    this.init();
  }

  async init() {
    this.bindNavigation();
    this.bindLanguageSelector();
    this.bindDeviceControls();
    this.bindOnboardingModal();
    this.bindQuickPrompts();
    this.bindSimulateHazardBtn();

    // Check backend health & sync bootstrap
    await this.syncData();

    // Initialize Map and Chat
    this.initMap();
    this.initChat();

    // Render initial language
    this.applyLanguage(this.currentLanguage);
  }

  bindNavigation() {
    const navButtons = document.querySelectorAll('[data-tab-target]');
    navButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-tab-target');
        this.switchTab(target);
      });
    });
  }

  switchTab(tabId) {
    this.currentTab = tabId;

    // Toggle nav active classes
    document.querySelectorAll('[data-tab-target]').forEach(b => {
      const active = b.getAttribute('data-tab-target') === tabId;
      if (active) {
        b.classList.add('bg-emerald-700', 'text-white', 'shadow-sm');
        b.classList.remove('text-slate-600', 'hover:bg-slate-100');
      } else {
        b.classList.remove('bg-emerald-700', 'text-white', 'shadow-sm');
        b.classList.add('text-slate-600', 'hover:bg-slate-100');
      }
    });

    // Toggle tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
      if (panel.id === `tab-${tabId}`) {
        panel.classList.remove('hidden');
      } else {
        panel.classList.add('hidden');
      }
    });

    // Invalidate map size if map tab opened
    if (tabId === 'map' && this.mapInstance) {
      this.mapInstance.resize();
    }
  }

  bindLanguageSelector() {
    const langSelect = document.getElementById('language-selector');
    if (!langSelect) return;

    langSelect.value = this.currentLanguage;
    langSelect.addEventListener('change', (e) => {
      const newLang = e.target.value;
      this.applyLanguage(newLang);
    });
  }

  applyLanguage(lang) {
    this.currentLanguage = lang;
    localStorage.setItem('agrinova_lang', lang);

    const trans = window.CONFIG?.TRANSLATIONS[lang] || window.CONFIG?.TRANSLATIONS.hi;

    // Update UI elements with data-i18n attributes
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (trans[key]) {
        el.textContent = trans[key];
      }
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (trans[key]) {
        el.placeholder = trans[key];
      }
    });

    // Update chat language
    if (this.chatInstance) {
      this.chatInstance.setLanguage(lang);
    }

    // Refresh quick prompts
    this.renderQuickPrompts(trans.quickPrompts || []);
  }

  bindDeviceControls() {
    const deviceDisplay = document.getElementById('device-id-display');
    if (deviceDisplay) {
      deviceDisplay.textContent = this.deviceId;
    }

    // Connection badge toggle (Live vs Demo)
    const modeToggle = document.getElementById('connection-mode-badge');
    if (modeToggle) {
      modeToggle.addEventListener('click', async () => {
        window.api.setDemoMode(!window.api.isDemoMode);
        await this.syncData();
        this.showToast(window.api.isDemoMode ? 'Switched to Demo Calibrated Mode' : 'Connecting to Live Backend...', 'info');
      });
    }
  }

  bindOnboardingModal() {
    const openBtn = document.getElementById('open-profile-modal-btn');
    const modal = document.getElementById('profile-modal');
    const closeBtn = document.getElementById('close-profile-modal-btn');
    const form = document.getElementById('onboard-form');

    if (openBtn && modal) {
      openBtn.addEventListener('click', () => {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        this.populateOnboardingForm();
      });
    }

    if (closeBtn && modal) {
      closeBtn.addEventListener('click', () => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
      });
    }

    if (form) {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          device_id: document.getElementById('input-device-id').value.trim() || this.deviceId,
          farmer_name: document.getElementById('input-farmer-name').value.trim(),
          preferred_language: document.getElementById('input-farmer-lang').value,
          phone_number: document.getElementById('input-farmer-phone').value.trim(),
          kisan_id: document.getElementById('input-farmer-kisan').value.trim()
        };

        try {
          await window.api.onboardFarmer(payload);
          this.deviceId = payload.device_id;
          localStorage.setItem('agrinova_device_id', this.deviceId);
          modal.classList.add('hidden');
          modal.classList.remove('flex');
          this.showToast('Farmer profile successfully updated!', 'success');
          await this.syncData();
          this.applyLanguage(payload.preferred_language);
        } catch (err) {
          this.showToast(err.message, 'error');
        }
      });
    }
  }

  populateOnboardingForm() {
    const profile = this.activeData?.profile || window.MOCK_DATA.bootstrap.profile;
    const devInput = document.getElementById('input-device-id');
    const nameInput = document.getElementById('input-farmer-name');
    const langInput = document.getElementById('input-farmer-lang');
    const phoneInput = document.getElementById('input-farmer-phone');
    const kisanInput = document.getElementById('input-farmer-kisan');

    if (devInput) devInput.value = this.deviceId;
    if (nameInput) nameInput.value = profile.farmer_name || '';
    if (langInput) langInput.value = profile.preferred_language || this.currentLanguage;
    if (phoneInput) phoneInput.value = profile.phone_number || '';
    if (kisanInput) kisanInput.value = profile.kisan_id || '';
  }

  bindQuickPrompts() {
    const sampleLeafBtn = document.getElementById('btn-sample-leaf');
    if (sampleLeafBtn) {
      sampleLeafBtn.addEventListener('click', () => {
        if (this.chatInstance) {
          this.chatInstance.useSampleLeafPhoto();
          this.switchTab('chat');
        }
      });
    }
  }

  renderQuickPrompts(prompts) {
    const container = document.getElementById('quick-prompts-container');
    if (!container) return;

    container.innerHTML = '';
    prompts.forEach(p => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'text-left px-3 py-2 bg-slate-50 hover:bg-emerald-50 hover:border-emerald-300 border border-slate-200 rounded-xl text-xs text-slate-700 transition flex items-center justify-between gap-2 shadow-xs';
      chip.innerHTML = `
        <span class="truncate">${p}</span>
        <svg class="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
      `;
      chip.addEventListener('click', () => {
        this.switchTab('chat');
        const input = document.getElementById('chat-input');
        if (input) input.value = p;
        if (this.chatInstance) this.chatInstance.handleSendMessage(null, p);
      });
      container.appendChild(chip);
    });
  }

  bindSimulateHazardBtn() {
    const toggleHazardBtn = document.getElementById('toggle-hazard-demo-btn');
    if (!toggleHazardBtn) return;

    toggleHazardBtn.addEventListener('click', () => {
      if (!this.activeData) return;
      const current = this.activeData.hazard_state;
      if (current === 'NORMAL_MODE') {
        this.activeData.hazard_state = 'STORM_FLOOD_MODE';
        this.activeData.enforced_restrictions = ['HALT_ALL_CHEMICAL_SPRAYING', 'HALT_FERTILIZERS', 'CLEAR_DRAINAGE_FURROWS'];
        this.showToast('Simulated Hazard State: STORM_FLOOD_MODE', 'warning');
      } else if (current === 'STORM_FLOOD_MODE') {
        this.activeData.hazard_state = 'EL_NINO_DROUGHT_MODE';
        this.activeData.enforced_restrictions = ['FORBID_SURFACE_FLOOD_IRRIGATION'];
        this.showToast('Simulated Hazard State: EL_NINO_DROUGHT_MODE', 'warning');
      } else {
        this.activeData.hazard_state = 'NORMAL_MODE';
        this.activeData.enforced_restrictions = [];
        this.showToast('Simulated Hazard State: NORMAL_MODE', 'info');
      }
      this.renderDashboard();
    });
  }

  async syncData() {
    try {
      const data = await window.api.getBootstrap(this.deviceId);
      this.activeData = data;
      this.plots = await window.api.getPlots(this.deviceId);

      this.updateConnectionBadge();
      this.renderDashboard();

      if (this.mapInstance && this.plots.length > 0) {
        this.mapInstance.renderPlotPolygon(this.plots[0]);
      }
    } catch (err) {
      console.warn('Sync failed, loading fallback:', err);
      this.activeData = window.MOCK_DATA.bootstrap;
      this.plots = window.MOCK_DATA.plots;
      this.updateConnectionBadge();
      this.renderDashboard();
    }
  }

  updateConnectionBadge() {
    const badge = document.getElementById('connection-mode-badge');
    if (!badge) return;

    const isReachable = window.api.isServerReachable && !window.api.isDemoMode;
    if (isReachable) {
      badge.innerHTML = `
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        <span class="text-xs font-semibold text-emerald-800">Backend Live (Port 8000)</span>
      `;
      badge.className = 'flex items-center gap-2 px-3 py-1 bg-emerald-50 border border-emerald-200 rounded-full cursor-pointer hover:bg-emerald-100 transition';
    } else {
      badge.innerHTML = `
        <span class="w-2 h-2 rounded-full bg-amber-500"></span>
        <span class="text-xs font-semibold text-amber-800">Demo Baseline Mode</span>
      `;
      badge.className = 'flex items-center gap-2 px-3 py-1 bg-amber-50 border border-amber-200 rounded-full cursor-pointer hover:bg-amber-100 transition';
    }
  }

  renderDashboard() {
    if (!this.activeData || !this.activeData.context) return;
    const ctx = this.activeData.context;
    const hydro = ctx.hydrology || {};
    const hazard = ctx.hazard || {};
    const weather = ctx.weather || {};
    const satellite = ctx.satellite || {};
    const soil = ctx.soil_nutrients || {};
    const gw = ctx.groundwater || {};

    // 1. Farmer & Crop Header summary
    const farmerNameEl = document.getElementById('dashboard-farmer-name');
    if (farmerNameEl) farmerNameEl.textContent = ctx.farmer_name || 'Rameshwar Patil';

    const cropSummaryEl = document.getElementById('dashboard-crop-summary');
    if (cropSummaryEl) {
      cropSummaryEl.textContent = `${ctx.crop_name || 'Cotton'} • ${ctx.growth_stage || 'FLOWERING'} • ${ctx.days_after_sowing || 72} DAS`;
    }

    // 2. Hazard Banner
    const hazardBanner = document.getElementById('hazard-state-banner');
    if (hazardBanner) {
      const state = this.activeData.hazard_state || 'NORMAL_MODE';
      if (state === 'STORM_FLOOD_MODE') {
        hazardBanner.className = 'p-4 rounded-2xl bg-amber-50 border-2 border-amber-500 text-amber-950 mb-6 shadow-sm flex items-start gap-3';
        hazardBanner.innerHTML = `
          <div class="text-2xl mt-0.5">⛈️</div>
          <div class="flex-1">
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-sm text-amber-900 uppercase tracking-wide">HAZARD STATE: STORM_FLOOD_MODE ACTIVE</h3>
              <span class="text-xs px-2.5 py-0.5 rounded-full bg-amber-200 text-amber-900 font-bold">Rainfall ≥ 50mm Alert</span>
            </div>
            <p class="text-xs mt-1 text-amber-800">
              Deterministic directive: Strictly halt all chemical spraying and top-dress fertilizers immediately. Clear field drainage furrows to avoid root asphyxiation.
            </p>
            <div class="mt-2 flex flex-wrap gap-2 text-[11px] font-semibold">
              <span class="bg-red-100 text-red-800 px-2 py-0.5 rounded">⛔ HALT CHEMICAL SPRAYING</span>
              <span class="bg-red-100 text-red-800 px-2 py-0.5 rounded">⛔ HALT UREA/DAP</span>
              <span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">✔️ CLEAR DRAINAGE FURROWS</span>
            </div>
          </div>
        `;
      } else if (state === 'EL_NINO_DROUGHT_MODE') {
        hazardBanner.className = 'p-4 rounded-2xl bg-orange-50 border-2 border-orange-500 text-orange-950 mb-6 shadow-sm flex items-start gap-3';
        hazardBanner.innerHTML = `
          <div class="text-2xl mt-0.5">☀️</div>
          <div class="flex-1">
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-sm text-orange-900 uppercase tracking-wide">HAZARD STATE: EL_NINO_DROUGHT_MODE</h3>
              <span class="text-xs px-2.5 py-0.5 rounded-full bg-orange-200 text-orange-900 font-bold">GW > 18m & Deficit > 35%</span>
            </div>
            <p class="text-xs mt-1 text-orange-800">
              Deterministic directive: Surface flood irrigation is strictly prohibited. Restrict watering to night-time drip cycles and apply straw/biomass mulching.
            </p>
          </div>
        `;
      } else {
        hazardBanner.className = 'p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-950 mb-6 shadow-xs flex items-center justify-between';
        hazardBanner.innerHTML = `
          <div class="flex items-center gap-3">
            <span class="flex h-3 w-3 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <div>
              <div class="text-xs font-bold text-emerald-900 uppercase tracking-wide">Hazard Engine: Normal Operating Envelope</div>
              <div class="text-[11px] text-emerald-700">No extreme weather hazards detected. Safe agronomic operating conditions.</div>
            </div>
          </div>
          <span class="text-xs font-semibold px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full border border-emerald-300">NORMAL_MODE</span>
        `;
      }
    }

    // 3. Hydrology Card (FAO-56 Penman-Monteith)
    const hydroTriggerBadge = document.getElementById('hydro-trigger-badge');
    const hydroRecDepth = document.getElementById('hydro-rec-depth');
    const hydroDetails = document.getElementById('hydro-details');
    const hydroEt0 = document.getElementById('hydro-et0');
    const hydroEtc = document.getElementById('hydro-etc');
    const hydroDepletion = document.getElementById('hydro-depletion');
    const hydroRaw = document.getElementById('hydro-raw');
    const hydroProgressBar = document.getElementById('hydro-progress-bar');

    if (hydroTriggerBadge) {
      const trig = hydro.trigger || 'HOLD';
      if (trig === 'IRRIGATE') {
        hydroTriggerBadge.className = 'px-3 py-1 bg-blue-600 text-white font-bold text-xs rounded-full shadow-xs flex items-center gap-1.5';
        hydroTriggerBadge.innerHTML = '💧 IRRIGATE TODAY';
      } else if (trig === 'DRAIN') {
        hydroTriggerBadge.className = 'px-3 py-1 bg-amber-600 text-white font-bold text-xs rounded-full shadow-xs flex items-center gap-1.5';
        hydroTriggerBadge.innerHTML = '⚠️ DRAIN WATERLOGGED';
      } else {
        hydroTriggerBadge.className = 'px-3 py-1 bg-emerald-600 text-white font-bold text-xs rounded-full shadow-xs flex items-center gap-1.5';
        hydroTriggerBadge.innerHTML = '🌿 SOIL MOISTURE SAFE (HOLD)';
      }
    }

    if (hydroRecDepth) hydroRecDepth.textContent = `${hydro.recommended_depth_mm || 0.0} mm`;
    if (hydroDetails) hydroDetails.textContent = hydro.details || 'Root zone depletion within safe buffer.';
    if (hydroEt0) hydroEt0.textContent = `${hydro.et0_mm || 4.85} mm/day`;
    if (hydroEtc) hydroEtc.textContent = `${hydro.etc_mm || 5.58} mm/day`;
    if (hydroDepletion) hydroDepletion.textContent = `${hydro.depletion_mm || 42.5} mm`;
    if (hydroRaw) hydroRaw.textContent = `${hydro.raw_mm || 78.0} mm`;

    if (hydroProgressBar) {
      const depletion = hydro.depletion_mm || 42.5;
      const raw = hydro.raw_mm || 78.0;
      const pct = Math.min(100, Math.round((depletion / raw) * 100));
      hydroProgressBar.style.width = `${pct}%`;
      if (pct > 90) {
        hydroProgressBar.className = 'h-full bg-red-500 rounded-full transition-all duration-500';
      } else if (pct > 70) {
        hydroProgressBar.className = 'h-full bg-amber-500 rounded-full transition-all duration-500';
      } else {
        hydroProgressBar.className = 'h-full bg-emerald-500 rounded-full transition-all duration-500';
      }
    }

    // 4. Satellite STAC (NDVI & NDWI)
    const ndviVal = document.getElementById('satellite-ndvi-val');
    const ndwiVal = document.getElementById('satellite-ndwi-val');
    const ndviBar = document.getElementById('satellite-ndvi-bar');
    const ndwiBar = document.getElementById('satellite-ndwi-bar');
    const satDetails = document.getElementById('satellite-details');

    if (ndviVal) ndviVal.textContent = satellite.ndvi !== undefined ? satellite.ndvi.toFixed(2) : '0.68';
    if (ndwiVal) ndwiVal.textContent = satellite.ndwi !== undefined ? satellite.ndwi.toFixed(2) : '0.14';
    if (satDetails) satDetails.textContent = satellite.details || 'Healthy canopy with robust chlorophyll absorption and adequate leaf water content.';

    if (ndviBar) {
      const ndviPct = Math.round(((satellite.ndvi || 0.68) / 1.0) * 100);
      ndviBar.style.width = `${Math.max(10, Math.min(100, ndviPct))}%`;
    }
    if (ndwiBar) {
      const ndwiNormalized = Math.round((((satellite.ndwi || 0.14) + 1.0) / 2.0) * 100);
      ndwiBar.style.width = `${Math.max(10, Math.min(100, ndwiNormalized))}%`;
    }

    // 5. Soil & Groundwater
    const gwDepthEl = document.getElementById('gw-depth-val');
    const soilN = document.getElementById('soil-n-val');
    const soilP = document.getElementById('soil-p-val');
    const soilK = document.getElementById('soil-k-val');
    const soilPh = document.getElementById('soil-ph-val');

    if (gwDepthEl) gwDepthEl.textContent = `${gw.depth_mbgl || 11.2} mbgl`;
    if (soilN) soilN.textContent = `${soil.nitrogen_kg_ha || 220} kg/ha`;
    if (soilP) soilP.textContent = `${soil.phosphorus_kg_ha || 18.5} kg/ha`;
    if (soilK) soilK.textContent = `${soil.potassium_kg_ha || 310} kg/ha`;
    if (soilPh) soilPh.textContent = `pH ${soil.ph || 7.8}`;

    // 6. Weather Widget
    const weatherTemp = document.getElementById('weather-temp-val');
    const weatherRain = document.getElementById('weather-rain-val');
    const weatherRh = document.getElementById('weather-rh-val');
    const weatherDesc = document.getElementById('weather-desc-val');

    if (weatherTemp) weatherTemp.textContent = `${weather.t_mean || 28.1}°C`;
    if (weatherRain) weatherRain.textContent = `${weather.rainfall_24h_mm || 0.0} mm`;
    if (weatherRh) weatherRh.textContent = `${weather.rh_mean || 68}%`;
    if (weatherDesc) weatherDesc.textContent = weather.condition || 'Clear sky';

    // 7. Update FAO-56 Depletion Chart
    this.renderDepletionChart(hydro);
  }

  renderDepletionChart(hydro) {
    const canvas = document.getElementById('depletionChart');
    if (!canvas || typeof Chart === 'undefined') return;

    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');
    const raw = hydro.raw_mm || 78.0;
    const currentDepletion = hydro.depletion_mm || 42.5;

    // Simulate 5-day soil moisture trajectory
    const labels = ['Day -2', 'Yesterday', 'Today', 'Tomorrow', 'Day +2'];
    const data = [32.0, 37.5, currentDepletion, currentDepletion + 5.5, currentDepletion + 11.0];

    this.chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Root Zone Depletion (mm)',
            data: data,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.3,
            borderWidth: 2.5,
            pointBackgroundColor: '#047857',
            pointRadius: 4
          },
          {
            label: 'Readily Available Water - RAW (Refill Threshold)',
            data: [raw, raw, raw, raw, raw],
            borderColor: '#ef4444',
            borderDash: [5, 5],
            borderWidth: 2,
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, font: { size: 10 } }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: Math.max(100, raw + 20),
            title: { display: true, text: 'Depletion (mm)', font: { size: 10 } },
            ticks: { font: { size: 9 } }
          },
          x: {
            ticks: { font: { size: 9 } }
          }
        }
      }
    });
  }

  initMap() {
    if (typeof FarmFieldMap !== 'undefined') {
      this.mapInstance = new FarmFieldMap('farm-map');
      this.mapInstance.init();
      if (this.plots && this.plots.length > 0) {
        this.mapInstance.renderPlotPolygon(this.plots[0]);
      }
    }
  }

  initChat() {
    if (typeof MultimodalChat !== 'undefined') {
      this.chatInstance = new MultimodalChat({
        containerId: 'chat-messages',
        deviceId: this.deviceId,
        language: this.currentLanguage
      });
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const colorMap = {
      info: 'bg-slate-800 text-white',
      success: 'bg-emerald-700 text-white',
      warning: 'bg-amber-600 text-white',
      error: 'bg-red-600 text-white'
    };

    toast.className = `px-4 py-2.5 rounded-xl text-xs font-medium shadow-lg transition-all duration-300 transform translate-y-2 opacity-0 flex items-center gap-2 ${colorMap[type] || colorMap.info}`;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    setTimeout(() => {
      toast.classList.add('opacity-0');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
}

// Instantiate on DOM loaded
document.addEventListener('DOMContentLoaded', () => {
  window.app = new AppController();
});
