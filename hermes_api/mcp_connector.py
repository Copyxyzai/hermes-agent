"""MCP connector helpers for the Hermes FastAPI API."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MCPConnectorConfig:
    """Client configuration for connecting to Hermes' stdio MCP server."""

    server_name: str = "hermes"
    command: str = "hermes"
    args: tuple[str, ...] = ("mcp", "serve")
    transport: str = "stdio"
    env: dict[str, str] = field(default_factory=dict)

    def as_client_config(self) -> dict[str, dict[str, object]]:
        """Return a standard MCP client `mcpServers` config fragment."""

        server_config: dict[str, object] = {
            "command": self.command,
            "args": list(self.args),
        }
        if self.env:
            server_config["env"] = dict(self.env)
        return {"mcpServers": {self.server_name: server_config}}


def create_mcp_connector_config(
    *,
    server_name: str = "hermes",
    command: str = "hermes",
    verbose: bool = False,
) -> MCPConnectorConfig:
    """Create a connector config for MCP clients that should launch Hermes.

    The API exposes the connector metadata only; it does not start an MCP server
    inside the HTTP process. MCP clients launch Hermes through the returned
    stdio command, preserving the existing `hermes mcp serve` entrypoint.
    """

    args = ["mcp", "serve"]
    if verbose:
        args.append("--verbose")
    return MCPConnectorConfig(
        server_name=server_name,
        command=command,
        args=tuple(args),
    )
