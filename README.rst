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


Usage
=====

.. TODO:: fill this

License
=======

Copyright 2015 Vladimir Rutsky <vladimir@rutsky.org>.

Licensed under the
`Apache License, Version 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`__,
see ``LICENSE`` file for details.

.. _cors: http://www.w3.org/TR/cors/
.. _aiohttp: https://github.com/KeepSafe/aiohttp/
.. _sop: https://en.wikipedia.org/wiki/Same-origin_policy
