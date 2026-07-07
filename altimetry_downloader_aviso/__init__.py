from .auth import ensure_credentials
from .catalog_client.client import get_product_from_short_name
from .catalog_client.geonetwork.models.model import AvisoCatalog, AvisoProduct
from .catalog_client.granule_discoverer import filter_infos
from .core import details, get, subset, summary

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
