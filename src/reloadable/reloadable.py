from __future__ import annotations

import importlib
import signal
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Timer, Lock
import types
from typing import Any

from rich.console import Console
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from tach.extension import DependentMap, Direction, ProjectConfig


console = Console()


@contextmanager
def timer(description: str, indent: int = 0):
    """Context manager to measure and print execution time"""
    prefix = "  " * indent
    console.print(f"{prefix}[blue]►[/blue] {description}...")
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    # Format time in ms if less than 1 second, otherwise in seconds
    time_str = f"{elapsed * 1000:.0f}ms" if elapsed < 1 else f"{elapsed:.2f}s"
    console.print(f"{prefix}[green]✓[/green] {description} ([cyan]{time_str}[/cyan])")


class BatchDebounceTimer:
    """Helper class to manage debounced events with batch collection"""

    def __init__(self, timeout: float, callback):
        self.timeout = timeout
        self.callback = callback
        self.timer = None
        self.batch: set[Path] = set()

    def add_to_batch(self, path: Path):
        """Add a path to the current batch and restart the timer"""
        console.print(f"[dim]Noticed edit to {path}...[/dim]")
        self.batch.add(path)
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(self.timeout, self.process_batch)
        self.timer.start()

    def process_batch(self):
        """Process all collected paths and clear the batch"""
        if self.batch:
            console.print(
                f"[blue]Processing batch of {len(self.batch)} file changes...[/blue]"
            )
            self.callback(self.batch)
            console.print("[green]Changes processed[/green]")
            self.batch.clear()


class ImportTracker:
    def __init__(self):
        self.original_import_order = []
        self.original_import_map = {}
        self.original_import_hook = __import__

    @contextmanager
    def track_imports(self):
        def import_tracker(name, *args, **kwargs):
            module = self.original_import_hook(name, *args, **kwargs)
            if isinstance(module, types.ModuleType) and not name.startswith("_"):
                if module.__name__ not in self.original_import_map:
                    self.original_import_map[module.__name__] = len(
                        self.original_import_order
                    )
                    self.original_import_order.append(module.__name__)
            return module

        sys.modules["builtins"].__import__ = import_tracker
        try:
            yield
        finally:
            sys.modules["builtins"].__import__ = self.original_import_hook

    def get_position(self, module_name):
        # Unknown modules go last
        return self.original_import_map.get(module_name, float("inf"))


def filepath_to_module_name(filepath: Path) -> str:
    # Takes a relpath and returns the module name
    return (
        filepath.with_suffix("").as_posix().replace("/", ".").removesuffix(".__init__")
    )


class PyModuleReloader(FileSystemEventHandler):
    def __init__(
        self,
        root_module_path: str,
        reload_lock: Lock,
        debounce_seconds: float = 0.25,
    ):
        super().__init__()
        self.project_root = Path.cwd()
        self.root_module_path = root_module_path
        self.reload_lock = reload_lock
        console.print("[blue]Building initial dependency map...[/blue]")
        # TODO: configure this correctly
        project_config = ProjectConfig()
        with timer("Initial dependency scan"):
            self.dep_map = DependentMap(
                project_root=self.project_root,
                project_config=project_config,
                direction=Direction.Dependents,
            )

        with timer("Initial import order tracking"):
            self.tracker = ImportTracker()
            self.tracker.original_import_order = [self.root_module_path]
            with self.tracker.track_imports():
                importlib.import_module(self.root_module_path)
            console.print("[blue]Initial import order:[/blue]")
            console.print(self.tracker.original_import_order)

        self.batch_handler = BatchDebounceTimer(debounce_seconds, self.handle_batch)

    def on_modified(self, event):
        if not isinstance(event, FileModifiedEvent):
            return

        file_path = Path(event.src_path)
        if not str(file_path).endswith(".py"):
            return

        console.print(f"[dim]Noticed edit to {file_path}...[/dim]")
        self.batch_handler.add_to_batch(file_path)

    def handle_batch(self, batch: set[Path]):
        with self.reload_lock:
            # Get all modules that need to be reloaded
            relpaths = [file_path.relative_to(self.project_root) for file_path in batch]
            with timer("Updating dependency map", indent=1):
                console.print(
                    f"  [yellow]Files changed: {', '.join(str(p) for p in relpaths)}[/yellow]"
                )
                self.dep_map.update_files(relpaths)

            with timer("Calculating affected modules", indent=1):
                try:
                    affected_files = set(map(Path, self.dep_map.get_closure(relpaths)))
                except ValueError:
                    affected_files = set(relpaths)

            if affected_files:
                preview = list(map(str, affected_files))[:5]
                console.print(
                    f"  [yellow]Will reload {len(affected_files)} "
                    f"file{'s' if len(affected_files) != 1 else ''}: "
                    f"{', '.join(preview)}"
                    f"{'[dim] [more...][/dim]' if len(affected_files) > 5 else ''}[/yellow]"
                )
                for file_path in affected_files:
                    try:
                        del sys.modules[filepath_to_module_name(file_path)]
                    except KeyError:
                        pass
                with timer("Reloading modules", indent=1):
                    reload_order = sorted(
                        affected_files,
                        key=lambda filepath: self.tracker.get_position(
                            filepath_to_module_name(filepath)
                        ),
                    )
                    for file_path in reload_order:
                        importlib.import_module(filepath_to_module_name(file_path))


class ReloadableWSGI:
    def __init__(self, wsgi_path: str):
        self.wsgi_path = wsgi_path
        self.app_module_path, self.app_name = self._parse_wsgi_path()
        self.lock = Lock()
        self._start()

    def _start(self):
        event_handler = PyModuleReloader(
            root_module_path=self.app_module_path, reload_lock=self.lock
        )
        observer = Observer()
        observer.schedule(event_handler, str(Path.cwd()), recursive=True)

        console.print(
            f"[green]Starting to watch Python files in:[/green] [blue]{Path.cwd()}[/blue]"
        )
        observer.daemon = True
        observer.start()

        def _kill_observer(_signum: int, _frame: Any) -> None:
            console.print("[red]Received SIGINT, exiting...[/red]")
            sys.exit(0)

        signal.signal(signal.SIGINT, _kill_observer)

    def _parse_wsgi_path(self):
        module, app = self.wsgi_path.rsplit(":", 1)
        return module, app

    def _get_app(self):
        app_module = importlib.import_module(self.app_module_path)
        return getattr(app_module, self.app_name)

    def __call__(self, environ, start_response):
        with self.lock:
            return self._get_app()(environ, start_response)
