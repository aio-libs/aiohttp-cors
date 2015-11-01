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

"""Base classes and utility functions for testing asyncio-powered code.
"""

import unittest
import asyncio
import socket
import functools


@asyncio.coroutine
def create_server(protocol_factory, loop=None):
    """Create server listening on random port"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(10)

    if loop is None:
        loop = asyncio.get_event_loop()

    return (yield from loop.create_server(protocol_factory, sock=sock))


class AioTestBase(unittest.TestCase):
    """Base class for tests that need temporary asyncio event loop"""
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)


def asynctest(test_method):
    """Decorator for coroutine tests.

    To be used with `AioTestBase`-based tests"""
    @functools.wraps(test_method)
    def wrapper(self):
        """Synchronously run test method in the event loop"""
        self.loop.run_until_complete(test_method(self))
    return wrapper
