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
A Sphinx extension to document Emacs projects.
"""


from __future__ import unicode_literals

from docutils import nodes as corenodes
from sphinx import addnodes

from sphinxcontrib.emacs import nodes, visitors
from sphinxcontrib.emacs.roles import InfoNodeXRefRole
from sphinxcontrib.emacs.domain import EmacsLispDomain
from sphinxcontrib.emacs.info import resolve_info_references
from sphinxcontrib.emacs.lisp import AbstractInterpreter


__version__ = '0.1'


def setup(app):
    """Initialize this extension.

    ``app`` is the Sphinx application object to add this extension to.

    """
    app.require_sphinx('1.2')
    # Emacs description units
    app.add_domain(EmacsLispDomain)
    # Auto doc support
    app.add_config_value('emacs_lisp_load_path', [], 'env')
    app.add_config_value('emacs_lisp_debug_docstring_parser', False, '')
    # Texinfo references
    app.add_role('infonode', InfoNodeXRefRole())
    app.connect(str('missing-reference'), resolve_info_references)
    # Nodes
    app.add_node(nodes.el_parameterlist,
                 html=(visitors.html.visit_el_parameterlist,
                       visitors.noop),
                 latex=visitors.delegate(addnodes.desc_parameterlist),
                 texinfo=(visitors.texinfo.visit_el_parameterlist,
                          visitors.noop))
    app.add_node(nodes.el_annotation,
                 html=visitors.delegate(addnodes.desc_annotation),
                 latex=visitors.delegate(addnodes.desc_annotation),
                 texinfo=(visitors.texinfo.visit_el_annotation,
                          visitors.texinfo.depart_el_annotation))
    app.add_node(nodes.el_parameter,
                 html=visitors.delegate(addnodes.desc_parameter),
                 latex=visitors.delegate(addnodes.desc_parameter),
                 texinfo=(visitors.texinfo.visit_el_parameter, None))
    app.add_node(nodes.el_metavariable,
                 html=(visitors.html.visit_el_metavariable,
                       visitors.html.depart_el_metavariable),
                 latex=visitors.delegate(corenodes.emphasis),
                 texinfo=(visitors.texinfo.visit_el_metavariable, None))
    app.add_node(nodes.infonode_reference,
                 texinfo=(visitors.texinfo.visit_infonode_reference, None))
