"""
Evaluation runner — simulates conversations with the agent using the Groq API
and scores each scenario against expected outcomes and tool calls.

Usage:
  python evaluation/eval_runner.py                  # run all scenarios
  python evaluation/eval_runner.py --id book_english_simple --verbose
"""
import os
import sys
import json
import argparse
import datetime
from pathlib import Path

from groq import Groq

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from database import SessionLocal
from services.vapi_tool_handler import handle_tool_call

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
MODEL = "llama-3.3-70b-versatile"


def load_system_prompt() -> str:
    raw = (PROMPTS_DIR / "system_prompt.md").read_text()
    today = datetime.date.today().isoformat()
    return raw.replace("{{current_date}}", today)


def load_tools() -> list:
    """Load tools in OpenAI format — Groq is fully OpenAI-compatible."""
    return json.loads((PROMPTS_DIR / "tools.json").read_text())


def run_scenario(scenario: dict, verbose: bool = False) -> dict:
    db = SessionLocal()
    try:
        system_prompt = load_system_prompt()
        tools = load_tools()
        messages = [{"role": "system", "content": system_prompt}]
        tool_calls_made = []
        total_tokens = 0

        for turn in scenario["turns"]:
            messages.append({"role": turn["role"], "content": turn["content"]})

            # Agentic loop: keep calling until no more tool calls
            while True:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=1024,
                    temperature=0.3,
                )
                total_tokens += resp.usage.total_tokens
                msg = resp.choices[0].message

                if msg.tool_calls:
                    # Process all tool calls in this response
                    messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                }
                            }
                            for tc in msg.tool_calls
                        ]
                    })

                    for tc in msg.tool_calls:
                        tool_name = tc.function.name
                        try:
                            args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args = {}

                        tool_calls_made.append(tool_name)
                        result = handle_tool_call(tool_name, args, db)

                        if verbose:
                            print(f"  🔧 {tool_name}({json.dumps(args)[:80]})")
                            print(f"     → {json.dumps(result)[:120]}")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result),
                        })
                else:
                    # No more tool calls — agent replied with text
                    agent_text = msg.content or ""
                    messages.append({"role": "assistant", "content": agent_text})
                    if verbose:
                        print(f"  🤖 {agent_text[:200]}")
                    break

        score = _score_scenario(scenario, tool_calls_made, messages)
        return {
            "scenario_id": scenario["id"],
            "description": scenario["description"],
            "passed": score["passed"],
            "tool_calls_made": tool_calls_made,
            "expected_tools": scenario.get("expected_tools", []),
            "tool_coverage": score["tool_coverage"],
            "response_checks": score["response_checks"],
            "total_tokens": total_tokens,
            "turns": len(scenario["turns"]),
        }
    finally:
        db.close()


def _score_scenario(scenario: dict, tool_calls_made: list, messages: list) -> dict:
    expected_tools = set(scenario.get("expected_tools", []))
    actual_tools = set(tool_calls_made)
    # All required tools must have been called (extras are fine)
    covered = expected_tools & actual_tools
    tool_coverage = len(covered) / len(expected_tools) if expected_tools else 1.0

    # Search across ALL assistant messages, not just the last one
    all_agent_text = " ".join(
        m["content"].lower()
        for m in messages
        if m.get("role") == "assistant" and isinstance(m.get("content"), str) and m["content"]
    )

    response_checks = {}
    for phrase in scenario.get("expected_in_response", []):
        response_checks[phrase] = phrase.lower() in all_agent_text

    passed = tool_coverage >= 1.0 and all(response_checks.values())
    return {"passed": passed, "tool_coverage": tool_coverage, "response_checks": response_checks}


def run_all(verbose: bool = False):
    from scenarios import SCENARIOS
    results = []
    print(f"\n{'='*60}")
    print(f"  2care.ai Voice Agent — Evaluation Run (Groq)")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    for scenario in SCENARIOS:
        print(f"▶ {scenario['id']} — {scenario['description'][:50]}...")
        result = run_scenario(scenario, verbose=verbose)
        results.append(result)
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"  {status} | tools: {result['tool_calls_made']} | tokens: {result['total_tokens']}\n")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed ({passed/total*100:.0f}%)")
    print(f"{'='*60}\n")

    output = Path(__file__).parent / "results" / f"eval_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, indent=2))
    print(f"Results saved to: {output}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Run a single scenario by ID")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.id:
        from scenarios import get_scenario
        scenario = get_scenario(args.id)
        if not scenario:
            print(f"Scenario '{args.id}' not found")
            sys.exit(1)
        result = run_scenario(scenario, verbose=True)
        print(json.dumps(result, indent=2))
    else:
        run_all(verbose=args.verbose)
