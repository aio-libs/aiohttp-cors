import asyncio
import unittest

from unittest import mock
from tests.aio_test_base import asynctest

from aiohttp_cors.preflight_handler import _PreflightHandler


class TestPreflightHandler(unittest.TestCase):
    """Unit tests for PreflightHandler"""

    def setUp(self):
        self.loop = asyncio.new_event_loop()

    def tearDown(self):
        self.loop.close()

    @asynctest
    @asyncio.coroutine
    def test_raises_when_handler_not_extend(self):
        request = mock.Mock()
        handler = _PreflightHandler()
        with self.assertRaises(NotImplementedError):
            yield from handler._get_config(request, 'origin', 'GET')
