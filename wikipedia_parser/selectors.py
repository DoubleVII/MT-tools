# 需要整个删除的节点
DROP_SELECTORS = [
    "script",
    "style",
    "noscript",
    "sup.reference",
    ".mw-editsection",
    ".reference",
    ".reflist",
    ".mw-references-wrap",
    ".shortdescription",
    ".hatnote",
    ".navbox",
    ".vertical-navbox",
    ".toc",
    ".toclimit-1",
    ".toclimit-2",
    ".toclimit-3",
    ".metadata",
    ".ambox",
    ".ombox",
    ".tmbox",
    ".fmbox",
    ".dmbox",
    ".cmbox",
    ".sistersitebox",
    ".portal",
    ".noprint",
    ".printfooter",
    ".catlinks",
    ".stub",
    ".mw-empty-elt",
]

# 一般不作为正文块处理
SKIP_BLOCK_SELECTORS = [
    ".thumb",
    "figure",
    ".tright",
    ".tleft",
]

# 主正文容器候选
CONTENT_ROOT_SELECTORS = [
    ".mw-parser-output",
    "#mw-content-text",
    "main",
    "article",
]

# 标题标签
HEADING_TAGS = {"h2", "h3", "h4"}

# 可以直接识别成块的标签
PARAGRAPH_TAGS = {"p", "blockquote"}
LIST_TAGS = {"ul", "ol"}
TABLE_TAGS = {"table"}
