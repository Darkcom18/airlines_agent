"""
Script để chạy C1 Travel Agent System locally (không cần Docker).
Yêu cầu: PostgreSQL và Redis đã chạy trên localhost.
"""
import subprocess
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Kiểm tra dependencies."""
    print("Checking dependencies...")

    # Check Python packages
    try:
        import fastapi
        import uvicorn
        import redis
        import asyncpg
        import structlog
        print("  Python packages: OK")
    except ImportError as e:
        print(f"  Missing package: {e}")
        print("  Run: pip install -r requirements.txt")
        return False

    return True


def run_api():
    """Chạy FastAPI server."""
    print("\nStarting FastAPI server on http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print("  Health: http://localhost:8000/health")
    print("\nPress Ctrl+C to stop\n")

    os.chdir(project_root)
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "src.api.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])


def run_mcp():
    """Chạy MCP server."""
    print("\nStarting MCP server on http://localhost:8001")
    print("  Health: http://localhost:8001/health")
    print("\nPress Ctrl+C to stop\n")

    os.chdir(project_root)
    subprocess.run([
        sys.executable, "-m", "src.mcp_server.server"
    ])


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python run_local.py [api|mcp|all]")
        print()
        print("Commands:")
        print("  api  - Run FastAPI server only")
        print("  mcp  - Run MCP server only")
        print("  all  - Run both (requires 2 terminals)")
        return

    if not check_dependencies():
        return

    command = sys.argv[1].lower()

    if command == "api":
        run_api()
    elif command == "mcp":
        run_mcp()
    elif command == "all":
        print("To run both servers, open 2 terminals:")
        print("  Terminal 1: python scripts/run_local.py mcp")
        print("  Terminal 2: python scripts/run_local.py api")
        print()
        print("Or use Docker Compose:")
        print("  docker-compose up -d")
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
