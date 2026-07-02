"""Toolset discovery routes for the Hermes Agent HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from hermes_api.schemas import PaginatedToolsetsResponse, ToolsetSummary
from toolsets import TOOLSETS

router = APIRouter(prefix="/toolsets", tags=["toolsets"])


def _toolset_tools(toolset_config: Any) -> list[str]:
    """Return the actual tool names from a Hermes toolset definition."""

    if isinstance(toolset_config, dict):
        tools = toolset_config.get("tools", [])
    else:
        tools = toolset_config
    if not isinstance(tools, (list, tuple, set)):
        return []
    return [tool for tool in tools if isinstance(tool, str)]


@router.get(
    "",
    response_model=PaginatedToolsetsResponse,
    summary="List Hermes toolsets",
)
def get_toolsets(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    name: str | None = Query(default=None),
    order_by: str = Query(default="name", pattern="^name$"),
) -> PaginatedToolsetsResponse:
    """Return available Hermes toolsets with pagination and name filtering."""

    del order_by
    items = [
        ToolsetSummary(name=toolset_name, tools=_toolset_tools(toolset_config))
        for toolset_name, toolset_config in sorted(TOOLSETS.items())
        if name is None or name.lower() in toolset_name.lower()
    ]
    total = len(items)
    return PaginatedToolsetsResponse(
        limit=limit,
        offset=offset,
        total=total,
        data=items[offset : offset + limit],
    )
