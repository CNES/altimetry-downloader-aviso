from contextlib import contextmanager

from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TransferSpeedColumn


class _NullProgress:
    """No-op stand-in when the progress bar is disabled."""

    def add_task(self, *a, **k):
        return None

    def update(self, *a, **k):
        pass

    def advance(self, *a, **k):
        pass


@contextmanager
def get_progress(enabled: bool, console: Console | None = None):
    if not enabled:
        yield _NullProgress()
        return
    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(binary_units=True),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        yield progress
