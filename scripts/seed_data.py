"""
Seeds the database with clinic data: 2 branches, 4 departments, doctors.
Run: python scripts/seed_data.py
"""
import sys
import os
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from database import SessionLocal, engine, Base
from models import Branch, Department, Doctor, Patient, Appointment

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def seed():
    if db.query(Branch).count() > 0:
        print("Database already seeded.")
        return

    # Branches
    delhi = Branch(name="Delhi", city="Delhi", address="14 Connaught Place, New Delhi 110001", phone="+911141234567")
    mumbai = Branch(name="Mumbai", city="Mumbai", address="45 Linking Road, Bandra West, Mumbai 400050", phone="+912226789012")
    db.add_all([delhi, mumbai])
    db.flush()

    # Departments
    gp = Department(name="General Practice")
    cardio = Department(name="Cardiology")
    derm = Department(name="Dermatology")
    ortho = Department(name="Orthopedics")
    db.add_all([gp, cardio, derm, ortho])
    db.flush()

    t9 = datetime.time(9, 0)
    t17 = datetime.time(17, 0)
    t9_30 = datetime.time(9, 30)
    t18 = datetime.time(18, 0)

    # Delhi doctors
    docs = [
        Doctor(name="Dr. Priya Sharma", branch_id=delhi.id, department_id=gp.id,
               available_days="Mon,Tue,Wed,Thu,Fri,Sat", slot_duration_minutes=30, start_time=t9, end_time=t17),
        Doctor(name="Dr. Rahul Mehta", branch_id=delhi.id, department_id=cardio.id,
               available_days="Mon,Tue,Wed,Thu,Fri", slot_duration_minutes=30, start_time=t9, end_time=t17),
        Doctor(name="Dr. Anjali Singh", branch_id=delhi.id, department_id=derm.id,
               available_days="Mon,Wed,Fri,Sat", slot_duration_minutes=30, start_time=t9_30, end_time=t17),
        Doctor(name="Dr. Vikram Nair", branch_id=delhi.id, department_id=ortho.id,
               available_days="Tue,Thu,Sat", slot_duration_minutes=30, start_time=t9, end_time=t17),
        # Mumbai doctors
        Doctor(name="Dr. Sneha Patel", branch_id=mumbai.id, department_id=gp.id,
               available_days="Mon,Tue,Wed,Thu,Fri,Sat", slot_duration_minutes=30, start_time=t9, end_time=t18),
        Doctor(name="Dr. Arjun Kapoor", branch_id=mumbai.id, department_id=cardio.id,
               available_days="Mon,Tue,Wed,Fri", slot_duration_minutes=30, start_time=t9, end_time=t17),
        Doctor(name="Dr. Meera Iyer", branch_id=mumbai.id, department_id=derm.id,
               available_days="Mon,Wed,Thu,Sat", slot_duration_minutes=30, start_time=t9, end_time=t17),
        Doctor(name="Dr. Suresh Reddy", branch_id=mumbai.id, department_id=ortho.id,
               available_days="Tue,Wed,Thu,Fri", slot_duration_minutes=30, start_time=t9, end_time=t17),
    ]
    db.add_all(docs)
    db.flush()

    # Sample patients and appointments for testing
    p1 = Patient(name="Amit Kumar", phone="+919876543210")
    p2 = Patient(name="Sunita Rao", phone="+919812345678")
    db.add_all([p1, p2])
    db.flush()

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    day_after = today + datetime.timedelta(days=2)

    appts = [
        Appointment(patient_id=p1.id, doctor_id=docs[0].id, branch_id=delhi.id,
                    date=tomorrow, time=datetime.time(10, 0), status="confirmed"),
        Appointment(patient_id=p2.id, doctor_id=docs[4].id, branch_id=mumbai.id,
                    date=day_after, time=datetime.time(14, 30), status="confirmed"),
    ]
    db.add_all(appts)
    db.commit()

    print("✅ Database seeded successfully!")
    print(f"   Branches: Delhi, Mumbai")
    print(f"   Departments: General Practice, Cardiology, Dermatology, Orthopedics")
    print(f"   Doctors: {len(docs)} total")
    print(f"   Sample patients & appointments added")


if __name__ == "__main__":
    seed()
    db.close()
