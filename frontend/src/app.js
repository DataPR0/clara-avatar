/**
 * Clara — Frontend App
 * Wake word "Oye Clara" → STT → Backend → LiveAvatar
 */

// ─── Config ──────────────────────────────────────────────────────────────────
let BACKEND_URL = localStorage.getItem("clara_backend_url") || "http://localhost:8090";
let sessionId = `session_${Date.now()}`;
let avatarSessionId = null;
let isListening = false;
let wakeWordActive = true;
let recognition = null;
let continuousRecognition = null;

// ─── DOM ─────────────────────────────────────────────────────────────────────
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const messages = document.getElementById("messages");
const textInput = document.getElementById("text-input");
const sendBtn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const avatarIframe = document.getElementById("avatar-iframe");
const avatarPlaceholder = document.getElementById("avatar-placeholder");
const startAvatarBtn = document.getElementById("start-avatar-btn");
const stopAvatarBtn = document.getElementById("stop-avatar-btn");
const wakeWordToggle = document.getElementById("wake-word-toggle");
const configToggleBtn = document.getElementById("config-toggle-btn");
const configPanel = document.getElementById("config-panel");
const backendUrlInput = document.getElementById("backend-url");
const saveConfigBtn = document.getElementById("save-config-btn");

// ─── Status ──────────────────────────────────────────────────────────────────
function setStatus(state, text) {
  statusDot.className = `dot ${state}`;
  statusText.textContent = text;
}

// ─── Messages ────────────────────────────────────────────────────────────────
function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function addSystemMessage(text) {
  addMessage("system", text);
}

// ─── Chat con Backend ────────────────────────────────────────────────────────
async function sendMessage(text) {
  if (!text.trim()) return;

  addMessage("user", text);
  setStatus("thinking", "Clara está pensando...");

  const thinkingDiv = addMessage("assistant", "...");

  try {
    const res = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    thinkingDiv.textContent = data.reply;
    setStatus("idle", 'Esperando "Oye Clara"...');

    // Si el avatar está activo, habla la respuesta
    if (avatarSessionId) {
      setStatus("speaking", "Clara está hablando...");
      setTimeout(() => setStatus("idle", 'Esperando "Oye Clara"...'), 3000);
    }
  } catch (err) {
    thinkingDiv.textContent = `Error: ${err.message}`;
    thinkingDiv.style.color = "#ef4444";
    setStatus("error", "Error de conexión");
    console.error(err);
  }
}

// ─── Wake Word "Oye Clara" ───────────────────────────────────────────────────
function startWakeWordDetection() {
  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    addSystemMessage("⚠️ Tu navegador no soporta reconocimiento de voz. Usa Chrome.");
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  continuousRecognition = new SpeechRecognition();
  continuousRecognition.continuous = true;
  continuousRecognition.interimResults = true;
  continuousRecognition.lang = "es-CO";
  continuousRecognition.maxAlternatives = 3;

  continuousRecognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((r) => r[0].transcript)
      .join(" ")
      .toLowerCase()
      .trim();

    // Detectar wake word
    if (
      wakeWordActive &&
      !isListening &&
      (transcript.includes("oye clara") ||
        transcript.includes("hey clara") ||
        transcript.includes("oye, clara"))
    ) {
      console.log("[Wake] Detectado:", transcript);
      activateClara();
    }
  };

  continuousRecognition.onerror = (e) => {
    if (e.error !== "no-speech" && e.error !== "aborted") {
      console.warn("[WakeWord] Error:", e.error);
    }
  };

  continuousRecognition.onend = () => {
    // Reiniciar si el toggle sigue activo
    if (wakeWordActive && !isListening) {
      setTimeout(() => {
        try { continuousRecognition.start(); } catch (e) {}
      }, 500);
    }
  };

  try {
    continuousRecognition.start();
    addSystemMessage('🎙️ Wake word activo — di "Oye Clara" para activarme');
  } catch (e) {
    addSystemMessage("⚠️ No se pudo iniciar el micrófono: " + e.message);
  }
}

function stopWakeWordDetection() {
  if (continuousRecognition) {
    try { continuousRecognition.stop(); } catch (e) {}
  }
}

// ─── Activar Clara (después del wake word) ──────────────────────────────────
function activateClara() {
  if (isListening) return;
  isListening = true;

  // Pausar wake word temporalmente
  stopWakeWordDetection();

  setStatus("listening", "Te escucho...");
  addSystemMessage("🎙️ Clara activada — habla ahora");

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = "es-CO";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    console.log("[STT] Escuché:", transcript);

    // Quitar el wake word del inicio si quedó en la transcripción
    const cleaned = transcript
      .replace(/^(oye|hey)\s*clara[,.]?\s*/i, "")
      .trim();

    if (cleaned) {
      sendMessage(cleaned);
    }
  };

  recognition.onerror = (e) => {
    console.warn("[STT] Error:", e.error);
    setStatus("idle", 'Esperando "Oye Clara"...');
  };

  recognition.onend = () => {
    isListening = false;
    micBtn.classList.remove("active");

    // Reactivar wake word después de responder
    setTimeout(() => {
      if (wakeWordActive) {
        startWakeWordDetection();
        setStatus("idle", 'Esperando "Oye Clara"...');
      }
    }, 2000);
  };

  micBtn.classList.add("active");

  try {
    recognition.start();
  } catch (e) {
    isListening = false;
    setStatus("error", "Error de micrófono");
  }
}

// ─── Avatar LiveAvatar ───────────────────────────────────────────────────────
async function startAvatar() {
  startAvatarBtn.disabled = true;
  setStatus("thinking", "Iniciando avatar...");
  addSystemMessage("🎥 Cargando avatar...");

  try {
    const res = await fetch(`${BACKEND_URL}/embed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sandbox: true }), // sandbox=true para no gastar créditos en pruebas
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.url) {
      avatarIframe.src = data.url;
      avatarIframe.style.display = "block";
      avatarPlaceholder.style.display = "none";
      stopAvatarBtn.disabled = false;
      avatarSessionId = data.session_id || "active";
      addSystemMessage("✅ Avatar conectado");
      setStatus("idle", 'Esperando "Oye Clara"...');
    }
  } catch (err) {
    addSystemMessage(`❌ Error iniciando avatar: ${err.message}`);
    addSystemMessage("💡 Verifica que LIVEAVATAR_API_KEY esté configurada en el backend");
    setStatus("idle", 'Esperando "Oye Clara"...');
    startAvatarBtn.disabled = false;
  }
}

async function stopAvatar() {
  avatarIframe.src = "";
  avatarIframe.style.display = "none";
  avatarPlaceholder.style.display = "flex";
  startAvatarBtn.disabled = false;
  stopAvatarBtn.disabled = true;
  avatarSessionId = null;
  addSystemMessage("⏹ Avatar desconectado");
  setStatus("idle", 'Esperando "Oye Clara"...');
}

// ─── Event Listeners ─────────────────────────────────────────────────────────
sendBtn.addEventListener("click", () => {
  sendMessage(textInput.value);
  textInput.value = "";
});

textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    sendMessage(textInput.value);
    textInput.value = "";
  }
});

micBtn.addEventListener("click", () => {
  if (isListening) {
    if (recognition) recognition.stop();
  } else {
    activateClara();
  }
});

startAvatarBtn.addEventListener("click", startAvatar);
stopAvatarBtn.addEventListener("click", stopAvatar);

wakeWordToggle.addEventListener("change", () => {
  wakeWordActive = wakeWordToggle.checked;
  if (wakeWordActive) {
    startWakeWordDetection();
    addSystemMessage('🎙️ Wake word activado — di "Oye Clara"');
  } else {
    stopWakeWordDetection();
    addSystemMessage("🔇 Wake word desactivado");
  }
});

configToggleBtn.addEventListener("click", () => {
  const visible = configPanel.style.display !== "none";
  configPanel.style.display = visible ? "none" : "flex";
});

saveConfigBtn.addEventListener("click", () => {
  BACKEND_URL = backendUrlInput.value.trim();
  localStorage.setItem("clara_backend_url", BACKEND_URL);
  configPanel.style.display = "none";
  addSystemMessage(`⚙️ Backend actualizado: ${BACKEND_URL}`);
});

// ─── Init ────────────────────────────────────────────────────────────────────
backendUrlInput.value = BACKEND_URL;
addSystemMessage("⚡ Clara lista");
startWakeWordDetection();
