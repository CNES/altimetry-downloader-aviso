import io

from rich.console import Console
from rich.progress import (
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    TransferSpeedColumn,
)

from altimetry_downloader_aviso.progress import (
    BytesProgress,
    CountProgress,
    get_progress,
)


def test_get_progress_disabled_returns_null_progress():
    with get_progress(enabled=False) as progress:
        # must not raise, regardless of arguments
        task_id = progress.add_task("Downloading", total=100)
        progress.advance(task_id, 10)
        progress.update(task_id, completed=100)


def test_get_progress_enabled_defaults_to_bytes_style():
    with get_progress(enabled=True) as progress:
        column_types = {type(c) for c in progress.columns}
        assert DownloadColumn in column_types
        assert TransferSpeedColumn in column_types


def test_get_progress_bytes_style_advances_by_bytes():
    with get_progress(enabled=True, style=BytesProgress()) as progress:
        task_id = progress.add_task("Downloading", total=100)
        progress.advance(task_id, 30)
        assert progress.tasks[0].completed == 30


def test_get_progress_count_style_shows_mofn_column():
    with get_progress(enabled=True, style=CountProgress()) as progress:
        column_types = {type(c) for c in progress.columns}
        assert MofNCompleteColumn in column_types
        assert DownloadColumn not in column_types


def test_get_progress_count_style_advances_by_file():
    with get_progress(enabled=True, style=CountProgress()) as progress:
        task_id = progress.add_task("Subsetting", total=3)
        progress.advance(task_id, 1)
        progress.advance(task_id, 1)
        assert progress.tasks[0].completed == 2


def test_get_progress_shares_given_console():
    buffer = io.StringIO()
    console = Console(file=buffer)

    with get_progress(enabled=True, console=console) as progress:
        assert progress.console is console
        progress.add_task("Downloading", total=10)

    # the Live display actually rendered through our console, not a new one
    assert buffer.getvalue() != ""


def test_get_progress_creates_own_console_if_none_given():
    with get_progress(enabled=True, console=None) as progress:
        assert isinstance(progress, Progress)
        assert progress.console is not None
