const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const { URL } = require('url');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const { startQrServer, broadcastState, openBrowserPopup } = require('./qr_server');

/**
 * Helper to dispatch JSON payload directly to Python Engine via HTTP Webhook POST
 */
async function sendNoticeToEngine(engineUrl, payload) {
  return new Promise((resolve, reject) => {
    try {
      const parsedUrl = new URL(engineUrl);
      const data = JSON.stringify(payload);
      const options = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80),
        path: parsedUrl.pathname + parsedUrl.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data)
        },
        timeout: 60000
      };

      const req = (parsedUrl.protocol === 'https:' ? https : http).request(options, (res) => {
        let responseBody = '';
        res.on('data', chunk => responseBody += chunk);
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(responseBody);
          } else {
            reject(new Error(`HTTP status ${res.statusCode}: ${responseBody}`));
          }
        });
      });

      req.on('error', (err) => reject(err));
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('HTTP request timed out after 60s'));
      });

      req.write(data);
      req.end();
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Initializes and starts the WhatsApp Listener and Webhook Dispatcher.
 * @param {Object} config Configuration options
 * @param {string} config.engineUrl Target HTTP Webhook URL for Python Engine
 */
async function startBroker(config = {}) {
  const engineUrl = config.engineUrl || process.env.ENGINE_URL || 'http://localhost:5005/process-notice';
  const qrPort = parseInt(config.qrPort || process.env.QR_PORT || '3000', 10);
  
  // Start the interactive glassmorphism QR code popup server
  startQrServer(qrPort);

  let botReadyTimestamp = null;
  const chatCache = new Map(); // Memory cache for chat metadata (0ms fast lookups)
  const processedMessageIds = new Set(); // Deduplication set to prevent double processing

  // Group filtering settings
  const allowedGroupsEnv = process.env.ALLOWED_GROUPS || '';
  const allowedGroups = allowedGroupsEnv
    .split(',')
    .map(g => g.trim())
    .filter(g => g.length > 0);
  const onlyGroups = process.env.ONLY_GROUPS === 'true' || allowedGroups.length > 0;

  console.log(`[Broker] Direct HTTP Webhook configured for: ${engineUrl}`);
  if (allowedGroups.length > 0) {
    console.log(`[Broker Configuration] Target group filters: ${JSON.stringify(allowedGroups)}`);
  } else if (onlyGroups) {
    console.log(`[Broker Configuration] Mode: Group messages only (private chats ignored).`);
  } else {
    console.log(`[Broker Configuration] Mode: All chat messages (statuses ignored).`);
  }

  // Configure Puppeteer options with Mac / Linux fallbacks and Anti-Sleep Chromium flags
  const macChromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  let executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;

  if (!executablePath && process.platform === 'darwin' && fs.existsSync(macChromePath)) {
    executablePath = macChromePath;
  }

  const puppeteerArgs = {
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--no-first-run',
      '--no-zygote',
      '--disable-gpu',
      '--disable-extensions',
      '--disable-default-apps',
      '--disable-sync',
      '--disable-translate',
      '--disable-features=Translate,BackForwardCache,AcceptCHFrame,AvoidUnnecessaryBeforeUnloadCheckSync',
      '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
      '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows',
      '--disable-renderer-backgrounding',
      '--disable-ipc-flooding-protection'
    ]
  };

  if (executablePath) {
    puppeteerArgs.executablePath = executablePath;
  }

  // Remove stale Chromium lock files if left behind by container recreation
  try {
    const sessionDir = path.resolve('./.wwebjs_auth/session');
    const lockFiles = ['SingletonLock', 'SingletonSocket', 'SingletonCookie', 'DevToolsActivePort'];
    for (const file of lockFiles) {
      const lockPath = path.join(sessionDir, file);
      try {
        fs.unlinkSync(lockPath);
      } catch (e) {}
      try {
        fs.rmSync(lockPath, { force: true, recursive: true });
      } catch (e) {}
    }
  } catch (e) {}

  const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    webVersionCache: {
      type: 'remote',
      remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.3000.1050029226-alpha.html'
    },
    puppeteer: puppeteerArgs
  });


  let popupTriggered = false;

  client.on('qr', async (qr) => {
    console.log('\n====================================================================');
    console.log('📱 SCAN THIS QR CODE WITH WHATSAPP ON YOUR PHONE TO LOG IN:');
    console.log(`🌐 Interactive Frosted Glass Popup: http://localhost:${qrPort}`);
    console.log('====================================================================\n');
    qrcode.generate(qr, { small: true });

    try {
      const qrDataUrl = await QRCode.toDataURL(qr, { margin: 2, scale: 8 });
      broadcastState({ status: 'qr', qrDataUrl });

      if (!popupTriggered) {
        popupTriggered = true;
        openBrowserPopup(`http://localhost:${qrPort}`);
      }
    } catch (err) {
      console.warn('Could not generate QR Data URL for web popup:', err.message);
    }
  });

  client.on('loading_screen', (percent, message) => {
    console.log(`⏳ [WhatsApp Loading] ${percent}% - ${message}`);
    broadcastState({ status: 'loading', percent, message });
  });

  client.on('change_state', (state) => {
    console.log(`🔄 [WhatsApp State Change] ${state}`);
  });

  client.on('authenticated', () => {
    console.log('✅ [WhatsApp] Authentication successful! Linking session...');
    broadcastState({ status: 'connected', message: 'Authentication successful! Linking session...' });
  });

  client.on('auth_failure', (msg) => {
    console.error('❌ [WhatsApp] Authentication failure:', msg);
    console.log('🧹 Purging corrupted local session auth folder...');
    try {
      fs.rmSync('./.wwebjs_auth', { recursive: true, force: true });
    } catch (e) {}
  });

  // Ultra-fast in-memory chat name resolver (0ms)
  function getChatNameFast(msg, targetJid) {
    const key = targetJid || msg.from;
    if (key && chatCache.has(key)) {
      return chatCache.get(key);
    }
    // Direct synchronous metadata extraction from WhatsApp Web internal packet
    const directName = msg._data?.chat?.name || msg._data?.name || msg._data?.subject || msg._data?.formattedTitle;
    if (directName) {
      if (key) chatCache.set(key, directName.trim());
      return directName.trim();
    }
    return null;
  }

  // Resilient Voice Note Media Downloader with Exponential Backoff & In-Memory Puppeteer Recovery
  async function downloadVoiceMediaRobust(msg, maxAttempts = 4) {
    let lastError = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        if (attempt === 1) {
          // Allow WhatsApp Web 600ms grace period to negotiate media keys on new arrival
          await new Promise(r => setTimeout(r, 600));
        } else {
          // Refresh message object state if supported
          if (typeof msg.reload === 'function') {
            await msg.reload().catch(() => {});
          }
          await new Promise(r => setTimeout(r, 800 * attempt));
        }

        const media = await msg.downloadMedia();
        if (media && media.data) {
          return media;
        }
      } catch (err) {
        lastError = err;
        console.warn(`⏳ [Voice Download] Attempt ${attempt}/${maxAttempts} failed (${err.message || err}). Retrying...`);
      }
    }

    // Direct Browser Context Extraction Fallback
    try {
      console.log('🔄 [Voice Download] Running direct in-browser decryption fallback...');
      const fallbackMedia = await client.pupPage.evaluate(async (rawId, serializedId) => {
        try {
          const MsgColl = window.require('WAWebCollections')?.Msg;
          if (!MsgColl) return null;

          let target = MsgColl.get(serializedId) || (rawId ? MsgColl.get(rawId) : null);
          if (!target && MsgColl.getMessagesById) {
            const lookupKeys = [serializedId];
            if (rawId) lookupKeys.push(rawId);
            const res = await MsgColl.getMessagesById(lookupKeys).catch(() => null);
            target = res?.messages?.[0];
          }
          if (!target && MsgColl.getModelsArray) {
            const all = MsgColl.getModelsArray();
            target = all.find(m => m.id?._serialized === serializedId || (rawId && m.id?.id === rawId?.id));
          }
          if (!target) return null;

          if (target.mediaData && target.mediaData.mediaStage !== 'RESOLVED' && typeof target.downloadMedia === 'function') {
            try {
              await target.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1 });
            } catch (e) {}

            for (let i = 0; i < 10; i++) {
              if (target.mediaData?.mediaStage === 'RESOLVED') break;
              await new Promise(r => setTimeout(r, 200));
            }
          }

          const dlMgr = window.require('WAWebDownloadManager')?.downloadManager;
          if (!dlMgr) return null;

          const qpl = { addAnnotations: () => qpl, addPoint: () => qpl };
          const directPath = target.directPath || target.mediaData?.directPath;
          const encFilehash = target.encFilehash || target.mediaData?.encFilehash;
          const filehash = target.filehash || target.mediaData?.filehash;
          const mediaKey = target.mediaKey || target.mediaData?.mediaKey;
          const mediaKeyTimestamp = target.mediaKeyTimestamp || target.mediaData?.mediaKeyTimestamp;

          if (!directPath || !mediaKey) return null;

          const decryptedMedia = await dlMgr.downloadAndMaybeDecrypt({
            directPath,
            encFilehash,
            filehash,
            mediaKey,
            mediaKeyTimestamp,
            type: target.type,
            signal: new AbortController().signal,
            downloadQpl: qpl,
          });

          if (!decryptedMedia) return null;
          const data = await window.WWebJS.arrayBufferToBase64Async(decryptedMedia);
          return {
            data,
            mimetype: target.mimetype || target.mediaData?.mimetype || 'audio/ogg'
          };
        } catch (e) {
          return null;
        }
      }, msg.id, msg.id?._serialized);

      if (fallbackMedia && fallbackMedia.data) {
        return fallbackMedia;
      }
    } catch (fallbackErr) {
      console.warn('⚠️ [Voice Download Fallback Error]:', fallbackErr.message);
    }

    return null;
  }

  // Ultra-fast message handler
  const handleMessage = async (msg, isHistoricalBatch = false) => {
    if (!msg) return;

    const isVoice = Boolean(msg.hasMedia && (msg.type === 'ptt' || msg.type === 'audio'));
    const messageText = (msg.body || '').trim();

    if (!messageText && !isVoice) {
      return;
    }

    // Deduplicate message handling
    const msgId = msg.id?._serialized || `${msg.from}_${msg.timestamp}`;
    if (processedMessageIds.has(msgId)) {
      return;
    }

    // INSTANT STATUS FILTER: Ignore WhatsApp Statuses / System Broadcasts
    if (
      msg.from === 'status@broadcast' ||
      msg.isStatus ||
      (msg.from && msg.from.includes('broadcast')) ||
      msg.type === 'status' ||
      msg.type === 'e2e_notification' ||
      msg.type === 'notification_template'
    ) {
      return;
    }

    // Determine Group JID (Check msg.from, msg.to, and msg.id.remote for self-sent group messages)
    const targetJid = (msg.from && msg.from.endsWith('@g.us')) ? msg.from :
                      ((msg.to && msg.to.endsWith('@g.us')) ? msg.to :
                      ((msg.id && msg.id.remote && msg.id.remote.endsWith('@g.us')) ? msg.id.remote : null));
    const isGroup = Boolean(targetJid) || msg.isGroup || false;

    // FAST GROUP CHECK
    if (onlyGroups && !isGroup) {
      return; // Skip non-group chats
    }

    try {
      // 0ms instant chat name lookup without waiting on Puppeteer CDP
      let chatName = getChatNameFast(msg, targetJid);
      if (!chatName) {
        const chat = await msg.getChat().catch(() => null);
        chatName = chat?.name ? chat.name.trim() : (isGroup ? 'Group Chat' : 'Private Chat');
        if (targetJid || msg.from) chatCache.set(targetJid || msg.from, chatName);
      }

      // TARGET GROUP MATCHING (Substring & Exact Matching)
      if (allowedGroups.length > 0) {
        const chatNameLower = chatName.toLowerCase();

        const isMatchedGroup = allowedGroups.some(target => {
          const targetLower = target.trim().toLowerCase();
          return chatNameLower.includes(targetLower) || chatName === target.trim();
        });

        if (!isMatchedGroup) {
          console.log(`⚠️ [Broker Filter] Skipped message from chat "${chatName}" (Allowed groups: ${JSON.stringify(allowedGroups)})`);
          return; // Ignore non-target groups
        }
      }

      // Mark message as processed
      processedMessageIds.add(msgId);

      // Fast sender name resolution from direct properties
      const senderName = msg._data?.notifyName || msg._data?.pushname || msg._data?.author || msg.author || (msg.fromMe ? 'Me (Self)' : msg.from);

      let audioBase64 = null;
      let audioMime = null;

      if (isVoice) {
        console.log(`🎙️ [Voice Note Detected] Downloading audio message from "${chatName}" (${senderName})...`);
        try {
          const media = await downloadVoiceMediaRobust(msg);
          if (media && media.data) {
            audioBase64 = media.data;
            audioMime = media.mimetype || 'audio/ogg';
            console.log(`🎙️ [Voice Note Downloaded] ${audioMime} (${Math.round((audioBase64.length * 0.75) / 1024)} KB)`);
          } else {
            console.warn(`⚠️ [Voice Note Warning] Audio media could not be resolved from WhatsApp.`);
          }
        } catch (mediaErr) {
          console.warn(`⚠️ Failed to download voice media: ${mediaErr.message || mediaErr}`);
        }
      }

      // If it is a voice note but audio download failed and there is no accompanying text, do not dispatch blank payload
      if (isVoice && !audioBase64 && !messageText) {
        console.warn(`⚠️ [Voice Note Skipped] No audio or text available to dispatch to engine.`);
        return;
      }

      const payload = {
        message_id: msgId,
        from: targetJid || msg.from,
        sender_name: senderName,
        chat_name: chatName,
        is_group: isGroup,
        text: messageText,
        is_voice: isVoice,
        audio_base64: audioBase64,
        audio_mimetype: audioMime,
        timestamp: msg.timestamp ? new Date(msg.timestamp * 1000).toISOString() : new Date().toISOString()
      };

      // Non-blocking fire-and-forget dispatch for zero-latency execution
      sendNoticeToEngine(engineUrl, payload)
        .then(() => {
          const logPrefix = isVoice ? '🎙️ [Live Voice Notice]' : (isHistoricalBatch ? '📂 [Past History Notice]' : '⚡ [Live Realtime Notice]');
          const textPreview = isVoice ? `Voice note audio forwarded to engine for Sarvam ASR` : `"${payload.text.substring(0, 60)}${payload.text.length > 60 ? '...' : ''}"`;
          console.log(`${logPrefix} Dispatched notice to engine from "${payload.chat_name}" (${payload.sender_name}): ${textPreview}`);
        })
        .catch((postErr) => {
          console.error(`❌ [Broker] Failed to dispatch notice to engine (${engineUrl}):`, postErr.message);
        });
    } catch (err) {
      console.error('❌ [Broker] Error processing message:', err);
    }
  };


  // Ingest recent past messages from target groups upon startup
  async function processTargetedGroupHistory() {
    if (allowedGroups.length === 0) return;

    console.log(`🔍 [History Ingestion] Fetching recent chat history for target groups: ${JSON.stringify(allowedGroups)}...`);
    try {
      const chats = await client.getChats().catch(() => []);
      for (const chat of chats) {
        if (!chat || !chat.isGroup) continue;

        const chatNameLower = (chat.name || '').toLowerCase();
        const isMatchedGroup = allowedGroups.some(target => {
          const targetLower = target.trim().toLowerCase();
          return chatNameLower.includes(targetLower) || chat.name.trim() === target.trim();
        });

        if (!isMatchedGroup) continue;

        console.log(`📂 [History Ingestion] Reading past messages from group: "${chat.name}"...`);
        const recentMessages = await chat.fetchMessages({ limit: 50 }).catch(() => []);

        for (const pastMsg of recentMessages) {
          await handleMessage(pastMsg, true);
        }
      }
      console.log(`✅ [History Ingestion Complete] Targeted group history parsed & queued!`);
    } catch (err) {
      console.error(`❌ Error reading target group history:`, err);
    }
  }

  client.on('ready', async () => {
    botReadyTimestamp = Math.floor(Date.now() / 1000);
    console.log(`🚀 [WhatsApp Listener Active] Linked & Ready at ${new Date(botReadyTimestamp * 1000).toISOString()}!`);
    broadcastState({ status: 'connected', message: 'WhatsApp Linked & Active!' });

    // Pre-cache all chat names on boot for 0ms instant synchronous resolution
    client.getChats().then(chats => {
      for (const c of chats) {
        if (c.id?._serialized) chatCache.set(c.id._serialized, c.name || c.formattedTitle || 'Group Chat');
      }
      console.log(`⚡ [Cache Warmed] Pre-cached ${chatCache.size} active chats for 0ms instant name resolution.`);
    }).catch(() => {});

    // Read recent past messages for targeted groups (e.g. Srijan) to extract dates
    await processTargetedGroupHistory();
  });

  client.on('message', (msg) => handleMessage(msg, false));
  client.on('message_create', (msg) => handleMessage(msg, false));

  client.on('disconnected', (reason) => {
    console.warn('⚠️ [WhatsApp] Client disconnected:', reason);
    broadcastState({ status: 'waiting', qrDataUrl: null, message: `Disconnected: ${reason}.` });
  });

  client.initialize().catch(err => {
    console.error('❌ [WhatsApp Init Error]:', err.message);
    if (err.message && err.message.includes('Execution context was destroyed')) {
      console.log('🧹 Purging corrupted session and auto-restarting for fresh QR code...');
      try {
        fs.rmSync('./.wwebjs_auth', { recursive: true, force: true });
      } catch (e) {}
      setTimeout(() => process.exit(1), 500);
    }
  });
}

module.exports = { startBroker };
