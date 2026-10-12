const http = require('http');
const { exec } = require('child_process');

let currentState = {
  status: 'waiting', // 'waiting' | 'qr' | 'loading' | 'connected'
  qrDataUrl: null,
  percent: 0,
  message: 'Initializing WhatsApp Web Engine...'
};

const sseClients = new Set();

/**
 * Broadcasts status updates to all connected browser popup windows via SSE
 */
function broadcastState(stateUpdate) {
  currentState = { ...currentState, ...stateUpdate };
  const payload = `data: ${JSON.stringify(currentState)}\n\n`;
  for (const client of sseClients) {
    try {
      client.write(payload);
    } catch (e) {
      sseClients.delete(client);
    }
  }
}

/**
 * Automatically triggers the macOS desktop browser window
 */
function openBrowserPopup(url = 'http://localhost:3000') {
  if (process.platform === 'darwin') {
    // Attempt opening in Chrome application mode (popup window without URL bar) if Chrome exists, otherwise default browser
    exec(`open -na "Google Chrome" --args --app="${url}" || open "${url}"`, (err) => {
      if (err) {
        exec(`open "${url}"`);
      }
    });
  } else if (process.platform === 'win32') {
    exec(`start ${url}`);
  } else {
    exec(`xdg-open ${url}`);
  }
}

const HTML_CONTENT = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NotifAI • WhatsApp Link</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
    }

    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #090a0f;
      color: #f1f5f9;
      overflow: hidden;
      position: relative;
    }

    /* Ambient animated blurred gradient background */
    .ambient-bg {
      position: fixed;
      inset: 0;
      z-index: 0;
      overflow: hidden;
      pointer-events: none;
    }

    .orb {
      position: absolute;
      border-radius: 50%;
      filter: blur(100px);
      opacity: 0.45;
      animation: float 14s infinite alternate ease-in-out;
    }

    .orb-1 {
      width: 480px;
      height: 480px;
      background: radial-gradient(circle, #10b981 0%, rgba(16, 185, 129, 0) 70%);
      top: -100px;
      left: -100px;
    }

    .orb-2 {
      width: 520px;
      height: 520px;
      background: radial-gradient(circle, #6366f1 0%, rgba(99, 102, 241, 0) 70%);
      bottom: -120px;
      right: -120px;
      animation-duration: 18s;
      animation-delay: -4s;
    }

    .orb-3 {
      width: 360px;
      height: 360px;
      background: radial-gradient(circle, #06b6d4 0%, rgba(6, 182, 212, 0) 70%);
      top: 40%;
      right: 20%;
      animation-duration: 12s;
      animation-delay: -2s;
    }

    @keyframes float {
      0% { transform: translate(0, 0) scale(1); }
      50% { transform: translate(60px, 40px) scale(1.08); }
      100% { transform: translate(-40px, 70px) scale(0.95); }
    }

    /* Fullscreen Glass Backdrop */
    .glass-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(8, 10, 15, 0.65);
      backdrop-filter: blur(36px);
      -webkit-backdrop-filter: blur(36px);
      z-index: 1;
    }

    /* Main Glass Modal Card */
    .modal-container {
      position: relative;
      z-index: 2;
      width: 90%;
      max-width: 440px;
      background: rgba(18, 22, 34, 0.72);
      backdrop-filter: blur(40px);
      -webkit-backdrop-filter: blur(40px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 28px;
      padding: 36px 32px 32px;
      box-shadow: 
        0 30px 70px -15px rgba(0, 0, 0, 0.75),
        0 0 0 1px rgba(255, 255, 255, 0.05),
        inset 0 1px 1px rgba(255, 255, 255, 0.2);
      text-align: center;
      transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Header & Badge */
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 6px 14px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      background: rgba(16, 185, 129, 0.12);
      color: #34d399;
      border: 1px solid rgba(52, 211, 153, 0.25);
      margin-bottom: 18px;
      transition: all 0.3s ease;
    }

    .badge-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 10px #10b981;
      animation: pulse 1.8s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    h1 {
      font-size: 1.65rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #ffffff;
      margin-bottom: 8px;
    }

    p.subtitle {
      font-size: 0.92rem;
      color: #94a3b8;
      font-family: 'Plus Jakarta Sans', sans-serif;
      margin-bottom: 24px;
      line-height: 1.45;
    }

    /* QR Code Display Wrapper */
    .qr-frame {
      position: relative;
      width: 256px;
      height: 256px;
      margin: 0 auto 24px;
      background: #ffffff;
      border-radius: 20px;
      padding: 12px;
      box-shadow: 
        0 20px 40px -10px rgba(0, 0, 0, 0.6),
        0 0 30px rgba(16, 185, 129, 0.25);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .qr-image {
      width: 100%;
      height: 100%;
      object-fit: contain;
      border-radius: 12px;
      transition: opacity 0.3s ease;
    }

    /* Laser Scanning Beam */
    .scan-beam {
      position: absolute;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, #10b981, #34d399, transparent);
      box-shadow: 0 0 16px 3px rgba(16, 185, 129, 0.8);
      animation: scan 2.6s infinite ease-in-out;
      pointer-events: none;
      z-index: 3;
    }

    @keyframes scan {
      0% { top: 0%; opacity: 0; }
      15% { opacity: 1; }
      85% { opacity: 1; }
      100% { top: 98%; opacity: 0; }
    }

    /* Instructions List */
    .steps {
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 16px;
      padding: 14px 16px;
      text-align: left;
      font-size: 0.85rem;
      color: #cbd5e1;
      font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .step-item {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .step-num {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 700;
      flex-shrink: 0;
    }

    /* Connected State Styles */
    .state-connected {
      display: none;
      animation: zoomIn 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes zoomIn {
      0% { transform: scale(0.85); opacity: 0; }
      100% { transform: scale(1); opacity: 1; }
    }

    .success-icon-wrapper {
      width: 100px;
      height: 100px;
      margin: 0 auto 22px;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .success-circle {
      width: 90px;
      height: 90px;
      border-radius: 50%;
      background: radial-gradient(circle, #10b981 0%, #059669 100%);
      box-shadow: 
        0 0 35px rgba(16, 185, 129, 0.6),
        0 0 60px rgba(16, 185, 129, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      animation: pulseGlow 2.5s infinite;
    }

    @keyframes pulseGlow {
      0%, 100% { box-shadow: 0 0 35px rgba(16, 185, 129, 0.6), 0 0 60px rgba(16, 185, 129, 0.3); }
      50% { box-shadow: 0 0 45px rgba(16, 185, 129, 0.8), 0 0 80px rgba(16, 185, 129, 0.45); }
    }

    .checkmark-svg {
      width: 48px;
      height: 48px;
      stroke: #ffffff;
      stroke-width: 3.5;
      stroke-linecap: round;
      stroke-linejoin: round;
      fill: none;
      stroke-dasharray: 60;
      stroke-dashoffset: 60;
      animation: drawCheck 0.7s 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes drawCheck {
      to { stroke-dashoffset: 0; }
    }

    .connected-title {
      font-size: 1.85rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 10px;
      letter-spacing: -0.02em;
    }

    .connected-desc {
      font-size: 0.95rem;
      color: #94a3b8;
      font-family: 'Plus Jakarta Sans', sans-serif;
      line-height: 1.5;
      margin-bottom: 24px;
    }

    .sync-tag {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 18px;
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.2);
      border-radius: 12px;
      font-size: 0.88rem;
      color: #6ee7b7;
      font-weight: 500;
    }

    /* Spinner for Waiting State */
    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid rgba(255, 255, 255, 0.1);
      border-top-color: #10b981;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>
</head>
<body>
  <!-- Ambient background with fluid glowing gradient orbs -->
  <div class="ambient-bg">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
  </div>

  <!-- Frosted Glass Fullscreen Blur Layer -->
  <div class="glass-backdrop"></div>

  <!-- Central Glassmorphism Modal Card -->
  <main class="modal-container" id="modalCard">
    <!-- QR VIEW STATE -->
    <div id="qrViewState">
      <div class="badge">
        <span class="badge-dot"></span>
        <span id="badgeText">Live Sync Session</span>
      </div>

      <h1 id="titleHeader">Scan QR Code</h1>
      <p class="subtitle" id="subtitleHeader">Open WhatsApp on your phone to link your NotifAI notice synchronization session.</p>

      <div class="qr-frame" id="qrFrame">
        <div class="scan-beam" id="scanBeam"></div>
        <img id="qrImg" class="qr-image" alt="WhatsApp QR Code" style="display: none;" />
        <div id="loadingPlaceholder" style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
          <div class="spinner"></div>
          <span style="font-size: 0.8rem; color: #64748b; font-family: 'Plus Jakarta Sans', sans-serif;">Generating secure QR...</span>
        </div>
      </div>

      <div class="steps">
        <div class="step-item">
          <div class="step-num">1</div>
          <span>Open <strong>WhatsApp</strong> on your mobile phone</span>
        </div>
        <div class="step-item">
          <div class="step-num">2</div>
          <span>Tap <strong>Settings</strong> ➔ <strong>Linked Devices</strong></span>
        </div>
        <div class="step-item">
          <div class="step-num">3</div>
          <span>Tap <strong>Link a Device</strong> and point camera here</span>
        </div>
      </div>
    </div>

    <!-- CONNECTED SUCCESS STATE -->
    <div id="connectedViewState" class="state-connected">
      <div class="success-icon-wrapper">
        <div class="success-circle">
          <svg class="checkmark-svg" viewBox="0 0 24 24">
            <path d="M4 12.5l5.5 5.5L20 7" />
          </svg>
        </div>
      </div>

      <h2 class="connected-title">Connected!</h2>
      <p class="connected-desc">WhatsApp session linked successfully. NotifAI is actively listening for college notices across targeted groups.</p>

      <div class="sync-tag">
        <span style="font-size: 1.1rem;">⚡</span>
        <span>Google Calendar Sync Active</span>
      </div>

      <div style="margin-top: 24px;">
        <button id="relinkBtn" onclick="resetSession()" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #cbd5e1; padding: 10px 18px; border-radius: 12px; font-size: 0.82rem; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 8px;">
          <span>🔄</span>
          <span>Unlink & Generate New QR Code</span>
        </button>
      </div>
    </div>
  </main>

  <script>
    function resetSession() {
      if (confirm("Generate a new WhatsApp QR code? This will reset the current session.")) {
        fetch('/api/reset')
          .then(() => {
            document.body.innerHTML = '<div style="display:flex;height:100vh;align-items:center;justify-content:center;color:#10b981;font-family:sans-serif;font-size:1.2rem;">Generating fresh QR code... Please wait 3 seconds.</div>';
            setTimeout(() => window.location.reload(), 3000);
          })
          .catch(() => window.location.reload());
      }
    }
    // Synthesize instant macOS-style chime using Web Audio API
    function playSuccessChime() {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;
        const ctx = new AudioContext();

        const playTone = (freq, startTime, duration, gainVal) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, startTime);
          
          gain.gain.setValueAtTime(0, startTime);
          gain.gain.linearRampToValueAtTime(gainVal, startTime + 0.03);
          gain.gain.exponentialRampToValueAtTime(0.0001, startTime + duration);

          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(startTime);
          osc.stop(startTime + duration);
        };

        const now = ctx.currentTime;
        playTone(523.25, now, 0.45, 0.25);        // C5
        playTone(659.25, now + 0.08, 0.55, 0.3);  // E5
        playTone(783.99, now + 0.16, 0.65, 0.35); // G5
        playTone(1046.50, now + 0.24, 0.9, 0.4);  // C6
      } catch (e) {
        console.warn('Audio chime unsupported or blocked:', e);
      }
    }

    const qrViewState = document.getElementById('qrViewState');
    const connectedViewState = document.getElementById('connectedViewState');
    const qrImg = document.getElementById('qrImg');
    const loadingPlaceholder = document.getElementById('loadingPlaceholder');
    const scanBeam = document.getElementById('scanBeam');
    const badgeText = document.getElementById('badgeText');
    const subtitleHeader = document.getElementById('subtitleHeader');

    let hasTriggeredSuccess = false;

    function applyState(data) {
      if (!data) return;

      if (data.status === 'connected') {
        if (!hasTriggeredSuccess) {
          hasTriggeredSuccess = true;
          qrViewState.style.display = 'none';
          connectedViewState.style.display = 'block';
          playSuccessChime();
        }
        return;
      }

      if (data.qrDataUrl) {
        qrImg.src = data.qrDataUrl;
        qrImg.style.display = 'block';
        loadingPlaceholder.style.display = 'none';
        scanBeam.style.display = 'block';
        badgeText.textContent = (data.status === 'loading') ? \`Authenticating \${data.percent || 100}%\` : 'Ready to Scan';
      }

      if (data.status === 'loading') {
        subtitleHeader.textContent = data.message || 'Linking WhatsApp session...';
        if (!data.qrDataUrl) {
          badgeText.textContent = \`Authenticating \${data.percent || 100}%\`;
          loadingPlaceholder.style.display = 'flex';
          qrImg.style.display = 'none';
          scanBeam.style.display = 'none';
        }
      }
    }

    // Instant status fetch on page load
    fetch('/api/status')
      .then(res => res.json())
      .then(applyState)
      .catch(console.warn);

    // Reliable 2-second polling fallback
    setInterval(() => {
      if (!hasTriggeredSuccess) {
        fetch('/api/status')
          .then(res => res.json())
          .then(applyState)
          .catch(() => {});
      }
    }, 2000);

    // Connect to Server-Sent Events (SSE) stream for zero-latency status updates
    const evtSource = new EventSource('/events');

    evtSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        applyState(data);
      } catch (err) {
        console.error('SSE parsing error:', err);
      }
    };

    evtSource.onerror = () => {
      badgeText.textContent = 'Syncing...';
    };
  </script>
</body>
</html>`;

/**
 * Initializes and starts the Webhook / QR Code Popup HTTP server.
 * @param {number} port HTTP Port (default 3000)
 */
function startQrServer(port = 3000) {
  const server = http.createServer((req, res) => {
    if (req.url === '/' || req.url === '/qr') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(HTML_CONTENT);
    } else if (req.url === '/events') {
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
      });
      res.write(`data: ${JSON.stringify(currentState)}\n\n`);
      sseClients.add(res);

      req.on('close', () => {
        sseClients.delete(res);
      });
    } else if (req.url === '/api/status') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(currentState));
    } else if (req.url === '/api/reset' || req.url === '/api/logout') {
      console.log('🔄 [QR Reset] Clearing session folder and restarting broker for new QR code...');
      try {
        const fs = require('fs');
        fs.rmSync('./.wwebjs_auth', { recursive: true, force: true });
      } catch (e) {}
      broadcastState({ status: 'waiting', qrDataUrl: null, message: 'Resetting session... generating new QR...' });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'success', message: 'Session reset triggered' }));
      setTimeout(() => {
        process.exit(0);
      }, 500);
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  server.listen(port, () => {
    console.log(`🌐 [QR Popup UI Ready] Listening on http://localhost:${port}`);
  });

  return { server, broadcastState, openBrowserPopup };
}

module.exports = { startQrServer, broadcastState, openBrowserPopup };
