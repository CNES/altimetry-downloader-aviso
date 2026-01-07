import logging
import os
import pathlib as pl

import numpy as np

from .auth import AuthenticationError
from .catalog_client.client import (
    fetch_catalog,
    get_details,
    search_granules,
)
from .catalog_client.geonetwork import AvisoCatalog, AvisoProduct
from .tds_client import http_bulk_download

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
        The list of downloaded local file paths
    """
    filters = {}
    if cycle_number is not None:
        filters["cycle_number"] = cycle_number
    if pass_number is not None:
        filters["pass_number"] = pass_number
    if time is not None:
        filters["time"] = time
    if version is not None:
        filters["version"] = version

    granule_paths = search_granules(product_short_name, **filters)

    if overwrite:
        logger.info("%d files to download.", len(granule_paths))
    else:
        local_files = [pl.Path(output_dir) / os.path.basename(p) for p in granule_paths]
        non_existing_granules = [
            p for p, f in zip(granule_paths, local_files) if not f.exists()
        ]
        logger.info(
            "%d files to download. %d files already exist.",
            len(non_existing_granules),
            len(granule_paths) - len(non_existing_granules),
        )

    logger.debug("Downloading granules: %s...", list(granule_paths))

    try:
        return list(
            http_bulk_download(
                urls=list(granule_paths), output_dir=output_dir, overwrite=overwrite
            )
        )

    except AuthenticationError as e:
        logging.error(e)
        return []
