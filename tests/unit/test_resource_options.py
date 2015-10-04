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

# TODO: test arguments parsing
