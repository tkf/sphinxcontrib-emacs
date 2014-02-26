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


"""Directives for description of objects."""


from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.directives import ObjectDescription

from sphinxcontrib.emacs import nodes
from sphinxcontrib.emacs.util import make_target
from sphinxcontrib.emacs.lisp.docstring import Parser as DocstringParser


class EmacsLispSymbol(ObjectDescription):
    """A directive to describe an Emacs Lisp symbol."""

    option_spec = {
        'auto': directives.flag
    }
    option_spec.update(ObjectDescription.option_spec)

    @property
    def object_type(self):
        """The :class:`~sphinx.domains.ObjType` of this directive."""
        return self.env.domains[self.domain].object_types[self.objtype]

    @property
    def emacs_lisp_scope(self):
        """The scope of this object type as string."""
        return self.object_type.attrs['scope']

    def make_type_annotation(self):
        """Create the type annotation for this directive.

        Return the type annotation node, preferably a :class:`el_annotation`
        node.

        """
        type_name = self.object_type.lname.title() + ' '
        return nodes.el_annotation(type_name, type_name)

    def get_signatures(self):
        if 'auto' in self.options:
            return [self.get_auto_signature()]
        else:
            return ObjectDescription.get_signatures(self)

    def handle_signature(self, sig, signode):
        parts = sig.split()
        name = parts[0]

        annotation = self.make_type_annotation()
        if annotation:
            signode += annotation

        signode += addnodes.desc_name(name, name)

        return name

    def add_target_and_index(self, name, sig, signode):
        # We must add the scope to target names, because Emacs Lisp allows for
        # variables and commands with the same name
        targetname = make_target(self.emacs_lisp_scope, name)
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = not self.names
            self.state.document.note_explicit_target(signode)

            data = self.env.domaindata[self.domain]
            symbol_scopes = data['namespace'].setdefault(name, {})
            if self.emacs_lisp_scope in symbol_scopes:
                self.state_machine.reporter.warning(
                    'duplicate object description of %s, ' % name +
                    'other instance in ' +
                    self.env.doc2path(symbol_scopes[self.emacs_lisp_scope][0]),
                    line=self.lineno)
            symbol_scopes[self.emacs_lisp_scope] = (self.env.docname,
                                                    self.objtype)

        indextext = '{0}; Emacs Lisp {1}'.format(name, self.object_type.lname)
        self.indexnode['entries'].append(('pair', indextext, targetname, ''))

    def get_auto_signature(self):
        name = self.arguments[0].strip()
        if not self.lookup_symbol(name):
            self.state_machine.reporter.warning(
                'Undefined symbol {0}'.format(name), line=self.lineno)
        return name

    def lookup_symbol(self, name):
        env = self.env.domaindata[self.domain]['environment']
        return env.top_level.get(name)

    def get_auto_docstring(self):
        symbol = self.lookup_symbol(self.names[0])
        if symbol:
            return symbol.properties.get('variable_documentation')

    def parse_docstring(self, docstring):
        parser = DocstringParser(self.state_machine.reporter)
        return parser.parse(docstring)

    def get_auto_doc(self):
        docstring = self.get_auto_docstring()
        if not docstring:
            self.state_machine.reporter.warning(
                'no docstring for symbol {0}'.format(self.names[0]),
                line=self.lineno)
            return []
        else:
            return self.parse_docstring(docstring)

    def run(self):
        result_nodes = ObjectDescription.run(self)

        if 'auto' in self.options:
            desc_node = result_nodes[-1]
            cont_node = desc_node[-1]
            self.before_content()
            children = self.get_auto_doc() + cont_node.children
            cont_node.clear()
            cont_node.extend(children)
            self.after_content()

        return result_nodes


class EmacsLispCLStruct(EmacsLispSymbol):
    """A directive to describe a CL struct."""

    def before_content(self):
        EmacsLispSymbol.before_content(self)
        if self.names:
            self.env.temp_data['el:cl-struct'] = self.names[0]

    def after_content(self):
        EmacsLispSymbol.after_content(self)
        del self.env.temp_data['el:cl-struct']


class EmacsLispCLSlot(EmacsLispSymbol):
    """A directive to describe a slot of a CL struct.

    This directive prepends the name of the current CL struct to the slot.

    """

    def handle_signature(self, sig, signode):
        name = EmacsLispSymbol.handle_signature(self, sig, signode)
        struct = self.env.temp_data.get('el:cl-struct')
        if not struct:
            raise ValueError('Missing containing structure')
        return struct + '-' + name


class EmacsLispFunction(EmacsLispSymbol):
    """A directive to describe an Emacs Lisp function.

    This directive is different from :class:`EmacsLispSymbol` in that it
    accepts a parameter list.

    """

    def get_auto_signature(self):
        symbol = self.lookup_symbol(self.arguments[0])
        sig = self.arguments[0]
        if symbol:
            arglist = ' '.join(symbol.properties.get('function_arglist', []))
            sig += ' ' + arglist
        return sig

    def get_auto_docstring(self):
        symbol = self.lookup_symbol(self.names[0])
        if symbol:
            return symbol.properties.get('function_documentation')

    def handle_signature(self, sig, signode):
        parts = sig.split(' ')
        name = parts[0]
        arguments = parts[1:]
        name = EmacsLispSymbol.handle_signature(self, name, signode)

        paramlist = nodes.el_parameterlist(' '.join(arguments), '')
        signode += paramlist
        for arg in arguments:
            if arg.startswith('&'):
                paramlist += addnodes.desc_annotation(' ' + arg + ' ',
                                                      ' ' + arg + ' ')
            else:
                node = nodes.el_parameter(arg, arg)
                node['noemph'] = True
                paramlist += node

        return name


class EmacsLispCommand(EmacsLispSymbol):
    """A directive to describe an interactive Emacs Lisp command.

    This directive is different from :class:`EmacsLispSymbol` in that it
    describes the command with its keybindings.  For this purpose, it has two
    additional options ``:binding:`` and ``:prefix-arg``.

    The former documents key bindings for this command (in addition to ``M-x``),
    and the latter adds a prefix argument to the description of this command.

    Typically, this directive is used multiple times for the same command,
    where the first use describes the command without prefix argument, and the
    latter describes the use with prefix argument.  The latter usually has
    ``:noindex:`` set.

    """

    option_spec = {
        'binding': directives.unchanged,
        'prefix-arg': directives.unchanged,
    }
    option_spec.update(EmacsLispSymbol.option_spec)

    def get_auto_docstring(self):
        symbol = self.lookup_symbol(self.names[0])
        if symbol:
            return symbol.properties.get('function_documentation')

    def with_prefix_arg(self, binding):
        """Add the ``:prefix-arg:`` option to the given ``binding``.

        Return the complete key binding including the ``:prefix-arg:`` option
        as string.  If there is no ``:prefix-arg:``, return ``binding``.

        """
        prefix_arg = self.options.get('prefix-arg')
        return prefix_arg + ' ' + binding if prefix_arg else binding

    def make_type_annotation(self):
        keys = self.with_prefix_arg('M-x')
        node = nodes.el_annotation(keys + ' ', keys + ' ')
        node['keep_texinfo'] = True
        return node

    def run(self):
        result_nodes = EmacsLispSymbol.run(self)

        # Insert a dedicated signature for the key binding before all other
        # signatures, but only for commands.  Nothing else has key bindings.
        binding = self.options.get('binding')
        if binding:
            binding = self.with_prefix_arg(binding)
            desc_node = result_nodes[-1]
            assert isinstance(desc_node, addnodes.desc)
            signode = addnodes.desc_signature(binding, '')
            # No clue what this property is for, but ObjectDescription sets it
            # for its signatures, so we should do as well for our signature.
            signode['first'] = False
            desc_node.insert(0, signode)
            signode += addnodes.desc_name(binding, binding)

        return result_nodes
