"""
LLM interface — uses Groq free API (llama-3.3-70b-versatile).
Falls back to rule-based logic when API key is not set.

To use Groq:
  1. Get a free API key at https://console.groq.com
  2. Set environment variable: export GROQ_API_KEY="gsk_..."
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"   # free tier

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
             temperature: float = 0.3) -> Optional[str]:
    """
    Call Groq LLM. Returns the text response, or None if unavailable.
    """
    client = _get_client()
    if client is None:
        return None
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
        return resp.choices[0].message.content
    except Exception as e:
        print(f"  [LLM WARNING] Groq call failed: {e}")
        return None


def call_llm_json(system_prompt: str, user_prompt: str) -> Optional[dict]:
    """Call LLM and parse JSON from response."""
    raw = call_llm(system_prompt, user_prompt, temperature=0.2)
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
