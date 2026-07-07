from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from ..tds_client import Protocol
from .geonetwork import AvisoProduct

if TYPE_CHECKING:
    # do not use tp.TYPE_CHECKING, else sphinx-autodoc-typehints will not load these
    # imports and will raise a warning.
    from fcollections.time import Period

    HalfOrbitRange = tuple[int, int], tuple[int, int]

logger = logging.getLogger(__name__)

TDS_CATALOG_BASE_URL = "https://tds-odatis.aviso.altimetry.fr/thredds/catalog/"

TDS_LAYOUT_CONFIG = Path(__file__).parent / "resources" / "tds_layout.yaml"


def filter_granules(product: AvisoProduct, protocol: Protocol, **filters) -> list[str]:
    """Filter granules of a product in AVISO's Thredds Data Server.

    Parameters
    ----------
    product
        the aviso product
    **filters
        filters for files selection. Unknown filters for the requested product will be
        ignored.

    Returns
    -------
    list[str]
        the urls of the granules corresponding to the provided filters
    """
    # LAZY IMPORTS: delay fcollections import to import netCDF4 as late as possible.
    # This is to ensure we can properly setup the ncrc and netrc configuration files.
    # See the authentication module for more infos.
    from ._granules_utils import _load_product_handler, _parse_tds_layout

    logger.info(
        "Filtering %s product with filters %s...",
        product.short_name,
        (lambda d: str(d))(filters),
    )

    # Get TDS product layout
    product_layout_conf = _parse_tds_layout(product)

    instance = _load_product_handler(product_layout_conf, protocol)

    # Allow unknown filters for this method to add flexibility for the multiple products
    # handled in the AVISO downloader. We just ignore them instead of raising an error
    # (raising an error is the default behavior in the files listing)
    filters = {**product_layout_conf.default_filters, **filters}
    unknown_fiters = set(filters) - set(instance.listing_parameters)
    filters = {k: v for k, v in filters.items() if k not in unknown_fiters}
    logger.debug("Removed unknown filters %s", unknown_fiters)

    granules = instance.list_files(**filters)

    return granules.filename


def filter_infos(
    product: AvisoProduct,
) -> (
    tuple[
        dict[str, Period],
        dict[str, HalfOrbitRange],
        set[str] | None,
    ]
    | tuple[Period, None, set[str] | None]
):
    """Get temporal coverage, half orbit range and versions available for a
    given product.

    The temporal coverage and half orbit range are returned as dictionaries for each
    Swot phases in case. This will allow

    See Also
    --------
    :func:`altimetry_downloader_aviso.get_product_from_short_name`
        For getting a product from its short name.

    Parameters
    ----------
    product
        the aviso product.

    Returns
    -------
    tuple[dict[str, Period], dict[str, HalfOrbitRange], set[str] | None] \
        | tuple[Period, None, set[str] | None]
        The temporal coverage, half orbit range (if the product has half orbits) and
        versions available (if the product has multiple versions).
    """
    # LAZY IMPORTS: delay fcollections import to import netCDF4 as late as possible.
    # This is to ensure we can properly setup the ncrc and netrc configuration files.
    # See the authentication module for more infos.
    with warnings.catch_warnings():
        # ImportWarning is raised when the geographical functionalities are disabled. We
        # do not need these functionalities, so we can ignore this warning
        warnings.simplefilter("ignore", category=ImportWarning)
        import fcollections.implementations

    from ._granules_utils import _load_product_handler, _parse_tds_layout

    # Get TDS product layout
    product_layout_conf = _parse_tds_layout(product)

    instance = _load_product_handler(product_layout_conf, Protocol.HTTP)

    temporal_coverage = {}
    half_orbit_range = {}
    try:
        for phase in fcollections.implementations.SwotPhases:
            half_orbit_range[phase.name] = instance.half_orbit_range(
                **product_layout_conf.default_filters, phase=phase
            )
            temporal_coverage[phase.name] = instance.time_coverage(
                **product_layout_conf.default_filters, phase=phase
            )
    except AttributeError:
        half_orbit_range = None
        temporal_coverage = instance.time_coverage(
            **product_layout_conf.default_filters
        )

    try:
        subsets = instance.subsets
        if len(subsets) == 0 or "version" not in instance.unmixer.keys:
            versions = instance.filter_values(
                "version", **product_layout_conf.default_filters
            )
        else:
            versions = {
                s["version"]
                for s in instance.subsets
                if s["subset"].name == product_layout_conf.default_filters["subset"]
            }
    except ValueError:
        versions = None

    return temporal_coverage, half_orbit_range, versions
