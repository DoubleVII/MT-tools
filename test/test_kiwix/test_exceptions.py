"""Tests for kiwix_reader exceptions module."""

import pytest

from kiwix_reader.exceptions import (
    ArchiveNotFoundError,
    EntryNotFoundError,
    ArticleReadError,
    ConfigError,
)


class TestExceptions:
    """Test exception classes."""

    def test_archive_not_found_error(self):
        """Test ArchiveNotFoundError can be raised and caught."""
        with pytest.raises(ArchiveNotFoundError):
            raise ArchiveNotFoundError("file not found")

    def test_entry_not_found_error(self):
        """Test EntryNotFoundError can be raised and caught."""
        with pytest.raises(EntryNotFoundError):
            raise EntryNotFoundError("entry not found")

    def test_article_read_error(self):
        """Test ArticleReadError can be raised and caught."""
        with pytest.raises(ArticleReadError):
            raise ArticleReadError("read failed")

    def test_config_error(self):
        """Test ConfigError can be raised and caught."""
        with pytest.raises(ConfigError):
            raise ConfigError("invalid config")

    def test_exception_message(self):
        """Test exception message is preserved."""
        msg = "custom error message"
        with pytest.raises(ArchiveNotFoundError, match=msg):
            raise ArchiveNotFoundError(msg)
