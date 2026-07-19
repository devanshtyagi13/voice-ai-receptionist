"""
Monitoring dashboard API — call metrics, recent calls, success rates.
"""
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import CallLog, Appointment

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    total_calls = db.query(func.count(CallLog.id)).scalar()
    by_outcome = db.query(CallLog.outcome, func.count(CallLog.id)).group_by(CallLog.outcome).all()
    avg_duration = db.query(func.avg(CallLog.duration_seconds)).scalar()
    total_appointments = db.query(func.count(Appointment.id)).filter(Appointment.status == "confirmed").scalar()

    return {
        "total_calls": total_calls,
        "total_confirmed_appointments": total_appointments,
        "average_call_duration_seconds": round(avg_duration or 0, 1),
        "outcomes": {row[0]: row[1] for row in by_outcome},
        "success_rate": _calc_success_rate(by_outcome, total_calls),
    }


@router.get("/calls")
def list_calls(limit: int = 20, db: Session = Depends(get_db)):
    calls = db.query(CallLog).order_by(CallLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": c.id,
            "call_id": c.call_id,
            "phone_number": c.phone_number,
            "outcome": c.outcome,
            "duration_seconds": c.duration_seconds,
            "language_detected": c.language_detected,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "cost_usd": c.cost_usd,
        }
        for c in calls
    ]


@router.get("/calls/{call_id}/transcript")
def get_transcript(call_id: str, db: Session = Depends(get_db)):
    log = db.query(CallLog).filter(CallLog.call_id == call_id).first()
    if not log:
        return {"error": "Call not found"}
    tool_calls = []
    try:
        tool_calls = json.loads(log.tool_calls_json or "[]")
    except Exception:
        pass
    return {
        "call_id": log.call_id,
        "outcome": log.outcome,
        "transcript": log.transcript,
        "tool_calls": tool_calls,
        "duration_seconds": log.duration_seconds,
        "language_detected": log.language_detected,
    }


@router.get("/language-stats")
def language_stats(db: Session = Depends(get_db)):
    rows = db.query(CallLog.language_detected, func.count(CallLog.id)).group_by(CallLog.language_detected).all()
    return {row[0] or "unknown": row[1] for row in rows}


def _calc_success_rate(by_outcome, total_calls):
    if not total_calls:
        return 0
    success_outcomes = {"booked", "rescheduled", "cancelled"}
    success_count = sum(count for outcome, count in by_outcome if outcome in success_outcomes)
    return round(success_count / total_calls * 100, 1)
