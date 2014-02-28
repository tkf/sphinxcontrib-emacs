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


from docutils import nodes as corenodes
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

    docstring_property = 'variable-documentation'

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

        By default, return the localized title of the object type corresponding
        to this directive.

        """
        type_name = self.object_type.lname.title() + ' '
        return nodes.el_annotation(type_name, type_name)

    def get_signatures(self):
        """Get all signatures of the current description unit.

        If the symbol is auto-documented, get the source code signature via
        :meth:`get_auto_signature`.  Otherwise, fall back to Sphinx' standard
        means of parsing signatures.

        Return a list of all signatures.

        """
        symbol = self.lookup_auto_symbol(self.arguments[0])
        if symbol:
            return [self.get_auto_signature(symbol)]
        else:
            return ObjectDescription.get_signatures(self)

    def handle_signature(self, signature, signode):
        """Handle a single ``signature``.

        Extract the symbol name from ``signature``, and add it to the
        ``signode``, and prepend the type annotation from
        :meth:`make_type_annotation` to it, if any.

        """
        parts = signature.split()
        name = parts[0]

        annotation = self.make_type_annotation()
        if annotation:
            signode += annotation

        signode += addnodes.desc_name(name, name)

        return name

    def add_target_and_index(self, name, sig, signode):
        """Add the target and index.

        Add the target to the environment, and create an index entry.

        """
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

    def lookup_auto_symbol(self, name=None):
        """Get the symbol with ``name`` for auto-documentation.

        If ``name`` is ``None``, use the name extracted from the first
        signature.

        If the ``auto`` option was set, try to get and return the
        :class:`~sphinxcontrib.emacs.lisp.Symbol` with ``name`` from the
        domain's interpreter environment.  If the symbol was not found, return
        ``None``.

        If the ``auto`` option was not set, always return ``None``.

        """
        name = name or self.names[0]
        if 'auto' in self.options:
            env = self.env.domaindata[self.domain]['environment']
            symbol = env.top_level.get(name)
            if not symbol:
                self.state_machine.reporter.warning(
                    'Undefined symbol {0}'.format(name), line=self.lineno)
            elif self.emacs_lisp_scope not in symbol.scopes:
                self.state_machine.reporter.warning(
                    'Symbol {0} not present in scope {1}'.format(
                        symbol.name, self.emacs_lisp_scope))
            return symbol
        else:
            return None

    def get_auto_signature(self, symbol):
        """Get the signature of ``symbol``.

        ``symbol`` is a :class:`~sphinxcontrib.emacs.lisp.Symbol` from the
        abstract interpreter, as returned by :meth:`lookup_auto_symbol`.

        """
        return symbol.name

    def get_auto_docstring(self, symbol):
        """Get the docstring of ``symbol``.

        By default, take the docstring from the property denoted by the
        ``docstring_property`` attribute of this object.

        ``symbol`` is a :class:`~sphinxcontrib.emacs.lisp.Symbol` from the
        abstract interpreter, as returned by :meth:`lookup_auto_symbol`.

        Return the ``docstring``, or ``None`` if ``symbol`` has no docstring.

        """
        return symbol.properties.get(self.docstring_property)

    def get_auto_doc_nodes(self):
        """Get the parsed docstring.

        Return the parsed docstring as list of nodes.  Return an empty list, if
        the ``auto`` option was not set.

        """
        symbol = self.lookup_auto_symbol()
        if symbol:
            docstring = self.get_auto_docstring(symbol)
            if not docstring:
                self.state_machine.reporter.warning(
                    'no docstring for symbol {0}'.format(self.names[0]),
                    line=self.lineno)
                return []
            else:
                parser = DocstringParser(self.state_machine.reporter)
                source = symbol.source_of_scope(self.emacs_lisp_scope)
                # FIXME: We should have a source mapping over the whole source
                # file, but unfortunately sexpdata doesn't provide source
                # locations
                return parser.parse(docstring, source_file=source.file,
                                    source_symbol=symbol.name)
        else:
            return []

    def run(self):
        """Run this directive.

        In addition to the default processing of the
        :class:`~sphinx.directives.ObjectDescription` directive, add the
        automatically extracted documentation if the ``auto`` option was set.

        """
        result_nodes = ObjectDescription.run(self)

        if 'auto' in self.options:
            cont_node = result_nodes[-1][-1]
            self.before_content()
            children = self.get_auto_doc_nodes() + cont_node.children
            cont_node.clear()
            cont_node.extend(children)
            self.after_content()

        return result_nodes


class EmacsLispCLStruct(EmacsLispSymbol):
    """A directive to describe a CL struct."""

    def before_content(self):
        """Add the name of the struct to the temporary environment data."""
        EmacsLispSymbol.before_content(self)
        if self.names:
            self.env.temp_data['el:cl-struct'] = self.names[0]

    def after_content(self):
        """Remove the name of the struct from the temporary environment data."""
        EmacsLispSymbol.after_content(self)
        del self.env.temp_data['el:cl-struct']


class EmacsLispCLSlot(EmacsLispSymbol):
    """A directive to describe a slot of a CL struct.

    This directive prepends the name of the current CL struct to the slot.

    """

    def handle_signature(self, sig, signode):
        """Resolve the slot name against the current struct."""
        name = EmacsLispSymbol.handle_signature(self, sig, signode)
        struct = self.env.temp_data.get('el:cl-struct')
        if not struct:
            raise ValueError('Missing containing structure')
        return struct + '-' + name


class EmacsLispVariable(EmacsLispSymbol):
    """A directive to describe an Emacs Lisp variable.

    This directive is different from :class:`EmacsLispSymbol` in that it adds
    special options for variables, namely whether a variable is buffer local.

    """

    option_spec = {
        'local': directives.flag,
        'risky': directives.flag,
        'safe': directives.unchanged,
    }
    option_spec.update(EmacsLispSymbol.option_spec)

    @property
    def is_local_variable(self):
        """Whether the documented variable is automatically buffer local."""
        if 'local' in self.options:
            return True
        else:
            symbol = self.lookup_auto_symbol()
            return symbol and symbol.properties.get('buffer-local')

    @property
    def is_risky_variable(self):
        """Whether the documented variable is risky."""
        if 'risky' in self.options:
            return True
        else:
            symbol = self.lookup_auto_symbol()
            return symbol and symbol.properties.get('risky-local-variable')

    def get_safe_variable_predicate(self):
        """Get the predicate marking the documented variable as safe.

        Return the name of the predicate as string, or ``None`` if the variable
        is not safe.

        """
        safe = self.options.get('safe')
        if not safe:
            symbol = self.lookup_auto_symbol()
            safe = symbol and symbol.properties.get('safe-local-variable')
        if safe:
            return str(safe)

    def add_inline_text(self, text, node):
        """Adds inline ``text`` to ``node``.

        Parse ``text`` with the inline text processor, and add the resulting
        nodes to ``node``.

        """
        children, msgs = self.state.inline_text(text, self.lineno)
        node.extend(children)
        node.extend(msgs)

    def make_variable_properties(self):
        """Get a node for the variable properties.

        Look at all special properties of the documented variables, and create
        an admonition that describes all these properties in a human-readable
        way.

        Return the admonition node, or ``None``, if the documented variable has
        no special properties.

        """
        title = corenodes.title('Variable properties', 'Variable properties')
        body = corenodes.paragraph('', '')
        props = corenodes.admonition(
            '', title, body, classes=['el-variable-properties'])
        if self.is_local_variable:
            self.add_inline_text(
                'Automatically becomes buffer-local when set.  ', body)
        if self.is_risky_variable:
            self.add_inline_text(
                'This variable may be risky if used as a file-local '
                'variable.  ', body)
        safe_predicate = self.get_safe_variable_predicate()
        if safe_predicate:
            self.add_inline_text(
                'This variable is safe as a file local variable if its value '
                'satisfies the predicate :el:function:`{0}`.  '.format(
                    safe_predicate), body)

        return props if len(body) > 0 else None

    def run(self):
        """Run this directive.

        In addition to the normal processing of the :class:`EmacsLispSymbol`
        directive, also add the variable properties as returned by
        :meth:`make_variable_properties` to the documentation.

        """
        result_nodes = EmacsLispSymbol.run(self)

        properties = self.make_variable_properties()
        if properties:
            cont_node = result_nodes[-1][-1]
            cont_node.insert(0, properties)

        return result_nodes


class EmacsLispFunction(EmacsLispSymbol):
    """A directive to describe an Emacs Lisp function.

    This directive is different from :class:`EmacsLispSymbol` in that it
    accepts a parameter list.

    """

    docstring_property = 'function-documentation'

    def get_auto_signature(self, symbol):
        """Extract the function signature of ``symbol``."""
        sig = EmacsLispSymbol.get_auto_signature(self, symbol)
        arglist = ' '.join(symbol.properties.get('function-arglist', []))
        return (sig + ' ' + arglist).strip()

    def handle_signature(self, signature, signode):
        """Handle the given ``signature``.

        In addition to the normal signature handling of the
        :class:`EmacsLispSymbol` directive, parse and annotate the function
        signature of the symbol.

        """
        parts = signature.split(' ')
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

    docstring_property = 'function-documentation'

    def with_prefix_arg(self, binding):
        """Add the ``:prefix-arg:`` option to the given ``binding``.

        Return the complete key binding including the ``:prefix-arg:`` option
        as string.  If there is no ``:prefix-arg:``, return ``binding``.

        """
        prefix_arg = self.options.get('prefix-arg')
        return prefix_arg + ' ' + binding if prefix_arg else binding

    def make_type_annotation(self):
        """Make a type annotation.

        Instead of using the name of the object type, use the key sequence for
        execution of this command as annotation.

        """
        keys = self.with_prefix_arg('M-x')
        node = nodes.el_annotation(keys + ' ', keys + ' ')
        node['keep_texinfo'] = True
        return node

    def run(self):
        """Run this directive.

        In addition to the normal processing of the :class:`EmacsLispSymbol`
        directive, also prepend an additional signature that describes the
        keybinding of the documented command, if any.

        """
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
