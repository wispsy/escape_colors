"""Lexer registry and language dispatch."""

from typing import Callable

from ..astree import tokenize_html_astree
from ..tokens import Token
from .json import tokenize_json
from .python import tokenize_python

LexerFunc = Callable[[str], list[Token]]

_REGISTRY: dict[str, LexerFunc] = {}


def register_lexer(name: str, lexer: LexerFunc, aliases: list[str] | tuple[str, ...] | None = None) -> None:
    """Register a lexer for a language name and optional aliases."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Language name must be a non-empty string")
    key = name.lower().strip()
    _REGISTRY[key] = lexer
    if aliases:
        for alias in aliases:
            _REGISTRY[alias.lower().strip()] = lexer


def get_lexer(language: str) -> LexerFunc:
    """Get the tokenizer function for a language name."""
    if not isinstance(language, str):
        raise TypeError(f"Language must be a str, got {type(language).__name__}")
    key = language.lower().strip()
    if key in _REGISTRY:
        return _REGISTRY[key]
    available = ", ".join(sorted(set(_REGISTRY.keys())))
    raise ValueError(f"Unsupported language: {language!r}. Available languages: {available}")


# Register built-ins
register_lexer("python", tokenize_python, aliases=("py", "py3"))
register_lexer("json", tokenize_json)
register_lexer("html", tokenize_html_astree, aliases=("htm",))

__all__ = [
    "get_lexer",
    "register_lexer",
    "tokenize_html_astree",
    "tokenize_json",
    "tokenize_python",
]
