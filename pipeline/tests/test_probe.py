import numpy as np
import pytest

from pipeline.probe import label_references, sample_cells


def test_sample_cells_balanced_and_abort_on_thin_cell():
    race = np.repeat(np.arange(7), 60); gender = np.tile([0, 1], 210)
    idx = sample_cells(race, gender, per_cell=10, seed=0)
    assert len(idx) == 140
    for r in range(7):
        for g in range(2):
            assert ((race[idx] == r) & (gender[idx] == g)).sum() == 10
    thin = race.copy(); thin[(race == 6) & (gender == 1)] = 5  # empty one cell
    with pytest.raises(SystemExit):
        sample_cells(thin, gender, per_cell=10, seed=0)


def test_label_references_marks_faceless_as_none():
    rng = np.random.default_rng(0)
    race, gender = rng.integers(0, 7, 700), rng.integers(0, 2, 700)
    probe = rng.normal(scale=0.3, size=(700, 8)).astype(np.float32)
    probe[:, 0] += 3 * race; probe[:, 1] += 3 * gender
    ref = probe[:10].copy()
    out = label_references(probe, race, gender, ref, has_face=np.array([True] * 9 + [False]))
    assert out["race"][:9].tolist() == race[:9].tolist() and out["gender"][:9].tolist() == gender[:9].tolist()
    assert out["race"][9] == -1 and out["gender"][9] == -1
    assert out["race_cv_acc"] > 0.9 and out["gender_cv_acc"] > 0.9
