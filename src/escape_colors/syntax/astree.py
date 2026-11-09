"""Optional integration adapter for the astree package."""

import importlib
import importlib.util
from typing import Any, Iterable

from .tokens import Token, TokenType, normalize_token


def is_astree_available() -> bool:
    """Return True if the astree package is installed and importable."""
    return importlib.util.find_spec("astree") is not None


def require_astree() -> Any:
    """Import and return astree, or raise an informative ImportError."""
    try:
        return importlib.import_module("astree")
    except ImportError as error:
        raise ImportError(
            "The 'astree' package is required for this feature. "
            "Install it with: pip install 'escape-colors[syntax]'"
        ) from error


def astree_node_to_tokens(node: Any) -> list[Token]:
    """Convert an astree Document or Node tree into a list of syntax tokens."""
    tokens: list[Token] = []

    kind = getattr(node, "kind", None)
    if kind == "document" or hasattr(node, "root"):
        target_node = getattr(node, "root", node)
        for child in getattr(target_node, "children", ()):
            tokens.extend(astree_node_to_tokens(child))
        return tokens

    if kind == "element":
        tag = getattr(node, "tag", "tag")
        tokens.append(Token(TokenType.PUNCTUATION, "<"))
        tokens.append(Token(TokenType.KEYWORD, tag))

        attrs = getattr(node, "attrs", {})
        for name, value in attrs.items():
            tokens.append(Token(TokenType.TEXT, " "))
            tokens.append(Token(TokenType.NAME, name))
            if value is not None:
                tokens.append(Token(TokenType.OPERATOR, "="))
                tokens.append(Token(TokenType.STRING, f'"{value}"'))

        tokens.append(Token(TokenType.PUNCTUATION, ">"))

        for child in getattr(node, "children", ()):
            tokens.extend(astree_node_to_tokens(child))

        tokens.append(Token(TokenType.PUNCTUATION, "</"))
        tokens.append(Token(TokenType.KEYWORD, tag))
        tokens.append(Token(TokenType.PUNCTUATION, ">"))
    elif kind == "text":
        tokens.append(Token(TokenType.TEXT, getattr(node, "data", "")))
    elif kind == "comment":
        tokens.append(Token(TokenType.COMMENT, f"<!--{getattr(node, 'data', '')}-->"))
    elif kind == "declaration":
        tokens.append(Token(TokenType.KEYWORD, f"<!{getattr(node, 'data', '')}>"))
    elif kind == "processing_instruction":
        tokens.append(Token(TokenType.KEYWORD, f"<?{getattr(node, 'data', '')}>"))
    elif hasattr(node, "children"):
        for child in getattr(node, "children"):
            tokens.extend(astree_node_to_tokens(child))

    return tokens


def adapt_astree_tokens(items: Iterable[Any]) -> list[Token]:
    """Adapt pre-tokenized items or AST nodes into normalized Tokens."""
    adapted: list[Token] = []
    for item in items:
        if hasattr(item, "kind") and hasattr(item, "children"):
            adapted.extend(astree_node_to_tokens(item))
        else:
            adapted.append(normalize_token(item))
    return adapted


def tokenize_html_astree(source: str) -> list[Token]:
    """Parse HTML using astree and convert to syntax tokens."""
    astree = require_astree()
    doc = astree.Document.from_html(source)
    return astree_node_to_tokens(doc)
