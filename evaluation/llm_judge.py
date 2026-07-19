"""
LLM-as-judge for qualitative evaluation of call transcripts.
Uses Groq (llama-3.3-70b) to score transcripts on key quality dimensions.

Usage:
  python evaluation/llm_judge.py --call-id <call_id>
  python evaluation/llm_judge.py --transcript "AGENT: ... USER: ..."
"""
import os
import sys
import json
import argparse
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
MODEL = "llama-3.3-70b-versatile"

JUDGE_PROMPT = """You are evaluating a voice AI receptionist call at a medical clinic.

The agent's job:
- Help patients book, reschedule, or cancel appointments
- Speak naturally in English, Hindi, or a mix (Hinglish)
- Collect patient name + phone, confirm details before acting
- Never make up slots or doctor names

Evaluate the transcript below on these dimensions (score each 1-5):

1. task_completion — Did the agent successfully complete what the patient asked?
2. naturalness — Did the conversation feel natural and human, not robotic?
3. language_adherence — Did the agent correctly match the patient's language or mix?
4. information_accuracy — Did the agent confirm accurate details (no hallucinated slots/names)?
5. error_handling — How well did the agent handle confusion, conflicts, or errors?

Also provide:
- overall_score: weighted average (task_completion x0.4 + naturalness x0.2 + information_accuracy x0.2 + error_handling x0.1 + language_adherence x0.1)
- outcome: one of: booked / rescheduled / cancelled / no_action / failed
- issues: list of specific problems found (empty list if none)
- highlights: list of things done well

Respond ONLY with a valid JSON object, no markdown, no explanation.

TRANSCRIPT:
{transcript}
"""


def judge_transcript(transcript: str) -> dict:
    prompt = JUDGE_PROMPT.format(transcript=transcript)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse judge response", "raw": text}


def judge_call_from_db(call_id: str) -> dict:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from database import SessionLocal
    from models import CallLog

    db = SessionLocal()
    try:
        log = db.query(CallLog).filter(CallLog.call_id == call_id).first()
        if not log:
            return {"error": f"Call {call_id} not found"}
        result = judge_transcript(log.transcript or "")
        result["call_id"] = call_id
        result["stored_outcome"] = log.outcome
        return result
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--call-id", help="Judge a stored call by ID")
    parser.add_argument("--transcript", help="Judge a raw transcript string")
    args = parser.parse_args()

    if args.call_id:
        result = judge_call_from_db(args.call_id)
    elif args.transcript:
        result = judge_transcript(args.transcript)
    else:
        print("Provide --call-id or --transcript")
        sys.exit(1)

    print(json.dumps(result, indent=2))
