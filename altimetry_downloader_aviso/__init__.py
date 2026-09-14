import os

from .auth import _setup_auth_env, ensure_credentials  # isort: skip

# Configure netCDF4-c authentication as early as possible, before any
# submodule import that could transitively load netCDF4 (e.g.
# `altimetry_search_requests` -> pyinterp), since netCDF4-c only reads
# NCRCENV_RC once, at its own import time
os.environ.setdefault("NCRCENV_RC", _setup_auth_env())

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
