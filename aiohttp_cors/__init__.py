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

"""CORS support for aiohttp."""

from collections.abc import Mapping
from typing import Any, Union

from aiohttp import web

from .__about__ import (
    __author__,
    __copyright__,
    __email__,
    __license__,
    __summary__,
    __title__,
    __uri__,
    __version__,
)
from .cors_config import CorsConfig
from .mixin import CorsViewMixin, custom_cors
from .resource_options import ResourceOptions

__all__ = (
    "CorsConfig",
    "CorsViewMixin",
    "ResourceOptions",
    "__author__",
    "__copyright__",
    "__email__",
    "__license__",
    "__summary__",
    "__title__",
    "__uri__",
    "__version__",
    "custom_cors",
    "setup",
)


APP_CONFIG_KEY: web.AppKey[CorsConfig] = web.AppKey("aiohttp_cors", CorsConfig)


def setup(
    app: web.Application,
    *,
    defaults: Mapping[str, Union[ResourceOptions, Mapping[str, Any]]] = None
) -> CorsConfig:
    """Setup CORS processing for the application.

    To enable CORS for a resource you need to explicitly add route for
    that resource using `CorsConfig.add()` method::

        app = aiohttp.web.Application()
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
