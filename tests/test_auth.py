import netrc
from pathlib import Path
from unittest.mock import mock_open

import pytest

from altimetry_downloader_aviso.auth import (
    AuthenticationError,
    _get_credentials,
    _prompt_and_save_credentials,
    ensure_credentials,
)


def test_netcdf4_import():
    # netCDF4 must be imported as late as possible. Functions and modules triggering its
    # import has been moved to a separate module that is imported in a lazy fashion.
    import sys

    import altimetry_downloader_aviso

    assert "netCDF4" not in sys.modules
    import altimetry_downloader_aviso.catalog_client._granules_utils

    assert "netCDF4" in sys.modules


def test_get_credentials(mocker):

    mock_netrc = mocker.patch("altimetry_downloader_aviso.auth.netrc.netrc")
    mock_netrc.return_value.authenticators.return_value = ("testuser", None, "testpass")

    creds = _get_credentials("example.com")
    assert creds == ("testuser", "testpass")


def test_get_credentials_netrc_not_exist(mocker):
    mocker.patch.object(Path, "exists", return_value=False)

    creds = _get_credentials("example.com")
    assert creds is None


def test_get_credentials_netrc_invalid(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.auth.netrc.netrc",
        side_effect=netrc.NetrcParseError("Invalid netrc"),
    )

    with pytest.raises(AuthenticationError):
        _get_credentials("example.com")


def test_get_credentials_host_notexist(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.auth.netrc.netrc",
        side_effect=TypeError("Host doesn't exist in .netrc file."),
    )

    with pytest.warns(UserWarning) as record:
        creds = _get_credentials("example.com")

    assert creds is None
    assert "Host example.com doesn't exist in .netrc file" in str(record[0].message)


def test_get_credentials_rvalue_error(mocker):
    mock_netrc_class = mocker.patch("altimetry_downloader_aviso.auth.netrc.netrc")

    mock_auth_data = mocker.Mock()
    mock_auth_data.authenticators.side_effect = ValueError("Fake value error")
    mock_netrc_class.return_value = mock_auth_data

    with pytest.raises(AuthenticationError) as exc_info:
        _get_credentials("example.com")

    assert "An error happened when authenticating Aviso client." in str(exc_info.value)


def test_prompt_and_save_credentials(mocker):
    mocker.patch("builtins.input", return_value="user2")
    mocker.patch("getpass.getpass", return_value="pass2")
    m_open = mocker.patch("builtins.open", mock_open())
    mocker.patch("os.chmod")

    creds = _prompt_and_save_credentials("example.org")
    assert creds == ("user2", "pass2")

    m_open().write.assert_called_with(
        "\nmachine example.org login user2 password pass2\n"
    )


def test_ensure_credentials_from_netrc(mocker):
    mock_get = mocker.patch(
        "altimetry_downloader_aviso.auth._get_credentials",
        return_value=("user3", "pass3"),
    )

    creds = ensure_credentials("example.com")
    assert creds == ("user3", "pass3")
    mock_get.assert_called_once_with("example.com")


def test_ensure_credentials_prompt(mocker):
    mock_get = mocker.patch(
        "altimetry_downloader_aviso.auth._get_credentials", return_value=None
    )
    mock_prompt = mocker.patch(
        "altimetry_downloader_aviso.auth._prompt_and_save_credentials",
        return_value=("user4", "pass4"),
    )

    creds = ensure_credentials("example.com")
    assert creds == ("user4", "pass4")
    mock_get.assert_called_once_with("example.com")
    mock_prompt.assert_called_once_with("example.com")
