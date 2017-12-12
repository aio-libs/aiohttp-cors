import asyncio
import collections

from aiohttp import hdrs, web

# Positive response to Access-Control-Allow-Credentials
_TRUE = "true"


def custom_cors(config):
    def wrapper(function):
        name = "{}_cors_config".format(function.__name__)
        setattr(function, name, config)
        return function
    return wrapper


class CorsViewMixin:
    cors_config = None

    @classmethod
    def get_request_config(cls, request, request_method):
        try:
            from . import APP_CONFIG_KEY
            cors = request.app[APP_CONFIG_KEY]
        except KeyError:
            raise ValueError("aiohttp-cors is not configured.")

        method = getattr(cls, request_method.lower(), None)

        if not method:
            raise KeyError()

        config_property_key = "{}_cors_config".format(request_method.lower())

        custom_config = getattr(method, config_property_key, None)
        if not custom_config:
            custom_config = {}

        class_config = cls.cors_config
        if not class_config:
            class_config = {}

        return collections.ChainMap(custom_config, class_config, cors.defaults)

    @property
    def request_method(self):
        """Parse Access-Control-Request-Method header of the preflight request
        """
        # CORS 6.2.3. Doing it out of order is not an error.
        method = self.request.headers.get(hdrs.ACCESS_CONTROL_REQUEST_METHOD)
        if method is None:
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "'Access-Control-Request-Method' header is not specified")

        # FIXME: validate method string (ABNF: method = token), if parsing
        # fails, raise HTTPForbidden.

        return method

    @property
    def request_headers(self):
        """Parse Access-Control-Request-Headers header or the preflight request

        Returns set of headers in upper case.
        """
        # CORS 6.2.4
        headers = self.request.headers.get(hdrs.ACCESS_CONTROL_REQUEST_HEADERS)
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
    def options(self):
        """CORS preflight request handler"""
        # Handle according to part 6.2 of the CORS specification.

        origin = self.request.headers.get(hdrs.ORIGIN)
        if origin is None:
            # Terminate CORS according to CORS 6.2.1.
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "origin header is not specified in the request")

        # CORS 6.2.5. Doing it out of order is not an error.
        try:
            config = self.get_request_config(self.request,
                                             self.request_method)
        except KeyError:
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "request method {!r} is not allowed "
                     "for {!r} origin".format(self.request_method, origin))

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

        # CORS 6.2.6
        if options.allow_headers == "*":
            pass
        else:
            disallowed_headers = self.request_headers - options.allow_headers
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
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_METHODS] = \
            self.request_method

        # CORS 6.2.10
        if self.request_headers:
            # Note: case of the headers in the request is changed, but this
            # shouldn't be a problem, since the headers should be compared in
            # the case-insensitive way.
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] = \
                ",".join(self.request_headers)

        return response
