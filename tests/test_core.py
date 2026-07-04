import logging
import netrc
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from altimetry_downloader_aviso.catalog_client.client import InvalidProductError
from altimetry_downloader_aviso.core import details, get, subset, summary


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
            [
                "dataset_02_02.nc",
                "dataset_02_22.nc",
                "dataset_03_03.nc",
                "dataset_03_33.nc",
            ],
        ),
        (
            "sample_product_a",
            {
                "cycle_number": 2,
            },
            ["dataset_02_02.nc", "dataset_02_22.nc"],
        ),
        ("sample_product_a", {"pass_number": 3}, ["dataset_03_03.nc"]),
        (
            "sample_product_a",
            {"time": ("2025-04-04", "2025-04-05"), "version": "2.1.1"},
            [
                "dataset_02_02.nc",
                "dataset_02_22.nc",
                "dataset_03_03.nc",
                "dataset_03_33.nc",
            ],
        ),
    ],
)
@pytest.mark.parametrize("command", [get, subset])
def test_get_subset(tmp_path, short_name, filters, files, command):
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name=short_name, output_dir=tmp_path, **filters
        )

    assert local_files == [str(tmp_path / f) for f in files]


def test_subset_parameters_passed(tmp_path):
    with patch(
        "altimetry_downloader_aviso.subset.subset_one_file", return_value=True
    ) as mock:
        subset(
            "sample_product_a",
            tmp_path,
            selected_variables=["foo", "bar"],
            box=(1, 1, 2, 2),
        )

    assert mock.call_args[0][2] == (1, 1, 2, 2)
    assert mock.call_args[0][3] == ["foo", "bar"]


@pytest.mark.parametrize("command", [get, subset])
def test_get_subset_overwrite(tmp_path, command):
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        short_name = "sample_product_a"
        filters = {"cycle_number": 2, "overwrite": False}
        files2 = ["dataset_02_02.nc", "dataset_02_22.nc"]
        local_files = get(product_short_name=short_name, output_dir=tmp_path, **filters)
        assert set(local_files) == {os.path.join(tmp_path, f) for f in files2}

        filters = {"cycle_number": [2, 3], "overwrite": False}
        files3 = ["dataset_03_03.nc", "dataset_03_33.nc"]
        local_files = command(
            product_short_name=short_name, output_dir=tmp_path, **filters
        )
        assert set(local_files) == {os.path.join(tmp_path, f) for f in files2 + files3}

        filters["overwrite"] = True
        local_files = get(product_short_name=short_name, output_dir=tmp_path, **filters)
        assert set(local_files) == {str(tmp_path / f) for f in files2 + files3}


@pytest.mark.parametrize("command", [get, subset])
def test_get_subset_invalid_product(tmp_path, command):
    with pytest.raises(InvalidProductError):
        command(product_short_name="bad_short_name", output_dir=tmp_path)


def test_subset_unsupported_product(tmp_path):
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        files = subset("sample_product_a", tmp_path)
        assert len(files) > 0

    with pytest.raises(NotImplementedError, match="not supported"):
        subset("sample_product_b", tmp_path)


@pytest.mark.parametrize("command", [get, subset])
def test_get_subset_invalid_filter(tmp_path, command):
    with pytest.raises(TypeError, match="unexpected keyword"):
        command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            other_filter="bad",
        )


@pytest.mark.parametrize("command", [get, subset])
def test_get_subset_auth_error(mocker, tmp_path, caplog, command):
    mocker.patch(
        "altimetry_downloader_aviso.auth.netrc.netrc",
        side_effect=netrc.NetrcParseError("Invalid netrc"),
    )

    with caplog.at_level(logging.ERROR):
        command(product_short_name="sample_product_a", output_dir=tmp_path)

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
        ("sample_product_a", {"pass_number": 55}),
    ],
)
@pytest.mark.parametrize("command", [get, subset])
def test_get_subset_bad_filters(tmp_path, short_name, filters, command):
    assert command(short_name, tmp_path, **filters) == []
