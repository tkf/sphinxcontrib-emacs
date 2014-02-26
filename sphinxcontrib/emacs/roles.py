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


"""
Roles for this extension.
"""


import re

from docutils import nodes, utils
from sphinx.roles import XRefRole

from sphinxcontrib.emacs.nodes import el_metavariable
from sphinxcontrib.emacs.info import INFO_RE


# pylint: disable=R0913


class EmacsLispSlotXRefRole(XRefRole):
    """A role to reference a CL slot."""

    def process_link(self, env, refnode, has_explicit_title, title, target):
        # Obtain the current structure
        current_struct = env.temp_data.get('el:cl-struct')
        omit_struct = target.startswith('~')
        target = target.lstrip('~')
        parts = target.split(' ', 1)
        # If the reference is given as "structure slot", adjust the title, and
        # reconstruct the function name
        if len(parts) > 1:
            struct, slot = parts
            target = parts.join('-')
            # If the first character is a tilde, or if there is a current
            # structure, omit the structure name
            if not has_explicit_title and (omit_struct or
                                           current_struct == struct):
                title = slot
        elif current_struct:
            # Resolve slot against the current struct
            target = current_struct + '-' + target

        return title, target


class InfoNodeXRefRole(XRefRole):
    """A role to reference a node in an Info manual."""

    innernodeclass = nodes.emphasis


    def process_link(self, env, refnode, has_explicit_title, title, target):
        # Normalize whitespace in info node targets
        target = re.sub(r'\s+', ' ', target, flags=re.UNICODE)
        refnode['has_explicit_title'] = has_explicit_title
        if not has_explicit_title:
            match = INFO_RE.match(target)
            if match:
                # Swap title and node to create a title like info does
                title = '{0}({1})'.format(match.group('node'),
                                          match.group('manual'))
        return title, target


def var(role, rawtext, text, _lineno, _inliner, _options=None, _content=None):
    """A role to indicate a meta variable."""
    return [el_metavariable(rawtext, text, role=role, classes=[role])], []


#: Regular expression to extract meta variables from text.
METAVAR_RE = re.compile('{([^}]+)}')


def varcode(role, rawtext, text, _lineno, _inliner_, _options=None,
            _content=None):
    """A role to indicate code with contained meta variables.

    Namely, all text enclosed with braces, e.g. ``{foo}``, in ``text`` is
    enclosed in a :class:`~sphinxcontrib.emacs.nodes.el_metavariable` node.

    """
    text = utils.unescape(text)
    position = 0
    node = nodes.literal(rawtext, '', role=role, classes=[role])
    for match in METAVAR_RE.finditer(text):
        if match.start() > position:
            trailing_text = text[position:match.start()]
            node += nodes.Text(trailing_text, trailing_text)
        node += el_metavariable(match.group(1), match.group(1))
        position = match.end()
    if position < len(text):
        node += nodes.Text(text[position:], text[position:])
    return [node], []
