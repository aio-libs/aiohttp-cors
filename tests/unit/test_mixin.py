import asyncio
import unittest

from unittest import mock
from aiohttp import web
from tests.aio_test_base import asynctest

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


class TestCustomCors(unittest.TestCase):
    """Unit tests for CorsConfig"""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.app = web.Application(loop=self.loop)
        self.cors = CorsConfig(self.app, defaults=DEFAULT_CONFIG)
        self.app[APP_CONFIG_KEY] = self.cors

    def tearDown(self):
        self.loop.close()

    def test_raise_exception_when_cors_not_configure(self):
        request = mock.Mock()
        request.app = {}
        view = CustomMethodView(request)

        with self.assertRaises(ValueError):
            view.get_request_config(request, 'post')

    @asynctest
    async def test_raises_forbidden_when_config_not_found(self):
        self.app[APP_CONFIG_KEY].defaults = {}
        request = mock.Mock()
        request.app = self.app
        request.headers = {
            'Origin': '*',
            'Access-Control-Request-Method': 'GET'
        }
        view = SimpleView(request)

        with self.assertRaises(web.HTTPForbidden):
            await view.options()

    def test_method_with_custom_cors(self):
        """Test adding resource with web.View as handler"""
        request = mock.Mock()
        request.app = self.app
        view = CustomMethodView(request)

        self.assertTrue(hasattr(view.post, 'post_cors_config'))
        self.assertTrue(asyncio.iscoroutinefunction(view.post))
        config = view.get_request_config(request, 'post')

        self.assertEqual(config.get('www.client1.com'),
                         CUSTOM_CONFIG['www.client1.com'])

    def test_method_with_class_config(self):
        """Test adding resource with web.View as handler"""
        request = mock.Mock()
        request.app = self.app
        view = SimpleViewWithConfig(request)

        self.assertFalse(hasattr(view.get, 'get_cors_config'))
        config = view.get_request_config(request, 'get')

        self.assertEqual(config.get('*'),
                         CLASS_CONFIG['*'])

    def test_method_with_default_config(self):
        """Test adding resource with web.View as handler"""
        request = mock.Mock()
        request.app = self.app
        view = SimpleView(request)

        self.assertFalse(hasattr(view.get, 'get_cors_config'))
        config = view.get_request_config(request, 'get')

        self.assertEqual(config.get('*'),
                         DEFAULT_CONFIG['*'])
