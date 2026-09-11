import os

from .auth import NCRC_PATH, ensure_credentials

# Must run before any submodule import: some of them transitively load
# netCDF4 (e.g. `altimetry_search_requests` -> pyinterp), and netCDF4-c only
# reads NCRCENV_RC once, at its own import time. Setting it later (e.g. in
# ensure_credentials(), called lazily from get()/subset()) has no effect.
os.environ.setdefault("NCRCENV_RC", NCRC_PATH.as_posix())

from .catalog_client.client import get_product_from_short_name  # noqa: E402
from .catalog_client.geonetwork.models.model import (  # noqa: E402
    AvisoCatalog,
    AvisoProduct,
)
from .catalog_client.granule_discoverer import filter_infos  # noqa: E402
from .core import details, get, subset, summary  # noqa: E402

__all__ = [
    "summary",
    "details",
    "get",
    "AvisoProduct",
    "AvisoCatalog",
    "filter_infos",
    "get_product_from_short_name",
    "subset",
    "ensure_credentials",
]
