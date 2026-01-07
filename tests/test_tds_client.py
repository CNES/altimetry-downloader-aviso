import logging
import os

import pytest
import requests

from altimetry_downloader_aviso.tds_client import (
    http_bulk_download,
    http_bulk_download_parallel,
    http_single_download,
    http_single_download_with_retries,
)

# coverage run --source=altimetry_downloader_aviso  -m pytest
# coverage report -m


def test_http_single_download_success(mocker, tmp_path):
    url = "https://example.com/file.txt"
    filename = os.path.basename(url)
    expected_path = tmp_path / filename

    mock_response = mocker.Mock()
    fake_data = b"dummy data"
    mock_response.content = fake_data
    mock_response.raise_for_status = mocker.Mock()

    mocker.patch("requests.get", return_value=mock_response)

    mocker.patch(
        "altimetry_downloader_aviso.auth.ensure_credentials",
        return_value=("user", "pass"),
    )

    result_path = http_single_download(url, tmp_path)

    assert os.path.exists(result_path)
    assert result_path == str(expected_path)
    with open(result_path, "rb") as f:
        assert f.read() == fake_data

    result_path = http_single_download(url, tmp_path)
    assert result_path == str(expected_path)

    result_path = http_single_download(url, tmp_path, overwrite=True)
    assert result_path == str(expected_path)
    with open(result_path, "rb") as f:
        assert f.read() == fake_data


def test_http_single_download_error(mocker):
    bad_url = "https://bad_url.com/file.txt"

    fake_response = mocker.MagicMock()
    fake_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Client Error"
    )

    mocker.patch("requests.get", return_value=fake_response)
    mocker.patch(
        "altimetry_downloader_aviso.auth.ensure_credentials",
        return_value=("user", "pass"),
    )

    with pytest.raises(requests.exceptions.HTTPError):
        http_single_download(bad_url, "/tmp_path")


def test_http_single_download_with_retries_success(mocker):

    url = "https://example.com/file.txt"
    tmp_path = "/tmp_path"
    filename = os.path.basename(url)
    expected_path = os.path.join(tmp_path, filename)
    mock_download = mocker.patch(
        "altimetry_downloader_aviso.tds_client.http_single_download"
    )
    mock_download.side_effect = [
        requests.exceptions.RequestException("fail"),
        str(expected_path),
    ]

    result_path = http_single_download_with_retries(url, tmp_path, retries=2, backoff=0)

    assert result_path == str(expected_path)
    assert mock_download.call_count == 2


def test_http_single_download_with_retries_backoff_timing(mocker, caplog):
    url = "https://example.com/file.txt"
    mock_download = mocker.patch(
        "altimetry_downloader_aviso.tds_client.http_single_download"
    )
    mock_download.side_effect = requests.exceptions.RequestException("fail")

    mock_sleep = mocker.patch("altimetry_downloader_aviso.tds_client.time.sleep")

    with pytest.raises(requests.exceptions.RequestException):
        with caplog.at_level(logging.DEBUG):
            http_single_download_with_retries(url, "/tmp_path", retries=3, backoff=2)

    assert mock_sleep.call_count == 2
    mock_sleep.assert_has_calls([mocker.call(2), mocker.call(4)])


def test_http_single_download_with_retries_fail_all(mocker):
    bad_url = "https://bad_url.com/file.txt"

    mocker.patch(
        "altimetry_downloader_aviso.tds_client.http_single_download",
        side_effect=requests.exceptions.RequestException("Network fail"),
    )
    with pytest.raises(requests.exceptions.RequestException):
        http_single_download_with_retries(bad_url, "/tmp_path", retries=3, backoff=0)


def test_http_bulk_download_success_and_skip_fail(mocker):
    mock_retry = mocker.patch(
        "altimetry_downloader_aviso.tds_client.http_single_download_with_retries"
    )
    mock_retry.side_effect = [
        "/tmp/file1.txt",
        requests.exceptions.RequestException("fail"),
        "/tmp/file3.txt",
    ]

    urls = ["https://a.com/1", "https://a.com/2", "https://a.com/3"]

    with pytest.warns(UserWarning) as record:
        paths = list(http_bulk_download(urls, "/tmp"))

    print(paths)
    assert paths == ["/tmp/file1.txt", "/tmp/file3.txt"]
    assert mock_retry.call_count == 3

    assert len(record) == 1
    assert "Failed to download https://a.com/2" in str(record[0].message)


def test_http_bulk_download_all_fail(mocker):
    mocker.patch(
        "altimetry_downloader_aviso.tds_client.http_single_download_with_retries",
        side_effect=requests.exceptions.RequestException("boom"),
    )
    urls = ["https://fail.com/1", "https://fail.com/2"]

    with pytest.warns(UserWarning) as record:
        results = list(http_bulk_download(urls, "/tmp"))

    assert results == []

    assert len(record) == 2
    assert "Failed to download https://fail.com/1" in str(record[0].message)
    assert "Failed to download https://fail.com/2" in str(record[1].message)


def test_http_bulk_download_parallel_success(mocker):
    mock_retry = mocker.patch(
        "altimetry_downloader_aviso.tds_client.http_single_download_with_retries"
    )
    mock_retry.side_effect = lambda url, *_: f"/tmp/{url.split('/')[-1]}"

    urls = ["https://x.com/a.txt", "https://x.com/b.txt"]
    results = list(
        http_bulk_download_parallel(urls, "/tmp", retries=1, backoff=0, max_workers=2)
    )

    assert sorted(results) == ["/tmp/a.txt", "/tmp/b.txt"]
    assert mock_retry.call_count == 2


def test_http_bulk_download_parallel_partial_fail(mocker):

    def fake_retry(url, *_):
        if "fail" in url:
            raise requests.exceptions.RequestException("Boom")
        return f"/tmp/{url.split('/')[-1]}"

    mocker.patch(
        "altimetry_downloader_aviso.tds_client.http_single_download_with_retries",
        side_effect=fake_retry,
    )
    urls = ["https://x.com/ok1.txt", "https://x.com/fail.txt", "https://x.com/ok2.txt"]

    with pytest.warns(UserWarning) as record:
        results = list(
            http_bulk_download_parallel(
                urls, "/tmp", retries=1, backoff=0, max_workers=3
            )
        )

    assert sorted(results) == ["/tmp/ok1.txt", "/tmp/ok2.txt"]

    assert len(record) == 1
    assert "Failed to download https://x.com/fail.txt" in str(record[0].message)
