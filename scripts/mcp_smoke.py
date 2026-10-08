import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "app.mcp.server"], env=dict(os.environ)
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            result = await client.list_tools()
            names = [t.name for t in result.tools]
            assert set(names) == {"search_company_policy", "get_order", "get_customer"}
            order = await client.call_tool("get_order", {"order_id": "NS-1042"})
            assert not order.isError
            assert "NS-1042" in str(order.content)
            policy = await client.call_tool(
                "search_company_policy",
                {"query": "Gold customer return extension", "top_k": 3},
            )
            assert not policy.isError and "vip" in str(policy.content).lower()
            print(
                json.dumps(
                    {
                        "transport": "stdio",
                        "initialized": True,
                        "tools": names,
                        "order_call": "passed",
                        "retrieval_call": "passed",
                        "schemas": [t.model_dump() for t in result.tools],
                    },
                    indent=2,
                )
            )


asyncio.run(main())
