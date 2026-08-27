from __future__ import annotations

import concurrent.futures as cf
import logging
import typing as tp
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests
import yaml
from fcollections.core import (
    FileNode,
    FilesDatabase,
    INode,
    LayoutVisitor,
    VisitResult,
)
from siphon.catalog import TDSCatalog

from ..tds_client import TDS_CATALOG_BASE_URL, TDS_LAYOUT_CONFIG, Protocol
from .geonetwork import AvisoProduct

with warnings.catch_warnings():
    # ImportWarning is raised when the geographical functionalities are disabled. We do
    # not need these functionalities, so we can ignore this warning
    warnings.simplefilter("ignore", category=ImportWarning)
    import fcollections.implementations

if TYPE_CHECKING:
    HalfOrbitRange = tuple[int, int], tuple[int, int]

logger = logging.getLogger(__name__)


class GranuleNode(FileNode):
    """File node of a TDS tree."""


class RemoteDirNode(INode):
    """Folder node of a TDS tree.

    Parameters
    ----------
    name
        Name of the node (not the URL): ex. cycle_001
    info
        Additional information. "name" should be present and contain the URL
        ex. {"name": "https://tds.mock.fr/mydataset/catalog.xml"}
    level
        Level of the node with respect to the tree root. Set to 0 for the root.
    """

    def __init__(
        self,
        name: str,
        info: dict[str, tp.Any],
        level: int,
        protocol: Protocol,
    ):
        super().__init__(name, info, level)
        self._protocol = protocol
        self._access_url_key = "HTTPServer" if protocol == Protocol.HTTP else "OPeNDAP"
        self._children: list[INode] | None = None

    def accept(self, visitor: LayoutVisitor) -> VisitResult:
        return visitor.visit_dir(self)

    def children(self) -> tp.Iterable[INode]:
        # Cache children computation to avoid expensive relisting and ensure
        # that one path of the TDS tree will be represented by the same node
        # Will raise a UserWarning if a TDS entry does not have the requested URL key
        if self._children is None:
            self._children = list(self._compute_children())
        return self._children

    def _compute_children(self) -> tp.Iterator[INode]:
        # return list of GranuleNode and RemoteFolderNode
        cat = TDSCatalog(self.info["name"])
        next_level = self.level + 1

        granules = []
        for name, d in cat.datasets.items():
            try:
                granules.append(
                    GranuleNode(
                        name, {"name": d.access_urls[self._access_url_key]}, next_level
                    )
                )
            except KeyError as e:
                logger.exception(e)
                msg = f"Cannot retrieve access URL for granule {name}"
                warnings.warn(msg)
        logger.debug("%s has %d granule children", self.name, len(granules))

        # Each `catalog_refs` should have (name, ref), and it should be possible
        # to follow `ref` with `child = ref.follow()`. But there is a "name"
        # marker missing somewhere in the Odatis TDS catalog.xml, so it's not
        # possible to follow the ref directly.
        # Instead, we use the `href` and create a new TDSCatalog object with it.
        # Example:
        #   ref.href = https://tds-odatis.aviso.altimetry.fr/thredds/catalog/
        #              dataset-l3-swot-karin-nadir-validated/l3_lr_ssh/v1_0_1/Unsmoothed/
        #              cycle_001/catalog.xml
        catalog_refs = [
            RemoteDirNode(folder, {"name": ref.href}, next_level, self._protocol)
            for folder, ref in cat.catalog_refs.items()
        ]
        logger.debug("%s has %d non-granule children", self.name, len(catalog_refs))

        return granules + catalog_refs


def _load_product_handler(
    product_config: ProductLayoutConfig, protocol: Protocol
) -> FilesDatabase:
    # Build TDS catalog URL
    tds_url = urljoin(
        TDS_CATALOG_BASE_URL,
        (Path(product_config.catalog_path) / "catalog.xml").as_posix(),
    )

    # Root node of the TDS. The node name (not the URL) should be given as an argument,
    # whereas the URL is given in the additional information
    root_node = RemoteDirNode(
        product_config.catalog_path, {"name": tds_url}, 0, protocol
    )

    # Create the product handler instance. Use a fs.Mock to bypass catalog path exist
    # check in the file system.
    from unittest.mock import Mock

    product_handler = product_config.product_handler
    instance = product_handler(product_config.catalog_path, fs=Mock())

    # Override the root node using the custom node of this TDS catalog.
    instance.discoverer.root_node = root_node

    return instance


def _import_product_handler(
    granule_discovery: dict, data_type: str
) -> type[FilesDatabase]:
    """Load the fcollections convention and layout objects from a data type."""
    if data_type not in granule_discovery:
        msg = (
            f"The data type {data_type} is missing from the "
            "tds_layout|granule_discovery configuration."
        )
        raise KeyError(msg)
    files_database_cls_name = granule_discovery[data_type]

    files_database_cls: FilesDatabase = getattr(
        fcollections.implementations, files_database_cls_name
    )
    return files_database_cls


@dataclass
class ProductLayoutConfig:
    """Configuration of a product layout.

    Defines how a product is named, organized, and stored in the catalog.

    Attributes
    ----------
    id: str
        Unique identifier of the product layout.
    short_name: str
        Short name of the product (used as reference in CLI or metadata).
    product_handler: type[FilesDatabase]
        Product handler class used to list the product files. It notably contains the
        Layout structures used to organize the product files and directories. Contain
        semantic information for both folders and granules.
    catalog_path: str
        Relative or absolute path to the product catalog location.
    default_filters: dict
        Default filters applied when querying or displaying the product.
    """

    id: str
    short_name: str
    product_handler: type[FilesDatabase]
    catalog_path: str
    default_filters: dict


def _parse_tds_layout(product: AvisoProduct) -> ProductLayoutConfig:
    """Parse resources/tds_layout.yaml to retrieve the layout information.

    The yaml should have a 'products' and a 'granule_discovery'
    sections.
    """
    with open(TDS_LAYOUT_CONFIG) as f:

        tds_layout = yaml.safe_load(f)

        products_tds_layout = tds_layout["products"]
        if product.id not in products_tds_layout:
            msg = (
                f"The product {product.id} is missing from the "
                "tds_layout configuration file."
            )
            raise KeyError(msg)
        product_layout = products_tds_layout[product.id]

        granule_discovery = tds_layout["granule_discovery"]
        data_type = product_layout["data_type"]
        product_handler = _import_product_handler(granule_discovery, data_type)

        if "filters" not in product_layout:
            product_layout["filters"] = {}

        return ProductLayoutConfig(
            id=product.id,
            short_name=product.short_name,
            product_handler=product_handler,
            catalog_path=product_layout["catalog_path"],
            default_filters=product_layout["filters"],
        )


def _get_size_from_url(url: str, timeout: float = 5.0) -> tp.Optional[int]:
    """Return the size in bytes of a remote file via an HTTP HEAD request, or
    None if unavailable."""
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout)
        resp.raise_for_status()
        content_length = resp.headers.get("Content-Length")
        return int(content_length) if content_length is not None else None
    except requests.RequestException as e:
        logger.warning("Cannot retrieve size for %s: %s", url, e)
        return None


def estimate_total_size(
    urls: tp.Sequence[str], max_workers: int = 8
) -> tp.Tuple[int, int]:
    """Estimate total download size (bytes) for a list of granule URLs.

    Returns (total_bytes, unknown_count), the latter being the number of
    granules whose size could not be determined via HEAD.
    """
    total = 0
    unknown = 0
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for size in executor.map(_get_size_from_url, urls):
            if size is None:
                unknown += 1
            else:
                total += size
    return total, unknown


def format_size(num_bytes: float) -> str:
    """Format a byte count as a human-readable string (e.g. '1.3 GB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"
