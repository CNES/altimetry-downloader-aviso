import getpass
import logging
import netrc
import os
import sys
import warnings
from pathlib import Path

NETRC_PATH = Path.home() / ".altimetry" / ".netrc"
NCRC_PATH = Path.home() / ".altimetry" / ".ncrc"
_NCRC_KEY = "HTTP.NETRC"
_NCRC_SEP = "="

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Exception raised when a problem happened when reading credentials."""


def ensure_credentials(host: str):
    """Ensure credentials are present in a .netrc, and prompt otherwise.

    Parameters
    ----------
    host: str
        host for which credentials are needed

    Returns
    -------
        (username, password) tuple

    Raises
    ------
    AuthenticationError
        In case an exception happens when reading credentials
    """
    _setup_auth_env()
    _validate_ncrc_file()
    creds = _get_credentials(host)
    if creds:
        return creds

    return _prompt_and_save_credentials(host)


def _setup_auth_env():
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


def _get_credentials(host: str):
    """Get credentials stored in .netrc."""
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
    """Prompt and save credentials."""
    logging.info("Credentials required for %s", host)
    login = input("Username : ")
    password = getpass.getpass("Password : ")

    with open(NETRC_PATH, "a") as f:
        f.write(f"\nmachine {host} login {login} password {password}\n")

    os.chmod(NETRC_PATH, 0o600)

    return login, password
