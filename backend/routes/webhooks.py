"""
Vapi webhook handler.
Vapi sends POST requests to this endpoint for all call events.
"""
import json
import datetime
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import CallLog
from services.vapi_tool_handler import handle_tool_call

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/vapi")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type")

    if msg_type == "assistant-request":
        # Return the assistant configuration (optional if using Vapi dashboard)
        return {"assistant": None}  # Use the pre-configured assistant

    elif msg_type == "function-call":
        function_call = message.get("functionCall", {})
        tool_name = function_call.get("name")
        params = function_call.get("parameters", {})

        result = handle_tool_call(tool_name, params, db)
        return {"result": json.dumps(result)}

    elif msg_type == "tool-calls":
        # Newer Vapi API format
        tool_calls = message.get("toolCallList", [])
        results = []
        for tc in tool_calls:
            fn = tc.get("function", {})
            tool_name = fn.get("name")
            try:
                params = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                params = {}
            result = handle_tool_call(tool_name, params, db)
            results.append({
                "toolCallId": tc.get("id"),
                "result": json.dumps(result)
            })
        return {"results": results}

    elif msg_type == "end-of-call-report":
        _save_call_log(message, db)
        return {"status": "ok"}

    elif msg_type == "hang":
        return {"status": "ok"}

    return {"status": "ok"}


def _save_call_log(message: dict, db: Session):
    try:
        call = message.get("call", {})
        artifact = message.get("artifact", {})
        analysis = message.get("analysis", {})

        transcript_messages = artifact.get("messages", [])
        transcript_text = "\n".join(
            f"{m.get('role', 'unknown').upper()}: {m.get('content', '')}"
            for m in transcript_messages
            if isinstance(m.get("content"), str)
        )

        tool_calls = [m for m in transcript_messages if m.get("role") == "tool_call"]

        started = call.get("startedAt")
        ended = call.get("endedAt")
        duration = None
        if started and ended:
            try:
                s = datetime.datetime.fromisoformat(started.replace("Z", "+00:00"))
                e = datetime.datetime.fromisoformat(ended.replace("Z", "+00:00"))
                duration = int((e - s).total_seconds())
            except Exception:
                pass

        # Determine outcome from summary
        summary = analysis.get("summary", "").lower()
        outcome = "no_action"
        if "booked" in summary or "appointment confirmed" in summary:
            outcome = "booked"
        elif "rescheduled" in summary:
            outcome = "rescheduled"
        elif "cancelled" in summary:
            outcome = "cancelled"
        elif "failed" in summary or "error" in summary:
            outcome = "failed"

        log = CallLog(
            call_id=call.get("id", ""),
            phone_number=call.get("customer", {}).get("number", ""),
            started_at=datetime.datetime.fromisoformat(started.replace("Z", "+00:00")) if started else None,
            ended_at=datetime.datetime.fromisoformat(ended.replace("Z", "+00:00")) if ended else None,
            duration_seconds=duration,
            transcript=transcript_text,
            outcome=outcome,
            language_detected=_detect_language(transcript_text),
            tool_calls_json=json.dumps(tool_calls),
            cost_usd=str(message.get("cost", "")),
            recording_url=artifact.get("recordingUrl", ""),
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Error saving call log: {e}")


def _detect_language(transcript: str) -> str:
    hindi_chars = sum(1 for c in transcript if "ऀ" <= c <= "ॿ")
    if hindi_chars > 20:
        return "hindi"
    if hindi_chars > 5:
        return "mixed"
    return "english"
