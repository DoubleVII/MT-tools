"""Kiwix Search custom exceptions."""


class KiwixReaderError(Exception):
    """Base exception for kiwix reader library."""

    pass


class ArchiveNotFoundError(KiwixReaderError):
    """Raised when ZIM archive file is not found."""

    pass



class ArticleReadError(KiwixReaderError):
    """Raised when reading an article fails."""

    pass


class ConfigError(KiwixReaderError):
    """Raised when configuration is invalid."""

    pass
