from wikipedia_parser.api import read_wikipedia_html


def test_youtube_outline_levels(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="outline",
    )

    outline = result["outline"]
    assert len(outline) > 10

    history = next(sec for sec in outline if sec["title"] == "History")
    founding = next(sec for sec in outline if sec["title"] == "Founding and initial growth (2005–2006)")
    content_id = next(sec for sec in outline if sec["title"] == "Content ID")

    assert history["level"] == 2
    assert founding["level"] == 3
    assert content_id["level"] == 4


def test_youtube_parent_section_collects_descendants(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="History",
        max_chars=5000,
    )

    text = result["content"]

    assert result["section"]["title"] == "History"
    assert text.strip() != ""

    # 至少命中 History 下若干子章节正文中的一个
    assert (
        "YouTube was founded" in text
        or "Google announced that they had acquired YouTube" in text
        or "Susan Wojcicki was appointed CEO" in text
    )


def test_youtube_leaf_section_only(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="Neal Mohan leadership (2023–present)",
        max_chars=2000,
    )

    assert result["section"]["title"] == "Neal Mohan leadership (2023–present)"
    assert result["content"].strip() != ""


def test_youtube_deep_level_section(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="Content ID",
        max_chars=2000,
    )

    assert result["section"]["level"] == 4
    assert result["content"].strip() != ""


def test_section_not_found(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="Definitely Missing Section",
    )

    assert result["error"] == "section_not_found"
    assert result["content"] == ""
    assert result["truncated"] is False


def test_section_truncation(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="History",
        max_chars=200,
    )

    assert result["content"].strip() != ""
    assert result["truncated"] is True
    assert len(result["content"]) <= 220  # 允许少量格式字符余量


def test_include_infobox_toggle(youtube_html):
    with_infobox = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="summary",
        include_infobox=True,
    )
    assert "infobox" in with_infobox

    without_infobox = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="summary",
        include_infobox=False,
    )
    assert without_infobox["infobox"] is None


def test_section_title_normalization(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="history",
        max_chars=3000,
    )

    assert result["section"]["title"] == "History"
    assert result["content"].strip() != ""


def test_section_title_partial_match(youtube_html):
    result = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="Founding and initial growth",
        max_chars=2000,
    )

    assert "Founding and initial growth" in result["section"]["title"]
    assert result["content"].strip() != ""


def test_parent_section_is_longer_than_leaf(youtube_html):
    parent = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="History",
        max_chars=5000,
    )

    leaf = read_wikipedia_html(
        youtube_html,
        lang="en",
        title="YouTube",
        mode="section",
        section="Founding and initial growth (2005–2006)",
        max_chars=5000,
    )

    assert len(parent["content"]) > len(leaf["content"])
