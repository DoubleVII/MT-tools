"""Kiwix Search custom exceptions."""


class ArchiveNotFoundError(Exception):
    """Raised when ZIM archive file is not found."""

    pass

class EntryNotFoundError(Exception):
    """Raised when entry is not found in ZIM archive."""

    pass


class ArticleReadError(Exception):
    """Raised when reading an article fails."""

    pass


class ConfigError(Exception):
    """Raised when configuration is invalid."""

    pass
