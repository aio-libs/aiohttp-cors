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

import aiohttp
import pytest

from aiohttp import web
from aiohttp import hdrs

from aiohttp_cors import setup as _setup, ResourceOptions, CorsViewMixin


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


@pytest.fixture(params=['resource', 'view', 'route'])
def make_app(loop, request):
    def inner(defaults, route_config):
        app = web.Application(loop=loop)
        cors = _setup(app, defaults=defaults)

        if request.param == 'resource':
            resource = cors.add(app.router.add_resource("/resource"))
            cors.add(resource.add_route("GET", handler), route_config)
        elif request.param == 'view':
            WebViewHandler.cors_config = route_config
            cors.add(
                app.router.add_route("*", "/resource", WebViewHandler),
                webview=True)
        elif request.param == 'route':
            cors.add(
                app.router.add_route("GET", "/resource", handler),
                route_config)
        else:
            raise RuntimeError('unknown parameter {}'.format(request.param))

        return app

    return inner


@asyncio.coroutine
def test_message_roundtrip(test_client):
    """Test that aiohttp server is correctly setup in the base class."""

    app = web.Application()
    app.router.add_route("GET", "/", handler)

    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert resp.status == 200
    data = yield from resp.text()

    assert data == TEST_BODY


@asyncio.coroutine
def test_dummy_setup(test_server):
    """Test a dummy configuration."""
    app = web.Application()
    _setup(app)

    yield from test_server(app)


@asyncio.coroutine
def test_dummy_setup_roundtrip(test_client):
    """Test a dummy configuration with a message round-trip."""
    app = web.Application()
    _setup(app)

    app.router.add_route("GET", "/", handler)

    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert resp.status == 200
    data = yield from resp.text()

    assert data == TEST_BODY


@asyncio.coroutine
def test_dummy_setup_roundtrip_resource(test_client):
    """Test a dummy configuration with a message round-trip."""
    app = web.Application()
    _setup(app)

    app.router.add_resource("/").add_route("GET", handler)

    client = yield from test_client(app)

    resp = yield from client.get('/')
    assert resp.status == 200
    data = yield from resp.text()

    assert data == TEST_BODY


@asyncio.coroutine
def test_simple_no_origin(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.get("/resource")
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_simple_allowed_origin(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'http://client1.example.org'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for hdr, val in {
            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: 'http://client1.example.org',
    }.items():
        assert resp.headers.get(hdr) == val

    for header_name in {
            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_simple_not_allowed_origin(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'http://client2.example.org'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_simple_explicit_port(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'http://client1.example.org:80'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_simple_different_scheme(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'https://client1.example.org'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@pytest.fixture(params=[
    (None,
     {"http://client1.example.org": ResourceOptions(allow_credentials=True)}),
    ({"http://client1.example.org": ResourceOptions(allow_credentials=True)},
      None),
])
def app_for_credentials(make_app, request):
    return make_app(*request.param)


@asyncio.coroutine
def test_cred_no_origin(test_client, app_for_credentials):
    app = app_for_credentials

    client = yield from test_client(app)

    resp = yield from client.get("/resource")
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_cred_allowed_origin(test_client, app_for_credentials):
    app = app_for_credentials

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'http://client1.example.org'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for hdr, val in {
            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: 'http://client1.example.org',
            hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS: "true"}.items():
        assert resp.headers.get(hdr) == val

    for header_name in {
                hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_cred_disallowed_origin(test_client, app_for_credentials):
    app = app_for_credentials

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'http://client2.example.org'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_simple_expose_headers_no_origin(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions(
                              expose_headers=(SERVER_CUSTOM_HEADER_NAME,))})

    client = yield from test_client(app)

    resp = yield from client.get("/resource")
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_simple_expose_headers_allowed_origin(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions(
                              expose_headers=(SERVER_CUSTOM_HEADER_NAME,))})

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'http://client1.example.org'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for hdr, val in {
            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: 'http://client1.example.org',
            hdrs.ACCESS_CONTROL_EXPOSE_HEADERS:
            SERVER_CUSTOM_HEADER_NAME}.items():
        assert resp.headers.get(hdr) == val

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_simple_expose_headers_not_allowed_origin(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions(
                              expose_headers=(SERVER_CUSTOM_HEADER_NAME,))})

    client = yield from test_client(app)

    resp = yield from client.get("/resource",
                                 headers={hdrs.ORIGIN:
                                          'http://client2.example.org'})
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert resp_text == TEST_BODY

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_preflight_default_no_origin(test_client, make_app):
    app = make_app(None, {"http://client1.example.org":
                          ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.options("/resource")
    assert resp.status == 403
    resp_text = yield from resp.text()
    assert "origin header is not specified" in resp_text

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        hdrs.ACCESS_CONTROL_MAX_AGE,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                        hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_preflight_default_no_method(test_client, make_app):

    app = make_app(None,{"http://client1.example.org":
                         ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.options("/resource", headers={
                        hdrs.ORIGIN: "http://client1.example.org",
                    })
    assert resp.status == 403
    resp_text = yield from resp.text()
    assert "'Access-Control-Request-Method' header is not specified"\
        in resp_text

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        hdrs.ACCESS_CONTROL_MAX_AGE,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                        hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_preflight_default_origin_and_method(test_client, make_app):

    app = make_app(None,{"http://client1.example.org":
                         ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.options("/resource", headers={
                        hdrs.ORIGIN: "http://client1.example.org",
                        hdrs.ACCESS_CONTROL_REQUEST_METHOD: "GET",
                    })
    assert resp.status == 200
    resp_text = yield from resp.text()
    assert '' == resp_text

    for hdr, val in {
            hdrs.ACCESS_CONTROL_ALLOW_ORIGIN: "http://client1.example.org",
            hdrs.ACCESS_CONTROL_ALLOW_METHODS: "GET"}.items():
        assert resp.headers.get(hdr) == val

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        hdrs.ACCESS_CONTROL_MAX_AGE,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_preflight_default_disallowed_origin(test_client, make_app):

    app = make_app(None,{"http://client1.example.org":
                         ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.options("/resource", headers={
                        hdrs.ORIGIN: "http://client2.example.org",
                        hdrs.ACCESS_CONTROL_REQUEST_METHOD: "GET",
                    })
    assert resp.status == 403
    resp_text = yield from resp.text()
    assert "origin 'http://client2.example.org' is not allowed" in resp_text

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        hdrs.ACCESS_CONTROL_MAX_AGE,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                        hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_preflight_default_disallowed_method(test_client, make_app):

    app = make_app(None,{"http://client1.example.org":
                         ResourceOptions()})

    client = yield from test_client(app)

    resp = yield from client.options("/resource", headers={
                        hdrs.ORIGIN: "http://client1.example.org",
                        hdrs.ACCESS_CONTROL_REQUEST_METHOD: "POST",
                    })
    assert resp.status == 403
    resp_text = yield from resp.text()
    assert ("request method 'POST' is not allowed for "
            "'http://client1.example.org' origin" in resp_text)

    for header_name in {
                        hdrs.ACCESS_CONTROL_ALLOW_ORIGIN,
                        hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                        hdrs.ACCESS_CONTROL_MAX_AGE,
                        hdrs.ACCESS_CONTROL_EXPOSE_HEADERS,
                        hdrs.ACCESS_CONTROL_ALLOW_METHODS,
                        hdrs.ACCESS_CONTROL_ALLOW_HEADERS,
                    }:
        assert header_name not in resp.headers


@asyncio.coroutine
def test_preflight_request_multiple_routes_with_one_options(test_client):
    """Test CORS preflight handling on resource that is available through
    several routes.
    """
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    cors.add(app.router.add_route("GET", "/{name}", handler))
    cors.add(app.router.add_route("PUT", "/{name}", handler))

    client = yield from test_client(app)

    resp = yield from client.options(
        "/user",
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT"
        }
    )
    assert resp.status == 200

    data = yield from resp.text()
    assert data == ""


@asyncio.coroutine
def test_preflight_request_mult_routes_with_one_options_resource(test_client):
    """Test CORS preflight handling on resource that is available through
    several routes.
    """
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    resource = cors.add(app.router.add_resource("/{name}"))
    cors.add(resource.add_route("GET", handler))
    cors.add(resource.add_route("PUT", handler))

    client = yield from test_client(app)

    resp = yield from client.options(
        "/user",
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT"
        }
    )
    assert resp.status == 200

    data = yield from resp.text()
    assert data == ""


@asyncio.coroutine
def test_preflight_request_max_age_resource(test_client):
    """Test CORS preflight handling on resource that is available through
    several routes.
    """
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            max_age=1200
        )
    })

    resource = cors.add(app.router.add_resource("/{name}"))
    cors.add(resource.add_route("GET", handler))

    client = yield from test_client(app)

    resp = yield from client.options(
        "/user",
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "GET"
        }
    )
    assert resp.status == 200
    assert resp.headers[hdrs.ACCESS_CONTROL_MAX_AGE].upper() == "1200"

    data = yield from resp.text()
    assert data == ""


@asyncio.coroutine
def test_preflight_request_max_age_webview(test_client):
    """Test CORS preflight handling on resource that is available through
    several routes.
    """
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            max_age=1200
        )
    })

    class TestView(web.View, CorsViewMixin):
        @asyncio.coroutine
        def get(self):
            resp = web.Response(text=TEST_BODY)

            resp.headers[SERVER_CUSTOM_HEADER_NAME] = \
                SERVER_CUSTOM_HEADER_VALUE

            return resp

    cors.add(app.router.add_route("*", "/{name}", TestView), webview=True)

    client = yield from test_client(app)

    resp = yield from client.options(
        "/user",
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "GET"
        }
    )
    assert resp.status == 200
    assert resp.headers[hdrs.ACCESS_CONTROL_MAX_AGE].upper() == "1200"

    data = yield from resp.text()
    assert data == ""


@asyncio.coroutine
def test_preflight_request_mult_routes_with_one_options_webview(test_client):
    """Test CORS preflight handling on resource that is available through
    several routes.
    """
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    class TestView(web.View, CorsViewMixin):
        @asyncio.coroutine
        def get(self):
            resp = web.Response(text=TEST_BODY)

            resp.headers[SERVER_CUSTOM_HEADER_NAME] = \
                SERVER_CUSTOM_HEADER_VALUE

            return resp

        put = get

    cors.add(app.router.add_route("*", "/{name}", TestView), webview=True)

    client = yield from test_client(app)

    resp = yield from client.options(
        "/user",
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT"
        }
    )
    assert resp.status == 200

    data = yield from resp.text()
    assert data == ""


@asyncio.coroutine
def test_preflight_request_headers_webview(test_client):
    """Test CORS preflight request handlers handling."""
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers=("Content-Type", "X-Header"),
        )
    })

    class TestView(web.View, CorsViewMixin):
        @asyncio.coroutine
        def put(self):
            response = web.Response(text=TEST_BODY)

            response.headers[SERVER_CUSTOM_HEADER_NAME] = \
                SERVER_CUSTOM_HEADER_VALUE

            return response

    cors.add(app.router.add_route("*", "/", TestView), webview=True)

    client = yield from test_client(app)

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type",
        }
    )
    assert (yield from resp.text()) == ""
    assert resp.status == 200
    # Access-Control-Allow-Headers must be compared in case-insensitive
    # way.
    assert (resp.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS].upper() ==
            "content-type".upper())

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "X-Header,content-type",
        }
    )
    assert resp.status == 200
    # Access-Control-Allow-Headers must be compared in case-insensitive
    # way.
    assert (
        frozenset(resp.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS]
                  .upper().split(",")) ==
        {"X-Header".upper(), "content-type".upper()})
    assert (yield from resp.text()) == ""

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type,Test",
        }
    )
    assert resp.status == 403
    assert hdrs.ACCESS_CONTROL_ALLOW_HEADERS not in resp.headers
    assert "headers are not allowed: TEST" in (yield from resp.text())


@asyncio.coroutine
def test_preflight_request_headers_resource(test_client):
    """Test CORS preflight request handlers handling."""
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers=("Content-Type", "X-Header"),
        )
    })

    cors.add(app.router.add_route("PUT", "/", handler))

    client = yield from test_client(app)

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type",
        }
    )
    assert (yield from resp.text()) == ""
    assert resp.status == 200
    # Access-Control-Allow-Headers must be compared in case-insensitive
    # way.
    assert (
        resp.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS].upper() ==
        "content-type".upper())

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "X-Header,content-type",
        }
    )
    assert resp.status == 200
    # Access-Control-Allow-Headers must be compared in case-insensitive
    # way.
    assert (
        frozenset(resp.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS]
                  .upper().split(",")) ==
        {"X-Header".upper(), "content-type".upper()})
    assert (yield from resp.text()) == ""

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type,Test",
        }
    )
    assert resp.status == 403
    assert hdrs.ACCESS_CONTROL_ALLOW_HEADERS not in resp.headers
    assert "headers are not allowed: TEST" in (yield from resp.text())


@asyncio.coroutine
def test_preflight_request_headers(test_client):
    """Test CORS preflight request handlers handling."""
    app = web.Application()
    cors = _setup(app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers=("Content-Type", "X-Header"),
        )
    })

    resource = cors.add(app.router.add_resource("/"))
    cors.add(resource.add_route("PUT", handler))

    client = yield from test_client(app)

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type",
        }
    )
    assert (yield from resp.text()) == ""
    assert resp.status == 200
    # Access-Control-Allow-Headers must be compared in case-insensitive
    # way.
    assert (
        resp.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS].upper() ==
        "content-type".upper())

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "X-Header,content-type",
        }
    )
    assert resp.status == 200
    # Access-Control-Allow-Headers must be compared in case-insensitive
    # way.
    assert (
        frozenset(resp.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS]
                  .upper().split(",")) ==
        {"X-Header".upper(), "content-type".upper()})
    assert (yield from resp.text()) == ""

    resp = yield from client.options(
        '/',
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "PUT",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type,Test",
        }
    )
    assert resp.status == 403
    assert hdrs.ACCESS_CONTROL_ALLOW_HEADERS not in resp.headers
    assert "headers are not allowed: TEST" in (yield from resp.text())


@asyncio.coroutine
def test_static_route(test_client):
    """Test a static route with CORS."""
    app = web.Application()
    cors = _setup(app, defaults={
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

    client = yield from test_client(app)

    resp = yield from client.options(
        "/static/test_page.html",
        headers={
            hdrs.ORIGIN: "http://example.org",
            hdrs.ACCESS_CONTROL_REQUEST_METHOD: "OPTIONS",
            hdrs.ACCESS_CONTROL_REQUEST_HEADERS: "content-type",
        }
    )
    data = yield from resp.text()
    assert resp.status == 200
    assert data == ''


# TODO: test requesting resources with not configured CORS.
# TODO: test wildcard origin in default config.
# TODO: test different combinations of ResourceOptions options.
# TODO: remove deplication of resource/not resource configuration using
# pytest's fixtures.
