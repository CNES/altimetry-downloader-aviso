import requests

from altimetry_downloader_aviso.catalog_client._granules_utils import (
    _get_size_from_url,
    estimate_total_size,
    format_size,
)

# --- _get_size_from_url ---


def test_get_size_from_url_with_content_length(mocker):
    mock_response = mocker.Mock()
    mock_response.headers = {"Content-Length": "12345"}
    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils.requests.head",
        return_value=mock_response,
    )

    assert _get_size_from_url("https://tds.mock/a.nc") == 12345


def test_get_size_from_url_without_content_length(mocker):
    mock_response = mocker.Mock()
    mock_response.headers = {}
    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils.requests.head",
        return_value=mock_response,
    )

    assert _get_size_from_url("https://tds.mock/a.nc") is None


def test_get_size_from_url_http_error(mocker):
    mock_response = mocker.Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404")
    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils.requests.head",
        return_value=mock_response,
    )

    assert _get_size_from_url("https://tds.mock/a.nc") is None


def test_get_size_from_url_connection_error(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils.requests.head",
        side_effect=requests.ConnectionError("unreachable"),
    )

    assert _get_size_from_url("https://tds.mock/a.nc") is None


def test_get_size_from_url_passes_timeout(mocker):
    mock_head = mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils.requests.head",
        return_value=mocker.Mock(headers={"Content-Length": "10"}),
    )

    _get_size_from_url("https://tds.mock/a.nc", timeout=2.5)

    assert mock_head.call_args.kwargs["timeout"] == 2.5


# --- estimate_total_size ---


def test_estimate_total_size_empty():
    assert estimate_total_size([]) == (0, 0)


def test_estimate_total_size_all_known(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils."
        "_get_size_from_url",
        side_effect=[100, 200, 300],
    )

    total, unknown = estimate_total_size(
        ["https://tds.mock/a.nc", "https://tds.mock/b.nc", "https://tds.mock/c.nc"]
    )

    assert total == 600
    assert unknown == 0


def test_estimate_total_size_mixed_unknown(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils."
        "_get_size_from_url",
        side_effect=[100, None, 300, None],
    )

    total, unknown = estimate_total_size(
        [
            "https://tds.mock/a.nc",
            "https://tds.mock/b.nc",
            "https://tds.mock/c.nc",
            "https://tds.mock/d.nc",
        ]
    )

    assert total == 400
    assert unknown == 2


def test_estimate_total_size_all_unknown(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.catalog_client._granules_utils."
        "_get_size_from_url",
        return_value=None,
    )

    total, unknown = estimate_total_size(["https://tds.mock/a.nc"])

    assert total == 0
    assert unknown == 1


# --- format_size ---


def test_format_size_bytes():
    assert format_size(500) == "500.0 B"


def test_format_size_petabytes():
    assert format_size(1024**5 * 1.1) == "1.1 PB"
