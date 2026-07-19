"""
Alert rules — checks recent call metrics and prints/sends alerts when thresholds are crossed.
Designed to be run as a cron job: */15 * * * * python monitoring/alert_rules.py
"""
import sys
import json
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from database import SessionLocal
from models import CallLog
from sqlalchemy import func

RULES = [
    {
        "name": "High failure rate",
        "description": "More than 20% of calls in the last hour failed",
        "severity": "critical",
    },
    {
        "name": "Low booking rate",
        "description": "Less than 40% of calls resulted in a booking in the last 2 hours",
        "severity": "warning",
    },
    {
        "name": "No calls in 4 hours",
        "description": "No calls received — phone number may be down",
        "severity": "critical",
    },
]


def check_alerts():
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        one_hour_ago = now - datetime.timedelta(hours=1)
        two_hours_ago = now - datetime.timedelta(hours=2)
        four_hours_ago = now - datetime.timedelta(hours=4)

        alerts = []

        # Check failure rate last hour
        recent = db.query(CallLog).filter(CallLog.created_at >= one_hour_ago).all()
        if recent:
            failed = sum(1 for c in recent if c.outcome == "failed")
            failure_rate = failed / len(recent)
            if failure_rate > 0.2:
                alerts.append({
                    "rule": "High failure rate",
                    "severity": "critical",
                    "detail": f"{failure_rate*100:.1f}% failure rate in the last hour ({failed}/{len(recent)} calls)",
                })

        # Check booking rate last 2 hours
        recent_2h = db.query(CallLog).filter(CallLog.created_at >= two_hours_ago).all()
        if len(recent_2h) >= 5:
            booked = sum(1 for c in recent_2h if c.outcome == "booked")
            booking_rate = booked / len(recent_2h)
            if booking_rate < 0.4:
                alerts.append({
                    "rule": "Low booking rate",
                    "severity": "warning",
                    "detail": f"Only {booking_rate*100:.1f}% booking rate in the last 2 hours",
                })

        # Check if any calls in 4 hours
        count_4h = db.query(func.count(CallLog.id)).filter(
            CallLog.created_at >= four_hours_ago
        ).scalar()
        if count_4h == 0:
            alerts.append({
                "rule": "No calls in 4 hours",
                "severity": "critical",
                "detail": "Zero calls in the last 4 hours — check if phone number is active",
            })

        if alerts:
            print(f"🚨 ALERTS at {now.strftime('%Y-%m-%d %H:%M UTC')}:")
            for a in alerts:
                emoji = "🔴" if a["severity"] == "critical" else "🟡"
                print(f"  {emoji} [{a['severity'].upper()}] {a['rule']}: {a['detail']}")
        else:
            print(f"✅ All clear at {now.strftime('%Y-%m-%d %H:%M UTC')}")

        return alerts
    finally:
        db.close()


if __name__ == "__main__":
    alerts = check_alerts()
    sys.exit(1 if any(a["severity"] == "critical" for a in alerts) else 0)
