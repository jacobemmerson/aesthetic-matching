import json

import httpx

from server.roast import BANDS, fallback, prompt, register, statement, two_sentences, warm


class FakeClient:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.sent = text, error, None

    def post(self, url, json=None, **k):
        self.sent = json
        if self.error:
            raise self.error
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": self.text}}]}, request=httpx.Request("POST", url))


def test_fallback_picks_the_band():
    assert len(BANDS) == 10
    assert fallback(0) == BANDS[0] and fallback(9) == BANDS[0]
    assert fallback(10) == BANDS[1] and fallback(100) == BANDS[9]


def test_statement_uses_the_model_text_or_the_fallback():
    assert statement(42, ["Goth"], client=FakeClient("  You're fairly niche.  ")) == "You're fairly niche."
    assert statement(42, ["Goth"], client=FakeClient(error=httpx.ConnectError("down"))) == fallback(42)
    assert statement(42, ["Goth"], client=FakeClient("")) == fallback(42)


def test_photos_travel_as_data_urls_and_change_the_prompt():
    c = FakeClient("Two sentences.")
    statement(70, ["Goth", "Y2K"], [b"\xff\xd8jpeg-bytes"], client=c)
    user = c.sent["messages"][1]["content"]
    assert user[0]["image_url"]["url"].startswith("data:image/jpeg;base64,/9hq")  # images first, so a warm-up shares the cached prefix
    assert user[1]["type"] == "text" and "photos are attached" in user[1]["text"]
    assert "photos are attached" not in prompt(70, ["Goth"], with_photos=False)


def test_warm_sends_the_photos_only_and_swallows_errors():
    c = FakeClient("")
    warm([b"\xff\xd8x"], client=c)
    assert c.sent["max_tokens"] == 1 and c.sent["messages"][1]["content"][-1] == {"type": "text", "text": ""}
    warm([b"x"], client=FakeClient(error=httpx.ConnectError("down")))  # no raise
    assert warm([], client=FakeClient("")) is None


def test_statement_is_cut_to_two_sentences_unless_they_are_too_short():
    long = "Your taste is the algorithm's most comfortable couch, every single cushion placed there by a feed that stopped being surprised long ago."  # 23 words
    assert two_sentences(f"{long} Second sentence here. Third sentence here.") == f"{long} Second sentence here."
    assert two_sentences(f"{long} That teacup? It is a relic from a world already mapped. Fourth.") == f"{long} That teacup? It is a relic from a world already mapped."
    assert two_sentences("  Only one.  ") == "Only one."
    assert statement(70, ["Goth"], client=FakeClient("A. B. C. D.")) == "A. B. C."


def test_register_follows_the_score():
    assert "impressed" in register(10) and "teasing" in register(50) and "roast" in register(90)
