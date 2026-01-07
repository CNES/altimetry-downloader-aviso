import logging
import os
import pathlib as pl
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, Iterable

import requests

from .auth import ensure_credentials

logger = logging.getLogger(__name__)

TDS_HOST = "tds-odatis.aviso.altimetry.fr"


def http_single_download(
    url: str,
    output_dir: str | pl.Path,
    username: str = None,
    password: str = None,
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
    username: str
        username for authentication. Retrieved from .netrc file if not provided
    password: str
        password for authentication. Retrieved from .netrc file if not provided
    overwrite: bool
        whether to overwrite the file if it already exists

    Returns
    -------
        the local path to the downloaded file
    """
    if username is None or password is None:
        (username, password) = ensure_credentials(TDS_HOST)

    logger.debug("Downloading %s...", url)

    filename = os.path.basename(url)
    output_dir = pl.Path(output_dir) if isinstance(output_dir, str) else output_dir
    local_filepath = output_dir / filename

    if not overwrite and local_filepath.exists():
        logger.debug("File %s already exist. Ignore download.", local_filepath)
        return str(local_filepath)

    response = requests.get(url, auth=(username, password))
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
    username: str = None,
    password: str = None,
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
    username: str
        username for authentication. Retrieved from .netrc file if not provided
    password: str
        password for authentication. Retrieved from .netrc file if not provided
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
    if username is None or password is None:
        (username, password) = ensure_credentials(TDS_HOST)

    last_exception = None

    for attempt in range(1, retries + 1):
        try:
            return http_single_download(url, output_dir, username, password, overwrite)

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
    username: str = None,
    password: str = None,
    overwrite: bool = False,
):
    try:
        return http_single_download_with_retries(
            url, output_dir, retries, backoff, username, password, overwrite
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
    username: str = None,
    password: str = None,
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
    username: str
        username for authentication. Retrieved from .netrc file if not provided
    password: str
        password for authentication. Retrieved from .netrc file if not provided
    overwrite: bool
        whether to overwrite the file if it already exists

    Returns
    -------
        An iterator over the downloaded paths, one for each download that have succeeded
    """
    if username is None or password is None:
        (username, password) = ensure_credentials(TDS_HOST)

    output_dir = pl.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for url in urls:
        file = _download_one(
            url, output_dir, retries, backoff, username, password, overwrite
        )
        if file:
            yield file


def http_bulk_download_parallel(
    urls: Iterable[str],
    output_dir: str | pl.Path,
    retries: int = 3,
    backoff: float = 1.0,
    max_workers: int = 4,
    username: str = None,
    password: str = None,
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
    username: str
        username for authentication. Retrieved from .netrc file if not provided
    password: str
        password for authentication. Retrieved from .netrc file if not provided
    overwrite: bool
        whether to overwrite the file if it already exists

    Returns
    -------
        An iterator over the downloaded paths, one for each download that have succeeded
    """
    if username is None or password is None:
        (username, password) = ensure_credentials(TDS_HOST)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                _download_one,
                url,
                output_dir,
                retries,
                backoff,
                username,
                password,
                overwrite,
            ): url
            for url in urls
        }

        for future in as_completed(future_to_url):
            result = future.result()
            if result:
                yield result
