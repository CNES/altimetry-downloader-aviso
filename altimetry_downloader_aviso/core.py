import logging
import os
import pathlib as pl
import typing as tp

import numpy as np
import yaml

from .auth import AuthenticationError, ensure_credentials
from .catalog_client.client import (
    Protocol,
    fetch_catalog,
    get_details,
    get_product_from_short_name,
    search_granules,
)
from .catalog_client.geonetwork import AvisoCatalog, AvisoProduct
from .catalog_client.granule_discoverer import TDS_LAYOUT_CONFIG
from .subset import subset_multiple_files
from .tds_client import TDS_HOST, http_bulk_download

logger = logging.getLogger(__name__)


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

    granule_paths, _, non_target_local_files = _search_granules_with_overwrite(
        product_short_name, Protocol.HTTP, output_dir, overwrite, **filters
    )

    logger.debug("Downloading granules: %s...", list(granule_paths))

    try:
        return (
            list(
                http_bulk_download(
                    urls=granule_paths, output_dir=output_dir, overwrite=overwrite
                )
            )
            + non_target_local_files
        )

    except AuthenticationError as e:
        logging.error(e)
        return []


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

    filters = dict(
        filter(
            lambda item: item[1] is not None,
            zip(
                ["cycle_number", "pass_number", "time", "version"],
                [cycle_number, pass_number, time, version],
            ),
        )
    )

    granule_paths, target_local_files, non_target_local_files = (
        _search_granules_with_overwrite(
            product_short_name, Protocol.DAP2, output_dir, overwrite, **filters
        )
    )

    logger.info("Subsetting %d granules...", len(granule_paths))

    try:
        ensure_credentials(TDS_HOST)
        return (
            subset_multiple_files(
                granule_paths, target_local_files, box, selected_variables
            )
            + non_target_local_files
        )
    except AuthenticationError as e:
        logging.error(e)
        return []


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
        target_local_files = [f.as_posix() for f, e in zip(local_files, exist) if not e]
        non_target_local_files = [f.as_posix() for f, e in zip(local_files, exist) if e]
        logger.debug("%d files already exist and will be kept.", sum(exist))
    else:
        logger.debug("%d files already exist and will be overwritten.", sum(exist))
        target_local_files = [f.as_posix() for f in local_files]
        non_target_local_files = []

    return granule_paths, target_local_files, non_target_local_files
