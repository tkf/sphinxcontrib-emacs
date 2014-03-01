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


def is_quoted(sexp):
    """Determine whether ``sexp`` is a quoted expression."""
    return isinstance(sexp, sexpdata.Quoted)


def is_quoted_symbol(sexp):
    """Determine whether ``sexp`` is a quoted symbol.

    Return ``True`` if so, or ``False`` otherwise.

    """
    return (is_quoted(sexp) and
            isinstance(unquote(sexp), sexpdata.Symbol))


def is_primitive(sexp):
    """Determine whether ``sexp`` is a primitive expression.

    A primitive expression is either an empty sexp (aka ``nil``), or constant
    of a primitive type, i.e. numbers, strings or booleans.

    """
    return ((isinstance(sexp, list) and sexp == [])
            or isinstance(sexp, (int, long, basestring, bool)))


def unquote(sexp):
    """Unquote ``sexp``.

    Return ``sexp`` without the leading quote.  Raise :exc:`ValueError`, if
    ``sexp`` is not quoted.

    """
    if not is_quoted(sexp):
        raise ValueError('Not a quoted expression: {0!r}'.format(sexp))
    return sexp.value()


def parse_cons_cell(sexp):
    """Parse a cons cell ``sexp``.

    Return the sub-expressions as ``(car, cdr)`` pair.  Raise
    :exc:`ValueError`, if ``sexp`` is not a cons cell.

    """
    if len(sexp) == 3 and sexp[1] == sexpdata.Symbol('.'):
        return sexp[0], sexp[2]
    else:
        raise ValueError('Not a cons cell: {0!r}'.format(sexp))


def parse_plist(sexps):
    """Turn ``sexp`` into a dictionary.

    ``sexp`` should be in the form of a property list.

    Return a dictionary mapping the keys to the values.  The keys are strings,
    the values the unmodified sexp of the corresponding plist values.

    """
    keys = [s.value() for s in sexps[::2]]
    values = sexps[1::2]
    return dict(zip(keys, values))


def parse_package_version(sexp):
    """Parse a ``:package-version`` argument.

    Return a pair ``(package, version)`` with the results.  Raise
    :exc:`ValueError`, if ``sexp`` is not a valid package version.

    """
    if is_quoted(sexp):
        sexp = unquote(sexp)
    car, cdr = parse_cons_cell(sexp)
    if isinstance(car, sexpdata.Symbol) and isinstance(cdr, basestring):
        return car.value(), cdr
    else:
        raise ValueError('Not a valid :package-version: {0!r}'.format(sexp))


def parse_custom_keywords(sexp):
    """Parse custom keywords from ``sexp``.

    Return a dictionary with corresponding symbol properties.

    """
    plist = parse_plist(sexp)
    properties = {}
    package_version = plist.get(':package-version')
    if package_version:
        try:
            properties['custom-package-version'] = parse_package_version(
                package_version)
        except ValueError:
            pass
    safe_predicate = plist.get(':safe')
    if is_quoted_symbol(safe_predicate):
        properties['safe-local-variable'] = unquote(safe_predicate).value()
    if plist.get(':risky'):
        properties['risky-local-variable'] = True
    return properties
