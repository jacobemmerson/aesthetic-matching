"""Two lines on how obscure or mainstream the result is, from a local Ollama model, with a static fallback."""
import os

import httpx

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")  # Ollama's default tag is the Q4_K_M quant

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


SYSTEM = (
    "You are the voice of a playful web quiz that places people's photos on a map of internet aesthetics. "
    "You are a sharp, well-read culture critic with a dry sense of humour: specific, never cruel, never corporate. "
    "Your tone follows the score. Obscure taste (low score) genuinely delights you: be warm, a little impressed, "
    "curious about where they found it. Middling taste gets gentle teasing. Mainstream taste (high score) gets a "
    "roast: affectionate but pointed, the kind a friend would deliver, poking at how predictable the feed has made "
    "them. Never insult appearance, identity, or intelligence; roast the taste, not the person."
)


def fallback(score: int) -> str:
    return BANDS[min(max(score, 0), 100) // 10 if score < 100 else 9]


def register(score: int) -> str:
    if score < 35:
        return "Register: delighted and a little impressed; this taste is genuinely rare."
    if score < 65:
        return "Register: gentle teasing; they are half explorer, half follower."
    return "Register: a roast. Be pointed and funny about how predictable and algorithm-fed this taste is; no compliments."


def statement(score: int, names: list[str], client: httpx.Client | None = None) -> str:
    prompt = (
        f"This person's taste scored {score} out of 100, where 0 is the most obscure taste in the catalog and 100 "
        f"the most mainstream. The aesthetics their photos matched: {', '.join(names)}.\n{register(score)}\n"
        "Write exactly two sentences, 30 to 45 words in total, second person. "
        "The first sentence says how obscure or mainstream their taste is and what that suggests about them. "
        "The second may nod to one of the matched aesthetics. Never use the word 'niche'. Never quote a number. "
        "No emoji, hashtags, lists, quotation marks, or preamble; reply with the two sentences only."
    )
    client = client or httpx.Client(timeout=60)  # the 8B model takes ~15 s on CPU, more on a cold load
    try:
        r = client.post(f"{OLLAMA}/api/generate", json={
            "model": MODEL, "system": SYSTEM, "prompt": prompt, "stream": False, "keep_alive": "1h",  # stay loaded between visitors
            "options": {"temperature": 0.8, "num_predict": 90},
        })
        r.raise_for_status()
        return r.json()["response"].strip() or fallback(score)
    except (httpx.HTTPError, KeyError, ValueError):
        return fallback(score)
