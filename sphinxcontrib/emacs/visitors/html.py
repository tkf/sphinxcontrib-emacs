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
Node visitors for HTML output.
"""


from sphinx import addnodes


def visit_el_parameterlist(self, node):
    """Process a :class:`~sphinxcontrib.emacs.nodes.el_parameterlist`.

    Compute the number of parameters, and set the parameter separator.

    """
    self.body.append(' ')
    self.first_param = 1
    self.optional_param_level = 0
    self.required_params_left = sum([isinstance(c, addnodes.desc_parameter)
                                     for c in node.children])
    self.param_separator = node.child_text_separator


def visit_el_metavariable(self, node):
    """Process a :class:`~sphinxcontrib.emacs.nodes.el_metavariable`.

    Add the opening ``var`` tag to the body.

    """
    self.body.append(self.starttag(node, 'var', ''))


def depart_el_metavariable(self, _node):
    """Depart from a :class:`~sphinxcontrib.emacs.nodes.el_metavariable`.

    Add the closing ``var`` tag to the body.

    """
    self.body.append('</var>')
