import os
import warnings

from .auth import (
    NCRC_PATH,
    _setup_auth_env,
    _validate_ncrc_file,
    ensure_credentials,
)  # isort: skip

# Must run before any submodule import: some of them transitively load
# netCDF4 (e.g. `altimetry_search_requests` -> pyinterp), and netCDF4-c
# caches the .ncrc configuration once, at its own import time -- not per
# connection. Both must therefore be correct before that happens:
# - NCRCENV_RC (which .ncrc file to read)
# - the .ncrc file's content itself (the HTTP.NETRC entry), populated by
#   _validate_ncrc_file()
os.environ.setdefault("NCRCENV_RC", _setup_auth_env())

try:
    _validate_ncrc_file()
except OSError as e:
    warnings.warn(
        f"Could not configure netCDF4-c authentication file ({NCRC_PATH}): {e}. "
        "OpenDAP-based subsetting authentication may not work correctly.",
        stacklevel=2,
    )


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
