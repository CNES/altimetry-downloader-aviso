import pytest
from fcollections.core import FileSystemMetadataCollector, Layout
from requests.exceptions import ProxyError

from altimetry_downloader_aviso.catalog_client.geonetwork.models.model import (
    AvisoProduct,
)
from altimetry_downloader_aviso.catalog_client.granule_discoverer import (
    ProductLayoutConfig,
    RemoteDirNode,
    _load_convention_layout,
    _parse_tds_layout,
    filter_granules,
)


@pytest.fixture
def metadata_collector(test_layouts: list[Layout]) -> FileSystemMetadataCollector:
    root_node = RemoteDirNode("root", {"name": "https://tds.mock/catalog.xml"}, 0)
    return FileSystemMetadataCollector(test_layouts, root_node)


class Test_FileSystemMetadataCollector:

    @pytest.mark.parametrize(
        "filter, exp_urls",
        [
            (
                {},
                [
                    "https://tds.mock/dataset_01.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_02.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_22.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_33.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_44.nc",
                ],
            ),
            (
                {"cycle_number": [3, 4]},
                [
                    "https://tds.mock/dataset_01.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_33.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_44.nc",
                ],
            ),
            (
                {"path_filter": "A"},
                [
                    "https://tds.mock/dataset_01.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_02.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_22.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_33.nc",
                ],
            ),
            (
                {"path_filter": "A", "cycle_number": 3},
                [
                    "https://tds.mock/dataset_01.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_33.nc",
                ],
            ),
            (
                {"path_filter": "B"},
                [
                    "https://tds.mock/dataset_01.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_44.nc",
                ],
            ),
            (
                {"path_filter": "C"},
                [
                    "https://tds.mock/dataset_01.nc",
                ],
            ),
            (
                {"cycle_number": "6"},
                [
                    "https://tds.mock/dataset_01.nc",
                ],
            ),
        ],
    )
    def test_find(self, metadata_collector, filter, exp_urls):
        dataframe = metadata_collector.to_dataframe(**filter)
        urls = dataframe["filename"].tolist()

        assert urls == exp_urls

    def test_find_not_layout(self, metadata_collector):
        dataframe = metadata_collector.to_dataframe(filter1=12, enable_layouts=False)
        urls = dataframe["filename"].tolist()

        assert urls == [
            "https://tds.mock/dataset_01.nc",
            "https://tds.mock/productA_path/cycle_02/dataset_02.nc",
            "https://tds.mock/productA_path/cycle_02/dataset_22.nc",
            "https://tds.mock/productA_path/cycle_03/dataset_03.nc",
            "https://tds.mock/productA_path/cycle_03/dataset_33.nc",
            "https://tds.mock/productB_path/cycle_04/dataset_04.nc",
            "https://tds.mock/productB_path/cycle_04/dataset_44.nc",
        ]

    @pytest.mark.parametrize(
        "filter, exp_urls",
        [
            (
                {"bad_filter": "B"},
                [
                    "https://tds.mock/dataset_01.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_02.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_22.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_33.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_44.nc",
                ],
            )
        ],
    )
    def test_find_bad_filter(self, metadata_collector, filter, exp_urls):
        # No warning, only a log message stating that the parameter is ignored
        dataframe = metadata_collector.to_dataframe(**filter)
        urls = dataframe["filename"].tolist()
        assert urls == exp_urls

    def test_find_bad_url(self, test_layouts):
        root_node = RemoteDirNode("root", {"name": "https://bad_url/catalog.xml"}, 0)
        collector = FileSystemMetadataCollector(test_layouts, root_node)
        with pytest.raises(ProxyError) as exc_info:
            collector.to_dataframe()

        assert (
            "HTTPSConnectionPool(host='https://bad_url/catalog.xml', port=443): "
            "Max retries exceeded with url: /L2-SWOT.html (Caused by ProxyError"
            "('Unable to connect to proxy', OSError('Tunnel connection failed: 503 "
            "Service Unavailable'))"
        ) in str(exc_info.value)


def test_filter_granules():
    urls = filter_granules(AvisoProduct(id="productA"))
    assert list(urls) == [
        "https://tds.mock/productA_path/cycle_02/dataset_02.nc",
        "https://tds.mock/productA_path/cycle_02/dataset_22.nc",
        "https://tds.mock/productA_path/cycle_03/dataset_03.nc",
        "https://tds.mock/productA_path/cycle_03/dataset_33.nc",
    ]
    urls = filter_granules(AvisoProduct(id="productA"), pass_number=3)
    assert list(urls) == ["https://tds.mock/productA_path/cycle_03/dataset_03.nc"]


def test_load_convention_layout(patch_some, test_layouts):
    conf = {"TEST_TYPE": "MyDatabase"}
    with pytest.raises(
        KeyError,
        match="The data type BAD_TYPE is missing from the "
        "tds_layout|granule_discovery configuration.",
    ):
        _load_convention_layout(conf, "BAD_TYPE")

    layouts = _load_convention_layout(conf, "TEST_TYPE")
    assert layouts == test_layouts


@pytest.mark.parametrize(
    "_id, short_name, path_filter",
    [("productA", "sample_product_a", "A"), ("productB", "sample_product_b", "B")],
)
def test_parse_tds_layout(patch_some, test_layouts, _id, short_name, path_filter):
    pl_conf = _parse_tds_layout(AvisoProduct(id=_id, short_name=short_name))
    assert isinstance(pl_conf, ProductLayoutConfig)

    assert pl_conf.id == _id
    assert pl_conf.default_filters == {"path_filter": path_filter}
    assert pl_conf.catalog_path == f"{_id}_path"
    assert pl_conf.short_name == short_name
    assert pl_conf.layouts == test_layouts


def test_parse_tds_layout_no_filter():
    pl_conf = _parse_tds_layout(AvisoProduct(id="productC"))
    assert isinstance(pl_conf, ProductLayoutConfig)

    assert pl_conf.default_filters == {}


def test_parse_tds_layout_bad_product():
    with pytest.raises(
        KeyError,
        match="The product bad_product_id is missing from the "
        "tds_layout configuration file.",
    ):
        _parse_tds_layout(AvisoProduct(id="bad_product_id"))
