"""Article reading functionality for ZIM files."""

from strip_tags import strip_tags

from .archive import get_archive_by_name, get_archive_by_lang
from .exceptions import ArchiveNotFoundError, ArticleReadError


def read_article_by_lang_title(lang: str, title: str) -> str:
    """Read and return plain text content of an article from a ZIM archive.

    Args:
        lang: Language code (e.g., "en").
        title: Article title (e.g., "Python (programming language)").
    """
    try:
        zim = get_archive_by_lang(lang)
        entry = zim.get_entry_by_title(title)
        html_content = bytes(entry.get_item().content).decode("UTF-8")
        plain_text = strip_tags(html_content, minify=True, remove_blank_lines=True)
        return plain_text.strip()
    except ArchiveNotFoundError:
        raise ArchiveNotFoundError(
            f"Error reading article '{title}' from '{lang}': Archive not found"
        )
    except Exception as e:
        raise ArticleReadError(
            f"Unexpected error reading '{title}' from '{lang}': {e}"
        )



def read_article(name: str, title: str) -> str:
    """Read and return plain text content of an article from a ZIM archive.

    Args:
        name: Name of the ZIM file as defined in config.
        title: Article title (e.g., "Python (programming language)").

    Returns:
        Plain text content of the article with HTML tags stripped.
    """
    try:
        zim = get_archive_by_name(name)
        entry = zim.get_entry_by_title(title)
        html_content = bytes(entry.get_item().content).decode("UTF-8")
        plain_text = strip_tags(html_content, minify=True, remove_blank_lines=True)
        return plain_text.strip()
    except RuntimeError as e:
        raise ArticleReadError(
            f"Error reading article '{title}' from '{name}': {e}"
        )
    except ArchiveNotFoundError:
        raise
    except Exception as e:
        raise ArticleReadError(
            f"Unexpected error reading '{title}' from '{name}': {e}"
        )


def has_entry_by_title_in_lang(lang: str, title: str) -> bool:
    """Check if an article exists in a ZIM archive.

    Args:
        lang: Language code (e.g., "en").
        title: Article title (e.g., "Python (programming language)").

    Returns:
        True if the article exists, False otherwise.
    """
    try:
        zim = get_archive_by_lang(lang)
        return zim.has_entry_by_title(title)
    except ArchiveNotFoundError:
        raise
    except RuntimeError:
        raise

def has_entry_by_title(name: str, title: str) -> bool:
    """Check if an article exists in a ZIM archive.

    Args:
        name: Name of the ZIM file as defined in config.
        title: Article title (e.g., "Python (programming language)").

    Returns:
        True if the article exists, False otherwise.
    """
    try:
        zim = get_archive_by_name(name)
        return zim.has_entry_by_title(title)
    except ArchiveNotFoundError:
        raise
    except RuntimeError:
        raise
   