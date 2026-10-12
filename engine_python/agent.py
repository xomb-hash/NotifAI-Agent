# =====================================================================
#   PLATFORM FOUNDATIONS & CONTEXT MANAGEMENT
#   SYSTEM TELEMETRY CONFIGURATION
# C++ equivalents: #include <iostream>, <vector>, <string>, <fstream>, <exception>
# =====================================================================
import os
import sys
import time
import datetime
import json
import logging
import subprocess
import threading
import re
import base64
import requests
from typing import List
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

try:
    from langchain_sarvam import ChatSarvam
except ImportError:
    ChatSarvam = None

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Injects security credentials and tokens from local hidden environmental variables (.env)
load_dotenv(override=True)

# OAuth 2.0 Access Scopes: Strictly limits the agent's write permission boundary to calendar events only
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# =====================================================================
# TELEMETRY CONFIGURATOR
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)  


# =====================================================================
# CUSTOM PIPELINE BOUNDARY EXCEPTIONS
# =====================================================================
class IngestionError(Exception):
    """Raised when parsing, loading, or reading the local Telegram JSON log fails.""" 
    pass

class AISchemaValidationError(Exception):
    """Raised when the LLM response fails to parse or violates Pydantic structural boundaries."""
    pass


# =====================================================================
#   DATA VALIDATION LAYER (PYDANTIC SCHEMAS)
# =====================================================================
class CollegeEvent(BaseModel):
    """
    Core Structural Entity for actionable events, notices, and reminders.
    """
    is_important_notice: bool = Field(
        description="True for any actionable reminder, to-do, event-related task, call/meeting request (e.g. 'call event manager', 'meet coordinator'), academic notice, exam, test, deadline, fest, workshop, or urgent announcement. False ONLY for pure conversational chatter like 'ok', 'gm', 'lol', 'thanks'."
    )
    title: str = Field(description="A concise, actionable title for the reminder/event (e.g., 'Call Event Manager', 'Midsem Exam in Hall A').")
    date: str = Field(description="The target event date in absolute format YYYY-MM-DD. If relative ('today', 'tomorrow'), resolve using today's anchor date. Default to today's date if unspecified.")
    time: str = Field(description="The target event timestamp in 24-hour HH:MM format. Default to '10:00' if unspecified.")
    description: str = Field(description="Context snippet, location flags, room details, or original message texts.")

class CollegeEventList(BaseModel):
    """Array structural collection wrapper mapping directly to std::vector<CollegeEvent>."""
    events: List[CollegeEvent] = Field(description="Array listing of individual valid parsed events and reminders discovered in text payloads.")


# =====================================================================
#  LANGCHAIN PIPELINE FACTORY WITH MODEL FALLBACKS
# =====================================================================
FALLBACK_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    "gemini-3.5-flash-lite",
    "gemini-1.5-flash",
    "gemini-3.8-flash"
]

_COMPILED_CHAINS = {}

def get_chain_for_model(model_name: str):
    """Retrieves or builds a cached structured LCEL chain for zero-latency execution."""
    if model_name not in _COMPILED_CHAINS:
        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.0, max_retries=0)
        structured_llm = llm.with_structured_output(CollegeEventList)
        actual_today = datetime.date.today().strftime("%A, %B %d, %Y")
        today_iso = datetime.date.today().strftime("%Y-%m-%d")

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"""You are NotifAI, an intelligent real-time executive assistant analyzing college & club group chats.
Extract all actionable events, task reminders, coordination notices, and academic announcements into structured calendar items.
Today's anchor date is explicitly {actual_today} ({today_iso}).

Rules:
1. ANY task or reminder (e.g. "Have to call event manager today", "Bring project files tomorrow", "Meet at lab", "Urgent meeting with team", "Submit assignment", "Exam on Friday") is IMPORTANT (is_important_notice = True).
2. If relative words like "today", "now", or "tonight" are used, or if no date is given for a task reminder, set date to {today_iso}.
3. If "tomorrow" is used, calculate tomorrow's date based on {today_iso}.
4. Only classify as is_important_notice = False if the text is pure casual chatter (e.g., "cool", "gm", "thanks", "ok", "see you").
5. Create a clear, actionable summary title (e.g. "Call Event Manager").
"""),
            ("user", "Analyze this chat message stream:\n\n{message}")
        ])
        _COMPILED_CHAINS[model_name] = prompt_template | structured_llm
    return _COMPILED_CHAINS[model_name]


_SARVAM_SESSION = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
_SARVAM_SESSION.mount('https://', _adapter)
_SARVAM_SESSION.mount('http://', _adapter)

# =====================================================================
#  SARVAM AI SPEECH-TO-TEXT (VOICE NOTE ASR PIPELINE)
# =====================================================================
def transcribe_audio_with_sarvam(audio_base64: str, audio_mimetype: str = "audio/ogg") -> str:
    """
    Sends WhatsApp audio voice notes to Sarvam Saaras Speech-to-Text API.
    Natively supports Indic, Hinglish, and English audio.
    """
    sarvam_api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not sarvam_api_key:
        logging.warning("⚠️ SARVAM_API_KEY is not set in engine_python/.env. Cannot transcribe voice note.")
        return ""

    try:
        base_url = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai").strip().rstrip("/")
        url = f"{base_url}/speech-to-text"
        headers = {
            "api-subscription-key": sarvam_api_key
        }

        file_ext = "ogg"
        if "wav" in audio_mimetype:
            file_ext = "wav"
        elif "mp3" in audio_mimetype:
            file_ext = "mp3"
        elif "mp4" in audio_mimetype or "m4a" in audio_mimetype:
            file_ext = "m4a"

        audio_bytes = base64.b64decode(audio_base64)
        files = {
            "file": (f"voice_note.{file_ext}", audio_bytes, audio_mimetype)
        }
        data = {
            "model": os.getenv("SARVAM_STT_MODEL", "saaras:v4"),
            "mode": os.getenv("SARVAM_STT_MODE", "translate")
        }

        logging.info(f"🎙️ [Sarvam Saaras ASR] Converting {len(audio_bytes)} bytes voice note ({audio_mimetype}) to English text (mode=translate)...")
        response = _SARVAM_SESSION.post(url, headers=headers, files=files, data=data, timeout=25)

        if response.status_code == 200:
            result = response.json()
            transcript = result.get("transcript", "").strip()
            detected_lang = result.get("language_code", "Indic")
            logging.info(f"🎙️ [Sarvam Saaras Voice -> English Output] (Detected Lang: {detected_lang}): \"{transcript}\"")
            return transcript
        else:
            logging.error(f"❌ Sarvam STT API Error ({response.status_code}): {response.text}")
            return ""
    except Exception as e:
        logging.error(f"❌ Failed to transcribe audio with Sarvam ASR: {e}")
        return ""


# =====================================================================
#  SARVAM AI INDIC LLM LANGCHAIN LCEL PIPELINE (indus.sarvam.ai)
# =====================================================================
def get_chain_for_sarvam(model_name: str = None):
    """
    Constructs native LangChain LCEL pipeline backed by Sarvam AI Indus model (e.g. sarvam-105b).
    Uses ChatSarvam (or ChatOpenAI fallback) connected to Sarvam's API with Pydantic structured output.
    """
    sarvam_api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not sarvam_api_key:
        raise ValueError("SARVAM_API_KEY is not configured in .env.")

    if not model_name:
        model_name = os.getenv("SARVAM_MODEL", "sarvam-105b").strip()

    base_url = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai/v1").strip().rstrip("/")
    if not base_url.endswith("/v1") and not base_url.endswith("/v2"):
        base_url = f"{base_url}/v1"

    cache_key = f"sarvam_langchain_{model_name}"
    if cache_key not in _COMPILED_CHAINS:
        if ChatSarvam is not None:
            try:
                llm = ChatSarvam(
                    model_name=model_name,
                    sarvam_api_key=sarvam_api_key,
                    max_tokens=350,
                    temperature=0.0
                )
            except Exception as sarvam_init_err:
                logging.warning(f"ChatSarvam native init note: {sarvam_init_err}. Engaging ChatOpenAI wrapper...")
                llm = ChatOpenAI(
                    model=model_name,
                    base_url=base_url,
                    api_key=sarvam_api_key,
                    default_headers={"api-subscription-key": sarvam_api_key},
                    temperature=0.0,
                    max_tokens=350,
                    timeout=20.0
                )
        else:
            llm = ChatOpenAI(
                model=model_name,
                base_url=base_url,
                api_key=sarvam_api_key,
                default_headers={"api-subscription-key": sarvam_api_key},
                temperature=0.0,
                max_tokens=350,
                timeout=20.0
            )


        structured_llm = llm.with_structured_output(CollegeEventList)
        actual_today = datetime.date.today().strftime("%A, %B %d, %Y")
        today_iso = datetime.date.today().strftime("%Y-%m-%d")

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"""You are NotifAI, an intelligent real-time executive assistant analyzing college & club group chats in India.
Extract all actionable events, task reminders, coordination notices, exams, deadlines, and announcements into structured calendar items.
You understand English, Hindi, and colloquial Hinglish (e.g., "kal 11 baje lab mein aana hai", "sabko attend karna hai", "auditorium mein submit karo").
Today's anchor date is explicitly {actual_today} ({today_iso}).

Rules:
1. ANY task, meeting, or reminder (in English, Hindi, or Hinglish) is IMPORTANT (is_important_notice = True).
2. Date parsing:
   - "today", "aaj", "now", "tonight" -> {today_iso}
   - "tomorrow", "kal", "subah kal" -> calculate tomorrow's date based on {today_iso}.
   - If no date is given for a task reminder, default to {today_iso}.
3. Time parsing:
   - Convert times (e.g. "11:30 AM", "shaam 5 baje", "10 baje") to 24-hour format HH:MM (e.g. "11:30", "17:00", "10:00"). Default to "10:00" if unspecified.
4. Only classify as is_important_notice = False if the text is pure casual chatter (e.g., "cool", "gm", "thanks", "ok", "see you").
5. Create a clear, actionable summary title in English (e.g. "Project Presentation in Lab", "Call Event Manager").
"""),
            ("user", "Analyze this chat message stream:\n\n{message}")
        ])
        _COMPILED_CHAINS[cache_key] = prompt_template | structured_llm

    return _COMPILED_CHAINS[cache_key]


def extract_with_sarvam_llm(user_input: str) -> CollegeEventList:
    """
    Executes LangChain LCEL extraction using Sarvam AI Indic model.
    Falls back to direct REST JSON schema validation if needed.
    """
    try:
        model_name = os.getenv("SARVAM_MODEL", "sarvam-105b").strip()
        logging.info(f"Routing text payload to Sarvam AI LangChain LCEL pipeline ('{model_name}')...")
        chain = get_chain_for_sarvam(model_name)
        res = chain.invoke({"message": user_input})
        if res and hasattr(res, 'events'):
            return res
    except Exception as lc_err:
        logging.warning(f"Sarvam LangChain LCEL invocation notice: {lc_err}. Engaging REST fallback...")

    # Fallback to direct REST call with Pydantic validation
    sarvam_api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not sarvam_api_key:
        raise ValueError("SARVAM_API_KEY is not configured in .env.")

    model_name = os.getenv("SARVAM_MODEL", "sarvam-105b").strip()
    base_url = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai").strip().rstrip("/")
    if "chat/completions" in base_url:
        url = base_url
    elif "v1" in base_url or "v2" in base_url:
        url = f"{base_url}/chat/completions"
    else:
        url = f"{base_url}/v1/chat/completions"

    actual_today = datetime.date.today().strftime("%A, %B %d, %Y")
    today_iso = datetime.date.today().strftime("%Y-%m-%d")

    system_prompt = f"""You are NotifAI, an intelligent real-time executive assistant analyzing college and workplace group chats in India.
You understand English, Hindi, and colloquial Hinglish (e.g., "kal 11 baje lab mein aana hai", "sabko attend karna hai", "auditorium mein submit karo").
Extract all actionable events, task reminders, coordination notices, exams, deadlines, and announcements into a structured JSON object.

Today's anchor date is explicitly {actual_today} ({today_iso}).

Rules:
1. ANY task, meeting, or reminder (in English, Hindi, or Hinglish) is IMPORTANT (is_important_notice = true).
   Examples: "Have to call event manager today", "Kal subah 10:30 baje lab mein meeting hai", "Submit assignment by Friday".
2. Date parsing:
   - "today", "aaj", "now", "tonight" -> {today_iso}
   - "tomorrow", "kal", "subah kal" -> calculate tomorrow's date based on {today_iso}.
   - If no date is given for a task reminder, default to {today_iso}.
3. Time parsing:
   - Convert times (e.g. "11:30 AM", "shaam 5 baje", "10 baje") to 24-hour format HH:MM (e.g. "11:30", "17:00", "10:00"). Default to "10:00" if unspecified.
4. Only classify as is_important_notice = false if the text is pure casual chatter (e.g., "ok", "gm", "thanks", "lol", "kaisa hai").
5. Create a concise, actionable summary title in English (e.g., "Project Presentation in Lab", "Call Event Manager").

Output ONLY a valid JSON object matching this schema without markdown fences:
{{
  "events": [
    {{
      "is_important_notice": true,
      "title": "Clear Event Title",
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "description": "Original context and location details"
    }}
  ]
}}
"""

    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": sarvam_api_key,
        "Authorization": f"Bearer {sarvam_api_key}"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this chat notice/message:\n\n{user_input}"}
        ],
        "temperature": 0.0,
        "max_tokens": 350
    }

    logging.info(f"Routing text payload to Sarvam AI REST API fallback ('{model_name}')...")
    response = _SARVAM_SESSION.post(url, headers=headers, json=payload, timeout=20)

    if response.status_code != 200:
        raise RuntimeError(f"Sarvam LLM API returned {response.status_code}: {response.text}")

    res_json = response.json()
    content = res_json.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        content = content.strip()

    parsed_data = json.loads(content)
    return CollegeEventList.model_validate(parsed_data)



# =====================================================================
#  SECURE OAUTH 2.0 PROTOCOL ENGINE & STATE HANDSHAKE
# =====================================================================

_CALENDAR_SERVICE = None

def get_calendar_service():
    """
    Coordinates state authentication and returns cached Google Calendar API client instance (0ms lookup).
    """
    global _CALENDAR_SERVICE
    if _CALENDAR_SERVICE is not None:
        return _CALENDAR_SERVICE

    base_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(base_dir, 'token.json')
    creds_path = os.path.join(base_dir, 'langcredentials.json')

    creds = None
    
    # Check for warm credential cache on local disk
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logging.info("Access token expired. Executing silent token refresh flow (Silent Healing)...")
                creds.refresh(Request())
            except Exception as e:
                logging.warning(f"Silent refresh failed: {e}. Purging corrupted local token cache...")
                if os.path.exists(token_path):
                    os.remove(token_path)
                creds = None
                
        if not creds:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"Google OAuth application signature config '{creds_path}' is missing.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
    _CALENDAR_SERVICE = build('calendar', 'v3', credentials=creds, cache_discovery=False)
    return _CALENDAR_SERVICE


# =====================================================================
# SYSTEM NOTIFICATION BELL & SOUND ALERTS
# =====================================================================
def trigger_notification_bell(title: str, date: str, time_str: str):
    """Triggers an audio bell chime and system notification popup when an event is added."""
    try:
        # Terminal ASCII Bell Chime
        sys.stdout.write('\a')
        sys.stdout.flush()

        # macOS System Banner Notification + Bell Chime Sound ("Glass")
        msg_body = f"Scheduled: {title} on {date} at {time_str}"
        apple_script = f'display notification "{msg_body}" with title "🔔 NotifAI Notice Added" sound name "Glass"'
        subprocess.run(['osascript', '-e', apple_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"🔔 [Notification Bell] Alert triggered for '{title}'!")
    except Exception as e:
        logging.debug(f"Notification bell trigger exception: {e}")


# =====================================================================
# GOOGLE CALENDAR RESTFUL API SCHEMA INTEGRATION
# =====================================================================
def add_to_google_calendar(event_data: CollegeEvent):
    """Formats structural event maps and executes API POST calls with multi-tier notification reminders."""
    try:
        service = get_calendar_service()
        try:
            start_dt = datetime.datetime.strptime(f"{event_data.date} {event_data.time}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + datetime.timedelta(hours=1)
            start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:00")
            end_iso = end_dt.strftime("%Y-%m-%dT%H:%M:00")
        except Exception:
            start_iso = f"{event_data.date}T{event_data.time}:00"
            end_iso = f"{event_data.date}T23:59:59"

        event_payload = {
            'summary': event_data.title,
            'description': f"{event_data.description}\n\n[Synchronized via NotifAI Client Agent]",
            'start': {'dateTime': start_iso, 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_iso, 'timeZone': 'Asia/Kolkata'},
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10},    # 10-Minute pop-up alarm
                    {'method': 'popup', 'minutes': 30},    # 30-Minute pop-up alarm
                    {'method': 'popup', 'minutes': 1440},  # 24-Hour pop-up alarm
                ],
            },
        }

        response = service.events().insert(calendarId='primary', body=event_payload).execute()
        logging.info(f"Successfully posted schedule event! Verification URL: {response.get('htmlLink')}")
        
        # Trigger Notification Bell & Chime
        trigger_notification_bell(event_data.title, event_data.date, event_data.time)
        
    except Exception as e:
        raise RuntimeError(f"Google REST network submission drop: {e}")


# =====================================================================
# DATA INGESTION PIPELINE (LOCAL TEXT BATCH COMPRESSION)
# =====================================================================
def parse_local_telegram_logs(file_path: str, limit: int = 50) -> str:
    """Ingests raw backup JSON payloads, drops structural noise, and compresses rich arrays down into context-dense strings."""
    if not os.path.exists(file_path):
        raise IngestionError(f"No valid local target file discovered matching path: {file_path}")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
    except json.JSONDecodeError as e:
        raise IngestionError(f"Target log backup payload file structure is corrupted: {e}")
    except OSError as e:
        raise IngestionError(f"Operating system environment rejected file stream tracking: {e}")
        
    raw_messages = log_data.get('messages', [])
    processed_slices = []
    
    for record in raw_messages[-limit:]:
        if record.get('type') == 'message' and record.get('text') != "":
            timestamp = record.get('date', '')
            origin_sender = record.get('from', 'Anonymous Node')
            unstructured_text = record.get('text')
            
            if isinstance(unstructured_text, list):
                fragment_buffer = []
                for node in unstructured_text:
                    if isinstance(node, dict):
                        fragment_buffer.append(node.get('text', ''))
                    else:
                        fragment_buffer.append(str(node))
                unstructured_text = "".join(fragment_buffer)
                
            if unstructured_text and unstructured_text.strip():
                processed_slices.append(f"[{timestamp}] {origin_sender}: {unstructured_text.strip()}")
                
    return "\n".join(processed_slices)


# =====================================================================
# CORE PIPELINE PROCESSOR WITH SARVAM AI & MODEL FALLBACK
# =====================================================================
def process_notice_payload(user_input: str = "", audio_base64: str = None, audio_mimetype: str = "audio/ogg"):
    """
    Executes notice extraction with Sarvam AI (LLM & Voice ASR), with multi-model fallback.
    """
    # Step 1: Voice transcription if audio payload is present
    if audio_base64:
        logging.info("🎙️ [Voice Pipeline Active] Processing WhatsApp voice note with Sarvam Saaras model (Voice -> English Translation)...")
        transcript = transcribe_audio_with_sarvam(audio_base64, audio_mimetype)
        if transcript:
            user_input = transcript
            logging.info(f"🎙️ [Saaras English Output Generated]: \"{user_input}\"")
            logging.info("🧠 Feeding English transcript directly into Sarvam 105B LLM for calendar notice extraction...")
        else:
            logging.warning("⚠️ Could not transcribe audio voice note. Skipping.")
            return

    if not user_input or not user_input.strip():
        logging.warning("Empty text received for processing. Skipping.")
        return

    inference_batch = None
    last_exception = None

    # Sarvam AI Indic Reasoning LLM (sarvam-105b) - Sole AI Processing Engine
    sarvam_api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not sarvam_api_key:
        logging.error("❌ [SARVAM AI REQUIRED] SARVAM_API_KEY is not configured in engine_python/.env.")
        logging.error("   The system is configured to process all notices strictly with Sarvam AI models (sarvam-105b & Saaras ASR).")
        logging.error("   Please open engine_python/.env and set: SARVAM_API_KEY=your_key_here")
        return

    try:
        inference_batch = extract_with_sarvam_llm(user_input)
    except Exception as sarvam_err:
        logging.error(f"❌ Sarvam 105B LLM extraction failed: {sarvam_err}")
        last_exception = sarvam_err

    if not inference_batch or not hasattr(inference_batch, 'events'):
        logging.error(f"❌ Sarvam 105B Extraction / Schema Validation Failure: {last_exception}")
        return

    has_valid_notices = False
    for target_event in inference_batch.events:
        has_valid_notices = True
        
        # ISOLATED LOOP SHIELD SAFETY BLOCK
        try:
            if target_event.is_important_notice:
                logging.info(f"🚨 [CRITICAL EVALUATION DETECTED]: {target_event.title}")
                logging.info(f"   Scheduled Date: {target_event.date} | Starting Clock Time: {target_event.time}")
                logging.info("   Syncing event entry directly to Google Calendar cloud servers...")
                add_to_google_calendar(target_event)
            else:
                logging.info(f"☕ [SKIPPED ADMINISTRATIVE RECORD]: {target_event.title} (Reason: Structural chat conversation noise)")
        except Exception as isolated_error:
            logging.error(f"❌ Error Isolation Shield Intercepted Event Defect on '{target_event.title}': {isolated_error}")
            continue
            
    if not has_valid_notices:
        logging.info("Pipeline processing completed. No actionable notice uncovered.")


# =====================================================================
# LIGHTWEIGHT MULTI-THREADED HTTP WEBHOOK SERVER (REPLACES RABBITMQ)
# =====================================================================
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads for zero-latency concurrent Webhook processing."""
    daemon_threads = True

class NoticeRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/process-notice' or self.path == '/':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                text_content = payload.get("text", "")
                audio_base64 = payload.get("audio_base64", None)
                audio_mimetype = payload.get("audio_mimetype", "audio/ogg")
                sender = payload.get("sender_name", "Unknown")
                chat = payload.get("chat_name", "Unknown Chat")
                is_voice = payload.get("is_voice", False)
                
                notice_type = "Voice Note 🎙️" if is_voice else "Text Message 💬"
                logging.info(f"📩 [HTTP Webhook Received] Type: {notice_type} | Chat: {chat} | Sender: {sender}")
                
                if text_content.strip() or audio_base64:
                    threading.Thread(
                        target=process_notice_payload,
                        args=(text_content, audio_base64, audio_mimetype),
                        daemon=True
                    ).start()
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Notice accepted for processing"}).encode('utf-8'))
            except Exception as e:
                logging.error(f"❌ Error handling HTTP POST notice: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress standard HTTP access log noise
        pass

def prewarm_engine():
    """Pre-warms Google Calendar API client (Google API only) and Sarvam 105B AI chain."""
    try:
        logging.info("⚡ [Pre-warming] Warming up Google Calendar client (Google APIs only)...")
        get_calendar_service()
        sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()
        if sarvam_key:
            logging.info(f"⚡ [Pre-warming] Pre-warming Sarvam Indic 105B LLM ({os.getenv('SARVAM_MODEL', 'sarvam-105b')})...")
            get_chain_for_sarvam()
            logging.info("⚡ [Pre-warming Complete] NotifAI Engine ready: Sarvam 105B AI + Google Calendar APIs!")
        else:
            logging.warning("⚠️ [Pre-warming Notice] SARVAM_API_KEY is not yet configured in engine_python/.env.")
            logging.warning("   Please paste your Sarvam API Key to activate Sarvam 105B inference.")
    except Exception as e:
        logging.debug(f"Pre-warming notice: {e}")


def start_http_server():
    port = int(os.getenv("PORT", "5005"))
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, NoticeRequestHandler)
    logging.info(f"🚀 [Engine HTTP Webhook Active] Listening for notices directly on port {port}...")
    threading.Thread(target=prewarm_engine, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down Engine HTTP Webhook server...")
        httpd.server_close()


# =====================================================================
# MAIN RUNTIME ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    logging.info("Booting NotifAI Core Framework Engine...")

    force_cli = "--cli" in sys.argv
    force_daemon = "--daemon" in sys.argv or os.getenv("RUN_MODE") == "consumer"
    is_interactive = sys.stdin.isatty() and not force_daemon

    if force_daemon or not is_interactive:
        start_http_server()
    else:
        print("\n🚀 ============================================================== 🚀")
        print("       NOTIFAI BATCH INGESTION & SCHEDULING SYSTEM ACTIVE       ")
        print("==================================================================")
        print("Select an option below to begin processing academic notices:")
        print("1. [Batch Ingestion] Parse local exported Telegram JSON chat logs")
        print("2. [Manual Fallback] Copy-paste notice texts directly into terminal")
        print("3. [HTTP Webhook Server] Start background HTTP Webhook listener")
        print("4. Exit system")
        print("------------------------------------------------------------------\n")
        
        while True:
            user_selection = input("Enter choice (1, 2, 3, or 4): ").strip()
            
            if user_selection == '4' or user_selection.lower() == 'exit':
                logging.info("Shutting down active NotifAI context.")
                break
                
            elif user_selection == '1':
                target_path = input("📂 Enter path to exported JSON file (default: result.json): ").strip()
                if not target_path:
                    target_path = "result.json"
                    
                logging.info(f"Initializing local ingestion routine over target file: '{target_path}'")
                try:
                    user_input = parse_local_telegram_logs(target_path, limit=50)
                    if not user_input:
                        logging.warning("Ingestion process resulted in an empty text matrix payload. Skipping run iteration.")
                        continue
                        
                    logging.info(f"Local ingestion compiled and isolated {len(user_input.splitlines())} dense data frames.")
                    process_notice_payload(user_input)
                except IngestionError as err:
                    logging.error(f"Ingestion Pipeline Execution Blocked: {err}")
                    continue
                except Exception as generic_err:
                    logging.error(f"Fatal platform processing divergence during extraction phase: {generic_err}")
                    continue
                    
            elif user_selection == '2':
                print("\n📥 Paste notice below. Press Enter, then submit via Ctrl+D (Linux/Mac) or Ctrl+Z (Windows).")
                line_accumulator = []
                while True:
                    try:
                        current_line = input()
                        line_accumulator.append(current_line)
                    except (KeyboardInterrupt, EOFError):
                        break
                user_input = "\n".join(line_accumulator).strip()
                if not user_input:
                    logging.warning("Manual fallback mode intercepted empty text buffer.")
                    continue
                process_notice_payload(user_input)
                
            elif user_selection == '3':
                start_http_server()
                break
            else:
                logging.warning("Unrecognized operational system choice selection profile specified.")
                continue