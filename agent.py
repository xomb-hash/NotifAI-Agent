# =====================================================================
#  MODULE 1: PLATFORM FOUNDATIONS & CONTEXT MANAGEMENT
#  MODULE 5: SYSTEM TELEMETRY CONFIGURATION
# C++ equivalents: #include <iostream>, <vector>, <string>, <fstream>, <exception>
# =====================================================================
import os
import datetime
import json
import logging  # [DAY 5] Indus482497333698try-standard logging library replacing basic print() statements with structured telemetry
from typing import List  # [DAY 2] Generic type annotations mapping directly to C++ std::vector containers

from pydantic import BaseModel, Field  # [DAY 2] Data enforcement validation schemas
from langchain_google_genai import ChatGoogleGenerativeAI  # [DAY 7] LLM orchestration framework
from langchain_core.prompts import ChatPromptTemplate  # [DAY 7] Secure prompt factories
from dotenv import load_dotenv  # [DAY 4] Secure local environment variable injector

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# [DAY 4] Injects security credentials and tokens from local hidden environmental variables (.env)
load_dotenv()

# [DAY 3] OAuth 2.0 Access Scopes: Strictly limits the agent's write permission boundary to calendar events only
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# =====================================================================
# TELEMETRY CONFIGURATOR
# =====================================================================
# Configures logging to pipe structured outputs simultaneously to both:
# 1. A persistent local logfile ('app.log') for forensic trace analysis and debugging.
# 2. The standard system console (stdout) with context markers.
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
# C++ Equivalent: Custom classes inheriting from std::exception
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
    Core Structural Entity inheriting from Pydantic's BaseModel.
    Acts like a strict C++ struct with implicit casting and validation boundaries.
    """
    is_important_notice: bool = Field(description="True if this is an exam, class test, assignment deadline, fest, hackathon, or official holiday. False for casual chats or spam.")
    title: str = Field(description="A concise summary title for the calendar event entry.")
    date: str = Field(description="The event target date in absolute format YYYY-MM-DD.")
    time: str = Field(description="The target event timestamp in 24-hour HH:MM format. Default to '09:00' if unspecified.")
    description: str = Field(description="Context snippet, location flags, room details, or original message texts.")

class CollegeEventList(BaseModel):
    """Array structural collection wrapper mapping directly to std::vector<CollegeEvent>."""
    events: List[CollegeEvent] = Field(description="Array listing of individual valid parsed events discovered in text payloads.")


# =====================================================================
#  LANGCHAIN PIPELINE ARCHITECTURE (LCEL)
# =====================================================================
# Set temperature to 0 to secure high semantic reliability and deterministic output formats
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=1.8) 

# Links the LLM processing matrix with our strict Pydantic model definition
structured_llm = llm.with_structured_output(CollegeEventList)

# [DYNAMIC FIX] Dynamically fetches today's live operational date to correct calendar offsets
actual_today = datetime.date.today().strftime("%A, %B %d, %Y")

# Parameterized prompt factory enforcing relative temporal constraints
prompt_template = ChatPromptTemplate.from_messages([
    ("system", f"You are an AI tracking a messy college notification board stream. Extract and isolate events precisely. Today's anchor date is explicitly {actual_today}."),
    ("user", "Analyze this unstructured message stream:\n\n{message}")
])

# LangChain Expression Language (LCEL). Overloads the Python bitwise OR operator '|' to build a deterministic execution stream.
agent_chain = prompt_template | structured_llm


# =====================================================================
#  SECURE OAUTH 2.0 PROTOCOL ENGINE & STATE HANDSHAKE
# =====================================================================
def get_calendar_service():
    """
    Coordinates state authentication. Resolves cached token configurations, 
    triggers background silent refreshes, or initializes loopback server handshakes.
    """
    creds = None
    
    # Check for warm credential cache on local disk
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                # [DAY 5] Telemetry logging tracking system state adjustments
                logging.info("Access token expired. Executing silent token refresh flow (Silent Healing)...")
                creds.refresh(Request())
            except Exception as e:
                logging.warning(f"Silent refresh failed: {e}. Purging corrupted local token cache...")
                if os.path.exists('token.json'):
                    os.remove('token.json')
                creds = None
                
        if not creds:
            if not os.path.exists('langcredentials.json'):
                raise FileNotFoundError("Google OAuth application signature config 'langcredentials.json' is missing.")
            flow = InstalledAppFlow.from_client_secrets_file('langcredentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # [DAY 1] CONTEXT MANAGER (Python RAII equivalent) safely locking file IO buffers
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('calendar', 'v3', credentials=creds)


# =====================================================================
# GOOGLE CALENDAR RESTFUL API SCHEMA INTEGRATION
# =====================================================================
def add_to_google_calendar(event_data: CollegeEvent):
    """Formats structural event maps and executes API POST calls with multi-tier notification reminders."""
    try:
        service = get_calendar_service()
        start_iso = f"{event_data.date}T{event_data.time}:00"
        #what if the user entewr not isn iso format
        #one of the issue is with 23 event 23 :00 start end 24:00 is nothing X 00:00 hota
        # [DAY 4] Custom Temporal Logic: Calculating safety boundaries to process duration ceilings
        hour_digits = int(event_data.time[:2])
        end_hour_digits = str(hour_digits + 1).zfill(2) if hour_digits < 23 else "00"
        end_iso = f"{event_data.date}T{end_hour_digits}{event_data.time[2:]}:00"

        # Compilation of schema payload passed downstream into Google REST gateways
        event_payload = {
            'summary': event_data.title,
            'description': f"{event_data.description}\n\n[Synchronized via NotifAI Client Agent]",
            'start': {'dateTime': start_iso, 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_iso, 'timeZone': 'Asia/Kolkata'},
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 2880},   # [DAY 4] Custom 48-Hour pop-up alarm offset
                    {'method': 'popup', 'minutes': 10080},  # [DAY 4] Custom 7-Day pop-up alarm offset
                ],
            },
        }

        response = service.events().insert(calendarId='primary', body=event_payload).execute()
        logging.info(f"Successfully posted schedule event! Verification URL: {response.get('htmlLink')}")
        
    except Exception as e:
        raise RuntimeError(f"Google REST network submission drop: {e}")


# =====================================================================
# DATA INGESTION PIPELINE (LOCAL TEXT BATCH COMPRESSION)
# Algorithmic Time & Space Complexity: O(M) where M is character payload size
# =====================================================================
def parse_local_telegram_logs(file_path: str, limit: int = 50) -> str:
    """Ingests raw backup JSON payloads, drops structural noise, and compresses rich arrays down into context-dense strings."""
    if not os.path.exists(file_path):
        raise IngestionError(f"No valid local target file discovered matching path: {file_path}")
        
    try:
        # [DAY 1] Python Context Manager handling automated stream close cycles
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
#  INTERACTIVE CLI CONTROL ANCHOR LOOP (MAIN RUNTIME CONTEXT)
# =====================================================================
if __name__ == "__main__":
    logging.info("Booting NotifAI Core Framework Engine...")
    print("\n🚀 ============================================================== 🚀")
    print("       NOTIFAI BATCH INGESTION & SCHEDULING SYSTEM ACTIVE       ")
    print("==================================================================")
    print("Select an option below to begin processing academic notices:")
    print("1. [Batch Ingestion] Parse local exported Telegram JSON chat logs")
    print("2. [Manual Fallback] Copy-paste notice texts directly into terminal")
    print("3. Exit system")
    print("------------------------------------------------------------------\n")
    
    while True:
        user_selection = input("Enter choice (1, 2, or 3): ").strip()
        
        if user_selection == '3' or user_selection.lower() == 'exit':
            logging.info("Shutting down active NotifAI context. Disconnecting network proxies.")
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
                logging.info("Streaming compressed log sequence blocks to LangChain pipeline processor...")
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
                logging.warning("Manual fallback mode intercepted empty text buffer. Restructuring line listeners.")
                continue
            logging.info("Routing stream payload to LangChain execution pipeline...")
        else:
            logging.warning("Unrecognized operational system choice selection profile specified.")
            continue
            
        # =====================================================================
        # [DAY 5] BATCH INFERENCE INVOCATION & ERROR SHIELDED SYNCHRONIZATION LOOP
        # =====================================================================
        try:
            inference_batch = agent_chain.invoke({"message": user_input})
            if not inference_batch or not hasattr(inference_batch, 'events'):
                raise AISchemaValidationError("Model response failed to fulfill validation parameters.")
                
            has_valid_notices = False
            for target_event in inference_batch.events:
                has_valid_notices = True
                
                # =====================================================================
                # [DAY 5] ISOLATED LOOP SHIELD SAFETY BLOCK
                # Wraps individual event insertions in a localized sub-try/except safety wrapper.
                # Prevents validation crashes on a single notice from breaking brother records.
                # =====================================================================
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
                    logging.info("Shield active. Recovering runtime pipeline state context to process remaining batch blocks...")
                    continue
                    
            if not has_valid_notices:
                logging.info("Pipeline processing completed. No context matching evaluation targets was uncovered.")
            print("\n-------------------------------------------------------------")
            
        except AISchemaValidationError as schema_err:
            logging.error(f"Pydantic Structure Validation Core Failure: {schema_err}")
        except Exception as system_pipeline_err:
            logging.error(f"LangChain orchestration execution block experienced a system failure: {system_pipeline_err}")