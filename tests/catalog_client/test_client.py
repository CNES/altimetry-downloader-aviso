import os
from datetime import datetime

import pytest
import requests

from altimetry_downloader_aviso.catalog_client.client import (
    InvalidProductError,
    Protocol,
    _request_catalog,
    _request_product,
    fetch_catalog,
    get_details,
    get_product_from_short_name,
    search_granules,
)
from altimetry_downloader_aviso.catalog_client.geonetwork.models.model import (
    AvisoCatalog,
)


def test_request_catalog(mock_post):
    catalog_response = _request_catalog()
    assert catalog_response is not None

    mock_post.assert_called_once()

    expected_url = os.path.join(
        "https://sextant.ifremer.fr/geonetwork/srv/api/", "search/records/_search"
    )
    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == expected_url

    assert "Accept" in call_kwargs["headers"]
    assert call_kwargs["headers"]["Accept"] == "application/json"


def test_request_catalog_http_error(mock_post):
    mock_response = mock_post.MagicMock()
    mock_response.raise_for_status.side_effect = Exception("Server Error 500")
    mock_post.return_value = mock_response
    with pytest.raises(Exception, match="Server Error 500"):
        _request_catalog()


def test_fetch_catalog():
    catalog = fetch_catalog()

    assert isinstance(catalog, AvisoCatalog)
    assert len(catalog.products) == 2
    assert catalog.products[0].short_name == "sample_product_a"
    assert catalog.products[1].short_name == "sample_product_b"


def test_request_product(mock_get):
    _id = "id"
    product_response = _request_product(product_id=_id)
    assert product_response is not None

    mock_get.assert_called_once()

    call_args, _ = mock_get.call_args
    assert (
        call_args[0] == f"https://sextant.ifremer.fr/geonetwork/srv/api/records/{_id}"
    )


def test_request_product_http_error(mock_get):
    mock_response = mock_get.MagicMock()
    mock_response.raise_for_status.side_effect = Exception("Server Error 500")
    mock_get.return_value = mock_response
    with pytest.raises(Exception, match="Server Error 500"):
        _request_product(product_id="record")


def test_request_product_timeout(mocker):
    mocker.patch("requests.get", side_effect=requests.Timeout)

    with pytest.raises(RuntimeError, match="Timeout after .* seconds"):
        _request_product("fake-id", timeout=1.0)


def test_request_product_requestexception(mocker):
    mocker.patch("requests.get", side_effect=requests.RequestException)

    with pytest.raises(RuntimeError, match="HTTP Error"):
        _request_product(
            "fake-id",
        )


def test_get_details():
    with pytest.raises(InvalidProductError):
        get_details(product_short_name="bad_short_name")

    product = get_details(product_short_name="sample_product_a")
    assert product.title == "Sample Product A"
    assert product.short_name == "sample_product_a"
    assert product.id == "productA"
    assert product.tds_catalog_url == "https://tds.mock/productA_path/catalog.xml"
    assert product.abstract == "This is an abstract."
    assert product.last_version == "1.2.3"
    assert product.credit == "Data provided by AVISO"
    assert product.processing_level == "L2"
    assert product.doi == "https://doi.org/10.1234/productA"
    assert product.last_update == datetime(2023, 6, 15, 0, 0)


@pytest.mark.parametrize(
    "short_name, id",
    [("sample_product_a", "productA"), ("sample_product_b", "productB")],
)
def test_get_product_from_short_name(short_name, id):
    product = get_product_from_short_name(short_name)

    assert product.id == id
    assert product.short_name == short_name

    assert product.tds_catalog_url == f"https://tds.mock/{id}_path/catalog.xml"


def test_get_product_from_short_name_error():
    with pytest.raises(InvalidProductError):
        get_product_from_short_name("bad_short_name")


@pytest.mark.parametrize(
    "short_name, filters, exp_granules",
    [
        (
            "sample_product_a",
            {},
            [
                "https://tds.mock/productA_path/cycle_02/dataset_02_02.nc",
                "https://tds.mock/productA_path/cycle_02/dataset_02_22.nc",
                "https://tds.mock/productA_path/cycle_03/dataset_03_03.nc",
                "https://tds.mock/productA_path/cycle_03/dataset_03_33.nc",
            ],
        ),
        (
            "sample_product_a",
            {
                "cycle_number": 2,
            },
            [
                "https://tds.mock/productA_path/cycle_02/dataset_02_02.nc",
                "https://tds.mock/productA_path/cycle_02/dataset_02_22.nc",
            ],
        ),
        (
            "sample_product_a",
            {
                "pass_number": 3,
            },
            ["https://tds.mock/productA_path/cycle_03/dataset_03_03.nc"],
        ),
        (
            "sample_product_b",
            {},
            [
                "https://tds.mock/productB_path/cycle_04/dataset_04_04.nc",
                "https://tds.mock/productB_path/cycle_04/dataset_04_44.nc",
            ],
        ),
        (
            "sample_product_b",
            {"other_filter": "bad"},
            [
                "https://tds.mock/productB_path/cycle_04/dataset_04_04.nc",
                "https://tds.mock/productB_path/cycle_04/dataset_04_44.nc",
            ],
        ),
    ],
)
def test_search_granules(short_name, filters, exp_granules):
    granules = search_granules(short_name, Protocol.HTTP, **filters)
    assert list(granules) == exp_granules


def test_search_granules_error():
    with pytest.raises(InvalidProductError):
        search_granules("Bad Product", Protocol.HTTP)


@pytest.mark.parametrize(
    "short_name, filters",
    [
        (
            "sample_product_a",
            {
                "cycle_number": "bad",
            },
        ),
        (
            "sample_product_a",
            {
                "cycle_number": 2,
                "pass_number": 3,
            },
        ),
        ("sample_product_b", {"pass_number": 55}),
    ],
)
def test_search_granules_bad_filter(short_name, filters):
    granules = search_granules(short_name, Protocol.HTTP, **filters)
    assert list(granules) == []
