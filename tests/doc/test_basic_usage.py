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

"""Test basic usage."""

import unittest


class TestBasicUsage(unittest.TestCase):
    def test_main(self):
        # This tests corresponds to example from documentation.
        # If you updating it, don't forget to update documentation.

        import asyncio
        from aiohttp import web
        import aiohttp_cors

        @asyncio.coroutine
        def handler(request):
            return web.Response(
                text="Hello!",
                headers={
                    "X-Custom-Server-Header": "Custom data",
                })

        app = web.Application()

        # `cors` object will store CORS configuration for the application.
        cors = aiohttp_cors.setup(app)

        # To enable CORS processing for specific route you need to add
        # that route to the CORS configuration object and specify it's
        # CORS options.
        cors.add(
            app.router.add_route("GET", "/hello", handler), {
                "http://client.example.org": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers=("X-Custom-Server-Header",),
                    allow_headers=("X-Requested-With", "Content-Type"),
                    max_age=3600,
                )
            })
