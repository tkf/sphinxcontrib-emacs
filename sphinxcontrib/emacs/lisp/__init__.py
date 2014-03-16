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


"""Emacs Lisp parsing and interpreting."""


import os
import os.path
from collections import namedtuple
from contextlib import contextmanager

import sexpdata

from sphinxcontrib.emacs.lisp import util as lisputil


def strip_broken_function_quotes(sexp):
    """Recursively strip broken function quotes from ``sexp``.

    :mod:`sexpdata` garbles function quotes, by putting the leading hash into a
    dedicated symbol.  See https://github.com/tkf/sexpdata/issues/3.

    This function recursively turns such broken quotes into standard quotes.

    """
    if isinstance(sexp, list):
        return [strip_broken_function_quotes(s) for i, s in enumerate(sexp)
                if not (s == sexpdata.Symbol('#')
                        and i + 1 < len(sexp)
                        and lisputil.is_quoted_symbol(sexp[i + 1]))]
    else:
        return sexp


class Source(namedtuple('_Source', 'file feature')):
    """The source of a definition.

    The ``file`` attribute is the name of the file, that contained the
    definition.  The ``feature`` is the name of the feature that provided the
    definition.  Both are either strings or ``None``.

    """

    @property
    def empty(self):
        """Whether this source is empty."""
        return (not self.file) and (not self.feature)


class Symbol(object):
    """A symbol in a symbol table.

    A symbol has a ``name``, as string, which is unique in the containing
    symbol table.

    Furthermore, a symbol has ``scopes``, which map an arbitrary identifier to
    a definition source.  Scopes track definitions of a symbol as variable,
    function, etc. and associate the definition to the source.  A symbol may
    have multiple definitions.

    Finally, a symbol has ``properties``, which are a mapping of arbitrary keys
    to arbitrary values.  These properties hold the constituents of
    definitions, or any other arbitrary properties.

    """

    def __init__(self, name):
        """Create a new symbol with the given ``name``.

        The new symbol has empty scopes and properties.

        """
        self.name = name
        self.scopes = {}
        self.properties = {}

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'Symbol({0}, {1!r})'.format(self.name, self.properties)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return self.name != other.name

    def source_of_scope(self, scope):
        """Get the source of the definition in ``scope``.

        Either a :class:`Source` pointing to the definition source, or
        ``None``, if the symbol was not defined in ``scope``.

        """
        return self.scopes.get(scope)


class Feature(namedtuple('_Feature', 'name filename load_time')):
    """A named feature.

    A feature has a unique ``name`` as string, an associated ``filename``, from
    which it was loaded, and a ``load_time``, as seconds since the epoch.

    """

    @property
    def outdated(self):
        """Whether the feature is outdated.

        A feature is outdated, if the modification time of the file it was
        loaded from is newer than the load time of the feature.

        Use this property to determine whether ``feature`` should be loaded
        again.

        """
        return (os.path.isfile(self.filename) and
                os.path.getmtime(self.filename) <= self.load_time)


class AbstractEnvironment(object):
    """The environment of an interpreter.

    An environment has a ``top_level`` symbol table, which maps symbol names to
    the corresponding :class:`Symbol` objects, and a list of provided
    ``features``, which map feature names to :class:`Feature` objects and
    tracks loaded libraries.

    Use :meth:`intern` to get or create a symbol in the symbol table, and
    :meth:`provide` to declare a provided feature.

    """

    def __init__(self):
        """Creates an empty environment."""
        self.features = {}
        self.top_level = {}

    @property
    def outdated(self):
        """Whether the environment is outdated.

        The environment is outdated, if any provided feature is outdated.

        .. seealso:: Feature.outdated

        """
        return any(feature.outdated for feature in self.features.itervalues())

    def intern(self, name):
        """Obtain a symbol with ``name`` from the top-level symbol table.

        If the symbol already exists, return the existing :class:`Symbol`
        object.  Otherwise, put the symbol into the symbol table first.

        ``name`` is either a string, or a :class:`sexpdata.Symbol`.  In any
        other case, raise :exc:`ValueError`.

        """
        if isinstance(name, sexpdata.Symbol):
            name = name.value()
        else:
            raise ValueError('Invalid symbol name: {0!r}'.format(name))
        return self.top_level.setdefault(name, Symbol(name))

    def provide(self, name, filename=None):
        """Provide a feature with ``name``.

        ``name`` is the name of the feature as string.  If given, ``filename``
        is a string with the name of the file which provides the feature.

        Return the corresponding :class:`Feature` object.

        """
        load_time = (os.path.getmtime(filename)
                     if filename and os.path.isfile(filename) else 0)
        feature = Feature(name=name, filename=filename, load_time=load_time)
        self.features[name] = feature
        return feature

    def is_provided(self, feature):
        """Determine whether ``feature`` is provided.

        ``feature`` is either a :class:`Feature` object, or a feature name as
        string.

        Return ``True`` if the feature is provided, or ``False`` otherwise.

        """
        name = feature.name if isinstance(feature, Feature) else feature
        return name in self.features


def new_context(old_context, **kwargs):
    """Create a new context from ``old_context``."""
    return dict(old_context or {}, **kwargs)


class AbstractInterpreter(object):
    """An abstract interpreter for Emacs Lisp.

    This interpreter evaluates Emacs Lisp expressions with a restricted
    semantics.  It does not implement the entire semantics of Emacs Lisp, but
    just enough to extract top-level symbol definitions and symbol properties.

    """

    def put(self, _context, _function, name, prop, value):
        """A call to ``put``.

        Tries to set the symbol property as set by ``put``."""
        if all(lisputil.is_quoted_symbol(s) for s in [name, prop]):
            symbol = self.env.intern(lisputil.unquote(name))
            prop = lisputil.unquote(prop).value()
            if lisputil.is_quoted_symbol(value):
                value = self.env.intern(lisputil.unquote(value))
            elif not lisputil.is_primitive(value):
                # We cannot handle non-constant values
                return
            symbol.properties[prop] = value

    def defun(self, context, _function, name, arglist, docstring=None, *_rest):
        """A call to ``defun`` or ``defmacro``.

        Parses the argument list and the docstring of the function.

        """
        symbol = self.intern_in_scope(name, 'function', context)
        symbol.properties['function-arglist'] = [s.value() for s in arglist]
        if docstring:
            symbol.properties['function-documentation'] = docstring

    def defvar(self, context, function, name, _initial_value=None,
               docstring=None, *rest):
        """A call to ``defvar`` and friends.

        Includes ``defvar-local`` and ``defcustom``.

        Parses the variable documentation, and tries to look at the keyword
        arguments to ``defcustom``.

        """
        symbol = self.intern_in_scope(name, 'variable', context)
        if docstring:
            if isinstance(docstring, basestring):
                symbol.properties['variable-documentation'] = docstring
            else:
                # The docstring isn't a string, so we put it back into the
                # remaining arguments
                rest = [docstring] + list(rest)
                docstring = None
        if rest and function == 'defcustom':
            symbol.properties.update(lisputil.parse_custom_keywords(rest))
        symbol.properties['buffer-local'] = function.endswith('-local')

    def defface(self, context, function, name, _face_def, docstring, *rest):
        """A call to ``defface``.

        Parses the face documentation, and evaluates the custom keywords.

        """
        symbol = self.intern_in_scope(name, 'face', context)
        symbol.properties['face-documentation'] = docstring
        if rest:
            symbol.properties.update(lisputil.parse_custom_keywords(rest))

    def eval_inner(self, _context, _function, *body):
        """Evaluate the inner expressions of a function.

        Handles `eval-when-compile` and friends."""
        for sexp in body:
            self.eval(sexp)

    #: The default function table.
    DEFAULT_FUNCTIONS = {
        'put': put,
        'defun': defun,
        'defun*': defun,
        'cl-defun': defun,
        'defmacro': defun,
        'defmacro*': defun,
        'cl-defmacro': defun,
        'defvar': defvar,
        'defcustom': defvar,
        'defvar-local': defvar,
        'defface': defface,
        'eval-and-compile': eval_inner,
        'eval-when-compile': eval_inner,
    }

    def __init__(self, load_path, env=None, **functions):
        """Create a new interpreter.

        ``load_path`` is the path to load features and libraries from.  ``env``
        is the :class:`AbstractEnvironment` for this interpreter.  If ``None``,
        a fresh environment is created.

        ``**functions`` are additional functions for this interpreter.

        """
        if not load_path:
            raise ValueError('Empty load path!')
        self.functions = dict(self.DEFAULT_FUNCTIONS)
        self.functions.update(functions)
        self.env = env or AbstractEnvironment()
        self.load_path = load_path

    def intern_in_scope(self, symbol, scope, context):
        """Intern a ``symbol`` in a ``scope``.

        Interns the symbol in the environment, and puts it into the given
        ``scope`` as well.

        """
        symbol = self.env.intern(symbol)
        symbol.scopes[scope] = Source(file=context.get('load_file_name'),
                                      feature=context.get('load_feature'))
        return symbol

    def locate(self, feature):
        """Locate the library for ``feature``.

        If the feature is not provided, look for the library in ``load_path``.
        Otherwise just return the file name of the feature.

        Return ``None``, if there is no library for ``feature``.

        """
        if feature in self.env.features:
            return self.env.features[feature].filename
        else:
            filename = feature + '.el'
            candidates = (os.path.join(d, filename)
                          for d in self.load_path)
            return next((f for f in candidates if os.path.isfile(f)), None)

    def require(self, feature, context=None):
        """Require a named feature.

        Locate and load the corresponding library.  Raise :class:`LookupError`
        if the library was not found.

        ``context`` is a dictionary with context information.

        """
        if not self.env.is_provided(feature):
            filename = self.locate(feature)
            if not filename:
                raise LookupError('Cannot locate library: {0}'.format(feature))
            context = new_context(context, load_feature=feature)
            self.load(filename, context)
            self.env.provide(feature, filename=filename)

    def load(self, library, context=None):
        """Load a ``library``.

        Evaluate all expressions in the ``library``.

        ``library`` is the file name of a library as string.  ``context`` is a
        dictionary with context information.

        """
        context = new_context(context, load_file_name=library)
        for sexp in self.read_file(library):
            self.eval(sexp, context=context)

    def read(self, string):
        """Parse and return a single expression from ``string``."""
        return sexpdata.loads(string)

    def read_file(self, filename):
        """Parse and return all expressions from ``filename``."""
        with open(filename, 'r') as source:
            # Wrap source into a top-level sexp, to make it consumable for
            # sexpdata
            return self.read('(\n{0}\n)'.format(source.read()))

    def eval(self, sexp, context=None):
        """Evaluate a single ``sexp`` and return the result.

        If ``sexp`` cannot be evaluated, return ``None``.

        ``context`` is a dictionary with additional context information.

        """
        sexp = strip_broken_function_quotes(sexp)
        function_name = sexp[0]
        args = sexp[1:]
        function = self.functions.get(function_name.value())
        if function:
            # pylint: disable=W0142
            return function(self, context or {}, function_name.value(), *args)
