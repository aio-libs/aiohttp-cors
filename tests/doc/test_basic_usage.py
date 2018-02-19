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


async def test_main():
    # This tests corresponds to example from documentation.
    # If you updating it, don't forget to update documentation.

    from aiohttp import web
    import aiohttp_cors

    async def handler(request):
        return web.Response(
            text="Hello!",
            headers={
                "X-Custom-Server-Header": "Custom data",
            })

    app = web.Application()

    # `aiohttp_cors.setup` returns `aiohttp_cors.CorsConfig` instance.
    # The `cors` instance will store CORS configuration for the
    # application.
    cors = aiohttp_cors.setup(app)

    # To enable CORS processing for specific route you need to add
    # that route to the CORS configuration object and specify its
    # CORS options.
    resource = cors.add(app.router.add_resource("/hello"))
    route = cors.add(
        resource.add_route("GET", handler), {
            "http://client.example.org": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers=("X-Custom-Server-Header",),
                allow_headers=("X-Requested-With", "Content-Type"),
                max_age=3600,
            )
        })

    assert route is not None


async def test_defaults():
    # This tests corresponds to example from documentation.
    # If you updating it, don't forget to update documentation.

    from aiohttp import web
    import aiohttp_cors

    async def handler(request):
        return web.Response(
            text="Hello!",
            headers={
                "X-Custom-Server-Header": "Custom data",
            })

    handler_post = handler
    handler_put = handler

    app = web.Application()

    # Example:

    cors = aiohttp_cors.setup(app, defaults={
            # Allow all to read all CORS-enabled resources from
            # http://client.example.org.
            "http://client.example.org": aiohttp_cors.ResourceOptions(),
        })

    # Enable CORS on routes.

    # According to defaults POST and PUT will be available only to
    # "http://client.example.org".
    hello_resource = cors.add(app.router.add_resource("/hello"))
    cors.add(hello_resource.add_route("POST", handler_post))
    cors.add(hello_resource.add_route("PUT", handler_put))

    # In addition to "http://client.example.org", GET request will be
    # allowed from "http://other-client.example.org" origin.
    cors.add(hello_resource.add_route("GET", handler), {
            "http://other-client.example.org":
            aiohttp_cors.ResourceOptions(),
        })

    # CORS will be enabled only on the resources added to `CorsConfig`,
    # so following resource will be NOT CORS-enabled.
    app.router.add_route("GET", "/private", handler)
