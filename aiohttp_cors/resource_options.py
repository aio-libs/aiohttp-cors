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
import collections
import collections.abc

__all__ = ("ResourceOptions",)


class ResourceOptions(collections.namedtuple(
        "Base",
        ("allow_credentials", "expose_headers", "allow_headers", "max_age"))):
    """Resource CORS options."""

    __slots__ = ()

    def __init__(self, *, allow_credentials=False, expose_headers=(),
                 allow_headers=(), max_age=None):
        """Construct resource CORS options.

        Options will be normalized.

        :param allow_credentials:
            Is passing client credentials to the resource from other origin
            is allowed.
            See <http://www.w3.org/TR/cors/#user-credentials> for
            the definition.
        :type allow_credentials: bool
            Is passing client credentials to the resource from other origin
            is allowed.
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
        super().__init__()

    def __new__(cls, *, allow_credentials=False, expose_headers=(),
                allow_headers=(), max_age=None):
        """Normalize source parameters and store them in namedtuple."""

        if not isinstance(allow_credentials, bool):
            raise ValueError(
                "'allow_credentials' must be boolean, "
                "got '{}'".format(allow_credentials))
        _allow_credentials = allow_credentials

        # `expose_headers` is either "*", or string with comma separated
        # headers.
        if expose_headers == "*":
            _expose_headers = expose_headers
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
            _expose_headers = frozenset(expose_headers)
        else:
            _expose_headers = frozenset()

        # `allow_headers` is either "*", or set of headers in upper case.
        if allow_headers == "*":
            _allow_headers = allow_headers
        elif (not isinstance(allow_headers, collections.abc.Sequence) or
              isinstance(allow_headers, str)):
            raise ValueError(
                "'allow_headers' must be either '*', or sequence of strings, "
                "got '{}'".format(allow_headers))
        else:
            # TODO: Check that headers are valid.
            _allow_headers = frozenset(h.upper() for h in allow_headers)

        if max_age is None:
            _max_age = None
        else:
            if not isinstance(max_age, numbers.Integral) or max_age < 0:
                raise ValueError(
                    "'max_age' must be non-negative integer, "
                    "got '{}'".format(max_age))
            _max_age = max_age

        return super().__new__(
            cls,
            allow_credentials=_allow_credentials,
            expose_headers=_expose_headers,
            allow_headers=_allow_headers,
            max_age=_max_age)
