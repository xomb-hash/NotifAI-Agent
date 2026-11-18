"""Typed Google Calendar tool for the Scheduler agent.

Google API imports are deferred to call time so the module can be imported
in environments without the Google client libraries installed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from notifai.config.settings import settings
from notifai.core.schemas import CollegeEvent

logger = logging.getLogger(__name__)

_CALENDAR_SERVICE: Any = None

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _get_calendar_service() -> Any:
    global _CALENDAR_SERVICE
    if _CALENDAR_SERVICE is not None:
        return _CALENDAR_SERVICE

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds: Credentials | None = None
    token_path = settings.google_calendar_token
    creds_path = settings.google_calendar_credentials

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    except (FileNotFoundError, ValueError):
        pass

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path:
                raise FileNotFoundError(
                    "Google Calendar credentials not configured."
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    _CALENDAR_SERVICE = build(
        "calendar", "v3", credentials=creds, cache_discovery=False
    )
    return _CALENDAR_SERVICE


def schedule_event(event: CollegeEvent) -> dict[str, Any]:
    """Schedule a single event on Google Calendar.

    Args:
        event: A CollegeEvent with title, date (YYYY-MM-DD), time (HH:MM), description.

    Returns:
        Dict with status, event_id, and html_link.
    """
    try:
        service = _get_calendar_service()
        start_iso = f"{event.date}T{event.time}:00"
        hour = int(event.time[:2])
        end_hour = str(hour + 1).zfill(2) if hour < 23 else "00"
        end_iso = f"{event.date}T{end_hour}{event.time[2:]}:00"

        body = {
            "summary": event.title,
            "description": f"{event.description}\n\n[Synchronized via NotifAI]",
            "start": {"dateTime": start_iso, "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_iso, "timeZone": "Asia/Kolkata"},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 10},
                    {"method": "popup", "minutes": 30},
                    {"method": "popup", "minutes": 1440},
                ],
            },
        }

        response = service.events().insert(
            calendarId=settings.google_calendar_id, body=body
        ).execute()

        logger.info(
            "Scheduled event '%s' on %s at %s: %s",
            event.title,
            event.date,
            event.time,
            response.get("htmlLink", "N/A"),
        )

        return {
            "status": "scheduled",
            "event_id": response.get("id"),
            "html_link": response.get("htmlLink"),
        }
    except Exception as e:
        logger.error("Failed to schedule event '%s': %s", event.title, e)
        return {"status": "error", "error": str(e)}


def schedule_events(events: list[CollegeEvent]) -> list[dict[str, Any]]:
    """Schedule multiple events on Google Calendar.

    Args:
        events: List of CollegeEvent objects.

    Returns:
        List of result dicts, one per event.
    """
    results: list[dict[str, Any]] = []
    for event in events:
        results.append(schedule_event(event))
    return results


def check_calendar_availability(
    date: str, time: str, duration_minutes: int = 60
) -> dict[str, Any]:
    """Check if a time slot is available on Google Calendar.

    Args:
        date: Date in YYYY-MM-DD format.
        time: Time in HH:MM format (24-hour).
        duration_minutes: Duration in minutes.

    Returns:
        Dict with available (bool) and conflicting_events (list).
    """
    try:
        service = _get_calendar_service()
        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        events_result = (
            service.events()
            .list(
                calendarId=settings.google_calendar_id,
                timeMin=start_dt.isoformat() + "Z",
                timeMax=end_dt.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        conflicts = events_result.get("items", [])
        return {
            "available": len(conflicts) == 0,
            "conflicting_events": [
                {"summary": e.get("summary"), "start": e.get("start")}
                for e in conflicts
            ],
        }
    except Exception as e:
        logger.error("Failed to check availability for %s %s: %s", date, time, e)
        return {"available": False, "error": str(e)}
