"""Two lines on how obscure or mainstream the result is, from a local vision-language model behind llama-server
(OpenAI-compatible chat API), looking at the photos with faces blanked. A static fallback covers the model being down."""
import base64
import os
import re

import httpx

LLM_URL = os.environ.get("LLM_URL", "http://localhost:8081")  # llama-server; see deploy/llama-server.service

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
    "them. Roast the taste, not the person: never mention anyone's body, face, hair, makeup, clothing or appearance, "
    "and never guess at identity."
)


def fallback(score: int) -> str:
    return BANDS[min(max(score, 0), 100) // 10 if score < 100 else 9]


def register(score: int) -> str:
    if score < 35:
        return "Register: delighted and a little impressed; this taste is genuinely rare."
    if score < 65:
        return "Register: gentle teasing; they are half explorer, half follower."
    return "Register: a roast. Be pointed and funny about how predictable and algorithm-fed this taste is; no compliments."


def prompt(score: int, names: list[str], with_photos: bool) -> str:
    seen = ("Their photos are attached. You may point to one concrete object, place or texture you see in them. " if with_photos else "")
    return (
        f"This person's taste scored {score} out of 100, where 0 is the most obscure taste in the catalog and 100 "
        f"the most mainstream. The aesthetics their photos matched: {', '.join(names)}.\n{register(score)}\n{seen}"
        "Write exactly two sentences, 30 to 45 words in total, second person. "
        "Neither sentence may begin with the word Your. Start the two sentences with different words. "
        "The first sentence says how obscure or mainstream their taste is and what that suggests about them. "
        "The second may nod to one of the matched aesthetics. Never use the word 'niche'. Never quote a number. "
        "No emoji, hashtags, lists, quotation marks, or preamble; reply with the two sentences only."
    )


def messages(images: list[bytes], text: str) -> list[dict]:
    """Images first, text last: llama-server reuses the cached prefix, so `warm` can encode the photos before the labels exist."""
    content = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}} for b in images]
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content + [{"type": "text", "text": text}]}]


def warm(images: list[bytes], client: httpx.Client | None = None) -> None:
    """Encode the photos into the server's prompt cache while the embedder is still matching them. Best effort."""
    if not images:
        return
    try:
        (client or httpx.Client(timeout=120)).post(f"{LLM_URL}/v1/chat/completions", json={"messages": messages(images, ""), "max_tokens": 1})
    except httpx.HTTPError:
        pass


MIN_WORDS, MAX_SENTENCES = 25, 3


def two_sentences(text: str) -> str:
    """Small models drift past the two-sentence rule. Keep two sentences, or a third when the first two are too short
    to stand alone (a rhetorical "That teacup?" needs its answer)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = []
    for p in parts[:MAX_SENTENCES]:
        kept.append(p)
        if len(kept) >= 2 and sum(len(k.split()) for k in kept) >= MIN_WORDS:
            break
    return " ".join(kept).strip()


def statement(score: int, names: list[str], images: list[bytes] = (), client: httpx.Client | None = None) -> str:
    """`images`: JPEG bytes, already face-masked and downscaled by the caller (see Encoder.preview)."""
    client = client or httpx.Client(timeout=120)  # ~10 s on the GTX 1650 Ti with three 336 px photos, ~3 s after `warm`; longer on CPU
    try:
        r = client.post(f"{LLM_URL}/v1/chat/completions", json={
            "messages": messages(images, prompt(score, names, bool(images))), "max_tokens": 90, "temperature": 0.8,
        })
        r.raise_for_status()
        return two_sentences(r.json()["choices"][0]["message"]["content"]) or fallback(score)
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return fallback(score)
