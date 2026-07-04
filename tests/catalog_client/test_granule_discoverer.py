import datetime as dt

import pytest
from fcollections.time import Period
from requests.exceptions import ProxyError

from altimetry_downloader_aviso.catalog_client.client import Protocol
from altimetry_downloader_aviso.catalog_client.geonetwork.models.model import (
    AvisoProduct,
)
from altimetry_downloader_aviso.catalog_client.granule_discoverer import (
    ProductLayoutConfig,
    RemoteDirNode,
    _import_product_handler,
    _parse_tds_layout,
    filter_granules,
    filter_infos,
)


class Test_FileSystemMetadataCollector:

    @pytest.mark.parametrize(
        "filter, exp_urls",
        [
            (
                {},
                [
                    "https://tds.mock/productA_path/cycle_02/dataset_02_02.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_02_22.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03_33.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04_04.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04_44.nc",
                ],
            ),
            (
                {"cycle_number": [3, 4]},
                [
                    "https://tds.mock/productA_path/cycle_03/dataset_03_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03_33.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04_04.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04_44.nc",
                ],
            ),
            (
                {"path_filter": "A"},
                [
                    "https://tds.mock/productA_path/cycle_02/dataset_02_02.nc",
                    "https://tds.mock/productA_path/cycle_02/dataset_02_22.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03_33.nc",
                ],
            ),
            (
                {"path_filter": "A", "cycle_number": 3},
                [
                    "https://tds.mock/productA_path/cycle_03/dataset_03_03.nc",
                    "https://tds.mock/productA_path/cycle_03/dataset_03_33.nc",
                ],
            ),
            (
                {"path_filter": "B"},
                [
                    "https://tds.mock/productB_path/cycle_04/dataset_04_04.nc",
                    "https://tds.mock/productB_path/cycle_04/dataset_04_44.nc",
                ],
            ),
            (
                {"cycle_number": "6"},
                [],
            ),
        ],
    )
    def test_find(self, product_handler, filter, exp_urls):
        dataframe = product_handler.list_files(**filter)
        urls = dataframe["filename"].tolist()

        assert urls == exp_urls

    def test_find_no_layout(self, product_handler_no_layouts):
        dataframe = product_handler_no_layouts.list_files()
        urls = dataframe["filename"].tolist()

        assert urls == [
            "https://tds.mock/productA_path/cycle_02/dataset_02_02.nc",
            "https://tds.mock/productA_path/cycle_02/dataset_02_22.nc",
            "https://tds.mock/productA_path/cycle_03/dataset_03_03.nc",
            "https://tds.mock/productA_path/cycle_03/dataset_03_33.nc",
            "https://tds.mock/productB_path/cycle_04/dataset_04_04.nc",
            "https://tds.mock/productB_path/cycle_04/dataset_04_44.nc",
        ]

    def test_find_bad_filter(self, product_handler):
        # Default behavior of the product handler in case of unknown filter. This is
        # overridden in the filter_granules method.
        with pytest.raises(ValueError, match="unexpected keyword argument"):
            product_handler.list_files(foo="bar")

    def test_find_bad_url(self, product_handler_bad):
        with pytest.raises(ProxyError) as exc_info:
            product_handler_bad.list_files()

        assert (
            "HTTPSConnectionPool(host='https://bad_url/catalog.xml', port=443): "
            "Max retries exceeded with url: /L2-SWOT.html (Caused by ProxyError"
            "('Unable to connect to proxy', OSError('Tunnel connection failed: 503 "
            "Service Unavailable'))"
        ) in str(exc_info.value)


def test_filter_granules():
    urls = filter_granules(AvisoProduct(id="productA"), Protocol.HTTP)
    assert list(urls) == [
        "https://tds.mock/productA_path/cycle_02/dataset_02_02.nc",
        "https://tds.mock/productA_path/cycle_02/dataset_02_22.nc",
        "https://tds.mock/productA_path/cycle_03/dataset_03_03.nc",
        "https://tds.mock/productA_path/cycle_03/dataset_03_33.nc",
    ]
    urls = filter_granules(AvisoProduct(id="productA"), Protocol.HTTP, pass_number=3)
    assert list(urls) == ["https://tds.mock/productA_path/cycle_03/dataset_03_03.nc"]


@pytest.mark.parametrize(
    "product, expected_time_coverage, expected_half_orbit_range, expected_versions",
    [
        (
            "productA",
            Period(dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 8)),
            None,
            None,
        ),
        (
            "productC",
            {
                "SCIENCE": Period(dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 8)),
                "CALVAL": Period(dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 8)),
            },
            {"SCIENCE": ((1, 1), (2, 3)), "CALVAL": ((1, 1), (2, 3))},
            {"v1", "v2"},
        ),
        (
            "productD",
            {
                "SCIENCE": Period(dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 8)),
                "CALVAL": Period(dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 8)),
            },
            {"SCIENCE": ((1, 1), (2, 3)), "CALVAL": ((1, 1), (2, 3))},
            {"s1", "s2"},
        ),
    ],
    ids=["time_series", "half_orbits", "half_orbits_versions_subset"],
)
def test_filter_infos(
    product, expected_time_coverage, expected_half_orbit_range, expected_versions
):
    time_coverage, half_orbit_range, versions = filter_infos(AvisoProduct(id=product))
    assert time_coverage == expected_time_coverage
    assert half_orbit_range == expected_half_orbit_range
    assert versions == expected_versions


def test_import_product_handler(product_handler_cls):
    conf = {"TEST_TYPE": "MyDatabase"}
    with pytest.raises(
        KeyError,
        match="The data type BAD_TYPE is missing from the "
        "tds_layout|granule_discovery configuration.",
    ):
        _import_product_handler(conf, "BAD_TYPE")

    product_handler = _import_product_handler(conf, "TEST_TYPE")
    assert product_handler == product_handler_cls


@pytest.mark.parametrize(
    "_id, short_name, default_filters",
    [
        ("productA", "sample_product_a", {}),
        ("productB", "sample_product_b", {"cycle_number": 4}),
    ],
)
def test_parse_tds_layout(product_handler_cls, _id, short_name, default_filters):
    pl_conf = _parse_tds_layout(AvisoProduct(id=_id, short_name=short_name))
    assert isinstance(pl_conf, ProductLayoutConfig)

    assert pl_conf.id == _id
    assert pl_conf.default_filters == default_filters
    assert pl_conf.catalog_path == f"{_id}_path"
    assert pl_conf.short_name == short_name
    assert pl_conf.product_handler == product_handler_cls


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


def test_bad_access_url_key():
    node = RemoteDirNode(
        "cycle_02",
        {"name": "https://tds.mock/productA_path/cycle_02/catalog.xml"},
        1,
        Protocol.HTTP,
    )
    node._access_url_key = "bad_url_key"
    with pytest.warns(UserWarning, match="Cannot retrieve access URL"):
        node.children()
