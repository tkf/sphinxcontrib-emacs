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


def is_quoted_symbol(sexp):
    return (isinstance(sexp, sexpdata.Quoted) and
            isinstance(sexp.value(), sexpdata.Symbol))


def is_primitive(sexp):
    return ((isinstance(sexp, list) and sexp == [])
            or isinstance(sexp, (int, long, basestring, bool)))


def unquote(sexp):
    if not isinstance(sexp, sexpdata.Quoted):
        raise ValueError('Not a quoted expression: {0!r}'.format(sexp))
    return sexp.value()


def to_plist(sexps):
    keys = [s.value() for s in sexps[::2]]
    values = sexps[1::2]
    return dict(zip(keys, values))


class Source(namedtuple('_Source', 'file feature')):

    @property
    def empty(self):
        return (not self.file) and (not self.feature)


class Symbol(object):
    def __init__(self, name):
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
        return self.scopes.get(scope)


class Feature(namedtuple('_Feature', 'name filename load_time')):

    @property
    def outdated(self):
        return (os.path.isfile(self.filename) and
                os.path.getmtime(self.filename) <= self.load_time)


class AbstractEnvironment(object):
    """The environment of an interpreter."""

    def __init__(self):
        self.features = {}
        self.top_level = {}

    @property
    def outdated(self):
        return any(feature.outdated for feature in self.features.itervalues())

    def intern(self, symbol):
        if isinstance(symbol, sexpdata.Symbol):
            name = symbol.value()
        elif isinstance(symbol, basestring):
            name = symbol
        else:
            raise ValueError('Invalid symbol name: {0!r}'.format(symbol))
        return self.top_level.setdefault(name, Symbol(name))

    def provide(self, feature, filename=None):
        load_time = (os.path.getmtime(filename)
                     if filename and os.path.isfile(filename) else 0)
        feature = Feature(name=feature, filename=filename, load_time=load_time)
        self.features[feature.name] = feature
        return feature

    def is_provided(self, feature):
        return feature in self.features


class AbstractInterpreter(object):

    def put(self, _context, _function, name, prop, value):
        if all(is_quoted_symbol(s) for s in [name, prop]):
            symbol = self.env.intern(unquote(name))
            prop = unquote(prop).value()
            if is_quoted_symbol(value):
                value = self.env.intern(unquote(value))
            elif not is_primitive(value):
                # We cannot handle non-constant values
                return
            symbol.properties[prop] = value

    def defun(self, context, _function, name, arglist, docstring=None, *_rest):
        symbol = self.intern_in_scope(name, 'function', context)
        symbol.properties['function-arglist'] = [s.value() for s in arglist]
        if docstring:
            symbol.properties['function-documentation'] = docstring

    def defvar(self, context, function, name, _initial_value=None,
               docstring=None, *rest):
        symbol = self.intern_in_scope(name, 'variable', context)
        if docstring:
            if isinstance(docstring, basestring):
                symbol.properties['variable-documentation'] = docstring
            else:
                # The docstring isn't a string, so we put it back into the
                # remaining arguments
                rest = [docstring] + list(rest)
                docstring = None
        if rest:
            # Destructure and evaluate the keyword arguments of defcustom's
            plist = to_plist(rest)
            package_version = plist.get(':package-version')
            if isinstance(package_version, sexpdata.Quoted):
                package_version = unquote(package_version)
                if isinstance(package_version, list):
                    package = package_version[0].value()
                    version = package_version[2]
                    symbol.properties['package-version'] = (package, version)
            safe_predicate = plist.get(':safe')
            if is_quoted_symbol(safe_predicate):
                symbol.properties['safe-local-variable'] = unquote(
                    safe_predicate).value()
            if plist.get(':risky'):
                symbol.properties['risky-local-variable'] = True
        symbol.properties['buffer-local'] = function.endswith('-local')

    def eval_inner(self, _context, _function, *body):
        for sexp in body:
            self.eval(sexp)

    DEFAULT_FUNCTIONS = {
        'put': put,
        'defun': defun,
        'defmacro': defun,
        'defvar': defvar,
        'defcustom': defvar,
        'defvar-local': defvar,
        'eval-and-compile': eval_inner,
        'eval-when-compile': eval_inner,
    }

    def __init__(self, load_path, env=None, **functions):
        if not load_path:
            raise ValueError('Empty load path!')
        self.functions = dict(self.DEFAULT_FUNCTIONS)
        self.functions.update(functions)
        self.env = env or AbstractEnvironment()
        self.load_path = load_path

    def intern_in_scope(self, symbol, scope, context):
        symbol = self.env.intern(symbol)
        symbol.scopes[scope] = Source(file=context.get('load_file_name'),
                                      feature=context.get('load_feature'))
        return symbol

    def locate(self, feature):
        if feature in self.env.features:
            return self.env.features[feature].filename
        else:
            filename = feature + '.el'
            candidates = (os.path.join(d, filename)
                          for d in self.load_path)
            return next((f for f in candidates if os.path.isfile(f)), None)

    def require(self, feature, context=None):
        if not self.env.is_provided(feature):
            filename = self.locate(feature)
            if not filename:
                raise LookupError('Cannot locate library: {0}'.format(feature))
            context = new_context(context, load_feature=feature)
            self.load(filename, context)
            self.env.provide(feature, filename=filename)

    def load(self, library, context=None):
        context = new_context(context, load_file_name=library)
        for sexp in self.read_file(library):
            self.eval(sexp, context=context)

    def read(self, string):
        return sexpdata.loads(string)

    def read_file(self, filename):
        with open(filename, 'r') as source:
            # Wrap source into a top-level sexp, to make it consumable for
            # sexpdata
            return self.read('(\n{0}\n)'.format(source.read()))

    def eval(self, sexp, context=None):
        function_name = sexp[0]
        args = sexp[1:]
        function = self.functions.get(function_name.value())
        if function:
            # pylint: disable=W0142
            return function(self, context or {}, function_name.value(), *args)


def new_context(old_context, **kwargs):
    return dict(old_context or {}, **kwargs)
