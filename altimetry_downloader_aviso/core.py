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


def _log_altisearch(step: str, mission: tp.Any, **kwargs: tp.Any) -> None:
    """Debug-log an Altimetry Search result (cycles and/or passes found)."""
    details = ", ".join(f"{key}={value}" for key, value in kwargs.items())
    logger.debug("Altimetry Search %s: mission=%s, %s", step, mission, details)


def _resolve_cycle_pass_filters(
    product_short_name: str,
    filters: dict[str, tp.Any],
    box: tuple[float, float, float, float] | None,
) -> bool:
    """Resolve `cycle_number`/`pass_number` filters via Altimetry Search, in
    place. `time`, if present, is left untouched in `filters` -- it still
    reaches fcollections for a final selection there too.

    No-op if the product isn't organized by orbit cycle/pass (see
    `_product_queryable_by_pass`).

    Returns
    -------
        `False` if the request has no result (caller should return an
        empty list). `True` otherwise.

    Raises
    ------
    ValueError
        If an explicit `cycle_number` (used without `time`) spans more
        than one mission phase, or matches none.
    """
    if not _product_queryable_by_pass(product_short_name):
        return True

    time = filters.get("time")
    cycles = filters.get("cycle_number")
    passes = filters.get("pass_number")

    cycles = cycles if (cycles is None or isinstance(cycles, list)) else [cycles]
    passes = passes if (passes is None or isinstance(passes, list)) else [passes]

    if time is not None:
        # Time -> mission + cycle range
        mission = altisearch.mission_for(time)
        try:
            time_cycles = altisearch.get_selected_cycles(time, mission)
        except altisearch.NoPassFoundError as err:
            logger.info("%s", err)
            return False
        _log_altisearch("get_selected_cycles", mission, cycle_number=time_cycles)
        # Merge with explicit cycle_number if given
        cycles = sorted(set(cycles) & set(time_cycles)) if cycles else time_cycles
        if not cycles:
            logger.info(
                "cycle_number=%s does not intersect the cycles covering "
                "time (%s); request is inconsistent.",
                filters.get("cycle_number"),
                time,
            )
            return False
    elif cycles:
        # No time: mission from the explicit cycle_number instead.
        missions = {altisearch.mission_for_cycle(c) for c in cycles}
        if len(missions) != 1:
            msg = f"cycle_number {cycles} spans more than one mission phase."
            raise ValueError(msg)
        mission = missions.pop()
    else:
        # No time or cycle_number: fall back to Science.
        mission = altisearch.DEFAULT_MISSION
        logger.warning(
            "No time or cycle_number given: assuming the Science phase to "
            "resolve box, which may be wrong if you're after CalVal data. "
            "For accurate results, give a cycle_number range (or time) "
            "matching the phase you want -- run 'query-help' (CLI) or call "
            "filter_infos() (Python API) for help picking one."
        )

    if cycles:
        filters["cycle_number"] = sorted(cycles)

    # Box -> passes crossing it, merged with the explicit pass_number.
    if box is not None:
        crossing = altisearch.passes_crossing_polygon(mission, box, passes)
        if not crossing:
            logger.info("No pass of mission %s crosses box %s.", mission, box)
            return False
        _log_altisearch("passes_crossing_polygon", mission, pass_number=crossing)
        filters["pass_number"] = crossing

    logger.debug(
        "Altimetry Search resolved filters: cycle_number=%s, pass_number=%s",
        filters.get("cycle_number"),
        filters.get("pass_number"),
    )
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
    """Whether `time`/`box` can be resolved into `cycle_number`/`pass_number`
    via Altimetry Search for this product."""
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
        Selection box (lon_min, lat_min, lon_max, lat_max) in degrees. Longitude range
        can be in either [0, 360[ or [-180, 180[ convention. lon_min must be inferior to
        lon_max (the convention must be changed to verify this constraint). Always used
        to select the granules to download.
        `pass_number` narrows the candidate passes tested against `box` if given
        (otherwise every pass of the mission is tested).

    Raises
    ------
    ValueError
        If `cycle_number` spans more than one mission phase, or matches
        none.

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

    if not _resolve_cycle_pass_filters(product_short_name, filters, box):
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
        lon_max (the convention must be changed to verify this constraint). Used to
        select the granules to download, and to crop downloaded datasets.
        `pass_number` narrows the candidate passes tested against `box` if given
        (otherwise every pass of the mission is tested).

    selected_variables
        List of variables to select.

    Raises
    ------
    NotImplementedError
        In case the input product does not support subsetting: only swath datasets on a
        (num_lines, num_pixels) grid are supported.
    ValueError
        If `cycle_number` spans more than one mission phase, or matches
        none.

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

    if not _resolve_cycle_pass_filters(product_short_name, filters, box):
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
