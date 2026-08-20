from app.scoring.bands import clamp_band, combine_writing_bands, mean_band, round_half_band


def test_round_half_band() -> None:
    assert round_half_band(6.24) == 6.0
    assert round_half_band(6.25) == 6.5
    assert round_half_band(6.75) == 7.0
    assert round_half_band(9.4) == 9.0
    assert round_half_band(-1) == 0.0


def test_mean_band() -> None:
    assert mean_band([6.0, 6.5, 7.0, 6.5]) == 6.5
    assert mean_band([5.0, 6.0, 6.0, 7.0]) == 6.0


def test_clamp() -> None:
    assert clamp_band(12) == 9.0
    assert clamp_band(-3) == 0.0


def test_combine_writing_bands() -> None:
    # Task 2 carries twice the weight of Task 1, then half-band rounding.
    assert combine_writing_bands(6.0, 7.0) == 6.5
    assert combine_writing_bands(6.5, 7.0) == 7.0
    assert combine_writing_bands(5.0, 8.0) == 7.0
    assert combine_writing_bands(8.0, 6.0) == 6.5
