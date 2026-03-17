# ============================================================
# core/mcp.py — Full Model Context Protocol (JSON-RPC 2.0)
#
# Implements the MCP standard for:
#   1. MCPClient: Connect to external MCP tool servers (stdio)
#   2. MCPServer: Expose ASURA's tools as an MCP server
#   3. Integration with existing tool_protocol.py dispatch()
#
# Spec: https://modelcontextprotocol.io/specification
# Transport: JSON-RPC 2.0 over stdio (stdin/stdout)
# ============================================================

import os
import sys
import json
import subprocess
import threading
import time
import uuid
from typing import Any

from skills.logger import log_audit, log_app


# ── JSON-RPC 2.0 Primitives ──────────────────────────────────

def _jsonrpc_request(method: str, params: dict = None, req_id: str = None) -> dict:
    """Build a JSON-RPC 2.0 request."""
    msg = {"jsonrpc": "2.0", "method": method}
    if params:
        msg["params"] = params
    if req_id:
        msg["id"] = req_id
    return msg


def _jsonrpc_response(req_id: str, result: Any) -> dict:
    """Build a JSON-RPC 2.0 success response."""
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id: str, code: int, message: str, data: Any = None) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": error}


# ── MCP Error Codes ───────────────────────────────────────────
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# ============================================================
# MCPClient — Connect to External MCP Tool Servers
# ============================================================

class MCPClient:
    """
    Connect to an external MCP tool server via stdio.

    Usage:
        client = MCPClient("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
        client.start()
        tools = client.list_tools()
        result = client.call_tool("read_file", {"path": "/tmp/test.txt"})
        client.stop()
    """

    def __init__(self, command: str, args: list[str] = None, env: dict = None):
        self.command = command
        self.args = args or []
        self.env = {**os.environ, **(env or {})}
        self.process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._request_id = 0
        self._pending: dict[str, threading.Event] = {}
        self._results: dict[str, dict] = {}
        self._reader_thread: threading.Thread | None = None
        self._running = False
        self.server_info: dict = {}
        self.server_capabilities: dict = {}

    def start(self, timeout: float = 10.0) -> dict:
        """Start the MCP server process and perform initialization handshake."""
        self.process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
            text=False,
        )
        self._running = True

        # Start reader thread
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

        # MCP Initialize handshake
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
            },
            "clientInfo": {
                "name": "ASURA",
                "version": "4.0",
            },
        }, timeout=timeout)

        self.server_info = result.get("serverInfo", {})
        self.server_capabilities = result.get("capabilities", {})

        # Send initialized notification
        self._send_notification("notifications/initialized")

        log_audit("MCP_CLIENT", f"Connected to {self.server_info.get('name', 'unknown')} v{self.server_info.get('version', '?')}")
        return result

    def stop(self):
        """Gracefully stop the MCP server."""
        self._running = False
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None

    def list_tools(self, timeout: float = 10.0) -> list[dict]:
        """List available tools from the server."""
        result = self._send_request("tools/list", {}, timeout=timeout)
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict = None, timeout: float = 30.0) -> str:
        """Call a tool on the server. Returns the text content."""
        result = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        }, timeout=timeout)

        # Extract text from content array
        content = result.get("content", [])
        texts = []
        for item in content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts) if texts else json.dumps(result)

    def list_resources(self, timeout: float = 10.0) -> list[dict]:
        """List available resources from the server."""
        result = self._send_request("resources/list", {}, timeout=timeout)
        return result.get("resources", [])

    def read_resource(self, uri: str, timeout: float = 10.0) -> str:
        """Read a resource by URI."""
        result = self._send_request("resources/read", {"uri": uri}, timeout=timeout)
        contents = result.get("contents", [])
        texts = [c.get("text", "") for c in contents if "text" in c]
        return "\n".join(texts) if texts else json.dumps(result)

    # ── Internal Transport ────────────────────────────────────

    def _next_id(self) -> str:
        self._request_id += 1
        return str(self._request_id)

    def _send_request(self, method: str, params: dict, timeout: float = 10.0) -> dict:
        """Send a request and wait for the response."""
        req_id = self._next_id()
        event = threading.Event()
        self._pending[req_id] = event

        msg = _jsonrpc_request(method, params, req_id)
        self._write_message(msg)

        if not event.wait(timeout=timeout):
            self._pending.pop(req_id, None)
            raise TimeoutError(f"MCP request {method} timed out after {timeout}s")

        result = self._results.pop(req_id, {})
        self._pending.pop(req_id, None)

        if "error" in result:
            err = result["error"]
            raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")

        return result.get("result", {})

    def _send_notification(self, method: str, params: dict = None):
        """Send a notification (no response expected)."""
        msg = _jsonrpc_request(method, params)
        self._write_message(msg)

    def _write_message(self, msg: dict):
        """Write a JSON-RPC message to the server's stdin."""
        with self._lock:
            if self.process and self.process.stdin:
                data = json.dumps(msg).encode("utf-8")
                self.process.stdin.write(data + b"\n")
                self.process.stdin.flush()

    def _read_loop(self):
        """Background thread: read JSON-RPC responses from stdout."""
        while self._running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                msg = json.loads(line.decode("utf-8"))

                # It's a response to a pending request
                if "id" in msg and msg["id"] in self._pending:
                    req_id = msg["id"]
                    self._results[req_id] = msg
                    self._pending[req_id].set()

            except json.JSONDecodeError:
                continue
            except Exception as e:
                if self._running:
                    log_app(f"MCP reader error: {e}")
                break

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def __repr__(self):
        name = self.server_info.get("name", self.command)
        return f"<MCPClient:{name}>"


# ============================================================
# MCPServer — Expose ASURA's Tools as an MCP Server
# ============================================================

class MCPServer:
    """
    Expose ASURA's registered tools as an MCP-compliant server.
    Reads JSON-RPC from stdin, writes responses to stdout.

    Usage:
        python -m core.mcp  (starts server mode)
    """

    def __init__(self):
        from core.tool_protocol import _registry, dispatch
        self._registry = _registry
        self._dispatch = dispatch

    def serve(self):
        """Main server loop — reads stdin, processes, writes stdout."""
        log_audit("MCP_SERVER", "Starting MCP server on stdio")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                self._write(_jsonrpc_error(None, PARSE_ERROR, "Parse error"))
                continue

            if "method" not in msg:
                continue  # Response or notification, skip

            req_id = msg.get("id")
            method = msg["method"]
            params = msg.get("params", {})

            try:
                result = self._handle(method, params)
                if req_id is not None:
                    self._write(_jsonrpc_response(req_id, result))
            except Exception as e:
                if req_id is not None:
                    self._write(_jsonrpc_error(req_id, INTERNAL_ERROR, str(e)))

    def _handle(self, method: str, params: dict) -> dict:
        """Route MCP methods to handlers."""
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {
                    "name": "ASURA",
                    "version": "4.0",
                },
            }

        elif method == "tools/list":
            tools = []
            for name, tool in self._registry.items():
                tools.append({
                    "name": name,
                    "description": tool["description"],
                    "inputSchema": tool["parameters"],
                })
            return {"tools": tools}

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result_text = self._dispatch(tool_name, arguments)
            return {
                "content": [{"type": "text", "text": result_text}],
                "isError": result_text.startswith("TOOL_ERROR") or result_text.startswith("Unknown tool"),
            }

        elif method == "resources/list":
            return {"resources": []}

        elif method == "resources/read":
            return {"contents": []}

        elif method == "ping":
            return {}

        else:
            raise RuntimeError(f"Unknown method: {method}")

    def _write(self, msg: dict):
        """Write a JSON-RPC message to stdout."""
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()


# ============================================================
# External Server Manager — Register External MCP Servers
# ============================================================

_external_clients: dict[str, MCPClient] = {}


def connect_server(name: str, command: str, args: list[str] = None, env: dict = None) -> MCPClient:
    """
    Connect to an external MCP server and register its tools.

    Args:
        name: Friendly name for this server
        command: Executable (e.g., "npx", "python")
        args: Arguments to the command
        env: Extra environment variables

    Returns the connected MCPClient.
    """
    from core.tool_protocol import register_tool

    client = MCPClient(command, args, env)
    client.start()

    # Discover and register all remote tools
    remote_tools = client.list_tools()
    for tool in remote_tools:
        tool_name = f"{name}.{tool['name']}"
        # Create closure for this specific tool
        def make_handler(c, tn):
            def handler(args):
                a = args if isinstance(args, dict) else {"input": str(args)}
                return c.call_tool(tn, a)
            return handler

        register_tool(
            name=tool_name,
            function=make_handler(client, tool["name"]),
            description=f"[{name}] {tool.get('description', '')}",
            parameters=tool.get("inputSchema", {}),
            category=f"mcp:{name}",
        )

    _external_clients[name] = client
    log_audit("MCP_CLIENT", f"Registered {len(remote_tools)} tools from '{name}' server")
    return client


def disconnect_server(name: str):
    """Disconnect from an external MCP server."""
    if name in _external_clients:
        _external_clients[name].stop()
        del _external_clients[name]
        log_audit("MCP_CLIENT", f"Disconnected from '{name}' server")


def list_servers() -> dict:
    """List connected external MCP servers."""
    return {
        name: {
            "info": client.server_info,
            "capabilities": client.server_capabilities,
        }
        for name, client in _external_clients.items()
    }


# ============================================================
# Entry Point — Run as MCP Server
# ============================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    # Ensure tools are registered
    import core.tool_protocol  # noqa: triggers _register_builtins()

    server = MCPServer()
    server.serve()
