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

from aiohttp import web

from .router_adapter import AbstractRouterAdapter

__all__ = ("UrlDistatcherRouterAdapter",)


class UrlDistatcherRouterAdapter(AbstractRouterAdapter):
    """AbstractRouterAdapter for aiohttp.web.UrlDispatcher"""
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
                method, handler, route.name, route._pattern, route._formatter)
            self._router.register_route(new_route)

        elif isinstance(route, web.StaticRoute):
            # TODO: Use custom matches that uses `str.startswith()` if
            # regexp performance is not enough.
            pattern = re.compile("^" + re.escape(route._prefix))
            new_route = web.DynamicRoute(
                method, handler, route.name, pattern, "")
            self._router.register_route(new_route)

        else:
            raise RuntimeError("Unhandled route type", route)

        return new_route
