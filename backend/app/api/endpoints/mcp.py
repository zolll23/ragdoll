"""
MCP Server HTTP endpoint for Goose
Provides MCP protocol over HTTP instead of stdio
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio
import sys
import os
from typing import Dict, Any

# Add mcp_server to path
# mcp_server is mounted at /app/mcp_server in backend container (via volume mount)
sys.path.insert(0, '/app/mcp_server')

from mcp_server.tools import CodeRAGTools
from mcp_server.resources import CodeRAGResources
from app.core.database import get_db

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

# Initialize tools and resources (singleton instances)
tools = CodeRAGTools()
resources = CodeRAGResources()


@router.post("/request")
async def mcp_request(request: Dict[str, Any]):
    """
    Handle MCP JSON-RPC requests over HTTP
    This allows Goose to connect to MCP server via HTTP instead of stdio
    """
    try:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Handle MCP protocol methods
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "coderag-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "tools/list":
            tools_list = await tools.get_tools()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools_list
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            # Tools create their own database session internally
            result_text = await tools.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            }
        elif method == "resources/list":
            resources_list = await resources.get_resources()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resources": resources_list
                }
            }
        elif method == "resources/read":
            uri = params.get("uri", "")
            resource_content = await resources.read_resource(uri)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": resource_content
                        }
                    ]
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
