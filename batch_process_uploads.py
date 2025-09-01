#!/usr/bin/env python3
"""
Batch process all files in uploads folder and add them to the RAG system
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

# Import the RAG service
from backend.services.rag_service import RAGService

async def main():
    print("🔄 Starting batch processing of uploaded files...")
    
    # Initialize RAG service
    rag_service = RAGService()
    
    # Get uploads directory
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        print("❌ Uploads directory not found!")
        return
    
    # Get all JSON files
    json_files = list(uploads_dir.glob("*.json"))
    print(f"📁 Found {len(json_files)} JSON files to process")
    
    if len(json_files) == 0:
        print("ℹ️ No JSON files found in uploads directory")
        return
    
    success_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            print(f"📄 Processing: {json_file.name}")
            
            # Process the file
            result = await rag_service.process_document(
                file_path=str(json_file),
                original_filename=json_file.name,
                file_type="application/json"
            )
            
            if result.get("status") == "success":
                chunks = result.get("chunks_created", 0)
                print(f"   ✅ Success - {chunks} chunks created")
                success_count += 1
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"   ❌ Error - {error_msg}")
                error_count += 1
                
        except Exception as e:
            print(f"   💥 Exception - {str(e)}")
            error_count += 1
    
    print(f"\n🎯 Batch processing complete!")
    print(f"   ✅ Successfully processed: {success_count} files")
    print(f"   ❌ Failed to process: {error_count} files")
    print(f"   📊 Total files: {len(json_files)}")

if __name__ == "__main__":
    asyncio.run(main())