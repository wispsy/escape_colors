"""Token styling and ANSI rendering engine."""

from typing import Any, Iterable

from .._codes import RESET
from .themes import Theme, get_theme
from .tokens import normalize_token


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
