# -*- coding: utf-8; -*-
# Copyright (c) 2014 Sebastian Wiesner <lunaryorn@gmail.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Docstring parsing."""


import re

from docutils import nodes
from docutils.transforms import Transform
from sphinx.addnodes import pending_xref

from sphinxcontrib.emacs.nodes import el_metavariable


class EmacsHelpModeMarkup(Transform):
    """Transform inline Emacs docstring markup in text nodes."""

    #: Inline markup as understood by Emacs help mode.
    INLINE_MARKUP = re.compile(
        r"""
        (?:(?P<infoprefix>[Ii]nfo\s+(?:[Nn]ode|[Aa]nchor)\s+)`(?P<infonode>[^']+)') | # An info reference
        (?:(?P<cmdprefix>[Cc]ommand\s+)`(?P<command>[^']+)') | # A command reference
        (?:(?P<funprefix>[Ff]unction\s+)`(?P<function>[^']+)') | # A function reference
        (?:(?P<optprefix>[Oo]ption\s+)`(?P<option>[^']+)') | # A option reference
        (?:(?P<varprefix>[Vv]ariable\s+)`(?P<variable>[^']+)') | # A variable reference
        (?:(?P<faceprefix>[Ff]ace\s+)`(?P<face>[^']+)') | # A face reference
        (?:(?P<symprefix>[Ss]ymbol\s+)`(?P<symbol>[^']+)') | # A literal symbol
        (?:(?P<urlprefix>URL\s+)`(?P<url>[^']+)') | # A URL reference
        (?:`(?P<literal>[^']+)') | # A literal reference
        (?:\b(?P<metavar>[A-Z][-_A-Z]{3,})\b) # A meta variable, as four or more uppercase letters
        """, re.MULTILINE | re.UNICODE | re.VERBOSE)

    #: Regular expression for a symbol.
    #
    # The list of non-symbol characters in this pattern is taken from
    # http://definitelyaplug.b0.cx/post/emacs-reader/
    SYMBOL_PATTERN = re.compile(r'^[^\s"\';()[\]`,]+$', re.UNICODE)

    #: A standalone meta variable
    METAVAR_PATTERN = re.compile(r'\b([A-Z][-_A-Z]*)\b', re.UNICODE)

    #: Literal node classes
    LITERAL_NODE = (nodes.literal, nodes.FixedTextElement)

    def apply(self):
        root = self.startnode or self.document
        for node in root.traverse(nodes.Text):
            if isinstance(node.parent, self.LITERAL_NODE):
                # Ignore inline and block literal text
                continue
            new_nodes = self._transform_text(unicode(node))
            node.parent.replace(node, new_nodes)

    def _transform_text(self, text):
        """Transform inline markup in ``text``.

        Return a list of all nodes parsed from ``text``.

        """
        new_nodes = []
        position = 0
        for match in self.INLINE_MARKUP.finditer(text):
            if match.start() > position:
                # Extract leading text
                leading = text[position:match.start()]
                new_nodes.append(nodes.Text(leading, leading))
            new_nodes.extend(self._transform_match(match,))
            position = match.end()
        if position < len(text):
            new_nodes.append(nodes.Text(text[position:], text[position:]))
        return new_nodes

    def _transform_match(self, match):
        """Transform ``match``.

        Delegate to the transformer method for the matched group, and return a
        list of nodes.

        """
        for key, value in match.groupdict().iteritems():
            if value is not None:
                transform = getattr(self, '_transform_' + key, None)
                if transform:
                    return transform(value, match)
        # The pattern wasn't handled, which is an implementation error!
        raise NotImplementedError(
            'Failed to handle a branch of the inline patterns!')

    # Utilities

    def _to_reference(self, reftype, reftarget,
                      innernodecls=nodes.literal, prefix=None):
        parts = reftype.split(':', 1)
        if len(parts) > 1:
            refdomain, reftype = parts
        else:
            refdomain = None
        rawtext = "`'".format(reftarget)
        ref = pending_xref(rawtext, refwarn=False,
                           reftype=reftype, refdomain=refdomain,
                           refexplicit=False, reftarget=reftarget)
        ref += innernodecls(reftarget, reftarget)
        result = []
        if prefix:
            result.append(nodes.Text(prefix, prefix))
        result.append(ref)
        return result

    # Handlers for pattern branches

    def _transform_infonode(self, value, match):
        return self._to_reference('infonode', value,
                                  innernodecls=nodes.emphasis,
                                  prefix=match.group('infoprefix'))

    def _transform_command(self, value, match):
        return self._to_reference(
            'el:command', value, prefix=match.group('cmdprefix'))

    def _transform_function(self, value, match):
        return self._to_reference(
            'el:function', value, prefix=match.group('funprefix'))

    def _transform_option(self, value, match):
        return self._to_reference(
            'el:option', value, prefix=match.group('optprefix'))

    def _transform_variable(self, value, match):
        return self._to_reference(
            'el:variable', value, prefix=match.group('varprefix'))

    def _transform_face(self, value, match):
        return self._to_reference(
            'el:face', value, prefix=match.group('faceprefix'))

    def _transform_symbol(self, value, match):
        prefix = match.group('symprefix')
        return [nodes.Text(prefix, prefix),
                nodes.literal("`{0}'".format(value), value)]

    def _transform_url(self, value, match):
        prefix = match.group('urlprefix')
        return [nodes.Text(prefix, prefix),
                nodes.reference(value, value, refuri=value, internal=False)]

    def _transform_literal(self, text, match):
        if self.SYMBOL_PATTERN.match(text):
            return [self._to_reference('el:symbol', text)]
        else:
            node = nodes.literal(text, '')
            position = 0
            # Substitute meta variables in literal code
            for match in self.METAVAR_PATTERN.iterfind(text):
                if position < match.start():
                    leading = text[position:match.start()]
                    node += nodes.Text(leading, leading)
                node += el_metavariable(match.group(0), match.group(0).lower())
                position = match.end()
            if position < len(text):
                node += nodes.Text(text[position:], text[position:])
            return [node]

    def _transform_metavar(self, value, _match):
        return [el_metavariable(value, value.lower())]
