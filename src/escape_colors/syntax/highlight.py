"""Token styling, tokenization, and ANSI rendering engine."""

from typing import Any, Iterable

from .._codes import RESET
from .lexers import get_lexer
from .themes import Theme, get_theme
from .tokens import Token, normalize_token


def tokenize(source: str, language: str) -> list[Token]:
    """Tokenize source code in the specified language into tokens."""
    if not isinstance(source, str):
        raise TypeError(f"source must be str, got {type(source).__name__}")
    lexer = get_lexer(language)
    return lexer(source)


def style_tokens(
    tokens: Iterable[Any],
    theme: Theme | str = "default",
) -> list[tuple[str, str]]:
    """Map a sequence of tokens into (style_ansi, text) pairs using a theme."""
    active_theme = get_theme(theme)
    styled: list[tuple[str, str]] = []
    for item in tokens:
        token = normalize_token(item)
        style = active_theme.get_style(token.type)
        styled.append((style, token.value))
    return styled


def render_ansi(styled_tokens: Iterable[tuple[str, str]]) -> str:
    """Render (style_ansi, text) pairs into an ANSI escape sequence string."""
    parts: list[str] = []
    current_style = ""
    for style, text in styled_tokens:
        if not text:
            continue
        if style != current_style:
            if current_style:
                parts.append(RESET)
            if style:
                parts.append(style)
            current_style = style
        parts.append(text)
    if current_style:
        parts.append(RESET)
    return "".join(parts)


def highlight(
    source_or_tokens: str | Iterable[Any],
    language: str | None = None,
    theme: Theme | str = "default",
) -> str:
    """Highlight source code or a pre-tokenized sequence into ANSI formatted text."""
    if isinstance(source_or_tokens, str):
        if language is None:
            raise ValueError("language must be specified when source is a string")
        tokens: Iterable[Any] = tokenize(source_or_tokens, language)
    elif isinstance(source_or_tokens, Iterable):
        tokens = source_or_tokens
    else:
        raise TypeError(
            f"source_or_tokens must be str or Iterable of tokens, got {type(source_or_tokens).__name__}"
        )
    styled = style_tokens(tokens, theme=theme)
    return render_ansi(styled)
