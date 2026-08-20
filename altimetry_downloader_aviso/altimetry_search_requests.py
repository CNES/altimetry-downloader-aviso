"""Thin wrappers around :mod:`altimetry.search` (the Altimetry Search package).

Each function here does input/output formatting only, around a single
Altimetry Search call. Chaining ``selected_passes`` with ``pass_passage_time``
(i.e. restricting passes to those crossing a bbox) is orchestrated in
``core.py::subset``, not here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from altimetry.search import (
    Mission,
    MissionProperties,
    MissionPropertiesLoader,
    get_pass_passage_time,
    get_selected_passes,
)
from pyinterp.geometry import geographic

#: Swath missions a `time` filter can resolve to. Nadir missions share the
#: same date ranges but are not used by this downloader.
_SWATH_MISSIONS = (Mission.SWOT_SWATH_CALVAL, Mission.SWOT_SWATH_SCIENCE)


class NoPassFoundError(Exception):
    """No pass of the mission's orbit falls in the requested time range."""


def mission_for(time: tuple[np.datetime64, np.datetime64]) -> Mission:
    """Pick the KaRIn swath mission (CalVal or Science) covering ``time``,
    using each mission's ``date_start``/``date_end``.

    Raises
    ------
    ValueError
        If ``time`` falls in no known mission phase, or straddles two.
    """
    start, end = _as_datetime64(time[0]), _as_datetime64(time[1])
    loader = MissionPropertiesLoader()
    matches = [
        mission
        for mission in _SWATH_MISSIONS
        if _covers(loader.load(mission), start, end)
    ]
    if len(matches) == 1:
        return matches[0]
    msg = f"time range {time} matches no single mission phase (matches: {matches})"
    raise ValueError(msg)


def _covers(
    properties: MissionProperties, start: np.datetime64, end: np.datetime64
) -> bool:
    date_start = _as_datetime64(properties.date_start)
    date_end = _as_datetime64(properties.date_end) if properties.date_end else None
    return start >= date_start and (date_end is None or end <= date_end)


def _as_datetime64(value: object) -> np.datetime64:
    """Normalize a date-like value (np.datetime64, datetime.date, str, ...)
    into an np.datetime64, so comparisons stay robust no matter how Altimetry
    Search represents ``MissionProperties`` dates."""
    return value if isinstance(value, np.datetime64) else np.datetime64(str(value))


def selected_passes(
    time: tuple[np.datetime64, np.datetime64], mission: Mission
) -> pd.DataFrame:
    """Wrap ``get_selected_passes``: turns a ``(start, end)`` time filter into
    its ``(date, search_duration)`` signature.

    Raises
    ------
    NoPassFoundError
        If no pass falls in ``time``.
    """
    start, end = _as_datetime64(time[0]), _as_datetime64(time[1])
    duration = np.timedelta64(end - start)
    if duration < np.timedelta64(0, "ns"):
        msg = f"time filter start ({start}) must be before its end ({end})"
        raise ValueError(msg)

    passes = get_selected_passes(mission, start, duration)
    if passes.empty:
        msg = f"No pass found for mission {mission} in period {time}"
        raise NoPassFoundError(msg)
    return passes


def pass_passage_time(
    passes: pd.DataFrame,
    box: tuple[float, float, float, float],
    mission: Mission,
) -> pd.DataFrame:
    """Wrap ``get_pass_passage_time``: turns a ``(lon_min, lat_min, lon_max,
    lat_max)`` box into the polygon it expects.

    A pass absent from the result does not cross ``box`` (see
    ``altimetry.search.orbit.get_pass_passage_time``, which only emits a row
    per intersecting pass).
    """
    return get_pass_passage_time(mission, passes, _box_to_polygon(box))


def _box_to_polygon(box: tuple[float, float, float, float]) -> geographic.Polygon:
    """Build a polygon from a bbox, densifying the constant-latitude edges
    so they follow the parallel rather than a geodesic chord between the
    corners -- same approach as Altimetry Search's own map widget
    (``altimetry.search.gui.widgets.draw_bbox``).
    """
    lon_min, lat_min, lon_max, lat_max = box
    n = max(round(lon_max - lon_min) * 2, 2)
    xs = np.linspace(lon_min, lon_max, n, endpoint=True)
    lons = np.concatenate([xs[::-1], xs])
    lats = np.concatenate([np.full(len(xs), lat_min), np.full(len(xs), lat_max)])
    lons = np.append(lons, lons[0])
    lats = np.append(lats, lats[0])
    return geographic.Polygon(
        geographic.Ring(lons.astype(np.float64), lats.astype(np.float64))
    )


def as_granule_filters(passes: pd.DataFrame) -> dict[str, list[int]]:
    """Format a passes dataframe into the ``cycle_number``/``pass_number``
    filters consumed by ``catalog_client.client.search_granules``.

    The two lists are independent, not paired -- correct here since a given
    ``pass_number``'s ground track is identical every cycle, so their cross
    product already matches what Altimetry Search selected (unless ``time``
    straddles a phase transition, which :func:`mission_for` rejects
    upstream).
    """
    return {
        "cycle_number": sorted(passes["cycle_number"].unique().tolist()),
        "pass_number": sorted(passes["pass_number"].unique().tolist()),
    }
