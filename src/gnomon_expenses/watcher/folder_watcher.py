"""watchdog-based folder watcher for auto-processing new PDFs."""

from __future__ import annotations

import time
from pathlib import Path
from threading import Timer

from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from watchdog.observers import Observer

from gnomon_expenses.config import SUPPORTED_EXTENSIONS
from gnomon_expenses.extraction.pipeline import process_pdf
from gnomon_expenses.models.expense import file_hash
from gnomon_expenses.storage.local_json import LocalJsonStorage

# Debounce delay in seconds (PDF writes may not be atomic)
DEBOUNCE_SECONDS = 2.0


class _PDFHandler(FileSystemEventHandler):
    def __init__(self, base_dir: Path) -> None:
        self._timers: dict[str, Timer] = {}
        self._storage = LocalJsonStorage()
        self._base_dir = base_dir

    def _process(self, path: str) -> None:
        import shutil

        p = Path(path)
        if not p.exists() or p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        fhash = file_hash(p)
        if self._storage.find_by_hash(fhash):
            return

        from rich.console import Console
        console = Console()

        expense = process_pdf(p)
        if expense:
            # File into monthly folder
            if expense.date:
                folder = self._base_dir / expense.date.strftime("%y-%m")
                folder.mkdir(exist_ok=True)
                dest = folder / p.name
                if dest != p:
                    if dest.exists():
                        stem, suffix = p.stem, p.suffix
                        i = 1
                        while dest.exists():
                            dest = folder / f"{stem}_{i}{suffix}"
                            i += 1
                    shutil.move(str(p), str(dest))
                    expense.file_path = str(dest)

            self._storage.save(expense)
            filed = f" -> {expense.date.strftime('%y-%m')}/" if expense.date else ""
            console.print(
                f"  [green]auto[/green]  {p.name} — "
                f"{expense.vendor} {expense.currency} {expense.amount_gross}{filed}"
            )
        else:
            console.print(f"  [red]fail[/red]  {p.name} (could not extract)")

    def _schedule(self, path: str) -> None:
        # Cancel existing timer for this path (debounce)
        if path in self._timers:
            self._timers[path].cancel()
        t = Timer(DEBOUNCE_SECONDS, self._process, args=[path])
        t.daemon = True
        t.start()
        self._timers[path] = t

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:
        if not event.is_directory:
            self._schedule(event.dest_path)


def start_watching(directory: str | Path, recursive: bool = False) -> None:
    """Start watching a directory for new PDFs. Blocks until Ctrl+C."""
    observer = Observer()
    observer.schedule(_PDFHandler(Path(directory).resolve()), str(directory), recursive=recursive)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
