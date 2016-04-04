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

import unittest

from aiohttp_cors.resource_options import ResourceOptions


class TestResourceOptions(unittest.TestCase):
    """Unit tests for ResourceOptions class"""

    def test_init_no_args(self):
        """Test construction without arguments"""
        opts = ResourceOptions()

        self.assertFalse(opts.allow_credentials)
        self.assertFalse(opts.expose_headers)
        self.assertFalse(opts.allow_headers)
        self.assertIsNone(opts.max_age)

    def test_comparison(self):
        self.assertTrue(ResourceOptions() == ResourceOptions())
        self.assertFalse(ResourceOptions() != ResourceOptions())
        self.assertFalse(
            ResourceOptions(allow_credentials=True) == ResourceOptions())
        self.assertTrue(
            ResourceOptions(allow_credentials=True) != ResourceOptions())

    def test_allow_methods(self):
        self.assertIsNone(ResourceOptions().allow_methods)
        self.assertEqual(
            ResourceOptions(allow_methods='*').allow_methods,
            '*')
        self.assertEqual(
            ResourceOptions(allow_methods=[]).allow_methods,
            frozenset())
        self.assertEqual(
            ResourceOptions(allow_methods=['get']).allow_methods,
            frozenset(['GET']))
        self.assertEqual(
            ResourceOptions(allow_methods=['get', 'Post']).allow_methods,
            {'GET', 'POST'})
        with self.assertRaises(ValueError):
            ResourceOptions(allow_methods='GET')

# TODO: test arguments parsing
