"""Page reading functionality for ZIM files."""

from strip_tags import strip_tags

from .archive import get_archive_by_name, get_archive_by_lang
from .exceptions import ArticleReadError, ArchiveNotFoundError


def read_page_by_lang_title(lang: str, title: str) -> str:
    """Read and return plain text content of an page from a ZIM archive.

    Args:
        lang: Language code (e.g., "en").
        title: Page title (e.g., "Python (programming language)").
    """
    try:
        zim = get_archive_by_lang(lang)
        entry = zim.get_entry_by_title(title)
        html_content = bytes(entry.get_item().content).decode("UTF-8")
        plain_text = strip_tags(html_content, minify=True, remove_blank_lines=True)
        return plain_text.strip()
    except ArchiveNotFoundError:
        return None
    except KeyError as e:
        return None # return None for cache
        # raise EntryNotFoundError(
        #     f"Error reading page '{title}' from '{lang}': Entry not found"
        # )
    except Exception as e:
        raise ArticleReadError(
            f"Unexpected error reading page '{title}' from '{lang}': {e}"
        )



def read_page(name: str, title: str) -> str:
    """Read and return plain text content of an page from a ZIM archive.

    Args:
        name: Name of the ZIM file as defined in config.
        title: Page title (e.g., "Python (programming language)").

    Returns:
        Plain text content of the page with HTML tags stripped.
    """
    try:
        zim = get_archive_by_name(name)
        entry = zim.get_entry_by_title(title)
        html_content = bytes(entry.get_item().content).decode("UTF-8")
        plain_text = strip_tags(html_content, minify=True, remove_blank_lines=True)
        return plain_text.strip()
    except ArchiveNotFoundError:
        return None
    except KeyError as e:
        return None # return None for cache
        # raise EntryNotFoundError(
        #     f"Error reading page '{title}' from '{name}': Entry not found"
        # )
    except Exception as e:
        raise ArticleReadError(
            f"Unexpected error reading page '{title}' from '{name}': {e}"
        )


def has_entry_by_title_in_lang(lang: str, title: str) -> bool:
    """Check if an page exists in a ZIM archive.

    Args:
        lang: Language code (e.g., "en").
        title: Page title (e.g., "Python (programming language)").

    Returns:
        True if the page exists, False otherwise.
    """
    try:
        zim = get_archive_by_lang(lang)
        return zim.has_entry_by_title(title)
    except ArchiveNotFoundError:
        raise
    except RuntimeError:
        raise

def has_entry_by_title(name: str, title: str) -> bool:
    """Check if an page exists in a ZIM archive.

    Args:
        name: Name of the ZIM file as defined in config.
        title: Page title (e.g., "Python (programming language)").

    Returns:
        True if the page exists, False otherwise.
    """
    try:
        zim = get_archive_by_name(name)
        return zim.has_entry_by_title(title)
    except RuntimeError:
        raise
   