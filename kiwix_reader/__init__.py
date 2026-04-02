"""Kiwix Reader - Offline search API for ZIM files."""

from .archive import (
    get_archive,
    get_archive_by_name,
    preload_archives,
)
from .config import (
    Config,
    ZimFileConfig,
    get_config,
    get_zim_names,
    get_zim_path,
    load_config,
)
from .exceptions import (
    ArchiveNotFoundError,
    ArticleReadError,
    ConfigError,
)
from .reader import read_article_by_lang_title, has_entry_by_title_in_lang
