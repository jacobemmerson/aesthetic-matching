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


def test_random_crop_is_smaller_and_inside():
    from PIL import Image

    from pipeline.build_index import random_crop

    img = Image.new("RGB", (100, 80))
    rng = np.random.default_rng(0)
    for _ in range(20):
        c = random_crop(img, rng)
        assert 50 <= c.width <= 90 and 40 <= c.height <= 72


def test_embed_images_source_rows(monkeypatch, tmp_path):
    import torch
    from PIL import Image

    from pipeline import build_index as bi

    class FakeModel:
        def encode_image(self, x):
            return torch.ones(x.shape[0], 4)

    monkeypatch.setattr(bi, "load_model", lambda: (FakeModel(), lambda im: torch.zeros(3, 8, 8), None, torch))
    paths = []
    for i in range(2):
        p = tmp_path / f"{i}.jpg"; Image.new("RGB", (32, 32)).save(p); paths.append(p)
    vecs, source = bi.embed_images(paths, crops=2)
    assert vecs.shape == (6, 4) and source.tolist() == [0, 1, 0, 1, 0, 1]
