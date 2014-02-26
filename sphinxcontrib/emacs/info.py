# -*- coding: utf-8 -*-
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
Info manual support.
"""

import re

from docutils import nodes

from sphinxcontrib.emacs.nodes import infonode_reference


#: Regular expression object to parse the contents of an Info reference role.
INFO_RE = re.compile(r'^\((?P<manual>.+)\)(?P<node>.+?)$')


#: Web URLs of Info manuals.
INFO_MANUAL_URLS = {
    'emacs': 'http://www.gnu.org/software/emacs/manual/html_node/emacs/{node}.html#{node}',
    'elisp': 'http://www.gnu.org/software/emacs/manual/html_node/elisp/{node}.html#{node}',
    'cl': 'http://www.gnu.org/software/emacs/manual/html_node/cl/{node}.html#{node}',
}


def resolve_info_references(app, _env, refnode, contnode):
    """Resolve Info references.

    Process all :class:`~sphinx.addnodes.pending_xref` nodes whose ``reftype``
    is ``infonode``.

    If the current output format is Texinfo, replace the
    :class:`~sphinx.addnodes.pending_xref` with a :class:`infonode_reference`
    node, which is then processed by the Texinfo writer.

    For all other output formats, replace the pending reference with a
    :class:`~docutils.nodes.reference` node, which references the corresponding
    web URL, as in :data:`INFO_MANUAL_URLS`.

    """
    if refnode['reftype'] != 'infonode':
        return None

    target = refnode['reftarget']
    match = INFO_RE.match(target)
    if not match:
        app.env.warn(refnode.source, 'Invalid info target: {0}'.format(target),
                     refnode.line)
        return contnode

    manual = match.group('manual')
    node = match.group('node')

    if app.builder.format == 'texinfo':
        reference = infonode_reference('', '')
        reference['refnode'] = node
        reference['refmanual'] = manual
        reference['has_explicit_title'] = refnode['has_explicit_title']
        reference.append(contnode)
        return reference
    else:
        base_uri = INFO_MANUAL_URLS.get(manual)
        if not base_uri:
            message = 'Cannot resolve info manual {0}'.format(manual)
            app.env.warn(refnode.source, message, refnode.line)
            return contnode
        else:
            reference = nodes.reference('', '', internal=False)
            reference['refuri'] = base_uri.format(node=node.replace(' ', '-'))
            reference['reftitle'] = target
            reference.append(contnode)
            return reference
