"""
Script to run the MCP Server.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    from src.mcp_server.server import main
    import asyncio

    asyncio.run(main())
