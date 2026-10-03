import numpy as np

from pipeline.prune import face_fraction, near_duplicates


def test_near_duplicates_keeps_the_first_of_each_pair_within_a_node():
    v = np.array([[1, 0, 0], [0.999, 0.04, 0], [0, 1, 0], [0.999, 0.04, 0]], np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    assert near_duplicates(v, ["a", "a", "a", "b"], threshold=0.95).tolist() == [False, True, False, False]  # row 3 is another node


def test_face_fraction_is_the_largest_face_over_the_image():
    assert face_fraction([(0, 0, 10, 10), (0, 0, 50, 40)], 100, 100) == 0.2
    assert face_fraction([], 100, 100) == 0.0
