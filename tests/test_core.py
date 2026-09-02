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


def test_subset_parameters_passed(tmp_path, mocker):
    # box alone now resolves via Altimetry Search too (see
    # test_box_alone_resolves_via_default_mission); mock it here so the
    # request actually reaches subset_one_file with the parameters below.
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
def test_resolve_selected_passes_time_none_is_no_time_filter(time):
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


def test_resolve_filters_skips_altisearch_for_non_queryable_product(mocker):
    mock_selected_passes = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.selected_passes"
    )
    filters = {"cycle_number": [2], "time": ("2025-01-01", "2025-01-02")}

    assert ac_core._resolve_filters("sample_product_e", filters, box=None) is True

    mock_selected_passes.assert_not_called()
    # Untouched: Altimetry Search was never consulted, time stays as-is.
    assert filters == {"cycle_number": [2], "time": ("2025-01-01", "2025-01-02")}


@pytest.mark.parametrize("command", [get, subset])
def test_non_queryable_product_bypasses_altisearch(tmp_path, mocker, command):
    # sample_product_a is queryable by pass; force it non-queryable here to
    # exercise get()/subset() end-to-end without a dedicated mock catalog
    # for a gridded product.
    mocker.patch(
        "altimetry_downloader_aviso.core._product_queryable_by_pass",
        return_value=False,
    )
    mock_selected_passes = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.selected_passes"
    )
    with patch("altimetry_downloader_aviso.subset.subset_one_file", return_value=True):
        local_files = command(
            product_short_name="sample_product_a",
            output_dir=tmp_path,
            time=("2025-04-04", "2025-04-05"),
        )
    mock_selected_passes.assert_not_called()
    # time passed straight through to fcollections, untouched: same result
    # as no filter at all against this mock catalog.
    assert sorted(local_files) == sorted(str(tmp_path / f) for f in ALL_FILES)


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
def test_time_none_none_keeps_explicit_cycle_pass_filters(tmp_path, command):
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


# ---------------------------------------------------------------------------
# _resolve_box_only / box without time
# ---------------------------------------------------------------------------


def test_resolve_box_only_narrows_pass_number(mocker, caplog):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[225],
    )
    filters = {"cycle_number": 1, "pass_number": [223, 225, 236]}
    with caplog.at_level("INFO", logger="altimetry_downloader_aviso.core"):
        result = ac_core._resolve_box_only(filters, (0, 0, 10, 10), 1, [223, 225, 236])
    assert result is True
    assert filters["pass_number"] == [225]
    assert "excludes pass_number=[223, 236]" in caplog.text


def test_resolve_box_only_no_intersection_returns_false(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[],
    )
    filters = {"cycle_number": 1, "pass_number": [223, 225]}
    assert ac_core._resolve_box_only(filters, (0, 0, 10, 10), 1, [223, 225]) is False


def test_resolve_box_only_cycle_spanning_missions_raises(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        side_effect=lambda c: "SCIENCE" if c < 400 else "CALVAL",
    )
    filters = {"cycle_number": [1, 500], "pass_number": [223]}
    with pytest.raises(ValueError, match="spans more than one mission phase"):
        ac_core._resolve_box_only(filters, (0, 0, 10, 10), [1, 500], [223])


def test_resolve_box_only_without_pass_number_tests_every_pass(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle",
        return_value="MOCK_MISSION",
    )
    mock_passes_crossing_polygon = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[2],
    )
    filters = {"cycle_number": 1}
    result = ac_core._resolve_box_only(filters, (0, 0, 10, 10), 1, None)
    assert result is True
    assert filters["pass_number"] == [2]
    mock_passes_crossing_polygon.assert_called_once_with(
        "MOCK_MISSION", (0, 0, 10, 10), None
    )


def test_resolve_box_only_without_cycle_number_uses_default_mission(mocker):
    mock_mission_for_cycle = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.mission_for_cycle"
    )
    mock_passes_crossing_polygon = mocker.patch(
        "altimetry_downloader_aviso.core.altisearch.passes_crossing_polygon",
        return_value=[12, 45],
    )
    filters = {}
    result = ac_core._resolve_box_only(filters, (0, 0, 10, 10), None, None)
    assert result is True
    assert filters["pass_number"] == [12, 45]
    mock_mission_for_cycle.assert_not_called()
    mock_passes_crossing_polygon.assert_called_once_with(
        ac_core.altisearch.DEFAULT_MISSION, (0, 0, 10, 10), None
    )


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
    # Altimetry Search too now, defaulting to the Science-phase mission.
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
