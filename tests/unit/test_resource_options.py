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

"""aiohttp_cors.resource_options unit tests.
"""

import pytest

from aiohttp_cors.resource_options import ResourceOptions


def test_init_no_args():
    """Test construction without arguments"""
    opts = ResourceOptions()

    assert not opts.allow_credentials
    assert not opts.expose_headers
    assert not opts.allow_headers
    assert opts.max_age is None


def test_comparison():
    assert ResourceOptions() == ResourceOptions()
    assert not (ResourceOptions() != ResourceOptions())
    assert not (ResourceOptions(allow_credentials=True) == ResourceOptions())
    assert ResourceOptions(allow_credentials=True) != ResourceOptions()


def test_allow_methods():
    assert ResourceOptions().allow_methods is None
    assert ResourceOptions(allow_methods='*').allow_methods == '*'
    assert ResourceOptions(allow_methods=[]).allow_methods == frozenset()
    assert (ResourceOptions(allow_methods=['get']).allow_methods ==
            frozenset(['GET']))
    assert (ResourceOptions(allow_methods=['get', 'Post']).allow_methods ==
            {'GET', 'POST'})
    with pytest.raises(ValueError):
        ResourceOptions(allow_methods='GET')

# TODO: test arguments parsing
