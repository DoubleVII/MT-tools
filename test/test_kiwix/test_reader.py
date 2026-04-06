"""Tests for kiwix_reader reader module."""

import pytest
from unittest.mock import patch, MagicMock

from kiwix_reader.reader import read_page, read_page_by_lang_title
from kiwix_reader.exceptions import ArchiveNotFoundError, ArticleReadError


class TestReadPage:
    """Test read_page function."""

    @patch("kiwix_reader.reader.get_archive_by_name")
    def test_read_page_success(self, mock_get_archive_by_name):
        """Test successful page reading."""
        mock_zim = MagicMock()
        mock_entry = MagicMock()
        mock_item = MagicMock()
        mock_item.content = b"<html><body>Test content</body></html>"
        mock_entry.get_item.return_value = mock_item
        mock_zim.get_entry_by_title.return_value = mock_entry
        mock_get_archive_by_name.return_value = mock_zim

        result = read_page("wikipedia", "TestArticle")
        assert "Test content" in result

    @patch("kiwix_reader.reader.get_archive_by_name")
    def test_read_page_entry_not_found(self, mock_get_archive_by_name):
        """Test page reading when entry not found."""
        mock_zim = MagicMock()
        mock_zim.get_entry_by_title.side_effect = KeyError("not found")
        mock_get_archive_by_name.return_value = mock_zim

        result = read_page("wikipedia", "NonExistent")
        assert result is None

    @patch("kiwix_reader.reader.get_archive_by_name")
    def test_read_page_runtime_error(self, mock_get_archive_by_name):
        """Test page reading with runtime error."""
        mock_get_archive_by_name.return_value = MagicMock()
        mock_get_archive_by_name.return_value.get_entry_by_title.side_effect = (
            RuntimeError("not found")
        )

        with pytest.raises(ArticleReadError):
            read_page("wikipedia", "NonExistent")

    @patch("kiwix_reader.reader.get_archive_by_name")
    def test_read_page_archive_not_found(self, mock_get_archive_by_name):
        """Test page reading with archive not found."""
        mock_get_archive_by_name.side_effect = ArchiveNotFoundError("ZIM not found")

        result = read_page("missing", "Article")
        assert result is None


class TestReadPageByLangTitle:
    """Test read_page_by_lang_title function."""

    @patch("kiwix_reader.reader.get_archive_by_lang")
    def test_read_page_by_lang_success(self, mock_get_archive_by_lang):
        """Test successful page reading by language."""
        mock_zim = MagicMock()
        mock_entry = MagicMock()
        mock_item = MagicMock()
        mock_item.content = b"<html><body>Test content</body></html>"
        mock_entry.get_item.return_value = mock_item
        mock_zim.get_entry_by_title.return_value = mock_entry
        mock_get_archive_by_lang.return_value = mock_zim

        result = read_page_by_lang_title("en", "TestArticle")
        assert "Test content" in result

    @patch("kiwix_reader.reader.get_archive_by_lang")
    def test_read_page_by_lang_entry_not_found(self, mock_get_archive_by_lang):
        """Test page reading by language when entry not found."""
        mock_zim = MagicMock()
        mock_zim.get_entry_by_title.side_effect = KeyError("not found")
        mock_get_archive_by_lang.return_value = mock_zim

        result = read_page_by_lang_title("en", "NonExistent")
        assert result is None

    @patch("kiwix_reader.reader.get_archive_by_lang")
    def test_read_page_by_lang_runtime_error(self, mock_get_archive_by_lang):
        """Test page reading by language with runtime error."""
        mock_get_archive_by_lang.return_value = MagicMock()
        mock_get_archive_by_lang.return_value.get_entry_by_title.side_effect = (
            RuntimeError("not found")
        )

        with pytest.raises(ArticleReadError):
            read_page_by_lang_title("en", "NonExistent")

    @patch("kiwix_reader.reader.get_archive_by_lang")
    def test_read_page_by_lang_archive_not_found(self, mock_get_archive_by_lang):
        """Test page reading by language with archive not found."""
        mock_get_archive_by_lang.side_effect = ArchiveNotFoundError("ZIM not found")

        result = read_page_by_lang_title("missing", "Article")
        assert result is None
