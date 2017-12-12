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

"""aiohttp_cors.urldispatcher_router_adapter unit tests.
"""

import asyncio
import unittest
from unittest import mock

from aiohttp import web

from aiohttp_cors.urldispatcher_router_adapter import \
    ResourcesUrlDispatcherRouterAdapter
from aiohttp_cors import ResourceOptions


def _handler(request):
    return web.Response(text="Done")


class TestResourcesUrlDispatcherRouterAdapter(unittest.TestCase):
    """Unit tests for CorsConfig"""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.app = web.Application(loop=self.loop)

        self.adapter = ResourcesUrlDispatcherRouterAdapter(
            self.app.router, defaults={
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
        result = self.adapter.add_preflight_handler(
            self.get_route.resource, _handler)
        self.assertIsNone(result)

        self.assertEqual(len(self.adapter._resource_config), 0)
        self.assertEqual(
            len(self.adapter._resources_with_preflight_handlers), 1)
        self.assertEqual(len(self.adapter._preflight_routes), 1)

    def test_add_options_route(self):
        """Test configuring OPTIONS route"""

        with self.assertRaisesRegex(
                ValueError,
                "CORS must be enabled for route's resource first"):
            self.adapter.add_preflight_handler(self.options_route, _handler)

        self.assertFalse(self.adapter._resources_with_preflight_handlers)
        self.assertFalse(self.adapter._preflight_routes)

    def test_get_non_preflight_request_config(self):
        self.adapter.add_preflight_handler(self.get_route.resource, _handler)
        self.adapter.set_config_for_routing_entity(
            self.get_route.resource, {
                'http://example.org': ResourceOptions(),
            })

        self.adapter.add_preflight_handler(self.get_route, _handler)
        self.adapter.set_config_for_routing_entity(
            self.get_route, {
                'http://test.example.org': ResourceOptions(),
            })

        request = mock.Mock()

        with mock.patch('aiohttp_cors.urldispatcher_router_adapter.'
                        'ResourcesUrlDispatcherRouterAdapter.'
                        'is_cors_enabled_on_request'
                        ) as is_cors_enabled_on_request, \
            mock.patch('aiohttp_cors.urldispatcher_router_adapter.'
                       'ResourcesUrlDispatcherRouterAdapter.'
                       '_request_resource'
                       ) as _request_resource:
            is_cors_enabled_on_request.return_value = True
            _request_resource.return_value = self.get_route.resource

            self.assertEqual(
                self.adapter.get_non_preflight_request_config(request),
                {
                    '*': ResourceOptions(),
                    'http://example.org': ResourceOptions(),
                })

            request.method = 'GET'

            self.assertEqual(
                self.adapter.get_non_preflight_request_config(request),
                {
                    '*': ResourceOptions(),
                    'http://example.org': ResourceOptions(),
                    'http://test.example.org': ResourceOptions(),
                })
