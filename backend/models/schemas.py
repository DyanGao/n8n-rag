"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    content: str = Field(..., description="Message content")
    role: MessageRole = Field(default=MessageRole.USER, description="Message role")
    session_id: str = Field(..., description="Chat session ID")
    use_knowledge_base: bool = Field(default=True, description="Use uploaded documents for context")
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp")

class DocumentUpload(BaseModel):
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="File size in bytes")
    file_id: str = Field(..., description="Unique file identifier")

class DocumentMetadata(BaseModel):
    file_id: str
    filename: str
    upload_date: datetime
    size: int
    content_type: str
    chunks_count: int
    processing_status: str

class WorkflowGeneration(BaseModel):
    query: str = Field(..., description="User query for workflow generation")
    workflow_json: Dict[str, Any] = Field(..., description="Generated n8n workflow JSON")
    confidence: float = Field(..., description="Generation confidence score")
    retrieved_documents: List[str] = Field(default=[], description="Documents used for generation")
    processing_time: float = Field(..., description="Time taken to generate workflow")

class WorkflowTemplate(BaseModel):
    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    workflow: Dict[str, Any]
    usage_count: int = Field(default=0)

class FeedbackData(BaseModel):
    session_id: str
    message_id: str
    workflow_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_type: str = Field(..., description="Type of feedback: helpful, unhelpful, error, etc.")
    comment: Optional[str] = Field(default="", description="Optional feedback comment")
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthStatus(BaseModel):
    status: str = Field(..., description="Overall service status")
    timestamp: datetime
    services: Dict[str, Any] = Field(..., description="Individual service statuses")

class ChatSession(BaseModel):
    session_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    title: Optional[str] = None

class StreamChunk(BaseModel):
    type: str = Field(..., description="Chunk type: text, workflow, error, complete")
    content: Union[str, Dict[str, Any]] = Field(..., description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    source_document: str

class QueryAnalysis(BaseModel):
    original_query: str
    intent: str
    entities: Dict[str, List[str]]
    complexity: str
    required_nodes: List[str]