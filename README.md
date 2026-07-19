# 2care.ai Voice AI Receptionist

A production-grade voice AI receptionist for a multi-branch clinic. Patients call, speak in English or Hindi (or both), and book, reschedule, or cancel appointments — no human involved.

Built for the **2care.ai Voice AI Engineer engineering assignment**.

---

## What's here

| Directory | What it does |
|---|---|
| `backend/` | FastAPI server — Vapi webhooks, booking API, monitoring API |
| `prompts/` | System prompt (v1.2) and Vapi tool definitions |
| `evaluation/` | Scripted test scenarios, eval runner, LLM judge |
| `monitoring/` | Live dashboard, alert rules |
| `scripts/` | Seed data, Vapi assistant setup |
| `docs/WRITEUP.md` | Full write-up — decisions, architecture, what I'd fix |

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/devanshtyagi13/voice-ai-receptionist.git
cd voice-ai-receptionist
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Fill in: VAPI_PRIVATE_KEY, GROQ_API_KEY, WEBHOOK_URL
```

### 3. Seed the database

```bash
python scripts/seed_data.py
```

Seeds 2 branches (Delhi, Mumbai), 4 departments, 8 doctors, and 2 sample patients.

### 4. Run the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs  
Monitoring: http://localhost:8000/monitoring/summary

### 5. Expose publicly (for Vapi webhooks)

```bash
ngrok http 8000
# Copy the https URL → set as WEBHOOK_URL in .env
```

### 6. Create the Vapi assistant

```bash
python scripts/setup_vapi.py create
```

Then go to [vapi.ai](https://vapi.ai) → Phone Numbers → Buy a number → Assign the assistant ID printed above.

### 7. Run the monitoring dashboard

```bash
python monitoring/dashboard.py
# Open http://localhost:8080
```

---

## Run evaluations

```bash
# All scenarios
python evaluation/eval_runner.py

# Single scenario
python evaluation/eval_runner.py --id book_hindi_simple --verbose

# Judge a call transcript
python evaluation/llm_judge.py --call-id <call_id_from_vapi>
```

---

## Docker

```bash
docker-compose up
```

Backend on :8000, dashboard on :8080.

---

## Clinic data

| Branch | City | Departments |
|---|---|---|
| Delhi | Connaught Place | GP, Cardiology, Dermatology, Orthopedics |
| Mumbai | Bandra West | GP, Cardiology, Dermatology, Orthopedics |

Slots: 30-minute intervals, 09:00–17:00, Mon–Sat (varies by doctor).

---

## Architecture

```
Patient call
     │
     ▼
  Vapi (voice platform)
  ├── STT: Deepgram Nova-2 (multi-language, smartFormat)
  ├── LLM: Llama 3.3 70B via Groq
  └── TTS: ElevenLabs
     │
     ▼ tool calls
  FastAPI backend (this repo)
  ├── POST /webhook/vapi      ← Vapi sends all events here
  ├── GET  /api/doctors
  ├── GET  /api/availability/:id
  ├── POST /api/appointments
  ├── GET  /monitoring/summary
  └── SQLite (or Postgres)
     │
     ▼ end-of-call report
  Call log saved → monitoring dashboard updated
```

---

## Prompt logic

See `prompts/system_prompt.md` for the full system prompt.

Key decisions:
- Agent is named "Priya" — gives it a persona without being deceptive
- Language: no gate, just "follow the patient's language" — handles Hinglish naturally
- Confirmation before action: always reads back doctor + date + time before calling `book_appointment`
- Tool call order: `get_doctors` → `check_availability` → confirm → `book_appointment`
- Conflict handling: immediate alternative suggestions without breaking flow

---

## The system around the agent

See `docs/WRITEUP.md` for a full explanation of the lifecycle system:
1. Prompt versioning (git + DB)
2. Pre-ship evaluation (scripted scenarios)
3. Post-call qualitative scoring (LLM judge)
4. Production monitoring (dashboard + alerts)
5. Review-and-fix loop
