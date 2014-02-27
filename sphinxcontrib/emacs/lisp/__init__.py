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

import sexpdata


def is_quoted_symbol(sexp):
    return (isinstance(sexp, sexpdata.Quoted) and
            isinstance(sexp.value(), sexpdata.Symbol))


def unquote(sexp):
    if not isinstance(sexp, sexpdata.Quoted):
        raise ValueError('Not a quoted expression: {0!r}'.format(sexp))
    return sexp.value()


class Symbol(object):
    def __init__(self, name):
        self.name = name
        self.scopes = set()
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

    def put(self, _function, name, prop, value):
        # We can only handle quoted constant symbols here.
        # FIXME: We should also handle constant symbols here!
        if all(is_quoted_symbol(s) for s in [name, prop, value]):
            symbol = self.env.intern(unquote(name))
            prop = unquote(prop).value()
            value = self.env.intern(unquote(value))
            symbol.properties[prop] = value

    def defun(self, _function, name, arglist, docstring=None, *_rest):
        symbol = self.env.intern(name)
        symbol.scopes.add('function')
        symbol.properties['function_arglist'] = [s.value() for s in arglist]
        if docstring:
            symbol.properties['function_documentation'] = docstring

    def defvar(self, function, name, _initial_value=None, docstring=None,
               *_rest):
        symbol = self.env.intern(name)
        symbol.scopes.add('variable')
        if docstring:
            symbol.properties['variable_documentation'] = docstring
        symbol.properties['local_variable'] = function.endswith('-local')

    def eval_inner(self, _function, *body):
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

    def locate(self, feature):
        if feature in self.env.features:
            return self.env.features[feature].filename
        else:
            filename = feature + '.el'
            candidates = (os.path.join(d, filename)
                          for d in self.load_path)
            return next((f for f in candidates if os.path.isfile(f)), None)

    def require(self, feature):
        if not self.env.is_provided(feature):
            filename = self.locate(feature)
            if not filename:
                raise LookupError('Cannot locate library: {0}'.format(feature))
            self.load(filename)
            self.env.provide(feature, filename=filename)

    def load(self, library):
        for sexp in self.read_file(library):
            self.eval(sexp)

    def read(self, string):
        return sexpdata.loads(string, nil=None, true=None, false=None)

    def read_file(self, filename):
        with open(filename, 'r') as source:
            # Wrap source into a top-level sexp, to make it consumable for
            # sexpdata
            return self.read('(\n{0}\n)'.format(source.read()))

    def eval(self, sexp):
        function_name = sexp[0]
        args = sexp[1:]
        function = self.functions.get(function_name.value())
        if function:
            # pylint: disable=W0142
            return function(self, function_name.value(), *args)
