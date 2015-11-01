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

import json
import asyncio
import pathlib
import logging
import webbrowser

from aiohttp import web, hdrs

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from aiohttp_cors import setup, ResourceOptions

from ..aio_test_base import create_server, AioTestBase, asynctest


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

    def __init__(self, *, loop=None):
        self.servers = {}

        self.loop = loop
        if self.loop is None:
            self.loop = asyncio.get_event_loop()

        self._logger = logging.getLogger("IntegrationServers")

    @property
    def origin_server_url(self):
        return self.servers["origin"].url

    @asyncio.coroutine
    def start_servers(self):
        test_page_path = pathlib.Path(__file__).with_name("test_page.html")

        @asyncio.coroutine
        def handle_test_page(request: web.Request) -> web.StreamResponse:
            with test_page_path.open("r", encoding="utf-8") as f:
                return web.Response(
                    text=f.read(),
                    headers={hdrs.CONTENT_TYPE: "text/html"})

        @asyncio.coroutine
        def handle_no_cors(request: web.Request) -> web.StreamResponse:
            return web.Response(
                text="""{"type": "no_cors.json"}""",
                headers={hdrs.CONTENT_TYPE: "application/json"})

        @asyncio.coroutine
        def handle_resource(request: web.Request) -> web.StreamResponse:
            return web.Response(
                text="""{"type": "resource"}""",
                headers={hdrs.CONTENT_TYPE: "application/json"})

        @asyncio.coroutine
        def handle_servers_addresses(
                request: web.Request) -> web.StreamResponse:
            servers_addresses = \
                {name: descr.url for name, descr in self.servers.items()}
            return web.Response(
                text=json.dumps(servers_addresses))

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

        # Create applications.
        for server_descr in self.servers.values():
            server_descr.app = web.Application()

        # Server test page from origin server.
        self.servers["origin"].app.router.add_route(
            "GET", "/", handle_test_page)
        self.servers["origin"].app.router.add_route(
            "GET", "/servers_addresses", handle_servers_addresses)

        # Add routes to all servers.
        for server_name in server_names:
            app = self.servers[server_name].app
            app.router.add_route("GET", "/no_cors.json", handle_no_cors)
            app.router.add_route("GET", "/cors_resource", handle_resource,
                                 name="cors_resource")

        # Start servers.
        for server_name, server_descr in self.servers.items():
            handler = server_descr.app.make_handler()
            server = yield from create_server(handler, self.loop)
            server_descr.handler = handler
            server_descr.server = server

            hostaddr, port = server.sockets[0].getsockname()
            server_descr.url = "http://{host}:{port}".format(
                host=hostaddr, port=port)

            self._logger.info("Started server '%s' at '%s'",
                              server_name, server_descr.url)

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
            server_descr.cors = setup(
                server_descr.app, defaults=default_config)

        # Add CORS routes.
        for server_name in cors_server_names:
            server_descr = self.servers[server_name]
            server_descr.cors.add(server_descr.app.router["cors_resource"])

    @asyncio.coroutine
    def stop_servers(self):
        for server_descr in self.servers.values():
            server_descr.server.close()
            yield from server_descr.handler.finish_connections()
            yield from server_descr.server.wait_closed()
            yield from server_descr.app.finish()

        self.servers = {}


class TestInFirefox(AioTestBase):
    @asynctest
    @asyncio.coroutine
    def test_firefox(self):
        servers = IntegrationServers()
        yield from servers.start_servers()

        def selenium_thread():
            driver = webdriver.Firefox()
            try:
                driver.get(servers.origin_server_url)
                assert "aiohttp_cors" in driver.title

                wait = WebDriverWait(driver, 10)

                run_button = wait.until(EC.element_to_be_clickable(
                    (By.ID, "runTestsButton")))

                # Start tests
                run_button.send_keys(Keys.RETURN)

                # Wait while test will finish
                clear_button = wait.until(EC.element_to_be_clickable(
                    (By.ID, "clearResultsButton")))

                # Get results json
                results_area = driver.find_element_by_id("results")

                return json.loads(results_area.get_attribute("value"))

            finally:
                driver.close()

        try:
            results = yield from self.loop.run_in_executor(
                self.thread_pool_executor, selenium_thread)

            self.assertEqual(results["status"], "success")
            for test_name, test_data in results["data"].items():
                with self.subTest(group_name=test_name):
                    self.assertEqual(test_data["status"], "success",
                                     msg=(test_name, test_data))

        finally:
            yield from servers.stop_servers()


def _run_integration_server():
    """Runs integration server for interactive debugging."""

    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger("run_integration_server")

    loop = asyncio.get_event_loop()

    servers = IntegrationServers()
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
