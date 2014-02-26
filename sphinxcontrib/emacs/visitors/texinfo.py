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
Node visitors for Texinfo output.
"""


from docutils import nodes


def visit_el_parameterlist(self, _node):
    """Process a :class:`~sphinxcontrib.emacs.nodes.el_parameterlist`."""
    self.body.append(' ')
    self.first_param = 1


def visit_el_annotation(self, node):
    """Process a :class:`~sphinxcontrib.emacs.nodes.el_annotation`.

    If the node has a ``keep_texinfo`` attribute with a truthy value, process
    the node like a :class:`~sphinx.addnodes.desc_annotation`.

    Otherwise skip the node and all its children.

    """
    if not node.get('keep_texinfo'):
        raise nodes.SkipNode
    else:
        self.visit_desc_annotation(node)


def depart_el_annotation(self, node):
    """Depart from a :class:`~sphinxcontrib.emacs.nodes.el_annotation`.

    Simply delegates to a :class:`~sphinx.addnodes.desc_annotation` node.

    """
    self.depart_desc_annotation(node)


def visit_el_parameter(self, node):
    """Process a :class:`~sphinxcontrib.emacs.nodes.el_parameter`

    Add the parameter with proper spacing to the node, and skip the children of
    the node.

    """
    if not self.first_param:
        self.body.append(' ')
    else:
        self.first_param = 0
    text = self.escape(node.astext())
    # replace no-break spaces with normal ones
    text = text.replace(u' ', '@w{ }')
    self.body.append(text)
    # Don't process the children
    raise nodes.SkipNode


def visit_el_metavariable(self, node):
    """Process a :class:`~sphinxcontrib.emacs.nodes.el_metavariable`

    Add a corresponding ``@var`` command to the body, and skip the children of
    the node.

    """
    self.body.append('@var{{{0}}}'.format(self.escape(node.astext())))
    # Do not process the children of this node, since we do not allow
    # formatting inside.
    raise nodes.SkipNode


def visit_infonode_reference(self, node):
    """Process a :class:`~sphinxcontrib.emacs.nodes.infonode_reference` node for
    Texinfo output.

    Add a corresponding ``@ref`` command to the body, and skip the children of
    the node.

    """
    infonode = node['refnode']
    manual = node['refmanual']

    name = node.astext().strip() if node['has_explicit_title'] else ''

    self.body.append('@ref{{{node},,{name},{manual}}}'.format(
        node=infonode, name=self.escape_menu(name), manual=manual))

    # Skip the node body
    raise nodes.SkipNode
