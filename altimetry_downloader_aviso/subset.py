"""Subsetting utilities.

Will handle robust subsetting via DAP2 for SWOT products under the
swath. Subsetting can help reduce the bandwidth usage by reducing the
downloaded swaths on the server side.

The requested data is uncompressed by the server before being cropped
and sent over the network. xarray uses the "Accept-Encoding: gzip, zstd,
deflate" header, so it is up to the server to apply a compression over
the HTTP layer (the binary stream via OpenDAP will NOT be compressed
using the original Netcdf compressors). However the server is
configured, selecting a subset of variables and an area of interest
should still be advantageous and reduce the bandwidth usage.

In addition, subsetting the Netcdf can only be done by giving slices
over dimensions. Because the swath grid is NOT in a zonal/meridional
frame, we must convert the requested box in slices using the
longitude/latitude coordinates. SWOT_L3_LR_SSH_Unsmoothed coordinates
can be big in size (num_lines, num_pixels) ~= (80000, 519), so we use
the fact "1 granule = 1 half orbit" and "latitudes are monotoneous in 1
half orbit" to setup an efficient algorithm for geographical selection
(efficient = minimizing the slices of the requested coordinates).
"""

import logging
import time
import warnings

import numpy as np
import xarray as xr

logger = logging.getLogger(__name__)


def subset_multiple_files(
    dap2_urls: list[str],
    output_files: list[str],
    box: tuple[float, float, float, float] | None = None,
    selected_variables: list[str] | None = None,
    retries: int = 3,
    backoff: float = 1.0,
) -> list[str]:
    """Subset multiple files via the open dap protocol.

    This method only supports subsetting swath datasets. The data should be organized in
    a (num_lines, num_pixels) grid, and should contain the (latitude, longitude)
    geographical coordinates.

    If output files already exist, they will be overwritten.

    Parameters
    ----------
    dap2_urls
        DAP2 URLs of the granules to subset.
    output_files
        Files to write the subsets to.
    selected_variables
        List of variables to select.
    box
        Selection box (lon_min, lat_min, lon_max, lat_max) in degrees. Longitude range
        can be in either [0, 360[ or [-180, 180[ convention. lon_min must be inferior to
        lon_max (the convention must be changed to verify this constraint).
    retries
        number of retries
    backoff
        waiting time between two tries. Increases exponentially.

    Warns
    -----
    UserWarning
        If a granule cannot be subsetted.

    Returns
    -------
    list[str]
        The subset of output_files that actually have data for the selection. Granules
        that could not be subsetted will also be removed from the results.
    """
    downloaded = []
    for dap2_url, output_file in zip(dap2_urls, output_files):
        all_attempts_failed = True
        for attempt in range(1, retries + 1):
            try:
                has_data = subset_one_file(
                    dap2_url, output_file, box, selected_variables
                )
                if has_data:
                    downloaded.append(output_file)
                all_attempts_failed = False
                break
            except Exception as e:
                logger.info("Attempt %d/%d failed for %s", attempt, retries, dap2_url)
                logger.exception(e)

                if attempt < retries:
                    time.sleep(backoff * (2 ** (attempt - 1)))

        if all_attempts_failed:
            msg = f"Subsetting {dap2_url} failed."
            warnings.warn(msg)

    return downloaded


def subset_one_file(
    dap2_url: str,
    output_file: str,
    box: tuple[float, float, float, float] | None = None,
    selected_variables: list[str] | None = None,
    compress: bool = True,
) -> bool:
    """Subset one file via the OpenDAP protocol.

    This method only supports subsetting swath datasets. The data should be organized in
    a (num_lines, num_pixels) grid, and should contain the (latitude, longitude)
    geographical coordinates.

    If the file to write the subset already exists, it will be overwritten.

    Parameters
    ----------
    dap2_url
        DAP2 URL of the granule to subset.
    box
        Selection box (lon_min, lat_min, lon_max, lat_max) in degrees. Longitude range
        can be in either [0, 360[ or [-180, 180[ convention. lon_min must be inferior to
        lon_max (the convention must be changed to verify this constraint).
    output_file
        File to write the subset to.
    selected_variables
        List of variables to select.

    Returns
    -------
    bool
        True if the requested dataset contains any line inside the configured box. False
        otherwise.


    Raises
    ------
    ValueError
        If the dataset is missing the requested {'num_lines', 'num_pixels'} dimensions.
    ValueError
        If the dataset is missing the requested {'longitude', 'latitude'} variables.
    IndexError
    """

    ds = xr.open_dataset(dap2_url, engine="netcdf4")

    missing_dimensions = {"num_lines", "num_pixels"} - set(ds.sizes)
    if len(missing_dimensions) > 0:
        msg = (
            f"Dimensions {missing_dimensions} are missing from the dataset. "
            "Dimensions present in dataset: {set(ds.sizes)}"
        )
        raise ValueError(msg)

    missing_variables = {"longitude", "latitude"} - set(ds.variables)
    if len(missing_variables) > 0:
        msg = (
            f"Variables {missing_variables} are missing from the dataset. Variables"
            " present in dataset: {set(ds.variables)}"
        )
        raise ValueError(msg)

    if box is not None:
        try:
            slice_num_lines = _get_indexes_fast(ds, (box[0], box[2]), (box[1], box[3]))
        except IndexError:
            logger.debug("No data in area, skipping %s", dap2_url)
            return False
        ds = ds.isel(num_lines=slice_num_lines)

    if selected_variables is not None:
        ds = ds[selected_variables]

    if compress:
        for v in ds.variables:
            # Encoding is not transmitted over DAP. Set a default compression
            # contiguous must be set to False to allow compression
            ds[v].encoding |= {"zlib": True, "complevel": 5, "contiguous": False}

    logger.debug("Downloading %s (%.2f MiB)", dap2_url, ds.nbytes / 1024**2)
    ds.to_netcdf(output_file, mode="w")
    return True


def _get_indexes_fast(
    ds: xr.Dataset, lon_range: tuple[float, float], lat_range: tuple[float, float]
) -> slice:
    # This method is optimized to limit the queries to the OpenDAP server. It asks two
    # lines of latitudes along the 'num_lines' dimension to filter out a great number
    # of lines, before requesting the longitude over the reduced segment and finalize
    # the selection.
    left_latitudes = ds.isel(num_pixels=0)["latitude"].values
    right_latitudes = ds.isel(num_pixels=-1)["latitude"].values

    lines = (lat_range[0] <= left_latitudes) & (left_latitudes <= lat_range[1]) | (
        lat_range[0] <= right_latitudes
    ) & (right_latitudes <= lat_range[1])

    num_lines_min, num_lines_max = np.where(lines)[0][[0, -1]]

    longitudes = ds.isel(num_lines=slice(num_lines_min, num_lines_max + 1))[
        "longitude"
    ].values

    # Handle circularity
    if np.any(np.array(lon_range) > 180) and np.any(longitudes < 0):
        longitudes %= 360
    elif np.any(np.array(lon_range) < 0) and np.any(longitudes > 180):
        longitudes[longitudes > 180] -= 360

    mask_left = (longitudes >= lon_range[0]) & (longitudes <= lon_range[1])
    mask = mask_left.any(axis=1)

    return slice(
        num_lines_min + np.where(mask)[0][0], num_lines_min + np.where(mask)[0][-1] + 1
    )
