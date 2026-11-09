import sys
import unittest
from unittest.mock import patch

from escape_colors.syntax import (
    Token,
    TokenType,
    adapt_astree_tokens,
    astree_node_to_tokens,
    highlight,
    is_astree_available,
    require_astree,
    tokenize,
)


class MockAstreeNode:
    def __init__(self, kind: str, tag: str | None = None, attrs: dict | None = None, data: str = "", children: tuple = ()):
        self.kind = kind
        self.tag = tag
        self.attrs = attrs or {}
        self.data = data
        self.children = children


class SyntaxAstreeIntegrationTests(unittest.TestCase):
    def test_lazy_astree_absence_handling(self):
        with patch("importlib.import_module", side_effect=ImportError("No module named 'astree'")):
            with self.assertRaises(ImportError) as ctx:
                require_astree()
            self.assertIn("escape-colors[syntax]", str(ctx.exception))

    def test_astree_node_to_tokens_mock_tree(self):
        text_node = MockAstreeNode("text", data="Hello world")
        elem_node = MockAstreeNode(
            "element",
            tag="h1",
            attrs={"class": "title"},
            children=(text_node,),
        )
        doc_node = MockAstreeNode("document", children=(elem_node,))

        tokens = astree_node_to_tokens(doc_node)
        self.assertTrue(any(t.type == TokenType.KEYWORD and t.value == "h1" for t in tokens))
        self.assertTrue(any(t.type == TokenType.NAME and t.value == "class" for t in tokens))
        self.assertTrue(any(t.type == TokenType.STRING and t.value == '"title"' for t in tokens))
        self.assertTrue(any(t.type == TokenType.TEXT and t.value == "Hello world" for t in tokens))

        # Can highlight adapted tokens
        styled = highlight(tokens, theme="default")
        self.assertIn("Hello world", styled)

    def test_adapt_astree_tokens_mixed_sequence(self):
        elem = MockAstreeNode("element", tag="b", children=(MockAstreeNode("text", data="bold text"),))
        regular = Token(TokenType.KEYWORD, "def")
        adapted = adapt_astree_tokens([regular, elem])
        self.assertGreater(len(adapted), 2)
        self.assertEqual(adapted[0], regular)

    def test_html_tokenize_requires_astree_or_succeeds(self):
        if not is_astree_available():
            with self.assertRaises(ImportError) as ctx:
                tokenize("<div>test</div>", "html")
            self.assertIn("escape-colors[syntax]", str(ctx.exception))
        else:
            tokens = tokenize("<div class=\"box\">Hello</div>", "html")
            self.assertGreater(len(tokens), 0)
            self.assertTrue(any(t.value == "div" for t in tokens))


if __name__ == "__main__":
    unittest.main()
