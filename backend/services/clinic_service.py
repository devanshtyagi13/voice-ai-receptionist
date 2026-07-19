import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models import Branch, Department, Doctor, Patient, Appointment


def get_all_branches(db: Session):
    branches = db.query(Branch).all()
    return [{"id": b.id, "name": b.name, "city": b.city, "address": b.address, "phone": b.phone} for b in branches]


def get_doctors(db: Session, branch_name: Optional[str] = None, department_name: Optional[str] = None):
    q = db.query(Doctor).join(Branch).join(Department)
    if branch_name:
        q = q.filter(Branch.name.ilike(f"%{branch_name}%"))
    if department_name:
        q = q.filter(Department.name.ilike(f"%{department_name}%"))
    doctors = q.all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "branch": d.branch.name,
            "department": d.department.name,
            "available_days": d.available_days,
            "slot_duration_minutes": d.slot_duration_minutes,
        }
        for d in doctors
    ]


def get_available_slots(db: Session, doctor_id: int, date_str: str):
    try:
        date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return {"error": "Doctor not found"}

    day_name = date.strftime("%a")  # Mon, Tue, etc.
    if day_name not in doctor.available_days:
        return {"available_slots": [], "message": f"Dr. {doctor.name} is not available on {day_name}"}

    # Generate all slots for the day
    slots = []
    current = datetime.datetime.combine(date, doctor.start_time)
    end = datetime.datetime.combine(date, doctor.end_time)
    delta = datetime.timedelta(minutes=doctor.slot_duration_minutes)
    while current + delta <= end:
        slots.append(current.time())
        current += delta

    # Remove booked slots
    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == date,
        Appointment.status == "confirmed"
    ).all()
    booked_times = {a.time for a in booked}
    available = [s.strftime("%H:%M") for s in slots if s not in booked_times]
    return {"doctor": doctor.name, "date": date_str, "available_slots": available}


def find_or_create_patient(db: Session, name: str, phone: str) -> Patient:
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        patient = Patient(name=name, phone=phone)
        db.add(patient)
        db.commit()
        db.refresh(patient)
    return patient


def book_appointment(
    db: Session,
    patient_name: str,
    patient_phone: str,
    doctor_id: int,
    date_str: str,
    time_str: str,
    notes: str = ""
):
    try:
        date = datetime.date.fromisoformat(date_str)
        time = datetime.time.fromisoformat(time_str)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return {"success": False, "error": "Doctor not found"}

    # Check slot is available
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == date,
        Appointment.time == time,
        Appointment.status == "confirmed"
    ).first()
    if conflict:
        return {"success": False, "error": "This slot is already booked. Please choose another time."}

    patient = find_or_create_patient(db, patient_name, patient_phone)
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor_id,
        branch_id=doctor.branch_id,
        date=date,
        time=time,
        notes=notes,
        status="confirmed"
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return {
        "success": True,
        "appointment_id": appt.id,
        "doctor": doctor.name,
        "branch": doctor.branch.name,
        "department": doctor.department.name,
        "date": date_str,
        "time": time_str,
        "patient": patient_name,
        "message": f"Appointment confirmed with {doctor.name} at {doctor.branch.name} on {date_str} at {time_str}."
    }


def get_patient_appointments(db: Session, patient_phone: str):
    patient = db.query(Patient).filter(Patient.phone == patient_phone).first()
    if not patient:
        return {"appointments": [], "message": "No patient found with this phone number."}

    upcoming = db.query(Appointment).filter(
        Appointment.patient_id == patient.id,
        Appointment.status == "confirmed",
        Appointment.date >= datetime.date.today()
    ).order_by(Appointment.date, Appointment.time).all()

    return {
        "patient": patient.name,
        "appointments": [
            {
                "id": a.id,
                "doctor": a.doctor.name,
                "department": a.doctor.department.name,
                "branch": a.branch.name,
                "date": a.date.isoformat(),
                "time": a.time.strftime("%H:%M"),
                "status": a.status,
            }
            for a in upcoming
        ]
    }


def reschedule_appointment(db: Session, appointment_id: int, new_date_str: str, new_time_str: str):
    try:
        new_date = datetime.date.fromisoformat(new_date_str)
        new_time = datetime.time.fromisoformat(new_time_str)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        return {"success": False, "error": "Appointment not found"}
    if appt.status != "confirmed":
        return {"success": False, "error": "Appointment is not active"}

    # Check new slot availability
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == appt.doctor_id,
        Appointment.date == new_date,
        Appointment.time == new_time,
        Appointment.status == "confirmed",
        Appointment.id != appointment_id
    ).first()
    if conflict:
        return {"success": False, "error": "The new slot is already taken. Please choose another time."}

    old_date = appt.date.isoformat()
    old_time = appt.time.strftime("%H:%M")
    appt.date = new_date
    appt.time = new_time
    db.commit()
    return {
        "success": True,
        "appointment_id": appt.id,
        "doctor": appt.doctor.name,
        "branch": appt.branch.name,
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date_str,
        "new_time": new_time_str,
        "message": f"Appointment rescheduled to {new_date_str} at {new_time_str} with {appt.doctor.name}."
    }


def cancel_appointment(db: Session, appointment_id: int):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        return {"success": False, "error": "Appointment not found"}
    if appt.status != "confirmed":
        return {"success": False, "error": "Appointment is already cancelled or completed"}

    appt.status = "cancelled"
    db.commit()
    return {
        "success": True,
        "appointment_id": appt.id,
        "message": f"Appointment with {appt.doctor.name} on {appt.date.isoformat()} at {appt.time.strftime('%H:%M')} has been cancelled."
    }
