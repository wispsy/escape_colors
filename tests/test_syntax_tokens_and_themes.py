import unittest

import escape_colors as colors
from escape_colors.syntax import (
    THEMES,
    Theme,
    Token,
    TokenType,
    get_theme,
    normalize_token,
    register_theme,
    render_ansi,
    resolve_style,
    style_tokens,
)


class DummyNode:
    def __init__(self, kind: str, text: str, start: int = 0, end: int = 5):
        self.kind = kind
        self.text = text
        self.start = start
        self.end = end


class SyntaxTokensAndThemesTests(unittest.TestCase):
    def test_token_type_values(self):
        self.assertEqual(TokenType.KEYWORD.value, "keyword")
        self.assertEqual(TokenType.STRING.value, "string")
        self.assertEqual(TokenType.NUMBER.value, "number")
        self.assertEqual(TokenType.COMMENT.value, "comment")
        self.assertEqual(TokenType.FUNCTION.value, "function")
        self.assertEqual(TokenType.CLASS.value, "class")
        self.assertEqual(TokenType.ERROR.value, "error")

    def test_token_unpacking_and_equality(self):
        tok = Token(TokenType.KEYWORD, "def", start=0, end=3)
        token_type, value = tok
        self.assertEqual(token_type, TokenType.KEYWORD)
        self.assertEqual(value, "def")
        self.assertEqual(tok.start, 0)
        self.assertEqual(tok.end, 3)

    def test_normalize_token(self):
        tok = Token(TokenType.KEYWORD, "import")
        self.assertIs(normalize_token(tok), tok)

        norm_tuple = normalize_token((TokenType.STRING, "'hello'"))
        self.assertEqual(norm_tuple, Token(TokenType.STRING, "'hello'"))

        duck = DummyNode("operator", "+", 10, 11)
        norm_duck = normalize_token(duck)
        self.assertEqual(norm_duck, Token("operator", "+", 10, 11))

        with self.assertRaises(TypeError):
            normalize_token((TokenType.STRING, 123))

        with self.assertRaises(TypeError):
            normalize_token(12345)

    def test_resolve_style(self):
        self.assertEqual(resolve_style(""), "")
        self.assertEqual(resolve_style(None), "")
        resolved = resolve_style("bold cyan")
        self.assertIn(colors.bold, resolved)
        self.assertIn(colors.cyan, resolved)

        palette = resolve_style("color_208")
        self.assertEqual(palette, colors.color(208))

        bg_palette = resolve_style("bg_100")
        self.assertEqual(bg_palette, colors.background(100))

        num_color = resolve_style("196")
        self.assertEqual(num_color, colors.color(196))

        with self.assertRaises(ValueError):
            resolve_style("invalid_style_name_xyz")

        with self.assertRaises(TypeError):
            resolve_style(123.45)

    def test_builtin_themes(self):
        self.assertIn("default", THEMES)
        self.assertIn("monokai", THEMES)
        self.assertIn("solarized-dark", THEMES)
        self.assertIn("solarized-light", THEMES)

        theme = get_theme("MONOKAI")
        self.assertEqual(theme.name, "monokai")

        solarized = get_theme("solarized_dark")
        self.assertEqual(solarized.name, "solarized-dark")

        with self.assertRaises(ValueError):
            get_theme("nonexistent_theme")

        with self.assertRaises(TypeError):
            get_theme(123)

    def test_theme_fallbacks(self):
        custom = Theme("test-fallback", {TokenType.NAME: "blue"})
        # FUNCTION should fall back to NAME
        self.assertEqual(custom.get_style(TokenType.FUNCTION), custom.get_style(TokenType.NAME))
        # Unknown type without match returns empty string
        self.assertEqual(custom.get_style(TokenType.COMMENT), "")

    def test_register_theme(self):
        my_theme = register_theme("custom-theme", {
            TokenType.KEYWORD: "bold yellow",
            TokenType.STRING: "green",
        })
        self.assertIs(get_theme("custom-theme"), my_theme)
        self.assertIn(colors.yellow, my_theme.get_style(TokenType.KEYWORD))

        with self.assertRaises(ValueError):
            register_theme("", {})

    def test_style_tokens_and_render_ansi(self):
        tokens = [
            Token(TokenType.KEYWORD, "def"),
            Token(TokenType.TEXT, " "),
            Token(TokenType.FUNCTION, "greet"),
            Token(TokenType.PUNCTUATION, "():"),
        ]
        styled = style_tokens(tokens, theme="default")
        self.assertEqual(len(styled), 4)

        rendered = render_ansi(styled)
        self.assertIn("def", rendered)
        self.assertIn("greet", rendered)
        self.assertTrue(rendered.endswith(colors.reset))

        # Plain text without styling produces exact original text
        plain_tokens = [Token(TokenType.TEXT, "hello world")]
        plain_styled = style_tokens(plain_tokens, theme="default")
        plain_rendered = render_ansi(plain_styled)
        self.assertEqual(plain_rendered, "hello world")


if __name__ == "__main__":
    unittest.main()
