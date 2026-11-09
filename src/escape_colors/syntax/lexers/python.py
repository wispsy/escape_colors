"""Built-in Python lexical tokenizer."""

import builtins
import io
import keyword
import tokenize
from typing import Iterator

from ..tokens import Token, TokenType

_BUILTIN_NAMES = set(dir(builtins))


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def tokenize_python(source: str) -> list[Token]:
    """Tokenize Python source into syntax tokens, preserving all characters."""
    if not source:
        return []

    tokens: list[Token] = []
    offsets = _line_offsets(source)
    last_offset = 0
    prev_sig_token: str | None = None

    def char_pos(row: int, col: int) -> int:
        if row - 1 < len(offsets):
            return min(len(source), offsets[row - 1] + col)
        return len(source)

    reader = io.BytesIO(source.encode("utf-8")).readline
    try:
        raw_tokens = list(tokenize.tokenize(reader))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        raw_tokens = []
        reader = io.BytesIO(source.encode("utf-8")).readline
        token_gen = tokenize.tokenize(reader)
        while True:
            try:
                raw_tokens.append(next(token_gen))
            except StopIteration:
                break
            except (tokenize.TokenError, SyntaxError, IndentationError):
                break

    for tok in raw_tokens:
        if tok.type in (tokenize.ENCODING, tokenize.ENDMARKER):
            continue

        s_offset = char_pos(tok.start[0], tok.start[1])
        e_offset = char_pos(tok.end[0], tok.end[1])

        if s_offset > last_offset:
            tokens.append(Token(TokenType.TEXT, source[last_offset:s_offset], start=last_offset, end=s_offset))

        val = tok.string
        tok_type = TokenType.TEXT

        if tok.type == tokenize.NAME:
            if val in ("True", "False"):
                tok_type = TokenType.BOOLEAN
            elif val == "None":
                tok_type = TokenType.NULL
            elif keyword.iskeyword(val) or keyword.issoftkeyword(val):
                tok_type = TokenType.KEYWORD
                prev_sig_token = val
            elif prev_sig_token == "def":
                tok_type = TokenType.FUNCTION
                prev_sig_token = None
            elif prev_sig_token == "class":
                tok_type = TokenType.CLASS
                prev_sig_token = None
            elif val in _BUILTIN_NAMES:
                tok_type = TokenType.BUILTIN
                prev_sig_token = val
            else:
                tok_type = TokenType.NAME
                prev_sig_token = val
        elif tok.type == tokenize.STRING:
            tok_type = TokenType.STRING
            prev_sig_token = None
        elif tok.type == tokenize.NUMBER:
            tok_type = TokenType.NUMBER
            prev_sig_token = None
        elif tok.type == tokenize.COMMENT:
            tok_type = TokenType.COMMENT
        elif tok.type == tokenize.OP:
            if val in ("(", ")", "[", "]", "{", "}", ",", ":", ";", "."):
                tok_type = TokenType.PUNCTUATION
            else:
                tok_type = TokenType.OPERATOR
        elif tok.type == tokenize.ERRORTOKEN:
            tok_type = TokenType.ERROR
        else:
            tok_type = TokenType.TEXT

        tokens.append(Token(tok_type, val, start=s_offset, end=e_offset))
        last_offset = e_offset

    if last_offset < len(source):
        tail = source[last_offset:]
        # If unclosed string was at the tail, classify as string or error
        if tail.lstrip().startswith(('"', "'")):
            tokens.append(Token(TokenType.STRING, tail, start=last_offset, end=len(source)))
        else:
            tokens.append(Token(TokenType.TEXT, tail, start=last_offset, end=len(source)))

    return tokens
