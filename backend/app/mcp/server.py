"""Read-only enterprise tools, served over the real MCP stdio transport."""

from mcp.server.fastmcp import FastMCP
from app.db.repository import init_db
from app.db.seed import seed
from app.tools.business import get_order as lookup_order, get_customer as lookup_customer
from app.rag.retriever import search_knowledge

mcp = FastMCP("OpsPilot enterprise tools")


@mcp.tool()
def search_company_policy(query: str, top_k: int = 6) -> list[dict]:
    """Search synthetic company policies and return citation-ready evidence."""
    if not 1 <= top_k <= 12 or not query.strip() or len(query) > 2000:
        raise ValueError("Invalid query or top_k")
    return search_knowledge(query, top_k)


@mcp.tool()
def get_order(order_id: str) -> dict:
    """Read a synthetic Northstar order by its exact identifier."""
    return lookup_order(order_id) or {"error": "not_found"}


@mcp.tool()
def get_customer(customer_id: str) -> dict:
    """Read a synthetic customer with email removed."""
    return lookup_customer(customer_id) or {"error": "not_found"}


if __name__ == "__main__":
    init_db()
    seed()
    mcp.run(transport="stdio")
