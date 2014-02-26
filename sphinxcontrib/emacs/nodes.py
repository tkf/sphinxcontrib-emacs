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
Additional nodes of this extension.
"""


from __future__ import unicode_literals

from docutils import nodes
from sphinx import addnodes


# Node classes have a special nameing
# pylint: disable=C0103


class el_parameterlist(addnodes.desc_parameterlist):
    """A container node for the parameter list of a Emacs Lisp function."""
    child_text_separator = ' '


class el_annotation(addnodes.desc_annotation):
    """A node for the type annotation of Emacs Lisp namespace."""
    pass


class el_parameter(addnodes.desc_parameter):
    """A node for parameters of Emacs Lisp functions."""
    pass


class el_metavariable(nodes.emphasis):
    """A node for a meta variable."""
    pass


class infonode_reference(nodes.reference):
    """A reference node to cross-reference an Info manual node."""
    pass
