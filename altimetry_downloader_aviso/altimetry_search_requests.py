"""Thin wrappers around :mod:`altimetry.search` (the Altimetry Search
package)."""

from __future__ import annotations

import numpy as np
from altimetry.search import (
    Mission,
    MissionProperties,
    MissionPropertiesLoader,
    get_passes_crossing_polygon,
    get_selected_passes,
)
from pyinterp.geometry import geographic

_SWATH_MISSIONS = (Mission.SWOT_SWATH_CALVAL, Mission.SWOT_SWATH_SCIENCE)

DEFAULT_MISSION = Mission.SWOT_SWATH_SCIENCE


class NoPassFoundError(Exception):
    """No pass of the mission's orbit falls in the requested time range."""


def as_datetime64(value: object) -> np.datetime64:
    """Normalize a date-like value (np.datetime64, datetime.date, str, ...)
    into an np.datetime64."""
    return value if isinstance(value, np.datetime64) else np.datetime64(str(value))


def mission_for(time: tuple[np.datetime64, np.datetime64]) -> Mission:
    """Pick the KaRIn swath mission (CalVal or Science) covering ``time``,
    using each mission's ``date_start``/``date_end``.

    Raises
    ------
    ValueError
        If ``time`` falls in no known mission phase, or straddles two.
    """
    start, end = as_datetime64(time[0]), as_datetime64(time[1])
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
    date_start = as_datetime64(properties.date_start)
    date_end = as_datetime64(properties.date_end) if properties.date_end else None
    return start >= date_start and (date_end is None or end <= date_end)


def mission_for_cycle(cycle_number: int) -> Mission:
    """Pick the KaRIn swath mission (CalVal or Science) covering
    ``cycle_number``, using each mission's ``first_cycle``/``nb_cycle``.

    Used when resolving ``box``/``cycle_number`` without a ``time`` filter,
    where ``mission_for`` has no period to work from.

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
        f"cycle_number {cycle_number} matches no single mission phase "
        f"(matches: {matches})"
    )
    raise ValueError(msg)


def _covers_cycle(properties: MissionProperties, cycle_number: int) -> bool:
    return (
        properties.first_cycle
        <= cycle_number
        < properties.first_cycle + properties.nb_cycle
    )


def get_selected_cycles(
    time: tuple[np.datetime64, np.datetime64], mission: Mission
) -> list[int]:
    """Return the cycle numbers covering ``time``, for ``mission``.

    Raises
    ------
    NoPassFoundError
        If no pass falls in ``time``.
    """
    start, end = as_datetime64(time[0]), as_datetime64(time[1])
    duration = np.timedelta64(end - start)
    if duration < np.timedelta64(0, "ns"):
        msg = f"time filter start ({start}) must be before its end ({end})"
        raise ValueError(msg)

    passes = get_selected_passes(mission, start, duration)
    if passes.empty:
        msg = f"No pass found for mission {mission} in period {time}"
        raise NoPassFoundError(msg)
    return sorted(passes["cycle_number"].unique().tolist())


def passes_crossing_polygon(
    mission: Mission,
    box: tuple[float, float, float, float],
    passes: list[int] | None = None,
) -> list[int]:
    """Wrap ``get_passes_crossing_polygon``: turns a bbox into the polygon it
    expects, and returns a plain sorted list of pass numbers crossing the
    polygon."""
    result = get_passes_crossing_polygon(mission, _box_to_polygon(box), passes)
    return sorted(int(p) for p in result)


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
