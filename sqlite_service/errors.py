class SearchError(Exception):
    pass


class InvalidQueryError(SearchError):
    pass


class UnsupportedLanguageError(SearchError):
    pass
