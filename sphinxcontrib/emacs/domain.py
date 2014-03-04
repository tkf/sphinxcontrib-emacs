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


"""The domain class."""


from itertools import ifilter

from sphinx.roles import XRefRole
from sphinx.domains import Domain, ObjType
from sphinx.util.nodes import make_refnode

from sphinxcontrib.emacs import lisp
from sphinxcontrib.emacs import roles as rolefuncs
from sphinxcontrib.emacs.directives import desc
from sphinxcontrib.emacs.directives.other import RequireLibrary
from sphinxcontrib.emacs.util import make_target


class EmacsLispDomain(Domain):
    """A domain to document Emacs Lisp namespace."""

    name = 'el'
    label = 'Emacs Lisp'
    object_types = {
        'function': ObjType('function', 'function', scope='function',
                            searchprio=0),
        'macro': ObjType('macro', 'macro', scope='function',
                         searchprio=0),
        'command': ObjType('command', 'command', scope='function',
                           searchprio=1),
        'variable': ObjType('variable', 'variable', scope='variable',
                            searchprio=0),
        'option': ObjType('user option', 'option', scope='variable',
                          searchprio=1),
        'hook': ObjType('hook', 'hook', scope='variable',
                        searchprio=0),
        'face': ObjType('face', 'face', scope='face', searchprio=0),
        'cl-struct': ObjType('CL struct', 'cl-struct', scope='struct',
                             searchprio=0),
        'cl-slot': ObjType('slot', 'cl-slot', scope='function',
                           searchprio=0)}
    directives = {
        'function': desc.EmacsLispFunction,
        'macro': desc.EmacsLispFunction,
        'command': desc.EmacsLispCommand,
        'variable': desc.EmacsLispVariable,
        'option': desc.EmacsLispVariable,
        'hook': desc.EmacsLispVariable,
        'face': desc.EmacsLispFace,
        'cl-struct': desc.EmacsLispCLStruct,
        'cl-slot': desc.EmacsLispCLSlot,
        'require': RequireLibrary,
    }
    roles = {
        'symbol': XRefRole(),
        'function': XRefRole(),
        'macro': XRefRole(),
        'command': XRefRole(),
        'variable': XRefRole(),
        'option': XRefRole(),
        'hook': XRefRole(),
        'face': XRefRole(),
        'cl-struct': XRefRole(),
        'cl-slot': rolefuncs.EmacsLispSlotXRefRole(),
        # Special markup roles
        'var': rolefuncs.var,
        'varcode': rolefuncs.varcode,
    }
    indices = []

    data_version = 4
    initial_data = {
        # fullname -> scope -> (docname, objtype)
        'namespace': {},
        'features': set(),
        'environment': None,
    }

    def __init__(self, build_env):
        Domain.__init__(self, build_env)
        interpreter_env = self.data['environment']
        if interpreter_env and interpreter_env.outdated:
            # Reset the environment if it is outdated
            interpreter_env = None

        self.interpreter = lisp.AbstractInterpreter(
            build_env.config.emacs_lisp_load_path,
            env=interpreter_env)
        self.data['environment'] = self.interpreter.env

    def clear_doc(self, docname):
        namespace = self.data['namespace']
        for symbol, scopes in namespace.items():
            for scope, (object_docname, _) in scopes.items():
                if docname == object_docname:
                    del namespace[symbol][scope]

    def resolve_xref(self, env, fromdoc, builder, # pylint: disable=R0913
                     objtype, target, node, content):
        target_scopes = self.data['namespace'].get(target, {})
        obj_scope = None
        if objtype == 'symbol':
            candidate_scopes = [s for s in ['function', 'variable']
                                if s in target_scopes]
            if not candidate_scopes:
                # The reference does not refer to a defined symbol, so do not
                # consider as reference at all.  This is quite different from
                # how missing references are normally handled in Sphinx, but we
                # make this special exception to handle them like Emacs does.
                # So instead of reporting an unresolved reference, we entirely
                # drop the reference, and return just its contents.  To drop
                # the reference, we also remove the corresponding classes from
                # the content node.
                content['classes'].remove('xref')
                return content
            if len(candidate_scopes) > 1:
                message = ('Ambiguous reference to {0}, '
                           'which is both variable and function').format(target)
                env.warn(fromdoc, message, getattr(node, 'line'))
            obj_scope = candidate_scopes[0]
        else:
            # Resolve a typed reference
            obj_scope = self.object_types[objtype].attrs['scope']

        if obj_scope not in target_scopes:
            # The symbol is not present in the scope of this reference
            return None
        todoc, _ = target_scopes[obj_scope]
        return make_refnode(
            builder, fromdoc, todoc, make_target(obj_scope, target),
            content, target)

    def get_objects(self):
        for symbol, scopes in self.data['namespace'].iteritems():
            for scope, (docname, objtype) in scopes.iteritems():
                yield (symbol, symbol, objtype, docname,
                       make_target(scope, symbol),
                       self.object_types[objtype].attrs['searchprio'])
