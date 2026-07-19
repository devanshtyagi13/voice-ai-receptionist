"""
Handles all tool calls from the Vapi voice agent.
Each function maps directly to a tool defined in prompts/tools.json.
"""
from sqlalchemy.orm import Session
from models import Doctor, Department, Branch
from services.clinic_service import (
    get_all_branches,
    get_doctors,
    get_available_slots,
    book_appointment,
    get_patient_appointments,
    reschedule_appointment,
    cancel_appointment,
)


def handle_tool_call(tool_name: str, args: dict, db: Session) -> dict:
    handlers = {
        "get_clinic_info": _get_clinic_info,
        "get_doctors": _get_doctors,
        "check_availability": _check_availability,
        "book_appointment": _book_appointment,
        "get_patient_appointments": _get_patient_appointments,
        "reschedule_appointment": _reschedule_appointment,
        "cancel_appointment": _cancel_appointment,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}
    return handler(args, db)


def _get_clinic_info(args: dict, db: Session) -> dict:
    branches = get_all_branches(db)
    departments = [{"id": d.id, "name": d.name} for d in db.query(Department).all()]
    return {
        "branches": branches,
        "departments": departments,
        "message": "We have two branches: Delhi (Connaught Place) and Mumbai (Bandra). Departments: General Practice, Cardiology, Dermatology, Orthopedics."
    }


def _get_doctors(args: dict, db: Session) -> dict:
    branch = args.get("branch")
    department = args.get("department")
    doctors = get_doctors(db, branch_name=branch, department_name=department)
    if not doctors:
        return {"doctors": [], "message": "No doctors found matching your criteria."}
    return {"doctors": doctors}


def _check_availability(args: dict, db: Session) -> dict:
    branch = args.get("branch")
    department = args.get("department")
    doctor_name = args.get("doctor_name")
    preferred_date = args.get("preferred_date")
    preferred_time_pref = args.get("preferred_time", "")

    if not preferred_date:
        return {"error": "Please provide a preferred date."}

    # Find matching doctors
    q = db.query(Doctor).join(Branch).join(Department)
    if branch:
        q = q.filter(Branch.name.ilike(f"%{branch}%"))
    if department:
        q = q.filter(Department.name.ilike(f"%{department}%"))
    if doctor_name:
        q = q.filter(Doctor.name.ilike(f"%{doctor_name}%"))
    doctors = q.all()

    if not doctors:
        return {"error": "No matching doctors found. Please check branch, department, or doctor name."}

    results = []
    for doc in doctors:
        slots_data = get_available_slots(db, doc.id, preferred_date)
        slots = slots_data.get("available_slots", [])

        # Filter by time preference
        if preferred_time_pref and slots:
            if "morning" in preferred_time_pref.lower():
                slots = [s for s in slots if s < "12:00"]
            elif "afternoon" in preferred_time_pref.lower():
                slots = [s for s in slots if "12:00" <= s < "17:00"]
            elif "evening" in preferred_time_pref.lower():
                slots = [s for s in slots if s >= "17:00"]

        results.append({
            "doctor_id": doc.id,
            "doctor_name": doc.name,
            "department": doc.department.name,
            "branch": doc.branch.name,
            "date": preferred_date,
            "available_slots": slots[:8],  # Return first 8 slots to keep response concise
        })

    return {"availability": results}


def _book_appointment(args: dict, db: Session) -> dict:
    required = ["patient_name", "patient_phone", "doctor_id", "date", "time"]
    for field in required:
        if not args.get(field):
            return {"success": False, "error": f"Missing required field: {field}"}

    return book_appointment(
        db=db,
        patient_name=args["patient_name"],
        patient_phone=args["patient_phone"],
        doctor_id=int(args["doctor_id"]),
        date_str=args["date"],
        time_str=args["time"],
        notes=args.get("notes", "")
    )


def _get_patient_appointments(args: dict, db: Session) -> dict:
    phone = args.get("patient_phone")
    if not phone:
        return {"error": "Please provide patient phone number."}
    return get_patient_appointments(db, phone)


def _reschedule_appointment(args: dict, db: Session) -> dict:
    appt_id = args.get("appointment_id")
    new_date = args.get("new_date")
    new_time = args.get("new_time")
    if not all([appt_id, new_date, new_time]):
        return {"success": False, "error": "appointment_id, new_date, and new_time are all required."}
    return reschedule_appointment(db, int(appt_id), new_date, new_time)


def _cancel_appointment(args: dict, db: Session) -> dict:
    appt_id = args.get("appointment_id")
    if not appt_id:
        return {"success": False, "error": "appointment_id is required."}
    return cancel_appointment(db, int(appt_id))
