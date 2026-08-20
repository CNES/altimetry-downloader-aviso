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
#: given, to distinguish from "time given but nothing matched" (None).
_NO_TIME_FILTER = object()


def _log_passes(step: str, mission: tp.Any, passes: tp.Any) -> None:
    """Debug-log an Altimetry Search result: cycles/passes involved."""
    logger.debug(
        "Altimetry Search %s: mission=%s, %d pass(es), cycle_number=%s, "
        "pass_number=%s",
        step,
        mission,
        len(passes),
        sorted(passes["cycle_number"].unique().tolist())
        if "cycle_number" in passes
        else "n/a",
        sorted(passes["pass_number"].unique().tolist()),
    )


def _resolve_selected_passes(
    filters: dict[str, tp.Any],
) -> tuple[altisearch.Mission, tp.Any] | None | object:
    """Pop the `time` filter and resolve it into the passes it covers.

    If `time` matches no pass but `cycle_number`/`pass_number` were also
    given, those are kept as-is (with a warning) instead of emptying the
    result.

    Returns
    -------
        `_NO_TIME_FILTER` if no `time` filter was given, or if it matched
        nothing but explicit cycle_number/pass_number filters remain to
        fall back on. `None` if `time` was given, matched nothing, and
        there is no fallback. Else `(mission, passes)`.
    """
    if "time" not in filters:
        return _NO_TIME_FILTER

    time = filters.pop("time")
    mission = altisearch.mission_for(time)
    try:
        passes = altisearch.selected_passes(time, mission)
    except altisearch.NoPassFoundError as err:
        if "cycle_number" in filters or "pass_number" in filters:
            logger.warning(
                "time filter matched no pass (%s); ignoring it and keeping "
                "the explicit cycle_number/pass_number filters.",
                err,
            )
            return _NO_TIME_FILTER
        logger.info("%s", err)
        return None
    _log_passes("selected_passes", mission, passes)
    return mission, passes


def _overlaps(explicit: int | list[int] | None, resolved: list[int]) -> bool:
    """True if `explicit` (None = no constraint on that filter) intersects
    `resolved`."""
    if explicit is None:
        return True
    values = explicit if isinstance(explicit, list) else [explicit]
    return bool(set(values) & set(resolved))


def _apply_selected_passes(filters: dict[str, tp.Any], passes: tp.Any) -> None:
    """Merge resolved passes into filters.

    If `cycle_number`/`pass_number` were given explicitly and don't overlap
    the passes resolved from `time` at all, they are kept as-is (`time` is
    ignored, with a warning) instead of being overridden by an
    empty/unrelated selection.
    """
    granule_filters = altisearch.as_granule_filters(passes)
    explicit_cycle = filters.get("cycle_number")
    explicit_pass = filters.get("pass_number")

    if explicit_cycle is not None or explicit_pass is not None:
        if not _overlaps(
            explicit_cycle, granule_filters["cycle_number"]
        ) or not _overlaps(explicit_pass, granule_filters["pass_number"]):
            logger.warning(
                "time filter matches no pass among the explicit "
                "cycle_number=%s/pass_number=%s; ignoring time and keeping "
                "those filters as-is.",
                explicit_cycle,
                explicit_pass,
            )
            return
        logger.warning(
            "Ignoring explicit cycle_number/pass_number filters: overridden "
            "by the time filter resolved through Altimetry Search."
        )

    logger.debug("Altimetry Search resolved granule filters: %s", granule_filters)
    filters.update(granule_filters)


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


@authenticate
def get(
    product_short_name: str,
    output_dir: str | pl.Path,
    cycle_number: int | list[int] | None = None,
    pass_number: int | list[int] | None = None,
    time: tuple[np.datetime64, np.datetime64] | None = None,
    version: str | None = None,
    overwrite: bool = False,
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

    resolved = _resolve_selected_passes(filters)
    if resolved is None:
        return []
    if resolved is not _NO_TIME_FILTER:
        _, passes = resolved
        _apply_selected_passes(filters, passes)

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
        lon_max (the convention must be changed to verify this constraint).
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

    resolved = _resolve_selected_passes(filters)
    if resolved is None:
        return []
    if resolved is not _NO_TIME_FILTER:
        mission, passes = resolved
        if box is not None:
            # Chain selected_passes -> pass_passage_time: keep only the
            # passes whose ground track crosses box.
            passage_time = altisearch.pass_passage_time(passes, box, mission)
            if passage_time.empty:
                logger.info("No pass of mission %s crosses box %s.", mission, box)
                return []
            _log_passes("pass_passage_time", mission, passage_time)
            passes = passes[passes["pass_number"].isin(passage_time["pass_number"])]
            _log_passes("passes retained after bbox filtering", mission, passes)
        _apply_selected_passes(filters, passes)

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