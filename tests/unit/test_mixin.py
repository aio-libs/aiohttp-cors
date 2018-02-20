import asyncio

from unittest import mock

import pytest
from aiohttp import web

from aiohttp_cors import CorsConfig, APP_CONFIG_KEY
from aiohttp_cors import ResourceOptions, CorsViewMixin, custom_cors


DEFAULT_CONFIG = {
    '*': ResourceOptions()
}

CLASS_CONFIG = {
    '*': ResourceOptions()
}

CUSTOM_CONFIG = {
    'www.client1.com': ResourceOptions(allow_headers=['X-Host'])
}


class SimpleView(web.View, CorsViewMixin):
    async def get(self):
        return web.Response(text="Done")


class SimpleViewWithConfig(web.View, CorsViewMixin):

    cors_config = CLASS_CONFIG

    async def get(self):
        return web.Response(text="Done")


class CustomMethodView(web.View, CorsViewMixin):

    cors_config = CLASS_CONFIG

    async def get(self):
        return web.Response(text="Done")

    @custom_cors(CUSTOM_CONFIG)
    async def post(self):
        return web.Response(text="Done")


@pytest.fixture
def _app():
    return web.Application()


@pytest.fixture
def cors(_app):
    ret = CorsConfig(_app, defaults=DEFAULT_CONFIG)
    _app[APP_CONFIG_KEY] = ret
    return ret


@pytest.fixture
def app(_app, cors):
    # a trick to install a cors into app
    return _app


def test_raise_exception_when_cors_not_configure():
    request = mock.Mock()
    request.app = {}
    view = CustomMethodView(request)

    with pytest.raises(ValueError):
        view.get_request_config(request, 'post')


async def test_raises_forbidden_when_config_not_found(app):
    app[APP_CONFIG_KEY].defaults = {}
    request = mock.Mock()
    request.app = app
    request.headers = {
        'Origin': '*',
        'Access-Control-Request-Method': 'GET'
    }
    view = SimpleView(request)

    with pytest.raises(web.HTTPForbidden):
        await view.options()


def test_method_with_custom_cors(app):
    """Test adding resource with web.View as handler"""
    request = mock.Mock()
    request.app = app
    view = CustomMethodView(request)

    assert hasattr(view.post, 'post_cors_config')
    assert asyncio.iscoroutinefunction(view.post)
    config = view.get_request_config(request, 'post')

    assert config.get('www.client1.com') == CUSTOM_CONFIG['www.client1.com']


def test_method_with_class_config(app):
    """Test adding resource with web.View as handler"""
    request = mock.Mock()
    request.app = app
    view = SimpleViewWithConfig(request)

    assert not hasattr(view.get, 'get_cors_config')
    config = view.get_request_config(request, 'get')

    assert config.get('*') == CLASS_CONFIG['*']


def test_method_with_default_config(app):
    """Test adding resource with web.View as handler"""
    request = mock.Mock()
    request.app = app
    view = SimpleView(request)

    assert not hasattr(view.get, 'get_cors_config')
    config = view.get_request_config(request, 'get')

    assert config.get('*') == DEFAULT_CONFIG['*']
