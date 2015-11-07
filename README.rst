CORS support for aiohttp
========================

``aiohttp_cors`` library implements
`Cross Origin Resource Sharing (CORS) <cors_>`__
support for `aiohttp <aiohttp_>`__
asyncio-powered asynchronous HTTP server.

Jump directly to `Usage`_ part to see how to use ``aiohttp_cors``.

Same-origin policy
==================

Web security model is tightly connected to
`Same-origin policy (SOP) <sop_>`__.
In short: web pages cannot *Read* resources which origin
doesn't match origin of requested page, but can *Embed* (or *Execute*)
resources and have limited ability to *Write* resources.

Origin of a page is defined in the `Standard <cors_>`__ as tuple
``(schema, host, port)``
(there is a notable exception with Internet Explorer: it doesn't use port to
define origin, but uses it's own
`Security Zones <https://msdn.microsoft.com/en-us/library/ms537183.aspx>`__).

Can *Embed* means that resource from other origin can be embedded into
the page,
e.g. by using ``<script src="...">``, ``<img src="...">``,
``<iframe src="...">``.

Cannot *Read* means that resource from other origin *source* cannot be
obtained by page
(*source* — any information that would allow to reconstruct resource).
E.g. the page can *Embed* image with ``<img src="...">``,
but it can't get information about specific pixels, so page can't reconstruct
original image
(though some information from the other resource may still be leaked:
e.g. the page can read embedded image dimensions).

Limited ability to *Write* means, that the page can send POST requests to
other origin with limited set of ``Content-Type`` values and headers.

Restriction to *Read* resource from other origin is related to authentication
mechanism that is used by browsers:
when browser reads (downloads) resource he automatically sends all security
credentials that user previously authorized for that resource
(e.g. cookies, HTTP Basic Authentication).

For example, if *Read* would be allowed and user is authenticated
in some internet banking,
malicious page would be able to embed internet banking page with ``iframe``
(since authentication is done by the browser it may be embedded as if
user is directly navigated to internet banking page),
then read user private information by reading *source* of the embedded page
(which may be not only source code, but, for example,
screenshot of the embedded internet banking page).

Cross-origin resource sharing
=============================

`Cross-origin Resource Sharing (CORS) <cors_>`__ allows to override
SOP for specific resources.

In short, CORS works in the following way.

When page ``https://client.example.com`` request (*Read*) resource
``https://server.example.com/resource`` that have other origin,
browser implicitly appends ``Origin: https://client.example.com`` header
to the HTTP request,
effectively requesting server to give read permission for
the resource to the ``https://client.example.com`` page::

    GET /resource HTTP/1.1
    Origin: https://client.example.com
    Host: server.example.com

If server allows access from the page to the resource, it responds with
resource with ``Access-Control-Allow-Origin: https://client.example.com``
HTTP header
(optionally allowing exposing custom server headers to the page and
enabling use of the user credentials on the server resource)::

    Access-Control-Allow-Origin: https://client.example.com
    Access-Control-Allow-Credentials: true
    Access-Control-Expose-Headers: X-Server-Header

Browser checks, if server responded with proper
``Access-Control-Allow-Origin`` header and accordingly allows or denies
access for the obtained resource to the page.

CORS specification designed in a way that servers that are not aware
of CORS will not expose any additional information, except allowed by the
SOP.

To request resources with custom headers or using custom HTTP methods
(e.g. ``PUT``, ``DELETE``) that are not allowed by SOP,
CORS-enabled browser first send *preflight request* to the
resource using ``OPTIONS`` method, in which he queries access to the resource
with specific method and headers::

    OPTIONS / HTTP/1.1
    Origin: https://client.example.com
    Access-Control-Request-Method: PUT
    Access-Control-Request-Headers: X-Client-Header

CORS-enabled server responds is requested method is allowed and which of
the specified headers are allowed::

    Access-Control-Allow-Origin: https://client.example.com
    Access-Control-Allow-Credentials: true
    Access-Control-Allow-Methods: PUT
    Access-Control-Allow-Headers: X-Client-Header
    Access-Control-Max-Age: 3600

Browser checks response to preflight request, and, if actual request allowed,
does actual request.

Installation
============

You can install ``aiohttp_cors`` as a typical Python library from PyPI or
from git:

.. code-block:: bash

    $ pip install aiohttp_cors

Note that ``aiohttp_cors`` requires versions of Python >= 3.4.1 and
``aiohttp`` >= 0.18.0.

Usage
=====

To use ``aiohttp_cors`` you need to configure the application and
enable CORS on routes of resources that you want to expose:

.. code-block:: python

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

    # `aiohttp_cors.setup` returns `aiohttp_cors.CorsConfig` instance.
    # The `cors` instance will store CORS configuration for the
    # application.
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

Each route has it's own CORS configuration passed in ``CorsConfig.add()``
method.
CORS configuration is a mapping from origins to options for that origins.

In the example above CORS is configured for the resource under path ``/hello``
and HTTP method ``GET``, and in the context of CORS:

* This resource will be available using CORS only to
  ``http://client.example.org`` origin.

* Passing of credentials to this resource will be allowed.

* The resource will expose to the client ``X-Custom-Server-Header``
  server header.

* The client will be allowed to pass ``X-Requested-With`` and
  ``Content-Type`` headers to the server.

* Preflight requests will be allowed to be cached by client for ``3600``
  seconds.

Resource will be available only to the explicitly specified origins.
You can specify "all other origins" using special ``*`` origin:

.. code-block:: python

    cors.add(route, {
            "*":
                aiohttp_cors.ResourceOptions(allow_credentials=False),
            "http://client.example.org":
                aiohttp_cors.ResourceOptions(allow_credentials=True),
        })

Here the resource specified by ``route`` will be available to all origins with
disallowed credentials passing, and with allowed credentials passing only to
``http://client.example.org``.

By default ``ResourceOptions`` will be constructed without any allowed CORS
options.
This means, that resource will be available using CORS to specified origin,
but client will not be allowed to send either credentials,
or send non-simple headers, or read from server non-simple headers.

To enable sending or receiving all headers you can specify special value
``*`` instead of sequence of headers:

.. code-block:: python

    cors.add(route, {
            "http://client.example.org":
                aiohttp_cors.ResourceOptions(
                    expose_headers="*",
                    allow_headers="*"),
        })

You can specify default CORS-enabled resource options using
``aiohttp_cors.setup()``'s ``defaults`` argument:

.. code-block:: python

    cors = aiohttp_cors.setup(app, defaults={
            # Allow all to read all CORS-enabled resources from
            # http://client.example.org.
            "http://client.example.org": aiohttp_cors.ResourceOptions(),
        })

    # Enable CORS on resources.

    # According to defaults POST and PUT will be available only to
    # "http://client.example.org".
    cors.add(app.router.add_route("POST", "/hello", handler_post))
    cors.add(app.router.add_route("PUT", "/hello", handler_put))

    # In addition to "http://client.example.org", GET request will be allowed
    # from "http://other-client.example.org" origin.
    cors.add(app.router.add_route("GET", "/hello", handler), {
            "http://other-client.example.org"
        })

    # CORS will be enabled only on the resources added to `CorsConfig`,
    # so following resource will be NOT CORS-enabled.
    app.router.add_route("GET", "/private", handler))

Here is an example of how to enable CORS for all origins with all CORS
features:

.. code-block:: python

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })

    # Add all resources to `CorsConfig`.
    cors.add(app.router.add_route("GET", "/hello", handler_get))
    cors.add(app.router.add_route("PUT", "/hello", handler_put))
    cors.add(app.router.add_route("POST", "/hello", handler_put))
    cors.add(app.router.add_route("DELETE", "/hello", handler_delete))


Also you can enable CORS for all added routes by accessing routes list
in router:

.. code-block:: python

    # Setup application routes.
    app.router.add_route("GET", "/hello", handler_get)
    app.router.add_route("PUT", "/hello", handler_put)
    app.router.add_route("POST", "/hello", handler_put)
    app.router.add_route("DELETE", "/hello", handler_delete)

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)

Security
========

TODO: fill this

Development
===========

TODO:

To run run Selenium tests with Firefox web driver you need to install Firefox.

To run run Selenium tests with Chromium web driver you need to:

1. Install Chrome driver. On Ubuntu 14.04 it's in ``chromium-chromedriver``
   package.

2. Either add ``chromedriver`` to PATH or set ``WEBDRIVER_CHROMEDRIVER_PATH``
   environment variable to ``chromedriver``, e.g. on Ubuntu 14.04
   ``WEBDRIVER_CHROMEDRIVER_PATH=/usr/lib/chromium-browser/chromedriver``.


Bugs
====

Please report bugs, issues, feature requests, etc. on 
`GitHub <https://github.com/aio-libs/aiohttp_cors/issues>`__.


License
=======

Copyright 2015 Vladimir Rutsky <vladimir@rutsky.org>.

Licensed under the
`Apache License, Version 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`__,
see ``LICENSE`` file for details.

.. _cors: http://www.w3.org/TR/cors/
.. _aiohttp: https://github.com/KeepSafe/aiohttp/
.. _sop: https://en.wikipedia.org/wiki/Same-origin_policy
