import logging
import os
import pathlib as pl
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, auto
from typing import Generator, Iterable

import requests

logger = logging.getLogger(__name__)

TDS_HOST = "tds-odatis.aviso.altimetry.fr"


class Protocol(Enum):
    """Protocols supported by the TDS server."""

    HTTP = auto()
    """HTTP request of a granule.

    Used to download the entire file.
    """
    DAP2 = auto()
    """OpenDAP protocol.

    Used to trigger server subsetting of the granule.
    """


def http_single_download(
    url: str,
    output_dir: str | pl.Path,
    overwrite: bool = False,
) -> str:
    """Download a granule from AVISO's Thredds Data Server using HTTPS
    protocol.

    Parameters
    ----------
    url: str
        the url to download
    output_dir: str | pl.Path
        existing directory to store the downloaded file
    overwrite: bool
        whether to overwrite the file if it already exists

    Returns
    -------
        the local path to the downloaded file
    """
    logger.debug("Downloading %s...", url)

    filename = os.path.basename(url)
    output_dir = pl.Path(output_dir) if isinstance(output_dir, str) else output_dir
    local_filepath = output_dir / filename

    if not overwrite and local_filepath.exists():
        logger.debug("File %s already exist. Ignore download.", local_filepath)
        return str(local_filepath)

    # requests will authenticate using the netrc file defined in the NETRC environment
    # variable
    logger.debug("NETRC environment variable: %s", os.environ["NETRC"])
    response = requests.get(url)
    response.raise_for_status()

    with open(local_filepath, "wb") as f:
        f.write(response.content)

    logger.info("File %s downloaded.", local_filepath)

    return str(local_filepath)


def http_single_download_with_retries(
    url: str,
    output_dir: str | pl.Path,
    retries: int = 3,
    backoff: float = 1.0,
    overwrite: bool = False,
) -> str:
    """Download a granule from AVISO's Thredds Data Server using HTTPS
    protocol. Retries if the download fails.

    Parameters
    ----------
    url: str
        the url to download
    output_dir: str | pl.Path
        existing directory to store the downloaded file
    retries: int
        number of retries
    backoff: float
        waiting time between two tries. Increases exponentially
    overwrite: bool
        whether to overwrite the file if it already exists

    Returns
    -------
        the local path to the downloaded file

    Raises
    ------
    RequestException
        In case an exception happens when requesting the file on the server
    """
    last_exception = None

    for attempt in range(1, 1 + 1):
        try:
            return http_single_download(url, output_dir, overwrite)

        except requests.RequestException as e:
            logger.debug("Attempt %d failed for %s: %s", attempt, url, e)

            last_exception = e
            if attempt < retries:
                time.sleep(backoff * (2 ** (attempt - 1)))

    raise last_exception


def _download_one(
    url: str,
    output_dir: str | pl.Path,
    retries: int = 3,
    backoff: float = 1.0,
    overwrite: bool = False,
):
    try:
        return http_single_download_with_retries(
            url, output_dir, retries, backoff, overwrite
        )
    except requests.RequestException as e:
        msg = f"Failed to download {url}. An error happened: {e}"
        warnings.warn(msg)
    return


def http_bulk_download(
    urls: list[str],
    output_dir: str | pl.Path,
    retries: int = 3,
    backoff: float = 1.0,
    overwrite: bool = False,
) -> Generator[str, None, None]:
    """Loop on a list of urls to download each granule from AVISO's Thredds
    Data Server using HTTPS protocol. Each download as retries if it fails.

    Parameters
    ----------
    urls: list[str]
        the urls to download
    output_dir: str | pl.Path
        a directory to store the downloaded file (create it if doesn't exist)
    retries: int
        number of retries
    backoff: float
        waiting time between two tries. Increases exponentially
    overwrite: bool
        whether to overwrite the file if it already exists

    Returns
    -------
        An iterator over the downloaded paths, one for each download that have succeeded
    """
    output_dir = pl.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for url in urls:
        file = _download_one(url, output_dir, retries, backoff, overwrite)
        if file:
            yield file


def http_bulk_download_parallel(
    urls: Iterable[str],
    output_dir: str | pl.Path,
    retries: int = 3,
    backoff: float = 1.0,
    max_workers: int = 4,
    overwrite: bool = False,
) -> Generator[str, None, None]:
    """Parallel download of granules from AVISO's Thredds Data Server using
    HTTPS protocol.

    Parameters
    ----------
    urls: list[str]
        the urls to download
    output_dir: str | pl.Path
        existing directory to store the downloaded file
    retries: int
        number of retries
    backoff: float
        waiting time between two tries. Increases exponentially
    max_workers: int
        Maximum number of workers
    overwrite: bool
        whether to overwrite the file if it already exists

    Returns
    -------
        An iterator over the downloaded paths, one for each download that have succeeded
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                _download_one,
                url,
                output_dir,
                retries,
                backoff,
                overwrite,
            ): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            result = future.result()
            if result:
                yield result
