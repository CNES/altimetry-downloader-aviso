import logging
import netrc
import os
from datetime import datetime

import pytest

from altimetry_downloader_aviso.catalog_client.client import InvalidProductError
from altimetry_downloader_aviso.core import details, get, summary


def test_summary():
    catalog = summary()
    assert len(catalog.products) == 2
    assert catalog.products[0].title == "Sample Product A"
    assert catalog.products[0].short_name == "sample_product_a"
    assert catalog.products[1].title == "Sample Product B"
    assert catalog.products[1].short_name == "sample_product_b"


def test_details():
    with pytest.raises(InvalidProductError):
        details(product_short_name="bad_short_name")

    product = details(product_short_name="sample_product_a")
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
    assert product.resolution == "2 km"


@pytest.mark.parametrize(
    "short_name, filters, files",
    [
        (
            "sample_product_a",
            {},
            ["dataset_02.nc", "dataset_22.nc", "dataset_03.nc", "dataset_33.nc"],
        ),
        (
            "sample_product_a",
            {
                "cycle_number": 2,
            },
            ["dataset_02.nc", "dataset_22.nc"],
        ),
        ("sample_product_a", {"pass_number": 3}, ["dataset_03.nc"]),
        (
            "sample_product_a",
            {"time": ("2025-04-04", "2025-04-05"), "version": "2.1.1"},
            ["dataset_02.nc", "dataset_22.nc", "dataset_03.nc", "dataset_33.nc"],
        ),
        ("sample_product_b", {}, ["dataset_04.nc", "dataset_44.nc"]),
    ],
)
def test_get(tmp_path, short_name, filters, files):
    local_files = get(product_short_name=short_name, output_dir=tmp_path, **filters)

    assert local_files == [os.path.join(tmp_path, f) for f in files]


def test_get_overwrite(tmp_path):
    short_name = "sample_product_a"
    filters = {"cycle_number": 2, "overwrite": False}
    files2 = ["dataset_02.nc", "dataset_22.nc"]
    local_files = get(product_short_name=short_name, output_dir=tmp_path, **filters)
    assert local_files == [os.path.join(tmp_path, f) for f in files2]

    filters = {"cycle_number": [2, 3], "overwrite": False}
    files3 = ["dataset_03.nc", "dataset_33.nc"]
    local_files = get(product_short_name=short_name, output_dir=tmp_path, **filters)
    assert local_files == [os.path.join(tmp_path, f) for f in files2 + files3]

    filters["overwrite"] = True
    local_files = get(product_short_name=short_name, output_dir=tmp_path, **filters)
    assert local_files == [os.path.join(tmp_path, f) for f in files2 + files3]


def test_get_error(tmp_path):
    with pytest.raises(InvalidProductError):
        get(product_short_name="bad_short_name", output_dir=tmp_path)
    with pytest.raises(TypeError):
        get(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            other_filter="bad",
        )


def test_get_auth_error(mocker, tmp_path, caplog):
    mocker.patch(
        "altimetry_downloader_aviso.auth.netrc.netrc",
        side_effect=netrc.NetrcParseError("Invalid netrc"),
    )

    with caplog.at_level(logging.ERROR):
        get(product_short_name="sample_product_a", output_dir=tmp_path)

    assert "Syntax error in .netrc file: Invalid netrc" in caplog.text


@pytest.mark.parametrize(
    "short_name, filters",
    [
        (
            "sample_product_a",
            {
                "cycle_number": "bad",
            },
        ),
        ("sample_product_a", {"cycle_number": 2, "pass_number": 3}),
        ("sample_product_b", {"pass_number": 55}),
    ],
)
def test_get_bad_filter(tmp_path, short_name, filters):
    assert get(product_short_name=short_name, output_dir=tmp_path, **filters) == []
