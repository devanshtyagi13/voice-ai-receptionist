"""
Test scenarios for the voice agent.
Each scenario defines the conversation turns, expected tools, and expected outcome.
"""
import datetime

TODAY = datetime.date.today()
TOMORROW = (TODAY + datetime.timedelta(days=1)).isoformat()
DAY_AFTER = (TODAY + datetime.timedelta(days=2)).isoformat()


SCENARIOS = [
    {
        "id": "book_english_simple",
        "description": "Patient books a GP appointment in Delhi — English, happy path",
        "language": "english",
        "turns": [
            {"role": "user", "content": "Hi, I want to book a new doctor's appointment please."},
            {"role": "user", "content": "My name is Rohan Gupta and my phone is +919876543210."},
            {"role": "user", "content": "I'd like Delhi branch, General Practice department."},
            {"role": "user", "content": f"I'd like {TOMORROW}, morning please."},
            {"role": "user", "content": "9:30 AM works perfectly for me."},
            {"role": "user", "content": "Yes, please go ahead and confirm the booking."},
        ],
        "expected_tools": ["get_doctors", "check_availability", "book_appointment"],
        "expected_outcome": "booked",
        "expected_in_response": ["appointment", "delhi"],
    },
    {
        "id": "book_hindi_simple",
        "description": "Patient books in Hindi — happy path",
        "language": "hindi",
        "turns": [
            {"role": "user", "content": "Namaste, mujhe nayi appointment chahiye."},
            {"role": "user", "content": "Mera naam Sunita Devi hai aur mera number hai +919811234567."},
            {"role": "user", "content": "Mumbai branch mein, skin ke doctor chahiye, Dermatology."},
            {"role": "user", "content": f"{DAY_AFTER} subah ka time chahiye."},
            {"role": "user", "content": "9 baje ka slot theek rahega."},
            {"role": "user", "content": "Haan, book kar dijiye."},
        ],
        "expected_tools": ["get_doctors", "check_availability", "book_appointment"],
        "expected_outcome": "booked",
        "expected_in_response": ["appointment", "mumbai"],
    },
    {
        "id": "book_hinglish",
        "description": "Patient mixes Hindi and English mid-call",
        "language": "mixed",
        "turns": [
            {"role": "user", "content": "Hello, I need to book a new appointment please."},
            {"role": "user", "content": "Mera naam Aryan Kapoor hai, number +919900112233."},
            {"role": "user", "content": "Delhi branch mein cardiology doctor chahiye."},
            {"role": "user", "content": f"I want {TOMORROW}, afternoon timing."},
            {"role": "user", "content": "2 PM slot theek rahega."},
            {"role": "user", "content": "Yes, book kar do please."},
        ],
        "expected_tools": ["get_doctors", "check_availability", "book_appointment"],
        "expected_outcome": "booked",
        "expected_in_response": ["appointment", "delhi"],
    },
    {
        "id": "reschedule",
        "description": "Existing patient reschedules their appointment",
        "language": "english",
        "turns": [
            {"role": "user", "content": "Hi, I want to reschedule an existing appointment I have."},
            {"role": "user", "content": "My phone number is +919876543210."},
            {"role": "user", "content": "I want to reschedule the first appointment listed."},
            {"role": "user", "content": f"Can I move it to {DAY_AFTER} at 11 AM?"},
            {"role": "user", "content": "Yes, please reschedule it."},
        ],
        "expected_tools": ["get_patient_appointments", "check_availability", "reschedule_appointment"],
        "expected_outcome": "rescheduled",
        "expected_in_response": ["appointment", "11"],
    },
    {
        "id": "cancel",
        "description": "Patient explicitly cancels an existing appointment",
        "language": "english",
        "turns": [
            {"role": "user", "content": "I want to cancel one of my appointments please."},
            {"role": "user", "content": "My phone number is +919876543210."},
            {"role": "user", "content": "Please cancel the first appointment."},
            {"role": "user", "content": "Yes, I am sure. Please cancel it."},
        ],
        "expected_tools": ["get_patient_appointments", "cancel_appointment"],
        "expected_outcome": "cancelled",
        "expected_in_response": ["cancel"],
    },
    {
        "id": "slot_conflict_resolved",
        "description": "Requested slot is fully booked — agent offers alternatives",
        "language": "english",
        "turns": [
            {"role": "user", "content": "Hi, I want to book a new appointment."},
            {"role": "user", "content": "Name is Priya Sharma, phone +919123456789."},
            {"role": "user", "content": "Delhi branch, General Practice please."},
            {"role": "user", "content": f"I want {TOMORROW} at 10 AM."},
            {"role": "user", "content": "Ok, give me any other available slot on the same day."},
            {"role": "user", "content": "Yes, book that one."},
        ],
        "expected_tools": ["get_doctors", "check_availability", "book_appointment"],
        "expected_outcome": "booked",
        "expected_in_response": ["appointment"],
    },
    {
        "id": "no_appointment_found",
        "description": "Patient asks for appointments but has none on record",
        "language": "english",
        "turns": [
            {"role": "user", "content": "Can you tell me what appointments I have scheduled?"},
            {"role": "user", "content": "My phone number is +919000000000."},
        ],
        "expected_tools": ["get_patient_appointments"],
        "expected_outcome": "no_action",
        "expected_in_response": ["don't have", "appointment"],
    },
    {
        "id": "branch_query_then_book",
        "description": "Patient asks about branches and departments, then books",
        "language": "english",
        "turns": [
            {"role": "user", "content": "What branches and departments do you have?"},
            {"role": "user", "content": "I'd like to book in Mumbai, Orthopedics."},
            {"role": "user", "content": "My name is Kartik Mehta, phone +919988776655."},
            {"role": "user", "content": f"This {DAY_AFTER}, afternoon please."},
            {"role": "user", "content": "3 PM works for me."},
            {"role": "user", "content": "Yes, confirm it."},
        ],
        "expected_tools": ["get_clinic_info", "get_doctors", "check_availability", "book_appointment"],
        "expected_outcome": "booked",
        "expected_in_response": ["appointment", "mumbai"],
    },
]


def get_scenario(scenario_id: str):
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None
