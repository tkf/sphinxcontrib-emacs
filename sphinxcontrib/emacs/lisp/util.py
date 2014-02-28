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


"""Utilities for lisp processing."""


import sexpdata


def is_quoted_symbol(sexp):
    """Determine whether ``sexp`` is a quoted symbol.

    Return ``True`` if so, or ``False`` otherwise.

    """
    return (isinstance(sexp, sexpdata.Quoted) and
            isinstance(sexp.value(), sexpdata.Symbol))


def is_primitive(sexp):
    """Determine whether ``sexp`` is a primitive expression.

    A primitive expression is either an empty sexp (aka ``nil``), or constant
    of a primitive type, i.e. numbers, strings or booleans.

    """
    return ((isinstance(sexp, list) and sexp == [])
            or isinstance(sexp, (int, long, basestring, bool)))


def unquote(sexp):
    """Unquotes ``sexp``.

    Return ``sexp`` without the leading quote.  Raise :exc:`ValueError`, if
    ``sexp`` is not quoted.

    """
    if not isinstance(sexp, sexpdata.Quoted):
        raise ValueError('Not a quoted expression: {0!r}'.format(sexp))
    return sexp.value()


def to_plist(sexps):
    """Turn ``sexp`` into a dictionary.

    ``sexp`` should be in the form of a property list.

    Return a dictionary mapping the keys to the values.  The keys are strings,
    the values the unmodified sexp of the corresponding plist values.

    """
    keys = [s.value() for s in sexps[::2]]
    values = sexps[1::2]
    return dict(zip(keys, values))
