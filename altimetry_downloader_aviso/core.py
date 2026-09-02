import functools
import logging
import os
import pathlib as pl
import typing as tp

import numpy as np
import yaml

from . import altimetry_search_requests as altisearch
from .auth import ensure_credentials
from .catalog_client.client import (
    fetch_catalog,
    get_details,
    get_product_from_short_name,
    search_granules,
)
from .catalog_client.geonetwork import AvisoCatalog, AvisoProduct
from .subset import subset_multiple_files
from .tds_client import TDS_HOST, TDS_LAYOUT_CONFIG, Protocol, http_bulk_download

logger = logging.getLogger(__name__)

#: Sentinel returned by _resolve_selected_passes when no `time` filter was
#: given, to distinguish from "time given but matches no pass" (None).
_NO_TIME_FILTER = object()


def _log_passes(step: str, mission: tp.Any, passes: tp.Any) -> None:
    """Debug-log an Altimetry Search result: cycles/passes involved."""
    logger.debug(
        "Altimetry Search %s: mission=%s, %d pass(es), cycle_number=%s, "
        "pass_number=%s",
        step,
        mission,
        len(passes),
        (
            sorted(passes["cycle_number"].unique().tolist())
            if "cycle_number" in passes
            else "n/a"
        ),
        sorted(passes["pass_number"].unique().tolist()),
    )


def _resolve_filters(
    product_short_name: str,
    filters: dict[str, tp.Any],
    box: tuple[float, float, float, float] | None,
) -> bool:
    """Resolve `time` (and `box`, if given) into `cycle_number`/ `pass_number`
    filters via Altimetry Search, in place.

    No-op if the product isn't organized by orbit cycle/pass (see
    `_product_queryable_by_pass`). If no `time` filter was given, `box`
    (if any) is resolved directly from `cycle_number`/`pass_number`
    instead, however much of either is given -- see `_resolve_box_only`.

    Returns
    -------
        `False` if the request has no result (caller should return an
        empty list). `True` otherwise.
    """
    if not _product_queryable_by_pass(product_short_name):
        return True

    resolved = _resolve_selected_passes(filters)
    if resolved is None:
        return False
    if resolved is _NO_TIME_FILTER:
        if box is None:
            return True
        return _resolve_box_only(
            filters, box, filters.get("cycle_number"), filters.get("pass_number")
        )

    mission, passes = resolved
    if box is not None:
        # Chain selected_passes -> pass_passage_time: keep only the
        # passes whose ground track crosses box.
        passage_time = altisearch.pass_passage_time(passes, box, mission)
        if passage_time.empty:
            logger.info("No pass of mission %s crosses box %s.", mission, box)
            return False
        _log_passes("pass_passage_time", mission, passage_time)
        passes = passes[passes["pass_number"].isin(passage_time["pass_number"])]
        _log_passes("passes retained after bbox filtering", mission, passes)

    return _apply_selected_passes(filters, passes)


def _resolve_box_only(
    filters: dict[str, tp.Any],
    box: tuple[float, float, float, float],
    cycle_number: int | list[int] | None,
    pass_number: int | list[int] | None,
) -> bool:
    """Resolve `box` into a `pass_number` filter without a `time` period.

    Without `time`, there is no `selected_passes` result to work from and
    no period to pick a mission from (see `mission_for`). `cycle_number`
    picks the mission instead (via `mission_for_cycle`) if given; if not,
    falls back to `altisearch.DEFAULT_MISSION` (every product currently
    exposed by this downloader is Science-phase).

    Returns
    -------
        `False` if no candidate pass crosses `box` (caller should return
        an empty result). `True` otherwise, with `filters["pass_number"]`
        set/narrowed in place.
    """
    if cycle_number is not None:
        cycles = cycle_number if isinstance(cycle_number, list) else [cycle_number]
        missions = {altisearch.mission_for_cycle(c) for c in cycles}
        if len(missions) != 1:
            msg = f"cycle_number {cycle_number} spans more than one mission phase."
            raise ValueError(msg)
        mission = missions.pop()
    else:
        mission = altisearch.DEFAULT_MISSION

    candidates = altisearch.passes_crossing_polygon(mission, box, pass_number)
    if not candidates:
        logger.info("No pass of mission %s crosses box %s.", mission, box)
        return False
    logger.debug(
        "Altimetry Search passes crossing box: mission=%s, pass_number=%s",
        mission,
        candidates,
    )

    if pass_number is not None:
        given = pass_number if isinstance(pass_number, list) else [pass_number]
        excluded = sorted(set(given) - set(candidates))
        if excluded:
            logger.info(
                "box %s excludes pass_number=%s; keeping pass_number=%s.",
                box,
                excluded,
                candidates,
            )

    filters["pass_number"] = candidates
    return True


def _is_empty_time(time: tp.Any) -> bool:
    """True if `time` carries no actual period: `None`, or a tuple whose bounds
    are all `None`."""
    return time is None or (isinstance(time, tuple) and all(b is None for b in time))


def _resolve_selected_passes(
    filters: dict[str, tp.Any],
) -> tuple[altisearch.Mission, tp.Any] | None | object:
    """Resolve the `time` filter into the passes it covers via Altimetry
    Search.

    Returns
    -------
        `_NO_TIME_FILTER` if no `time` filter was given. `None` if `time`
        was given but matches no pass at all. Else `(mission, passes)`.
    """
    if "time" not in filters:
        return _NO_TIME_FILTER

    time = filters["time"]
    if _is_empty_time(time):
        del filters["time"]
        return _NO_TIME_FILTER
    start, end = time
    if start is None or end is None:
        msg = f"time filter needs both --start and --end (got {time})"
        raise ValueError(msg)

    mission = altisearch.mission_for(time)
    try:
        passes = altisearch.selected_passes(time, mission)
    except altisearch.NoPassFoundError as err:
        logger.info("%s", err)
        return None
    _log_passes("selected_passes", mission, passes)
    return mission, passes


def _intersect(explicit: int | list[int], resolved: list[int]) -> list[int]:
    """Values in `explicit` (int or list[int]) that are also in `resolved`."""
    values = explicit if isinstance(explicit, list) else [explicit]
    return sorted(set(values) & set(resolved))


def _apply_selected_passes(filters: dict[str, tp.Any], passes: tp.Any) -> bool:
    """Merge resolved passes into filters.

    If `cycle_number`/`pass_number` were given explicitly together with
    `time`, they are narrowed down to their intersection with the passes
    resolved from `time` -- keeping only the values that match both. An
    empty intersection on either one means the request is inconsistent.

    Returns
    -------
        `False` if the request is inconsistent (caller should return an
        empty result). `True` otherwise, with `filters` updated in place.
    """
    granule_filters = altisearch.as_granule_filters(passes)

    explicit_cycle = filters.get("cycle_number")
    if explicit_cycle is not None:
        cycle_number = _intersect(explicit_cycle, granule_filters["cycle_number"])
        if not cycle_number:
            logger.info(
                "cycle_number=%s does not intersect the cycles resolved "
                "from time (%s); request is inconsistent.",
                explicit_cycle,
                granule_filters["cycle_number"],
            )
            return False
        granule_filters["cycle_number"] = cycle_number

    explicit_pass = filters.get("pass_number")
    if explicit_pass is not None:
        pass_number = _intersect(explicit_pass, granule_filters["pass_number"])
        if not pass_number:
            logger.info(
                "pass_number=%s does not intersect the passes resolved "
                "from time (%s); request is inconsistent.",
                explicit_pass,
                granule_filters["pass_number"],
            )
            return False
        granule_filters["pass_number"] = pass_number

    logger.debug("Altimetry Search resolved granule filters: %s", granule_filters)
    filters.update(granule_filters)
    return True


def authenticate(func: tp.Callable) -> tp.Callable:
    """Ensure authentication with the TDS server is setup before calling the
    input function.

    Parameters
    ----------
    func
        Any high level method that will need authentication with the TDS server.

    Returns
    -------
    :
        The same function, but with the authentication setup automatically called before
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        ensure_credentials(TDS_HOST)
        return func(*args, **kwargs)

    return wrapped


def summary() -> AvisoCatalog:
    """Summarizes CDS-AVISO and SWOT products from AVISO's catalog.

    Returns
    -------
        The AVISO catalog object containing all the CDS-AVISO and SWOT products
    """
    return fetch_catalog()


def details(product_short_name: str) -> AvisoProduct:
    """Details a product information from AVISO's catalog.

    Parameters
    ----------
    product_short_name
        the short name of the product

    Returns
    -------
        The description of product
    """
    return get_details(product_short_name)


def _product_queryable_by_pass(product_short_name: str) -> bool:
    """Whether `time` can be resolved into `cycle_number`/`pass_number` via
    Altimetry Search for this product."""
    with open(TDS_LAYOUT_CONFIG, encoding="utf-8") as f:
        tds_layout = yaml.safe_load(f)
    for product in tds_layout["products"].values():
        if product["short_name"] == product_short_name:
            return product.get("queryable_by_pass", True)
    return True


@authenticate
def get(
    product_short_name: str,
    output_dir: str | pl.Path,
    cycle_number: int | list[int] | None = None,
    pass_number: int | list[int] | None = None,
    time: tuple[np.datetime64, np.datetime64] | None = None,
    version: str | None = None,
    overwrite: bool = False,
    box: tuple[float, float, float, float] | None = None,
) -> list[str]:
    """Downloads a product from Aviso's Thredds Data Server.

    Parameters
    ----------
    product_short_name
        the short name of the product
    output_dir
        directory to store downloaded product files
    cycle_number
        the cycle number for files/folders selection
    pass_number
        the pass number for files/folders selection
    time
        the period for files/folders selection
    version
        the version for files/folders selection
    overwrite: bool
        whether to overwrite files if they already exist
    box
        Selection box (lon_min, lat_min, lon_max, lat_max) in degrees, used
        to restrict downloaded granules to those whose ground track
        crosses it (via Altimetry Search). Unlike `subset`, `get` never
        crops file content: `box` only has an effect through Altimetry
        Search. If `time` is set, it narrows the passes resolved from
        `time`. Otherwise, `cycle_number` picks the mission if given
        (falling back to the Science phase otherwise), and `pass_number`
        narrows the candidate passes tested against `box` if given
        (otherwise every pass of the mission is tested).

    Raises
    ------
    ValueError
        If `cycle_number` spans more than one mission phase.

    Returns
    -------
        The list of local files matching the request, including both that were already
        present, and those created by the get operation.
    """
    filters = dict(
        filter(
            lambda item: item[1] is not None,
            zip(
                ["cycle_number", "pass_number", "time", "version"],
                [cycle_number, pass_number, time, version],
            ),
        )
    )

    if not _resolve_filters(product_short_name, filters, box):
        return []

    granule_paths, _, non_target_local_files = _search_granules_with_overwrite(
        product_short_name, Protocol.HTTP, output_dir, overwrite, **filters
    )

    logger.debug("Downloading granules: %s...", list(granule_paths))

    return (
        list(
            http_bulk_download(
                urls=granule_paths, output_dir=output_dir, overwrite=overwrite
            )
        )
        + non_target_local_files
    )


@authenticate
def subset(
    product_short_name: str,
    output_dir: str | pl.Path,
    cycle_number: int | list[int] | None = None,
    pass_number: int | list[int] | None = None,
    time: tuple[np.datetime64, np.datetime64] | None = None,
    version: str | None = None,
    overwrite: bool = False,
    box: tuple[float, float, float, float] | None = None,
    selected_variables: list[str] | None = None,
) -> list[str]:
    """Subset a product from Aviso's Thredds Data Server.

    Parameters
    ----------
    product_short_name
        the short name of the product
    output_dir
        directory to store downloaded product files
    cycle_number
        the cycle number for files/folders selection
    pass_number
        the pass number for files/folders selection
    time
        the period for files/folders selection
    version
        the version for files/folders selection
    overwrite: bool
        whether to overwrite files if they already exist
    box
        Selection box (lon_min, lat_min, lon_max, lat_max) in degrees. Longitude range
        can be in either [0, 360[ or [-180, 180[ convention. lon_min must be inferior to
        lon_max (the convention must be changed to verify this constraint). Always used
        to crop the content of downloaded granules. Also always used beforehand, via
        Altimetry Search, to restrict which granules are downloaded in the first place:
        chained with `time` if set, otherwise with `cycle_number`/`pass_number` if given
        (falling back to every pass of the Science-phase mission otherwise).
    selected_variables
        List of variables to select.

    Raises
    ------
    NotImplementedError
        In case the input product does not support subsetting: only swath datasets on a
        (num_lines, num_pixels) grid are supported.

    Warns
    -----
    UserWarning
        If a granule download failed.
    UserWarning
        If a granule listed in the TDS catalog does not expose a valid OpenDAP URL.

    Returns
    -------
        The list of local files matching the request, including both that were already
        present, and those created by the subset operation.
    """
    # Trigger short name verification before checking if subset is enabled for the
    # dataset. This should emit a better error message for the user.
    get_product_from_short_name(product_short_name)

    logger.debug("Loading list of products supporting subsetting feature")
    with open(TDS_LAYOUT_CONFIG, encoding="utf-8") as f:
        tds_layout = yaml.safe_load(f)
        authorized_products = [
            product["short_name"]
            for product in tds_layout["products"].values()
            if product["subset"]
        ]

    if product_short_name not in authorized_products:
        msg = (
            f"Subsetting for product {product_short_name} is not supported. List of "
            f"supported products: {authorized_products}"
        )
        raise NotImplementedError(msg)

    output_dir = pl.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filters = dict(
        filter(
            lambda item: item[1] is not None,
            zip(
                ["cycle_number", "pass_number", "time", "version"],
                [cycle_number, pass_number, time, version],
            ),
        )
    )

    if not _resolve_filters(product_short_name, filters, box):
        return []

    granule_paths, target_local_files, non_target_local_files = (
        _search_granules_with_overwrite(
            product_short_name, Protocol.DAP2, output_dir, overwrite, **filters
        )
    )

    logger.info("Subsetting %d granules...", len(granule_paths))

    return (
        subset_multiple_files(
            granule_paths, target_local_files, box, selected_variables
        )
        + non_target_local_files
    )


def _search_granules_with_overwrite(
    product_short_name: str,
    protocol: Protocol,
    output_dir: str,
    overwrite: bool,
    **filters: tp.Any,
) -> tuple[list[str], list[str], list[str]]:
    granule_paths = search_granules(product_short_name, protocol, **filters)
    granule_paths = granule_paths.tolist()

    local_files = [pl.Path(output_dir) / os.path.basename(p) for p in granule_paths]
    exist = [f.exists() for f in local_files]

    if not overwrite:
        granule_paths = [g for g, e in zip(granule_paths, exist) if not e]
        target_local_files = [str(f) for f, e in zip(local_files, exist) if not e]
        non_target_local_files = [str(f) for f, e in zip(local_files, exist) if e]
        logger.debug("%d files already exist and will be kept.", sum(exist))
    else:
        logger.debug("%d files already exist and will be overwritten.", sum(exist))
        target_local_files = [str(f) for f in local_files]
        non_target_local_files = []

    return granule_paths, target_local_files, non_target_local_files
