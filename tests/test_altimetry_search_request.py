import datetime as dt
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from altimetry_downloader_aviso import altimetry_search_requests as altisearch
from altimetry_downloader_aviso.altimetry_search_requests import Mission

# ---------------------------------------------------------------------------
# mission_for
# ---------------------------------------------------------------------------


def _mock_loader(
    mocker,
    calval_range,
    science_range,
    calval_cycles=(474, 105),
    science_cycles=(1, 399),
):
    properties = {
        Mission.SWOT_SWATH_CALVAL: SimpleNamespace(
            date_start=calval_range[0],
            date_end=calval_range[1],
            first_cycle=calval_cycles[0],
            nb_cycle=calval_cycles[1],
        ),
        Mission.SWOT_SWATH_SCIENCE: SimpleNamespace(
            date_start=science_range[0],
            date_end=science_range[1],
            first_cycle=science_cycles[0],
            nb_cycle=science_cycles[1],
        ),
    }
    loader = mocker.Mock()
    loader.load.side_effect = lambda mission: properties[mission]
    mocker.patch.object(altisearch, "MissionPropertiesLoader", return_value=loader)
    return loader


@pytest.fixture
def mocked_mission_phases(mocker):
    return _mock_loader(
        mocker,
        calval_range=(dt.date(2023, 3, 29), dt.date(2023, 7, 10)),
        science_range=(dt.date(2023, 7, 21), None),
    )


def test_mission_for_calval(mocked_mission_phases):
    assert (
        altisearch.mission_for(
            (np.datetime64("2023-04-01"), np.datetime64("2023-04-05"))
        )
        is Mission.SWOT_SWATH_CALVAL
    )


def test_mission_for_science(mocked_mission_phases):
    assert (
        altisearch.mission_for(
            (np.datetime64("2025-01-01"), np.datetime64("2025-01-10"))
        )
        is Mission.SWOT_SWATH_SCIENCE
    )


def test_mission_for_science_open_ended(mocked_mission_phases):
    # date_end=None for Science: any far-future date must still match.
    assert (
        altisearch.mission_for(
            (np.datetime64("2030-01-01"), np.datetime64("2030-01-10"))
        )
        is Mission.SWOT_SWATH_SCIENCE
    )


def test_mission_for_gap_between_phases_raises(mocked_mission_phases):
    # Falls between CalVal's date_end and Science's date_start: matches
    # neither phase.
    with pytest.raises(ValueError, match="matches no single mission phase"):
        altisearch.mission_for(
            (np.datetime64("2023-07-12"), np.datetime64("2023-07-15"))
        )


def test_mission_for_straddling_phases_raises(mocked_mission_phases):
    with pytest.raises(ValueError, match="matches no single mission phase"):
        altisearch.mission_for(
            (np.datetime64("2023-06-01"), np.datetime64("2023-08-01"))
        )


# ---------------------------------------------------------------------------
# mission_for_cycle / _covers_cycle
# ---------------------------------------------------------------------------


def test_covers_cycle_within_range():
    properties = SimpleNamespace(first_cycle=10, nb_cycle=5)
    assert altisearch._covers_cycle(properties, 10) is True  # lower bound, inclusive
    assert altisearch._covers_cycle(properties, 14) is True  # upper bound, inclusive
    assert altisearch._covers_cycle(properties, 15) is False  # exclusive
    assert altisearch._covers_cycle(properties, 9) is False  # below range


def test_mission_for_cycle_calval(mocked_mission_phases):
    assert altisearch.mission_for_cycle(474) is Mission.SWOT_SWATH_CALVAL
    assert altisearch.mission_for_cycle(578) is Mission.SWOT_SWATH_CALVAL


def test_mission_for_cycle_science(mocked_mission_phases):
    assert altisearch.mission_for_cycle(1) is Mission.SWOT_SWATH_SCIENCE
    assert altisearch.mission_for_cycle(399) is Mission.SWOT_SWATH_SCIENCE


def test_mission_for_cycle_gap_between_phases_raises(mocked_mission_phases):
    # Falls between Science's last cycle (399) and CalVal's first (474):
    # matches neither phase.
    with pytest.raises(ValueError, match="matches no single mission phase"):
        altisearch.mission_for_cycle(400)


def test_mission_for_cycle_overlapping_phases_raises(mocker):
    # Degenerate case: two phases whose cycle ranges overlap -- matches
    # both, which is just as invalid as matching neither.
    _mock_loader(
        mocker,
        calval_range=(dt.date(2023, 3, 29), dt.date(2023, 7, 10)),
        science_range=(dt.date(2023, 7, 21), None),
        calval_cycles=(1, 10),
        science_cycles=(5, 10),
    )
    with pytest.raises(ValueError, match="matches no single mission phase"):
        altisearch.mission_for_cycle(7)


# ---------------------------------------------------------------------------
# get_selected_cycles
# ---------------------------------------------------------------------------


def test_get_selected_cycles_wraps_get_selected_passes(mocker):
    expected = pd.DataFrame({"cycle_number": [10, 10, 11], "pass_number": [1, 2, 1]})
    mock = mocker.patch.object(altisearch, "get_selected_passes", return_value=expected)

    result = altisearch.get_selected_cycles(
        (np.datetime64("2025-01-01"), np.datetime64("2025-01-05")),
        Mission.SWOT_SWATH_SCIENCE,
    )

    assert result == [10, 11]
    mock.assert_called_once()
    mission_arg, date_arg, duration_arg = mock.call_args[0]
    assert mission_arg is Mission.SWOT_SWATH_SCIENCE
    assert date_arg == np.datetime64("2025-01-01")
    assert duration_arg == np.timedelta64(4, "D")


def test_get_selected_cycles_raises_when_empty(mocker):
    mocker.patch.object(altisearch, "get_selected_passes", return_value=pd.DataFrame())
    with pytest.raises(altisearch.NoPassFoundError):
        altisearch.get_selected_cycles(
            (np.datetime64("2025-01-01"), np.datetime64("2025-01-05")),
            Mission.SWOT_SWATH_SCIENCE,
        )


def test_get_selected_cycles_rejects_end_before_start():
    with pytest.raises(ValueError, match="must be before its end"):
        altisearch.get_selected_cycles(
            (np.datetime64("2025-01-05"), np.datetime64("2025-01-01")),
            Mission.SWOT_SWATH_SCIENCE,
        )


# ---------------------------------------------------------------------------
# passes_crossing_polygon / _box_to_polygon
# ---------------------------------------------------------------------------


def test_passes_crossing_polygon_wraps_get_passes_crossing_polygon(mocker):
    mock = mocker.patch.object(
        altisearch,
        "get_passes_crossing_polygon",
        return_value=np.array([33, 2], dtype=np.uint16),
    )

    result = altisearch.passes_crossing_polygon(
        Mission.SWOT_SWATH_SCIENCE, (0, 0, 10, 10), [2, 33]
    )

    # Sorted, and plain Python ints (not numpy.uint16).
    assert result == [2, 33]
    assert all(type(p) is int for p in result)
    mission_arg, polygon_arg, passes_arg = mock.call_args[0]
    assert mission_arg is Mission.SWOT_SWATH_SCIENCE
    assert polygon_arg is not None
    assert passes_arg == [2, 33]


def test_passes_crossing_polygon_defaults_passes_to_none(mocker):
    mock = mocker.patch.object(
        altisearch,
        "get_passes_crossing_polygon",
        return_value=np.array([], dtype=np.uint16),
    )

    result = altisearch.passes_crossing_polygon(
        Mission.SWOT_SWATH_SCIENCE, (0, 0, 10, 10)
    )

    assert result == []
    mission_arg, polygon_arg, passes_arg = mock.call_args[0]
    assert passes_arg is None


def test_box_to_polygon_densifies_constant_latitude_edges(mocker):
    captured = {}

    def fake_ring(lons, lats):
        captured["lons"] = lons
        captured["lats"] = lats
        return mocker.Mock()

    mocker.patch.object(altisearch.geographic, "Ring", side_effect=fake_ring)
    mocker.patch.object(altisearch.geographic, "Polygon", side_effect=lambda ring: ring)

    altisearch._box_to_polygon((0, 0, 20, 10))

    lons, lats = captured["lons"], captured["lats"]
    # Ring is closed: first and last point identical.
    assert lons[0] == lons[-1]
    assert lats[0] == lats[-1]
    # More than the 4 corners: constant-latitude edges got interpolated.
    assert len(lons) > 5
    # Both constant-latitude edges (top and bottom) are present.
    assert 0 in lats
    assert 10 in lats
