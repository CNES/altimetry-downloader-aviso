from __future__ import annotations

import logging
import typing as tp
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import yaml
from fcollections.core import (
    FileNode,
    FilesDatabase,
    INode,
    LayoutVisitor,
    VisitResult,
)
from siphon.catalog import TDSCatalog

from .geonetwork import AvisoProduct

with warnings.catch_warnings():
    # ImportWarning is raised when the geographical functionalities are disabled. We do
    # not need these functionalities, so we can ignore this warning
    warnings.simplefilter("ignore", category=ImportWarning)
    import fcollections.implementations

if TYPE_CHECKING:
    # do not use tp.TYPE_CHECKING, else sphinx-autodoc-typehints will not load these
    # imports and will raise a warning.
    from fcollections.time import Period

    HalfOrbitRange = tuple[int, int], tuple[int, int]

logger = logging.getLogger(__name__)

TDS_CATALOG_BASE_URL = "https://tds-odatis.aviso.altimetry.fr/thredds/catalog/"

TDS_LAYOUT_CONFIG = Path(__file__).parent / "resources" / "tds_layout.yaml"


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
    ):
        super().__init__(name, info, level)
        self._children: list[INode] | None = None

    def accept(self, visitor: LayoutVisitor) -> VisitResult:
        return visitor.visit_dir(self)

    def children(self) -> tp.Iterable[INode]:
        # Cache children computation to avoid expensive relisting and ensure
        # that one path of the TDS tree will be represented by the same node
        if self._children is None:
            self._children = list(self._compute_children())
        return self._children

    def _compute_children(self) -> tp.Iterator[INode]:
        # return list of GranuleNode and RemoteFolderNode
        cat = TDSCatalog(self.info["name"])
        next_level = self.level + 1

        granules = [
            GranuleNode(name, {"name": d.access_urls["HTTPServer"]}, next_level)
            for name, d in cat.datasets.items()
        ]
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
            RemoteDirNode(folder, {"name": ref.href}, next_level)
            for folder, ref in cat.catalog_refs.items()
        ]
        logger.debug("%s has %d non-granule children", self.name, len(catalog_refs))

        return granules + catalog_refs


def filter_granules(product: AvisoProduct, **filters) -> list[str]:
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
    logger.info(
        "Filtering %s product with filters %s...",
        product.short_name,
        (lambda d: str(d))(filters),
    )

    # Get TDS product layout
    product_layout_conf = _parse_tds_layout(product)

    instance = _load_product_handler(product_layout_conf)

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
    # Get TDS product layout
    product_layout_conf = _parse_tds_layout(product)

    instance = _load_product_handler(product_layout_conf)

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


def _load_product_handler(product_config: ProductLayoutConfig) -> FilesDatabase:
    # Build TDS catalog URL
    tds_url = urljoin(
        TDS_CATALOG_BASE_URL,
        str(Path(product_config.catalog_path) / "catalog.xml"),
    )

    # Root node of the TDS. The node name (not the URL) should be given as an argument,
    # whereas the URL is given in the additional information
    root_node = RemoteDirNode(product_config.catalog_path, {"name": tds_url}, 0)

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
