"""
LLM interface — uses Groq free API (llama-3.3-70b-versatile).
Falls back to rule-based logic when API key is not set.

Phase 3 additions:
  - Per-call timing, token, and cost tracking for CLASSic Report
  - Module-level LLM_CALL_LOG for aggregated metrics

To use Groq:
  1. Get a free API key at https://console.groq.com
  2. Set environment variable: export GROQ_API_KEY="gsk_..."
"""

import os
import json
import time
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"   # free tier

# ── Cost estimation (Groq pricing as of 2024) ─────────────────────
# llama-3.3-70b: $0.59/M input tokens, $0.79/M output tokens
_COST_PER_INPUT_TOKEN = 0.59 / 1_000_000
_COST_PER_OUTPUT_TOKEN = 0.79 / 1_000_000

# ── Global call log for CLASSic Report ─────────────────────────────
LLM_CALL_LOG: list[dict] = []

_client = None

def _get_client():
    global _client
    if _client is None and GROQ_API_KEY:
        try:
            from groq import Groq
            _client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            pass
    return _client


def call_llm(system_prompt: str, user_prompt: str,
             temperature: float = 0.3,
             caller: str = "unknown") -> Optional[str]:
    """
    Call Groq LLM. Returns the text response, or None if unavailable.
    Logs timing, token usage, and estimated cost.
    """
    client = _get_client()
    if client is None:
        LLM_CALL_LOG.append({
            "timestamp": datetime.now().isoformat(),
            "caller": caller,
            "model": GROQ_MODEL,
            "status": "SKIPPED",
            "reason": "No API key or client unavailable",
            "duration_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        })
        return None

    start_time = time.time()
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=1500,
        )
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Extract token usage from response
        usage = resp.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = (prompt_tokens * _COST_PER_INPUT_TOKEN +
                          completion_tokens * _COST_PER_OUTPUT_TOKEN)

        LLM_CALL_LOG.append({
            "timestamp": datetime.now().isoformat(),
            "caller": caller,
            "model": GROQ_MODEL,
            "status": "SUCCESS",
            "duration_ms": duration_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
        })

        return resp.choices[0].message.content

    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        LLM_CALL_LOG.append({
            "timestamp": datetime.now().isoformat(),
            "caller": caller,
            "model": GROQ_MODEL,
            "status": "ERROR",
            "error": str(e),
            "duration_ms": duration_ms,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        })
        print(f"  [LLM WARNING] Groq call failed: {e}")
        return None


def call_llm_json(system_prompt: str, user_prompt: str,
                  caller: str = "unknown") -> Optional[dict]:
    """Call LLM and parse JSON from response."""
    raw = call_llm(system_prompt, user_prompt, temperature=0.2, caller=caller)
    if raw is None:
        return None
    # Strip markdown fences
    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


def get_llm_metrics() -> dict:
    """Return aggregated LLM usage metrics for CLASSic Report."""
    if not LLM_CALL_LOG:
        return {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "skipped_calls": 0,
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "calls": [],
        }

    successful = [c for c in LLM_CALL_LOG if c["status"] == "SUCCESS"]
    failed = [c for c in LLM_CALL_LOG if c["status"] == "ERROR"]
    skipped = [c for c in LLM_CALL_LOG if c["status"] == "SKIPPED"]

    latencies = sorted([c["duration_ms"] for c in successful]) if successful else [0]

    return {
        "total_calls": len(LLM_CALL_LOG),
        "successful_calls": len(successful),
        "failed_calls": len(failed),
        "skipped_calls": len(skipped),
        "total_tokens": sum(c["total_tokens"] for c in LLM_CALL_LOG),
        "total_prompt_tokens": sum(c["prompt_tokens"] for c in LLM_CALL_LOG),
        "total_completion_tokens": sum(c["completion_tokens"] for c in LLM_CALL_LOG),
        "total_cost_usd": round(sum(c["estimated_cost_usd"] for c in LLM_CALL_LOG), 4),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "p50_latency_ms": round(latencies[len(latencies) // 2], 2) if latencies else 0,
        "p95_latency_ms": round(latencies[int(len(latencies) * 0.95)], 2) if latencies else 0,
        "calls": LLM_CALL_LOG,
    }


def reset_llm_log():
    """Clear the LLM call log (useful between evaluation runs)."""
    global LLM_CALL_LOG
    LLM_CALL_LOG.clear()
