"""Thread-safe ZIM Archive management."""

import threading
from pathlib import Path
from typing import Dict, Optional

from libzim.reader import Archive

from .config import get_config, get_zim_path
from .exceptions import ArchiveNotFoundError
import logging
logger = logging.getLogger(__name__)

class ArchivePool:
    """Thread-safe pool of ZIM Archive instances."""

    def __init__(self):
        self._lock = threading.Lock()
        self._archives: Dict[str, Archive] = {}
        self._name_to_path: Dict[str, str] = {}
        self._lang_to_name: Dict[str, str] = {}

    def get_archive(self, zim_path: str) -> Archive:
        """Get or create a ZIM Archive instance for the given path."""
        with self._lock:
            if zim_path not in self._archives:
                path = Path(zim_path)
                if not path.exists():
                    raise ArchiveNotFoundError(f"ZIM file not found: {zim_path}")
                self._archives[zim_path] = Archive(path)
            return self._archives[zim_path]

    def get_archive_by_name(self, name: str) -> Archive:
        """Get or create a ZIM Archive instance by name."""
        with self._lock:
            if name in self._name_to_path:
                zim_path = self._name_to_path[name]
                archive = self._archives.get(zim_path)
                if archive is not None:
                    return archive


            zim_path = get_zim_path(name)
            if zim_path is None:
                raise ArchiveNotFoundError(f"ZIM file not found with name: {name}")

            path = Path(zim_path)
            if not path.exists():
                raise ArchiveNotFoundError(f"ZIM file not found: {zim_path}")

            self._archives[zim_path] = Archive(path)
            self._name_to_path[name] = zim_path
            return self._archives[zim_path]

    def get_archive_by_lang(self, lang: str) -> Archive:
        """Get or create a ZIM Archive instance by language."""
        if lang in self._lang_to_name:
            name = self._lang_to_name[lang]
            return self.get_archive_by_name(name)
        else:
            config = get_config()
            zim_files = config.zim_files
            for zf in zim_files:
                if zf.lang == lang:
                    name = zf.name
                    return self.get_archive_by_name(name)
            raise ArchiveNotFoundError(f"ZIM file not found for language: {lang}")



    def preload(self, names: Optional[list] = None):
        """Preload archives into pool."""
        config = get_config()
        zim_files = config.zim_files

        for zf in zim_files:
            if names and zf.name not in names:
                continue
            try:
                self.get_archive_by_name(zf.name)
                self._lang_to_name[zf.lang] = zf.name
            except ArchiveNotFoundError:
                logger.warning("Preload failed for %s: %s", zf.name, e)

    # def close_all(self):
    #     """Close all Archive instances."""
    #     with self._lock:
    #         self._archives.clear()
    #         self._name_to_path.clear()


_archive_pool = ArchivePool()


def get_archive(zim_path: str) -> Archive:
    """Get a ZIM Archive from the global pool by path."""
    return _archive_pool.get_archive(zim_path)


def get_archive_by_name(name: str) -> Archive:
    """Get a ZIM Archive from the global pool by name."""
    return _archive_pool.get_archive_by_name(name)


def get_archive_by_lang(lang: str) -> Archive:
    """Get a ZIM Archive from the global pool by language."""
    return _archive_pool.get_archive_by_lang(lang)



def preload_archives(names: Optional[list] = None):
    """Preload all configured archives into the global pool."""
    _archive_pool.preload(names)

