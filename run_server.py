#!/usr/bin/env python3
"""
Unified RAG Ecosystem & Web Application Server Launcher.
Starts the FastAPI Web Interface, API Gateway and connects all registered RAG engines.
"""

import os
import sys
import argparse
import uvicorn
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add web directory to sys.path
web_dir = PROJECT_ROOT / "web"
if str(web_dir) not in sys.path:
    sys.path.insert(0, str(web_dir))

def print_banner(host: str, port: int):
    print("=" * 65)
    print("  Iranian Capital Market Regulatory RAG Ecosystem & Chatbot")
    print("=" * 65)
    
    # Check registered RAG engines
    try:
        from rag_ecosystem import rag_registry
        engines = rag_registry.list_engines()
        print("\n[+] Registered RAG Engines:")
        for eng in engines:
            def_badge = " (Default)" if eng.get("is_default") else ""
            print(f"    - [{eng.get('id')}] {eng.get('name')}{def_badge}")
            print(f"      Desc: {eng.get('description')}")
    except Exception as e:
        print(f"\n[!] Notice: Could not inspect RAG registry: {e}")

    print(f"\n[+] Web Application Interface: http://{host}:{port}")
    print(f"[+] API Documentation:        http://{host}:{port}/docs")
    print(f"[+] Default Administrator:    admin / admin123")
    print("=" * 65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Run the Unified RAG Ecosystem Web Server")
    parser.add_argument("--host", type=str, default=os.getenv("HOST", "0.0.0.0"), help="Host IP to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload for development")
    args = parser.parse_args()

    print_banner(args.host, args.port)

    # Launch uvicorn pointing to web.app.main:app
    uvicorn.run(
        "web.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
