"""Directory scanner for discovering agent config files."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


@dataclass
class DiscoveredAgent:
    """Discovered agent from directory scan."""
    agent_id: str
    name: str
    source: str = "directory"  # always "directory" for this scanner
    config_path: Path = None
    config: dict = None

    def __post_init__(self):
        if self.config_path is None:
            self.config_path = Path()
        if self.config is None:
            self.config = {}


class DirectoryScanner:
    """Scans directories for agent configuration files."""

    DEFAULT_PATHS = [
        ".zoo/agents/",
        "~/.zoo/agents/",
    ]

    FILE_PATTERNS = ["*.yaml", "*.yml", "*.json"]

    def __init__(self, scan_paths: List[str] = None):
        """
        Initialize the directory scanner.

        Args:
            scan_paths: List of paths to scan. Defaults to DEFAULT_PATHS.
        """
        self.scan_paths = scan_paths or self.DEFAULT_PATHS

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a path string, expanding user home directory."""
        path = Path(path_str)
        if pathStr := os.path.expanduser(path_str):
            path = Path(os.path.expanduser(path_str))
        return path

    def _scan_directory(self, directory: Path) -> List[DiscoveredAgent]:
        """
        Scan a single directory for agent config files.

        Args:
            directory: Directory path to scan.

        Returns:
            List of discovered agents from this directory.
        """
        discovered = []

        if not directory.exists() or not directory.is_dir():
            return discovered

        for pattern in self.FILE_PATTERNS:
            for file_path in directory.glob(pattern):
                agents = self._parse_config_file(file_path)
                discovered.extend(agents)

        return discovered

    def _parse_config_file(self, file_path: Path) -> List[DiscoveredAgent]:
        """
        Parse a config file and extract agent definitions.

        Args:
            file_path: Path to config file.

        Returns:
            List of discovered agents from this file.
        """
        discovered = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.suffix in (".yaml", ".yml"):
                    raw_config = yaml.safe_load(f)
                elif file_path.suffix == ".json":
                    raw_config = json.load(f)
                else:
                    return discovered
        except (OSError, yaml.YAMLError, json.JSONDecodeError):
            return discovered

        if not raw_config:
            return discovered

        # Handle both direct agent dict and agents list format
        agents_list = []
        if isinstance(raw_config, dict):
            if "agents" in raw_config:
                agents_list = raw_config["agents"]
            elif "id" in raw_config:
                # Single agent config without wrapping "agents" key
                agents_list = [raw_config]

        for agent_data in agents_list:
            if not isinstance(agent_data, dict):
                continue
            if "id" not in agent_data:
                continue

            agent_id = agent_data.get("id", "")
            name = agent_data.get("name", agent_id)

            discovered.append(DiscoveredAgent(
                agent_id=agent_id,
                name=name,
                source="directory",
                config_path=file_path,
                config=agent_data,
            ))

        return discovered

    def scan(self) -> List[DiscoveredAgent]:
        """
        Scan all configured paths for agent configs.

        Returns:
            List of all discovered agents from all scan paths.
        """
        all_discovered = []

        for path_str in self.scan_paths:
            directory = self._resolve_path(path_str)
            discovered = self._scan_directory(directory)
            all_discovered.extend(discovered)

        return all_discovered


class _AgentFileHandler(FileSystemEventHandler):
    """Handler for file system events on agent config files."""

    def __init__(self, watcher: "DirectoryWatcher"):
        self.watcher = watcher

    def _is_agent_config(self, path: Path) -> bool:
        """Check if the file is an agent config file."""
        return path.suffix in (".yaml", ".yml", ".json")

    def on_modified(self, event):
        if not event.is_directory and self._is_agent_config(Path(event.src_path)):
            self.watcher._notify_change("modified", event.src_path)

    def on_created(self, event):
        if not event.is_directory and self._is_agent_config(Path(event.src_path)):
            self.watcher._notify_change("created", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._is_agent_config(Path(event.src_path)):
            self.watcher._notify_change("deleted", event.src_path)


class DirectoryWatcher:
    """Watch directories for agent config changes."""

    def __init__(self, scanner: DirectoryScanner, on_change: Callable = None):
        """
        Initialize the directory watcher.

        Args:
            scanner: DirectoryScanner instance to use for rescanning.
            on_change: Optional callback function(path, event_type) called on changes.
        """
        self.scanner = scanner
        self.on_change = on_change
        self.observer = Observer()
        self._handler = _AgentFileHandler(self)

    def _notify_change(self, event_type: str, path: str):
        """Notify about a file change."""
        if self.on_change:
            self.on_change(path, event_type)

    def start(self):
        """Start watching directories for changes."""
        for path_str in self.scanner.scan_paths:
            directory = self.scanner._resolve_path(path_str)
            if directory.exists() and directory.is_dir():
                self.observer.schedule(self._handler, str(directory), recursive=True)

        if not self.observer._watchers:
            return

        self.observer.start()

    def stop(self):
        """Stop watching for changes."""
        self.observer.stop()
        self.observer.join()
