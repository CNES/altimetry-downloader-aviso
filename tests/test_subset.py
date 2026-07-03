from __future__ import annotations

import typing as tp
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

from altimetry_downloader_aviso.subset import subset_multiple_files, subset_one_file

if tp.TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "dataset, context",
    [
        (xr.Dataset(), pytest.raises(ValueError, match="num_pixels")),
        (
            xr.Dataset(data_vars=dict(latitude=("num_pixels", np.empty(2)))),
            pytest.raises(ValueError, match="num_lines"),
        ),
        (
            xr.Dataset(
                data_vars=dict(
                    longitude=(("num_lines", "num_pixels"), np.empty((3, 3)))
                )
            ),
            pytest.raises(ValueError, match="latitude"),
        ),
        (
            xr.Dataset(
                data_vars=dict(latitude=(("num_lines", "num_pixels"), np.empty((3, 3))))
            ),
            pytest.raises(ValueError, match="longitude"),
        ),
    ],
    ids=[
        "missing_num_lines_dim",
        "missing_num_pixels_dim",
        "missing_latitude_var",
        "missing_longitude_var",
    ],
)
def test_subset_one_file_bad_dataset(
    tmp_path_factory: pytest.TempPathFactory, dataset: xr.Dataset, context
):
    nc_file_in = tmp_path_factory.mktemp("files") / "file_in.nc"
    nc_file_out = tmp_path_factory.mktemp("files") / "file_out.nc"

    dataset.to_netcdf(nc_file_in)

    with context:
        subset_one_file(
            nc_file_in, nc_file_out, box=(-180, -90, 180, 90), selected_variables=None
        )


@pytest.fixture(scope="session", params=[0, 1, 2])
def dap_dataset(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> Path:
    nc_file_in = tmp_path_factory.mktemp("files") / "file_in.nc"

    num_pixels = 10

    latitudes = np.reshape(
        np.repeat(np.concatenate([np.arange(-10, 11), np.arange(20, 41)]), num_pixels),
        (42, num_pixels),
    )
    longitudes = np.reshape(
        np.repeat(
            np.concatenate([np.arange(-10, 11), np.arange(170, 191)]), num_pixels
        ),
        (42, num_pixels),
    )
    if request.param == 1:
        longitudes[longitudes < 0] += 360
    elif request.param == 2:
        longitudes[longitudes > 180] -= 360

    ds = xr.Dataset(
        coords=dict(
            latitude=(("num_lines", "num_pixels"), latitudes),
            longitude=(("num_lines", "num_pixels"), longitudes),
        ),
        data_vars=dict(
            varA=(("num_lines", "num_pixels"), np.ones_like(latitudes)),
            varB=(("num_lines", "num_pixels"), np.ones_like(latitudes)),
        ),
    )
    ds.to_netcdf(nc_file_in)
    return nc_file_in


@pytest.mark.parametrize(
    "box, selection, selected_variables, has_data",
    [
        ((-180, -90, 180, 90), slice(0, None), None, True),
        ((0, -90, 360, 90), slice(0, None), None, True),
        ((-180, -90, 180, 90), slice(0, None), ["varA"], True),
        ((-5, -90, 5, 90), slice(5, 16), None, True),
        ((178, -90, 182, 90), slice(29, 34), None, True),
        ((-180, -4, 180, 6), slice(6, 17), None, True),
        ((-5, -4, 5, 6), slice(6, 16), None, True),
        ((60, 60, 70, 70), slice(0, 0), None, False),
    ],
    ids=[
        "no_sel",
        "no_sel_360",
        "sel_variables",
        "sel_longitude",
        "sel_longitude_360",
        "sel_latitude",
        "sel_box",
        "out_of_box",
    ],
)
def test_subset_one_file(
    tmp_path_factory: pytest.TempPathFactory,
    dap_dataset: Path,
    box: tuple[float, float, float, float],
    selection: slice,
    selected_variables: list[str] | None,
    has_data: bool,
):
    nc_file_out = tmp_path_factory.mktemp("files") / "file_out.nc"

    has_data_actual = subset_one_file(
        dap_dataset,
        nc_file_out,
        box=box,
        selected_variables=selected_variables,
        compress=False,
    )
    assert has_data_actual is has_data

    if has_data:
        ds = xr.open_dataset(dap_dataset)
        selected_variables = (
            ["varA", "varB"] if selected_variables is None else selected_variables
        )
        subset = ds.isel(num_lines=selection)[selected_variables]
        actual = xr.open_dataset(nc_file_out)

        # Longitude and latitude are coordinates in L3_LR_SSH datasets, and should
        # always be selected
        assert "longitude" in subset.coords
        assert "latitude" in subset.coords

        xr.testing.assert_equal(subset, actual)


def test_subset_one_file_compress(
    tmp_path_factory: pytest.TempPathFactory,
    dap_dataset: Path,
):
    nc_file_out = tmp_path_factory.mktemp("files") / "file_out.nc"

    subset_one_file(dap_dataset, nc_file_out, compress=False)
    assert nc_file_out.stat().st_size == dap_dataset.stat().st_size

    # Compression will actually have bad performance for a dataset too small. Need about
    # 10 pixels for compression to show storage improvements.
    subset_one_file(dap_dataset, nc_file_out, compress=True)
    assert nc_file_out.stat().st_size < dap_dataset.stat().st_size


def test_subset_multiple_files():
    def subset_mock(url, *args, **kwargs):
        if url == "a":
            return False
        elif url == "b":
            raise Exception("b download error")
        else:
            return True

    with (
        patch("altimetry_downloader_aviso.subset.subset_one_file", wraps=subset_mock),
        pytest.warns(UserWarning, match="Subsetting b failed."),
    ):
        downloaded = subset_multiple_files(
            ["a", "b", "c"], ["a.nc", "b.nc", "c.nc"], backoff=0
        )

    assert downloaded == ["c.nc"]
