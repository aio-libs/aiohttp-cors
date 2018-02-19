import asyncio
from unittest import mock

import pytest

from aiohttp_cors.preflight_handler import _PreflightHandler


@asyncio.coroutine
def test_raises_when_handler_not_extend():
    request = mock.Mock()
    handler = _PreflightHandler()
    with pytest.raises(NotImplementedError):
        yield from handler._get_config(request, 'origin', 'GET')
