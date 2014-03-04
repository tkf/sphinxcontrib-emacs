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


class DocstringSourceTransformer(object):
    """Transform Emacs docstring markup to ReST on source level."""

    #: Inline markup as understood by Emacs help mode.
    INLINE_MARKUP =  re.compile(
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
        (?:\b(?P<metavar>[A-Z][-_A-Z]+)\b) # A meta variable, as uppercase letters
        """, re.MULTILINE | re.UNICODE | re.VERBOSE)

    #: Regular expression for a symbol.
    #
    # The list of non-symbol characters in this pattern is taken from
    # http://definitelyaplug.b0.cx/post/emacs-reader/
    SYMBOL_PATTERN = re.compile(r'^[^\s"\';()[\]`,]+$', re.UNICODE)

    #: A standalone meta variable
    METAVAR_PATTERN = re.compile(r'\b([-_A-Z]+)\b', re.UNICODE)

    def __init__(self, min_metavars_chars=4):
        """Create a new inliner.

        ``min_metavars_chars`` is the minimum number of subsequent uppercase
        letters to consider as metavariable, to avoid marking normal acronyms
        such as XML as meta-variable.

        """
        self.min_metavars_chars = min_metavars_chars
        # The inliner to parse the contents of a literal.  Inside a literal, we
        # consider all uppercase letters as meta-variable.

    def transform(self, docstring):
        """Transform ``docstring`` into pure ReST.

        Return the transformed docstring."""
        return self.INLINE_MARKUP.sub(self._to_rst, docstring)

    def _to_rst(self, match):
        """Return the ReST replacement text for ``match``."""
        groups = match.groupdict()
        for key, value in groups.iteritems():
            if value is not None:
                transform = getattr(self, '_transform_' + key, None)
                if transform:
                    return transform(value, groups)
        # The pattern wasn't handled, which is an implementation error!
        raise NotImplementedError(
            'Failed to handle a branch of the inline patterns!')

    def _to_role(self, role, text, prefix=''):
        return '{0}:{1}:`{2}`'.format(prefix, role, text)

    # Handlers for pattern branches

    def _transform_infonode(self, value, groups):
        return self._to_role('infonode', value, prefix=groups['infoprefix'])

    def _transform_command(self, value, groups):
        return self._to_role('el:command', value, prefix=groups['cmdprefix'])

    def _transform_function(self, value, groups):
        return self._to_role('el:function', value, prefix=groups['funprefix'])

    def _transform_option(self, value, groups):
        return self._to_role('el:option', value, prefix=groups['optprefix'])

    def _transform_variable(self, value, groups):
        return self._to_role('el:variable', value, prefix=groups['varprefix'])

    def _transform_face(self, value, groups):
        return self._to_role('el:face', value, prefix=groups['faceprefix'])

    def _transform_symbol(self, value, groups):
        self._to_role('code', value, prefix=groups['symbprefix'])

    def _transform_url(self, value, groups):
        return '{0}{1}'.format(groups['urlprefix'], value)

    def _transform_literal(self, value, _groups):
        if self.SYMBOL_PATTERN.match(value):
            # A generic symbol reference
            return self._to_role('el:symbol', value)
        else:
            # A literal.  Parse and replace meta variables, and return the
            # thing
            varcode = self.METAVAR_PATTERN.sub(
                lambda m: '{{{0}}}'.format(m.group(1).lower()),
                value)
            return self._to_role('el:varcode', varcode)

    def _transform_metavar(self, value, _groups):
        if len(value) >= self.min_metavars_chars:
            return self._to_role('el:var', value.lower())
        else:
            return value


DEFAULT_DOCSTRING_TRANSFORMER = DocstringSourceTransformer()


def transform_emacs_markup_to_rst(docstring):
    """Convert all Emacs markup in ``docstring`` to ReST equivalents.

    Return the transformed docstring.

    """
    return DEFAULT_DOCSTRING_TRANSFORMER.transform(docstring)
