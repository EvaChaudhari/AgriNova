/**
 * Krishi Mitra (AgriNova) - Multimodal Conversational Receptor (Voice/Vision/Text)
 * Implements MediaRecorder voice capture, leaf pathology image upload, and TTS playback
 */

class MultimodalChat {
  constructor(options = {}) {
    this.containerId = options.containerId || 'chat-messages';
    this.deviceId = options.deviceId || window.CONFIG?.DEFAULT_DEVICE_ID;
    this.language = options.language || window.CONFIG?.DEFAULT_LANGUAGE || 'hi';
    this.sessionId = 'sess-' + Math.random().toString(36).substring(2, 9);

    // Audio recording state
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.selectedImageBlob = null;
    this.selectedImageUrl = null;

    // Elements
    this.messagesContainer = document.getElementById(this.containerId);
    this.textInput = document.getElementById('chat-input');
    this.sendBtn = document.getElementById('chat-send-btn');
    this.micBtn = document.getElementById('chat-mic-btn');
    this.leafInput = document.getElementById('chat-leaf-input');
    this.imagePreviewContainer = document.getElementById('image-preview-bar');

    this.init();
  }

  setLanguage(lang) {
    this.language = lang;
    this.renderInitialGreeting();
  }

  setDeviceId(id) {
    this.deviceId = id;
  }

  init() {
    // Bind listeners
    if (this.sendBtn) {
      this.sendBtn.addEventListener('click', () => this.handleSendMessage());
    }
    if (this.textInput) {
      this.textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.handleSendMessage();
        }
      });
    }
    if (this.micBtn) {
      this.micBtn.addEventListener('click', () => this.toggleVoiceRecording());
    }
    if (this.leafInput) {
      this.leafInput.addEventListener('change', (e) => this.handleImageSelect(e));
    }

    this.renderInitialGreeting();
  }

  renderInitialGreeting() {
    if (!this.messagesContainer) return;
    this.messagesContainer.innerHTML = '';

    const greetings = {
      hi: 'नमस्ते किसान भाई! मैं कृषि मित्र AI कृषि वैज्ञानिक हूँ। आप बोलकर, पत्ती का फोटो भेजकर, या लिखकर अपनी फसल, सिंचाई व कीट प्रबंधन के बारे में पूछ सकते हैं।',
      en: 'Welcome Farmer friend! I am your Krishi Mitra Senior Agronomist. Ask questions via voice, upload crop leaf photos for pest diagnosis, or type your query below.',
      mr: 'नमस्कार शेतकरी बंधू! मी तुमचा कृषी मित्र AI शास्त्रज्ञ आहे. तुम्ही बोलून, पानाचा फोटो टाकून किंवा टाईप करून पिकाविषयी सल्ला विचारू शकता.',
      te: 'నమస్కారం రైతు సోదరా! నేను కృషి మిత్ర వ్యవసాయ శాస్త్రవేత్తను. మీ పంట, నీటిపారుదల మరియు తెగుళ్ల నిర్వహణపై వాయిస్ లేదా ఫోటో ద్వారా అడగవచ్చు.'
    };

    this.appendMessage({
      sender: 'bot',
      text: greetings[this.language] || greetings.hi,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      badges: ['ICAR Senior Agronomist', 'FAO-56 Grounded']
    });
  }

  /**
   * Voice Recording via MediaRecorder API
   */
  async toggleVoiceRecording() {
    if (this.isRecording) {
      this.stopVoiceRecording();
    } else {
      await this.startVoiceRecording();
    }
  }

  async startVoiceRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        // Stop all audio tracks
        stream.getTracks().forEach(track => track.stop());
        this.submitVoiceQuery(audioBlob);
      };

      this.mediaRecorder.start();
      this.isRecording = true;
      this.updateMicUi(true);
    } catch (err) {
      console.warn('Microphone access denied or unsupported:', err);
      // Simulate voice input fallback
      this.simulateVoiceQuery();
    }
  }

  stopVoiceRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.isRecording = false;
      this.updateMicUi(false);
    }
  }

  updateMicUi(recording) {
    if (!this.micBtn) return;
    if (recording) {
      this.micBtn.classList.add('bg-red-500', 'text-white', 'animate-pulse');
      this.micBtn.classList.remove('bg-emerald-50', 'text-emerald-700');
      this.micBtn.setAttribute('title', 'Recording... Tap to stop');
      if (this.textInput) this.textInput.placeholder = '🎙️ Recording voice... Speak clearly now';
    } else {
      this.micBtn.classList.remove('bg-red-500', 'text-white', 'animate-pulse');
      this.micBtn.classList.add('bg-emerald-50', 'text-emerald-700');
      this.micBtn.setAttribute('title', 'Record Voice');
      if (this.textInput) {
        const trans = window.CONFIG?.TRANSLATIONS[this.language] || window.CONFIG?.TRANSLATIONS.hi;
        this.textInput.placeholder = trans.chatPlaceholder;
      }
    }
  }

  simulateVoiceQuery() {
    this.updateMicUi(true);
    if (this.textInput) this.textInput.placeholder = '🎙️ Listening to farmer voice...';
    setTimeout(() => {
      this.updateMicUi(false);
      const voiceQueries = {
        hi: 'मेरी कपास की फसल में आज पानी देना है या नहीं?',
        en: 'Do I need to irrigate my cotton field today?',
        mr: 'माझ्या कापूस पिकाला आज पाणी द्यायचे आहे का?',
        te: 'ఈరోజు నా పత్తి పంటకు నీరు పెట్టాలా?'
      };
      const text = voiceQueries[this.language] || voiceQueries.hi;
      if (this.textInput) this.textInput.value = text;
      this.handleSendMessage(null, text);
    }, 1800);
  }

  /**
   * Leaf image selection & preview
   */
  handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    this.selectedImageBlob = file;
    this.selectedImageUrl = URL.createObjectURL(file);
    this.showImagePreview(this.selectedImageUrl, file.name);
  }

  useSampleLeafPhoto() {
    // Generate a visual canvas of a crop leaf with pathology spots for instant test
    const canvas = document.createElement('canvas');
    canvas.width = 300;
    canvas.height = 300;
    const ctx = canvas.getContext('2d');

    // Draw background leaf
    ctx.fillStyle = '#2d6a4f';
    ctx.fillRect(0, 300, 300, 300);

    // Leaf vein structure
    ctx.strokeStyle = '#40916c';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(150, 20);
    ctx.lineTo(150, 280);
    ctx.stroke();

    // Pathology spots (yellowish brown lesions)
    ctx.fillStyle = '#d4a373';
    ctx.beginPath();
    ctx.arc(110, 90, 25, 0, Math.PI * 2);
    ctx.arc(190, 150, 30, 0, Math.PI * 2);
    ctx.arc(130, 210, 20, 0, Math.PI * 2);
    ctx.fill();

    canvas.toBlob((blob) => {
      this.selectedImageBlob = blob;
      this.selectedImageUrl = URL.createObjectURL(blob);
      this.showImagePreview(this.selectedImageUrl, 'sample_cotton_leaf.jpg');
    }, 'image/jpeg');
  }

  showImagePreview(url, name) {
    if (!this.imagePreviewContainer) return;
    this.imagePreviewContainer.innerHTML = `
      <div class="inline-flex items-center gap-2 p-1.5 px-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 shadow-sm">
        <img src="${url}" class="w-8 h-8 rounded object-cover border border-emerald-300" alt="Leaf Preview" />
        <span class="font-medium truncate max-w-[150px]">${name || 'Crop Leaf Photo'}</span>
        <button type="button" id="clear-leaf-btn" class="ml-1 p-0.5 text-slate-400 hover:text-red-500 rounded-full">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>
    `;
    this.imagePreviewContainer.classList.remove('hidden');

    document.getElementById('clear-leaf-btn')?.addEventListener('click', () => {
      this.clearSelectedImage();
    });
  }

  clearSelectedImage() {
    this.selectedImageBlob = null;
    if (this.selectedImageUrl) {
      URL.revokeObjectURL(this.selectedImageUrl);
      this.selectedImageUrl = null;
    }
    if (this.imagePreviewContainer) {
      this.imagePreviewContainer.innerHTML = '';
      this.imagePreviewContainer.classList.add('hidden');
    }
    if (this.leafInput) this.leafInput.value = '';
  }

  submitVoiceQuery(audioBlob) {
    const defaultVoicePrompts = {
      hi: '🎙️ किसान का वॉइस संदेश (ऑडियो इनपुट)',
      en: '🎙️ Farmer Voice Audio Query',
      mr: '🎙️ शेतकऱ्याचा व्हॉइस संदेश',
      te: '🎙️ రైతు వాయిస్ సందేశం'
    };
    this.handleSendMessage(audioBlob, defaultVoicePrompts[this.language] || defaultVoicePrompts.hi);
  }

  async handleSendMessage(audioBlob = null, explicitText = null) {
    const text = explicitText !== null ? explicitText : (this.textInput?.value || '').trim();
    const imageBlob = this.selectedImageBlob;
    const imageUrl = this.selectedImageUrl;

    if (!text && !audioBlob && !imageBlob) return;

    // Clear input bar
    if (this.textInput) this.textInput.value = '';

    // Append Farmer user message
    this.appendMessage({
      sender: 'user',
      text: text || (imageBlob ? '🔍 Affected crop leaf pathology analysis' : '🎙️ Voice Query'),
      imageUrl: imageUrl,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });

    // Clear image selection
    this.clearSelectedImage();

    // Show typing / processing indicator
    const typingIndicatorId = this.showTypingIndicator();

    try {
      const response = await window.api.sendChatReceptor({
        deviceId: this.deviceId,
        sessionId: this.sessionId,
        queryText: text,
        language: this.language,
        audioBlob: audioBlob,
        imageBlob: imageBlob
      });

      this.removeTypingIndicator(typingIndicatorId);

      const badges = [];
      if (response.hazard_state) badges.push(`Hazard: ${response.hazard_state}`);
      if (response.injected_context?.hydrology?.trigger) {
        badges.push(`FAO-56: ${response.injected_context.hydrology.trigger}`);
      }

      this.appendMessage({
        sender: 'bot',
        text: response.reply_text,
        audioBase64: response.audio_base64_url,
        hazardState: response.hazard_state,
        badges: badges,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });

      // Auto play TTS speech if available or synthesized
      if (response.audio_base64_url) {
        this.playBase64Audio(response.audio_base64_url);
      } else {
        this.synthesizeSpeech(response.reply_text);
      }
    } catch (err) {
      this.removeTypingIndicator(typingIndicatorId);
      this.appendMessage({
        sender: 'bot',
        text: 'क्षमा करें किसान भाई, अनुरोध संसाधित करने में समस्या आई। कृपया पुनः प्रयास करें।',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });
    }
  }

  appendMessage({ sender, text, imageUrl, audioBase64, hazardState, badges = [], time }) {
    if (!this.messagesContainer) return;

    const isUser = sender === 'user';
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex flex-col ${isUser ? 'items-end' : 'items-start'} mb-4`;

    let hazardAlert = '';
    if (hazardState === 'STORM_FLOOD_MODE') {
      hazardAlert = `
        <div class="mb-2 p-2 bg-amber-50 border-l-4 border-amber-500 rounded text-xs text-amber-900 font-medium">
          ⚠️ <b>STORM FLOOD DIRECTIVE ENFORCED:</b> Chemical spraying & fertilizers halted.
        </div>
      `;
    }

    let imageEl = '';
    if (imageUrl) {
      imageEl = `
        <div class="mb-2">
          <img src="${imageUrl}" class="w-48 h-36 object-cover rounded-lg border border-emerald-200 shadow-sm" alt="Leaf Crop Photo" />
        </div>
      `;
    }

    let audioEl = '';
    if (audioBase64) {
      audioEl = `
        <div class="mt-2.5 pt-2 border-t border-emerald-100 flex items-center gap-2">
          <button class="play-audio-btn flex items-center gap-1.5 px-3 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded-full text-xs font-medium transition shadow-sm" data-audio="${audioBase64}">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4l12 6-12 6V4z"></path></svg>
            <span>Play Voice Advisory (वॉइस सुनें)</span>
          </button>
        </div>
      `;
    }

    let badgesEl = '';
    if (badges && badges.length > 0) {
      badgesEl = `
        <div class="mt-2 flex flex-wrap gap-1.5">
          ${badges.map(b => `<span class="px-2 py-0.5 bg-emerald-50 text-emerald-800 text-[10px] font-medium rounded-full border border-emerald-200">${b}</span>`).join('')}
        </div>
      `;
    }

    messageDiv.innerHTML = `
      <div class="max-w-[85%] md:max-w-[75%] rounded-2xl p-4 shadow-sm ${
        isUser
          ? 'bg-emerald-700 text-white rounded-br-sm'
          : 'bg-white text-slate-800 border border-slate-200 rounded-bl-sm'
      }">
        ${hazardAlert}
        ${imageEl}
        <div class="text-sm leading-relaxed whitespace-pre-line">${text}</div>
        ${audioEl}
        ${badgesEl}
        <div class="mt-1 text-[10px] text-right ${isUser ? 'text-emerald-100' : 'text-slate-400'}">${time}</div>
      </div>
    `;

    this.messagesContainer.appendChild(messageDiv);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

    // Bind audio button
    messageDiv.querySelectorAll('.play-audio-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const audioSrc = btn.getAttribute('data-audio');
        if (audioSrc) this.playBase64Audio(audioSrc);
      });
    });
  }

  showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const indicator = document.createElement('div');
    indicator.id = id;
    indicator.className = 'flex items-center gap-2 p-3 bg-white border border-slate-200 rounded-2xl rounded-bl-sm w-fit mb-4 text-xs text-slate-500 shadow-sm';
    indicator.innerHTML = `
      <span class="w-2 h-2 rounded-full bg-emerald-600 animate-ping"></span>
      <span class="font-medium text-slate-600">Krishi Mitra is analyzing agronomic models...</span>
    `;
    this.messagesContainer.appendChild(indicator);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    return id;
  }

  removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  playBase64Audio(base64Src) {
    try {
      const audio = new Audio(base64Src);
      audio.play().catch(e => console.log('Audio autoplay prevented:', e));
    } catch (err) {
      console.warn('Audio playback error:', err);
    }
  }

  synthesizeSpeech(text) {
    if (!('speechSynthesis' in window)) return;
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      // Map language code
      const langMap = { hi: 'hi-IN', en: 'en-IN', mr: 'mr-IN', te: 'te-IN' };
      utterance.lang = langMap[this.language] || 'hi-IN';
      utterance.rate = 0.95;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.log('Speech synthesis unavailable');
    }
  }
}

window.MultimodalChat = MultimodalChat;
