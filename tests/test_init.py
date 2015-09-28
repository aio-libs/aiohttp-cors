"""Test package metainformation
"""

import unittest
from pkg_resources import parse_version

import aiohttp_cors


class TestMetainformation(unittest.TestCase):
    """Test package metainformation"""
    # pylint: disable=no-self-use
    def test_version(self):
        """Test package version string"""
        parse_version(aiohttp_cors.__version__)
