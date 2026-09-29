"""Minimal MCP stdio client for tests: `async with Client(env) as c: await c.call(tool, args)`."""
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, "bin", "use-fusion-mcp")


class Client:
    def __init__(self, env=None):
        e = dict(os.environ)
        e.update(env or {})
        self.params = StdioServerParameters(command=SERVER, args=[], env=e)

    async def __aenter__(self):
        self._cm = stdio_client(self.params)
        r, w = await self._cm.__aenter__()
        self._s = ClientSession(r, w)
        await self._s.__aenter__()
        self.init = await self._s.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._s.__aexit__(*exc)
        await self._cm.__aexit__(*exc)

    async def tools(self):
        return (await self._s.list_tools()).tools

    async def call(self, tool, args=None):
        r = await self._s.call_tool(tool, args or {})
        sc = r.structuredContent
        if isinstance(sc, dict):
            sc = dict(sc, _images=sum(1 for c in r.content if getattr(c, "type", "") == "image"))
        if sc is None:
            sc = json.loads(r.content[0].text) if r.content and r.content[0].text.startswith("{") else {"ok": not r.isError, "text": r.content[0].text}
        return sc

    async def do(self, operation, args=None, **kw):
        return await self.call("fu_do", {"operation": operation, "args": args or {}, **kw})
