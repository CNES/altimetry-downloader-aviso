import logging

import numpy as np
import xarray as xr

logger = logging.getLogger(__name__)


def subset_multiple_files(
    dap2_urls: list[str],
    output_files: list[str],
    box: tuple[float, float, float, float] | None = None,
    selected_variables: list[str] | None = None,
):
    downloaded = []
    for dap2_url, output_file in zip(dap2_urls, output_files):
        try:
            subset_one_file(dap2_url, output_file, box, selected_variables)
            downloaded.append(output_file)
        except IndexError:
            logger.debug("No data in area, skipping %s", dap2_url)

    return downloaded


def subset_one_file(
    dap2_url: str,
    output_file: str,
    box: tuple[float, float, float, float] | None = None,
    selected_variables: list[str] | None = None,
):

    ds = xr.open_dataset(dap2_url, engine="netcdf4")

    if box is not None:
        slice_num_lines = _get_indexes_fast(ds, (box[0], box[2]), (box[1], box[3]))
        ds = ds.isel(num_lines=slice_num_lines)

    if selected_variables is not None:
        ds = ds[selected_variables]

    logger.debug("Downloading %s (%.2f MiB)", dap2_url, ds.nbytes / 1024**2)
    ds.to_netcdf(output_file, mode="w")


def _get_indexes_fast(
    ds: xr.Dataset, lon_range: tuple[float, float], lat_range: tuple[float, float]
) -> slice:
    left_latitudes = ds.isel(num_pixels=0)["latitude"].values
    right_latitudes = ds.isel(num_pixels=-1)["latitude"].values

    lines = (lat_range[0] <= left_latitudes) & (left_latitudes <= lat_range[1]) | (
        lat_range[0] <= right_latitudes
    ) & (right_latitudes <= lat_range[1])

    num_lines_min, num_lines_max = np.where(lines)[0][[0, -1]]

    longitudes = ds.isel(num_lines=slice(num_lines_min, num_lines_max + 1))[
        "longitude"
    ].values
    mask_left = (longitudes >= lon_range[0]) & (longitudes <= lon_range[1])
    mask = mask_left.any(axis=1)

    return slice(
        num_lines_min + np.where(mask)[0][0], num_lines_min + np.where(mask)[0][-1] + 1
    )
