import httpx

from server.roast import BANDS, fallback, statement


class FakeClient:
    def __init__(self, text=None, error=None):
        self.text, self.error = text, error

    def post(self, *a, **k):
        if self.error:
            raise self.error
        return httpx.Response(200, json={"response": self.text}, request=httpx.Request("POST", "http://x"))


def test_fallback_picks_the_band():
    assert len(BANDS) == 10
    assert fallback(0) == BANDS[0] and fallback(9) == BANDS[0]
    assert fallback(10) == BANDS[1] and fallback(100) == BANDS[9]


def test_statement_uses_the_model_text_or_the_fallback():
    assert statement(42, ["Goth"], FakeClient("  You're fairly niche.  ")) == "You're fairly niche."
    assert statement(42, ["Goth"], FakeClient(error=httpx.ConnectError("down"))) == fallback(42)
    assert statement(42, ["Goth"], FakeClient("")) == fallback(42)
