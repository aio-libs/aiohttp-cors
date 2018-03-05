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

import pytest
from aiohttp import web

from aiohttp_cors import CorsConfig, ResourceOptions, CorsViewMixin


async def _handler(request):
    return web.Response(text="Done")


class _View(web.View, CorsViewMixin):

    @asyncio.coroutine
    def get(self):
        return web.Response(text="Done")


@pytest.fixture
def app():
    return web.Application()


@pytest.fixture
def cors(app):
    return CorsConfig(app, defaults={
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


def test_add_options_route(cors, options_route):
    """Test configuring OPTIONS route"""

    with pytest.raises(ValueError,
                       match="/options_path already has OPTIONS handler"):
        cors.add(options_route.resource)


def test_plain_named_route(app, cors):
    """Test adding plain named route."""
    # Adding CORS routes should not introduce new named routes.
    assert len(app.router.keys()) == 0
    route = app.router.add_route(
        "GET", "/{name}", _handler, name="dynamic_named_route")
    assert len(app.router.keys()) == 1
    cors.add(route)
    assert len(app.router.keys()) == 1


def test_dynamic_named_route(app, cors):
    """Test adding dynamic named route."""
    assert len(app.router.keys()) == 0
    route = app.router.add_route(
        "GET", "/{name}", _handler, name="dynamic_named_route")
    assert len(app.router.keys()) == 1
    cors.add(route)
    assert len(app.router.keys()) == 1


def test_static_named_route(app, cors):
    """Test adding dynamic named route."""
    assert len(app.router.keys()) == 0
    route = app.router.add_static(
        "/file", "/", name="dynamic_named_route")
    assert len(app.router.keys()) == 1
    cors.add(route)
    assert len(app.router.keys()) == 1


def test_static_resource(app, cors):
    """Test adding static resource."""
    assert len(app.router.keys()) == 0
    app.router.add_static(
        "/file", "/", name="dynamic_named_route")
    assert len(app.router.keys()) == 1
    for resource in list(app.router.resources()):
        if issubclass(resource, web.StaticResource):
            cors.add(resource)
    assert len(app.router.keys()) == 1


def test_web_view_resource(app, cors):
    """Test adding resource with web.View as handler"""
    assert len(app.router.keys()) == 0
    route = app.router.add_route(
        "GET", "/{name}", _View, name="dynamic_named_route")
    assert len(app.router.keys()) == 1
    cors.add(route)
    assert len(app.router.keys()) == 1


def test_web_view_warning(app, cors):
    """Test adding resource with web.View as handler"""
    route = app.router.add_route("*", "/", _View)
    with pytest.warns(DeprecationWarning):
        cors.add(route, webview=True)


def test_disable_bare_view(app, cors):
    class View(web.View):
        pass

    route = app.router.add_route("*", "/", View)
    with pytest.raises(ValueError):
        cors.add(route)
