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

"""AbstractRouterAdapter for aiohttp.web.UrlDispatcher.
"""

import re
from pkg_resources import parse_version

import aiohttp
from aiohttp import web

from .abc import AbstractRouterAdapter

__all__ = ("UrlDispatcherRouterAdapter",)


_AIOHTTP_0_21 = parse_version(aiohttp.__version__) >= parse_version('0.21.0')


# Router adapter for aiohttp < 0.21.0
class _UrlDispatcherRouterAdapter_v20(AbstractRouterAdapter):
    """Router adapter for aiohttp.web.UrlDispatcher"""
    def __init__(self, router: web.UrlDispatcher):
        self._router = router

    def route_methods(self, route: web.Route):
        """Returns list of HTTP methods that route handles"""
        return [route.method]

    def add_options_method_handler(self, route: web.Route, handler):
        method = "OPTIONS"

        if isinstance(route, web.PlainRoute):
            new_route = self._router.add_route(method, route._path, handler)

        elif isinstance(route, web.DynamicRoute):
            new_route = web.DynamicRoute(
                method, handler, None, route._pattern, route._formatter)
            self._router.register_route(new_route)

        elif isinstance(route, web.StaticRoute):
            # TODO: Use custom matches that uses `str.startswith()` if
            # regexp performance is not enough.
            pattern = re.compile("^" + re.escape(route._prefix))
            new_route = web.DynamicRoute(
                method, handler, None, pattern, "")
            self._router.register_route(new_route)

        else:
            raise RuntimeError("Unhandled route type", route)

        return new_route


# Router adapter for aiohttp >= 0.21.0
class _UrlDispatcherRouterAdapter_v21(AbstractRouterAdapter):
    """Router adapter for aiohttp.web.UrlDispatcher"""
    def __init__(self, router: web.UrlDispatcher):
        self._router = router

    def route_methods(self, route):
        """Returns list of HTTP methods that route handles"""
        return [route.method]

    def add_options_method_handler(self, route, handler):
        method = "OPTIONS"

        # TODO: Use web.ResourceRoute when this issue will be fixed:
        # <https://github.com/KeepSafe/aiohttp/pull/767>
        from aiohttp.web_urldispatcher import ResourceRoute

        if isinstance(route, ResourceRoute):
            # Route added through Resource API.
            new_route = route.resource.add_route(method, handler)

        elif isinstance(route, web.StaticRoute):
            # Route added through add_static() - not handled as ResourceRoute
            # in aiohttp 0.21.0.

            # TODO: Use custom matches that uses `str.startswith()` if
            # regexp performance is not enough.
            pattern = re.compile("^" + re.escape(route._prefix))
            new_route = web.DynamicRoute(
                method, handler, None, pattern, "")
            self._router.register_route(new_route)

        elif isinstance(route, web.PlainRoute):
            # May occur only if user manually creates PlainRoute.
            new_route = self._router.add_route(method, route._path, handler)

        elif isinstance(route, web.DynamicRoute):
            # May occur only if user manually creates DynamicRoute.
            new_route = web.DynamicRoute(
                method, handler, None, route._pattern, route._formatter)
            self._router.register_route(new_route)

        else:
            raise RuntimeError("Unhandled route type", route)

        return new_route


if _AIOHTTP_0_21:
    UrlDispatcherRouterAdapter = _UrlDispatcherRouterAdapter_v21
else:
    UrlDispatcherRouterAdapter = _UrlDispatcherRouterAdapter_v20
