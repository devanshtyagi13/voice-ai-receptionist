"""
Creates or updates the Vapi assistant using the Vapi API.
Run: python scripts/setup_vapi.py

Requires: VAPI_API_KEY in environment.
"""
import os
import json
import requests
from pathlib import Path

VAPI_API_KEY = os.environ.get("VAPI_PRIVATE_KEY", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-server.com/webhook/vapi")

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_system_prompt():
    return (PROMPTS_DIR / "system_prompt.md").read_text()


def load_tools():
    return json.loads((PROMPTS_DIR / "tools.json").read_text())


def create_assistant():
    if not VAPI_API_KEY:
        print("❌ VAPI_PRIVATE_KEY not set. Export it and rerun.")
        return

    system_prompt = load_system_prompt()
    tools = load_tools()

    payload = {
        "name": "2care.ai Receptionist",
        "firstMessage": "Namaste! 2care.ai clinics mein aapka swagat hai. Main Priya bol rahi hoon. Kya main aapki appointment book karne mein madad kar sakti hoon?",
        "model": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "systemPrompt": system_prompt,
            "tools": tools,
            "temperature": 0.3,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "burt",
            "stability": 0.5,
            "similarityBoost": 0.75,
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "multi",
            "smartFormat": True,
        },
        "serverUrl": WEBHOOK_URL,
        "serverUrlSecret": os.environ.get("WEBHOOK_SECRET", ""),
        "endCallMessage": "Thank you for calling 2care.ai. Have a healthy day!",
        "endCallPhrases": [
            "goodbye", "bye", "alvida", "shukriya", "theek hai bye"
        ],
        "backgroundSound": "off",
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 600,
        "clientMessages": ["transcript", "function-call", "hang"],
        "serverMessages": ["end-of-call-report", "function-call", "hang"],
    }

    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.post("https://api.vapi.ai/assistant", json=payload, headers=headers)
    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"✅ Assistant created! ID: {data['id']}")
        print(f"   Name: {data['name']}")
        print(f"\nNext step: Create a phone number in Vapi dashboard and assign assistant ID: {data['id']}")
        return data["id"]
    else:
        print(f"❌ Error: {resp.status_code} — {resp.text}")
        return None


def list_assistants():
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
    resp = requests.get("https://api.vapi.ai/assistant", headers=headers)
    if resp.status_code == 200:
        for a in resp.json():
            print(f"  {a['id']} — {a['name']}")
    else:
        print(f"Error: {resp.status_code} — {resp.text}")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    if cmd == "create":
        create_assistant()
    elif cmd == "list":
        list_assistants()
    else:
        print("Usage: python setup_vapi.py [create|list]")
