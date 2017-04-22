# Copyright 2015 Vladimir Rutsky <vladimir@rutsky.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from setuptools import setup


def read_file(filename):
    abs_path = os.path.join(os.path.dirname(__file__), filename)
    with open(abs_path, encoding="utf-8") as f:
        return f.read()


about = {}
exec(read_file(os.path.join("aiohttp_cors", "__about__.py")), about)

needs_pytest = {'pytest', 'test'}.intersection(sys.argv)
pytest_runner = ['pytest_runner'] if needs_pytest else []

# aiohttp requires Python >= 3.4.1, so as aiohttp_cors.
if sys.version_info[:3] < (3, 4, 1):
    print("Error: aiohttp_cors requires Python interpreter version >= 3.4.1, "
          "this interpreter has version '{}'".format(sys.version),
          file=sys.stderr)
    sys.exit(1)


setup(
    name=about["__title__"],
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__email__"],
    description=about["__summary__"],
    url=about["__uri__"],
    long_description="\n\n".join((
        read_file("README.rst"),
        read_file("CHANGES.rst"),
    )),
    packages=["aiohttp_cors"],
    setup_requires=[
        # Environment markers were implemented and stabilized in setuptools
        # v20.8.1 (see <http://stackoverflow.com/a/32643122/391865>).
        "setuptools>=20.8.1",
        # If line above doesn't work, check that you have at least
        # setuptools v19.4 (released 2016-01-16):
        # <https://github.com/pypa/setuptools/issues/141>
    ] + pytest_runner,
    tests_require=[
        "pytest",
        "pytest-cov",
        "pytest-pylint",
        "selenium",
    ],
    test_suite="tests",
    install_requires=[
        "aiohttp>=1.1",
        "typing;python_version<'3.5'",
    ],
    license=about["__license__"],
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: AsyncIO",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Development Status :: 3 - Alpha",
    ],
)
