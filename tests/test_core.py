import os
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from altimetry_downloader_aviso import core as ac_core
from altimetry_downloader_aviso.auth import AuthenticationError
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
def test_get_subset_auth_error(mocker, tmp_path, command):
    mocker.patch(
        "altimetry_downloader_aviso.core.ensure_credentials",
        side_effect=AuthenticationError("Invalid netrc"),
    )

    with pytest.raises(AuthenticationError):
        command(product_short_name="sample_product_a", output_dir=tmp_path)


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


# ---------------------------------------------------------------------------
# _resolve_selected_passes / _intersect / _apply_selected_passes
# ---------------------------------------------------------------------------


def test_resolve_selected_passes_no_time_filter():
    filters = {"cycle_number": [2]}
    resolved = ac_core._resolve_selected_passes(filters)
    assert resolved is ac_core._NO_TIME_FILTER
    assert filters == {"cycle_number": [2]}


@pytest.mark.parametrize("time", [(None, None), None])
def test_resolve_selected_passes_time_none_filter(time):
    filters = {"cycle_number": [2], "time": time}
    resolved = ac_core._resolve_selected_passes(filters)
    assert resolved is ac_core._NO_TIME_FILTER
    assert filters == {"cycle_number": [2]}


@pytest.mark.parametrize("time", [("2025-01-01", None), (None, "2025-01-02")])
def test_resolve_selected_passes_time_partial_raises(time):
    filters = {"time": time}
    with pytest.raises(ValueError, match="needs both --start and --end"):
        ac_core._resolve_selected_passes(filters)


def test_resolve_selected_passes_success(mocker):
    passes = pd.DataFrame({"cycle_number": [2, 3], "pass_number": [2, 3]})
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.selected_passes",
        return_value=passes,
    )

    filters = {"time": ("2025-01-01", "2025-01-02")}
    resolved = ac_core._resolve_selected_passes(filters)

    assert resolved == ("MOCK_MISSION", passes)
    assert "time" not in filters


def test_resolve_selected_passes_no_pass_found(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.selected_passes",
        side_effect=ac_core.altisearch.NoPassFoundError("nothing found"),
    )

    filters = {"cycle_number": [2], "time": ("2025-01-01", "2025-01-02")}
    assert ac_core._resolve_selected_passes(filters) is None


@pytest.mark.parametrize(
    "explicit, resolved, expected",
    [
        (5, [5, 6, 7], [5]),
        ([5, 6], [5, 6, 7], [5, 6]),
        ([5, 99], [5, 6, 7], [5]),
        (99, [5, 6, 7], []),
    ],
)
def test_intersect(explicit, resolved, expected):
    assert ac_core._intersect(explicit, resolved) == expected


def test_apply_selected_passes_no_explicit_filters():
    passes = pd.DataFrame({"cycle_number": [2, 3], "pass_number": [2, 3]})
    filters = {}
    assert ac_core._apply_selected_passes(filters, passes) is True
    assert filters == {"cycle_number": [2, 3], "pass_number": [2, 3]}


def test_apply_selected_passes_narrows_to_intersection():
    passes = pd.DataFrame({"cycle_number": [2, 2, 3, 3], "pass_number": [2, 22, 3, 33]})
    filters = {"cycle_number": [2, 3], "pass_number": 22}
    assert ac_core._apply_selected_passes(filters, passes) is True
    assert filters == {"cycle_number": [2, 3], "pass_number": [22]}


def test_apply_selected_passes_inconsistent_cycle_returns_false():
    passes = pd.DataFrame({"cycle_number": [2, 3], "pass_number": [2, 3]})
    filters = {"cycle_number": 99}
    assert ac_core._apply_selected_passes(filters, passes) is False
    # Unchanged: no partial merge happened.
    assert filters == {"cycle_number": 99}


def test_apply_selected_passes_inconsistent_pass_returns_false():
    passes = pd.DataFrame({"cycle_number": [2, 3], "pass_number": [2, 3]})
    filters = {"pass_number": 99}
    assert ac_core._apply_selected_passes(filters, passes) is False
    assert filters == {"pass_number": 99}


# ---------------------------------------------------------------------------
# get()/subset() end-to-end with a `time` filter
# ---------------------------------------------------------------------------


ALL_FILES = [
    "dataset_02_02.nc",
    "dataset_02_22.nc",
    "dataset_03_03.nc",
    "dataset_03_33.nc",
]


@pytest.fixture
def mock_full_period(mocker):
    """Time resolves to every (cycle, pass) present in the mock catalog."""
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    return mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.selected_passes",
        return_value=pd.DataFrame(
            {"cycle_number": [2, 2, 3, 3], "pass_number": [2, 22, 3, 33]}
        ),
    )


@pytest.mark.parametrize("command", [get, subset])
def test_time_filter_matches_no_pass_returns_empty(tmp_path, mocker, command):
    # Covers `if resolved is None: return []` in get()/subset(): time given,
    # but no pass at all exists in that period (mission-wide).
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.selected_passes",
        side_effect=ac_core.altisearch.NoPassFoundError("nothing found"),
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-01-01", "2025-01-02"),
        )
    assert local_files == []


@pytest.mark.parametrize("command", [get, subset])
def test_time_filter_alone_resolves_to_all_matching_files(
    tmp_path, mock_full_period, command
):
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-01-01", "2025-01-02"),
        )
    assert sorted(local_files) == sorted(str(tmp_path / f) for f in ALL_FILES)


@pytest.mark.parametrize("command", [get, subset])
def test_time_and_explicit_filters_narrow_down(tmp_path, mock_full_period, command):
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            cycle_number=2,
            pass_number=22,
            time=("2025-01-01", "2025-01-02"),
        )
    assert local_files == [str(tmp_path / "dataset_02_22.nc")]


@pytest.mark.parametrize("command", [get, subset])
def test_time_and_explicit_filters_no_intersection_returns_empty(
    tmp_path, mock_full_period, command
):
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            cycle_number=99,
            time=("2025-01-01", "2025-01-02"),
        )
    assert local_files == []


@pytest.mark.parametrize("command", [get, subset])
def test_time_none_and_pass_filters(tmp_path, command):
    # Regression: the CLI always passes time=(start, end), which is
    # (None, None) when --start/--end are omitted.
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            cycle_number=2,
            time=(None, None),
        )
    assert sorted(local_files) == sorted(
        str(tmp_path / f) for f in ["dataset_02_02.nc", "dataset_02_22.nc"]
    )


def test_subset_bbox_chains_pass_passage_time(tmp_path, mock_full_period, mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.pass_passage_time",
        return_value=pd.DataFrame({"pass_number": [22, 33]}),
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = subset(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-01-01", "2025-01-02"),
            box=(0, 0, 10, 10),
        )
    assert sorted(local_files) == sorted(
        str(tmp_path / f) for f in ["dataset_02_22.nc", "dataset_03_33.nc"]
    )


def test_subset_bbox_no_intersection_returns_empty(tmp_path, mock_full_period, mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.pass_passage_time",
        return_value=pd.DataFrame({"pass_number": []}),
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = subset(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-01-01", "2025-01-02"),
            box=(0, 0, 10, 10),
        )
    assert local_files == []
