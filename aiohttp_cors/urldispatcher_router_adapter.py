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
import asyncio
import collections
import re

from typing import Union

from aiohttp import web
from aiohttp import hdrs

from .abc import AbstractRouterAdapter


# There several usage patterns of routes which should be handled
# differently.
#
# 1. Using new Resources:
#
#     resource = app.router.add_resource(path)
#     cors.add(resource, resource_defaults=...)
#     cors.add(resource.add_route(method1, handler1), config=...)
#     cors.add(resource.add_route(method2, handler2), config=...)
#     cors.add(resource.add_route(method3, handler3), config=...)
#
# Here all related Routes (i.e. routes with the same path) are in
# a single Resource.
#
# 2. Using `router.add_static()`:
#
#     route1 = app.router.add_static(
#         "/images", "/usr/share/app/images/")
#     cors.add(route1, config=...)
#
# Here old-style `web.StaticRoute` is created and wrapped with
# `web.ResourceAdapter`.
#
# 3. Using old `router.add_route()`:
#
#     cors.add(app.router.add_route(method1, path, hand1), config=...)
#     cors.add(app.router.add_route(method2, path, hand2), config=...)
#     cors.add(app.router.add_route(method3, path, hand3), config=...)
#
# This creates three Resources with single Route in each.
#
# 4. Using deprecated `register_route` with manually created
#    `web.Route`:
#
#     route1 = RouteSubclass(...)
#     app.router.register_route(route1)
#     cors.add(route1, config=...)
#
# Here old-style route is wrapped with `web.ResourceAdapter`.
#
# Preflight requests is roughly an OPTIONS request with query
# "is specific HTTP method is allowed".
# In order to properly handle preflight request we need to know which
# routes have enabled CORS on the request path and CORS configuration
# for requested HTTP method.
#
# In case of new usage pattern it's simple: we need to take a look at
# self._resource_config[resource][method] for the processing resource.
#
# In case of old usage pattern we need to iterate over routes with
# enabled CORS and check is requested path and HTTP method is accepted
# by a route.


class _ResourceConfig:
    def __init__(self, default_config):
        # Resource default config.
        self.default_config = default_config

        # HTTP method to route configuration.
        self.method_config = {}


class ResourcesUrlDispatcherRouterAdapter(AbstractRouterAdapter):
    """Adapter for `UrlDispatcher` for Resources-based routing only.

    Should be used with routes added in the following way:

        resource = app.router.add_resource(path)
        cors.add(resource, resource_defaults=...)
        cors.add(resource.add_route(method1, handler1), config=...)
        cors.add(resource.add_route(method2, handler2), config=...)
        cors.add(resource.add_route(method3, handler3), config=...)
    """

    def __init__(self,
                 router: web.UrlDispatcher,
                 defaults):
        """
        :param defaults:
            Default CORS configuration.
        """
        self._router = router

        # Default configuration for all routes.
        self._default_config = defaults

        # Mapping from Resource to _ResourceConfig.
        self._resource_config = {}

        self._resources_with_preflight_handlers = set()
        self._preflight_routes = set()

    def add_preflight_handler(
            self,
            routing_entity: Union[web.Resource, web.StaticResource,
                                  web.ResourceRoute],
            handler):
        """Add OPTIONS handler for all routes defined by `routing_entity`.

        Does nothing if CORS handler already handles routing entity.
        Should fail if there are conflicting user-defined OPTIONS handlers.
        """

        if isinstance(routing_entity, web.Resource):
            resource = routing_entity

            # Add preflight handler for Resource, if not yet added.

            if resource in self._resources_with_preflight_handlers:
                # Preflight handler already added for this resource.
                return

            preflight_route = resource.add_route(hdrs.METH_OPTIONS, handler)
            self._preflight_routes.add(preflight_route)
            self._resources_with_preflight_handlers.add(resource)

        elif isinstance(routing_entity, web.StaticResource):
            resource = routing_entity

            # Add preflight handler for Resource, if not yet added.

            if resource in self._resources_with_preflight_handlers:
                # Preflight handler already added for this resource.
                return

            resource.set_options_route(handler)
            preflight_route = resource._routes[hdrs.METH_OPTIONS]
            self._preflight_routes.add(preflight_route)
            self._resources_with_preflight_handlers.add(resource)

        elif isinstance(routing_entity, web.ResourceRoute):
            route = routing_entity

            # Preflight handler for Route's Resource already must be
            # configured.
            if not self.is_cors_for_resource(route.resource):
                raise ValueError(
                    "Can't setup CORS for {!r} request, "
                    "CORS must be enabled for route's resource first.".format(
                        route))

        else:
            raise ValueError(
                "Resource or ResourceRoute expected, got {!r}".format(
                    routing_entity))

    def is_cors_for_resource(self, resource: web.Resource) -> bool:
        """Is CORS is configured for the resource"""
        return resource in self._resources_with_preflight_handlers

    def _request_route(self, request: web.Request) -> web.ResourceRoute:
        match_info = request.match_info
        assert isinstance(match_info, web.UrlMappingMatchInfo)
        return match_info.route

    def _request_resource(self, request: web.Request) -> web.Resource:
        return self._request_route(request).resource

    def is_preflight_request(self, request: web.Request) -> bool:
        """Is `request` is a CORS preflight request."""

        return self._request_route(request) in self._preflight_routes

    def is_cors_enabled_on_request(self, request: web.Request) -> bool:
        """Is `request` is a request for CORS-enabled resource."""

        return self._request_resource(request) in self._resource_config

    def set_config_for_routing_entity(
            self,
            routing_entity: Union[web.Resource, web.StaticResource,
                                  web.ResourceRoute],
            config):
        """Record configuration for resource or it's route."""

        if isinstance(routing_entity, (web.Resource, web.StaticResource)):
            resource = routing_entity

            # Add resource configuration or fail if it's already added.
            if resource in self._resource_config:
                raise ValueError(
                    "CORS is already configured for {!r} resource.".format(
                        resource))

            self._resource_config[resource] = _ResourceConfig(
                default_config=config)

        elif isinstance(routing_entity, web.ResourceRoute):
            route = routing_entity

            # Add resource's route configuration or fail if it's already added.
            if route.resource not in self._resource_config:
                raise ValueError(
                    "Can't setup CORS for {!r} request, "
                    "CORS must be enabled for route's resource first.".format(
                        route))

            resource_config = self._resource_config[route.resource]

            if route.method in resource_config.method_config:
                raise ValueError(
                    "Can't setup CORS for {!r} route: CORS already "
                    "configured on resource {!r} for {} method".format(
                        route, route.resource, route.method))

            resource_config.method_config[route.method] = config

        else:
            raise ValueError(
                "Resource or ResourceRoute expected, got {!r}".format(
                    routing_entity))

    @asyncio.coroutine
    def get_preflight_request_config(
            self,
            preflight_request: web.Request,
            origin: str,
            requested_method: str):
        assert self.is_preflight_request(preflight_request)

        resource = self._request_resource(preflight_request)
        resource_config = self._resource_config[resource]
        defaulted_config = collections.ChainMap(
            resource_config.default_config,
            self._default_config)

        options = defaulted_config.get(origin, defaulted_config.get("*"))
        if options is not None and options.is_method_allowed(requested_method):
            # Requested method enabled for CORS in defaults, override it with
            # explicit route configuration (if any).
            route_config = resource_config.method_config.get(
                requested_method, {})

        else:
            # Requested method is not enabled in defaults.
            # Enable CORS for it only if explicit configuration exists.
            route_config = resource_config.method_config[requested_method]

        defaulted_config = collections.ChainMap(route_config, defaulted_config)

        return defaulted_config

    def get_non_preflight_request_config(self, request: web.Request):
        """Get stored CORS configuration for routing entity that handles
        specified request."""

        assert self.is_cors_enabled_on_request(request)

        resource = self._request_resource(request)
        resource_config = self._resource_config[resource]
        # Take Route config (if any) with defaults from Resource CORS
        # configuration and global defaults.
        defaulted_config = collections.ChainMap(
            resource_config.method_config.get(request.method, {}),
            resource_config.default_config,
            self._default_config)

        return defaulted_config


class OldRoutesUrlDispatcherRouterAdapter(AbstractRouterAdapter):
    """Adapter for `UrlDispatcher` for old-style routing only.

    In all use cases when Resource is not explicitly used,
    Resource will automatically allocated for old route.
    In this case all routes will have it's own resource, and to find
    related routes (routes that shares same path) we need to iterate over
    all routes with enabled CORS and check is they handle specific path.

    This whole class should go away when user will migrate to proper
    Resource/Route usage scheme.
    """

    def __init__(self,
                 router: web.UrlDispatcher,
                 defaults):
        """
        :param defaults:
            Default CORS configuration.
        """
        self._router = router

        # Default configuration for all routes.
        self._default_config = defaults

        # Mapping from route to config.
        self._route_config = collections.OrderedDict()

        self._preflight_routes = set()

    def add_preflight_handler(
            self,
            route: web.AbstractRoute,
            handler):
        """Add OPTIONS handler for same paths that `route` handles."""

        assert isinstance(route, web.AbstractRoute)

        if isinstance(route, web.ResourceRoute):
            # New-style route (which Resource is not used explicitly,
            # otherwise it would be handled by other adapter).
            preflight_route = route.resource.add_route(
                hdrs.METH_OPTIONS, handler)

        elif isinstance(route, web.Route):
            # Old-style route.

            if isinstance(route, web.StaticRoute):
                # TODO: Use custom matches that uses `str.startswith()`
                # if regexp performance is not enough.
                pattern = re.compile("^" + re.escape(route._prefix))
                preflight_route = web.DynamicRoute(
                    hdrs.METH_OPTIONS, handler, None, pattern, "")
                self._router.register_route(preflight_route)

            elif isinstance(route, web.PlainRoute):
                # May occur only if user manually creates PlainRoute.
                preflight_route = self._router.add_route(
                    hdrs.METH_OPTIONS, route._path, handler)

            elif isinstance(route, web.DynamicRoute):
                # May occur only if user manually creates DynamicRoute.
                preflight_route = web.DynamicRoute(
                    hdrs.METH_OPTIONS, handler, None,
                    route._pattern, route._formatter)
                self._router.register_route(preflight_route)

            else:
                raise RuntimeError(
                    "Unhandled deprecated route type {!r}".format(route))

        else:
            raise RuntimeError("Unhandled route type {!r}".format(route))

        self._preflight_routes.add(preflight_route)

    def _request_route(self, request: web.Request) -> web.ResourceRoute:
        match_info = request.match_info
        assert isinstance(match_info, web.UrlMappingMatchInfo)
        return match_info.route

    def is_preflight_request(self, request: web.Request) -> bool:
        """Is `request` is a CORS preflight request."""

        return self._request_route(request) in self._preflight_routes

    def is_cors_enabled_on_request(self, request: web.Request) -> bool:
        """Is `request` is a request for CORS-enabled resource."""

        return self._request_route(request) in self._route_config

    def set_config_for_routing_entity(
            self,
            route: web.AbstractRoute,
            config):
        """Record CORS configuration for route."""

        assert isinstance(route, web.AbstractRoute)

        if any(options.allow_methods is not None
               for options in config.values()):
            raise ValueError(
                "'allow_methods' parameter is not supported on old-style "
                "routes. You specified {!r} for {!r}. "
                "Use Resources to configure CORS.".format(
                    config, route))

        if route in self._route_config:
            raise ValueError(
                "CORS is already configured for {!r} route.".format(
                    route))

        self._route_config[route] = config

    @asyncio.coroutine
    def get_preflight_request_config(
            self,
            preflight_request: web.Request,
            origin: str,
            requested_method: str):
        assert self.is_preflight_request(preflight_request)

        request = preflight_request.clone(method=requested_method)
        for route, config in self._route_config.items():
            match_info, allowed_methods = yield from route.resource.resolve(
                request)
            if match_info is not None:
                return collections.ChainMap(config, self._default_config)
        else:
            raise KeyError

    def get_non_preflight_request_config(self, request: web.Request):
        """Get stored CORS configuration for routing entity that handles
        specified request."""

        assert self.is_cors_enabled_on_request(request)

        route = self._request_route(request)
        route_config = self._route_config[route]

        defaulted_config = collections.ChainMap(
            route_config, self._default_config)

        return defaulted_config
