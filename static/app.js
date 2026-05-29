// DOM Elements
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const btnClear = document.getElementById("btn-clear");
const btnFloat = document.getElementById("btn-float");
const selectSource = document.getElementById("select-source");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const transcriptBox = document.getElementById("transcript-box");
const placeholderText = document.getElementById("placeholder-text");
const finalSpan = document.getElementById("final-span");
const nonfinalSpan = document.getElementById("nonfinal-span");
const waveBars = document.querySelectorAll(".wave-bar");

// Audio & WebSocket Variables
let audioContext = null;
let mediaStreams = []; // Track all active streams (mic, screen-share)
let processorNode = null;
let socket = null;
let finalTranscript = "";

// State syncing managed directly via backend websocket

// Initialize Visualizer (set default small scale)
function resetVisualizer() {
    waveBars.forEach(bar => {
        bar.style.transform = "scaleY(1)";
    });
}

// Update Visualizer bars based on audio amplitude (RMS)
function updateVisualizer(rms) {
    const multiplier = 25;
    const baseVolume = Math.min(6, 1 + (rms * multiplier));
    
    waveBars.forEach((bar, index) => {
        const phase = Date.now() * 0.01 + index * 0.5;
        const waveFactor = 0.7 + Math.sin(phase) * 0.3;
        const scale = Math.max(1, baseVolume * waveFactor);
        bar.style.transform = `scaleY(${scale})`;
    });
}

// Set status indicator state
function setStatus(state, text) {
    statusDot.className = "dot";
    statusText.innerText = text;
    
    if (state === "ready") {
        statusDot.classList.add("dot-offline");
    } else if (state === "connecting") {
        statusDot.classList.add("dot-connecting");
    } else if (state === "listening") {
        statusDot.classList.add("dot-online");
    }
}

// Helper to auto scroll element to bottom
function scrollToBottom(el) {
    if (el) {
        el.scrollTop = el.scrollHeight;
    }
}

// Start recording and WebSocket streaming
async function startStreaming() {
    setStatus("connecting", "Connecting...");
    btnStart.disabled = true;
    selectSource.disabled = true;
    
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/stream`;
    
    try {
        socket = new WebSocket(wsUrl);
    } catch (err) {
        console.error("Failed to create WebSocket:", err);
        showError("Could not connect to server.");
        stopStreaming();
        return;
    }
    
    socket.onopen = async () => {
        console.log("WebSocket connection established.");
        try {
            const captureMode = selectSource.value;
            await startAudioCapture(captureMode);
            setStatus("listening", "Listening...");
            btnStop.disabled = false;
            if (placeholderText) {
                placeholderText.style.display = "none";
            }
        } catch (err) {
            console.error("Error setting up audio:", err);
            showError(err.message || "Microphone or Screen audio access denied.");
            stopStreaming();
        }
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.error) {
            console.error("Server returned error:", data.error);
            showError(data.error);
            stopStreaming();
            return;
        }
        
        if (data.tokens) {
            let newFinals = "";
            let currentNonFinals = "";
            
            for (const token of data.tokens) {
                if (token.is_final) {
                    newFinals += token.text;
                } else {
                    currentNonFinals += token.text;
                }
            }
            
            if (newFinals) {
                finalTranscript += newFinals;
                finalSpan.innerText = finalTranscript;
            }
            nonfinalSpan.innerText = currentNonFinals;
            
            // Transcript broadcast is handled directly on the server-side to the captions websocket
            
            scrollToBottom(transcriptBox);
        }
    };
    
    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        showError("WebSocket connection error.");
        stopStreaming();
    };
    
    socket.onclose = () => {
        console.log("WebSocket connection closed.");
        stopStreaming();
    };
}

// Access audio inputs and set up mixing nodes
async function startAudioCapture(mode) {
    mediaStreams = [];
    let micStream = null;
    let systemStream = null;
    
    // 1. Capture Microphone Audio if needed
    if (mode === "mic" || mode === "mixed") {
        micStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000
            }
        });
        mediaStreams.push(micStream);
        
        const micTrack = micStream.getAudioTracks()[0];
        console.log(`[Audio Debug] Mic track found - Label: "${micTrack.label}", Active: ${micTrack.active}, Muted: ${micTrack.muted}`);
    }
    
    // 2. Capture System/Display Audio if needed
    let sysAudioStream = null;
    if (mode === "system" || mode === "mixed") {
        systemStream = await navigator.mediaDevices.getDisplayMedia({
            video: true,
            audio: {
                systemAudio: 'include'
            }
        });
        
        const audioTracks = systemStream.getAudioTracks();
        if (audioTracks.length === 0) {
            systemStream.getTracks().forEach(track => track.stop());
            throw new Error("No system audio was shared. Please check the 'Share system audio' checkbox in the Chrome sharing dialog.");
        }
        
        // Ensure the audio track is active and enabled
        audioTracks[0].enabled = true;
        console.log(`[Audio Debug] System audio track found - Label: "${audioTracks[0].label}", Active: ${audioTracks[0].active}, Muted: ${audioTracks[0].muted}`);
        
        // Create an audio-only MediaStream
        sysAudioStream = new MediaStream(audioTracks);
        mediaStreams.push(sysAudioStream);
        
        // Track the original stream to stop video tracks on stop
        mediaStreams.push(systemStream);
        
        // Stop video tracks immediately so we don't process video frames
        systemStream.getVideoTracks().forEach(track => {
            console.log(`[Audio Debug] Stopping video track: ${track.label}`);
            track.stop();
        });
    }
    
    // 3. Initialize Audio Context forcing 16000Hz (downsampling automatically)
    audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000
    });
    
    // 4. Create common ScriptProcessorNode (8192 buffer size, mono for lower CPU overhead)
    processorNode = audioContext.createScriptProcessor(8192, 1, 1);
    
    // 5. Connect input streams to AudioContext graph
    if (micStream) {
        const micSource = audioContext.createMediaStreamSource(micStream);
        micSource.connect(processorNode);
        console.log("[Audio Debug] Connected micSource to processorNode.");
    }
    
    if (sysAudioStream) {
        const sysSource = audioContext.createMediaStreamSource(sysAudioStream);
        sysSource.connect(processorNode);
        console.log("[Audio Debug] Connected sysAudioStream to processorNode.");
    }
    
    // 6. Connect processorNode output destination (to keep it running)
    processorNode.connect(audioContext.destination);
    
    // 7. Implement buffer processing
    processorNode.onaudioprocess = (e) => {
        if (!socket || socket.readyState !== WebSocket.OPEN) return;
        
        const inputBuffer = e.inputBuffer.getChannelData(0);
        
        // Calculate RMS (volume level) for visualizer
        let sum = 0;
        for (let i = 0; i < inputBuffer.length; i++) {
            sum += inputBuffer[i] * inputBuffer[i];
        }
        const rms = Math.sqrt(sum / inputBuffer.length);
        updateVisualizer(rms);
        
        // Convert Float32 samples to 16-bit PCM Signed Le
        const pcmBuffer = new Int16Array(inputBuffer.length);
        for (let i = 0; i < inputBuffer.length; i++) {
            const sample = Math.max(-1, Math.min(1, inputBuffer[i]));
            pcmBuffer[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        
        // Compress 16-bit PCM to 8-bit G.711 mu-law (halves network traffic)
        const mulawBuffer = encodePcm16ToMulaw(pcmBuffer);
        socket.send(mulawBuffer.buffer);
    };
}

// Stop recording and WebSocket streaming
function stopStreaming() {
    setStatus("ready", "Ready to start");
    btnStart.disabled = false;
    btnStop.disabled = true;
    selectSource.disabled = false;
    resetVisualizer();
    
    if (processorNode) {
        processorNode.disconnect();
        processorNode = null;
    }
    
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    
    // Stop all tracks on all media streams (mic, display share)
    mediaStreams.forEach(stream => {
        stream.getTracks().forEach(track => track.stop());
    });
    mediaStreams = [];
    
    if (socket) {
        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
            socket.close();
        }
        socket = null;
    }
}

// Show error messages
function showError(message) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "error-message";
    errorDiv.style.color = "var(--danger)";
    errorDiv.style.margin = "10px 0";
    errorDiv.style.fontSize = "0.95rem";
    errorDiv.style.fontWeight = "600";
    errorDiv.innerText = `⚠️ System Error: ${message}`;
    transcriptBox.appendChild(errorDiv);
    scrollToBottom(transcriptBox);
}

// Launch Native Transparent Window via backend
async function launchFloatWindow() {
    try {
        console.log("Requesting native transparent window launch...");
        const response = await fetch("/launch_float");
        const data = await response.json();
        if (data.status === "success") {
            console.log(`Native transparent float window launched (PID: ${data.pid}).`);
        } else {
            console.error("Failed to launch native float window:", data.message);
        }
    } catch (err) {
        console.error("Error launching native float window:", err);
    }
}

// Event Listeners
btnStart.addEventListener("click", startStreaming);
btnStop.addEventListener("click", stopStreaming);
btnFloat.addEventListener("click", launchFloatWindow);

btnClear.addEventListener("click", () => {
    finalTranscript = "";
    finalSpan.innerText = "";
    nonfinalSpan.innerText = "";
    
    // Tell the server to clear and broadcast clear event
    fetch("/clear").catch(err => console.error("Error clearing server state:", err));
    
    if (placeholderText) {
        placeholderText.style.display = "block";
    }
});

// Spacebar shortcut
document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && e.target === document.body) {
        e.preventDefault();
        if (btnStart.disabled) {
            stopStreaming();
        } else {
            startStreaming();
        }
    }
});

// G.711 mu-law encoder to compress 16-bit signed PCM to 8-bit mu-law
function encodePcm16ToMulaw(pcm16Array) {
    const mulawBuffer = new Uint8Array(pcm16Array.length);
    for (let i = 0; i < pcm16Array.length; i++) {
        let sample = pcm16Array[i];
        let sign = 0;
        
        if (sample < 0) {
            sample = -sample;
            sign = 0x80;
        }
        
        if (sample > 32635) sample = 32635;
        sample += 0x84; // Add bias
        
        let exponent = 0;
        if (sample >= 0x4000) { sample >>= 7; exponent = 7; }
        else if (sample >= 0x2000) { sample >>= 6; exponent = 6; }
        else if (sample >= 0x1000) { sample >>= 5; exponent = 5; }
        else if (sample >= 0x0800) { sample >>= 4; exponent = 4; }
        else if (sample >= 0x0400) { sample >>= 3; exponent = 3; }
        else if (sample >= 0x0200) { sample >>= 2; exponent = 2; }
        else if (sample >= 0x0100) { sample >>= 1; exponent = 1; }
        
        let mantissa = (sample >> 2) & 0x0F;
        mulawBuffer[i] = ~(sign | (exponent << 4) | mantissa) & 0xFF;
    }
    return mulawBuffer;
}

// Connect to dashboard keepalive websocket on load
function connectDashboardKeepalive() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/dashboard_ws`;
    const socket = new WebSocket(wsUrl);
    socket.onclose = () => {
        // Retry connection if disconnected (e.g. server restart)
        setTimeout(connectDashboardKeepalive, 2000);
    };
}
connectDashboardKeepalive();

// Font Size Control Logic
const fontSizeSlider = document.getElementById("font-size-slider");
const fontSizeValue = document.getElementById("font-size-value");

function setFontSize(size) {
    const parsedSize = parseInt(size, 10);
    document.documentElement.style.setProperty("--caption-font-size", `${parsedSize}px`);
    if (fontSizeSlider) fontSizeSlider.value = parsedSize;
    if (fontSizeValue) fontSizeValue.innerText = `${parsedSize}px`;
    localStorage.setItem("caption-font-size", parsedSize);
}

if (fontSizeSlider) {
    fontSizeSlider.addEventListener("input", (e) => {
        setFontSize(e.target.value);
    });
}

// Read saved size on startup (default to 18px for dashboard)
const savedFontSize = localStorage.getItem("caption-font-size") || 18;
setFontSize(savedFontSize);

// Sync with storage changes (e.g. from float window)
window.addEventListener("storage", (e) => {
    if (e.key === "caption-font-size" && e.newValue) {
        setFontSize(e.newValue);
    }
});

