# 2care.ai Engineering Assignment — Write-up

**Role applied:** Voice AI Engineer / ML & Backend Engineer  
**Submitted by:** Devansh Tyagi

---

## What I built

### Half 1: The Agent

A voice AI receptionist named **Priya** for a two-branch clinic (Delhi and Mumbai). Patients call a live number, speak in English, Hindi, or Hinglish, and complete appointment actions — booking, rescheduling, cancellation — entirely without human involvement.

**Stack:**
- **Voice platform:** Vapi — chosen over Bolna and Retell because it gives the most control over the model, voice, transcriber, and webhook contract; its tool-calling API is stable and well-documented.
- **LLM:** Llama 3.3 70B via Groq (via Vapi's model config) — best instruction-following for structured tool use, and the only frontier model that handles Hinglish mid-call switching reliably without explicit language tagging.
- **Voice:** ElevenLabs (Nadia voice) — Hindi-capable, natural prosody, low latency on Vapi's infra.
- **Transcriber:** Deepgram Nova-2, language set to `hi` with `smartFormat: true` — handles code-switching better than Whisper at this latency budget.
- **Backend:** FastAPI + SQLAlchemy + SQLite (swap to Postgres for production)
- **Clinic data model:** 2 branches, 4 departments, 8 doctors, 30-minute slot grid 9–17:00

**What the agent can do:**
1. Book a new appointment — collects name, phone, branch, department, date/time preference; checks real availability; confirms; books.
2. Reschedule — looks up patient's appointments, confirms which one, finds new slot, reschedules.
3. Cancel — looks up appointments, confirms, cancels; offers rebooking.
4. Handle slot conflicts — if a slot is taken, immediately offers 2–3 alternatives without breaking the conversation.
5. Handle branch/department discovery — patient can ask "what branches do you have" and the agent answers from live data.

**Why it works in Hindi/Hinglish:**  
The system prompt instructs the model to follow the patient's language without announcement. The Deepgram transcriber handles Hindi characters. Llama 3.3 70B is instructed in the system prompt with example Hinglish phrasing, and naturally mirrors whatever register the patient uses. No language detection gate, no explicit switching — just follow the human.

---

### Half 2: The system around it

The harder half. An agent that books appointments once isn't useful. An agent that keeps working reliably — and gets better when it doesn't — is what the job is actually about.

**The loop I built:**

```
Define → Build → Evaluate → Ship → Watch → Review → Fix → repeat
```

**1. Define (Prompt versioning)**

The system prompt lives in `prompts/system_prompt.md`, version-controlled in git. Each deploy logs the active prompt version to the `prompt_versions` table with a timestamp. I can roll back by redeploying a prior version to Vapi via `scripts/setup_vapi.py`.

Decision: prompt-as-code, not prompt-in-dashboard. When a prompt change causes a regression I can `git blame` it, revert it, and redeploy in 60 seconds. A dashboard change is invisible to git.

**2. Evaluate (before shipping)**

`evaluation/eval_runner.py` runs 8 scripted scenarios against the agent logic — not against the live phone number, but against the same tool-handling code, using Llama 3.3 70B via Groq as the simulated caller. Each scenario defines:
- The conversation turns (user side)
- Which tools should be called
- What the final agent response should contain

Scoring: tool coverage ≥ 80% AND response content checks pass → PASS.

This runs in CI before every prompt change. A prompt that breaks booking in Hindi doesn't ship.

**3. Evaluate (qualitative — after calls)**

`evaluation/llm_judge.py` takes a call transcript and scores it 1–5 on: task completion, naturalness, language adherence, information accuracy, error handling. This is the LLM-as-judge pattern. I run it nightly on the previous day's calls to catch degradation that the binary pass/fail eval misses — things like the agent becoming overly formal, or failing to offer an alternative when a slot is taken.

**4. Ship deliberately**

`scripts/setup_vapi.py` creates or updates the Vapi assistant via API. The script reads the system prompt and tools from files — no copy-pasting into a dashboard. The deploy is one command, logged, repeatable.

**5. Watch (production monitoring)**

Every call end-of-call report from Vapi hits `POST /webhook/vapi`, which saves:
- Full transcript
- Tool calls made
- Outcome (booked/rescheduled/cancelled/failed/no_action) — inferred from the summary
- Duration, cost, recording URL, detected language

The monitoring dashboard (`monitoring/dashboard.py`) shows KPIs in real time: total calls, success rate, avg duration, outcome breakdown, language distribution, recent call list. Auto-refreshes every 30 seconds.

**6. Alert**

`monitoring/alert_rules.py` runs every 15 minutes (cron). It fires on:
- Failure rate > 20% in the last hour (critical)
- Booking rate < 40% in the last 2 hours (warning)
- Zero calls in 4 hours — phone number down (critical)

**7. Review and fix**

The review loop works like this:
1. Each morning, run the LLM judge on the previous day's failed/low-scoring calls.
2. For each issue cluster (e.g., "agent not handling 'kal' correctly as tomorrow"), write a targeted scenario in `evaluation/scenarios.py`.
3. Fix in the system prompt.
4. Evals must pass before redeploying.
5. Deploy. Confirm in monitoring that the metric improves.

---

## Decisions I'd defend

**Why SQLite and not Postgres?**  
For a solo assignment with a single-instance backend, SQLite is zero setup and zero ops. The ORM is identical; switching to Postgres is one env var change. I didn't want infra noise to obscure the logic.

**Why infer outcome from the summary instead of tracking it in tool calls?**  
Vapi's end-of-call report includes a GPT summary. Parsing tool call results from the transcript is fragile — a booking attempt could fail, or the patient could cancel mid-call. The summary is more reliable for reporting; the tool call log is preserved for deeper debugging.

**Why not use a RAG retrieval system for clinic data?**  
The clinic's slot data is live (changes with every booking). RAG retrieves from a static index. Real-time tool calls to a queryable backend are the right pattern here — the agent always sees true availability, never a stale embedding.

**Why LLM-as-judge instead of rule-based scoring?**  
Hinglish naturalness and tone quality can't be rule-matched. An LLM judge evaluates "did this feel like talking to a good receptionist" in a way that regex can't. The tradeoff is cost and occasional inconsistency — mitigated by running it on a sample (failed/short calls first).

---

## What I'd fix next

1. **Postgres + connection pooling** — SQLite won't survive concurrent Vapi webhooks at volume.
2. **Patient verification** — right now, any caller can look up appointments by phone number. In production, send an OTP.
3. **Multi-turn state across intent shifts** — if a patient says "actually, cancel that and book a new one instead," the current prompt handles it most of the time but not always. Needs a dedicated scenario and prompt fix.
4. **Slot recommendation** — instead of asking for date and time preferences separately, infer from context ("after 5pm", "not Monday", "closest to the weekend") and surface the best match.
5. **IVR fallback** — if the agent fails to complete a task in 3 turns, transfer to a human or offer a callback.
6. **Per-doctor breaking availability** — doctors go on leave; the current model assumes the seeded schedule is always true. Real integration would sync from Cliniko's leave management.
7. **A/B prompt testing** — split live traffic between prompt versions and measure booking rate per variant. Currently everything runs on one prompt version.
