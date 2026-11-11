"""Syntax highlighting examples with built-in themes and custom token streams.

Run with:
    uv run python examples/syntax_highlighting.py
"""

from escape_colors import ansi_print
from escape_colors.syntax import (
    Token,
    TokenType,
    highlight,
    register_theme,
    tokenize,
)

PYTHON_SNIPPET = '''def calculate_total(items: list[dict], tax_rate: float = 0.08) -> float:
    # Compute subtotal and apply sales tax
    subtotal = sum(item["price"] * item.get("qty", 1) for item in items)
    is_valid = subtotal > 0 and tax_rate is not None
    return subtotal * (1.0 + tax_rate) if is_valid else 0.0
'''

JSON_SNIPPET = '''{
  "project": "escape-colors",
  "version": "0.2.0",
  "tags": ["ansi", "terminal", "syntax"],
  "active": true,
  "config": null
}'''


def main() -> None:
    ansi_print("bold(underline(Python Highlighting (Monokai Theme):))")
    print(highlight(PYTHON_SNIPPET, language="python", theme="monokai"))

    ansi_print("bold(underline(JSON Highlighting (Solarized-Dark Theme):))")
    print(highlight(JSON_SNIPPET, language="json", theme="solarized-dark"))

    ansi_print("bold(underline(Custom Theme Registration:))")
    custom_theme = register_theme("autumn", {
        TokenType.KEYWORD: "bold yellow",
        TokenType.FUNCTION: "bright_red",
        TokenType.STRING: "bright_yellow",
        TokenType.NUMBER: "red",
        TokenType.COMMENT: "dim",
    })
    print(highlight(PYTHON_SNIPPET, language="python", theme=custom_theme))

    ansi_print("bold(underline(Pre-tokenized Stream Highlighting:))")
    tokens = [
        Token(TokenType.KEYWORD, "from"),
        Token(TokenType.TEXT, " "),
        Token(TokenType.NAME, "astree"),
        Token(TokenType.TEXT, " "),
        Token(TokenType.KEYWORD, "import"),
        Token(TokenType.TEXT, " "),
        Token(TokenType.NAME, "tokenize"),
    ]
    print(highlight(tokens, theme="default"))


if __name__ == "__main__":
    main()
