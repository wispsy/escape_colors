"""Themes and style resolution for syntax highlighting."""

from typing import Any, Mapping

from .._codes import ESC, NAMED_CODES, background, color
from .tokens import TokenType

FALLBACK_TYPES: dict[TokenType | str, list[TokenType | str]] = {
    TokenType.FUNCTION: [TokenType.NAME, TokenType.TEXT],
    TokenType.CLASS: [TokenType.NAME, TokenType.TEXT],
    TokenType.BUILTIN: [TokenType.KEYWORD, TokenType.NAME, TokenType.TEXT],
    TokenType.BOOLEAN: [TokenType.LITERAL, TokenType.KEYWORD, TokenType.TEXT],
    TokenType.NULL: [TokenType.LITERAL, TokenType.KEYWORD, TokenType.TEXT],
    TokenType.LITERAL: [TokenType.KEYWORD, TokenType.TEXT],
    TokenType.PUNCTUATION: [TokenType.OPERATOR, TokenType.TEXT],
    TokenType.NAME: [TokenType.TEXT],
    TokenType.KEYWORD: [TokenType.TEXT],
    TokenType.STRING: [TokenType.TEXT],
    TokenType.NUMBER: [TokenType.TEXT],
    TokenType.COMMENT: [TokenType.TEXT],
    TokenType.OPERATOR: [TokenType.TEXT],
    TokenType.ERROR: [TokenType.TEXT],
}


def resolve_style(spec: Any) -> str:
    """Resolve a style specification into ANSI SGR sequences."""
    if not spec:
        return ""
    if isinstance(spec, str):
        if ESC in spec:
            return spec
        parts = spec.replace(",", " ").split()
    elif isinstance(spec, (list, tuple)):
        parts = []
        for item in spec:
            if isinstance(item, str):
                parts.extend(item.replace(",", " ").split())
            elif isinstance(item, int):
                parts.append(str(item))
            else:
                raise TypeError(f"Invalid style element: {item!r}")
    else:
        raise TypeError(f"Style spec must be str, tuple, or list, got {type(spec).__name__}")

    codes: list[str] = []
    for part in parts:
        if ESC in part:
            codes.append(part)
        elif part in NAMED_CODES:
            codes.append(NAMED_CODES[part])
        elif part.startswith("color_") and part[6:].isdigit():
            codes.append(color(int(part[6:])))
        elif part.startswith("color:") and part[6:].isdigit():
            codes.append(color(int(part[6:])))
        elif part.startswith("bg_") and part[3:].isdigit():
            codes.append(background(int(part[3:])))
        elif part.startswith("bg:") and part[3:].isdigit():
            codes.append(background(int(part[3:])))
        elif part.isdigit():
            codes.append(color(int(part)))
        else:
            raise ValueError(f"Unknown style specifier: {part!r}")

    return "".join(codes)


class Theme:
    """Mapping from token types to resolved ANSI styling sequences."""

    def __init__(
        self,
        name: str,
        styles: Mapping[TokenType | str, Any],
    ) -> None:
        self.name = name
        self._raw_styles = dict(styles)
        self._resolved: dict[str, str] = {}
        for key, spec in self._raw_styles.items():
            token_key = key.value if isinstance(key, TokenType) else str(key)
            self._resolved[token_key] = resolve_style(spec)

    def get_style(self, token_type: TokenType | str) -> str:
        """Return the ANSI escape code for the given token type, applying fallbacks."""
        key = token_type.value if isinstance(token_type, TokenType) else str(token_type)
        if key in self._resolved:
            return self._resolved[key]
        for fallback in FALLBACK_TYPES.get(token_type, []):
            fallback_key = fallback.value if isinstance(fallback, TokenType) else str(fallback)
            if fallback_key in self._resolved:
                return self._resolved[fallback_key]
        return ""

    def __repr__(self) -> str:
        return f"Theme({self.name!r})"


_DEFAULT_THEMES: dict[str, dict[TokenType | str, str]] = {
    "default": {
        TokenType.KEYWORD: "bold cyan",
        TokenType.NAME: "",
        TokenType.FUNCTION: "bright_yellow",
        TokenType.CLASS: "bold bright_yellow",
        TokenType.BUILTIN: "bright_cyan",
        TokenType.STRING: "green",
        TokenType.NUMBER: "magenta",
        TokenType.COMMENT: "dim",
        TokenType.OPERATOR: "bright_white",
        TokenType.PUNCTUATION: "white",
        TokenType.BOOLEAN: "bold magenta",
        TokenType.NULL: "bold magenta",
        TokenType.ERROR: "bold red",
    },
    "monokai": {
        TokenType.KEYWORD: "bold bright_red",
        TokenType.NAME: "white",
        TokenType.FUNCTION: "bright_green",
        TokenType.CLASS: "bold bright_cyan",
        TokenType.BUILTIN: "cyan",
        TokenType.STRING: "yellow",
        TokenType.NUMBER: "bright_magenta",
        TokenType.COMMENT: "bright_black",
        TokenType.OPERATOR: "bright_red",
        TokenType.PUNCTUATION: "white",
        TokenType.BOOLEAN: "bright_magenta",
        TokenType.NULL: "bright_magenta",
        TokenType.ERROR: "bold bg_red white",
    },
    "solarized-dark": {
        TokenType.KEYWORD: "green",
        TokenType.NAME: "bright_blue",
        TokenType.FUNCTION: "blue",
        TokenType.CLASS: "bold yellow",
        TokenType.BUILTIN: "yellow",
        TokenType.STRING: "cyan",
        TokenType.NUMBER: "magenta",
        TokenType.COMMENT: "bright_black italic",
        TokenType.OPERATOR: "green",
        TokenType.PUNCTUATION: "white",
        TokenType.BOOLEAN: "magenta",
        TokenType.NULL: "magenta",
        TokenType.ERROR: "bold red",
    },
    "solarized-light": {
        TokenType.KEYWORD: "green",
        TokenType.NAME: "blue",
        TokenType.FUNCTION: "blue",
        TokenType.CLASS: "bold yellow",
        TokenType.BUILTIN: "yellow",
        TokenType.STRING: "cyan",
        TokenType.NUMBER: "magenta",
        TokenType.COMMENT: "bright_black italic",
        TokenType.OPERATOR: "green",
        TokenType.PUNCTUATION: "black",
        TokenType.BOOLEAN: "magenta",
        TokenType.NULL: "magenta",
        TokenType.ERROR: "bold red",
    },
}

THEMES: dict[str, Theme] = {
    name: Theme(name, styles) for name, styles in _DEFAULT_THEMES.items()
}


def _normalize_name(name: str) -> str:
    return name.lower().replace("_", "-").strip()


def register_theme(name: str, theme_or_styles: Theme | Mapping[TokenType | str, Any]) -> Theme:
    """Register a new theme by name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Theme name must be a non-empty string")
    normalized = _normalize_name(name)
    if isinstance(theme_or_styles, Theme):
        theme = theme_or_styles
    elif isinstance(theme_or_styles, Mapping):
        theme = Theme(name, theme_or_styles)
    else:
        raise TypeError(f"Expected Theme or Mapping, got {type(theme_or_styles).__name__}")
    THEMES[normalized] = theme
    return theme


def get_theme(name_or_theme: str | Theme) -> Theme:
    """Retrieve a theme by name or return the Theme object."""
    if isinstance(name_or_theme, Theme):
        return name_or_theme
    if not isinstance(name_or_theme, str):
        raise TypeError(f"Theme must be str or Theme, got {type(name_or_theme).__name__}")
    normalized = _normalize_name(name_or_theme)
    if normalized in THEMES:
        return THEMES[normalized]
    raise ValueError(f"Unknown theme: {name_or_theme!r}. Available themes: {', '.join(sorted(THEMES.keys()))}")
