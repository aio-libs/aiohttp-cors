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

"""Test generic usage
"""

import asyncio
import pathlib

from yarl import URL

from tests.aio_test_base import AioTestBase, create_server, asynctest

import aiohttp
from aiohttp import web
from aiohttp import hdrs

from aiohttp_cors import setup, ResourceOptions, CorsViewMixin


TEST_BODY = "Hello, world"
SERVER_CUSTOM_HEADER_NAME = "X-Server-Custom-Header"
SERVER_CUSTOM_HEADER_VALUE = "some value"


@asyncio.coroutine
# pylint: disable=unused-argument
def handler(request: web.Request) -> web.StreamResponse:
    """Dummy request handler, returning `TEST_BODY`."""
    response = web.Response(text=TEST_BODY)

    response.headers[SERVER_CUSTOM_HEADER_NAME] = SERVER_CUSTOM_HEADER_VALUE

    return response


class WebViewHandler(web.View, CorsViewMixin):

    @asyncio.coroutine
    def get(self) -> web.StreamResponse:
        """Dummy request handler, returning `TEST_BODY`."""
        response = web.Response(text=TEST_BODY)

        response.headers[SERVER_CUSTOM_HEADER_NAME] = \
            SERVER_CUSTOM_HEADER_VALUE

        return response


class AioAiohttpAppTestBase(AioTestBase):
    """Base class for tests that create single aiohttp server.

    Class manages server creation using create_server() method and proper
    server shutdown.
    """

    def setUp(self):
        super().setUp()

        self.handler = None
        self.app = None
        self.url = None

        self.server = None

        self.session = aiohttp.ClientSession(loop=self.loop)

    def tearDown(self):
        self.session.close()

        if self.server is not None:
            self.loop.run_until_complete(self.shutdown_server())

        super().tearDown()

    @asyncio.coroutine
    def create_server(self, app: web.Application):
        """Create server listening on random port."""

        assert self.app is None
        self.app = app

        assert self.handler is None
        self.handler = app.make_handler()

        self.server = (yield from create_server(self.handler, self.loop))

        return self.server

    @property
    def server_url(self):
        """Server navigatable URL."""
        assert self.server is not None
        hostaddr, port = self.server.sockets[0].getsockname()
        return "http://{host}:{port}/".format(host=hostaddr, port=port)

    @asyncio.coroutine
    def shutdown_server(self):
        """Shutdown server."""
        assert self.server is not None

        self.server.close()
        yield from self.handler.shutdown()
        yield from self.server.wait_closed()
        yield from self.app.cleanup()

        self.server = None
        self.app = None
        self.handler = None


class TestMain(AioAiohttpAppTestBase):
    """Tests CORS server by issuing CORS requests."""

    @asynctest
    @asyncio.coroutine
    def test_message_roundtrip(self):
        """Test that aiohttp server is correctly setup in the base class."""

        app = web.Application()

        app.router.add_route("GET", "/", handler)

        yield from self.create_server(app)

        response = yield from self.session.request("GET", self.server_url)
        self.assertEqual(response.status, 200)
        data = yield from response.text()

        self.assertEqual(data, TEST_BODY)

    @asynctest
    @asyncio.coroutine
    def test_dummy_setup(self):
        """Test a dummy configuration."""
        app = web.Application()
        setup(app)

        yield from self.create_server(app)

    @asynctest
    @asyncio.coroutine
    def test_dummy_setup_roundtrip(self):
        """Test a dummy configuration with a message round-trip."""
        app = web.Application()
        setup(app)

        app.router.add_route("GET", "/", handler)

        yield from self.create_server(app)

        response = yield from self.session.request("GET", self.server_url)
        self.assertEqual(response.status, 200)
        data = yield from response.text()

        self.assertEqual(data, TEST_BODY)

    @asynctest
    @asyncio.coroutine
    def test_dummy_setup_roundtrip_resource(self):
        """Test a dummy configuration with a message round-trip."""
        app = web.Application()
        setup(app)

        app.router.add_resource("/").add_route("GET", handler)

        yield from self.create_server(app)

        response = yield from self.session.request("GET", self.server_url)
        self.assertEqual(response.status, 200)
        data = yield from response.text()

        self.assertEqual(data, TEST_BODY)

    @asyncio.coroutine
    def _run_simple_requests_tests(self,
                                   tests_descriptions,
                                   use_resources,
                                   use_webview):
        """Runs CORS simple requests (without a preflight request) based
        on the passed tests descriptions.
        """

        @asyncio.coroutine
        def run_test(test):
            """Run single test"""

            response = yield from self.session.get(
                self.server_url + "resource",
                headers=test.get("request_headers", {}))
            self.assertEqual(response.status, 200)
            self.assertEqual((yield from response.text()), TEST_BODY)

            for header_name, header_value in test.get(
                    "in_response_headers", {}).items():
                with self.subTest(header_name=header_name):
                    self.assertEqual(
                        response.headers.get(header_name),
                        header_value)

            for header_name in test.get("not_in_request_headers", {}).items():
                self.assertNotIn(header_name, response.headers)

        for test_descr in tests_descriptions:
            with self.subTest(group_name=test_descr["name"]):
                app = web.Application()
                cors = setup(app, defaults=test_descr["defaults"])

                if use_resources:
                    resource = cors.add(app.router.add_resource("/resource"))
                    cors.add(resource.add_route("GET", handler),
                             test_descr["route_config"])
                elif use_webview:
                    WebViewHandler.cors_config = test_descr["route_config"]
                    cors.add(
                        app.router.add_route("*", "/resource", WebViewHandler),
                        webview=True)
                else:
                    cors.add(
                        app.router.add_route("GET", "/resource", handler),
                        test_descr["route_config"])

                yield from self.create_server(app)

                try:
                    for test_data in test_descr["tests"]:
                        with self.subTest(name=test_data["name"]):
                            yield from run_test(test_data)
                finally:
                    yield from self.shutdown_server()

    @asynctest
    @asyncio.coroutine
    def test_simple_default(self):
        """Test CORS simple requests with a route with the default
        configuration.

        The default configuration means that:
          * no credentials are allowed,
          * no headers are exposed,
          * no client headers are allowed.
        """

        client1 = "http://client1.example.org"
        client2 = "http://client2.example.org"
        client1_80 = "http://client1.example.org:80"
        client1_https = "https://client2.example.org"

        tests_descriptions = [
            {
                "name": "default",
                "defaults": None,
                "route_config":
                    {
                        client1: ResourceOptions(),
                    },
                "tests": [
                    {
                        "name": "no origin header",
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    {
                        "name": "allowed origin",
                        "request_headers": {
                            hdrs.ORIGIN: client1,
                        },
                        "in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: client1,
                        },
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    {
                        "name": "not allowed origin",
                        "request_headers": {
                            hdrs.ORIGIN: client2,
                        },
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    {
                        "name": "explicitly specified default port",
                        # CORS specification says, that origins may compared
                        # as strings, so "example.org:80" is not the same as
                        # "example.org".
                        "request_headers": {
                            hdrs.ORIGIN: client1_80,
                        },
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    {
                        "name": "different scheme",
                        "request_headers": {
                            hdrs.ORIGIN: client1_https,
                        },
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    ],
            },
        ]

        yield from self._run_simple_requests_tests(
            tests_descriptions, False, False)
        yield from self._run_simple_requests_tests(
            tests_descriptions, True, False)
        yield from self._run_simple_requests_tests(
            tests_descriptions, False, True)

    @asynctest
    @asyncio.coroutine
    def test_simple_with_credentials(self):
        """Test CORS simple requests with a route with enabled authorization.

        Route with enabled authorization must return
        Origin: <origin as requested, NOT "*">
        Access-Control-Allow-Credentials: true
        """

        client1 = "http://client1.example.org"
        client2 = "http://client2.example.org"

        credential_tests = [
            {
                "name": "no origin header",
                "not_in_response_headers": {
                    hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                    hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                    hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                }
            },
            {
                "name": "allowed origin",
                "request_headers": {
                    hdrs.ORIGIN: client1,
                },
                "in_response_headers": {
                    hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: client1,
                    hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS: "true",
                },
                "not_in_response_headers": {
                    hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                }
            },
            {
                "name": "disallowed origin",
                "request_headers": {
                    hdrs.ORIGIN: client2,
                },
                "not_in_response_headers": {
                    hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                    hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                    hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                }
            },
        ]

        tests_descriptions = [
            {
                "name": "route settings",
                "defaults": None,
                "route_config":
                    {
                        client1: ResourceOptions(allow_credentials=True),
                    },
                "tests": credential_tests,
            },
            {
                "name": "cors default settings",
                "defaults":
                    {
                        client1: ResourceOptions(allow_credentials=True),
                    },
                "route_config": None,
                "tests": credential_tests,
            },
        ]

        yield from self._run_simple_requests_tests(
            tests_descriptions, False, False)
        yield from self._run_simple_requests_tests(
            tests_descriptions, True, False)
        yield from self._run_simple_requests_tests(
            tests_descriptions, False, True)

    @asynctest
    @asyncio.coroutine
    def test_simple_expose_headers(self):
        """Test CORS simple requests with a route that exposes header."""

        client1 = "http://client1.example.org"
        client2 = "http://client2.example.org"

        tests_descriptions = [
            {
                "name": "default",
                "defaults": None,
                "route_config":
                    {
                        client1: ResourceOptions(
                            expose_headers=(SERVER_CUSTOM_HEADER_NAME,)),
                    },
                "tests": [
                    {
                        "name": "no origin header",
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    {
                        "name": "allowed origin",
                        "request_headers": {
                            hdrs.ORIGIN: client1,
                        },
                        "in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: client1,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS:
                                SERVER_CUSTOM_HEADER_NAME,
                        },
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    {
                        "name": "not allowed origin",
                        "request_headers": {
                            hdrs.ORIGIN: client2,
                        },
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        }
                    },
                    ],
            },
        ]

        yield from self._run_simple_requests_tests(
            tests_descriptions, False, False)
        yield from self._run_simple_requests_tests(
            tests_descriptions, True, False)
        yield from self._run_simple_requests_tests(
            tests_descriptions, False, True)

    @asyncio.coroutine
    def _run_preflight_requests_tests(self,
                                      tests_descriptions,
                                      use_resources,
                                      use_webview):
        """Runs CORS preflight requests based on the passed tests descriptions.
        """

        @asyncio.coroutine
        def run_test(test):
            """Run single test"""

            response = yield from self.session.options(
                self.server_url + "resource",
                headers=test.get("request_headers", {}))
            self.assertEqual(response.status, test.get("response_status", 200))
            response_text = yield from response.text()
            in_response = test.get("in_response")
            if in_response is not None:
                self.assertIn(in_response, response_text)
            else:
                self.assertEqual(response_text, "")

            for header_name, header_value in test.get(
                    "in_response_headers", {}).items():
                self.assertEqual(
                    response.headers.get(header_name),
                    header_value)

            for header_name in test.get("not_in_request_headers", {}).items():
                self.assertNotIn(header_name, response.headers)

        for test_descr in tests_descriptions:
            with self.subTest(group_name=test_descr["name"]):
                app = web.Application()
                cors = setup(app, defaults=test_descr["defaults"])

                if use_resources:
                    resource = cors.add(app.router.add_resource("/resource"))
                    cors.add(resource.add_route("GET", handler),
                             test_descr["route_config"])
                elif use_webview:
                    WebViewHandler.cors_config = test_descr["route_config"]
                    cors.add(
                        app.router.add_route("*", "/resource", WebViewHandler),
                        webview=True)
                else:
                    cors.add(
                        app.router.add_route("GET", "/resource", handler),
                        test_descr["route_config"])

                yield from self.create_server(app)

                try:
                    for test_data in test_descr["tests"]:
                        with self.subTest(name=test_data["name"]):
                            yield from run_test(test_data)
                finally:
                    yield from self.shutdown_server()

    @asynctest
    @asyncio.coroutine
    def test_preflight_default(self):
        """Test CORS preflight requests with a route with the default
        configuration.

        The default configuration means that:
          * no credentials are allowed,
          * no headers are exposed,
          * no client headers are allowed.
        """

        client1 = "http://client1.example.org"
        client2 = "http://client2.example.org"

        tests_descriptions = [
            {
                "name": "default",
                "defaults": None,
                "route_config":
                    {
                        client1: ResourceOptions(),
                    },
                "tests": [
                    {
                        "name": "no origin",
                        "response_status": 403,
                        "in_response": "origin header is not specified",
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                            hdrs.ACCESS_CONTROL_MAX_AGE,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                            hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                        },
                    },
                    {
                        "name": "no method",
                        "request_headers": {
                            hdrs.ORIGIN: client1,
                        },
                        "response_status": 403,
                        "in_response": "'Access-Control-Request-Method' "
                                       "header is not specified",
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                            hdrs.ACCESS_CONTROL_MAX_AGE,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                            hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                        },
                    },
                    {
                        "name": "origin and method",
                        "request_headers": {
                            hdrs.ORIGIN: client1,
                            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "GET",
                        },
                        "in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: client1,
                            hdrs.ACCESS_CONTROL_ALLOW_METHODS: "GET",
                        },
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                            hdrs.ACCESS_CONTROL_MAX_AGE,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                        },
                    },
                    {
                        "name": "disallowed origin",
                        "request_headers": {
                            hdrs.ORIGIN: client2,
                            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "GET",
                        },
                        "response_status": 403,
                        "in_response": "origin '{}' is not allowed".format(
                            client2),
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                            hdrs.ACCESS_CONTROL_MAX_AGE,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                            hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                        },
                    },
                    {
                        "name": "disallowed method",
                        "request_headers": {
                            hdrs.ORIGIN: client1,
                            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "POST",
                        },
                        "response_status": 403,
                        "in_response": "request method 'POST' is not allowed",
                        "not_in_response_headers": {
                            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                            hdrs.ACCESS_CONTROL_MAX_AGE,
                            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                            hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                            hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                        },
                    },
                    ],
            },
        ]

        yield from self._run_preflight_requests_tests(
            tests_descriptions, False, False)
        yield from self._run_preflight_requests_tests(
            tests_descriptions, True, False)
        yield from self._run_preflight_requests_tests(
            tests_descriptions, False, True)

    @asynctest
    @asyncio.coroutine
    def test_preflight_request_multiple_routes_with_one_options(self):
        """Test CORS preflight handling on resource that is available through
        several routes.
        """
        app = web.Application()
        cors = setup(app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        cors.add(app.router.add_route("GET", "/{name}", handler))
        cors.add(app.router.add_route("PUT", "/{name}", handler))

        yield from self.create_server(app)

        response = yield from self.session.request(
            "OPTIONS", self.server_url + "user",
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT"
            }
        )
        self.assertEqual(response.status, 200)

        data = yield from response.text()
        self.assertEqual(data, "")

    @asynctest
    @asyncio.coroutine
    def test_preflight_request_multiple_routes_with_one_options_resource(self):
        """Test CORS preflight handling on resource that is available through
        several routes.
        """
        app = web.Application()
        cors = setup(app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        resource = cors.add(app.router.add_resource("/{name}"))
        cors.add(resource.add_route("GET", handler))
        cors.add(resource.add_route("PUT", handler))

        yield from self.create_server(app)

        response = yield from self.session.request(
            "OPTIONS", self.server_url + "user",
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT"
            }
        )
        self.assertEqual(response.status, 200)

        data = yield from response.text()
        self.assertEqual(data, "")

    @asynctest
    @asyncio.coroutine
    def test_preflight_request_headers_resource(self):
        """Test CORS preflight request handlers handling."""
        app = web.Application()
        cors = setup(app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers=("Content-Type", "X-Header"),
            )
        })

        cors.add(app.router.add_route("PUT", "/", handler))

        yield from self.create_server(app)

        response = yield from self.session.request(
            "OPTIONS", self.server_url,
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
                hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type",
            }
        )
        self.assertEqual((yield from response.text()), "")
        self.assertEqual(response.status, 200)
        # Access-Control-Allow-Headers must be compared in case-insensitive
        # way.
        self.assertEqual(
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS].upper(),
            "content-type".upper())

        response = yield from self.session.request(
            "OPTIONS", self.server_url,
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
                hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "X-Header,content-type",
            }
        )
        self.assertEqual(response.status, 200)
        # Access-Control-Allow-Headers must be compared in case-insensitive
        # way.
        self.assertEqual(
            frozenset(response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS]
                      .upper().split(",")),
            {"X-Header".upper(), "content-type".upper()})
        self.assertEqual((yield from response.text()), "")

        response = yield from self.session.request(
            "OPTIONS", self.server_url,
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
                hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type,Test",
            }
        )
        self.assertEqual(response.status, 403)
        self.assertNotIn(
            hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
            response.headers)
        self.assertIn(
            "headers are not allowed: TEST",
            (yield from response.text()))

    @asynctest
    @asyncio.coroutine
    def test_preflight_request_headers(self):
        """Test CORS preflight request handlers handling."""
        app = web.Application()
        cors = setup(app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers=("Content-Type", "X-Header"),
            )
        })

        resource = cors.add(app.router.add_resource("/"))
        cors.add(resource.add_route("PUT", handler))

        yield from self.create_server(app)

        response = yield from self.session.request(
            "OPTIONS", self.server_url,
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
                hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type",
            }
        )
        self.assertEqual((yield from response.text()), "")
        self.assertEqual(response.status, 200)
        # Access-Control-Allow-Headers must be compared in case-insensitive
        # way.
        self.assertEqual(
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS].upper(),
            "content-type".upper())

        response = yield from self.session.request(
            "OPTIONS", self.server_url,
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
                hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "X-Header,content-type",
            }
        )
        self.assertEqual(response.status, 200)
        # Access-Control-Allow-Headers must be compared in case-insensitive
        # way.
        self.assertEqual(
            frozenset(response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS]
                      .upper().split(",")),
            {"X-Header".upper(), "content-type".upper()})
        self.assertEqual((yield from response.text()), "")

        response = yield from self.session.request(
            "OPTIONS", self.server_url,
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
                hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type,Test",
            }
        )
        self.assertEqual(response.status, 403)
        self.assertNotIn(
            hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
            response.headers)
        self.assertIn(
            "headers are not allowed: TEST",
            (yield from response.text()))

    @asynctest
    @asyncio.coroutine
    def test_static_route(self):
        """Test a static route with CORS."""
        app = web.Application()
        cors = setup(app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_methods="*",
                allow_headers=("Content-Type", "X-Header"),
            )
        })

        test_static_path = pathlib.Path(__file__).parent
        cors.add(app.router.add_static("/static", test_static_path,
                                       name='static'))

        yield from self.create_server(app)

        response = yield from self.session.request(
            "OPTIONS", URL(self.server_url) / "static/test_page.html",
            headers={
                hdrs.ORIGIN: "http://example.org",
                hdrs.ACCESS_CONTROL_REQUEST_METHOD: "OPTIONS",
                hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type",
            }
        )
        data = yield from response.text()
        self.assertEqual(response.status, 200)
        self.assertEqual(data, '')


# TODO: test requesting resources with not configured CORS.
# TODO: test wildcard origin in default config.
# TODO: test different combinations of ResourceOptions options.
# TODO: remove deplication of resource/not resource configuration using
# pytest's fixtures.
