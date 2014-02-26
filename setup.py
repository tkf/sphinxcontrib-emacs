# -*- coding: utf-8 -*-
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


# Setup.py should have a docstring? Really?  C'mon pylint…
# pylint: disable=C0111


import os
import re
import sys
if sys.version_info[0] < 3:
    from codecs import open     # pylint: disable=W0622


from setuptools import setup, find_packages


VERSION_PATTERN = re.compile(r"__version__ = '([^']+)'")
VERSION_FILE = os.path.join('sphinxcontrib', 'emacs', '__init__.py')


def read_file(filename):
    """Read all contents of ``filename``."""
    with open(filename, encoding='utf-8') as source:
        return source.read()


def read_version_number(filename):
    """Extract the version number from ``filename``."""
    with open(filename, encoding='utf-8') as source:
        for line in source:
            match = VERSION_PATTERN.search(line)
            if match:
                return match.group(1)

        raise ValueError('Could not extract version number')


setup(
    name='sphinxcontrib-emacs',
    version=read_version_number(VERSION_FILE),
    url='https://github.com/flycheck/sphinxcontrib-emacs',
    license='MIT License',
    author='Sebastian Wiesner',
    author_email='lunaryorn@gmail.com',
    description='Emacs documentation support for Sphinx',
    long_description=read_file('README.rst'),
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Emacs-Lisp',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Documentation',
        'Topic :: Text Editors :: Emacs',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['Sphinx>=1.2', 'sexpdata>=0.0.3'],
    namespace_packages=['sphinxcontrib'],
)
