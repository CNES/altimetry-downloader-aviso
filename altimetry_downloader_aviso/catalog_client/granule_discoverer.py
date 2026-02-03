import logging
import typing as tp
import warnings
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import yaml
from fcollections.core import (
    FileNode,
    FilesDatabase,
    FileSystemMetadataCollector,
    INode,
    Layout,
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

logger = logging.getLogger(__name__)

TDS_CATALOG_BASE_URL = "https://tds-odatis.aviso.altimetry.fr/thredds/catalog/"

TDS_LAYOUT_CONFIG = Path(__file__).parent / "resources" / "tds_layout.yaml"


class GranuleNode(FileNode):
    """File node of a TDS tree."""


class RemoteDirNode(INode):

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
        # that one path on the filesystem will be represented by the same node
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

        return granules + catalog_refs


def filter_granules(product: AvisoProduct, **filters) -> list[str]:
    """Filter granules of a product in AVISO's Thredds Data Server.

    Parameters
    ----------
    product
        the aviso product
    **filters
        filters for files selection

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

    # Build TDS catalog URL
    tds_url = urljoin(
        TDS_CATALOG_BASE_URL,
        str(Path(product_layout_conf.catalog_path) / "catalog.xml"),
    )

    # Root node of the TDS
    root_node = RemoteDirNode(product_layout_conf.catalog_path, {"name": tds_url}, 0)

    # Create the file discoverer for this TDS catalog
    file_discoverer = FileSystemMetadataCollector(
        layouts=product_layout_conf.layouts, root_node=root_node
    )

    filters = {**product_layout_conf.default_filters, **filters}

    granules = file_discoverer.to_dataframe(**filters)

    return granules.filename


def _load_convention_layout(
    granule_discovery: dict, data_type: str
) -> tuple[list[Layout]]:
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
    return files_database_cls.layouts


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
    convention: FileNameConvention
        Convention used for naming files related to the product.
    layout: Layout
        Layout structure used to organize the product files and directories.
    catalog_path: str
        Relative or absolute path to the product catalog location.
    default_filters: dict
        Default filters applied when querying or displaying the product.
    """

    id: str
    short_name: str
    layouts: list[Layout]
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
        layouts_obj = _load_convention_layout(granule_discovery, data_type)

        if "filters" not in product_layout:
            product_layout["filters"] = {}

        return ProductLayoutConfig(
            id=product.id,
            short_name=product_layout["short_name"],
            layouts=layouts_obj,
            catalog_path=product_layout["catalog_path"],
            default_filters=product_layout["filters"],
        )
