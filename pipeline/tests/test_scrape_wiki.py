from pathlib import Path

from pipeline.scrape_wiki import parse_page, slugify

FIXTURE = Path(__file__).parent / "fixtures" / "cottagecore.txt"


def test_parse_cottagecore():
    page = parse_page("Cottagecore", FIXTURE.read_text())
    assert page["name"] == "Cottagecore"
    assert page["slug"] == "cottagecore"
    assert page["other_names"] == "Farmcore, Countrycore"
    assert page["key_values"].startswith("Simplicity")
    assert len(page["related"]) == 12 and "Goblincore" in page["related"]
    assert len(page["subgenres"]) == 6 and "Honeycore" in page["subgenres"]
    assert page["description"].startswith("Cottagecore is an aesthetic inspired")
    assert "{{" not in page["description"] and "[[" not in page["description"]
    assert page["word_count"] > 3000


def test_page_without_infobox_is_flagged():
    page = parse_page("List of stuff", "Just some text with [[links]].")
    assert page["has_infobox"] is False and page["related"] == []


def test_infobox_with_unbalanced_markup_still_parses():
    page = parse_page("McBling", (FIXTURE.parent / "mcbling.txt").read_text())
    assert page["has_infobox"] and page["other_names"].startswith("Trashy Y2K")
    assert "Barbiecore" in page["related"]
    assert page["description"].startswith("McBling is a fashion and lifestyle aesthetic")


def test_slugify():
    assert slugify("Y2K Aesthetic") == "y2k-aesthetic"
    assert slugify("Día De Muertos") == "dia-de-muertos"
    assert slugify("Girls' Sleepover") == "girls-sleepover"


def test_pagename_template_is_expanded():
    text = "{{Aesthetic|title1=Foo}}\n'''{{PAGENAME}}''' is a trend."
    assert parse_page("Foo", text)["description"] == "Foo is a trend."


def test_single_line_infobox():
    text = "{{Aesthetic|title1=Tenniscore|related_aesthetics=[[Preppy]]}}\n'''Tenniscore''' is a look."
    page = parse_page("Tenniscore", text)
    assert page["has_infobox"] and page["related"] == ["Preppy"]
    assert page["description"] == "Tenniscore is a look."


def test_ref_footnotes_are_dropped_from_description():
    text = "{{Aesthetic|title1=Foo}}\n'''Foo''' is a look.<ref>\"Foo\" on example.com</ref> It is nice.<ref name=x/>"
    assert parse_page("Foo", text)["description"] == "Foo is a look. It is nice."
