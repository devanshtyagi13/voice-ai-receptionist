import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from database import engine, Base
from routes.webhooks import router as webhook_router
from routes.appointments import router as appointments_router
from routes.monitoring import router as monitoring_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="2care.ai Voice AI Receptionist",
    description="Backend for the clinic voice AI agent — booking, rescheduling, cancellations.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(appointments_router)
app.include_router(monitoring_router)


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><body>
    <h2>2care.ai Voice AI Receptionist — Backend</h2>
    <ul>
      <li><a href="/docs">API Docs (Swagger)</a></li>
      <li><a href="/monitoring/summary">Monitoring Summary</a></li>
      <li><a href="/monitoring/calls">Recent Calls</a></li>
      <li><a href="/api/branches">Branches</a></li>
      <li><a href="/api/doctors">Doctors</a></li>
    </ul>
    </body></html>
    """


@app.get("/health")
def health():
    return {"status": "ok", "service": "voice-ai-receptionist"}
