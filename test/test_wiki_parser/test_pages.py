from wikipedia_parser.api import read_wikipedia_html


def test_python_outline_not_empty(python_html):
    result = read_wikipedia_html(
        python_html,
        lang="en",
        title="Python (programming language)",
        mode="outline",
    )

    assert result["outline"]
    assert len(result["outline"]) >= 5


def test_python_summary_not_empty(python_html):
    result = read_wikipedia_html(
        python_html,
        lang="en",
        title="Python (programming language)",
        mode="summary",
        max_chars=1200,
    )

    assert result["content"].strip() != ""
    assert isinstance(result["truncated"], bool)



def test_earth_summary_and_outline(earth_html):
    summary = read_wikipedia_html(
        earth_html,
        lang="en",
        title="Earth",
        mode="summary",
        max_chars=1000,
    )
    assert summary["content"].strip() != ""

    outline = read_wikipedia_html(
        earth_html,
        lang="en",
        title="Earth",
        mode="outline",
    )
    assert len(outline["outline"]) > 5
