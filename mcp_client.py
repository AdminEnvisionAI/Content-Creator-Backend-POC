# from mcp import ClientSession
# from mcp.client.sse import sse_client
# import json

# async def call_mcp(tool: str, args: dict):
#     async with sse_client(url="http://localhost:8000/sse") as streams:
#         async with ClientSession(*streams) as session:
#             try:

#                 await session.initialize()
#                 tools=await session.list_tools()
#                 print("tooooooooooooooooooooooooools",tools)
#                 print("abc------------------------>",tool,"args---------->",args)
#                 result = await session.call_tool("llm_to_mongo", arguments={"query":"top engagement_rate_per_post youtube influncer"})
#                 print("result----------------------->",result)
#                 content = result.content[0].text

#                 return content
#             except Exception as e:
#                 print("error------------------------->",e)



# mcp_client.py (CORRECTED)

from mcp import ClientSession
from mcp.client.sse import sse_client
import json

async def call_mcp(tool: str, args: dict):
    async with sse_client(url="http://localhost:8000/sse") as streams:
        async with ClientSession(*streams) as session:
            try:
                await session.initialize()
                tools = await session.list_tools()
                print("Available tools:", tools)
                
                print(f"Calling tool '{tool}' with arguments: {args}")
                
                # Use the function parameters instead of hardcoded values
                result = await session.call_tool(tool, arguments=args)
                
                print("Result from MCP:", result)

                # Proper error checking
                if result.isError:
                    error_message = result.content[0].text if result.content else "Unknown error"
                    print(f"Error from server: {error_message}")
                    return f"Error: {error_message}"

                # Success case
                content = result.content[0].text if result.content else None
                # If the tool returns structured data, you might want this instead:
                # content = result.structuredContent 
                
                return content
                
            except Exception as e:
                print(f"An unexpected client-side error occurred: {e}")
                return f"Client Error: {e}"

# Example of how to use the corrected function:
# import asyncio
#
# async def main():
#     response = await call_mcp(
#         tool="llm_to_mongo", 
#         args={"query": "top engagement_rate_per_post youtube influncer"}
#     )
#     print("\nFinal Content:", response)
#
# if __name__ == "__main__":
#     asyncio.run(main())