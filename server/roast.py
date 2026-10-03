"""Two lines on how obscure or mainstream the result is, from a local Ollama model, with a static fallback."""
import os

import httpx

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

# One line per score decile (0-9, 10-19, ... 90-100): served when the model is unreachable.
BANDS = [
    "Almost nobody's photos land where yours do. You found these corners long before any feed could point you there.",
    "Your taste lives well off the main road. Most people would need a guide to find half of what you're drawn to.",
    "You're drawn to things that take some digging to know about. Recognisable to the initiated, invisible to the rest.",
    "Off the beaten path, with a foot in something people recognise. You explore, but you still bring the others along.",
    "You lean obscure, but not stubbornly so. There's room in your photos for things everyone has heard of.",
    "Right down the middle: half discovery, half what everyone's into. You pick up trends, then wander off from them.",
    "Mostly recognisable, with the odd curveball. You're fluent in the mainstream and occasionally bored by it.",
    "The feed has clearly been taking notes on you. Your photos read like a well-curated version of what's popular.",
    "You and the algorithm agree on nearly everything. What you like is what a lot of people like, and you wear it well.",
    "Peak mainstream. Your taste is the moodboard everyone else is copying, whether they admit it or not.",
]


def fallback(score: int) -> str:
    return BANDS[min(max(score, 0), 100) // 10 if score < 100 else 9]


def statement(score: int, names: list[str], client: httpx.Client | None = None) -> str:
    prompt = (
        f"Score {score}/100 where 0 is the most obscure taste and 100 the most mainstream; aesthetics: {', '.join(names)}. "
        "Write two sentences, 30 to 45 words in total, second person, telling them how obscure or mainstream their "
        "taste is and what that says about them. Never use the word 'niche'. Do not quote the score or any number. "
        "No emoji, no hashtags, no lists, no preamble."
    )
    client = client or httpx.Client(timeout=10)
    try:
        r = client.post(f"{OLLAMA}/api/generate", json={
            "model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.8, "num_predict": 90},
        })
        r.raise_for_status()
        return r.json()["response"].strip() or fallback(score)
    except (httpx.HTTPError, KeyError, ValueError):
        return fallback(score)
