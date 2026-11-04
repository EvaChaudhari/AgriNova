/**
 * Krishi Mitra (AgriNova) - API Client
 * Connects to FastAPI Backend with Automatic Offline Fallback
 */

class AgriAPI {
  constructor() {
    this.baseUrl = window.CONFIG?.API_BASE_URL || 'http://localhost:8000/api/v1';
    this.isDemoMode = false;
    this.isServerReachable = false;
  }

  setBaseUrl(url) {
    this.baseUrl = url.replace(/\/+$/, '');
  }

  setDemoMode(val) {
    this.isDemoMode = !!val;
    localStorage.setItem('agrinova_demo_mode', this.isDemoMode ? '1' : '0');
  }

  async checkHealth() {
    if (this.isDemoMode) {
      this.isServerReachable = false;
      return false;
    }
    try {
      const rootUrl = this.baseUrl.replace(/\/api\/v1$/, '');
      const res = await fetch(`${rootUrl}/healthz`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: AbortSignal.timeout(2500)
      });
      this.isServerReachable = res.ok;
      return res.ok;
    } catch {
      this.isServerReachable = false;
      return false;
    }
  }

  /**
   * Bootstrap endpoint: Retrieves device profile, active plot, live environmental layers,
   * FAO-56 hydrological water balance, and hazard state machine status.
   */
  async getBootstrap(deviceId) {
    if (this.isDemoMode) {
      return window.MOCK_DATA.bootstrap;
    }

    try {
      const res = await fetch(`${this.baseUrl}/bootstrap?device_id=${encodeURIComponent(deviceId)}`, {
        headers: { 'Accept': 'application/json' },
        signal: AbortSignal.timeout(4000)
      });

      if (!res.ok) {
        throw new Error(`Bootstrap failed: HTTP ${res.status}`);
      }
      this.isServerReachable = true;
      return await res.json();
    } catch (err) {
      console.warn('[AgriAPI] Falling back to calibrated baseline:', err.message);
      this.isServerReachable = false;
      return window.MOCK_DATA.bootstrap;
    }
  }

  /**
   * Onboard or update farmer profile
   */
  async onboardFarmer(profile) {
    if (this.isDemoMode || !this.isServerReachable) {
      // Simulate successful local onboarding
      const updated = {
        ...window.MOCK_DATA.bootstrap.profile,
        farmer_name: profile.farmer_name,
        preferred_language: profile.preferred_language,
        phone_number: profile.phone_number,
        kisan_id: profile.kisan_id,
        updated_at: new Date().toISOString()
      };
      window.MOCK_DATA.bootstrap.profile = updated;
      window.MOCK_DATA.bootstrap.is_onboarded = true;
      return updated;
    }

    const res = await fetch(`${this.baseUrl}/bootstrap/onboard`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(profile)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to onboard farmer');
    }
    return await res.json();
  }

  /**
   * Fetch all registered plots for device
   */
  async getPlots(deviceId) {
    if (this.isDemoMode || !this.isServerReachable) {
      return window.MOCK_DATA.plots;
    }

    try {
      const res = await fetch(`${this.baseUrl}/plots?device_id=${encodeURIComponent(deviceId)}`, {
        signal: AbortSignal.timeout(4000)
      });
      if (!res.ok) throw new Error(`Plots fetch failed: ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('[AgriAPI] Plots fallback:', err.message);
      return window.MOCK_DATA.plots;
    }
  }

  /**
   * Register a new farm field boundary polygon
   */
  async createPlot(plotPayload) {
    if (this.isDemoMode || !this.isServerReachable) {
      const newPlot = {
        id: Date.now(),
        ...plotPayload,
        centroid_lat: plotPayload.boundary.coordinates[0][0][1],
        centroid_lon: plotPayload.boundary.coordinates[0][0][0],
        area_hectares: 1.25,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      window.MOCK_DATA.plots.unshift(newPlot);
      return newPlot;
    }

    const res = await fetch(`${this.baseUrl}/plots`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(plotPayload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to register plot');
    }
    return await res.json();
  }

  /**
   * Register active crop cycle
   */
  async registerCropCycle(plotId, cyclePayload) {
    if (this.isDemoMode || !this.isServerReachable) {
      const cycle = {
        id: Date.now(),
        plot_id: plotId,
        ...cyclePayload,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      const plot = window.MOCK_DATA.plots.find(p => p.id === plotId);
      if (plot) plot.crop_cycle = cycle;
      return cycle;
    }

    const res = await fetch(`${this.baseUrl}/plots/${plotId}/crop-cycle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(cyclePayload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Failed to register crop cycle');
    }
    return await res.json();
  }

  /**
   * Unified Voice / Vision / Text Chat Receptor Endpoint
   */
  async sendChatReceptor({ deviceId, sessionId, queryText, language, audioBlob, imageBlob }) {
    if (this.isDemoMode || !this.isServerReachable) {
      return this._simulateChatResponse(queryText, language, imageBlob, audioBlob);
    }

    try {
      // If multimodal files (audio / image) present, send multipart/form-data
      if (audioBlob || imageBlob) {
        const formData = new FormData();
        formData.append('device_id', deviceId);
        formData.append('session_id', sessionId || 'new');
        formData.append('language', language || 'hi');

        if (queryText) {
          formData.append('query_text', queryText);
        }
        if (audioBlob) {
          formData.append('audio_file', audioBlob, 'farmer_voice.wav');
        }
        if (imageBlob) {
          formData.append('image_file', imageBlob, 'affected_leaf.jpg');
        }

        const res = await fetch(`${this.baseUrl}/chat/receptor`, {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          throw new Error(`Chat receptor HTTP ${res.status}`);
        }
        return await res.json();
      } else {
        // Pure text query: send JSON payload
        const res = await fetch(`${this.baseUrl}/chat/receptor`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            device_id: deviceId,
            session_id: sessionId || 'new',
            query_text: queryText,
            language: language || 'hi'
          })
        });

        if (!res.ok) {
          throw new Error(`Chat receptor HTTP ${res.status}`);
        }
        return await res.json();
      }
    } catch (err) {
      console.warn('[AgriAPI] Chat receptor offline fallback:', err.message);
      return this._simulateChatResponse(queryText, language, imageBlob, audioBlob);
    }
  }

  _simulateChatResponse(queryText, language, imageBlob, audioBlob) {
    const q = (queryText || '').toLowerCase();
    const lang = language || 'hi';

    if (imageBlob) {
      return lang === 'hi'
        ? window.MOCK_DATA.chatResponses.pest_hi
        : window.MOCK_DATA.chatResponses.pest_en;
    }

    if (q.includes('पानी') || q.includes('irrigate') || q.includes('water') || q.includes('सिंचाई') || q.includes('నీరు')) {
      return lang === 'hi'
        ? window.MOCK_DATA.chatResponses.irrigate_hi
        : window.MOCK_DATA.chatResponses.irrigate_en;
    }

    if (q.includes('बारिश') || q.includes('storm') || q.includes('flood') || q.includes('पाऊस') || q.includes('వర్షం')) {
      return window.MOCK_DATA.chatResponses.storm_alert_hi;
    }

    // Default intelligent ICAR guidance
    return {
      session_id: 'sim-' + Date.now(),
      reply_text: lang === 'hi'
        ? 'किसान भाई, आपकी कपास की फसल में फूल आने की अवस्था है। मिट्टी में नमी का स्तर संतुलित है। किसी भी रासायनिक छिड़काव से पहले 5% नीम तेल (NSKE) का उपयोग करें और मौसम पूर्वानुमान पर नज़र रखें।'
        : 'Farmer brother, your cotton crop is in the flowering stage. Soil moisture is balanced. Please prioritize biological IPM (5% NSKE) before applying chemical sprays, and monitor 24h rainfall forecasts.',
      hazard_state: 'NORMAL_MODE',
      injected_context: {
        crop_name: 'Cotton',
        growth_stage: 'FLOWERING',
        hydrology: { trigger: 'HOLD', recommended_depth_mm: 0.0 },
        hazard: { current_state: 'NORMAL_MODE', enforced_restrictions: [] }
      }
    };
  }
}

window.api = new AgriAPI();

