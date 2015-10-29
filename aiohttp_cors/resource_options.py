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

"""Resource CORS options class definition.
"""

import numbers
import collections.abc

__all__ = ("ResourceOptions",)


class ResourceOptions:
    """Resource CORS options.

    Resource is already bound to specific path and HTTP method.

    The options accessors are part of the private interface and optimized for
    faster request processing.
    """

    __slots__ = (
        "_allow_credentials", "_expose_headers", "_allow_headers", "_max_age")

    def __init__(self, *, allow_credentials=False, expose_headers=(),
                 allow_headers=(), max_age=None):
        """Construct resource CORS options.

        :param allow_credentials:
            Is passing client credentials to the resource from other origin
            is allowed.
            See <http://www.w3.org/TR/cors/#user-credentials> for
            the definition.
        :type allow_credentials: bool
        :param expose_headers:
            Server headers that are allowed to be exposed to the client.
            Simple response headers are excluded from this set, see
            <http://www.w3.org/TR/cors/#list-of-exposed-headers>.
        :type expose_headers: sequence of strings or ``*`` string.
        :param allow_headers:
            Client headers that are allowed to be passed to the resource.
            See <http://www.w3.org/TR/cors/#list-of-headers>.
        :type allow_headers: sequence of strings or ``*`` string.
        :param max_age:
            How long the results of a preflight request can be cached in a
            preflight result cache (in seconds).
            See <http://www.w3.org/TR/cors/#http-access-control-max-age>.
        """
        # TODO: storing precomputed values looks like premature optimization.
        # Benchmarks should be done, maybe this optimization not worth it.

        if not isinstance(allow_credentials, bool):
            raise ValueError(
                "'allow_credentials' must be boolean, "
                "got '{}'".format(allow_credentials))
        self._allow_credentials = allow_credentials

        # `expose_headers` is either "*", or string with comma separated
        # headers.
        if expose_headers == "*":
            self._expose_headers = expose_headers
        elif (not isinstance(expose_headers, collections.abc.Sequence) or
              isinstance(expose_headers, str)):
            raise ValueError(
                "'expose_headers' must be either '*', or sequence of strings, "
                "got '{}'".format(expose_headers))
        elif expose_headers:
            # "Access-Control-Expose-Headers" ":" #field-name
            # TODO: Check that headers are valid.
            # TODO: Remove headers that in the _SIMPLE_RESPONSE_HEADERS set
            # according to
            # <http://www.w3.org/TR/cors/#list-of-exposed-headers>.
            self._expose_headers = ",".join(expose_headers)
        else:
            self._expose_headers = None

        # `allow_headers` is either "*", or set of headers in upper case.
        if allow_headers == "*":
            self._allow_headers = allow_headers
        elif (not isinstance(expose_headers, collections.abc.Sequence) or
              isinstance(expose_headers, str)):
            raise ValueError(
                "'allow_headers' must be either '*', or sequence of strings, "
                "got '{}'".format(allow_headers))
        else:
            # TODO: Check that headers are valid.
            self._allow_headers = frozenset(h.upper() for h in allow_headers)

        if max_age is None:
            self._max_age = None
        else:
            if not isinstance(max_age, numbers.Integral) or max_age < 0:
                raise ValueError(
                    "'max_age' must be non-negative integer, "
                    "got '{}'".format(max_age))
            self._max_age = str(max_age)

    @property
    def allow_credentials(self):
        """Is passing client credentials to the resource from other origin
        is allowed.

        :rtype: bool
        """
        return self._allow_credentials

    @property
    def expose_headers(self):
        """Server headers that are allowed to be exposed to the client.

        :returns:
            Non-empty string with comma-separated header names,
            or "*", or None.
        """
        return self._expose_headers

    @property
    def allow_headers(self):
        """Client headers that are allowed to be passed to the resource.

        :returns:
            "*", or set of uppercase strings.
        """
        return self._allow_headers

    @property
    def max_age(self):
        """How long a client can cache a preflight response for the resource.

        :returns:
            string representation of MaxAge.
        :rtype: str
        """
        return self._max_age
