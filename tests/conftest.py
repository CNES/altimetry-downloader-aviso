import datetime as dt
import json
import re
from enum import Enum, auto
from pathlib import Path
from unittest.mock import Mock

import fcollections.implementations
import pytest
from fcollections.core import (
    FileNameConvention,
    FileNameFieldInteger,
    FileNameFieldString,
    FilesDatabase,
    Layout,
    OpenMfDataset,
)
from fcollections.time import Period
from requests.exceptions import ProxyError

import altimetry_downloader_aviso.auth
from altimetry_downloader_aviso.catalog_client._granules_utils import RemoteDirNode
from altimetry_downloader_aviso.catalog_client.granule_discoverer import Protocol

# PATCH GEONETWORK CATALOG RESPONSES


@pytest.fixture
def catalog_response():
    fixture_path = Path(__file__).parent / "resources" / "catalog_response.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def catalog_response2():
    fixture_path = Path(__file__).parent / "resources" / "catalog_response2.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def bad_catalog_response():
    fixture_path = Path(__file__).parent / "resources" / "bad_catalog_response.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def product_response():
    fixture_path = Path(__file__).parent / "resources" / "product_response.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def product_response2():
    fixture_path = Path(__file__).parent / "resources" / "product_response2.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def bad_product_responses():
    fixture_path = Path(__file__).parent / "resources" / "bad_product_responses.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def mock_post(mocker, catalog_response):
    mock_post = mocker.patch(
        "altimetry_downloader_aviso.catalog_client.client.requests.post"
    )
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = catalog_response
    mock_post.return_value = mock_response
    return mock_post


@pytest.fixture(autouse=True)
def mock_get(mocker, product_response):
    mock_get = mocker.patch(
        "altimetry_downloader_aviso.catalog_client.client.requests.get"
    )
    mock_response = mocker.Mock()
    mock_response.content = b"fake file contents"
    mock_response.status_code = 200
    mock_response.json.return_value = product_response
    mock_get.return_value = mock_response
    return mock_get


# PATCH GRANULES DISCOVERING


class FileNameConventionTestOld(FileNameConvention):

    def __init__(self):
        super().__init__(
            regex=re.compile(r"dataset_(?P<a_number>\d{2}).nc"),
            fields=[FileNameFieldInteger("a_number")],
            generation_string="dataset_{a_number:0>2d}.nc",
        )


class FileNameConventionTest(FileNameConvention):

    def __init__(self):
        super().__init__(
            regex=re.compile(
                r"dataset_(?P<cycle_number>\d{2})_(?P<pass_number>\d{2}).nc"
            ),
            fields=[
                FileNameFieldInteger("cycle_number"),
                FileNameFieldInteger("pass_number"),
            ],
            generation_string="dataset_{cycle_number:0>2d}_{pass_number:0>2d}.nc",
        )


TEST_LAYOUT = Layout(
    [
        FileNameConvention(
            re.compile("product(?P<path_filter>.*)_path"),
            [FileNameFieldString("path_filter")],
            "product{path_filter!f}_path",
        ),
        FileNameConvention(
            re.compile(r"cycle_(?P<cycle_number>\d{2})"),
            [FileNameFieldInteger("cycle_number")],
            "cycle_{cycle_number:0>2d}",
        ),
        FileNameConventionTest(),
    ]
)

TEST_PRODUCT_LAYOUT = Layout(
    [
        FileNameConvention(
            re.compile(r"cycle_(?P<cycle_number>\d{2})"),
            [FileNameFieldInteger("cycle_number")],
            "cycle_{cycle_number:0>2d}",
        ),
        FileNameConventionTest(),
    ]
)


class MyDatabase(FilesDatabase):
    layouts = [TEST_PRODUCT_LAYOUT]
    reader = OpenMfDataset()

    def time_coverage(self, **kwargs):
        return Period(dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 8))


class MyDatabase2(FilesDatabase):
    layouts = [TEST_LAYOUT, Layout([FileNameConventionTest()])]

    def time_coverage(self, **kwargs):
        return Period(dt.datetime(2025, 1, 1), dt.datetime(2025, 1, 8))

    def half_orbit_range(self, **kwargs):
        return ((1, 1), (2, 3))

    def _filter_values(self, filter_name, **kwargs):
        return {"v1", "v2"}


class SubsetMock(Enum):
    foo = auto()
    bar = auto()


class MyDatabase3(MyDatabase2):
    @property
    def subsets(self):
        # Create a case similar to the reality: subset if an enum with a name attribute
        return [
            {"subset": SubsetMock.foo, "version": "s1"},
            {"subset": SubsetMock.foo, "version": "s2"},
            {"subset": SubsetMock.bar, "version": "s1"},
        ]


# Add version in the partitioning keys. This is a hint that is used to detect that we
# can use the 'subsets' property for getting the 'version' possible values. If 'version'
# is not a partitioning key, the implementation will default to the
# FilesDatabase.filter_values method.
MyDatabase3.unmixer = Mock()
MyDatabase3.unmixer.keys = {"version"}

# Mock the parser property to ensure that the incompatibility between
# FileNameFieldConventionTest and the unmixer is not detected ('version' field is not in
# the test convention). An cleaner alternative would be to rewrite the test closer to
# the real use case with a 'version' field.
MyDatabase3.parser = Mock()
MyDatabase3.parser.fields = {FileNameFieldString("version")}


@pytest.fixture
def product_handler_cls() -> type[FilesDatabase]:
    return MyDatabase


@pytest.fixture(scope="session")
def product_handler() -> FilesDatabase:
    root_node = RemoteDirNode(
        "root", {"name": "https://tds.mock/catalog.xml"}, 0, Protocol.HTTP
    )
    instance = MyDatabase2("root", fs=Mock())
    instance.discoverer.root_node = root_node
    return instance


@pytest.fixture(scope="session")
def product_handler_bad() -> FilesDatabase:
    root_node = RemoteDirNode(
        "root", {"name": "https://bad_url/catalog.xml"}, 0, Protocol.HTTP
    )
    instance = MyDatabase2("root", fs=Mock())
    instance.discoverer.root_node = root_node
    return instance


@pytest.fixture(scope="session")
def product_handler_no_layouts() -> FilesDatabase:
    root_node = RemoteDirNode(
        "root", {"name": "https://tds.mock/catalog.xml"}, 0, Protocol.HTTP
    )
    instance = MyDatabase2("root", fs=Mock(), enable_layouts=False)
    instance.discoverer.root_node = root_node
    return instance


@pytest.fixture
def test_product_layout():
    return TEST_PRODUCT_LAYOUT


@pytest.fixture(autouse=True)
def patch_all(mocker):
    setattr(fcollections.implementations, "MyDatabase", MyDatabase)
    setattr(fcollections.implementations, "MyDatabase2", MyDatabase2)
    setattr(fcollections.implementations, "MyDatabase3", MyDatabase3)

    for x in [
        "altimetry_downloader_aviso.catalog_client._granules_utils.TDS_LAYOUT_CONFIG",
        "altimetry_downloader_aviso.catalog_client.client.TDS_LAYOUT_CONFIG",
        "altimetry_downloader_aviso.tds_client.TDS_LAYOUT_CONFIG",
        "altimetry_downloader_aviso.core.TDS_LAYOUT_CONFIG",
    ]:
        mocker.patch(x, Path(__file__).parent / "resources" / "tds_layout.yaml")

    for x in [
        "altimetry_downloader_aviso.tds_client.TDS_CATALOG_BASE_URL",
        (
            "altimetry_downloader_aviso.catalog_client._granules_utils."
            "TDS_CATALOG_BASE_URL"
        ),
    ]:
        mocker.patch(x, "https://tds.mock/")

    for x in [
        "altimetry_downloader_aviso.auth.ensure_credentials",
        "altimetry_downloader_aviso.core.ensure_credentials",
    ]:
        mocker.patch(x)


@pytest.fixture(autouse=True)
def bypass_download_confirmation(mocker):
    mocker.patch("altimetry_downloader_aviso.core.confirm_download", return_value=True)


# PATCH TDS CATALOG CONTENT


@pytest.fixture(autouse=True)
def mock_tds_catalog(mocker):
    """Recursive TDSCatalog mock with three sub-catalogs.

    Testing tree structure:
    / -> https://tds.mock/catalog.xml
    - dataset_03_01.nc
    /productA_path/ -> https://tds.mock/productA_path/catalog.xml
        /cycle_02/  -> https://tds.mock/productA_path/cycle_02/catalog.xml
            - dataset_02_02.nc
            - dataset_02_22.nc
        /cycle_03/  -> https://tds.mock/productA_path/cycle_03/catalog.xml
            - dataset_03_03.nc
            - dataset_03_33.nc
    /productB_path/ -> https://tds.mock/productB_path/catalog.xml
        /cycle_04/  -> https://tds.mock/productB_path/cycle_04/catalog.xml
        - dataset_04_04.nc
        - dataset_04_44.nc
    """

    def _get_dataset(path: str, nc: str, nb: str):
        mock_dataset = mocker.Mock()
        mock_dataset.access_urls = {
            "HTTPServer": f"https://tds.mock{path}/dataset_{nc:0>2d}_{nb:0>2d}.nc",
            "OPeNDAP": f"https://tds.mock{path}/dataset_{nc:0>2d}_{nb:0>2d}.nc",
        }
        return mock_dataset

    mock_catalog_vA_2 = mocker.Mock()
    mock_catalog_vA_2.datasets = {
        f"dataset_02_{nb:0>2d}.nc": _get_dataset("/productA_path/cycle_02", 2, nb)
        for nb in [2, 22]
    }
    mock_catalog_vA_2.catalog_refs = {}

    mock_ref_vA_2 = mocker.Mock()
    mock_ref_vA_2.href = "https://tds.mock/productA_path/cycle_02/catalog.xml"

    mock_catalog_vA_3 = mocker.Mock()
    mock_catalog_vA_3.datasets = {
        f"dataset_03_{nb:0>2d}.nc": _get_dataset("/productA_path/cycle_03", 3, nb)
        for nb in [3, 33]
    }
    mock_catalog_vA_3.catalog_refs = {}

    mock_ref_vA_3 = mocker.Mock()
    mock_ref_vA_3.href = "https://tds.mock/productA_path/cycle_03/catalog.xml"

    mock_catalog_vB_4 = mocker.Mock()
    mock_catalog_vB_4.datasets = {
        f"dataset_04_{nb:0>2d}.nc": _get_dataset("/productB_path/cycle_04", 4, nb)
        for nb in [4, 44]
    }
    mock_catalog_vB_4.catalog_refs = {}

    mock_ref_vB_4 = mocker.Mock()
    mock_ref_vB_4.href = "https://tds.mock/productB_path/cycle_04/catalog.xml"

    mock_catalog_vA = mocker.Mock()
    mock_catalog_vA.datasets = {}
    mock_catalog_vA.catalog_refs = {
        "cycle_02": mock_ref_vA_2,
        "cycle_03": mock_ref_vA_3,
    }

    mock_ref_vA = mocker.Mock()
    mock_ref_vA.href = "https://tds.mock/productA_path/catalog.xml"

    mock_catalog_vB = mocker.Mock()
    mock_catalog_vB.datasets = {}
    mock_catalog_vB.catalog_refs = {
        "cycle_04": mock_ref_vB_4,
    }

    mock_ref_vB = mocker.Mock()
    mock_ref_vB.href = "https://tds.mock/productB_path/catalog.xml"

    def tds_catalog_side_effect(url):
        if url == "https://tds.mock/catalog.xml":
            mock_root = mocker.Mock()
            mock_root.datasets = {}
            mock_root.catalog_refs = {
                "productA_path": mock_ref_vA,
                "productB_path": mock_ref_vB,
            }
            return mock_root
        elif url == "https://tds.mock/productA_path/catalog.xml":
            return mock_catalog_vA
        elif url == "https://tds.mock/productA_path/cycle_02/catalog.xml":
            return mock_catalog_vA_2
        elif url == "https://tds.mock/productA_path/cycle_03/catalog.xml":
            return mock_catalog_vA_3
        elif url == "https://tds.mock/productB_path/catalog.xml":
            return mock_catalog_vB
        elif url == "https://tds.mock/productB_path/cycle_04/catalog.xml":
            return mock_catalog_vB_4
        else:
            raise ProxyError(
                f"HTTPSConnectionPool(host='{url}', port=443): Max retries "
                "exceeded with url: /L2-SWOT.html (Caused by ProxyError('Unable "
                "to connect to proxy', OSError('Tunnel connection failed: 503 "
                "Service Unavailable'))"
            )

    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils.TDSCatalog",
        side_effect=tds_catalog_side_effect,
    )


@pytest.fixture(autouse=True)
def fake_netrc_path(tmp_path, mocker):
    path = tmp_path / ".netrc"
    mocker.patch.object(altimetry_downloader_aviso.auth, "NETRC_PATH", path)
    path.write_text(
        """
        machine example.com login testuser password testpass
        machine tds-odatis.aviso.altimetry.fr login testuser password testpass
    """
    )
    return path


@pytest.fixture(autouse=True)
def fake_ncrc_path(tmp_path, mocker):
    path = tmp_path / ".ncrc"
    mocker.patch.object(altimetry_downloader_aviso.auth, "NCRC_PATH", path)
    return path
