from pipeline.popularity import score


def test_score_counts_suggestions_containing_the_full_name():
    assert score("Dresiarz", ["dres aesthetic", "dresiarze meaning", "dresses aesthetics"]) == 1
    assert score("Gorpcore", ["gorpcore aesthetic", "Gorpcore aesthetic men"]) == 2
    assert score("Grocery Girl Fall", ["grocery girl fall aesthetic", "fall grocery list"]) == 1
    assert score("X", []) == 0
    assert score("Hip-Hop", ["hip hop aesthetic", "hiphop"]) == 1
    assert score("E-Girl", ["e girl aesthetic", "egirl aesthetic outfits"]) == 1
