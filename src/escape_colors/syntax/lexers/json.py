"""Built-in JSON lexical tokenizer."""

import re

from ..tokens import Token, TokenType

_JSON_REGEX = re.compile(
    r"(?P<WHITESPACE>\s+)"
    r'|(?P<STRING>"(?:\\.|[^"\\])*(?:"|$))'
    r"|(?P<NUMBER>-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)"
    r"|(?P<BOOLEAN>\b(?:true|false)\b)"
    r"|(?P<NULL>\bnull\b)"
    r"|(?P<PUNCTUATION>[{}[\]:,])"
    r"|(?P<ERROR>.)"
)


def tokenize_json(source: str) -> list[Token]:
    """Tokenize JSON source text into syntax tokens."""
    if not source:
        return []

    tokens: list[Token] = []
    for match in _JSON_REGEX.finditer(source):
        kind = match.lastgroup
        val = match.group()
        start = match.start()
        end = match.end()

        if kind == "WHITESPACE":
            tokens.append(Token(TokenType.TEXT, val, start=start, end=end))
        elif kind == "STRING":
            # Check if this string is an object key followed by ':'
            rest = source[end:].lstrip()
            is_key = rest.startswith(":")
            if not val.endswith('"'):
                tok_type = TokenType.ERROR
            elif is_key:
                tok_type = TokenType.NAME
            else:
                tok_type = TokenType.STRING
            tokens.append(Token(tok_type, val, start=start, end=end))
        elif kind == "NUMBER":
            tokens.append(Token(TokenType.NUMBER, val, start=start, end=end))
        elif kind == "BOOLEAN":
            tokens.append(Token(TokenType.BOOLEAN, val, start=start, end=end))
        elif kind == "NULL":
            tokens.append(Token(TokenType.NULL, val, start=start, end=end))
        elif kind == "PUNCTUATION":
            tokens.append(Token(TokenType.PUNCTUATION, val, start=start, end=end))
        else:
            tokens.append(Token(TokenType.ERROR, val, start=start, end=end))

    return tokens
