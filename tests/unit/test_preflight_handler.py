from unittest import mock

import pytest

from aiohttp_cors.preflight_handler import _PreflightHandler


async def test_raises_when_handler_not_extend():
    request = mock.Mock()
    handler = _PreflightHandler()
    with pytest.raises(NotImplementedError):
        await handler._get_config(request, 'origin', 'GET')
