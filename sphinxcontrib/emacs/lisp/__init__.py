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

import sexpdata


class Symbol(object):
    def __init__(self, name):
        self.name = name,
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


class AbstractInterpreter(object):

    def defun(self, _function, name, arglist, docstring=None, *_rest):
        symbol = self.intern(name)
        symbol.scopes.add('function')
        symbol.properties['function_arglist'] = [s.value() for s in arglist]
        if docstring:
            symbol.properties['function_documentation'] = docstring

    def defvar(self, function, name, _initial_value=None, docstring=None,
               *_rest):
        symbol = self.intern(name)
        symbol.scopes.add('variable')
        if docstring:
            symbol.properties['variable_documentation'] = docstring
        symbol.properties['local_variable'] = function.endswith('-local')

    def eval_inner(self, _function, *args):
        self.eval_all(args)

    DEFAULT_FUNCTIONS = {
        'defun': defun,
        'defmacro': defun,
        'defvar': defvar,
        'defcustom': defvar,
        'defvar-local': defvar,
        'eval-and-compile': eval_inner,
        'eval-when-compile': eval_inner,
    }

    def __init__(self, load_path, **functions):
        if not load_path:
            raise ValueError('Empty load path!')

        self.functions = dict(self.DEFAULT_FUNCTIONS)
        self.functions.update(functions)
        self.namespace = namespace if namespace is not None else {}
        self.load_path = load_path
        self.features = {}

    def intern(self, symbol):
        name = symbol.value()
        return self.namespace.setdefault(name, Symbol(name))

    def locate(self, feature):
        if feature in self.features:
            return self.features[feature]
        else:
            filename = feature + '.el'
            candidates = (os.path.join(d, filename)
                          for d in config.emacs_lisp_load_path)
            return next((f for f in candidates if os.path.isfile(f)), None)

    def require(self, feature):
        if feature not in self.features:
            filename = self.locate(feature)
            if not filename:
                raise LookupError('Cannot locate library: {0}'.format(feature))
            self.load(filename)
            self.features[feature] = filename

    def load(self, library):
        return self.eval_sexps(self.read_file(library))

    def read(self, string):
        return sexpdata.loads(string, nil=None, true=None, false=None)

    def read_file(self, filename):
        with open(filename, 'r') as source:
            # Wrap source into a top-level sexp, to make it consumable for
            # sexpdata
            return self.read('(\n{0}\n)'.format(source.read()))

    def eval_sexp(self, sexp):
        function_name = sexp[0]
        args = sexp[1:]
        function = self.functions.get(function_name.value())
        if function:
            # pylint: disable=W0142
            return function(self, function_name.value(), *args)

    def eval_sexps(self, sexps):
        for sexp in sexps:
            self.eval(sexp)
