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

"""CORS support for aiohttp.
"""

import asyncio
import collections
import collections.abc

from aiohttp import web, hdrs

from .__about__ import (
    __title__, __version__, __author__, __email__, __summary__, __uri__,
    __license__, __copyright__,
)
from .urldispatcher_router_adapter import UrlDistatcherRouterAdapter
from .router_adapter import RouterAdapter
from .log import logger as _logger
from .resource_options import ResourceOptions

__all__ = (
    "__title__", "__version__", "__author__", "__email__", "__summary__",
    "__uri__", "__license__", "__copyright__",
    "setup", "CorsConfig", "ResourceOptions",
)


APP_CONFIG_KEY = "aiohttp_cors"
# Positive response to Access-Control-Allow-Credentials
_TRUE = "true"
# CORS simple response headers:
# <http://www.w3.org/TR/cors/#simple-response-header>
_SIMPLE_RESPONSE_HEADERS = frozenset([
    hdrs.CACHE_CONTROL,
    hdrs.CONTENT_LANGUAGE,
    hdrs.CONTENT_TYPE,
    hdrs.EXPIRES,
    hdrs.LAST_MODIFIED,
    hdrs.PRAGMA
])


def _parse_config_options(config: collections.abc.Mapping=None):
    """Parse CORS configuration (default or per-route)

    :param config:
        Mapping from Origin to Resource configuration (allowed headers etc)
        defined either as mapping or `ResourceOptions` instance.

    Raises `ValueError` if configuration is not correct.
    """

    if config is None:
        return {}

    if not isinstance(config, collections.abc.Mapping):
        raise ValueError(
            "Config must be mapping, got '{}'".format(config))

    parsed = {}

    options_keys = {
        "allow_credentials", "expose_headers", "allow_headers", "max_age"
    }

    for origin, options in config.items():
        # TODO: check that all origins are properly formatted.
        # This is not a security issue, since origin is compared as strings.
        if not isinstance(origin, str):
            raise ValueError(
                "Origin must be string, got '{}'".format(origin))

        if isinstance(options, ResourceOptions):
            resource_options = options

        else:
            if not isinstance(options, collections.abc.Mapping):
                raise ValueError(
                    "Origin options must be either "
                    "aiohttp_cors.ResourceOptions instance or mapping, "
                    "got '{}'".format(options))

            unexpected_args = frozenset(options.keys()) - options_keys
            if unexpected_args:
                raise ValueError(
                    "Unexpected keywords in resource options: {}".format(
                        # pylint: disable=bad-builtin
                        ",".join(map(str, unexpected_args))))

            resource_options = ResourceOptions(**options)

        parsed[origin] = resource_options

    return parsed


class CorsConfig:
    """CORS configuration instance.

    The instance holds default CORS parameters and per-route options specified
    in `add()` method.

    Each `aiohttp.web.Application` can have exactly one instance of this class.
    """

    def __init__(self, app: web.Application, *,
                 defaults: dict=None,
                 router_adapter: RouterAdapter=None):
        """Construct CORS configuration.

        :param app:
            Application for which CORS configuration is built.
        :param defaults:
            Default CORS settings for origins.
        :param router_adapter:
            Router adapter. Required if application uses non-default router.
        """

        self._app = app

        self._router_adapter = router_adapter
        if self._router_adapter is None:
            if isinstance(self._app.router, web.UrlDispatcher):
                self._router_adapter = UrlDistatcherRouterAdapter(
                    self._app.router)
            else:
                raise RuntimeError(
                    "Router adapter not specified. "
                    "Routers other than aiohttp.web.UrlDispatcher requires"
                    "custom router adapter.")

        self._default_config = _parse_config_options(defaults)

        self._route_config = {}
        self._preflight_route_settings = {}

        self._app.on_response_prepare.append(self._on_response_prepare)

    def add(self, route, config: collections.abc.Mapping=None):
        """Enable CORS for specific route.

        CORS is enable **only** for routes added with this method.

        :param route:
            Route for which CORS will be enabled.
        :param config:
            CORS options for the route.
        """
        if config is None and not self._default_config:
            _logger.warning(
                "No allowed origins configured for route %s, "
                "resource will not be shared with other origins. "
                "Setup either default origins in "
                "aiohttp_cors.setup(app, defaults=...) or"
                "explicitly specify origins when adding route to CORS.", route)

        parsed_config = _parse_config_options(config)
        defaulted_config = collections.ChainMap(
            parsed_config, self._default_config)

        route_methods = frozenset(self._router_adapter.route_methods(route))

        # TODO: Limited handling of CORS on OPTIONS may be useful?
        if {hdrs.METH_ANY, hdrs.METH_OPTIONS}.intersection(route_methods):
            raise ValueError(
                "CORS can't be enabled on route that handles OPTIONS request.")

        assert route not in self._route_config
        self._route_config[route] = defaulted_config

        # Add preflight request handler
        preflight_route = self._router_adapter.add_options_method_handler(
            route, self._preflight_handler)

        assert preflight_route not in self._preflight_route_settings
        self._preflight_route_settings[preflight_route] = \
            (defaulted_config, route_methods)

        return route

    @asyncio.coroutine
    def _on_response_prepare(self,
                             request: web.Request,
                             response: web.StreamResponse):
        """(Potentially) simple CORS request response processor.

        If request is done on CORS-enabled route, process request parameters
        and set appropriate CORS response headers.
        """
        route = request.match_info.route
        config = self._route_config.get(route)
        if config is None:
            return

        # Handle according to part 6.1 of the CORS specification.

        origin = request.headers.get(hdrs.ORIGIN)
        if origin is None:
            # Terminate CORS according to CORS 6.1.1.
            return

        options = config.get(origin, config.get("*"))
        if options is None:
            # Terminate CORS according to CORS 6.1.2.
            return

        assert hdrs.ACCESS_CONTROL_ALLOW_ORIGIN not in response.headers
        assert hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS not in response.headers
        assert hdrs.ACCESS_CONTROL_EXPOSE_HEADERS not in response.headers

        # Process according to CORS 6.1.4.
        # Set exposed headers (server headers exposed to client) before
        # setting any other headers.
        if options.expose_headers == "*":
            # Expose all headers that are set in response.
            exposed_headers = \
                frozenset(response.headers.keys()) - _SIMPLE_RESPONSE_HEADERS
            response.headers[hdrs.ACCESS_CONTROL_EXPOSE_HEADERS] = \
                ",".join(exposed_headers)

        elif options.expose_headers:
            # Expose predefined list of headers.
            response.headers[hdrs.ACCESS_CONTROL_EXPOSE_HEADERS] = \
                ",".join(options.expose_headers)

        # Process according to CORS 6.1.3.
        # Set allowed origin.
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = origin
        if options.allow_credentials:
            # Set allowed credentials.
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS] = _TRUE

    @staticmethod
    def _parse_request_method(request: web.Request):
        """Parse Access-Control-Request-Method header of the preflight request
        """
        method = request.headers.get(hdrs.ACCESS_CONTROL_REQUEST_METHOD)
        if method is None:
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "'Access-Control-Request-Method' header is not specified")

        # FIXME: validate method string (ABNF: method = token), if parsing
        # fails, raise HTTPForbidden.

        return method

    @staticmethod
    def _parse_request_headers(request: web.Request):
        """Parse Access-Control-Request-Headers header or the preflight request

        Returns set of headers in upper case.
        """
        headers = request.headers.get(hdrs.ACCESS_CONTROL_REQUEST_HEADERS)
        if headers is None:
            return frozenset()

        # FIXME: validate each header string, if parsing fails, raise
        # HTTPForbidden.
        # FIXME: check, that headers split and stripped correctly (according
        # to ABNF).
        headers = (h.strip(" \t").upper() for h in headers.split(","))
        # pylint: disable=bad-builtin
        return frozenset(filter(None, headers))

    @asyncio.coroutine
    def _preflight_handler(self, request: web.Request):
        """CORS preflight request handler"""
        route = request.match_info.route
        config, allowed_methods = self._preflight_route_settings[route]

        # Handle according to part 6.2 of the CORS specification.

        origin = request.headers.get(hdrs.ORIGIN)
        if origin is None:
            # Terminate CORS according to CORS 6.2.1.
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "origin header is not specified in the request")

        if not config:
            # No allowed origins for the route.
            # Terminate CORS according to CORS 6.2.1.
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "no origins are allowed")

        options = config.get(origin, config.get("*"))
        if options is None:
            # No configuration for the origin - deny.
            # Terminate CORS according to CORS 6.2.2.
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "origin '{}' is not allowed".format(origin))

        # CORS 6.2.3
        request_method = self._parse_request_method(request)

        # CORS 6.2.4
        request_headers = self._parse_request_headers(request)

        # CORS 6.2.5
        if request_method not in allowed_methods:
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "request method '{}' is not allowed".format(
                         request_method))

        # CORS 6.2.6
        if options.allow_headers == "*":
            pass
        else:
            disallowed_headers = request_headers - options.allow_headers
            if disallowed_headers:
                raise web.HTTPForbidden(
                    text="CORS preflight request failed: "
                         "headers are not allowed: {}".format(
                             ", ".join(disallowed_headers)))

        # Ok, CORS actual request with specified in the preflight request
        # parameters is allowed.
        # Set appropriate headers and return 200 response.

        response = web.Response()

        # CORS 6.2.7
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = origin
        if options.allow_credentials:
            # Set allowed credentials.
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS] = _TRUE

        # CORS 6.2.8
        if options.max_age is not None:
            response.headers[hdrs.ACCESS_CONTROL_MAX_AGE] = \
                str(options.max_age)

        # CORS 6.2.9
        # TODO: more optimal for client preflight request cache would be to
        # respond with ALL allowed methods.
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_METHODS] = request_method

        # CORS 6.2.10
        if request_headers:
            # Note: case of the headers in the request is changed, but this
            # shouldn't be a problem, since the headers should be compared in
            # the case-insensitive way.
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] = \
                ",".join(request_headers)

        return response


def setup(app: web.Application, *, defaults: dict=None) -> CorsConfig:
    """Setup CORS processing for the application.

    To enable CORS for a resource you need to explicitly add route for
    that resource using `CorsConfig.add()` method::

        app = aiohttp.web.Application(
        cors = aiohttp_cors.setup(app)
        cors.add(
            app.router.add_route("GET", "/resource", handler),
            {
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*"),
            })

    :param app:
        The application for which CORS will be configured.
    :param defaults:
        Default settings for origins.
    )
    """
    cors = CorsConfig(app, defaults=defaults)
    app[APP_CONFIG_KEY] = cors
    return cors
