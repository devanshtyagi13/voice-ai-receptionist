from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from services.clinic_service import (
    get_all_branches,
    get_doctors,
    get_available_slots,
    book_appointment,
    get_patient_appointments,
    reschedule_appointment,
    cancel_appointment,
)

router = APIRouter(prefix="/api", tags=["appointments"])


class BookRequest(BaseModel):
    patient_name: str
    patient_phone: str
    doctor_id: int
    date: str
    time: str
    notes: Optional[str] = ""


class RescheduleRequest(BaseModel):
    new_date: str
    new_time: str


@router.get("/branches")
def list_branches(db: Session = Depends(get_db)):
    return get_all_branches(db)


@router.get("/doctors")
def list_doctors(
    branch: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return get_doctors(db, branch_name=branch, department_name=department)


@router.get("/availability/{doctor_id}")
def check_slot_availability(doctor_id: int, date: str, db: Session = Depends(get_db)):
    return get_available_slots(db, doctor_id, date)


@router.post("/appointments")
def create_appointment(req: BookRequest, db: Session = Depends(get_db)):
    result = book_appointment(
        db, req.patient_name, req.patient_phone, req.doctor_id, req.date, req.time, req.notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/appointments/patient/{phone}")
def patient_appointments(phone: str, db: Session = Depends(get_db)):
    return get_patient_appointments(db, phone)


@router.patch("/appointments/{appointment_id}/reschedule")
def reschedule(appointment_id: int, req: RescheduleRequest, db: Session = Depends(get_db)):
    result = reschedule_appointment(db, appointment_id, req.new_date, req.new_time)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.delete("/appointments/{appointment_id}")
def cancel(appointment_id: int, db: Session = Depends(get_db)):
    result = cancel_appointment(db, appointment_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
