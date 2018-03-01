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

"""System test using real browser.
"""

import os
import json
import asyncio
import socket
import pathlib
import logging
import webbrowser

from aiohttp import web, hdrs
import pytest

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from aiohttp_cors import setup as _setup, ResourceOptions, CorsViewMixin


class _ServerDescr:
    """Auxiliary class for storing server info"""

    def __init__(self):
        self.app = None
        self.cors = None
        self.handler = None
        self.server = None
        self.url = None


class IntegrationServers:
    """Integration servers starting/stopping manager"""

    def __init__(self, use_resources, use_webview, *, loop=None):
        self.servers = {}

        self.loop = loop
        if self.loop is None:
            self.loop = asyncio.get_event_loop()

        self.use_resources = use_resources
        self.use_webview = use_webview

        self._logger = logging.getLogger("IntegrationServers")

    @property
    def origin_server_url(self):
        return self.servers["origin"].url

    async def start_servers(self):
        test_page_path = pathlib.Path(__file__).with_name("test_page.html")

        async def handle_test_page(request: web.Request) -> web.StreamResponse:
            with test_page_path.open("r", encoding="utf-8") as f:
                return web.Response(
                    text=f.read(),
                    headers={hdrs.CONTENT_TYPE: "text/html"})

        async def handle_no_cors(request: web.Request) -> web.StreamResponse:
            return web.Response(
                text="""{"type": "no_cors.json"}""",
                headers={hdrs.CONTENT_TYPE: "application/json"})

        async def handle_resource(request: web.Request) -> web.StreamResponse:
            return web.Response(
                text="""{"type": "resource"}""",
                headers={hdrs.CONTENT_TYPE: "application/json"})

        async def handle_servers_addresses(
                request: web.Request) -> web.StreamResponse:
            servers_addresses = \
                {name: descr.url for name, descr in self.servers.items()}
            return web.Response(
                text=json.dumps(servers_addresses))

        class ResourceView(web.View, CorsViewMixin):

            async def get(self) -> web.StreamResponse:
                return await handle_resource(self.request)

        # For most resources:
        # "origin" server has no CORS configuration.
        # "allowing" server explicitly allows CORS requests to "origin" server.
        # "denying" server explicitly disallows CORS requests to "origin"
        # server.
        # "free_for_all" server allows CORS requests for all origins server.
        # "no_cors" server has no CORS configuration.
        cors_server_names = ["allowing", "denying", "free_for_all"]
        server_names = cors_server_names + ["origin", "no_cors"]

        for server_name in server_names:
            assert server_name not in self.servers
            self.servers[server_name] = _ServerDescr()

        server_sockets = {}

        # Create applications and sockets.
        for server_name, server_descr in self.servers.items():
            server_descr.app = web.Application()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            sock.listen(10)
            server_sockets[server_name] = sock

            hostaddr, port = sock.getsockname()
            server_descr.url = "http://{host}:{port}".format(
                host=hostaddr, port=port)

        # Server test page from origin server.
        self.servers["origin"].app.router.add_route(
            "GET", "/", handle_test_page)
        self.servers["origin"].app.router.add_route(
            "GET", "/servers_addresses", handle_servers_addresses)

        # Add routes to all servers.
        for server_name in server_names:
            app = self.servers[server_name].app
            app.router.add_route("GET", "/no_cors.json", handle_no_cors)
            if self.use_webview:
                app.router.add_route("*", "/cors_resource", ResourceView,
                                     name="cors_resource")
            else:
                app.router.add_route("GET", "/cors_resource", handle_resource,
                                     name="cors_resource")

        cors_default_configs = {
            "allowing": {
                self.servers["origin"].url:
                    ResourceOptions(
                        allow_credentials=True, expose_headers="*",
                        allow_headers="*")
            },
            "denying": {
                # Allow requests to other than "origin" server.
                self.servers["allowing"].url:
                    ResourceOptions(
                        allow_credentials=True, expose_headers="*",
                        allow_headers="*")
            },
            "free_for_all": {
                "*":
                    ResourceOptions(
                        allow_credentials=True, expose_headers="*",
                        allow_headers="*")
            },
        }

        # Configure CORS.
        for server_name, server_descr in self.servers.items():
            default_config = cors_default_configs.get(server_name)
            if default_config is None:
                continue
            server_descr.cors = _setup(
                server_descr.app, defaults=default_config)

        # Add CORS routes.
        for server_name in cors_server_names:
            server_descr = self.servers[server_name]
            # TODO: Starting from aiohttp 0.21.0 name-based access returns
            # Resource, not Route. Manually get route while aiohttp_cors
            # doesn't support configuring for Resources.
            resource = server_descr.app.router["cors_resource"]
            route = next(iter(resource))
            if self.use_resources:
                server_descr.cors.add(resource)
                server_descr.cors.add(route)

            elif self.use_webview:
                server_descr.cors.add(route)

            else:
                server_descr.cors.add(route)

        # Start servers.
        for server_name, server_descr in self.servers.items():
            handler = server_descr.app.make_handler()
            server = await self.loop.create_server(
                handler,
                sock=server_sockets[server_name])
            server_descr.handler = handler
            server_descr.server = server

            self._logger.info("Started server '%s' at '%s'",
                              server_name, server_descr.url)

    async def stop_servers(self):
        for server_descr in self.servers.values():
            server_descr.server.close()
            await server_descr.handler.shutdown()
            await server_descr.server.wait_closed()
            await server_descr.app.cleanup()

        self.servers = {}


def _get_chrome_driver():
    driver_path_env = "WEBDRIVER_CHROMEDRIVER_PATH"

    if driver_path_env in os.environ:
        driver = webdriver.Chrome(executable_path=os.environ[driver_path_env])
    else:
        driver = webdriver.Chrome()

    return driver


@pytest.fixture(params=[(False, False),
                        (True, False),
                        (False, True)])
def server(request, loop):
    async def inner():
        # to grab implicit loop
        return IntegrationServers(*request.param)
    return loop.run_until_complete(inner())


@pytest.fixture(params=[webdriver.Firefox,
                        _get_chrome_driver])
def driver(request):
    try:
        driver = request.param()
    except selenium.common.exceptions.WebDriverException:
        pytest.skip("Driver is not supported")

    yield driver
    driver.close()


async def test_in_webdriver(driver, server):
    loop = asyncio.get_event_loop()
    await server.start_servers()

    def selenium_thread():
        driver.get(server.origin_server_url)
        assert "aiohttp_cors" in driver.title

        wait = WebDriverWait(driver, 10)

        run_button = wait.until(EC.element_to_be_clickable(
            (By.ID, "runTestsButton")))

        # Start tests.
        run_button.send_keys(Keys.RETURN)

        # Wait while test will finish (until clear button is not
        # activated).
        wait.until(EC.element_to_be_clickable(
            (By.ID, "clearResultsButton")))

        # Get results json
        results_area = driver.find_element_by_id("results")

        return json.loads(results_area.get_attribute("value"))

    try:
        results = await loop.run_in_executor(
            None, selenium_thread)

        assert results["status"] == "success"
        for test_name, test_data in results["data"].items():
            assert test_data["status"] == "success"

    finally:
        await server.stop_servers()


def _run_integration_server():
    """Runs integration server for interactive debugging."""

    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger("run_integration_server")

    loop = asyncio.get_event_loop()

    servers = IntegrationServers(False, True)
    logger.info("Starting integration servers...")
    loop.run_until_complete(servers.start_servers())

    try:
        webbrowser.open(servers.origin_server_url)
    except webbrowser.Error:
        pass

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stopping integration servers...")
        loop.run_until_complete(servers.stop_servers())


if __name__ == "__main__":
    # This module can be run in the following way:
    #     $ python -m tests.integration.test_real_browser
    # from aiohttp_cors root directory.
    _run_integration_server()
