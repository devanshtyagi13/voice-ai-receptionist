"""
Standalone monitoring dashboard — serves a simple HTML page summarizing call metrics.
Reads directly from the SQLite database.

Run: python monitoring/dashboard.py
Open: http://localhost:8080
"""
import sys
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from database import SessionLocal
from models import CallLog, Appointment
from sqlalchemy import func


def get_stats():
    db = SessionLocal()
    try:
        total_calls = db.query(func.count(CallLog.id)).scalar() or 0
        by_outcome = dict(
            db.query(CallLog.outcome, func.count(CallLog.id))
            .group_by(CallLog.outcome).all()
        )
        by_language = dict(
            db.query(CallLog.language_detected, func.count(CallLog.id))
            .group_by(CallLog.language_detected).all()
        )
        avg_dur = db.query(func.avg(CallLog.duration_seconds)).scalar() or 0
        total_appts = db.query(func.count(Appointment.id)).filter(
            Appointment.status == "confirmed"
        ).scalar() or 0

        recent = db.query(CallLog).order_by(CallLog.created_at.desc()).limit(10).all()
        recent_list = [
            {
                "call_id": c.call_id[:12] + "..." if c.call_id else "—",
                "phone": c.phone_number or "—",
                "outcome": c.outcome or "—",
                "duration": f"{c.duration_seconds}s" if c.duration_seconds else "—",
                "language": c.language_detected or "—",
                "started_at": c.started_at.strftime("%Y-%m-%d %H:%M") if c.started_at else "—",
            }
            for c in recent
        ]

        success = sum(v for k, v in by_outcome.items() if k in {"booked", "rescheduled", "cancelled"})
        success_rate = round(success / total_calls * 100, 1) if total_calls else 0

        return {
            "total_calls": total_calls,
            "total_appointments": total_appts,
            "avg_duration": round(avg_dur, 1),
            "success_rate": success_rate,
            "by_outcome": by_outcome,
            "by_language": by_language,
            "recent": recent_list,
        }
    finally:
        db.close()


def render_html(stats: dict) -> str:
    outcome_rows = "".join(
        f"<tr><td>{k or 'unknown'}</td><td>{v}</td></tr>"
        for k, v in stats["by_outcome"].items()
    )
    language_rows = "".join(
        f"<tr><td>{k or 'unknown'}</td><td>{v}</td></tr>"
        for k, v in stats["by_language"].items()
    )
    recent_rows = "".join(
        f"<tr><td>{r['started_at']}</td><td>{r['phone']}</td>"
        f"<td><span class='badge {r['outcome']}'>{r['outcome']}</span></td>"
        f"<td>{r['duration']}</td><td>{r['language']}</td></tr>"
        for r in stats["recent"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>2care.ai Voice AI — Monitoring</title>
<meta http-equiv="refresh" content="30">
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; background: #f8fafc; color: #1e293b; }}
  header {{ background: #0f172a; color: white; padding: 16px 32px; }}
  header h1 {{ margin: 0; font-size: 1.2rem; font-weight: 600; }}
  header p {{ margin: 4px 0 0; font-size: 0.85rem; opacity: 0.7; }}
  .container {{ max-width: 1100px; margin: 32px auto; padding: 0 24px; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .kpi {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .kpi .value {{ font-size: 2rem; font-weight: 700; color: #0ea5e9; }}
  .kpi .label {{ font-size: 0.8rem; color: #64748b; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .card h3 {{ margin: 0 0 16px; font-size: 0.95rem; color: #475569; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th {{ text-align: left; padding: 8px 12px; border-bottom: 2px solid #e2e8f0; font-weight: 600; color: #475569; font-size: 0.8rem; text-transform: uppercase; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }}
  tr:last-child td {{ border-bottom: none; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
  .badge.booked {{ background: #dcfce7; color: #166534; }}
  .badge.rescheduled {{ background: #dbeafe; color: #1d4ed8; }}
  .badge.cancelled {{ background: #fee2e2; color: #991b1b; }}
  .badge.failed {{ background: #fef3c7; color: #92400e; }}
  .badge.no_action {{ background: #f1f5f9; color: #64748b; }}
  .full {{ grid-column: 1 / -1; }}
  .refresh {{ font-size: 0.75rem; color: #94a3b8; }}
</style>
</head>
<body>
<header>
  <h1>2care.ai Voice AI — Live Monitoring</h1>
  <p class="refresh">Auto-refreshes every 30 seconds</p>
</header>
<div class="container">
  <div class="kpi-row">
    <div class="kpi"><div class="value">{stats['total_calls']}</div><div class="label">Total Calls</div></div>
    <div class="kpi"><div class="value">{stats['total_appointments']}</div><div class="label">Active Appointments</div></div>
    <div class="kpi"><div class="value">{stats['success_rate']}%</div><div class="label">Task Success Rate</div></div>
    <div class="kpi"><div class="value">{stats['avg_duration']}s</div><div class="label">Avg Call Duration</div></div>
  </div>
  <div class="grid">
    <div class="card">
      <h3>Outcomes</h3>
      <table><thead><tr><th>Outcome</th><th>Count</th></tr></thead>
      <tbody>{outcome_rows}</tbody></table>
    </div>
    <div class="card">
      <h3>Language Distribution</h3>
      <table><thead><tr><th>Language</th><th>Count</th></tr></thead>
      <tbody>{language_rows}</tbody></table>
    </div>
    <div class="card full">
      <h3>Recent Calls</h3>
      <table>
        <thead><tr><th>Time</th><th>Phone</th><th>Outcome</th><th>Duration</th><th>Language</th></tr></thead>
        <tbody>{recent_rows}</tbody>
      </table>
    </div>
  </div>
</div>
</body></html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif path == "/api/stats":
            stats = get_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
        else:
            stats = get_stats()
            html = render_html(stats)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # suppress default access logs


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"📊 Monitoring dashboard running at http://localhost:{port}")
    HTTPServer(("", port), DashboardHandler).serve_forever()
