"""Syntax token classification, themes, and styled ANSI highlighting."""

from .highlight import render_ansi, style_tokens
from .themes import THEMES, Theme, get_theme, register_theme, resolve_style
from .tokens import Token, TokenType, normalize_token

__all__ = [
    "THEMES",
    "Theme",
    "Token",
    "TokenType",
    "get_theme",
    "normalize_token",
    "register_theme",
    "render_ansi",
    "resolve_style",
    "style_tokens",
]
