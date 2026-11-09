import unittest

import escape_colors as colors
from escape_colors.syntax import (
    Token,
    TokenType,
    get_lexer,
    highlight,
    register_lexer,
    tokenize,
)


class SyntaxHighlightTests(unittest.TestCase):
    def test_tokenize_python_roundtrip_and_types(self):
        source = (
            "# A comment\n"
            "class Greeter:\n"
            "    def hello(self, name: str = 'world') -> int:\n"
            "        x = 42\n"
            "        flag = True and None\n"
            "        print(f'Hello {name}')\n"
            "        return x + 1\n"
        )
        tokens = tokenize(source, "python")
        # Exact round-trip preservation
        self.assertEqual("".join(t.value for t in tokens), source)

        types = {t.type for t in tokens}
        self.assertIn(TokenType.COMMENT, types)
        self.assertIn(TokenType.CLASS, types)
        self.assertIn(TokenType.KEYWORD, types)
        self.assertIn(TokenType.FUNCTION, types)
        self.assertIn(TokenType.STRING, types)
        self.assertIn(TokenType.NUMBER, types)
        self.assertIn(TokenType.BOOLEAN, types)
        self.assertIn(TokenType.NULL, types)
        self.assertIn(TokenType.BUILTIN, types)
        self.assertIn(TokenType.OPERATOR, types)
        self.assertIn(TokenType.PUNCTUATION, types)

    def test_tokenize_python_incomplete_code(self):
        # Incomplete syntax should not raise TokenError or SyntaxError
        incomplete = "def broken():\n    msg = 'unclosed string"
        tokens = tokenize(incomplete, "py")
        self.assertEqual("".join(t.value for t in tokens), incomplete)

    def test_tokenize_python_empty(self):
        self.assertEqual(tokenize("", "python"), [])

    def test_tokenize_json_roundtrip_and_types(self):
        json_source = '{\n  "title": "Escape Colors",\n  "count": 42,\n  "active": true,\n  "extra": null\n}'
        tokens = tokenize(json_source, "json")
        self.assertEqual("".join(t.value for t in tokens), json_source)

        token_map = {t.value: t.type for t in tokens}
        self.assertEqual(token_map['"title"'], TokenType.NAME)
        self.assertEqual(token_map['"Escape Colors"'], TokenType.STRING)
        self.assertEqual(token_map["42"], TokenType.NUMBER)
        self.assertEqual(token_map["true"], TokenType.BOOLEAN)
        self.assertEqual(token_map["null"], TokenType.NULL)
        self.assertEqual(token_map["{"], TokenType.PUNCTUATION)

    def test_tokenize_json_incomplete(self):
        incomplete = '{"key": "unclosed'
        tokens = tokenize(incomplete, "json")
        self.assertEqual("".join(t.value for t in tokens), incomplete)

    def test_tokenize_json_empty(self):
        self.assertEqual(tokenize("", "json"), [])

    def test_lexer_registry(self):
        py_lexer = get_lexer("python")
        self.assertIs(get_lexer("py"), py_lexer)
        self.assertIs(get_lexer("PY3"), py_lexer)
        self.assertIsNotNone(get_lexer("JSON"))

        with self.assertRaises(ValueError):
            get_lexer("unsupported_language_xyz")

        with self.assertRaises(TypeError):
            get_lexer(123)

        # Custom lexer registration
        register_lexer("custom", lambda s: [Token(TokenType.TEXT, s)], aliases=["cstm"])
        self.assertIsNotNone(get_lexer("custom"))
        self.assertIsNotNone(get_lexer("cstm"))

    def test_highlight_string_with_language(self):
        code = "def add(a, b): return a + b"
        result = highlight(code, language="python", theme="monokai")
        self.assertIn("add", result)
        self.assertIn(colors.reset, result)

    def test_highlight_pretokenized_input(self):
        pre_tokens = [
            Token(TokenType.KEYWORD, "def"),
            Token(TokenType.TEXT, " "),
            Token(TokenType.FUNCTION, "foo"),
            Token(TokenType.PUNCTUATION, "()"),
        ]
        # pre-tokenized does not require language
        result = highlight(pre_tokens, theme="default")
        self.assertIn("foo", result)
        self.assertTrue(result.endswith(colors.reset))

    def test_highlight_errors(self):
        with self.assertRaises(ValueError):
            highlight("print('hello')", language=None)

        with self.assertRaises(TypeError):
            highlight(12345)


if __name__ == "__main__":
    unittest.main()
