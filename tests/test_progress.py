from altimetry_downloader_aviso.progress import get_progress
from rich.progress import Progress


def test_get_progress_disabled_returns_null_progress():
    with get_progress(enabled=False) as progress:
        # must not raise, regardless of arguments
        task_id = progress.add_task("Downloading", total=100)
        progress.advance(task_id, 10)
        progress.update(task_id, completed=100)


def test_get_progress_enabled_returns_rich_progress():
    with get_progress(enabled=True) as progress:
        assert isinstance(progress, Progress)
        task_id = progress.add_task("Downloading", total=100)
        progress.advance(task_id, 10)
        assert progress.tasks[0].completed == 10