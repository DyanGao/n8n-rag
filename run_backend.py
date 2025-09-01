#!/usr/bin/env python3
"""
Start script for n8n RAG Studio backend
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Set default log level for production
if 'LOG_LEVEL' not in os.environ:
    os.environ['LOG_LEVEL'] = 'WARNING'  

def check_requirements():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import chromadb
        import sentence_transformers
        print("✅ Required dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install requirements with: pip install -r backend/requirements.txt")
        return False

def check_data():
    """Check if RAG data exists"""
    data_dir = Path("n8n_rag_data")
    if data_dir.exists() and list(data_dir.glob("**/*.json")):
        print("✅ RAG data found")
        return True
    else:
        print("⚠️ No RAG data found. You may want to run data extraction first:")
        print("   python 1_1_n8n_data_extractor.py")
        print("   python 2_vector_indexer.py")
        return False

def check_ollama():
    """Check if Ollama is running"""
    try:
        import httpx
        import asyncio
        
        async def ping_ollama():
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
                return response.status_code == 200
        
        if asyncio.run(ping_ollama()):
            print("✅ Ollama is running")
            return True
        else:
            print("⚠️ Ollama is not responding")
            return False
    except Exception as e:
        print("⚠️ Could not connect to Ollama - will run in mock mode")
        return False

def main():
    parser = argparse.ArgumentParser(description="Start n8n RAG Studio backend")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency checks")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--quiet", action="store_true", help="Minimal logging (ERROR level only)")
    
    args = parser.parse_args()
    
    # Set logging level based on arguments
    if args.verbose:
        os.environ['LOG_LEVEL'] = 'DEBUG'
    elif args.quiet:
        os.environ['LOG_LEVEL'] = 'ERROR'
    
    print("🚀 Starting n8n RAG Studio Backend")
    print("=" * 40)
    
    if not args.skip_checks:
        print("Running pre-flight checks...")
        
        if not check_requirements():
            sys.exit(1)
        
        check_data()
        check_ollama()
        
        print("=" * 40)
    
    # Change to backend directory
    os.chdir("backend")
    
    # Start the server
    cmd = [
        "uvicorn",
        "app:app",
        f"--host={args.host}",
        f"--port={args.port}",
        "--log-level=info"
    ]
    
    if args.reload:
        cmd.append("--reload")
    
    print(f"Starting server at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    main()