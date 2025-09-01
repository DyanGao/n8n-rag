"""
FastAPI backend for n8n RAG Web UI
Cherry Studio inspired interface for workflow generation
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import asyncio

# Import existing RAG components
import sys
sys.path.append('..')
from models.schemas import ChatMessage, DocumentUpload, WorkflowGeneration
from services.rag_service import RAGService
from services.websocket_manager import ConnectionManager

app = FastAPI(
    title="n8n RAG Studio API",
    description="AI-powered n8n workflow generation with document knowledge base",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
rag_service = RAGService()
manager = ConnectionManager()

# Ensure upload directories exist
UPLOAD_DIR = Path("../uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "n8n RAG Studio API", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if core services are available
        rag_status = await rag_service.health_check()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "rag": rag_status,
                "ollama": await check_ollama_status(),
                "vector_db": await check_vector_db_status()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

async def check_ollama_status() -> Dict[str, Any]:
    """Check Ollama service status"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {"status": "available", "model_count": len(models)}
            else:
                return {"status": "error", "message": "Ollama not responding"}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)}

async def check_vector_db_status() -> Dict[str, Any]:
    """Check ChromaDB status"""
    try:
        return await rag_service.check_vector_db()
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process document for knowledge base"""
    try:
        # Validate file type
        allowed_types = {
            "application/json", "text/plain", "text/markdown", 
            "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file.content_type} not supported. Allowed: {', '.join(allowed_types)}"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        saved_filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / saved_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process file for knowledge base
        processing_result = await rag_service.process_document(
            file_path=str(file_path),
            original_filename=file.filename,
            file_type=file.content_type
        )
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "size": file_path.stat().st_size,
            "type": file.content_type,
            "processing_status": processing_result["status"],
            "chunks_created": processing_result.get("chunks_created", 0),
            "upload_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/documents")
async def list_documents(
    page: int = 1, 
    per_page: int = 50,
    search: str = None
):
    """List uploaded documents with pagination"""
    try:
        documents = await rag_service.list_documents_paginated(
            page=page, 
            per_page=min(per_page, 100),  # Max 100 per page
            search=search
        )
        print(f"🔍 API returning {len(documents.get('documents', []))} documents")
        print(f"📄 Sample document: {documents.get('documents', [{}])[0] if documents.get('documents') else 'None'}")
        print(f"📊 Pagination info: {documents.get('pagination', {})}")
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/api/documents/{file_id}")
async def delete_document(file_id: str):
    """Delete document from knowledge base"""
    try:
        result = await rag_service.delete_document(file_id)
        return {"success": result["success"], "message": result.get("message", "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.delete("/api/documents")
async def delete_all_documents():
    """Delete all documents from knowledge base"""
    try:
        result = await rag_service.delete_all_documents()
        return {"success": result["success"], "message": result.get("message", ""), "deleted_count": result.get("deleted_count", 0)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete all documents: {str(e)}")

@app.post("/api/chat")
async def chat_completion(message: ChatMessage):
    """Generate workflow based on chat message"""
    try:
        # Process query through RAG pipeline
        response = await rag_service.generate_workflow(
            query=message.content,
            session_id=message.session_id,
            use_knowledge_base=message.use_knowledge_base
        )
        
        return {
            "response": response["workflow"],
            "metadata": {
                "retrieved_documents": response.get("retrieved_docs", []),
                "confidence": response.get("confidence", 0.0),
                "processing_time": response.get("processing_time", 0.0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")

@app.get("/api/templates")
async def get_workflow_templates():
    """Get available workflow templates"""
    try:
        templates = await rag_service.get_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

@app.post("/api/feedback")
async def submit_feedback(feedback: Dict[str, Any]):
    """Submit feedback for workflow generation"""
    try:
        result = await rag_service.submit_feedback(feedback)
        return {"success": True, "message": "Feedback recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Skip ping messages and only process chat messages
            if message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": message_data.get("timestamp")}))
                continue
                
            # Only process chat messages with actual content
            if message_data.get("type") == "chat" and message_data.get("content", "").strip():
                # Process message through RAG pipeline with streaming
                async for chunk in rag_service.generate_workflow_stream(
                    query=message_data.get("content", ""),
                    session_id=message_data.get("session_id", client_id)
                ):
                    await manager.send_personal_message(json.dumps(chunk), client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await manager.send_personal_message(
            json.dumps({"type": "error", "content": str(e)}), 
            client_id
        )
        manager.disconnect(client_id)

@app.get("/api/sessions/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat history for session"""
    try:
        history = await rag_service.get_chat_history(session_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )