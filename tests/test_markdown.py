import importlib.util
import io
import os
import re
import unittest
from unittest.mock import patch

from escape_colors import strip_ansi
from escape_colors.markdown import RenderLimitError, RenderLimits, markdown_print, render_html, render_markdown

_AVAILABLE = importlib.util.find_spec('astree') is not None and importlib.util.find_spec('parse_md') is not None


@unittest.skipUnless(_AVAILABLE, 'optional Markdown profile is not installed')
class MarkdownTests(unittest.TestCase):
    def test_default_parser_headings_inline_styles_and_literal_notation(self):
        source = '# Title\n\nA **bold** and *italic* paragraph with red(literal).\n'
        plain = render_markdown(source)
        styled = render_markdown(source, color=True)
        self.assertIn('Title\n\nA bold and italic paragraph with red(literal).', plain)
        self.assertEqual(strip_ansi(styled), plain)
        self.assertIn('\x1b[1m', styled)
        self.assertIn('\x1b[3m', styled)

    def test_lists_quotes_tasks_and_rules(self):
        source = '3. first\n4. second\n\n> quoted\n> text\n\n- [x] done\n- [ ] todo\n\n---\n'
        value = render_markdown(source, width=30)
        self.assertIn('3. first\n4. second', value)
        self.assertIn('> quoted\n> text', value)
        self.assertIn('- [x] done', value)
        self.assertIn('- [ ] todo', value)
        self.assertIn('-'*30, value)

    def test_python_json_and_unknown_code_preserve_literal_text(self):
        for language, source in (('python','def hi():\n    return "red(x)"\n'),
                                 ('json','{"value": true}\n'),('unknown','literal <tag> red(x)\n')):
            markdown = '```'+language+'\n'+source+'```\n'
            plain = render_markdown(markdown, width=80)
            styled = render_markdown(markdown, color=True)
            self.assertEqual(strip_ansi(styled), plain)
            self.assertIn(source.splitlines()[0], plain)
            self.assertNotIn('<code', plain)
            if language != 'unknown':
                self.assertIn('\x1b[', styled)

    def test_table_layout_and_narrow_fallback(self):
        source = '| Name | Count |\n| :--- | ---: |\n| café | 12 |\n| long value that wraps | 3 |\n'
        for width in (16,40):
            value = render_markdown(source,width=width)
            self.assertIn('Name',value)
            self.assertIn('Count',value)
            self.assertIn('café',value)
            self.assertTrue(all(len(line)<=width for line in value.splitlines()),value)

    def test_tree_based_html_lexer_cannot_rewrite_fenced_source(self):
        source='<br data-x="literal">\n<!-- comment -->\n'
        markdown='```html\n'+source+'```\n'
        output=render_markdown(markdown,color=True)
        self.assertIn('<br data-x="literal">',strip_ansi(output))
        self.assertNotIn('</br>',strip_ansi(output))

    def test_width_cjk_combining_long_words_and_nested_containers(self):
        from escape_colors.markdown import _width
        value=render_markdown('> - 漢字 café e\u0301 '+('word'*20)+'\n',width=20)
        self.assertIn('漢字',value)
        self.assertIn('e\u0301',value)
        self.assertTrue(all(_width(line)<=20 for line in value.splitlines()),value)

    def test_links_plain_targets_and_opt_in_osc(self):
        source='[label](https://example.com/path) and [local](/notes/a)'
        plain=render_markdown(source)
        self.assertIn('label (https://example.com/path)',plain)
        self.assertIn('local (/notes/a)',plain)
        styled=render_markdown(source,hyperlinks=True)
        self.assertIn('\x1b]8;;https://example.com/path\x1b\\',styled)
        self.assertNotIn('\x1b]8;;/notes/a',styled)
        self.assertNotIn('\x1b',plain)

    def test_explicit_custom_schemes_and_unsafe_destinations(self):
        html='<p><a href="pnbp:///safe">note</a> <a href="javascript:alert(1)">unsafe</a></p>'
        self.assertNotIn('pnbp:',render_html(html,hyperlinks=True))
        value=render_html(html,hyperlinks=True,allowed_schemes=('pnbp',))
        self.assertIn('\x1b]8;;pnbp:///safe',value)
        self.assertNotIn('javascript:',value)
        self.assertNotIn('\x1b]8;;javascript',value)

    def test_raw_controls_hidden_subtrees_and_styles_are_sanitized(self):
        value=render_html('<script>hidden()</script><style>secret</style><p>safe\x1b]52;;payload\x07\x9b31m</p><span hidden>hidden text</span>')
        self.assertNotIn('\x1b',value)
        self.assertNotIn('\x07',value)
        self.assertNotIn('\x9b',value)
        self.assertNotIn('hidden()',value)
        self.assertNotIn('secret',value)
        self.assertNotIn('hidden text',value)
        self.assertIn('\\x1b]52;;payload\\x07\\x9b31m',value)
        from escape_colors.syntax import Theme
        bad=Theme('bad',{'keyword':'\x1b]52;;bad\x07'})
        with self.assertRaises(ValueError):
            render_markdown('```python\ndef hi(): pass\n```',theme=bad,color=True)

    def test_source_tree_depth_line_and_encoded_output_limits(self):
        for call in (lambda:render_markdown('x'*11,limits=RenderLimits(max_chars=10)),
                     lambda:render_html('<b>'*10+'x'+'</b>'*10,limits=RenderLimits(max_depth=4)),
                     lambda:render_html('<p>a</p><p>b</p>',limits=RenderLimits(max_nodes=2)),
                     lambda:render_html('<pre>a\nb\nc</pre>',limits=RenderLimits(max_lines=2)),
                     lambda:render_html('<b>text</b>',color=True,limits=RenderLimits(max_output_chars=5))):
            with self.assertRaises(RenderLimitError):
                call()

    def test_astree_inputs_are_read_only_and_callback_parser_is_selected_once(self):
        import astree
        document=astree.Document.from_html('<h1>Heading</h1><p>Body</p>')
        before=[(id(node),node.kind,node.tag,node.data,tuple(node.attrs.items()),tuple(map(id,node.children))) for node in document.descendants()]
        self.assertEqual(render_html(document),'Heading\n\nBody')
        calls=[]
        value=render_markdown('source',parser=lambda source:(calls.append(source),document)[1])
        self.assertEqual(calls,['source'])
        self.assertEqual(value,'Heading\n\nBody')
        self.assertEqual(before,[(id(node),node.kind,node.tag,node.data,tuple(node.attrs.items()),tuple(map(id,node.children))) for node in document.descendants()])

    def test_print_destination_no_color_redirected_output_and_literal_markup(self):
        stream=io.StringIO()
        markdown_print('**bold** red(literal)',file=stream)
        self.assertEqual(stream.getvalue(),'bold red(literal)\n')
        class TTY(io.StringIO):
            def isatty(self):
                return True
        stream=TTY()
        with patch.dict(os.environ,{'NO_COLOR':'1'}):
            markdown_print('[link](https://example.com)',file=stream,hyperlinks=True)
        self.assertNotIn('\x1b',stream.getvalue())
        stream=io.StringIO()
        markdown_print('**bold**',file=stream,color=True,end='!')
        self.assertIn('\x1b[1m',stream.getvalue())
        self.assertTrue(stream.getvalue().endswith('!'))

    def test_async_or_invalid_parser_results_fail_before_printing(self):
        async def parser(source):
            return '<p>async</p>'
        for selected in (parser,lambda source:object()):
            stream=io.StringIO()
            with self.assertRaises(TypeError):
                markdown_print('text',parser=selected,file=stream)
            self.assertEqual(stream.getvalue(),'')


class OptionalMarkdownTests(unittest.TestCase):
    def test_absent_optional_packages_report_the_extra_without_global_imports(self):
        with patch('importlib.import_module',side_effect=ImportError('missing')):
            with self.assertRaisesRegex(ImportError,r'escape-colors\[markdown\]'):
                render_html('<p>text</p>')
            with self.assertRaisesRegex(ImportError,r'escape-colors\[markdown\]'):
                render_markdown('text')

    def test_configuration_rejects_invalid_widths_and_limits(self):
        for width in (0,True,7,401):
            with self.assertRaises(ValueError):
                render_html('text',width=width)
        for options in ({'max_depth':129},{'max_nodes':0},{'max_chars':True}):
            with self.assertRaises(ValueError):
                RenderLimits(**options)


if __name__=='__main__':
    unittest.main()
