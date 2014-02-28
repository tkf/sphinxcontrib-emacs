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
from collections import namedtuple

from docutils import nodes
from docutils.statemachine import (string2lines,
                                   StateMachineWS, StateWS,
                                   UnexpectedIndentationError)
from sphinx import addnodes

from sphinxcontrib.emacs.nodes import el_metavariable


class Context(namedtuple('_Context', 'inliner reporter pending_text')):

    def with_pending_text(self, text):
        return self._replace(pending_text=text)


class Parser(object):
    def __init__(self, reporter):
        self.reporter = reporter

    def parse(self, inputstring, source_file=None, source_symbol=None):
        statemachine = StateMachineWS(initial_state='Body',
                                      state_classes=STATE_CLASSES,
                                      debug=True)
        inputlines = string2lines(inputstring, tab_width=8,
                                  convert_whitespace=True)
        if source_file and source_symbol:
            input_source = '{0}#{1}'.format(source_file, source_symbol)
        context = Context(inliner=Inliner(), reporter=self.reporter,
                          pending_text=None)
        return statemachine.run(inputlines, input_source=input_source,
                                context=context)


class DocstringState(StateWS):

    def __init__(self, state_machine, debug=False):
        if self.nested_sm_kwargs is None:
            self.nested_sm_kwargs = {'state_classes': STATE_CLASSES,
                                     'initial_state': 'Body'}
        StateWS.__init__(self, state_machine, debug)

    # Helpers

    def _nested_parse(self, block, input_offset, context):
        state_machine = self.nested_sm(
            debug=self.debug, **self.nested_sm_kwargs)
        children = state_machine.run(block, input_offset, context=context)
        return children, state_machine.abs_line_offset()

    def _nested_list_parse(self, lines, input_offset, initial_state,
                           blank_finish, blank_finish_state=None, context=None):
        sm_args = dict(self.nested_sm_kwargs)
        sm_args['initial_state'] = initial_state
        state_machine = self.nested_sm(debug=self.debug, **sm_args)
        children = state_machine.run(lines, input_offset, context=context)
        if blank_finish_state is None:
            blank_finish_state = initial_state
        state_machine.states[blank_finish_state].blank_finish = blank_finish
        blank_finish = state_machine.states[blank_finish_state].blank_finish
        state_machine.unlink()
        return children, state_machine.abs_line_offset(), blank_finish

    def _goto_line_safe(self, newline_offset):
        try:
            self.state_machine.goto_line(newline_offset)
        except EOFError:
            pass


class Body(DocstringState):
    patterns = {'text': r''}
    initial_transitions = ('text',)

    def text(self, match, context, _next_state):
        return context.with_pending_text(match.string), 'Text', []


class SpecializedBody(Body):

    # Abort all body states, to let subclasses only enable the specific states
    # allowed in a special body part

    def _invalid_input(self, _match=None, _context=None, _next_state=None):
        self.state_machine.previous_line()
        raise EOFError()

    text = _invalid_input


class DefinitionList(SpecializedBody):

    def text(self, match, context, _next_state):
        # Instead of parsing plain text as in Body, we now proceed to parse a
        # Definition
        return context.with_pending_text(match.string), 'Definition', []


class Text(DocstringState):
    patterns = {'text': r''}
    initial_transitions = [('text', 'Body')]

    # Helpers

    def _paragraph(self, text, inliner, lineno=None):
        if lineno is None:
            lineno = self.state_machine.abs_line_number() - 1
        text = text.rstrip()
        children = inliner.parse(text)
        para = nodes.paragraph(text, '')
        para.extend(children)
        para.source, para.line = self.state_machine.get_source_and_line(lineno)
        return para

    def _make_definition_list_item(self, termtext, context):
        # Get the indented block
        indented, _, line_offset, blank_finish = self.state_machine.get_indented()
        item = nodes.definition_list_item(
            termtext + '\n' + '\n'.join(indented))
        # Compensate for the term line which was already parsed
        lineno = self.state_machine.abs_line_number() - 1
        item.source, item.line = self.state_machine.get_source_and_line(lineno)
        # Parse the term line
        term = nodes.term(termtext)
        term.extend(context.inliner.parse(termtext))
        term.source, term.line = self.state_machine.get_source_and_line(lineno)
        item += term
        # And the definition
        definition = nodes.definition('')
        item += definition
        children, _ = self._nested_parse(
            indented, input_offset=line_offset,
            context=context.with_pending_text(None))
        definition.extend(children)
        return item, blank_finish

    # Whitespace transitions

    def eof(self, context):
        return [self._paragraph(context.pending_text, context.inliner)]

    def indent(self, match, context, next_state):
        definition_list = nodes.definition_list()
        item, blank_finish = self._make_definition_list_item(
            context.pending_text, context)
        definition_list += item
        offset = self.state_machine.line_offset + 1   # next line
        children, newline_offset, blank_finish = self._nested_list_parse(
            self.state_machine.input_lines[offset:],
            input_offset=self.state_machine.abs_line_offset() + 1,
            initial_state='DefinitionList',
            blank_finish=blank_finish, blank_finish_state='Definition',
            context=context)
        definition_list.extend(children)
        self._goto_line_safe(newline_offset)
        result = [definition_list]
        if not blank_finish:
            lineno = self.state_machine.abs_line_number() + 1
            reporter = context.reporter
            result.append(
                reporter.warning('Definition list ends without a blank line; '
                                 'unexpected unindent.', line=lineno))
        return context.with_pending_text(None), 'Body', result

    def blank(self, match, context, next_state):
        """End of a paragraph"""
        para = self._paragraph(context.pending_text, context.inliner)
        return context.with_pending_text(None), 'Body', [para]

    #  State transitions

    def text(self, _match, context, next_state):
        msg = None
        try:
            block = self.state_machine.get_text_block(flush_left=True)
        except UnexpectedIndentationError as err:
            block, src, srcline = err.args
            msg = self.state_machine.reporter.error(
                'Unexpected indentation.', source=src, line=srcline)
        text = context.pending_text + '\n' + '\n'.join(block)
        paragraph = self._paragraph(text, context.inliner)
        result = [paragraph]
        if msg is not None:
            result.append(msg)
        return context.with_pending_text(None), next_state, result


class SpecializedText(Text):

    # Same pattern as in SpecializedBody.  We disable all state transitions, so
    # that subclasses can re-enable and override the permitted ones.

    def eof(self, _context):
        # The current construct is incomplete
        return []

    def _invalid_input(self, _match=None, _context=None, _next_state=None):
        raise EOFError

    text = _invalid_input
    blank = _invalid_input
    indent = _invalid_input


class Definition(SpecializedText):
    def eof(self, _context):
        # If we are at EOF, when we should be in a definition, we are obviously
        # wrong, so retract and let the parent state machine reassess the
        # situation
        self.state_machine.previous_line(2)
        return []

    def indent(self, _match, context, _next_state):
        # Parse the current definition list item
        item, blank_finish = self._make_definition_list_item(
            context.pending_text, context)
        self.blank_finish = blank_finish
        return context.with_pending_text(None), 'DefinitionList', [item]


STATE_CLASSES = [
    Body, Text,                 # Basic states
    DefinitionList, Definition, # Definition lists
]


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
        (?:`(?P<literal>[^']+)') | # A literal reference
        (?:\b(?P<metavar>[-_A-Z]{4,})\b) # A meta variable, as four or more uppercase letters
        """,
        re.MULTILINE | re.UNICODE | re.VERBOSE)

    symbol_pattern = re.compile(r'^[\w/?-]+$', re.UNICODE)

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

    def handle_literal(self, rawtext, value, _groups):
        # Try to parse the nested contents of the value
        nested_nodes = self.parse(value)
        if len(nested_nodes) == 1 and isinstance(nested_nodes[0], nodes.Text):
            # There was nothing to parse, so check whether its a symbol,
            # otherwise fall back to a plain literal
            if self.symbol_pattern.match(value):
                return self._make_reference(rawtext, value, ('el', 'symbol'))
            else:
                return [nodes.literal(rawtext, value)]
        else:
            return [nodes.literal(rawtext, '', *nested_nodes)]

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
