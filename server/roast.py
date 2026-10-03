"""One short line on how niche the result is, from a local Ollama model, with a static fallback."""
import os

import httpx

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

# One line per score decile (0-9, 10-19, ... 90-100): served when the model is unreachable.
BANDS = [
    "Wow. Genuinely niche: almost nobody's photos land here.",
    "Deeply niche. Your taste lives in the corners of the map.",
    "Properly niche. You found this before the algorithm did.",
    "Off the beaten path, with a foot in something people recognise.",
    "A little niche. You lean obscure but you still go outside.",
    "Right in the middle: half discovery, half what everyone's into.",
    "A little mainstream. Recognisable, with the odd curveball.",
    "Mostly mainstream. The feed has clearly been taking notes on you.",
    "Trendy. You and the algorithm agree on nearly everything.",
    "Peak mainstream. Your taste is the moodboard everyone else copies.",
]


def fallback(score: int) -> str:
    return BANDS[min(max(score, 0), 100) // 10 if score < 100 else 9]


def statement(score: int, names: list[str], client: httpx.Client | None = None) -> str:
    prompt = (
        f"Score {score}/100 where 0 is the most niche and 100 the most mainstream; aesthetics: {', '.join(names)}. "
        "Write ONE sentence, under 20 words, second person, telling them how niche or mainstream their taste is. "
        "No emoji, no hashtags, no lists, no preamble."
    )
    client = client or httpx.Client(timeout=10)
    try:
        r = client.post(f"{OLLAMA}/api/generate", json={
            "model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.8, "num_predict": 40},
        })
        r.raise_for_status()
        return r.json()["response"].strip() or fallback(score)
    except (httpx.HTTPError, KeyError, ValueError):
        return fallback(score)
