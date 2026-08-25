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

#: Swath missions a `time` filter can resolve to
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


def mission_for_cycle(cycle_number: int) -> Mission:
    """Pick the KaRIn swath mission (CalVal or Science) covering
    ``cycle_number``, using each mission's ``first_cycle``/``nb_cycle``.

    Used when resolving ``box`` without a ``time`` filter, where
    ``mission_for`` has no period to work from.

    Raises
    ------
    ValueError
        If ``cycle_number`` falls in no known mission phase.
    """
    loader = MissionPropertiesLoader()
    matches = [
        mission
        for mission in _SWATH_MISSIONS
        if _covers_cycle(loader.load(mission), cycle_number)
    ]
    if len(matches) == 1:
        return matches[0]
    msg = (
        f"cycle_number {cycle_number} matches no single",
        "mission phase (matches: {matches})",
    )
    raise ValueError(msg)


def _covers_cycle(properties: MissionProperties, cycle_number: int) -> bool:
    return (
        properties.first_cycle
        <= cycle_number
        < properties.first_cycle + properties.nb_cycle
    )


def all_pass_numbers(mission: Mission) -> list[int]:
    """Every pass number of ``mission``'s orbit: ``1`` to ``nb_pass``
    (inclusive), the same set every cycle -- see
    ``altimetry.search.orbit.get_pass_passage_time``."""
    nb_pass = MissionPropertiesLoader().load(mission).nb_pass
    return list(range(1, nb_pass + 1))


def _as_datetime64(value: object) -> np.datetime64:
    """Normalize a date-like value (np.datetime64, datetime.date, str, ...)
    into an np.datetime64."""
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
    filters consumed by ``catalog_client.client.search_granules``."""
    return {
        "cycle_number": sorted(passes["cycle_number"].unique().tolist()),
        "pass_number": sorted(passes["pass_number"].unique().tolist()),
    }
