from pathlib import Path
import pytest


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def youtube_html():
    return load_fixture("youtube.html")


@pytest.fixture
def python_html():
    return load_fixture("python_programming_language.html")


@pytest.fixture
def earth_html():
    return load_fixture("earth.html")
