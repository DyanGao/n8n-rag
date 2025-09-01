"""
Phase 2: Vector Indexing System for n8n RAG
Creates and manages vector embeddings for efficient retrieval
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np
from datetime import datetime
import hashlib
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

class N8nVectorIndexer:
    """Create and manage vector index for n8n documentation"""
    
    def __init__(
        self,
        data_dir: str = "./n8n_rag_data",
        db_dir: str = "./n8n_vector_db",
        model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 800,
        chunk_overlap: int = 100
    ):
        self.data_dir = Path(data_dir)
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)
        
        # Store chunking configuration
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize embedding model
        print(f"🤖 Loading embedding model: {model_name}")
        print(f"📏 Chunking config: {chunk_size} chars with {chunk_overlap} overlap")
        self.embedding_model = SentenceTransformer(model_name)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.db_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create collections for different document types
        self.collections = {}
        self.init_collections()
        
    def init_collections(self):
        """Initialize ChromaDB collections"""
        print("📚 Initializing vector collections...")
        
        collection_configs = [
            {
                "name": "n8n_nodes",
                "description": "Node documentation and properties"
            },
            {
                "name": "n8n_templates",
                "description": "Workflow templates and patterns"
            },
            {
                "name": "n8n_tasks",
                "description": "Task-specific configurations"
            },
            {
                "name": "n8n_connections",
                "description": "Node connection patterns"
            }
        ]
        
        for config in collection_configs:
            try:
                # Try to get existing collection
                collection = self.chroma_client.get_collection(config["name"])
                print(f"  ✅ Found existing collection: {config['name']}")
            except:
                # Create new collection
                collection = self.chroma_client.create_collection(
                    name=config["name"],
                    metadata={"description": config["description"]}
                )
                print(f"  ✨ Created new collection: {config['name']}")
            
            self.collections[config["name"]] = collection
    
    def load_chunks(self) -> List[Dict[str, Any]]:
        """Load prepared chunks from data directory"""
        chunks_file = self.data_dir / "chunks" / "all_chunks.json"
        
        if not chunks_file.exists():
            raise FileNotFoundError(f"Chunks file not found: {chunks_file}")
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        print(f"📄 Loaded {len(chunks)} chunks from {chunks_file}")
        return chunks
    
    def create_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Create embeddings for texts in batches"""
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Creating embeddings"):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.embedding_model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_embeddings)
        
        return np.array(embeddings)
    
    def index_chunks(self, chunks: List[Dict[str, Any]]):
        """Index chunks into appropriate collections"""
        print("\n🔄 Indexing chunks into vector database...")
        
        # Group chunks by type
        chunks_by_type = {
            "node_overview": [],
            "node_properties": [],
            "node_documentation": [],
            "node_examples": [],
            "ai_tool_usage": [],
            "workflow_template": [],
            "workflow_pattern": [],  
            "task_configuration": [],
            "connection_pattern": []
        }
        
        for chunk in chunks:
            chunk_type = chunk.get("chunk_type", "unknown")
            if chunk_type in chunks_by_type:
                chunks_by_type[chunk_type].append(chunk)
        
        # Map chunk types to collections
        type_to_collection = {
            "node_overview": "n8n_nodes",
            "node_properties": "n8n_nodes",
            "node_documentation": "n8n_nodes",
            "node_examples": "n8n_nodes",
            "ai_tool_usage": "n8n_nodes",
            "workflow_template": "n8n_templates",
            "workflow_pattern": "n8n_templates",  
            "task_configuration": "n8n_tasks",
            "connection_pattern": "n8n_connections"
        }
        
        # Index each chunk type
        for chunk_type, chunk_list in chunks_by_type.items():
            if not chunk_list:
                continue
            
            collection_name = type_to_collection.get(chunk_type, "n8n_nodes")
            collection = self.collections[collection_name]
            
            print(f"\n  📝 Indexing {len(chunk_list)} {chunk_type} chunks...")
            
            # Prepare data for indexing with deduplication
            seen_ids = set()
            ids = []
            texts = []
            metadatas = []
            documents = []
            
            for chunk in chunk_list:
                chunk_id = chunk["chunk_id"]
                # Skip duplicates within this batch
                if chunk_id in seen_ids:
                    print(f"    ⚠️ Skipping duplicate ID: {chunk_id}")
                    continue
                    
                seen_ids.add(chunk_id)
                ids.append(chunk_id)
                texts.append(chunk["embedding_text"])
                
                # Prepare metadata (ChromaDB only accepts str, int, float, bool)
                metadata = chunk.get("metadata", {})
                metadata["chunk_type"] = chunk_type
                metadata["indexed_at"] = datetime.now().isoformat()
                
                # Convert any list values to strings
                for key, value in list(metadata.items()):
                    if isinstance(value, list):
                        metadata[key] = ', '.join(str(v) for v in value) if value else ""
                
                metadatas.append(metadata)
                
                # Store original content as document
                documents.append(chunk.get("content", chunk["embedding_text"]))
            
            if not ids:
                print(f"  ⚠️ No unique chunks to index for {chunk_type}")
                continue
                
            print(f"  📊 Processing {len(ids)} unique chunks for {chunk_type}")
            
            # Create embeddings
            embeddings = self.create_embeddings(texts)
            
            # Add to collection with duplicate handling
            try:
                collection.add(
                    ids=ids,
                    embeddings=embeddings.tolist(),
                    metadatas=metadatas,
                    documents=documents
                )
            except Exception as e:
                if "duplicate" in str(e).lower():
                    print(f"  ⚠️ Handling duplicate IDs in {chunk_type} chunks...")
                    # Try to upsert instead
                    try:
                        collection.upsert(
                            ids=ids,
                            embeddings=embeddings.tolist(),
                            metadatas=metadatas,
                            documents=documents
                        )
                        print(f"  ✅ Successfully upserted {len(chunk_list)} {chunk_type} chunks")
                    except Exception as upsert_error:
                        print(f"  ❌ Failed to upsert {chunk_type}: {upsert_error}")
                        raise
                else:
                    raise
            
            print(f"  ✅ Indexed {len(chunk_list)} {chunk_type} chunks")
    
    def create_index_statistics(self) -> Dict[str, Any]:
        """Generate statistics about the vector index"""
        print("\n📊 Generating index statistics...")
        
        stats = {
            "index_date": datetime.now().isoformat(),
            "embedding_model": "all-MiniLM-L6-v2",
            "collections": {}
        }
        
        for name, collection in self.collections.items():
            count = collection.count()
            stats["collections"][name] = {
                "document_count": count,
                "description": collection.metadata.get("description", "")
            }
        
        # Save statistics
        stats_file = self.db_dir / "index_statistics.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        return stats
    
    def test_retrieval(self, query: str, collection_name: str = "n8n_nodes", k: int = 5):
        """Test retrieval with a sample query"""
        print(f"\n🔍 Testing retrieval for: '{query}'")
        
        collection = self.collections[collection_name]
        
        # Create query embedding
        query_embedding = self.embedding_model.encode([query])
        
        # Search
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=k
        )
        
        print(f"\n📋 Top {k} results from {collection_name}:")
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            print(f"\n  {i+1}. Distance: {distance:.4f}")
            print(f"     Type: {metadata.get('chunk_type', 'unknown')}")
            if 'node_type' in metadata:
                print(f"     Node: {metadata['node_type']}")
            print(f"     Preview: {doc[:200]}...")
    
    def run_indexing(self):
        """Run the complete indexing pipeline"""
        print("\n" + "="*60)
        print("🚀 n8n Vector Indexing Pipeline")
        print("="*60)
        
        try:
            # Load chunks
            chunks = self.load_chunks()
            
            # Index chunks
            self.index_chunks(chunks)
            
            # Generate statistics
            stats = self.create_index_statistics()
            
            # Print summary
            print("\n" + "="*60)
            print("📈 INDEXING SUMMARY")
            print("="*60)
            
            total_docs = sum(col["document_count"] for col in stats["collections"].values())
            print(f"✅ Total documents indexed: {total_docs}")
            print("\nDocuments per collection:")
            for name, info in stats["collections"].items():
                print(f"  • {name}: {info['document_count']} documents")
            
            print(f"\n📁 Vector database saved to: {self.db_dir}")
            
            # Test retrieval
            print("\n" + "="*60)
            print("🧪 TESTING RETRIEVAL")
            print("="*60)
            
            test_queries = [
                "webhook trigger slack notification",
                "transform data with javascript",
                "AI agent with tools",
                "connect to database"
            ]
            
            for query in test_queries:
                self.test_retrieval(query, k=3)
            
            print("\n✨ Vector indexing complete! RAG system ready.")
            
        except Exception as e:
            print(f"\n❌ Error during indexing: {e}")
            raise

class N8nRetriever:
    """Retrieval interface for the RAG system"""
    
    def __init__(self, db_dir: str = "./n8n_vector_db"):
        self.db_dir = Path(db_dir)
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Connect to ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=str(self.db_dir))
        
        # Load collections
        self.collections = {
            "n8n_nodes": self.chroma_client.get_collection("n8n_nodes"),
            "n8n_templates": self.chroma_client.get_collection("n8n_templates"),
            "n8n_tasks": self.chroma_client.get_collection("n8n_tasks"),
            "n8n_connections": self.chroma_client.get_collection("n8n_connections")
        }
    
    def multi_stage_retrieval(
        self,
        query: str,
        k_per_stage: int = 5,
        rerank: bool = True
    ) -> Dict[str, Any]:
        """
        Multi-stage retrieval for comprehensive context
        """
        # Create query embedding
        query_embedding = self.embedding_model.encode([query])
        
        results = {
            "query": query,
            "nodes": [],
            "templates": [],
            "tasks": [],
            "connections": [],
            "combined_context": ""
        }
        
        # Stage 1: Retrieve relevant nodes
        node_results = self.collections["n8n_nodes"].query(
            query_embeddings=query_embedding.tolist(),
            n_results=k_per_stage
        )
        results["nodes"] = self._format_results(node_results)
        
        # Stage 2: Retrieve templates
        template_results = self.collections["n8n_templates"].query(
            query_embeddings=query_embedding.tolist(),
            n_results=k_per_stage
        )
        results["templates"] = self._format_results(template_results)
        
        # Stage 3: Retrieve tasks
        task_results = self.collections["n8n_tasks"].query(
            query_embeddings=query_embedding.tolist(),
            n_results=k_per_stage
        )
        results["tasks"] = self._format_results(task_results)
        
        # Stage 4: Retrieve connection patterns
        connection_results = self.collections["n8n_connections"].query(
            query_embeddings=query_embedding.tolist(),
            n_results=k_per_stage
        )
        results["connections"] = self._format_results(connection_results)
        
        # Combine context
        results["combined_context"] = self._create_combined_context(results)
        
        return results
    
    def _format_results(self, raw_results: Dict) -> List[Dict]:
        """Format ChromaDB results"""
        formatted = []
        
        if raw_results['documents'] and len(raw_results['documents']) > 0:
            for doc, metadata, distance in zip(
                raw_results['documents'][0],
                raw_results['metadatas'][0],
                raw_results['distances'][0]
            ):
                formatted.append({
                    "content": doc,
                    "metadata": metadata,
                    "relevance_score": 1 - distance  # Convert distance to similarity
                })
        
        return formatted
    
    def _create_combined_context(self, results: Dict) -> str:
        """Create combined context for LLM"""
        context_parts = []
        
        # Add node information
        if results["nodes"]:
            context_parts.append("RELEVANT NODES:")
            for node in results["nodes"][:3]:
                context_parts.append(node["content"][:500])
        
        # Add templates
        if results["templates"]:
            context_parts.append("\nWORKFLOW TEMPLATES:")
            for template in results["templates"][:2]:
                context_parts.append(template["content"][:500])
        
        # Add tasks
        if results["tasks"]:
            context_parts.append("\nTASK CONFIGURATIONS:")
            for task in results["tasks"][:2]:
                context_parts.append(task["content"][:300])
        
        # Add connection patterns
        if results["connections"]:
            context_parts.append("\nCONNECTION PATTERNS:")
            for conn in results["connections"][:2]:
                context_parts.append(conn["content"][:300])
        
        return "\n".join(context_parts)

def main():
    """Main entry point for indexing"""
    indexer = N8nVectorIndexer()
    indexer.run_indexing()

if __name__ == "__main__":
    main()
