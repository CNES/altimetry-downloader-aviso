import getpass
import logging
import netrc
import os
import sys
import warnings
from pathlib import Path

#: Default path to the .netrc file for requests.
NETRC_PATH = Path.home() / ".altimetry" / ".netrc"
#: Default path to the .ncrc configuration file for netCDF4-c.
NCRC_PATH = Path.home() / ".altimetry" / ".ncrc"
#: Entry in .ncrc, pointing to the .netrc file that will be loaded by netCDF4-c.
_NCRC_KEY = "HTTP.NETRC"
#: Separator for entries in the .ncrc file.
_NCRC_SEP = "="

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Exception raised when a problem happened when reading credentials."""


def ensure_credentials(host: str):
    """Ensure authentication credentials can be found by netCDF4-c and
    requests.

    requests looks for a .netrc file in either the home directory or at the path given
    by the NETRC environment variable.

    netCDF4-c loads its .ncrc configuration file. If it finds a HTTP.NETRC entry, it
    will load the configuration from the .netrc, containing the credentials of interest.
    The .ncrc path can be given through the NCRCENV_RC, but this variable must be set
    prior importing the netCDF4 python library.

    By defaults, the credentials are setup in an isolated folder. The defaults ~/.ncrc
    and ~/.netrc will not be used. Instead, the ~/.altimetry/.netrc and
    ~/.altimetry/.ncrc will be used.

    Parameters
    ----------
    host: str
        host for which credentials are needed

    Raises
    ------
    AuthenticationError
        In case an exception happens when reading credentials
    """
    _setup_auth_env()
    _validate_ncrc_file()
    creds = _get_credentials(host)
    if not creds:
        _prompt_and_save_credentials(host)


def _setup_auth_env():
    """Setup environment variables needed by netCDF4-c and requests for
    authentication.

    netCDF4 will use the NCRCENV_RC environment variable to load the .ncrc configuration
    file. This file is expected to contain an HTTP.NETRC entry to point to the proper
    .netrc configuration file and load its contents.

    requests will use the NETRC environment variable to load the credentials from the
    .netrc configuration file.

    Warns
    -----
    UserWarning
        If netCDF4 is already imported. In that case, setting NCRCENV_RC will have no
        effect, and authentication errors may arise when opening datasets over protocols
        requiring authentication.
    """
    for name in sorted(sys.modules):
        if name.startswith("netCDF"):
            msg = (
                "netCDF4 is already loaded. Authentication configuration may not be "
                "applied"
            )
            warnings.warn(msg)

    os.environ["NCRCENV_RC"] = NCRC_PATH.as_posix()
    os.environ["NETRC"] = NETRC_PATH.as_posix()


def _validate_ncrc_file():
    """Ensure the .ncrc file points to the .netrc file containing the
    authentication.

    This method will open the .ncrc file defined in this module. If the HTTP.NETRC entry
    is already present and with the expected value - the path to the .netrc file
    defined in this module - nothing will be done.

    If the entry either does not exist, or contains a value different from the expected
    .netrc path, it will be created/updated (the .ncrc file will be modified).
    """
    NCRC_PATH.parent.mkdir(parents=True, exist_ok=True)
    NCRC_PATH.touch(exist_ok=True, mode=0o600)
    update = True

    with open(NCRC_PATH) as f:
        lines = f.readlines()

    ncrc_entry = f"{_NCRC_KEY}{_NCRC_SEP}{NETRC_PATH.as_posix()}"
    for ii, line in enumerate(lines):
        split = line.split(_NCRC_SEP)
        if split[0] == _NCRC_KEY and split[1] == NETRC_PATH.as_posix():
            logger.debug("%s entry in %s is up to date.", _NCRC_KEY, NCRC_PATH)
            update = False
            break
        elif split[0] == _NCRC_KEY:
            logger.debug("Updating existing %s entry in %s", _NCRC_KEY, NCRC_PATH)
            lines[ii] = ncrc_entry
            update = False
            break

    if update:
        logger.debug("Adding new %s entry in %s", _NCRC_KEY, NCRC_PATH)
        lines.append(ncrc_entry)
        with open(NCRC_PATH, mode="w") as f:
            f.writelines(lines)


def _get_credentials(host: str) -> tuple[str, str] | None:
    """Get credentials stored in .netrc.

    Parameters
    ----------
    host
        Host for which credentials are requested.

    Raises
    ------
    AuthenticationError
        If the .netrc file cannot be parsed properly.

    Returns
    -------
    tuple[str, str] | None
        A pair of (login, password) matching the host, or None if the host has no
        credentials.
    """
    if not NETRC_PATH.exists():
        return None

    try:
        auth_data = netrc.netrc(NETRC_PATH)
        login, _, password = auth_data.authenticators(host)
        if login and password:
            logger.debug("Retrieved credentials from .netrc")
            return login, password
    except TypeError:
        msg = f"Host {host} doesn't exist in .netrc file."
        logger.info(msg)
        return None
    except netrc.NetrcParseError as exc:
        msg = f"Syntax error in .netrc file: {exc}"
        raise AuthenticationError(msg) from exc
    except (AttributeError, ValueError) as exc:
        msg = "An error happened when authenticating Aviso client."
        raise AuthenticationError(msg) from exc


def _prompt_and_save_credentials(host: str):
    """Prompt and save credentials.

    The credentials will be saved in the .netrc file defined in this module.

    Parameters
    ----------
    host
        Host for which credentials are prompted.
    """
    logging.info("Credentials required for %s", host)
    login = input("Username : ")
    password = getpass.getpass("Password : ")

    with open(NETRC_PATH, "a") as f:
        f.write(f"\nmachine {host} login {login} password {password}\n")

    os.chmod(NETRC_PATH, 0o600)
