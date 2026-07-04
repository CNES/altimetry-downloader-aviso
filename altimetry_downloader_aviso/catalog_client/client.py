from __future__ import annotations

import logging
import typing as tp
import urllib.parse
from pathlib import Path

import requests
import yaml

from .geonetwork import (
    AvisoCatalog,
    AvisoProduct,
    Field,
    GeoNetworkQueryBuilder,
    parse_catalog_response,
    parse_product_response,
)
from .granule_discoverer import TDS_LAYOUT_CONFIG, Protocol, filter_granules

if tp.TYPE_CHECKING:
    import pandas as pda_t

logger = logging.getLogger(__name__)

# Keep the trailing / to join url with urlib.parse.urljoin
AVISO_CATALOG_URL = "https://sextant.ifremer.fr/geonetwork/srv/api/"


class InvalidProductError(Exception):
    """Exception raised when a product doesn't exist in the catalog."""


def fetch_catalog() -> AvisoCatalog:
    """Fetches CDS-AVISO and SWOT products from AVISO's catalog.

    Returns
    -------
        the AVISO catalog object containing all the CDS-AVISO and SWOT products
    """
    logger.info("Fetching products from Aviso's catalog...")
    resp = _request_catalog()
    catalog = parse_catalog_response(resp)
    return catalog


def get_details(product_short_name: str) -> AvisoProduct:
    """Details a product information from AVISO's catalog.

    Parameters
    ----------
    product_short_name: str
        the short name of the product

    Returns
    -------
        the product details

    Raises
    ------
    InvalidProductError
        In case the product short name doesn't correspond to any product
    RuntimeError
        In case an exception happens when requesting catalog
    """
    product = get_product_from_short_name(product_short_name)
    logger.info("Requesting '%s' product from Aviso's catalog...", product_short_name)
    resp = _request_product(product.id)
    product = parse_product_response(resp, product)
    return product


def search_granules(
    product_short_name: str, protocol: Protocol.HTTP, **filters
) -> pda_t.Series[str]:
    """Search for granules of a product in AVISO's Thredds Data Server.

    Parameters
    ----------
    product_short_name: str
        the short name of the product
    protocol
        Whether the granule URL should return the fileAccess (HTTP) or OpenDAP protocol.
    **filters
        filters for files selection. Unknown filters for the requested product will be
        ignored.

    Returns
    -------
        the urls of the granules corresponding to the provided filters

    Raises
    ------
    InvalidProductError
        In case the product short name doesn't correspond to any product
    """
    product = get_product_from_short_name(product_short_name)
    return filter_granules(product, protocol, **filters)


def get_product_from_short_name(product_short_name: str) -> AvisoProduct:
    """Search for a product in AVISO's catalog from its short name."""
    catalog = fetch_catalog()
    for p in catalog.products:
        if p.short_name == product_short_name:
            return p
    msg = f'Invalid product short_name "{product_short_name}"'
    raise InvalidProductError(msg)


def _request_catalog() -> dict:
    """Request AVISO's catalog products: filters on CDS-AVISO and SWOT."""
    url = urllib.parse.urljoin(AVISO_CATALOG_URL, "search/records/_search")

    # Retrieve the list of configured products from the TDS layout declaration. The IDs
    # will be used to restrict the perimeter (aka supported products) of the client.
    builder = GeoNetworkQueryBuilder()
    with open(TDS_LAYOUT_CONFIG) as f:
        tds_layout = yaml.safe_load(f)
        known_ids = tds_layout["products"].keys()

    payload = (
        builder.must_term(Field.DATA_CENTER, "CDS-AVISO")
        .must_term(Field.PLATFORMS, "SWOT")
        .must_terms(Field.ID, list(known_ids))
        .build()
    )

    resp = requests.post(url, json=payload, headers={"Accept": "application/json"})
    resp.raise_for_status()

    return resp.json()


def _request_product(product_id: str, timeout: float = 10.0):
    """Request AVISO's catalog product details."""
    url = urllib.parse.urljoin(
        AVISO_CATALOG_URL, (Path("records") / product_id).as_posix()
    )

    try:
        resp = requests.get(
            url, headers={"Accept": "application/json"}, timeout=timeout
        )
        resp.raise_for_status()

    except requests.Timeout:
        msg = f"Timeout after {timeout} seconds when requesting {url}"
        raise RuntimeError(msg)

    except requests.RequestException as e:
        msg = f"HTTP Error : {e}"
        raise RuntimeError(msg)

    return resp.json()
