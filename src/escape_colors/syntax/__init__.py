"""Syntax token classification, themes, and styled ANSI highlighting."""

from .highlight import highlight, render_ansi, style_tokens, tokenize
from .lexers import get_lexer, register_lexer
from .themes import THEMES, Theme, get_theme, register_theme, resolve_style
from .tokens import Token, TokenType, normalize_token

__all__ = [
    "THEMES",
    "Theme",
    "Token",
    "TokenType",
    "get_lexer",
    "get_theme",
    "highlight",
    "normalize_token",
    "register_lexer",
    "register_theme",
    "render_ansi",
    "resolve_style",
    "style_tokens",
    "tokenize",
]
