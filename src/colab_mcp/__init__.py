# Copyright 2026 Google Inc.
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

import argparse
import asyncio
import datetime
import logging
import tempfile
import sys

from fastmcp import FastMCP
from fastmcp.utilities import logging as fastmcp_logger

from colab_mcp.session import ColabSessionProxy


mcp = FastMCP(name="ColabMCP")


def init_logger(logdir):
    log_filename = datetime.datetime.now().strftime(
        f"{logdir}/colab-mcp.%Y-%m-%d_%H-%M-%S.log"
    )
    logging.basicConfig(
        format="%(asctime)s %(levelname)s:%(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        filename=log_filename,
        level=logging.INFO,  # Set the minimum logging level to capture
    )
    fastmcp_logger.get_logger("colab-mcp").info("logging to %s" % log_filename)


def parse_args(v):
    parser = argparse.ArgumentParser(
        description="ColabMCP is an MCP server that lets you interact with Colab."
    )
    parser.add_argument(
        "-l",
        "--log",
        help="if set, use this directory as a location for logfiles (if unset, will log to %s/colab-mcp-logs/)"
        % tempfile.gettempdir(),
        action="store",
        default=tempfile.mkdtemp(prefix="colab-mcp-logs-"),
    )
    parser.add_argument(
        "-p",
        "--enable-proxy",
        help="if set, enable the runtime proxy (enabled by default).",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "-n",
        "--notebook",
        help="URL or path of the Colab notebook to open (default: empty scratch notebook).",
        action="store",
        default=None,
    )
    parser.add_argument(
        "-H",
        "--host",
        help="Host address for the WebSocket server to bind to (default: localhost).",
        action="store",
        default="localhost",
    )
    parser.add_argument(
        "-P",
        "--port",
        help="Port for the WebSocket server to bind to (default: 0, random port).",
        action="store",
        default=0,
        type=int,
    )
    parser.add_argument(
        "--no-browser",
        help="Do not auto-open a browser session. Instead, print the connection URL to the console.",
        action="store_true",
        default=False,
    )
    return parser.parse_args(v)


async def main_async():
    args = parse_args(sys.argv[1:])
    init_logger(args.log)

    if args.enable_proxy:
        logging.info("enabling session proxy tools")
        if args.host != "localhost":
            logging.warning(
                f"WebSocket server binding to {args.host}, which exposes it to the network. "
                "Ensure your firewall is configured appropriately."
            )
        session_mcp = ColabSessionProxy(
            notebook_url=args.notebook,
            host=args.host,
            port=args.port,
            no_browser=args.no_browser,
        )
        await session_mcp.start_proxy_server()
        mcp.mount(session_mcp.proxy_server)
        for middleware in session_mcp.middleware:
            mcp.add_middleware(middleware)

    try:
        await mcp.run_async()

    finally:
        if args.enable_proxy:
            await session_mcp.cleanup()


def main() -> None:
    asyncio.run(main_async())
