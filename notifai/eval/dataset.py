"""Labeled evaluation dataset for NotifAI.

52 test cases covering:
- Simple English events (10)
- Hinglish events (10)
- Ambiguous dates (8)
- Multiple events per message (6)
- Cancellations / updates (5)
- Pure chatter / no events (5)
- Deadlines (4)
- Mixed complexity (4)

Each case has:
  message: the raw notice text
  category: grouping for per-category metrics
  expected: list of expected event dicts with title, date, time, description,
            notice_type, is_important_notice
"""

from __future__ import annotations

from typing import Any

# Anchor date for relative date resolution: 2026-11-18 (Wednesday)
ANCHOR_DATE = "2026-11-18"

EVAL_CASES: list[dict[str, Any]] = [
    # === Simple English events (10) ===
    {
        "message": "Team meeting tomorrow at 10am in Conference Room B.",
        "category": "simple_english",
        "expected": [
            {"title": "Team Meeting", "date": "2026-11-19", "time": "10:00",
             "description": "Team meeting in Conference Room B", "notice_type": "meeting",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Submit the project report by Friday 5pm.",
        "category": "simple_english",
        "expected": [
            {"title": "Submit Project Report", "date": "2026-11-21", "time": "17:00",
             "description": "Submit project report", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Exam on November 25th at 9am in Hall A.",
        "category": "simple_english",
        "expected": [
            {"title": "Exam", "date": "2026-11-25", "time": "09:00",
             "description": "Exam in Hall A", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Don't forget to bring your laptop to the lab session today at 2pm.",
        "category": "simple_english",
        "expected": [
            {"title": "Bring Laptop to Lab", "date": "2026-11-18", "time": "14:00",
             "description": "Lab session, bring laptop", "notice_type": "reminder",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Workshop on AI/ML this Saturday 11:30 AM, Auditorium.",
        "category": "simple_english",
        "expected": [
            {"title": "AI/ML Workshop", "date": "2026-11-22", "time": "11:30",
             "description": "AI/ML Workshop in Auditorium", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Call the event manager today evening.",
        "category": "simple_english",
        "expected": [
            {"title": "Call Event Manager", "date": "2026-11-18", "time": "10:00",
             "description": "Call the event manager", "notice_type": "reminder",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Library books due tomorrow, return by 4pm.",
        "category": "simple_english",
        "expected": [
            {"title": "Return Library Books", "date": "2026-11-19", "time": "16:00",
             "description": "Return library books", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Guest lecture by Dr. Sharma on Nov 28 at 3 PM in Room 204.",
        "category": "simple_english",
        "expected": [
            {"title": "Guest Lecture by Dr. Sharma", "date": "2026-11-28", "time": "15:00",
             "description": "Guest lecture in Room 204", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Sports day practice at 6am tomorrow morning, ground.",
        "category": "simple_english",
        "expected": [
            {"title": "Sports Day Practice", "date": "2026-11-19", "time": "06:00",
             "description": "Sports day practice on ground", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Pay semester fees before December 1st.",
        "category": "simple_english",
        "expected": [
            {"title": "Pay Semester Fees", "date": "2026-12-01", "time": "10:00",
             "description": "Pay semester fees", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },

    # === Hinglish events (10) ===
    {
        "message": "Kal 11 baje lab mein meeting hai, sabko aana hai.",
        "category": "hinglish",
        "expected": [
            {"title": "Lab Meeting", "date": "2026-11-19", "time": "11:00",
             "description": "Lab meeting, everyone must attend", "notice_type": "meeting",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Aaj shaam 5 baje auditorium mein submit karo project files.",
        "category": "hinglish",
        "expected": [
            {"title": "Submit Project Files", "date": "2026-11-18", "time": "17:00",
             "description": "Submit project files in auditorium", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Parso se hackathon shuru hai, 9am tak aana.",
        "category": "hinglish",
        "expected": [
            {"title": "Hackathon", "date": "2026-11-20", "time": "09:00",
             "description": "Hackathon starts, arrive by 9am", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Bacchon, kal subah 8 baje test hai. Syllabus complete karo.",
        "category": "hinglish",
        "expected": [
            {"title": "Test", "date": "2026-11-19", "time": "08:00",
             "description": "Test tomorrow morning", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Friday ko presentation hai, 2 baje. Slides bhej do.",
        "category": "hinglish",
        "expected": [
            {"title": "Presentation", "date": "2026-11-21", "time": "14:00",
             "description": "Presentation on Friday", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Aaj raat ko 10 baje tak assignment submit karna hai.",
        "category": "hinglish",
        "expected": [
            {"title": "Submit Assignment", "date": "2026-11-18", "time": "22:00",
             "description": "Submit assignment by 10pm tonight", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Kal se 3 din ka festival hai, 10am se 5pm tak.",
        "category": "hinglish",
        "expected": [
            {"title": "Festival", "date": "2026-11-19", "time": "10:00",
             "description": "3-day festival, 10am to 5pm", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Sunday ko 11 baje club meeting hai, sab log aayenge.",
        "category": "hinglish",
        "expected": [
            {"title": "Club Meeting", "date": "2026-11-23", "time": "11:00",
             "description": "Club meeting on Sunday", "notice_type": "meeting",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Kal exam ke baad 4 baje result aayega.",
        "category": "hinglish",
        "expected": [
            {"title": "Exam Result", "date": "2026-11-19", "time": "16:00",
             "description": "Exam result after exam tomorrow", "notice_type": "announcement",
             "is_important_notice": True},
        ],
    },
    {
        "message": "12 baje lunch hai team ke saath, cafeteria mein.",
        "category": "hinglish",
        "expected": [
            {"title": "Team Lunch", "date": "2026-11-18", "time": "12:00",
             "description": "Team lunch in cafeteria", "notice_type": "meeting",
             "is_important_notice": True},
        ],
    },

    # === Ambiguous dates (8) ===
    {
        "message": "Meeting next Friday at 3pm.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Meeting", "date": "2026-11-28", "time": "15:00",
             "description": "Meeting next Friday", "notice_type": "meeting",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Submit assignment in 2 days by end of day.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Submit Assignment", "date": "2026-11-20", "time": "10:00",
             "description": "Submit assignment in 2 days", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Workshop next Monday 10am.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Workshop", "date": "2026-11-24", "time": "10:00",
             "description": "Workshop next Monday", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Team outing this weekend, Saturday 9am.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Team Outing", "date": "2026-11-22", "time": "09:00",
             "description": "Team outing this weekend", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Exam in 3 days, be prepared.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Exam", "date": "2026-11-21", "time": "10:00",
             "description": "Exam in 3 days", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Meeting the day after tomorrow at 2pm.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Meeting", "date": "2026-11-20", "time": "14:00",
             "description": "Meeting day after tomorrow", "notice_type": "meeting",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Presentation next Wednesday 11am.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Presentation", "date": "2026-11-26", "time": "11:00",
             "description": "Presentation next Wednesday", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Club event this Thursday 4:30pm.",
        "category": "ambiguous_dates",
        "expected": [
            {"title": "Club Event", "date": "2026-11-20", "time": "16:30",
             "description": "Club event this Thursday", "notice_type": "event",
             "is_important_notice": True},
        ],
    },

    # === Multiple events per message (6) ===
    {
        "message": "Two things: 1) Meeting tomorrow 10am in Room 101. 2) Submit report by Friday 5pm.",
        "category": "multi_event",
        "expected": [
            {"title": "Meeting", "date": "2026-11-19", "time": "10:00",
             "description": "Meeting in Room 101", "notice_type": "meeting",
             "is_important_notice": True},
            {"title": "Submit Report", "date": "2026-11-21", "time": "17:00",
             "description": "Submit report", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Exam on Nov 25 at 9am. Result on Nov 30 at 3pm.",
        "category": "multi_event",
        "expected": [
            {"title": "Exam", "date": "2026-11-25", "time": "09:00",
             "description": "Exam", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Exam Result", "date": "2026-11-30", "time": "15:00",
             "description": "Exam result", "notice_type": "announcement",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Kal 10 baje meeting, aur Friday ko presentation 2pm.",
        "category": "multi_event",
        "expected": [
            {"title": "Meeting", "date": "2026-11-19", "time": "10:00",
             "description": "Meeting tomorrow", "notice_type": "meeting",
             "is_important_notice": True},
            {"title": "Presentation", "date": "2026-11-21", "time": "14:00",
             "description": "Presentation on Friday", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Monday: workshop 10am. Wednesday: guest lecture 2pm. Friday: project demo 11am.",
        "category": "multi_event",
        "expected": [
            {"title": "Workshop", "date": "2026-11-24", "time": "10:00",
             "description": "Workshop on Monday", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Guest Lecture", "date": "2026-11-26", "time": "14:00",
             "description": "Guest lecture on Wednesday", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Project Demo", "date": "2026-11-28", "time": "11:00",
             "description": "Project demo on Friday", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Don't forget: library books due tomorrow 4pm. Also team dinner Friday 7pm.",
        "category": "multi_event",
        "expected": [
            {"title": "Return Library Books", "date": "2026-11-19", "time": "16:00",
             "description": "Library books due", "notice_type": "deadline",
             "is_important_notice": True},
            {"title": "Team Dinner", "date": "2026-11-21", "time": "19:00",
             "description": "Team dinner", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Aaj 3 baje lab mein test. Kal 11 baje results. Friday ko 5 baje viva.",
        "category": "multi_event",
        "expected": [
            {"title": "Lab Test", "date": "2026-11-18", "time": "15:00",
             "description": "Lab test", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Test Results", "date": "2026-11-19", "time": "11:00",
             "description": "Results tomorrow", "notice_type": "announcement",
             "is_important_notice": True},
            {"title": "Viva", "date": "2026-11-21", "time": "17:00",
             "description": "Viva on Friday", "notice_type": "event",
             "is_important_notice": True},
        ],
    },

    # === Cancellations / updates (5) ===
    {
        "message": "Tomorrow's meeting at 10am is cancelled.",
        "category": "cancellation",
        "expected": [
            {"title": "Meeting Cancelled", "date": "2026-11-19", "time": "10:00",
             "description": "Tomorrow's meeting cancelled", "notice_type": "cancellation",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Friday exam has been postponed to next Monday 9am.",
        "category": "cancellation",
        "expected": [
            {"title": "Exam Postponed", "date": "2026-11-24", "time": "09:00",
             "description": "Friday exam postponed to Monday", "notice_type": "cancellation",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Kal ki meeting cancel ho gayi hai.",
        "category": "cancellation",
        "expected": [
            {"title": "Meeting Cancelled", "date": "2026-11-19", "time": "10:00",
             "description": "Tomorrow's meeting cancelled", "notice_type": "cancellation",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Workshop moved from Room A to Room B, same time 11am tomorrow.",
        "category": "cancellation",
        "expected": [
            {"title": "Workshop (Moved to Room B)", "date": "2026-11-19", "time": "11:00",
             "description": "Workshop moved to Room B", "notice_type": "cancellation",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Presentation time changed from 2pm to 4pm on Friday.",
        "category": "cancellation",
        "expected": [
            {"title": "Presentation (Time Changed to 4pm)", "date": "2026-11-21", "time": "16:00",
             "description": "Presentation time changed to 4pm", "notice_type": "cancellation",
             "is_important_notice": True},
        ],
    },

    # === Pure chatter / no events (5) ===
    {
        "message": "lol that's hilarious",
        "category": "chatter",
        "expected": [],
    },
    {
        "message": "Thanks for the update!",
        "category": "chatter",
        "expected": [],
    },
    {
        "message": "Haha same here, kaisa hai tu?",
        "category": "chatter",
        "expected": [],
    },
    {
        "message": "Good morning everyone!",
        "category": "chatter",
        "expected": [],
    },
    {
        "message": "Ok noted, will check and revert.",
        "category": "chatter",
        "expected": [],
    },

    # === Deadlines (4) ===
    {
        "message": "Assignment submission deadline extended to November 30, 11:59 PM.",
        "category": "deadlines",
        "expected": [
            {"title": "Assignment Submission (Extended)", "date": "2026-11-30", "time": "23:59",
             "description": "Assignment deadline extended", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Last date to register for the conference is Nov 22, 6pm.",
        "category": "deadlines",
        "expected": [
            {"title": "Conference Registration Deadline", "date": "2026-11-22", "time": "18:00",
             "description": "Register for conference", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Scholarship application due December 5th, no late submissions.",
        "category": "deadlines",
        "expected": [
            {"title": "Scholarship Application", "date": "2026-12-05", "time": "10:00",
             "description": "Scholarship application due", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Hackathon registration closes tomorrow 8pm.",
        "category": "deadlines",
        "expected": [
            {"title": "Hackathon Registration", "date": "2026-11-19", "time": "20:00",
             "description": "Hackathon registration closes", "notice_type": "deadline",
             "is_important_notice": True},
        ],
    },

    # === Mixed complexity (4) ===
    {
        "message": "Reminder: 1) Submit timesheet today 6pm. 2) Team sync tomorrow 9:30am. 3) Code review Friday 3pm. All mandatory.",
        "category": "mixed",
        "expected": [
            {"title": "Submit Timesheet", "date": "2026-11-18", "time": "18:00",
             "description": "Submit timesheet today", "notice_type": "deadline",
             "is_important_notice": True},
            {"title": "Team Sync", "date": "2026-11-19", "time": "09:30",
             "description": "Team sync tomorrow", "notice_type": "meeting",
             "is_important_notice": True},
            {"title": "Code Review", "date": "2026-11-21", "time": "15:00",
             "description": "Code review Friday", "notice_type": "meeting",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Important updates: Exam postponed to Nov 27. New venue: Hall C. Reporting time 8:30am. Bring your own stationery.",
        "category": "mixed",
        "expected": [
            {"title": "Exam (Postponed to Nov 27)", "date": "2026-11-27", "time": "08:30",
             "description": "Exam in Hall C, bring stationery", "notice_type": "cancellation",
             "is_important_notice": True},
        ],
    },
    {
        "message": "College fest 'Srijan' from Nov 25-27. Day 1: 10am inauguration. Day 2: 11am workshops. Day 3: 4pm closing ceremony. All in main auditorium.",
        "category": "mixed",
        "expected": [
            {"title": "Srijan Fest - Inauguration", "date": "2026-11-25", "time": "10:00",
             "description": "Srijan fest inauguration in auditorium", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Srijan Fest - Workshops", "date": "2026-11-26", "time": "11:00",
             "description": "Srijan fest workshops in auditorium", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Srijan Fest - Closing", "date": "2026-11-27", "time": "16:00",
             "description": "Srijan fest closing ceremony in auditorium", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
    {
        "message": "Bhaisab, kal se 3 din ka industrial visit hai. Day 1: factory tour 9am. Day 2: 10am presentation. Day 3: 2pm feedback session. Attendance mandatory.",
        "category": "mixed",
        "expected": [
            {"title": "Industrial Visit - Factory Tour", "date": "2026-11-19", "time": "09:00",
             "description": "Industrial visit factory tour", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Industrial Visit - Presentation", "date": "2026-11-20", "time": "10:00",
             "description": "Industrial visit presentation", "notice_type": "event",
             "is_important_notice": True},
            {"title": "Industrial Visit - Feedback", "date": "2026-11-21", "time": "14:00",
             "description": "Industrial visit feedback session", "notice_type": "event",
             "is_important_notice": True},
        ],
    },
]