# progress.py
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    TransferSpeedColumn,
)


class ProgressStyle:
    """Base class defining which extra rich columns to display, on top of the
    description and the bar (common to every style)."""

    columns: tuple[ProgressColumn, ...] = ()


class BytesProgress(ProgressStyle):
    """Byte-transfer progress: amount downloaded and transfer speed."""

    columns = (DownloadColumn(), TransferSpeedColumn())


class CountProgress(ProgressStyle):
    """File-count progress: "completed/total" files."""

    columns = (MofNCompleteColumn(),)


class _NullProgress:
    """No-op stand-in when the progress bar is disabled."""

    def add_task(self, *a, **k):
        return None

    def update(self, *a, **k):
        pass

    def advance(self, *a, **k):
        pass


@contextmanager
def get_progress(
    enabled: bool,
    console: Console | None = None,
    style: ProgressStyle | None = None,
):
    """Context manager yielding a rich Progress (or a no-op stand-in).

    style: ProgressStyle | None
        determines the extra columns shown (see BytesProgress, CountProgress).
        Defaults to BytesProgress if not given.
    """
    if not enabled:
        yield _NullProgress()
        return

    style = style or BytesProgress()

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        *style.columns,
        # share the Console so other rich output doesn't clash with the Live redraw
        console=console,
    ) as progress:
        yield progress
