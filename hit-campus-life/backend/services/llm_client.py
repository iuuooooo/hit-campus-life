from __future__ import annotations

import os
import json
import urllib.request
import urllib.error


def call_openai_compatible_chat(prompt: str) -> str | None:
    """Call an OpenAI-compatible chat completion API.

    Configure with environment variables:
    LLM_API_KEY=xxx
    LLM_BASE_URL=https://api.example.com/v1
    LLM_MODEL=some-free-open-model

    The function intentionally fails closed. If no key or network/API error occurs,
    the caller should fall back to deterministic rule-based matching.
    """
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    model = os.getenv("LLM_MODEL", "").strip()
    if not api_key or not base_url or not model:
        return None

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是校园搭子匹配助手，只输出简短、克制、可解释的中文建议。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 260,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw)
            return body["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError):
        return None
