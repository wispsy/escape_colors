"""Bounded terminal layout for caller-selected Markdown and Astree HTML trees."""

from dataclasses import dataclass
import importlib
import inspect
import re
import shutil
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

from ._codes import NAMED_CODES, RESET
from ._terminal import color_enabled
from .syntax import get_lexer, get_theme, normalize_token, style_tokens


class RenderLimitError(ValueError):
    """A selected source, tree, line or output limit was exceeded."""


@dataclass(frozen=True)
class RenderLimits:
    max_chars: int = 2_000_000
    max_nodes: int = 100_000
    max_depth: int = 64
    max_lines: int = 20_000
    max_output_chars: int = 8_000_000

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in vars(self).values()) or self.max_depth > 128:
            raise ValueError('Render limits must be positive integers with depth at most 128.')


def _clean(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return ''.join(char if char in '\n\t' or ord(char) >= 32 and not 127 <= ord(char) <= 159
                   else '\\x' + format(ord(char), '02x') for char in text)


def _width(text):
    return sum(0 if unicodedata.combining(char) or char == '\u200d' else 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1 for char in text)


def _destination(value, schemes):
    if not isinstance(value, str) or not value or len(value) > 8192:
        return None
    decoded = unquote(value)
    if any(ord(char) < 32 or 127 <= ord(char) <= 159 or char == '\\' for char in decoded + value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in (*schemes, '') or value.startswith('//') or parsed.username is not None or parsed.password is not None:
            return None
        if parsed.scheme in ('http', 'https') and not parsed.hostname:
            return None
    except ValueError:
        return None
    return value


@dataclass(frozen=True)
class _Span:
    text: str
    style: str = ''
    link: str | None = None


class _Writer:
    def __init__(self, width, limits):
        self.width, self.limits = width, limits
        self.lines, self.line = [], []
        self.column, self.body, self.space, self.count = 0, False, False, 0
        self.prefix = ''

    def _append(self, text, style='', link=None):
        self.count += len(text)
        if self.count > self.limits.max_output_chars:
            raise RenderLimitError('Visible output exceeds max_output_chars.')
        if self.line and (self.line[-1].style, self.line[-1].link) == (style, link):
            previous = self.line[-1]
            self.line[-1] = _Span(previous.text + text, style, link)
        else:
            self.line.append(_Span(text, style, link))
        self.column += _width(text)

    def _begin(self):
        if not self.line:
            prefix = self.prefix
            while _width(prefix) > self.width - 2:
                prefix = prefix[:-1]
            if prefix:
                self._append(prefix)

    def newline(self, *, force=False):
        if self.body or force:
            self.lines.append(self.line)
            if len(self.lines) > self.limits.max_lines:
                raise RenderLimitError('Output exceeds max_lines.')
        self.line, self.column, self.body, self.space = [], 0, False, False

    def blank(self):
        self.newline()
        if self.lines and self.lines[-1]:
            self.lines.append([])
            if len(self.lines) > self.limits.max_lines:
                raise RenderLimitError('Output exceeds max_lines.')

    def write(self, text, style='', link=None, *, preserve=False):
        for token in re.findall(r'\S+|\s+', _clean(text).expandtabs(4)):
            if not preserve and token.isspace():
                self.space = self.body
                continue
            if not preserve:
                self._begin()
                if self.body and self.column + int(self.space) + _width(token) > self.width:
                    self.newline()
                if self.space and self.body:
                    self._append(' ')
                self.space = False
            for char in token:
                if char == '\n':
                    self.newline(force=True)
                    continue
                self._begin()
                if self.body and self.column + _width(char) > self.width:
                    self.newline()
                    self._begin()
                self._append(char, style, link)
                self.body = True

    def finish(self, *, color=False, hyperlinks=False):
        self.newline()
        while self.lines and not self.lines[-1]:
            self.lines.pop()
        pieces, count = [], 0
        for number, line in enumerate(self.lines):
            if number:
                pieces.append('\n')
                count += 1
            for span in line:
                value = span.text
                if color and span.style:
                    if not re.fullmatch(r'(?:\x1b\[[0-9;]*m)*', span.style):
                        raise ValueError('Terminal themes must contain numeric SGR styles only.')
                    value = span.style + value + RESET
                if hyperlinks and span.link:
                    value = '\x1b]8;;' + span.link + '\x1b\\' + value + '\x1b]8;;\x1b\\'
                count += len(value)
                if count > self.limits.max_output_chars:
                    raise RenderLimitError('Encoded output exceeds max_output_chars.')
                pieces.append(value)
        return ''.join(pieces)


def _tree(source, limits):
    try:
        astree = importlib.import_module('astree')
    except ImportError as error:
        raise ImportError('Terminal Markdown needs escape-colors[markdown].') from error
    if isinstance(source, str):
        if len(source) > limits.max_chars:
            raise RenderLimitError('HTML exceeds max_chars.')
        try:
            source = astree.Document.from_html(source, max_chars=limits.max_chars,
                                               max_nodes=limits.max_nodes, max_depth=limits.max_depth)
        except astree.ParseLimitError as error:
            raise RenderLimitError('HTML exceeds the selected tree limits.') from error
    if not isinstance(source, astree.Node):
        raise TypeError('Select HTML text or an Astree Document/Node.')
    pending, seen, chars = [(source, 0)], set(), 0
    while pending:
        node, depth = pending.pop()
        if id(node) in seen:
            raise RenderLimitError('Input nodes must form a tree.')
        seen.add(id(node))
        chars += len(node.data) + sum(len(key) + len(value or '') for key, value in node.attrs.items())
        if depth > limits.max_depth or len(seen) > limits.max_nodes or chars > limits.max_chars:
            raise RenderLimitError('Tree exceeds the selected limits.')
        pending.extend((child, depth + 1) for child in node.children)
    return source


class _Layout:
    def __init__(self, writer, theme, schemes, hyperlinks):
        self.writer, self.theme, self.schemes, self.hyperlinks = writer, theme, schemes, hyperlinks

    def children(self, node, style='', link=None, *, inline=False):
        for child in node.children:
            self.visit(child, style, link, inline=inline)

    def table(self, node):
        writer = self.writer
        rows = []
        for child in node.children:
            candidates = (child,) if child.tag == 'tr' else child.children if child.tag in ('thead', 'tbody', 'tfoot') else ()
            for row in candidates:
                cells = [cell for cell in row.children if cell.tag in ('td', 'th')]
                if cells:
                    rows.append(cells)
        if not rows:
            return
        count = max(len(row) for row in rows)
        if count > 64:
            raise RenderLimitError('Tables allow at most 64 columns.')
        values = [[re.sub(r'\s+', ' ', _clean(cell.get_text(' ', strip=True))) for cell in row] for row in rows]
        available = max(2, writer.width - _width(writer.prefix))
        writer.blank()
        if count * 3 + (count - 1) * 3 > available:
            for row in values:
                writer.write(' | '.join(row))
                writer.newline()
        else:
            widths = [max(3, max((_width(row[index]) for row in values if index < len(row)), default=0)) for index in range(count)]
            while sum(widths) + 3 * (count - 1) > available:
                index = max(range(count), key=widths.__getitem__)
                widths[index] -= 1
            for position, row in enumerate(values):
                wrapped = []
                for index in range(count):
                    cell = _Writer(widths[index], writer.limits)
                    cell.write(row[index] if index < len(row) else '')
                    wrapped.append(cell.finish().split('\n'))
                for line in range(max(map(len, wrapped))):
                    pieces = []
                    for index, parts in enumerate(wrapped):
                        value = parts[line] if line < len(parts) else ''
                        padding = ' ' * max(0, widths[index] - _width(value))
                        align = index < len(rows[position]) and 'text-align: right' in (rows[position][index].attrs.get('style') or '')
                        pieces.append(padding + value if align else value + padding)
                    writer.write(' | '.join(pieces), NAMED_CODES['bold'] if position == 0 else '', preserve=True)
                    writer.newline()
                if position == 0 and any(cell.tag == 'th' for cell in rows[0]):
                    writer.write('-+-'.join('-' * width for width in widths), preserve=True)
                    writer.newline()
        writer.blank()

    def visit(self, node, style='', link=None, *, inline=False):
        writer, tag = self.writer, node.tag
        if node.kind == 'text':
            writer.write(node.data, style, link)
            return
        if node.kind not in ('document', 'element') or tag in ('script', 'style', 'head', 'template', 'svg') or 'hidden' in node.attrs or node.attrs.get('aria-hidden') == 'true':
            return
        if tag == 'table':
            self.table(node)
            return
        if tag == 'pre':
            writer.blank()
            prefix, writer.prefix = writer.prefix, writer.prefix + '    '
            code = next((child for child in node.children if child.tag == 'code'), node)
            text = _clean(code.get_text())
            language = next((name[9:] for name in (code.attrs.get('class') or '').split() if name.startswith('language-')), '')
            try:
                lexer = get_lexer(language)
            except ValueError:
                writer.write(text, preserve=True)
            else:
                tokens = []
                for token in lexer(text):
                    if len(tokens) >= writer.limits.max_nodes:
                        raise RenderLimitError('Code tokens exceed max_nodes.')
                    tokens.append(normalize_token(token))
                if ''.join(token.value for token in tokens) != text:
                    writer.write(text, preserve=True)
                else:
                    for selected, value in style_tokens(tokens, self.theme):
                        writer.write(value, selected, preserve=True)
            writer.newline()
            writer.prefix = prefix
            writer.blank()
            return
        if tag in ('ul', 'ol'):
            writer.newline()
            start = node.attrs.get('start') or '1'
            if tag == 'ol' and (not start.isascii() or not start.isdigit() or len(start) > 9):
                raise RenderLimitError('Ordered list starts must be bounded nonnegative integers.')
            position = int(start) if tag == 'ol' else 0
            for child in node.children:
                if child.tag != 'li':
                    continue
                marker = str(position) + '. ' if tag == 'ol' else '- '
                writer.newline()
                old = writer.prefix
                writer.write(marker, preserve=True)
                writer.prefix = old + ' ' * len(marker)
                self.children(child, style, link, inline=True)
                writer.newline()
                writer.prefix = old
                position += 1
            writer.blank()
            return
        if tag == 'blockquote':
            writer.blank()
            old, writer.prefix = writer.prefix, writer.prefix + '> '
            self.children(node, style, link)
            writer.newline()
            writer.prefix = old
            writer.blank()
            return
        if tag == 'hr':
            writer.blank()
            writer.write('-' * max(1, writer.width - _width(writer.prefix)), preserve=True)
            writer.blank()
            return
        if tag == 'br':
            writer.newline(force=True)
            return
        if tag == 'input':
            if node.attrs.get('type') == 'checkbox':
                writer.write('[x] ' if 'checked' in node.attrs else '[ ] ')
            return
        if tag == 'img':
            label = node.attrs.get('alt') or 'image'
            target = _destination(node.attrs.get('src'), self.schemes)
            writer.write('[' + label + ']' + (' (' + target + ')' if target else ''), NAMED_CODES['dim'])
            return
        if tag == 'a':
            target = _destination(node.attrs.get('href'), self.schemes)
            active = target if target and urlsplit(target).scheme in self.schemes and self.hyperlinks else None
            self.children(node, style + NAMED_CODES['cyan'] + NAMED_CODES['underline'], active, inline=True)
            label = re.sub(r'\s+', ' ', node.get_text()).strip()
            if target and active is None and target != label:
                writer.write(' (' + target + ')', NAMED_CODES['dim'])
            return
        styles = {'strong': 'bold', 'b': 'bold', 'em': 'italic', 'i': 'italic', 's': 'strike', 'del': 'strike',
                  'code': 'cyan', 'mark': 'bg_yellow', 'u': 'underline'}
        if tag in styles:
            style += NAMED_CODES[styles[tag]]
        heading = tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
        block = heading or tag in ('p', 'div', 'article', 'section', 'header', 'footer', 'dl', 'dt', 'dd')
        if block and not inline:
            writer.blank()
        if heading:
            style += NAMED_CODES['bold'] + NAMED_CODES['bright_cyan']
        self.children(node, style, link, inline=inline)
        if block:
            writer.newline() if inline else writer.blank()


def render_html(source, *, width=80, color=False, hyperlinks=False, theme='default',
                allowed_schemes=('http', 'https', 'mailto'), limits=None):
    """Return terminal text for HTML or an Astree tree without side effects."""
    limits = limits if limits is not None else RenderLimits()
    if (not isinstance(limits, RenderLimits) or type(width) is not int or not 8 <= width <= 400
            or type(color) is not bool or type(hyperlinks) is not bool or isinstance(allowed_schemes, str)):
        raise ValueError('Select render limits, width 8–400 and explicit boolean styles/links.')
    schemes = tuple(allowed_schemes)
    if any(type(name) is not str or not re.fullmatch(r'[a-z][a-z0-9+.-]*', name) for name in schemes):
        raise ValueError('Allowed hyperlink schemes must be explicit lowercase names.')
    selected_theme = get_theme(theme)
    tree = _tree(source, limits)
    writer = _Writer(width, limits)
    _Layout(writer, selected_theme, schemes, hyperlinks).visit(tree)
    return writer.finish(color=color, hyperlinks=hyperlinks)


def render_markdown(source, *, parser=None, limits=None, **options):
    """Render Markdown with parse-md's extended profile or a selected parser."""
    limits = limits if limits is not None else RenderLimits()
    if not isinstance(source, str):
        raise TypeError('Markdown source must be text.')
    if not isinstance(limits, RenderLimits) or len(source) > limits.max_chars:
        raise RenderLimitError('Markdown exceeds the selected source limit.')
    if parser is None:
        try:
            parse_md = importlib.import_module('parse_md')
        except ImportError as error:
            raise ImportError('Default Markdown parsing needs escape-colors[markdown].') from error
        document = parse_md.render(source, dialect=parse_md.EXTENDED,
                                   options=parse_md.ParseOptions(max_characters=limits.max_chars,
                                                                max_nodes=limits.max_nodes, max_nesting=min(64, limits.max_depth)))
    else:
        if not callable(parser):
            raise TypeError('Select a synchronous Markdown parser callable.')
        document = parser(source)
    if inspect.isawaitable(document):
        if inspect.iscoroutine(document):
            document.close()
        raise TypeError('Terminal Markdown parser callbacks must be synchronous.')
    return render_html(getattr(document, 'html', document), limits=limits, **options)


def markdown_print(source, *, parser=None, file=None, width=None, color=None, hyperlinks=False,
                   end='\n', flush=False, **options):
    """Print buffered Markdown using destination-aware styles and optional links."""
    if type(end) is not str or type(flush) is not bool or type(hyperlinks) is not bool:
        raise TypeError('Select a string ending and boolean printing options.')
    stream = sys.stdout if file is None else file
    if stream is None:
        return
    enabled = color_enabled(stream, color)
    selected_width = width if width is not None else min(400, max(8, shutil.get_terminal_size((80, 24)).columns))
    rendered = render_markdown(source, parser=parser, width=selected_width, color=enabled,
                               hyperlinks=hyperlinks and enabled, **options)
    print(rendered, file=stream, end=_clean(end), flush=flush)


__all__ = ['RenderLimitError', 'RenderLimits', 'render_html', 'render_markdown', 'markdown_print']
