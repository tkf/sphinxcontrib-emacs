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
from docutils.statemachine import (string2lines,
                                   StateMachineWS, StateWS,
                                   UnexpectedIndentationError)
from sphinx import addnodes

from sphinxcontrib.emacs.nodes import el_metavariable


class Parser(object):
    def __init__(self, reporter):
        self.state_classes = [Body, Text]
        self.reporter = reporter

    def parse(self, inputstring):
        statemachine = StateMachineWS(state_classes=self.state_classes,
                                      initial_state='Body',
                                      debug=True)
        statemachine.reporter = self.reporter
        statemachine.inliner = Inliner()
        inputlines = string2lines(inputstring, tab_width=8,
                                  convert_whitespace=True)
        return statemachine.run(inputlines)


class Body(StateWS):
    patterns = {'text': r''}
    initial_transitions = ('text',)

    def text(self, match, _context, _next_state):
        return [match.string], 'Text', []


class Text(StateWS):
    patterns = {'text': r''}
    initial_transitions = [('text', 'Body')]

    def paragraph(self, lines, lineno=None):
        if lineno is None:
            lineno = self.state_machine.abs_line_number() - 1
        text = '\n'.join(lines).rstrip()
        children = self.state_machine.inliner.parse(text)
        para = nodes.paragraph(text, '')
        para.extend(children)
        para.source, para.line = self.state_machine.get_source_and_line(lineno)
        return para

    def eof(self, context):
        return [self.paragraph(context)]

    def blank(self, match, context, next_state):
        """End of a paragraph"""
        return [], 'Body', [self.paragraph(context)]

    def text(self, _match, context, next_state):
        msg = None
        try:
            block = self.state_machine.get_text_block(flush_left=True)
        except UnexpectedIndentationError as err:
            block, src, srcline = err.args
            msg = self.state_machine.reporter.error(
                'Unexpected indentation.', source=src, line=srcline)
        lines = context + list(block)
        paragraph = self.paragraph(lines)
        result = [paragraph]
        if msg is not None:
            result.append(msg)
        return [], next_state, result

class Inliner(object):

    inline_patterns = re.compile(
        r"""
        (?:\*(?P<emphasis>[^*]+)\*) | # An emphasis
        (?:(?P<infoprefix>[Ii]nfo\s+(?:[Nn]ode|[Aa]nchor)\s+)`(?P<infonode>[^']+)') | # An info reference
        (?:(?P<cmdprefix>[Cc]ommand\s+)`(?P<command>[^']+)') | # A command reference
        (?:(?P<funprefix>[Ff]unction\s+)`(?P<function>[^']+)') | # A function reference
        (?:(?P<optprefix>[Oo]ption\s+)`(?P<option>[^']+)') | # A option reference
        (?:(?P<varprefix>[Vv]ariable\s+)`(?P<variable>[^']+)') | # A variable reference
        (?:(?P<faceprefix>[Ff]ace\s+)`(?P<face>[^']+)') | # A face reference
        (?:(?P<symprefix>[Ss]ymbol\s+)`(?P<symbol>[^']+)') | # A literal symbol
        (?:(?P<urlprefix>URL\s+)`(?P<url>[^']+)') | # A URL reference
        (?:`(?P<symbol_reference>[^']+)') | # A generic symbol reference
        (?:\b(?P<metavar>[-_A-Z]{4,})\b) # A meta variable, as four or more uppercase letters
        """,
        re.MULTILINE | re.UNICODE | re.VERBOSE)

    def handle_emphasis(self, rawtext, value, _groups): # pylint: disable=R0201
        return [nodes.strong(rawtext, value)]

    def handle_infonode(self, rawtext, value, groups):
        return self._make_reference(rawtext, value, 'infonode',
                                    innernodeclass=nodes.emphasis,
                                    prefix=groups['infoprefix'])

    def handle_command(self, rawtext, value, groups):
        return self._make_reference(rawtext, value, ('el', 'command'),
                                    prefix=groups['cmdprefix'])

    def handle_function(self, rawtext, value, groups):
        return self._make_reference(rawtext, value, ('el', 'function'),
                                    prefix=groups['funprefix'])

    def handle_option(self, rawtext, value, groups):
        return self._make_reference(rawtext, value, ('el', 'option'),
                                    prefix=groups['optprefix'],)

    def handle_variable(self, rawtext, value, groups):
        return self._make_reference(rawtext, value, ('el', 'variable'),
                                    prefix=groups['varprefix'])

    def handle_face(self, rawtext, value, groups):
        return self._make_reference(rawtext, value, ('el', 'face'),
                                    prefix=groups['faceprefix'])

    def handle_symbol(self, rawtext, value, groups):
        return [nodes.Text(groups['symprefix'], groups['symprefix']),
                nodes.literal(rawtext, value)]

    def handle_url(self, rawtext, value, groups):
        ref = nodes.reference(rawtext, '', internal=False)
        ref['refuri'] = value
        ref += nodes.Text(value)
        return [nodes.Text(groups['urlprefix'], groups['urlprefix']), ref]

    def handle_symbol_reference(self, rawtext, value, _groups):
        return self._make_reference(rawtext, value, ('el', 'symbol'))

    def handle_metavar(self, rawtext, value, _groups):
        return [el_metavariable(rawtext, value.lower())]

    def _make_reference(self, rawtext, target, reftype,
                        innernodeclass=nodes.literal, prefix=None):
        if isinstance(reftype, basestring):
            refdomain = None
        else:
            refdomain, reftype = reftype
        ref = addnodes.pending_xref(rawtext, refwarn=False,
                                    reftype=reftype, refdomain=refdomain,
                                    refexplicit=False, reftarget=target)
        ref += innernodeclass(target, target)
        result = []
        if prefix:
            result.append(nodes.Text(prefix, prefix))
        result.append(ref)
        return result

    def parse(self, text):
        position = 0
        result_nodes = []
        for match in self.inline_patterns.finditer(text):
            if match.start() > position:
                leading_text = text[position:match.start()]
                result_nodes.append(nodes.Text(leading_text, leading_text))
            position = match.end()
            groups = match.groupdict()
            handled = False
            for key, value in groups.iteritems():
                if value is not None:
                    makenode = getattr(self, 'handle_' + key, None)
                    if makenode:
                        result_nodes.extend(makenode(match.group(0), value,
                                                     groups))
                        handled = True
            if not handled:
                raise NotImplementedError(
                    'Failed to handle a branch of the inline patterns!')
        if position < len(text):
            trailing_text = text[position:]
            result_nodes.append(nodes.Text(trailing_text, trailing_text))
        return result_nodes
