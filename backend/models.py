import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, Time
from sqlalchemy.orm import relationship
from database import Base


class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String)
    city = Column(String)
    phone = Column(String)
    doctors = relationship("Doctor", back_populates="branch")


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    doctors = relationship("Doctor", back_populates="department")


class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    available_days = Column(String, default="Mon,Tue,Wed,Thu,Fri,Sat")
    slot_duration_minutes = Column(Integer, default=30)
    start_time = Column(Time, default=datetime.time(9, 0))
    end_time = Column(Time, default=datetime.time(17, 0))
    branch = relationship("Branch", back_populates="doctors")
    department = relationship("Department", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True)
    appointments = relationship("Appointment", back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    branch_id = Column(Integer, ForeignKey("branches.id"))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    status = Column(String, default="confirmed")  # confirmed, cancelled, completed
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    branch = relationship("Branch")


class CallLog(Base):
    __tablename__ = "call_logs"
    id = Column(Integer, primary_key=True)
    call_id = Column(String, unique=True)
    phone_number = Column(String)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    transcript = Column(Text)
    outcome = Column(String)  # booked, rescheduled, cancelled, failed, no_action
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    language_detected = Column(String)
    tool_calls_json = Column(Text)
    cost_usd = Column(String)
    recording_url = Column(String)
    error_details = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id = Column(Integer, primary_key=True)
    version = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    tools_json = Column(Text)
    notes = Column(Text)
    is_active = Column(Integer, default=0)
    deployed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
