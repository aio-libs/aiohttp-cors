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

from aiohttp_cors import CorsConfig, ResourceOptions, CorsViewMixin


def _handler(request):
    return web.Response(text="Done")


class _View(web.View, CorsViewMixin):

    @asyncio.coroutine
    def get(self):
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

    def test_add_options_route(self):
        """Test configuring OPTIONS route"""

        with self.assertRaises(RuntimeError):
            self.cors.add(self.options_route.resource)

    def test_plain_named_route(self):
        """Test adding plain named route."""
        # Adding CORS routes should not introduce new named routes.
        self.assertEqual(len(self.app.router.keys()), 0)
        route = self.app.router.add_route(
            "GET", "/{name}", _handler, name="dynamic_named_route")
        self.assertEqual(len(self.app.router.keys()), 1)
        self.cors.add(route)
        self.assertEqual(len(self.app.router.keys()), 1)

    def test_dynamic_named_route(self):
        """Test adding dynamic named route."""
        self.assertEqual(len(self.app.router.keys()), 0)
        route = self.app.router.add_route(
            "GET", "/{name}", _handler, name="dynamic_named_route")
        self.assertEqual(len(self.app.router.keys()), 1)
        self.cors.add(route)
        self.assertEqual(len(self.app.router.keys()), 1)

    def test_static_named_route(self):
        """Test adding dynamic named route."""
        self.assertEqual(len(self.app.router.keys()), 0)
        route = self.app.router.add_static(
            "/file", "/", name="dynamic_named_route")
        self.assertEqual(len(self.app.router.keys()), 1)
        self.cors.add(route)
        self.assertEqual(len(self.app.router.keys()), 1)

    def test_static_resource(self):
        """Test adding static resource."""
        self.assertEqual(len(self.app.router.keys()), 0)
        self.app.router.add_static(
            "/file", "/", name="dynamic_named_route")
        self.assertEqual(len(self.app.router.keys()), 1)
        for resource in list(self.app.router.resources()):
            if issubclass(resource, web.StaticResource):
                self.cors.add(resource)
        self.assertEqual(len(self.app.router.keys()), 1)

    def test_web_view_resource(self):
        """Test adding resource with web.View as handler"""
        self.assertEqual(len(self.app.router.keys()), 0)
        route = self.app.router.add_route(
            "GET", "/{name}", _View, name="dynamic_named_route")
        self.assertEqual(len(self.app.router.keys()), 1)
        self.cors.add(route)
        self.assertEqual(len(self.app.router.keys()), 1)
