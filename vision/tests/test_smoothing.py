from atlas_vision.smoothing import MedianSmoother


def test_sliding_median():
    sm = MedianSmoother(7.0, clock=lambda: 0.0)
    sm.add("R", 13, 0)
    sm.add("R", 11, 1)
    sm.add("R", 14, 2)
    sm.add("R", 12, 3)
    assert sm.value("R", 3) == 12
    sm.add("R", 30, 10)
    assert sm.value("R", 10) == 21
