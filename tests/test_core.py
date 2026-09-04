import os
from datetime import datetime
from unittest.mock import patch

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
def test_get_subset(tmp_path, short_name, filters, files, command, mocker):
    # cycle_number alone (no time) resolves a mission via mission_for_cycle;
    # pass_number alone touches no filter resolution at all (no time, no
    # box). Mock defensively so this generic case doesn't depend on real
    # Altimetry Search data.
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name=short_name, output_dir=tmp_path, **filters
        )

    assert local_files == [str(tmp_path / f) for f in files]


def test_subset_parameters_passed(tmp_path, mocker):
    # box alone resolves via Altimetry Search too (default mission, since
    # neither time nor cycle_number is given).
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[2, 22, 3, 33],
    )
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
def test_get_subset_overwrite(tmp_path, command, mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
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
def test_get_subset_bad_filters(tmp_path, short_name, filters, command, mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    assert command(short_name, tmp_path, **filters) == []


# ---------------------------------------------------------------------------
# _resolve_cycle_pass_filters
# ---------------------------------------------------------------------------


def test_resolve_cycle_pass_filters_skips_altisearch_for_non_queryable_product(mocker):
    mock_mission_for = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for"
    )
    filters = {"cycle_number": [2], "time": ("2025-01-01", "2025-01-02")}

    assert (
        ac_core._resolve_cycle_pass_filters("sample_product_e", filters, box=None)
        is True
    )

    mock_mission_for.assert_not_called()
    assert filters == {"cycle_number": [2], "time": ("2025-01-01", "2025-01-02")}


def test_resolve_cycle_pass_filters_time_alone(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.get_selected_cycles",
        return_value=[2, 3],
    )
    filters = {"time": ("2025-01-01", "2025-01-02")}

    assert (
        ac_core._resolve_cycle_pass_filters("sample_product_a", filters, box=None)
        is True
    )
    assert filters == {"time": ("2025-01-01", "2025-01-02"), "cycle_number": [2, 3]}


def test_resolve_cycle_pass_filters_time_and_cycle_number_intersect(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.get_selected_cycles",
        return_value=[2, 3],
    )
    filters = {"time": ("2025-01-01", "2025-01-02"), "cycle_number": 2}

    assert (
        ac_core._resolve_cycle_pass_filters("sample_product_a", filters, box=None)
        is True
    )
    assert filters["cycle_number"] == [2]


def test_resolve_cycle_pass_filters_time_and_cycle_number_no_intersection(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.get_selected_cycles",
        return_value=[2, 3],
    )
    filters = {"time": ("2025-01-01", "2025-01-02"), "cycle_number": 99}

    assert (
        ac_core._resolve_cycle_pass_filters("sample_product_a", filters, box=None)
        is False
    )


def test_resolve_cycle_pass_filters_time_matches_no_pass(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.get_selected_cycles",
        side_effect=ac_core.altisearch.NoPassFoundError("nothing found"),
    )
    filters = {"time": ("2025-01-01", "2025-01-02")}

    assert (
        ac_core._resolve_cycle_pass_filters("sample_product_a", filters, box=None)
        is False
    )


def test_resolve_cycle_pass_filters_cycle_number_alone_uses_mission_for_cycle(mocker):
    mock_mission_for = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for"
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    filters = {"cycle_number": 2}

    assert (
        ac_core._resolve_cycle_pass_filters("sample_product_a", filters, box=None)
        is True
    )
    mock_mission_for.assert_not_called()
    assert filters["cycle_number"] == [2]


def test_resolve_cycle_pass_filters_cycle_number_spanning_missions_raises(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        side_effect=lambda c: "SCIENCE" if c < 400 else "CALVAL",
    )
    filters = {"cycle_number": [1, 500]}

    with pytest.raises(ValueError, match="spans more than one mission phase"):
        ac_core._resolve_cycle_pass_filters("sample_product_a", filters, box=None)


def test_resolve_cycle_pass_filters_nothing_defaults_to_default_mission(mocker, caplog):
    mock_mission_for_cycle = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle"
    )
    mock_passes_crossing_polygon = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[12, 45],
    )
    filters = {}

    with caplog.at_level("WARNING", logger="altimetry_downloader_aviso.core"):
        result = ac_core._resolve_cycle_pass_filters(
            "sample_product_a", filters, box=(0, 0, 10, 10)
        )

    assert result is True
    mock_mission_for_cycle.assert_not_called()
    mock_passes_crossing_polygon.assert_called_once_with(
        ac_core.altisearch.DEFAULT_MISSION, (0, 0, 10, 10), None
    )
    assert filters["pass_number"] == [12, 45]
    assert "cycle_number" not in filters
    assert "assuming the Science phase" in caplog.text
    assert "query-help" in caplog.text
    assert "filter_infos" in caplog.text


def test_resolve_cycle_pass_filters_box_narrows_pass_number(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[22],
    )
    filters = {"cycle_number": 2, "pass_number": [2, 22]}

    assert (
        ac_core._resolve_cycle_pass_filters(
            "sample_product_a", filters, box=(0, 0, 10, 10)
        )
        is True
    )
    assert filters["pass_number"] == [22]


def test_resolve_cycle_pass_filters_box_no_crossing_returns_false(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[],
    )
    filters = {"cycle_number": 2}

    assert (
        ac_core._resolve_cycle_pass_filters(
            "sample_product_a", filters, box=(0, 0, 10, 10)
        )
        is False
    )


def test_resolve_cycle_pass_filters_time_without_box_leaves_pass_number_untouched(
    mocker,
):
    # Without box, pass_number is never checked against Altimetry Search,
    # even when time is given -- only cycle_number is.
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.get_selected_cycles",
        return_value=[2, 3],
    )
    mock_passes_crossing_polygon = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon"
    )
    filters = {"time": ("2025-01-01", "2025-01-02"), "pass_number": 999}

    assert (
        ac_core._resolve_cycle_pass_filters("sample_product_a", filters, box=None)
        is True
    )
    mock_passes_crossing_polygon.assert_not_called()
    assert filters["pass_number"] == 999


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
    """Time resolves to every cycle present in the mock catalog."""
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    return mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.get_selected_cycles",
        return_value=[2, 3],
    )


@pytest.mark.parametrize("command", [get, subset])
def test_non_queryable_product_bypasses_altisearch(tmp_path, mocker, command):
    # sample_product_a is queryable by pass; force it non-queryable here to
    # exercise get()/subset() end-to-end without a dedicated mock catalog
    # for a gridded product.
    mocker.patch(
        "altimetry_downloader_aviso.core._product_queryable_by_pass",
        return_value=False,
    )
    mock_mission_for = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for"
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-04-04", "2025-04-05"),
        )
    mock_mission_for.assert_not_called()
    # time passed straight through to fcollections, untouched: same result
    # as no filter at all against this mock catalog.
    assert sorted(local_files) == sorted(str(tmp_path / f) for f in ALL_FILES)


@pytest.mark.parametrize("command", [get, subset])
def test_time_filter_matches_no_pass_returns_empty(tmp_path, mocker, command):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.get_selected_cycles",
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
def test_time_none_keeps_explicit_cycle_pass_filters(tmp_path, command, mocker):
    # Direct API callers must pass time=None (not (None, None), which is a
    # CLI-only quirk now normalized before ever reaching get()/subset()).
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            cycle_number=2,
            time=None,
        )
    assert sorted(local_files) == sorted(
        str(tmp_path / f) for f in ["dataset_02_02.nc", "dataset_02_22.nc"]
    )


@pytest.mark.parametrize("command", [get, subset])
def test_bbox_chains_passes_crossing_polygon(
    tmp_path, mock_full_period, mocker, command
):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[22, 33],
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-01-01", "2025-01-02"),
            box=(0, 0, 10, 10),
        )
    assert sorted(local_files) == sorted(
        str(tmp_path / f) for f in ["dataset_02_22.nc", "dataset_03_33.nc"]
    )


@pytest.mark.parametrize("command", [get, subset])
def test_bbox_no_intersection_returns_empty(
    tmp_path, mock_full_period, mocker, command
):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[],
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-01-01", "2025-01-02"),
            box=(0, 0, 10, 10),
        )
    assert local_files == []


@pytest.mark.parametrize("command", [get, subset])
def test_box_with_cycle_pass_no_time_narrows(tmp_path, mocker, command):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[22],
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            cycle_number=2,
            pass_number=[2, 22],
            box=(0, 0, 10, 10),
        )
    assert local_files == [str(tmp_path / "dataset_02_22.nc")]


@pytest.mark.parametrize("command", [get, subset])
def test_box_with_cycle_number_only_resolves_all_passes(tmp_path, mocker, command):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[22],
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            cycle_number=2,
            box=(0, 0, 10, 10),
        )
    assert local_files == [str(tmp_path / "dataset_02_22.nc")]


@pytest.mark.parametrize("command", [get, subset])
def test_box_alone_resolves_via_default_mission(tmp_path, mocker, command):
    # box alone (no time, no cycle_number, no pass_number) resolves via
    # Altimetry Search too, defaulting to the Science-phase mission.
    mock_mission_for_cycle = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle"
    )
    mock_passes_crossing_polygon = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[22, 33],
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            box=(0, 0, 10, 10),
        )
    mock_mission_for_cycle.assert_not_called()
    mock_passes_crossing_polygon.assert_called_once_with(
        ac_core.altisearch.DEFAULT_MISSION, (0, 0, 10, 10), None
    )
    assert sorted(local_files) == sorted(
        str(tmp_path / f) for f in ["dataset_02_22.nc", "dataset_03_33.nc"]
    )


# ---------------------------------------------------------------------------
# _product_queryable_by_pass
# ---------------------------------------------------------------------------


def test_gridded_product_is_not_queryable_by_pass():
    assert ac_core._product_queryable_by_pass("sample_product_e") is False


@pytest.mark.parametrize(
    "short_name",
    ["sample_product_a", "sample_product_b", "sample_product_c"],
)
def test_swath_products_are_queryable_by_pass(short_name):
    assert ac_core._product_queryable_by_pass(short_name) is True


def test_unknown_product_defaults_to_queryable_by_pass():
    assert ac_core._product_queryable_by_pass("does-not-exist") is True
