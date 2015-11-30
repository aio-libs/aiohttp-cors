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

"""aiohttp_cors.cors_config unit tests.
"""

import asyncio
import unittest

from aiohttp import web

from aiohttp_cors import CorsConfig, ResourceOptions


def _handler(request):
    return web.Response(text="Done")


class TestCorsConfig(unittest.TestCase):
    """Unit tests for CorsConfig"""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.app = web.Application(loop=self.loop)
        self.cors = CorsConfig(self.app, defaults={
            "*": ResourceOptions()
        })
        self.get_route = self.app.router.add_route(
            "GET", "/get_path", _handler)
        self.options_route = self.app.router.add_route(
            "OPTIONS", "/options_path", _handler)

    def tearDown(self):
        self.loop.close()

    def test_add_get_route(self):
        """Test configuring GET route"""
        result = self.cors.add(self.get_route)
        self.assertIs(result, self.get_route)

        self.assertEqual(len(self.cors._route_config), 1)
        self.assertIn(self.get_route, self.cors._route_config)

        self.assertEqual(len(self.cors._preflight_route_settings), 1)

    def test_add_options_route(self):
        """Test configuring OPTIONS route"""

        with self.assertRaisesRegex(
                ValueError,
                "CORS can't be enabled on route that handles OPTIONS request"):
            self.cors.add(self.options_route)

        self.assertFalse(self.cors._route_config)
        self.assertFalse(self.cors._preflight_route_settings)

    def test_add_preflight_route(self):
        """Test configuring preflight route"""

        self.cors.add(self.get_route)
        preflight_route = next(iter(
            self.cors._preflight_route_settings.keys()))

        self.assertEqual(len(self.cors._route_config), 1)
        self.assertEqual(len(self.cors._preflight_route_settings), 1)

        # TODO: Capture and verify log warning message.
        result = self.cors.add(preflight_route)
        self.assertIs(result, preflight_route)

        self.assertEqual(len(self.cors._route_config), 1)
        self.assertEqual(len(self.cors._preflight_route_settings), 1)
