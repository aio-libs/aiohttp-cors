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

from pathlib import Path
import sys
from setuptools import setup

import ast
currentDir = Path(__file__).parent

def extractMetaInfo(src):
    info = {}
    a=ast.parse(src)
    for e in a.body:
        if isinstance(e, ast.Assign) and isinstance(e.value, ast.Str):
            info[e.targets[0].id] = e.value.s
    return info

about = extractMetaInfo((currentDir / "aiohttp_cors" / "__about__.py").read_text())


setup(
    name=about["__title__"],
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__email__"],
    description=about["__summary__"],
    url=about["__uri__"],
    long_description="\n\n".join(( (currentDir / sn).read_text() for sn in ("README.rst", "CHANGES.rst") )),
)
