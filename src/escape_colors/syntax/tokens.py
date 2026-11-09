"""Token types and representations for syntax highlighting."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TokenType(StrEnum):
    """Semantic classifications for source tokens."""

    KEYWORD = "keyword"
    NAME = "name"
    FUNCTION = "function"
    CLASS = "class"
    BUILTIN = "builtin"
    STRING = "string"
    NUMBER = "number"
    COMMENT = "comment"
    OPERATOR = "operator"
    PUNCTUATION = "punctuation"
    LITERAL = "literal"
    BOOLEAN = "boolean"
    NULL = "null"
    TEXT = "text"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Token:
    """A syntax token with semantic classification and text value."""

    type: TokenType | str
    value: str
    start: int | None = None
    end: int | None = None

    def __iter__(self):
        """Allow tuple unpacking into (type, value)."""
        yield self.type
        yield self.value


def normalize_token(item: Any) -> Token:
    """Convert a Token instance, tuple, or duck-typed object into a Token."""
    if isinstance(item, Token):
        return item
    if isinstance(item, tuple) and len(item) == 2:
        token_type, value = item
        if not isinstance(value, str):
            raise TypeError(f"Token value must be str, got {type(value).__name__}")
        return Token(type=token_type, value=value)
    if hasattr(item, "type") and hasattr(item, "value"):
        value = getattr(item, "value")
        if not isinstance(value, str):
            raise TypeError(f"Token value must be str, got {type(value).__name__}")
        start = getattr(item, "start", None)
        end = getattr(item, "end", None)
        return Token(type=getattr(item, "type"), value=value, start=start, end=end)
    if hasattr(item, "kind") and hasattr(item, "text"):
        value = getattr(item, "text")
        if not isinstance(value, str):
            raise TypeError(f"Token value must be str, got {type(value).__name__}")
        start = getattr(item, "start", None)
        end = getattr(item, "end", None)
        return Token(type=getattr(item, "kind"), value=value, start=start, end=end)
    raise TypeError(f"Cannot normalize object to Token: {item!r}")
