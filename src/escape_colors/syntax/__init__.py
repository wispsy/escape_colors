"""Syntax token classification, themes, and styled ANSI highlighting."""

from .astree import (
    adapt_astree_tokens,
    astree_node_to_tokens,
    is_astree_available,
    require_astree,
)
from .highlight import highlight, render_ansi, style_tokens, tokenize
from .lexers import get_lexer, register_lexer
from .themes import THEMES, Theme, get_theme, register_theme, resolve_style
from .tokens import Token, TokenType, normalize_token

__all__ = [
    "THEMES",
    "Theme",
    "Token",
    "TokenType",
    "adapt_astree_tokens",
    "astree_node_to_tokens",
    "get_lexer",
    "get_theme",
    "highlight",
    "is_astree_available",
    "normalize_token",
    "register_lexer",
    "register_theme",
    "render_ansi",
    "require_astree",
    "resolve_style",
    "style_tokens",
    "tokenize",
]
