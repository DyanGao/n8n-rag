#!/usr/bin/env python3
"""
Start script for n8n RAG Studio frontend
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_node():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js found: {version}")
            return True
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not installed")
        print("Please install Node.js from https://nodejs.org/")
        return False

def check_npm():
    """Check if npm is installed"""
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ npm found: {version}")
            return True
        else:
            print("❌ npm not found")
            return False
    except FileNotFoundError:
        print("❌ npm not installed")
        return False

def install_dependencies():
    """Install npm dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run(["npm", "install"], cwd="frontend", check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def main():
    parser = argparse.ArgumentParser(description="Start n8n RAG Studio frontend")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind to")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency checks")
    parser.add_argument("--install", action="store_true", help="Install dependencies before starting")
    
    args = parser.parse_args()
    
    print("🌐 Starting n8n RAG Studio Frontend")
    print("=" * 40)
    
    if not args.skip_checks:
        print("Running pre-flight checks...")
        
        if not check_node() or not check_npm():
            sys.exit(1)
        
        # Check if node_modules exists
        node_modules = Path("frontend/node_modules")
        if not node_modules.exists() or args.install:
            if not install_dependencies():
                sys.exit(1)
        else:
            print("✅ Dependencies already installed")
        
        print("=" * 40)
    
    # Change to frontend directory
    os.chdir("frontend")
    
    # Set environment variables
    env = os.environ.copy()
    env["PORT"] = str(args.port)
    env["BROWSER"] = "none"  # Don't auto-open browser
    
    print(f"Starting React development server at http://localhost:{args.port}")
    print("Press Ctrl+C to stop")
    print("=" * 40)
    
    try:
        subprocess.run(["npm", "start"], env=env)
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped")

if __name__ == "__main__":
    main()