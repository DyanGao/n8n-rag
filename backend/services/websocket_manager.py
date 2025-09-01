"""
WebSocket connection manager for real-time chat
"""

from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = {
            "connected_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0
        }
        print(f"WebSocket connection established for client: {client_id}")
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            print(f"WebSocket connection closed for client: {client_id}")
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(message)
                
                # Update connection metadata
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["last_activity"] = datetime.now()
                    self.connection_metadata[client_id]["message_count"] += 1
                    
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_json(self, data: dict, client_id: str):
        """Send JSON data to specific client"""
        message = json.dumps(data)
        await self.send_personal_message(message, client_id)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected clients"""
        message = json.dumps(data)
        await self.broadcast(message)
    
    def get_client_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_client_info(self, client_id: str) -> Dict:
        """Get connection metadata for specific client"""
        return self.connection_metadata.get(client_id, {})
    
    def is_connected(self, client_id: str) -> bool:
        """Check if client is connected"""
        return client_id in self.active_connections
    
    async def ping_all_clients(self):
        """Send ping to all clients to check connection health"""
        ping_message = json.dumps({
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        })
        await self.broadcast(ping_message)
    
    async def send_typing_indicator(self, client_id: str, is_typing: bool):
        """Send typing indicator to specific client"""
        typing_data = {
            "type": "typing",
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_json(typing_data, client_id)
    
    async def send_workflow_progress(self, client_id: str, progress: float, stage: str):
        """Send workflow generation progress update"""
        progress_data = {
            "type": "progress",
            "progress": progress,
            "stage": stage,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_json(progress_data, client_id)
    
    async def send_error(self, client_id: str, error_message: str, error_code: str = "GENERAL_ERROR"):
        """Send error message to client"""
        error_data = {
            "type": "error",
            "error_code": error_code,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_json(error_data, client_id)