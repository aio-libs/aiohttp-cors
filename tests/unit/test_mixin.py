import asyncio
import unittest

from unittest import mock
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
    @asyncio.coroutine
    def get(self):
        return web.Response(text="Done")


class SimpleViewWithConfig(web.View, CorsViewMixin):

    cors_config = CLASS_CONFIG

    @asyncio.coroutine
    def get(self):
        return web.Response(text="Done")


class CustomMethodView(web.View, CorsViewMixin):

    cors_config = CLASS_CONFIG

    @asyncio.coroutine
    def get(self):
        return web.Response(text="Done")

    @custom_cors(CUSTOM_CONFIG)
    @asyncio.coroutine
    def post(self):
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
