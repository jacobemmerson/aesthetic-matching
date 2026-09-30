"""One humorous verdict from a local Ollama model, given the matched aesthetics."""
import os

import httpx

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
FALLBACK = "The oracle is asleep. Your aesthetic remains a mystery, which is honestly a look in itself."

SYSTEM = (
    "You are a snarky but affectionate fashion and lifestyle critic who has seen every internet aesthetic. "
    "You are given the aesthetics a person's photos matched. Write ONE verdict of about 100 words, second person, "
    "roasting them with specific, playful jabs drawn from the aesthetic descriptions. Name the top aesthetic and at "
    "least one other. No lists, no headings, no hashtags, no emoji, no disclaimers."
)


def build_prompt(overall: list[dict], per_image: list[str], nodes: dict[str, dict]) -> str:
    lines = ["Overall matched aesthetics, strongest first:"]
    for i, m in enumerate(overall, 1):
        n = nodes[m["slug"]]
        lines.append(f"{i}. {n['name']}: {n['description'][:400]}")
        if n.get("key_values"):
            lines.append(f"   values: {n['key_values'][:200]}")
    lines.append(f"Per-photo top matches: {', '.join(per_image)}.")
    lines.append("Write the verdict now.")
    return "\n".join(lines)


def roast(prompt: str, client: httpx.Client | None = None) -> str:
    client = client or httpx.Client(timeout=90)
    try:
        r = client.post(f"{OLLAMA}/api/generate", json={
            "model": MODEL, "system": SYSTEM, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.9, "num_predict": 220},
        })
        r.raise_for_status()
        return r.json()["response"].strip() or FALLBACK
    except (httpx.HTTPError, KeyError, ValueError):
        return FALLBACK
