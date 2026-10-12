import sys
import os
import json
import time

# Ensure engine_python directory is in python path
sys.path.append(os.path.abspath('./engine_python'))

from agent import process_notice_payload

def run_srijan_test_cases():
    print("\n🚀 ==================================================================== 🚀")
    print("      NOTIFAI ENTERPRISE - SRIJAN GROUP END-TO-END TEST SUITE        ")
    print("====================================================================\n")

    test_messages = [
        {
            "case": "Target Group History / Live Notice 1 (Srijan Fest Date)",
            "chat_name": "Srijan",
            "sender": "Class Representative",
            "text": "All studenr srijan is on 27 november 2026 at 10:00 AM."
        },
        {
            "case": "Target Group Notice 2 (Srijan Hackathon Deadline)",
            "chat_name": "Srijan",
            "sender": "Faculty Coordinator",
            "text": "Srijan Hackathon final project submission deadline is November 30, 2026 at 17:00 in Lab 3."
        },
        {
            "case": "Non-Important Conversation Noise in Srijan Group",
            "chat_name": "Srijan",
            "sender": "Student",
            "text": "Yeaa 27th e to amar e ticket hoi ni, high demand in IRCTC."
        }
    ]

    for idx, test in enumerate(test_messages, 1):
        print(f"\n--------------------------------------------------------------------")
        print(f"📌 TEST CASE {idx}: {test['case']}")
        print(f"   Group Name : {test['chat_name']}")
        print(f"   Sender     : {test['sender']}")
        print(f"   Payload    : \"{test['text']}\"")
        print(f"--------------------------------------------------------------------")

        process_notice_payload(test['text'])
        time.sleep(1)

    print("\n====================================================================")
    print("✅ ALL SRIJAN GROUP TEST CASES COMPLETED SUCCESSFULLY!")
    print("====================================================================\n")

if __name__ == "__main__":
    run_srijan_test_cases()
