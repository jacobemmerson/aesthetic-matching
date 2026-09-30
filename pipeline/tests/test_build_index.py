import numpy as np

from pipeline.build_index import build_graph, centroids, layout, normalize, prior


def test_centroids_are_unit_means_and_counts():
    vecs = normalize(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32))
    cents, counts = centroids(vecs, ["a", "a", "b"], ["a", "b", "empty"])
    assert counts.tolist() == [2, 1, 0]
    np.testing.assert_allclose(cents[0], [2**-0.5, 2**-0.5, 0], atol=1e-6)
    np.testing.assert_allclose(cents[1], [0, 0, 1], atol=1e-6)
    assert not cents[2].any()


def test_layout_shape():
    assert layout(np.random.rand(3, 8).astype(np.float32)).shape == (3, 2)
    assert layout(np.random.rand(40, 8).astype(np.float32)).shape == (40, 2)


def test_build_graph_drops_edges_to_unknown_nodes():
    nodes = [{"slug": "a", "name": "A", "description": "d", "other_names": "", "key_values": "", "wiki_url": "u", "related": ["b", "ghost"], "subgenres": []},
             {"slug": "b", "name": "B", "description": "d", "other_names": "", "key_values": "", "wiki_url": "u", "related": [], "subgenres": ["a"]}]
    g = build_graph(nodes, np.zeros((2, 2)), np.array([3, 0]))
    assert [e["target"] for e in g["edges"]] == ["b", "a"] and g["edges"][1]["type"] == "subgenre"
    assert g["nodes"][0]["image_count"] == 3 and g["nodes"][0]["x"] == 0.0


def test_prior_is_unit_scaled_and_autocomplete_dominates():
    p = prior([{"popularity": 10, "mentions": 5}, {"popularity": 0, "mentions": 100}, {"popularity": 0, "mentions": 0}])
    assert p.tolist()[2] == 0.0 and p.max() == 1.0 and p[0] > p[1]
