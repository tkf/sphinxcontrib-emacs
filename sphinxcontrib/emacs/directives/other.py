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


"""Miscellaneous directives of this extension."""


from docutils.parsers.rst import Directive


class RequireLibrary(Directive):
    """Load and parse an Emacs Lisp library."""

    required_arguments = 1
    optional_arguments = 0
    has_content = False

    def run(self):
        """Run this directive.

        Load the feature with the abstract interpreter of
        :class:`~sphinxcontrib.emacs.domain.EmacsLispDomain`, and make the
        current document depend on the feature source.

        """
        self.domain, self.objtype = self.name.split(':', 1)
        env = self.state.document.settings.env
        interpreter = env.domains['el'].interpreter
        feature = self.arguments[0]

        try:
            interpreter.require(feature)
            env.note_dependency(interpreter.locate(feature))
        except LookupError as error:
            self.state_machine.reporter.warning(unicode(error), line=self.lineno)

        return []
