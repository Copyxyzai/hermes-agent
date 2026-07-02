"""MCP connector routes for the Hermes Agent HTTP API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hermes_api.auth import require_bearer_token
from hermes_api.mcp_connector import create_mcp_connector_config
from hermes_api.schemas import ApiResponse, MCPConnectorResponse

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get(
    "/connector",
    response_model=ApiResponse[MCPConnectorResponse],
    dependencies=[Depends(require_bearer_token)],
    summary="Return Hermes MCP connector configuration",
)
def get_mcp_connector(
    server_name: str = Query(default="hermes", min_length=1),
    command: str = Query(default="hermes", min_length=1),
    verbose: bool = Query(default=False),
) -> ApiResponse[MCPConnectorResponse]:
    """Return an MCP client config fragment for launching Hermes MCP stdio."""

    connector = create_mcp_connector_config(
        server_name=server_name,
        command=command,
        verbose=verbose,
    )
    return ApiResponse(
        data=MCPConnectorResponse(
            server_name=connector.server_name,
            transport=connector.transport,
            command=connector.command,
            args=list(connector.args),
            client_config=connector.as_client_config(),
            usage=f"{connector.command} {' '.join(connector.args)}",
        ),
        message="MCP connector configuration generated",
    )
