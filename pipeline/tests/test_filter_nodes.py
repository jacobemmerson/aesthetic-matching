from pipeline.filter_nodes import filter_nodes

NODES = [
    {"slug": "a", "name": "A", "description": "x" * 200, "related": ["b"], "subgenres": []},
    {"slug": "b", "name": "B", "description": "x" * 200, "related": [], "subgenres": []},
    {"slug": "short", "name": "Short", "description": "tiny", "related": ["a"], "subgenres": []},
    {"slug": "lonely", "name": "Lonely", "description": "x" * 200, "related": [], "subgenres": []},
    {"slug": "denied", "name": "Denied", "description": "x" * 200, "related": ["a"], "subgenres": []},
]


def test_filter_reasons():
    kept, dropped = filter_nodes(NODES, exclude={"denied"})
    assert [n["slug"] for n in kept] == ["a", "b"]
    assert dropped == {"short": "description < 150 chars", "lonely": "no edges", "denied": "in exclude.txt"}
    assert kept[0]["related"] == ["b"]  # edge to a dropped node is removed


def test_min_mentions():
    from collections import Counter
    kept, dropped = filter_nodes(NODES[:2], exclude=set(), mentions=Counter({"a": 9}), min_mentions=5)
    assert [n["slug"] for n in kept] == ["a"] and dropped == {"b": "mentioned by < 5 pages"}
    assert kept[0]["mentions"] == 9


def test_merge_nodes():
    from pipeline.filter_nodes import merge_nodes
    nodes = [
        {"slug": "preppy", "name": "Preppy", "other_names": "Prep", "mentions": 5, "related": ["old-preppy"], "subgenres": []},
        {"slug": "old-preppy", "name": "2000s Preppy", "other_names": "", "mentions": 2, "related": ["preppy", "x"], "subgenres": []},
        {"slug": "x", "name": "X", "other_names": "", "mentions": 1, "related": ["old-preppy"], "subgenres": []},
    ]
    kept = merge_nodes(nodes, {"old-preppy": "preppy"})
    assert [n["slug"] for n in kept] == ["preppy", "x"]
    assert kept[0]["other_names"] == "Prep, 2000s Preppy" and kept[0]["mentions"] == 7
    assert kept[0]["related"] == ["x"] and kept[1]["related"] == ["preppy"]


def test_min_popularity_only_applies_to_scored_nodes():
    nodes = [{"slug": "a", "name": "A", "description": "x" * 200, "related": ["b"], "subgenres": []},
             {"slug": "b", "name": "B", "description": "x" * 200, "related": ["a"], "subgenres": []}]
    kept, dropped = filter_nodes(nodes, exclude=set(), popularity={"a": 0}, min_popularity=2)
    assert [n["slug"] for n in kept] == ["b"] and dropped == {"a": "< 2 google autocomplete hits"}
    assert kept[0]["popularity"] is None
