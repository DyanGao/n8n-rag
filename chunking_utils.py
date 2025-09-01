"""
Intelligent Text Chunking Utilities for n8n RAG System
Provides semantic-aware text splitting with configurable overlap
"""

from typing import List, Dict, Any, Optional
import json
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter


class IntelligentChunker:
    """Handles intelligent text chunking with semantic boundary preservation"""
    
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize chunker with configurable parameters
        
        Args:
            chunk_size: Target chunk size in characters (default: 800)
            chunk_overlap: Overlap between chunks in characters (default: 100)  
            separators: Custom separators for text splitting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Default separators optimized for technical documentation
        if separators is None:
            separators = [
                "\n\n",      # Paragraph breaks
                "\n",        # Line breaks  
                ". ",        # Sentence endings
                ", ",        # Clause breaks
                " ",         # Word boundaries
                ""           # Character level fallback
            ]
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            keep_separator=True,
            is_separator_regex=False,
        )
    
    def split_text(self, text: str) -> List[str]:
        """Split text into semantic chunks"""
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        
        return self.text_splitter.split_text(text)
    
    def split_json_content(self, json_obj: Dict[str, Any], max_chunk_size: int = 1000) -> List[str]:
        """Split large JSON objects into manageable chunks"""
        json_str = json.dumps(json_obj, indent=2)
        
        # If JSON is small enough, return as single chunk
        if len(json_str) <= max_chunk_size:
            return [json_str]
        
        chunks = []
        
        # For objects with multiple keys, split by key
        if isinstance(json_obj, dict) and len(json_obj) > 1:
            for key, value in json_obj.items():
                chunk_content = json.dumps({key: value}, indent=2)
                
                # If individual key-value is still too large, split further
                if len(chunk_content) > max_chunk_size:
                    sub_chunks = self.split_text(chunk_content)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_content)
        
        # For arrays or single large values, use text splitting
        else:
            chunks = self.split_text(json_str)
        
        return chunks
    
    def create_overlapping_chunks(
        self,
        content: str,
        chunk_type: str,
        base_id: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create overlapping chunks with proper metadata"""
        
        text_chunks = self.split_text(content)
        chunk_objects = []
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_obj = {
                "chunk_id": f"{base_id}_chunk_{i}",
                "chunk_type": chunk_type,
                "content": chunk_text,
                "embedding_text": chunk_text,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "chunk_size": len(chunk_text),
                    "is_partial": len(text_chunks) > 1
                }
            }
            chunk_objects.append(chunk_obj)
        
        return chunk_objects
    
    def validate_chunk_sizes(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate chunk sizes and provide statistics"""
        if not chunks:
            return {"status": "empty", "chunks": 0}
        
        sizes = [len(chunk.get("content", "")) for chunk in chunks]
        oversized = [s for s in sizes if s > self.chunk_size * 1.2]  # 20% tolerance
        
        stats = {
            "total_chunks": len(chunks),
            "avg_size": sum(sizes) / len(sizes),
            "min_size": min(sizes),
            "max_size": max(sizes),
            "oversized_count": len(oversized),
            "size_compliance": (len(chunks) - len(oversized)) / len(chunks) * 100
        }
        
        return {
            "status": "valid" if len(oversized) == 0 else "has_oversized",
            "stats": stats,
            "oversized_chunks": oversized
        }


def create_intelligent_node_chunks(
    node: Dict[str, Any],
    chunker: IntelligentChunker,
    chunk_id_generator
) -> List[Dict[str, Any]]:
    """Create intelligently chunked node documentation"""
    chunks = []
    node_type = node.get('nodeType', 'unknown')
    
    # 1. Node Overview - usually small, keep as single chunk
    overview_content = f"""
    Node: {node.get('displayName', 'Unknown')}
    Type: {node_type}
    Category: {node.get('category', 'unknown')}
    Description: {node.get('description', 'No description')}
    Is Trigger: {node.get('isTrigger', False)}
    Is AI Tool: {node.get('isAITool', False)}
    Package: {node.get('package', 'unknown')}
    """.strip()
    
    overview_chunk = {
        "chunk_id": chunk_id_generator(node_type, "overview"),
        "chunk_type": "node_overview", 
        "node_type": node_type,
        "content": overview_content,
        "embedding_text": overview_content,
        "metadata": {
            "node_type": node_type,
            "category": node.get('category', 'unknown'),
            "is_trigger": node.get('isTrigger', False),
            "is_ai_tool": node.get('isAITool', False)
        }
    }
    chunks.append(overview_chunk)
    
    # 2. Properties - may need chunking if large
    if 'properties' in node and node['properties']:
        props_chunks = chunker.split_json_content(node['properties'])
        
        for i, props_chunk in enumerate(props_chunks):
            chunk = {
                "chunk_id": chunk_id_generator(f"{node_type}_props", f"part_{i}"),
                "chunk_type": "node_properties",
                "node_type": node_type,
                "content": props_chunk,
                "embedding_text": f"Node: {node.get('displayName')} Properties\n{props_chunk}",
                "metadata": {
                    "node_type": node_type,
                    "property_part": i,
                    "total_property_parts": len(props_chunks)
                }
            }
            chunks.append(chunk)
    
    # 3. Documentation - use overlapping chunks for large docs
    if 'documentation' in node and node['documentation']:
        doc_content = f"{node.get('displayName')} Documentation:\n{node['documentation']}"
        
        doc_chunks = chunker.create_overlapping_chunks(
            content=doc_content,
            chunk_type="node_documentation", 
            base_id=chunk_id_generator(node_type, "docs"),
            metadata={
                "node_type": node_type,
                "has_examples": 'examples' in node and len(node.get('examples', [])) > 0
            }
        )
        chunks.extend(doc_chunks)
    
    # 4. Examples - keep individual examples as separate chunks
    if 'examples' in node and node['examples']:
        for idx, example in enumerate(node['examples']):
            example_content = f"""
            Example: {example.get('title', f'Example {idx+1}')} for {node.get('displayName')}
            Configuration: {json.dumps(example.get('config', {}), indent=2)}
            """.strip()
            
            chunk = {
                "chunk_id": chunk_id_generator(f"{node_type}_ex_{idx}", "example"),
                "chunk_type": "node_examples",
                "node_type": node_type,
                "content": example_content,
                "embedding_text": example_content,
                "metadata": {
                    "node_type": node_type,
                    "example_index": idx,
                    "example_title": example.get('title', f'Example {idx+1}')
                }
            }
            chunks.append(chunk)
    
    return chunks