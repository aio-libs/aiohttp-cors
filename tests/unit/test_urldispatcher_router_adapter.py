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

from unittest import mock

import pytest
from aiohttp import web

from aiohttp_cors.urldispatcher_router_adapter import \
    ResourcesUrlDispatcherRouterAdapter
from aiohttp_cors import ResourceOptions


async def _handler(request):
    return web.Response(text="Done")


@pytest.fixture
def app():
    return web.Application()


@pytest.fixture
def adapter(app):
    return ResourcesUrlDispatcherRouterAdapter(
        app.router, defaults={
            "*": ResourceOptions()
        })


@pytest.fixture
def get_route(app):
    return app.router.add_route(
        "GET", "/get_path", _handler)


@pytest.fixture
def options_route(app):
    return app.router.add_route(
        "OPTIONS", "/options_path", _handler)


def test_add_get_route(adapter, get_route):
    """Test configuring GET route"""
    result = adapter.add_preflight_handler(
        get_route.resource, _handler)
    assert result is None

    assert len(adapter._resource_config) == 0
    assert len(adapter._resources_with_preflight_handlers) == 1
    assert len(adapter._preflight_routes) == 1


def test_add_options_route(adapter, options_route):
    """Test configuring OPTIONS route"""

    adapter.add_preflight_handler(options_route, _handler)

    assert not adapter._resources_with_preflight_handlers
    assert not adapter._preflight_routes


def test_get_non_preflight_request_config(adapter, get_route):
    adapter.add_preflight_handler(get_route.resource, _handler)
    adapter.set_config_for_routing_entity(
        get_route.resource, {
            'http://example.org': ResourceOptions(),
        })

    adapter.add_preflight_handler(get_route, _handler)
    adapter.set_config_for_routing_entity(
        get_route, {
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
        _request_resource.return_value = get_route.resource

        assert (adapter.get_non_preflight_request_config(request) ==
                {
                    '*': ResourceOptions(),
                    'http://example.org': ResourceOptions(),
                })

        request.method = 'GET'

        assert (adapter.get_non_preflight_request_config(request) ==
                {
                    '*': ResourceOptions(),
                    'http://example.org': ResourceOptions(),
                    'http://test.example.org': ResourceOptions(),
                })
