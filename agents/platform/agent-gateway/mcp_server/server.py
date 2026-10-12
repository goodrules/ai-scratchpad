"""FastMCP Banking Server for Google Cloud Agent Gateway demo.

Exposes core banking tools:
- get_account(customer_id)
- lookup_customer_by_phone(phone)
- transfer_to_phone(customer_id, target_phone, amount)
- pay_bill(customer_id, biller_name, account_number, amount)
- get_transaction_history(customer_id)

Endpoints:
- /: Service health & metadata endpoint
- /tools: JSON array of tool specifications (compatible with Google Cloud Codelab)
- /toolspec.json: Agent Registry tool-spec format {"tools": [...]}
- /mcp: FastMCP Streamable HTTP transport
- stdio support: mcp.run(transport="stdio")
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

from pydantic import Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP as MCPServer

from mcp_server.data import (
    execute_bill_payment,
    execute_transfer,
    find_customer_by_phone,
    get_customer,
    reset_database,
)

# Instantiate MCP server (supports both MCP SDK v2 MCPServer and v1 FastMCP)
_MCP_INSTRUCTIONS = (
    "Production-grade Enterprise Banking Model Context Protocol (MCP) server. "
    "Provides customer account queries, verified phone lookups, peer-to-peer transfers, "
    "utility bill payments, and audit ledgers governed by Google Cloud Agent Gateway."
)
try:
    mcp = MCPServer(
        name="banking-mcp-server",
        instructions=_MCP_INSTRUCTIONS,
        stateless_http=True,
    )
except TypeError:
    mcp = MCPServer(
        name="banking-mcp-server",
        instructions=_MCP_INSTRUCTIONS,
    )

# Allow flexible host matching for Cloud Run, Private Service Connect, and test clients
if hasattr(mcp, "settings") and hasattr(mcp.settings, "transport_security"):
    mcp.settings.transport_security.enable_dns_rebinding_protection = False


# ==============================================================================
# MCP Tools Registration
# ==============================================================================


@mcp.tool(
    name="get_account",
    description="Fetches customer account details, current available balance (USD), daily limits, and status.",
)
def get_account(
    customer_id: str = Field(
        ...,
        description="Unique identifier of the customer (e.g., 'CUST001', 'CUST005').",
    ),
) -> Dict[str, Any]:
    """Retrieve customer account details and balance."""
    cust = get_customer(customer_id)
    if not cust:
        return {
            "status": "ERROR",
            "error_code": "CUSTOMER_NOT_FOUND",
            "message": f"Customer ID '{customer_id}' was not found in the banking system.",
        }

    return {
        "status": "SUCCESS",
        "customer_id": cust["customer_id"],
        "name": cust["name"],
        "tier": cust["tier"],
        "balance": cust["balance"],
        "currency": cust.get("currency", "USD"),
        "phone": cust["phone"],
        "email": cust["email"],
        "daily_limit": cust["daily_limit"],
        "risk_score": cust["risk_score"],
        "account_status": cust["account_status"],
    }


@mcp.tool(
    name="lookup_customer_by_phone",
    description="Resolves a customer's banking identity, account ID, and verification status by phone number.",
)
def lookup_customer_by_phone(
    phone: str = Field(
        ...,
        description="Customer phone number in 555-xxxx format (e.g., '555-0002').",
    ),
) -> Dict[str, Any]:
    """Look up a customer account by phone number."""
    cust = find_customer_by_phone(phone)
    if not cust:
        return {
            "status": "ERROR",
            "error_code": "PHONE_NOT_FOUND",
            "message": f"No registered customer account found matching phone number '{phone}'.",
        }

    return {
        "status": "SUCCESS",
        "customer_id": cust["customer_id"],
        "name": cust["name"],
        "tier": cust["tier"],
        "phone": cust["phone"],
        "account_status": cust["account_status"],
    }


@mcp.tool(
    name="transfer_to_phone",
    description="Moves funds from an authenticated customer account to a recipient identified by phone number.",
)
def transfer_to_phone(
    customer_id: str = Field(
        ...,
        description="Source customer account ID initiating the transfer (e.g., 'CUST005').",
    ),
    target_phone: str = Field(
        ...,
        description="Recipient phone number (e.g., '555-0002').",
    ),
    amount: float = Field(
        ...,
        description="Amount in USD to transfer (must be strictly positive).",
    ),
) -> Dict[str, Any]:
    """Transfer funds to a recipient identified by phone number."""
    return execute_transfer(
        sender_id=customer_id,
        target_phone=target_phone,
        amount=amount,
    )


@mcp.tool(
    name="pay_bill",
    description="Settles utility, telecom, or merchant invoices for an authenticated customer account.",
)
def pay_bill(
    customer_id: str = Field(
        ...,
        description="Customer account ID paying the bill (e.g., 'CUST001', 'CUST005').",
    ),
    biller_name: str = Field(
        ...,
        description="Name of the biller or service provider (e.g., 'Cloud Electric', 'Metro Water').",
    ),
    account_number: str = Field(
        ...,
        description="Customer account or reference invoice number with the biller.",
    ),
    amount: float = Field(
        ...,
        description="Amount in USD to pay (must be strictly positive).",
    ),
) -> Dict[str, Any]:
    """Pay an invoice or utility bill."""
    return execute_bill_payment(
        customer_id=customer_id,
        biller_name=biller_name,
        account_number=account_number,
        amount=amount,
    )


@mcp.tool(
    name="get_transaction_history",
    description="Retrieves comprehensive audit ledger and transaction history for a customer account.",
)
def get_transaction_history(
    customer_id: str = Field(
        ...,
        description="Unique customer identifier (e.g., 'CUST001', 'CUST005').",
    ),
) -> Dict[str, Any]:
    """Retrieve transaction history for audit logging."""
    cust = get_customer(customer_id)
    if not cust:
        return {
            "status": "ERROR",
            "error_code": "CUSTOMER_NOT_FOUND",
            "message": f"Customer ID '{customer_id}' was not found in the banking system.",
        }

    return {
        "status": "SUCCESS",
        "customer_id": cust["customer_id"],
        "customer_name": cust["name"],
        "tier": cust["tier"],
        "current_balance": cust["balance"],
        "currency": cust.get("currency", "USD"),
        "total_transactions": len(cust.get("transaction_history", [])),
        "transactions": cust.get("transaction_history", []),
    }


# ==============================================================================
# Custom Starlette HTTP Routes (Codelab & Agent Registry Compatibility)
# ==============================================================================


@mcp.custom_route("/", methods=["GET"])
async def root_endpoint(request: Request) -> JSONResponse:
    """Service health and discovery metadata."""
    tools = await mcp.list_tools()
    return JSONResponse(
        {
            "service": "banking-mcp-server",
            "status": "healthy",
            "version": "1.0.0",
            "protocol": "Model Context Protocol (MCP) + Streamable HTTP",
            "endpoints": {
                "root": "/",
                "tools": "/tools",
                "toolspec": "/toolspec.json",
                "mcp": "/mcp",
            },
            "tools_count": len(tools),
            "available_tools": [t.name for t in tools],
        }
    )


@mcp.custom_route("/tools", methods=["GET"])
async def list_tools_endpoint(request: Request) -> JSONResponse:
    """List tool specifications matching Google Codelab /tools response format."""
    tools = await mcp.list_tools()
    tool_dicts = [t.model_dump(by_alias=True, exclude_none=True) for t in tools]
    return JSONResponse(tool_dicts)


@mcp.custom_route("/toolspec.json", methods=["GET"])
async def toolspec_endpoint(request: Request) -> JSONResponse:
    """Export tool specification in Google Cloud Agent Registry format: {'tools': [...]}."""
    tools = await mcp.list_tools()
    tool_dicts = [t.model_dump(by_alias=True, exclude_none=True) for t in tools]
    return JSONResponse({"tools": tool_dicts})


def create_app() -> Starlette:
    """Return a configured Starlette application instance with refreshed session manager."""
    mcp._session_manager = None
    try:
        from mcp.server.transport_security import TransportSecuritySettings

        security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
        return mcp.streamable_http_app(
            stateless_http=True,
            transport_security=security,
        )
    except (TypeError, ImportError):
        return mcp.streamable_http_app()


# Module-level ASGI Starlette app instance
app: Starlette = create_app()


# ==============================================================================
# Execution Entry Point
# ==============================================================================


def main() -> None:
    """CLI entrypoint for running the banking MCP server."""
    parser = argparse.ArgumentParser(description="Banking FastMCP Server")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run using MCP stdio transport instead of HTTP",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host interface for HTTP server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8080")),
        help="Port for HTTP server (default: $PORT or 8080)",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset in-memory database to pristine baseline state",
    )

    args = parser.parse_args()

    if args.reset_db:
        reset_database()
        print("Database reset to pristine initial state.")

    if args.stdio:
        print("Starting Banking FastMCP Server on stdio transport...", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        import uvicorn

        print(
            f"Starting Banking FastMCP Server on http://{args.host}:{args.port} (MCP route: /mcp)..."
        )
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
