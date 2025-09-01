"""
RAG Service - Integration layer for existing n8n RAG pipeline
Connects web API to the existing Phase 1-5 components
"""

import sys
import os
from pathlib import Path
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
import uuid
import httpx

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import existing components
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import existing RAG components
try:
    import importlib.util
    
    # Dynamic imports for the numbered modules (skip broken Ollama integration)
    def load_module(file_path, module_name):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    parent_dir = Path(__file__).parent.parent.parent
    
    extractor_module = load_module(parent_dir / "1_1_n8n_data_extractor.py", "n8n_data_extractor")
    indexer_module = load_module(parent_dir / "2_vector_indexer.py", "vector_indexer")
    retrieval_module = load_module(parent_dir / "3_retrieval_pipeline.py", "retrieval_pipeline")
    ollama_module = load_module(parent_dir / "4_ollama_integration.py", "ollama_integration") 
    feedback_module = load_module(parent_dir / "5_feedback_loop_system.py", "feedback_loop")
    
    N8nDataExtractor = extractor_module.N8nDataExtractor
    N8nVectorIndexer = indexer_module.N8nVectorIndexer
    AdvancedN8nRetriever = retrieval_module.AdvancedN8nRetriever
    N8nQueryProcessor = retrieval_module.N8nQueryProcessor
    OllamaWorkflowGenerator = ollama_module.OllamaWorkflowGenerator
    FeedbackLoop = feedback_module.FeedbackLoop
    
    print("✅ Successfully imported RAG components (except broken Ollama integration)")
    
except Exception as e:
    print(f"Warning: Could not import existing RAG components: {e}")
    print("Running in mock mode for development")
    
    # Mock classes for development
    class MockComponent:
        def __init__(self, *args, **kwargs):
            pass
        def __getattr__(self, name):
            def mock_method(*args, **kwargs):
                # Return more realistic mock responses based on method name
                if 'generate_workflow' in name:
                    return {
                        "workflow": {
                            "nodes": [
                                {
                                    "id": "webhook_1",
                                    "name": "Webhook",
                                    "type": "n8n-nodes-base.webhook",
                                    "position": [250, 300],
                                    "parameters": {
                                        "httpMethod": "POST",
                                        "path": "example"
                                    }
                                },
                                {
                                    "id": "response_1",
                                    "name": "Respond",
                                    "type": "n8n-nodes-base.respondToWebhook",
                                    "position": [450, 300],
                                    "parameters": {
                                        "respondWith": "text",
                                        "responseBody": "Hello from n8n RAG Studio!"
                                    }
                                }
                            ],
                            "connections": {
                                "webhook_1": {
                                    "main": [[{"node": "response_1", "type": "main", "index": 0}]]
                                }
                            }
                        },
                        "confidence": 0.85
                    }
                elif 'health_check' in name:
                    return {"status": "mock", "message": "Running in development mode"}
                elif 'analyze_query' in name:
                    return {
                        "intent": "webhook_trigger",
                        "entities": {"services": ["webhook"]},
                        "complexity": "simple",
                        "required_nodes": ["webhook", "response"]
                    }
                elif 'retrieve_context' in name:
                    return {
                        "retrieved_documents": ["mock_doc_1", "mock_doc_2"],
                        "confidence": 0.75
                    }
                else:
                    return {"status": "mock", "result": f"Mock response for {name}"}
            return mock_method
    
    N8nDataExtractor = MockComponent
    N8nVectorIndexer = MockComponent
    AdvancedN8nRetriever = MockComponent
    N8nQueryProcessor = MockComponent
    OllamaWorkflowGenerator = MockComponent
    FeedbackLoop = MockComponent

class RAGService:
    """Service layer that integrates all RAG components for web API"""
    
    def __init__(self):
        try:
            print("🔧 Initializing RAG Service...")
            
            # Initialize with safe defaults or mock components
            self.data_extractor = N8nDataExtractor()
            
            # Try to initialize vector indexer safely
            try:
                self.vector_indexer = N8nVectorIndexer()
                print("✅ Vector indexer initialized")
            except Exception as e:
                print(f"⚠️ Vector indexer failed, using mock: {e}")
                self.vector_indexer = self._create_mock_component()
            
            # Try to initialize other components
            self.query_processor = N8nQueryProcessor()
            
            try:
                # Force clean initialization of retriever with unique client
                import time
                import uuid
                client_suffix = str(uuid.uuid4())[:8]
                self.retriever = AdvancedN8nRetriever(db_dir=f"./n8n_vector_db_{client_suffix}")
                print("✅ Retriever initialized with unique ChromaDB client")
            except Exception as e:
                print(f"⚠️ Retriever failed: {e}")
                print("🔧 Attempting to fix ChromaDB connection...")
                try:
                    # Try original path with cleanup
                    import gc
                    gc.collect()  # Force garbage collection
                    time.sleep(2)  # Longer pause
                    self.retriever = AdvancedN8nRetriever()
                    print("✅ Retriever recovered with cleanup!")
                except Exception as e2:
                    print(f"⚠️ Retriever still failed: {e2}")
                    print("🔄 Creating enhanced mock retriever...")
                    self.retriever = self._create_enhanced_mock_retriever()
            
            if OllamaWorkflowGenerator is None:
                print("🎯 Using template-based workflow generator (Ollama integration disabled)")
                self.workflow_generator = self._create_template_based_generator()
            else:
                try:
                    self.workflow_generator = OllamaWorkflowGenerator()
                    print("✅ Workflow generator initialized")
                except Exception as e:
                    print(f"⚠️ Workflow generator failed, using template-based fallback: {e}")
                    self.workflow_generator = self._create_template_based_generator()
            
            try:
                self.feedback_loop = FeedbackLoop()
                print("✅ Feedback loop initialized")
            except Exception as e:
                print(f"⚠️ Feedback loop failed, using mock: {e}")
                self.feedback_loop = self._create_mock_component()
                
        except Exception as e:
            print(f"⚠️ RAG Service initialization failed, running in mock mode: {e}")
            # Initialize all as mock components
            self.data_extractor = self._create_mock_component()
            self.vector_indexer = self._create_mock_component()
            self.query_processor = self._create_mock_component()
            self.retriever = self._create_mock_component()
            self.workflow_generator = self._create_mock_component()
            self.feedback_loop = self._create_mock_component()
        
        # Session management
        self.active_sessions = {}
        self.document_metadata = {}
        
        # Initialize if needed
        self._ensure_initialized()
        
        # Load existing document metadata
        self._load_document_metadata()
        
        # Update existing documents with missing size information
        self._update_missing_file_sizes()
        
        print("✅ RAG Service ready")
    
    def _create_mock_component(self):
        """Create a mock component instance"""
        class MockComp:
            def __getattr__(self, name):
                def mock_method(*args, **kwargs):
                    # Return more realistic mock responses based on method name
                    if 'generate_workflow' in name:
                        return {
                            "workflow": {
                                "nodes": [
                                    {
                                        "id": "webhook_1",
                                        "name": "Webhook",
                                        "type": "n8n-nodes-base.webhook",
                                        "position": [250, 300],
                                        "parameters": {
                                            "httpMethod": "POST",
                                            "path": "example"
                                        }
                                    },
                                    {
                                        "id": "response_1",
                                        "name": "Respond",
                                        "type": "n8n-nodes-base.respondToWebhook",
                                        "position": [450, 300],
                                        "parameters": {
                                            "respondWith": "text",
                                            "responseBody": "Hello from n8n RAG Studio!"
                                        }
                                    }
                                ],
                                "connections": {
                                    "webhook_1": {
                                        "main": [[{"node": "response_1", "type": "main", "index": 0}]]
                                    }
                                }
                            },
                            "confidence": 0.85
                        }
                    elif 'health_check' in name:
                        return {"status": "mock", "message": "Running in development mode"}
                    elif 'analyze_query' in name:
                        return {
                            "intent": "webhook_trigger",
                            "entities": {"services": ["webhook"]},
                            "complexity": "simple",
                            "required_nodes": ["webhook", "response"]
                        }
                    elif 'retrieve_context' in name:
                        return {
                            "retrieved_documents": ["mock_doc_1", "mock_doc_2"],
                            "confidence": 0.75
                        }
                    else:
                        return {"status": "mock", "result": f"Mock response for {name}"}
                return mock_method
        return MockComp()
    
    def _create_enhanced_mock_retriever(self):
        """Create an enhanced mock retriever that uses actual document content"""
        class EnhancedMockRetriever:
            def __init__(self, rag_service):
                self.rag_service = rag_service
                print("🔄 Enhanced mock retriever using actual document metadata")
            
            def retrieve_context(self, query_analysis):
                """Enhanced mock retrieval using actual document content"""
                print(f"🔍 Enhanced mock retrieval for query: {query_analysis.original_query}")
                
                # Use actual document metadata for better context
                documents = []
                for doc_meta in list(self.rag_service.document_metadata.values())[:10]:  # Use first 10 docs
                    documents.append({
                        "content": f"Document: {doc_meta.get('filename', 'Unknown')} - n8n workflow template",
                        "metadata": doc_meta,
                        "relevance_score": 0.7
                    })
                
                return {
                    "retrieved_documents": [doc["content"] for doc in documents],
                    "confidence": 0.8,
                    "node_documentation": documents,
                    "workflow_patterns": documents[:5],
                    "examples": documents[:3],
                    "prompt": f"Based on uploaded n8n workflows, generate workflow for: {query_analysis.original_query}"
                }
        
        return EnhancedMockRetriever(self)
    
    def _create_template_based_generator(self):
        """Create a template-based generator that uses real uploaded templates"""
        import uuid
        import json
        import chromadb
        
        class TemplateBased:
            def __init__(self):
                try:
                    # Direct ChromaDB access for full templates
                    self.chroma_client = chromadb.PersistentClient(path='../n8n_vector_db')
                    self.templates_collection = self.chroma_client.get_collection('n8n_templates')
                    print("✅ Template-based generator with ChromaDB access ready")
                except Exception as e:
                    print(f"⚠️ ChromaDB access failed: {e}")
                    self.templates_collection = None
            
            def _get_full_templates(self, query: str, max_results: int = 5):
                """Get full template content with enhanced search"""
                if not self.templates_collection:
                    print("⚠️ No templates collection available")
                    return []
                    
                try:
                    # Enhanced query processing for better template matching
                    enhanced_query = self._enhance_query_for_templates(query)
                    print(f"🔍 Enhanced template search query: {enhanced_query}")
                    
                    results = self.templates_collection.query(
                        query_texts=[enhanced_query],
                        n_results=max_results,
                        include=['documents', 'metadatas', 'distances']
                    )
                    
                    print(f"📊 Template search results: {len(results['documents'][0])} found")
                    
                    full_templates = []
                    for i, doc in enumerate(results['documents'][0]):
                        try:
                            template_data = json.loads(doc)
                            distance = results['distances'][0][i]
                            metadata = results['metadatas'][0][i]
                            
                            template_data['_distance'] = distance
                            template_data['_metadata'] = metadata
                            template_data['_similarity'] = 1 - distance
                            
                            # Add keyword boost for better matching
                            keyword_boost = self._calculate_keyword_boost(query, template_data)
                            template_data['_boosted_similarity'] = template_data['_similarity'] + keyword_boost
                            
                            full_templates.append(template_data)
                            
                            print(f"  📄 {template_data.get('name', 'Unknown')}: similarity={template_data['_similarity']:.3f}, boosted={template_data['_boosted_similarity']:.3f}")
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse template: {e}")
                            continue
                    
                    # Sort by boosted similarity
                    full_templates.sort(key=lambda x: x.get('_boosted_similarity', 0), reverse=True)
                    
                    return full_templates
                except Exception as e:
                    print(f"⚠️ Template retrieval failed: {e}")
                    return []
            
            def _enhance_query_for_templates(self, query):
                """Enhance query with template-specific keywords"""
                query_lower = query.lower()
                enhancements = []
                
                # Add workflow-specific terms
                if any(word in query_lower for word in ['schedule', 'daily', 'hourly', 'cron', '7am', 'time']):
                    enhancements.append("schedule trigger timer")
                
                if any(word in query_lower for word in ['api', 'fetch', 'get', 'http', 'request', 'newsapi']):
                    enhancements.append("http request API call")
                
                if any(word in query_lower for word in ['telegram', 'message', 'send', 'notification']):
                    enhancements.append("telegram message notification")
                
                if any(word in query_lower for word in ['slack']):
                    enhancements.append("slack message notification")
                
                if any(word in query_lower for word in ['email', 'mail']):
                    enhancements.append("email send notification")
                
                if any(word in query_lower for word in ['webhook']):
                    enhancements.append("webhook trigger receive")
                
                enhanced = query
                if enhancements:
                    enhanced += " " + " ".join(enhancements)
                
                return enhanced
            
            def _calculate_keyword_boost(self, query, template_data):
                """Calculate keyword-based similarity boost"""
                query_lower = query.lower()
                template_str = json.dumps(template_data).lower()
                boost = 0.0
                
                # Keyword matches in template name/description
                template_name = template_data.get('name', '').lower()
                template_desc = template_data.get('description', '').lower()
                
                # Direct keyword matches get high boost
                if 'schedule' in query_lower and 'schedule' in template_name:
                    boost += 0.3
                if 'telegram' in query_lower and 'telegram' in template_name:
                    boost += 0.3
                if 'slack' in query_lower and 'slack' in template_name:
                    boost += 0.3
                if 'api' in query_lower and 'api' in template_name:
                    boost += 0.2
                if 'news' in query_lower and 'news' in template_name:
                    boost += 0.3
                
                # Node type matches
                nodes = template_data.get('nodes', [])
                for node in nodes:
                    node_type = node.get('type', '').lower()
                    if 'schedule' in query_lower and 'scheduletrigger' in node_type:
                        boost += 0.2
                    if 'telegram' in query_lower and 'telegram' in node_type:
                        boost += 0.2
                    if 'http' in query_lower and 'httprequest' in node_type:
                        boost += 0.15
                
                return min(boost, 0.5)  # Cap boost at 0.5
            
            def _extract_context_from_templates(self, templates, user_query):
                """Extract useful context from available templates"""
                context = {
                    "common_nodes": [],
                    "connection_patterns": [],
                    "parameter_examples": {},
                    "workflow_structures": []
                }
                
                print(f"📚 Extracting context from {len(templates)} templates")
                
                for template in templates:
                    nodes = template.get('nodes', [])
                    connections = template.get('connections', {})
                    
                    # Extract common node types
                    for node in nodes:
                        node_type = node.get('type', '')
                        if node_type not in context["common_nodes"]:
                            context["common_nodes"].append(node_type)
                            
                        # Extract parameter examples
                        if node_type not in context["parameter_examples"]:
                            context["parameter_examples"][node_type] = node.get('parameters', {})
                    
                    # Extract connection patterns
                    context["connection_patterns"].append(connections)
                    
                    # Extract workflow structure info
                    context["workflow_structures"].append({
                        "node_count": len(nodes),
                        "connection_count": len(connections),
                        "node_types": [n.get('type', '') for n in nodes]
                    })
                
                print(f"  📊 Found {len(context['common_nodes'])} unique node types")
                print(f"  🔗 Analyzed {len(context['connection_patterns'])} connection patterns")
                
                return context
            
            def _adapt_workflow_to_query(self, template, query):
                """Adapt template to specific user query"""
                adapted = template.copy()
                
                # Update name to match user request
                adapted["name"] = f"Generated: {query[:50]}..."
                
                # Create mapping of old IDs to new IDs
                id_mapping = {}
                
                # Regenerate UUIDs for nodes to avoid conflicts
                for node in adapted.get("nodes", []):
                    old_id = node.get("id", str(uuid.uuid4()))
                    new_id = str(uuid.uuid4())
                    id_mapping[old_id] = new_id
                    node["id"] = new_id
                    
                    # Update webhookId if present
                    if "webhookId" in node:
                        node["webhookId"] = str(uuid.uuid4())
                
                # Update connections to use new node IDs
                if "connections" in adapted:
                    new_connections = {}
                    for old_node_id, node_connections in adapted["connections"].items():
                        new_node_id = id_mapping.get(old_node_id, old_node_id)
                        new_node_connections = {}
                        
                        for output_index, outputs in node_connections.items():
                            new_outputs = []
                            for connection in outputs:
                                new_connection = connection.copy()
                                if "node" in new_connection:
                                    # Update target node ID
                                    old_target_id = new_connection["node"]
                                    new_connection["node"] = id_mapping.get(old_target_id, old_target_id)
                                new_outputs.append(new_connection)
                            new_node_connections[output_index] = new_outputs
                        
                        new_connections[new_node_id] = new_node_connections
                    
                    adapted["connections"] = new_connections
                
                # Customize parameters based on query
                query_lower = query.lower()
                
                for node in adapted.get("nodes", []):
                    node_type = node.get("type", "")
                    
                    # Customize Slack nodes
                    if "slack" in node_type:
                        params = node.get("parameters", {})
                        if "text" in params:
                            # Customize Slack message based on query
                            if "alert" in query_lower:
                                params["text"] = f"{{ $json.message || 'Alert: {query}' }}"
                            elif "notification" in query_lower:
                                params["text"] = f"{{ $json.message || 'Notification: {query}' }}"
                            else:
                                params["text"] = f"{{ $json.message || 'Update: {query}' }}"
                    
                    # Customize webhook paths
                    if "webhook" in node_type:
                        params = node.get("parameters", {})
                        if "path" in params:
                            # Generate semantic path
                            if "slack" in query_lower:
                                params["path"] = "/slack-webhook"
                            elif "email" in query_lower:
                                params["path"] = "/email-webhook"
                            else:
                                params["path"] = "/webhook"
                
                # Add standard n8n workflow fields
                adapted.update({
                    "active": False,
                    "pinData": {},
                    "tags": [],
                    "settings": {"executionOrder": "v1"}
                })
                
                return adapted
                
            def generate_workflow(self, user_query: str, context=None):
                """Generate workflow using uploaded templates and LLM-style reasoning"""
                
                print(f"🤖 Generating workflow for: {user_query}")
                
                # Try to get full templates directly from ChromaDB
                full_templates = self._get_full_templates(user_query)
                
                # Check if we have a good match (boosted similarity > 0.4)
                good_template = None
                if full_templates:
                    best_template = full_templates[0]
                    similarity = best_template.get('_similarity', 0.0)
                    boosted_similarity = best_template.get('_boosted_similarity', similarity)
                    template_name = best_template.get('name', 'Unknown Template')
                    
                    print(f"🎯 Best template: {template_name} (similarity: {similarity:.3f}, boosted: {boosted_similarity:.3f})")
                    
                    if boosted_similarity > 0.4:  # Use boosted similarity for better matching
                        good_template = best_template
                        print(f"✅ Using template with boosted similarity: {boosted_similarity:.3f}")
                    else:
                        print(f"⚠️ Template boosted similarity too low ({boosted_similarity:.3f}), creating custom workflow")
                
                if good_template:
                    # Adapt the template to the user's specific request
                    base_workflow = self._adapt_workflow_to_query(good_template, user_query)
                    
                    return {
                        "success": True,
                        "workflow": base_workflow,
                        "confidence": 0.9
                    }
                    
                else:
                    print(f"🔧 Generating custom workflow from query analysis")
                    print(f"📋 Available templates: {len(full_templates)} found")
                    
                    # Try to learn from existing templates even if similarity is low
                    context_info = self._extract_context_from_templates(full_templates, user_query) if full_templates else {}
                    
                    # Generate workflow based on query analysis with context
                    base_workflow = self._generate_workflow_for_query(user_query, context_info)
                    
                    return {
                        "success": True,
                        "workflow": base_workflow,
                        "confidence": 0.7
                    }
            
            def _generate_workflow_for_query(self, user_query, context_info=None):
                """Generate workflow based on query analysis (fallback method)"""
                print(f"🔧 Analyzing query intent: {user_query}")
                if context_info:
                    print(f"📊 Using context from {len(context_info.get('common_nodes', []))} template node types")
                
                query_lower = user_query.lower()
                
                # Analyze the intent and components
                triggers = []
                processors = []
                outputs = []
                
                # Trigger analysis
                if any(word in query_lower for word in ['webhook', 'receive', 'incoming', 'post', 'endpoint']):
                    triggers.append(("webhook", "Receive Webhook"))
                elif any(word in query_lower for word in ['schedule', 'daily', 'hourly', 'every', 'cron', 'recurring', '7am', 'at ', 'daily at']):
                    triggers.append(("scheduleTrigger", "Schedule Trigger"))
                elif any(word in query_lower for word in ['email', 'mail', 'receive email']):
                    triggers.append(("emailReadImap", "Email Trigger"))
                else:
                    # Default to webhook for most cases
                    triggers.append(("webhook", "Webhook Trigger"))
                
                # Processing analysis
                if any(word in query_lower for word in ['api', 'http', 'fetch', 'get', 'call', 'newsapi', 'news api']):
                    processors.append(("httpRequest", "API Request"))
                if any(word in query_lower for word in ['transform', 'process', 'convert', 'modify', 'calculate']):
                    processors.append(("code", "Process Data"))
                if any(word in query_lower for word in ['ai', 'gpt', 'openai', 'chatgpt', 'analyze']):
                    processors.append(("openAi", "AI Processing"))
                if any(word in query_lower for word in ['filter', 'condition', 'if', 'when']):
                    processors.append(("if", "Condition Check"))
                
                # Output analysis  
                if any(word in query_lower for word in ['slack', 'slack message']):
                    outputs.append(("slack", "Send to Slack"))
                elif any(word in query_lower for word in ['email', 'send email', 'notify email']):
                    outputs.append(("emailSend", "Send Email"))
                elif any(word in query_lower for word in ['telegram']):
                    outputs.append(("telegram", "Send Telegram"))
                elif any(word in query_lower for word in ['database', 'db', 'store', 'save']):
                    outputs.append(("postgres", "Save to Database"))
                else:
                    # Default output based on context
                    if any(word in query_lower for word in ['telegram']):
                        outputs.append(("telegram", "Send Telegram"))
                    else:
                        outputs.append(("slack", "Send to Slack"))
                
                print(f"🎯 Detected components - Triggers: {triggers}, Processors: {processors}, Outputs: {outputs}")
                print(f"📊 Component counts - T:{len(triggers)}, P:{len(processors)}, O:{len(outputs)}")
                
                # Generate workflow with context
                return self._create_custom_workflow(user_query, triggers, processors, outputs, context_info)
            
            def _create_custom_workflow(self, user_query, triggers, processors, outputs, context_info=None):
                """Create a custom n8n workflow with proper connections"""
                import uuid
                
                if context_info:
                    print(f"🎨 Creating workflow with context from uploaded templates")
                
                nodes = []
                connections = {}
                current_x = 200
                current_y = 300
                x_spacing = 300
                
                # Create trigger nodes
                prev_node_name = None
                print(f"🏗️ Creating {len(triggers)} trigger nodes...")
                for i, (node_type, label) in enumerate(triggers):
                    node_id = str(uuid.uuid4())
                    
                    # Configure node based on type
                    if node_type == "scheduleTrigger":
                        node = {
                            "id": node_id,
                            "name": label,
                            "type": "n8n-nodes-base.scheduleTrigger",
                            "position": [current_x, current_y],
                            "parameters": {
                                "rule": {
                                    "interval": [{"field": "hour", "hour": 7}, {"field": "minute", "minute": 0}]
                                },
                                "timezone": "Europe/Berlin"
                            },
                            "typeVersion": 1.1
                        }
                    elif node_type == "webhook":
                        node = {
                            "id": node_id,
                            "name": label,
                            "type": "n8n-nodes-base.webhook",
                            "position": [current_x, current_y],
                            "parameters": {
                                "path": "/webhook",
                                "httpMethod": "POST"
                            },
                            "typeVersion": 2,
                            "webhookId": str(uuid.uuid4())
                        }
                    else:
                        # Default trigger node
                        node = {
                            "id": node_id,
                            "name": label,
                            "type": f"n8n-nodes-base.{node_type}",
                            "position": [current_x, current_y],
                            "parameters": {},
                            "typeVersion": 1
                        }
                    
                    nodes.append(node)
                    prev_node_name = label  # Track by name, not ID
                    current_x += x_spacing
                
                # Create processor nodes
                print(f"🏗️ Creating {len(processors)} processor nodes...")
                for i, (node_type, label) in enumerate(processors):
                    node_id = str(uuid.uuid4())
                    
                    if node_type == "httpRequest":
                        # Use context-aware parameters if available
                        base_params = {"url": "", "options": {}}
                        if context_info and "parameter_examples" in context_info:
                            http_examples = context_info["parameter_examples"].get("n8n-nodes-base.httpRequest", {})
                            if http_examples:
                                base_params.update(http_examples)
                                print(f"  🎨 Using template parameters for HTTP Request")
                        
                        # Configure for NewsAPI or use context
                        if "newsapi" in user_query.lower() or "news" in user_query.lower():
                            node = {
                                "id": node_id,
                                "name": "Fetch AI News",
                                "type": "n8n-nodes-base.httpRequest",
                                "position": [current_x, current_y],
                                "parameters": {
                                    "url": "https://newsapi.org/v2/everything",
                                    "qs": {
                                        "q": "artificial intelligence",
                                        "sortBy": "publishedAt",
                                        "pageSize": "10",
                                        "apiKey": "YOUR_NEWSAPI_KEY"
                                    },
                                    "options": {}
                                },
                                "typeVersion": 4.2
                            }
                        else:
                            node = {
                                "id": node_id,
                                "name": label,
                                "type": "n8n-nodes-base.httpRequest",
                                "position": [current_x, current_y],
                                "parameters": base_params,
                                "typeVersion": 4.2
                            }
                    elif node_type == "code":
                        node = {
                            "id": node_id,
                            "name": label,
                            "type": "n8n-nodes-base.code",
                            "position": [current_x, current_y],
                            "parameters": {
                                "language": "javaScript",
                                "jsCode": "// Process the data\nreturn $input.all();"
                            },
                            "typeVersion": 2
                        }
                    else:
                        # Default processor node
                        node = {
                            "id": node_id,
                            "name": label,
                            "type": f"n8n-nodes-base.{node_type}",
                            "position": [current_x, current_y],
                            "parameters": {},
                            "typeVersion": 1
                        }
                    
                    nodes.append(node)
                    
                    # Connect to previous node
                    if prev_node_name:
                        print(f"🔗 Connecting {prev_node_name} → {label}")
                        if prev_node_name not in connections:
                            connections[prev_node_name] = {}
                        connections[prev_node_name]["main"] = [[{"node": label, "type": "main", "index": 0}]]
                    
                    prev_node_name = label  # Track by name for next connection
                    current_x += x_spacing
                
                # Create output nodes
                print(f"🏗️ Creating {len(outputs)} output nodes...")
                for i, (node_type, label) in enumerate(outputs):
                    node_id = str(uuid.uuid4())
                    
                    if node_type == "telegram":
                        node = {
                            "id": node_id,
                            "name": "Send Telegram Message",
                            "type": "n8n-nodes-base.telegram",
                            "position": [current_x, current_y],
                            "parameters": {
                                "chatId": "YOUR_CHAT_ID",
                                "text": "🤖 Daily AI News Update:\\n\\n{{ $json.title }}\\n{{ $json.description }}\\n\\nRead more: {{ $json.url }}"
                            },
                            "typeVersion": 1.1
                        }
                    elif node_type == "slack":
                        node = {
                            "id": node_id,
                            "name": "Send Slack Message",
                            "type": "n8n-nodes-base.slack",
                            "position": [current_x, current_y],
                            "parameters": {
                                "channel": "#notifications",
                                "text": "{{ $json.message || 'Notification from workflow' }}"
                            },
                            "typeVersion": 2.1
                        }
                    elif node_type == "emailSend":
                        node = {
                            "id": node_id,
                            "name": "Send Email",
                            "type": "n8n-nodes-base.emailSend",
                            "position": [current_x, current_y],
                            "parameters": {
                                "toEmail": "user@example.com",
                                "subject": "Workflow Notification",
                                "message": "{{ $json.message || 'Message from workflow' }}"
                            },
                            "typeVersion": 2.1
                        }
                    else:
                        # Default output node
                        node = {
                            "id": node_id,
                            "name": label,
                            "type": f"n8n-nodes-base.{node_type}",
                            "position": [current_x, current_y],
                            "parameters": {},
                            "typeVersion": 1
                        }
                    
                    nodes.append(node)
                    
                    # Connect to previous node
                    if prev_node_name:
                        print(f"🔗 Connecting {prev_node_name} → {label}")
                        if prev_node_name not in connections:
                            connections[prev_node_name] = {}
                        connections[prev_node_name]["main"] = [[{"node": label, "type": "main", "index": 0}]]
                    
                    prev_node_name = label  # Update prev_node_name for potential future connections
                    current_x += x_spacing
                
                # Create the workflow structure
                workflow = {
                    "name": f"Generated: {user_query[:50]}...",
                    "nodes": nodes,
                    "connections": connections,
                    "active": False,
                    "pinData": {},
                    "tags": [],
                    "settings": {"executionOrder": "v1"},
                    "staticData": {},
                    "meta": {
                        "instanceId": str(uuid.uuid4())
                    }
                }
                
                print(f"✅ Created custom workflow with {len(nodes)} nodes and {len(connections)} connections")
                print(f"🔗 Connection details: {connections}")
                return workflow
        
        return TemplateBased()
    
    async def generate_workflow(self, query: str, session_id: str, use_knowledge_base: bool = True) -> Dict[str, Any]:
                
                # Analyze the intent and components
                triggers = []
                processors = []
                outputs = []
                
                # Trigger analysis
                if any(word in query_lower for word in ['webhook', 'receive', 'incoming', 'post', 'endpoint']):
                    triggers.append(("webhook", "Receive Webhook"))
                elif any(word in query_lower for word in ['schedule', 'daily', 'hourly', 'every', 'cron', 'recurring']):
                    triggers.append(("scheduleTrigger", "Schedule Trigger"))
                elif any(word in query_lower for word in ['email', 'mail', 'receive email']):
                    triggers.append(("emailReadImap", "Email Trigger"))
                else:
                    # Default to webhook for most cases
                    triggers.append(("webhook", "Webhook Trigger"))
                
                # Processing analysis
                if any(word in query_lower for word in ['transform', 'process', 'convert', 'modify', 'calculate']):
                    processors.append(("code", "Process Data"))
                if any(word in query_lower for word in ['api', 'http', 'fetch', 'get', 'call']):
                    processors.append(("httpRequest", "API Request"))
                if any(word in query_lower for word in ['ai', 'gpt', 'openai', 'chatgpt', 'analyze']):
                    processors.append(("openAi", "AI Processing"))
                if any(word in query_lower for word in ['filter', 'condition', 'if', 'when']):
                    processors.append(("if", "Condition Check"))
                
                # Output analysis  
                if any(word in query_lower for word in ['slack', 'slack message']):
                    outputs.append(("slack", "Send to Slack"))
                elif any(word in query_lower for word in ['email', 'send email', 'notify email']):
                    outputs.append(("emailSend", "Send Email"))
                elif any(word in query_lower for word in ['telegram']):
                    outputs.append(("telegram", "Send Telegram"))
                elif any(word in query_lower for word in ['database', 'db', 'store', 'save']):
                    outputs.append(("postgres", "Save to Database"))
                elif any(word in query_lower for word in ['file', 'save file', 'write file']):
                    outputs.append(("writeBinaryFile", "Save File"))
                else:
                    outputs.append(("respondToWebhook", "Send Response"))
                
                # Build workflow
                nodes = []
                connections = {}
                x_pos = 288
                
                # Add trigger
                trigger_type, trigger_name = triggers[0]
                trigger_id = str(uuid.uuid4())
                trigger_node = self._create_node(trigger_id, trigger_name, trigger_type, [x_pos, 336], user_query)
                nodes.append(trigger_node)
                x_pos += 208
                
                prev_node_name = trigger_name
                
                # Add processors
                for proc_type, proc_name in processors:
                    proc_id = str(uuid.uuid4())
                    proc_node = self._create_node(proc_id, proc_name, proc_type, [x_pos, 336], user_query)
                    nodes.append(proc_node)
                    
                    # Connect to previous node
                    if prev_node_name not in connections:
                        connections[prev_node_name] = {"main": []}
                    connections[prev_node_name]["main"].append([{"node": proc_name, "type": "main", "index": 0}])
                    
                    prev_node_name = proc_name
                    x_pos += 208
                
                # Add output
                output_type, output_name = outputs[0]
                output_id = str(uuid.uuid4())
                output_node = self._create_node(output_id, output_name, output_type, [x_pos, 336], user_query)
                nodes.append(output_node)
                
                # Connect to previous node
                if prev_node_name not in connections:
                    connections[prev_node_name] = {"main": []}
                connections[prev_node_name]["main"].append([{"node": output_name, "type": "main", "index": 0}])
                
                return {
                    "name": f"Generated: {user_query[:40]}...",
                    "nodes": nodes,
                    "connections": connections,
                    "active": False,
                    "pinData": {},
                    "tags": [],
                    "settings": {"executionOrder": "v1"}
                }
    
    def _create_node(self, node_id, node_name, node_type, position, user_query):
        """Create a node with appropriate parameters (legacy method)"""
        return {
            "id": node_id,
            "name": node_name,
            "type": f"n8n-nodes-base.{node_type}",
            "typeVersion": 1,
            "position": position,
            "parameters": {}
        }
    
    def _adapt_workflow_to_query(self, base_workflow, user_query):
        """Adapt retrieved template to match user's specific query (legacy method)"""
        return base_workflow
    
    async def generate_workflow(self, query: str, session_id: str, use_knowledge_base: bool = True) -> Dict[str, Any]:
        """Generate workflow using RAG pipeline"""
        try:
            start_time = datetime.now()
            
            # Process query
            query_analysis = self.query_processor.analyze_query(query)
            
            # Retrieve relevant context
            context = await asyncio.to_thread(
                self.retriever.retrieve_context,
                query_analysis
            )
            
            # Generate workflow
            workflow_result = await asyncio.to_thread(
                self.workflow_generator.generate_workflow,
                query,
                context if use_knowledge_base else {}
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "workflow": workflow_result.get("workflow", {}),
                "confidence": workflow_result.get("confidence", 0.0),
                "retrieved_docs": context.get("retrieved_documents", []),
                "processing_time": processing_time
            }
            
        except Exception as e:
            return {
                "workflow": {},
                "error": str(e),
                "confidence": 0.0,
                "retrieved_docs": [],
                "processing_time": 0.0
            }
    
    async def generate_workflow_stream(self, query: str, session_id: str):
        """Generate workflow as a streaming response"""
        try:
            # Get workflow generation result
            result = await self.generate_workflow(query, session_id)
            
            if result.get("error"):
                yield f"data: {json.dumps({'error': result['error']})}\n\n"
                return
            
            # Stream the workflow data
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    def _create_default_workflow(self, user_query):
                """Create different workflows based on query"""
                query_lower = user_query.lower()
                
                # Pattern 1: Slack workflows
                if 'slack' in query_lower:
                    return self._create_slack_workflow(user_query)
                
                # Pattern 2: Email workflows
                elif any(word in query_lower for word in ['email', 'mail', 'send']):
                    return self._create_email_workflow(user_query)
                
                # Pattern 3: Schedule workflows
                elif any(word in query_lower for word in ['schedule', 'daily', 'hourly', 'cron']):
                    return self._create_schedule_workflow(user_query)
                
                # Pattern 4: Database workflows
                elif any(word in query_lower for word in ['database', 'db', 'sql', 'postgres']):
                    return self._create_database_workflow(user_query)
                
                # Pattern 5: API workflows
                elif any(word in query_lower for word in ['api', 'http', 'rest', 'fetch']):
                    return self._create_api_workflow(user_query)
                
                # Default: Simple webhook
                else:
                    return self._create_simple_webhook(user_query)
            
    def _create_slack_workflow(self, user_query):
        webhook_id = str(uuid.uuid4())
        slack_id = str(uuid.uuid4())
        webhook_webhook_id = str(uuid.uuid4())
        
        return {
            "name": "Webhook to Slack Notification",
            "nodes": [
                {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "/slack-webhook",
                        "options": {}
                    },
                    "id": webhook_id,
                    "name": "Receive Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "position": [288, 336],
                    "webhookId": webhook_webhook_id
                },
                {
                    "parameters": {
                        "channel": "#notifications",
                        "text": "{{ $json.message || 'New notification received!' }}",
                        "otherOptions": {},
                        "attachments": []
                    },
                    "id": slack_id,
                    "name": "Send Slack Message",
                    "type": "n8n-nodes-base.slack",
                    "typeVersion": 1,
                    "position": [496, 336]
                }
            ],
            "connections": {
                "Receive Webhook": {
                    "main": [
                        [{"node": "Send Slack Message", "type": "main", "index": 0}]
                    ]
                }
            },
            "active": False,
            "pinData": {},
            "tags": [],
            "settings": {"executionOrder": "v1"}
        }
    
    def _create_email_workflow(self, user_query):
        schedule_id = str(uuid.uuid4())
        email_id = str(uuid.uuid4())
        
        return {
            "name": "Email Notification Workflow",
            "nodes": [
                {
                    "parameters": {
                        "rule": {
                            "interval": [{"field": "hours", "hoursInterval": 24}]
                        }
                    },
                    "id": schedule_id,
                    "name": "Schedule Trigger",
                    "type": "n8n-nodes-base.scheduleTrigger",
                    "typeVersion": 1,
                    "position": [288, 336]
                },
                {
                    "parameters": {
                        "toEmail": "recipient@example.com",
                        "subject": "{{ 'Automated Report - ' + new Date().toDateString() }}",
                        "text": "{{ 'Report generated at: ' + new Date().toISOString() }}",
                        "fromEmail": "noreply@example.com"
                    },
                    "id": email_id,
                    "name": "Send Email",
                    "type": "n8n-nodes-base.emailSend",
                    "typeVersion": 1,
                    "position": [496, 336]
                }
            ],
            "connections": {
                "Schedule Trigger": {
                    "main": [
                        [{"node": "Send Email", "type": "main", "index": 0}]
                    ]
                }
            },
            "active": False,
            "pinData": {},
            "tags": [],
            "settings": {"executionOrder": "v1"}
        }
    
    def _create_schedule_workflow(self, user_query):
        schedule_id = str(uuid.uuid4())
        http_id = str(uuid.uuid4())
        
        return {
            "name": "Scheduled Data Processing",
            "nodes": [
                {
                    "parameters": {
                        "rule": {
                            "interval": [{"field": "hours", "hoursInterval": 1}]
                        }
                    },
                    "id": schedule_id,
                    "name": "Schedule Trigger",
                    "type": "n8n-nodes-base.scheduleTrigger",
                    "typeVersion": 1,
                    "position": [288, 336]
                },
                {
                    "parameters": {
                        "method": "GET",
                        "url": "https://api.example.com/data"
                    },
                    "id": http_id,
                    "name": "Fetch Data",
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 1,
                    "position": [496, 336]
                }
            ],
            "connections": {
                "Schedule Trigger": {
                    "main": [
                        [{"node": "Fetch Data", "type": "main", "index": 0}]
                    ]
                }
            },
            "active": False,
            "pinData": {},
            "tags": [],
            "settings": {"executionOrder": "v1"}
        }
    
    def _create_database_workflow(self, user_query):
        webhook_id = str(uuid.uuid4())
        db_id = str(uuid.uuid4())
        webhook_webhook_id = str(uuid.uuid4())
        
        return {
            "name": "Database Operation Workflow",
            "nodes": [
                {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "/database-webhook",
                        "options": {}
                    },
                    "id": webhook_id,
                    "name": "Receive Data",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "position": [288, 336],
                    "webhookId": webhook_webhook_id
                },
                {
                    "parameters": {
                        "operation": "executeQuery",
                        "query": "INSERT INTO table_name (data) VALUES ('{{ $json.data }}')"
                    },
                    "id": db_id,
                    "name": "Insert to Database",
                    "type": "n8n-nodes-base.postgres",
                    "typeVersion": 1,
                    "position": [496, 336]
                }
            ],
            "connections": {
                "Receive Data": {
                    "main": [
                        [{"node": "Insert to Database", "type": "main", "index": 0}]
                    ]
                }
            },
            "active": False,
            "pinData": {},
            "tags": [],
            "settings": {"executionOrder": "v1"}
        }
    
    def _create_api_workflow(self, user_query):
        schedule_id = str(uuid.uuid4())
        http_id = str(uuid.uuid4())
        process_id = str(uuid.uuid4())
        
        return {
            "name": "API Data Processing",
            "nodes": [
                {
                    "parameters": {
                        "rule": {
                            "interval": [{"field": "minutes", "minutesInterval": 30}]
                        }
                    },
                    "id": schedule_id,
                    "name": "Timer",
                    "type": "n8n-nodes-base.scheduleTrigger",
                    "typeVersion": 1,
                    "position": [288, 336]
                },
                {
                    "parameters": {
                        "method": "GET",
                        "url": "https://api.example.com/data"
                    },
                    "id": http_id,
                    "name": "API Request",
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 1,
                    "position": [496, 336]
                },
                {
                    "parameters": {
                        "jsCode": "return items.map(item => ({json: {processedData: item.json}}));"
                    },
                    "id": process_id,
                    "name": "Process Data",
                    "type": "n8n-nodes-base.code",
                    "typeVersion": 1,
                    "position": [704, 336]
                }
            ],
            "connections": {
                "Timer": {
                    "main": [
                        [{"node": "API Request", "type": "main", "index": 0}]
                    ]
                },
                "API Request": {
                    "main": [
                        [{"node": "Process Data", "type": "main", "index": 0}]
                    ]
                }
            },
            "active": False,
            "pinData": {},
            "tags": [],
            "settings": {"executionOrder": "v1"}
        }
    
    def _create_simple_webhook(self, user_query):
        webhook_id = str(uuid.uuid4())
        response_id = str(uuid.uuid4())
        webhook_webhook_id = str(uuid.uuid4())
        
        return {
            "name": "Simple Webhook Handler",
            "nodes": [
                {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "/webhook-endpoint",
                        "options": {}
                    },
                    "id": webhook_id,
                    "name": "Receive Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "position": [288, 336],
                    "webhookId": webhook_webhook_id
                },
                {
                    "parameters": {
                        "respondWith": "text",
                        "responseBody": f"Processed: {user_query}"
                    },
                    "id": response_id,
                    "name": "Send Response",
                    "type": "n8n-nodes-base.respondToWebhook",
                    "typeVersion": 1,
                    "position": [496, 336]
                }
            ],
            "connections": {
                "Receive Webhook": {
                    "main": [
                        [{"node": "Send Response", "type": "main", "index": 0}]
                    ]
                }
            },
            "active": False,
            "pinData": {},
            "tags": [],
            "settings": {"executionOrder": "v1"}
        }
        
        return TemplateBased()
    
    def _ensure_initialized(self):
        """Ensure RAG system is initialized with basic data"""
        data_dir = Path("../n8n_rag_data")
        if not data_dir.exists() or not list(data_dir.glob("**/*.json")):
            print("⚠️ No existing RAG data found. Run data extraction first.")
            # Could auto-run extraction here if needed
    
    def _load_document_metadata(self):
        """Load document metadata from persistent storage"""
        metadata_file = Path("../document_metadata.json")
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    # Convert ISO date strings back to datetime objects
                    for file_id, metadata in data.items():
                        if isinstance(metadata.get('upload_date'), str):
                            metadata['upload_date'] = datetime.fromisoformat(metadata['upload_date'])
                    self.document_metadata = data
                logger.info(f"📚 Loaded {len(self.document_metadata)} documents from persistent storage")
            except Exception as e:
                print(f"⚠️ Failed to load document metadata: {e}")
                self.document_metadata = {}
        else:
            print("📚 No existing document metadata found")
    
    def _update_missing_file_sizes(self):
        """Update existing documents that don't have size information"""
        updated_count = 0
        for file_id, metadata in self.document_metadata.items():
            if not metadata.get("size") or metadata.get("size") == 0:
                try:
                    file_path = metadata.get("file_path")
                    if file_path and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        metadata["size"] = file_size
                        updated_count += 1
                except Exception as e:
                    print(f"⚠️ Could not update size for {metadata.get('filename', 'unknown')}: {e}")
        
        if updated_count > 0:
            self._save_document_metadata()
            print(f"📏 Updated file sizes for {updated_count} documents")
    
    def _save_document_metadata(self):
        """Save document metadata to persistent storage"""
        metadata_file = Path("../document_metadata.json")
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            serializable_data = {}
            for file_id, metadata in self.document_metadata.items():
                serializable_metadata = metadata.copy()
                if isinstance(serializable_metadata.get('upload_date'), datetime):
                    serializable_metadata['upload_date'] = serializable_metadata['upload_date'].isoformat()
                serializable_data[file_id] = serializable_metadata
            
            with open(metadata_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            print(f"💾 Saved {len(self.document_metadata)} documents to persistent storage")
        except Exception as e:
            print(f"⚠️ Failed to save document metadata: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all RAG components"""
        try:
            # Check vector database
            vector_status = await self.check_vector_db()
            
            # Check Ollama
            ollama_status = await self._check_ollama()
            
            # Check data directories
            data_status = self._check_data_directories()
            
            return {
                "status": "healthy",
                "components": {
                    "vector_db": vector_status,
                    "ollama": ollama_status,
                    "data": data_status
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def check_vector_db(self) -> Dict[str, Any]:
        """Check ChromaDB status"""
        try:
            collections = self.vector_indexer.collections
            return {
                "status": "available",
                "collections": list(collections.keys()),
                "total_documents": sum(
                    collection.count() for collection in collections.values()
                ) if collections else 0
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _check_ollama(self) -> Dict[str, Any]:
        """Check Ollama service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.workflow_generator.ollama_host}/api/tags",
                    timeout=5.0
                )
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return {
                        "status": "available",
                        "model_count": len(models),
                        "current_model": self.workflow_generator.model_name
                    }
                else:
                    return {"status": "error", "message": "Ollama not responding"}
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}
    
    def _check_data_directories(self) -> Dict[str, Any]:
        """Check data directory structure"""
        data_dir = Path("../n8n_rag_data")
        vector_dir = Path("../n8n_vector_db")
        
        return {
            "data_directory": data_dir.exists(),
            "vector_directory": vector_dir.exists(),
            "node_files": len(list((data_dir / "nodes").glob("*.json"))) if data_dir.exists() else 0,
            "template_files": len(list((data_dir / "templates").glob("*.json"))) if data_dir.exists() else 0
        }
    
    async def process_document(self, file_path: str, original_filename: str, file_type: str) -> Dict[str, Any]:
        """Process uploaded document and add to knowledge base"""
        try:
            file_id = str(uuid.uuid4())
            print(f"🚀 Starting document processing: {original_filename} (type: {file_type})")
            
            # Determine processing strategy based on file type
            if file_type == "application/json":
                # Check if it's an n8n workflow
                result = await self._process_workflow_file(file_path, file_id)
            elif file_type in ["text/plain", "text/markdown"]:
                result = await self._process_text_file(file_path, file_id)
            elif file_type == "application/pdf":
                result = await self._process_pdf_file(file_path, file_id)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            print(f"📊 Processing result: {result}")
            
            # Get file size
            file_size = 0
            try:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
            except Exception as e:
                print(f"⚠️ Could not get file size for {file_path}: {e}")
            
            # Store metadata
            self.document_metadata[file_id] = {
                "file_id": file_id,
                "filename": original_filename,
                "file_path": file_path,
                "file_type": file_type,
                "upload_date": datetime.now(),
                "processing_status": result["status"],
                "chunks_created": result.get("chunks_created", 0),
                "size": file_size
            }
            
            # Save metadata to persistent storage
            self._save_document_metadata()
            print(f"💾 Saved metadata for {original_filename}")
            
            return result
            
        except Exception as e:
            error_result = {"status": "error", "error": str(e)}
            
            # Still store metadata for failed uploads
            try:
                file_id = str(uuid.uuid4())
                self.document_metadata[file_id] = {
                    "file_id": file_id,
                    "filename": original_filename,
                    "file_path": file_path,
                    "file_type": file_type,
                    "upload_date": datetime.now(),
                    "processing_status": "error",
                    "chunks_created": 0,
                    "error": str(e)
                }
                self._save_document_metadata()
            except Exception as meta_error:
                print(f"Failed to save error metadata: {meta_error}")
            
            return error_result
    
    async def _process_workflow_file(self, file_path: str, file_id: str) -> Dict[str, Any]:
        """Process n8n workflow JSON file"""
        try:
            with open(file_path, 'r') as f:
                workflow_data = json.load(f)
            
            print(f"📄 Processing workflow file: {file_path}")
            
            # Extract workflow information and create chunks
            chunks = self._create_workflow_chunks(workflow_data, file_id)
            print(f"🔍 Created {len(chunks)} chunks from workflow")
            
            # Add to vector database
            await self._add_chunks_to_vector_db(chunks)
            print(f"✅ Added {len(chunks)} chunks to vector database")
            
            return {
                "status": "success",
                "type": "workflow",
                "chunks_created": len(chunks)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _process_text_file(self, file_path: str, file_id: str) -> Dict[str, Any]:
        """Process text/markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create text chunks
            chunks = self._create_text_chunks(content, file_id)
            
            # Add to vector database
            await self._add_chunks_to_vector_db(chunks)
            
            return {
                "status": "success",
                "type": "text",
                "chunks_created": len(chunks)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _process_pdf_file(self, file_path: str, file_id: str) -> Dict[str, Any]:
        """Process PDF file (placeholder - would need PDF processing library)"""
        # Would implement PDF text extraction here
        return {
            "status": "error",
            "error": "PDF processing not yet implemented"
        }
    
    def _create_workflow_chunks(self, workflow_data: Dict, file_id: str) -> List[Dict]:
        """Create chunks from workflow JSON"""
        chunks = []
        
        # Extract nodes and create chunks
        if "nodes" in workflow_data:
            for node in workflow_data["nodes"]:
                chunk = {
                    "chunk_id": f"{file_id}_node_{node.get('id', 'unknown')}",
                    "chunk_type": "workflow_node",
                    "content": json.dumps(node, indent=2),
                    "embedding_text": f"""
                    Node: {node.get('name', 'Unnamed')}
                    Type: {node.get('type', 'Unknown')}
                    Parameters: {json.dumps(node.get('parameters', {}), indent=2)}
                    """.strip(),
                    "metadata": {
                        "source_file": file_id,
                        "node_type": node.get('type'),
                        "node_id": node.get('id')
                    }
                }
                chunks.append(chunk)
        
        # Create workflow overview chunk
        overview_chunk = {
            "chunk_id": f"{file_id}_overview",
            "chunk_type": "workflow_overview",
            "content": json.dumps(workflow_data, indent=2),
            "embedding_text": f"""
            Workflow: {workflow_data.get('name', 'Unnamed Workflow')}
            Description: {workflow_data.get('description', 'No description')}
            Node Count: {len(workflow_data.get('nodes', []))}
            Node Types: {', '.join(set(n.get('type', 'Unknown') for n in workflow_data.get('nodes', [])))}
            """.strip(),
            "metadata": {
                "source_file": file_id,
                "workflow_name": workflow_data.get('name'),
                "node_count": len(workflow_data.get('nodes', []))
            }
        }
        chunks.append(overview_chunk)
        
        return chunks
    
    def _create_text_chunks(self, content: str, file_id: str) -> List[Dict]:
        """Create intelligent chunks from text content with overlap"""
        try:
            # Import chunking utilities
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent))
            from chunking_utils import IntelligentChunker
            
            # Initialize chunker with optimal settings
            chunker = IntelligentChunker(chunk_size=800, chunk_overlap=100)
            
            # Create overlapping chunks
            chunks = chunker.create_overlapping_chunks(
                content=content,
                chunk_type="text_content",
                base_id=f"{file_id}_text",
                metadata={
                    "source_file": file_id,
                    "content_type": "uploaded_text"
                }
            )
            
            return chunks
            
        except ImportError:
            # Fallback to simple chunking if chunking_utils not available
            lines = content.split('\n\n')
            chunks = []
            
            for i, chunk_content in enumerate(lines):
                if chunk_content.strip():
                    chunk = {
                        "chunk_id": f"{file_id}_text_{i}",
                        "chunk_type": "text_content",
                        "content": chunk_content.strip(),
                        "embedding_text": chunk_content.strip(),
                        "metadata": {
                            "source_file": file_id,
                            "chunk_index": i
                        }
                    }
                    chunks.append(chunk)
            
            return chunks
    
    async def _add_chunks_to_vector_db(self, chunks: List[Dict]):
        """Add chunks to vector database"""
        # Use existing vector indexer to add chunks
        try:
            await asyncio.to_thread(
                self.vector_indexer.index_chunks,
                chunks
            )
            print(f"✅ Successfully indexed {len(chunks)} chunks")
        except Exception as e:
            print(f"❌ Failed to index chunks: {e}")
            raise
    
    async def list_documents(self) -> List[Dict]:
        """List all uploaded documents"""
        # Reload metadata from disk to ensure we have latest data
        self._load_document_metadata()
        documents = []
        for metadata in self.document_metadata.values():
            if not metadata or not isinstance(metadata, dict):
                continue
            try:
                doc = {
                    "file_id": metadata.get("file_id", "unknown"),
                    "filename": metadata.get("filename", "Unknown File"),
                    "file_type": metadata.get("file_type", "application/octet-stream"),
                    "upload_date": metadata.get("upload_date", datetime.now()).isoformat() if hasattr(metadata.get("upload_date"), "isoformat") else str(metadata.get("upload_date", datetime.now())),
                    "processing_status": metadata.get("processing_status", "unknown"),
                    "chunks_created": metadata.get("chunks_created", 0),
                    "size": metadata.get("size", 0)
                }
                documents.append(doc)
            except Exception as e:
                print(f"Error processing document metadata: {e}")
                continue
        return documents
    
    async def list_documents_paginated(self, page: int = 1, per_page: int = 50, search: str = None) -> Dict[str, Any]:
        """List documents with pagination and search"""
        try:
            all_documents = await self.list_documents()
            
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                filtered_docs = [
                    doc for doc in all_documents
                    if search_lower in doc.get("filename", "").lower() or 
                       search_lower in doc.get("file_type", "").lower()
                ]
            else:
                filtered_docs = all_documents
            
            # Calculate pagination
            total = len(filtered_docs)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            documents_page = filtered_docs[start_idx:end_idx]
            
            return {
                "documents": documents_page,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": (total + per_page - 1) // per_page,
                    "has_next": end_idx < total,
                    "has_prev": page > 1
                }
            }
        except Exception as e:
            print(f"Error in list_documents_paginated: {e}")
            return {
                "documents": [],
                "pagination": {
                    "page": 1,
                    "per_page": per_page,
                    "total": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }
    
    async def delete_document(self, file_id: str) -> Dict[str, Any]:
        """Delete document from knowledge base"""
        if file_id not in self.document_metadata:
            return {"success": False, "message": "Document not found"}
        
        try:
            # Remove from vector database - check if method exists first
            if hasattr(self.vector_indexer, 'remove_document_chunks'):
                await asyncio.to_thread(
                    self.vector_indexer.remove_document_chunks,
                    file_id
                )
            else:
                print(f"⚠️ Vector indexer does not have remove_document_chunks method")
            
            # Remove file
            metadata = self.document_metadata[file_id]
            if os.path.exists(metadata["file_path"]):
                os.remove(metadata["file_path"])
            
            # Remove metadata
            del self.document_metadata[file_id]
            
            # Save updated metadata to persistent storage
            self._save_document_metadata()
            
            return {"success": True, "message": "Document deleted successfully"}
        except Exception as e:
            return {"success": False, "message": f"Delete failed: {str(e)}"}
    
    async def delete_all_documents(self) -> Dict[str, Any]:
        """Delete all documents from knowledge base"""
        try:
            if not self.document_metadata:
                return {"success": True, "message": "No documents to delete", "deleted_count": 0}
            
            # Count documents before deletion
            document_count = len(self.document_metadata)
            
            # Delete all files
            for file_id, metadata in list(self.document_metadata.items()):
                try:
                    # Remove file if it exists
                    if os.path.exists(metadata["file_path"]):
                        os.remove(metadata["file_path"])
                except Exception as e:
                    print(f"⚠️ Failed to remove file {metadata['file_path']}: {e}")
            
            # Clear all metadata
            self.document_metadata.clear()
            
            # Save empty metadata to persistent storage
            self._save_document_metadata()
            
            print(f"🗑️ Deleted all {document_count} documents from knowledge base")
            return {"success": True, "message": f"Successfully deleted all {document_count} documents", "deleted_count": document_count}
            
        except Exception as e:
            return {"success": False, "message": f"Failed to delete all documents: {str(e)}", "deleted_count": 0}
    
    async def generate_workflow(self, query: str, session_id: str, use_knowledge_base: bool = True) -> Dict[str, Any]:
        """Generate workflow using RAG pipeline"""
        try:
            start_time = datetime.now()
            
            # Process query
            query_analysis = self.query_processor.analyze_query(query)
            
            # Retrieve relevant context
            context = await asyncio.to_thread(
                self.retriever.retrieve_context,
                query_analysis
            )
            
            # Generate workflow
            workflow_result = await asyncio.to_thread(
                self.workflow_generator.generate_workflow,
                query,
                context if use_knowledge_base else {}
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "workflow": workflow_result.get("workflow", {}),
                "confidence": workflow_result.get("confidence", 0.0),
                "retrieved_docs": context.get("retrieved_documents", []),
                "processing_time": processing_time
            }
            
        except Exception as e:
            return {
                "workflow": {},
                "error": str(e),
                "confidence": 0.0,
                "retrieved_docs": [],
                "processing_time": 0.0
            }
    
    async def generate_workflow_stream(self, query: str, session_id: str) -> AsyncGenerator[Dict, None]:
        """Generate workflow with streaming response"""
        try:
            yield {"type": "progress", "content": "Analyzing query...", "progress": 0.1}
            
            # Process query
            query_analysis = self.query_processor.analyze_query(query)
            yield {"type": "progress", "content": "Retrieving context...", "progress": 0.3}
            
            # Retrieve context
            context = await asyncio.to_thread(
                self.retriever.retrieve_context,
                query_analysis
            )
            yield {"type": "progress", "content": "Generating workflow...", "progress": 0.6}
            
            # Generate workflow (this would ideally be streaming from Ollama)
            workflow_result = await asyncio.to_thread(
                self.workflow_generator.generate_workflow,
                query,
                context
            )
            
            logger.debug(f"🔍 Workflow result: {workflow_result}")
            logger.debug(f"🔍 Workflow success: {workflow_result.get('success', False) if workflow_result else 'None'}")
            logger.debug(f"🔍 Workflow content: {type(workflow_result.get('workflow', {}) if workflow_result else 'None')}")
            
            yield {"type": "progress", "content": "Finalizing...", "progress": 0.9}
            
            # Ensure we have a valid workflow result
            if not workflow_result or not workflow_result.get("success", False):
                yield {
                    "type": "error", 
                    "content": f"Workflow generation failed: {workflow_result.get('error', 'Unknown error') if workflow_result else 'No result returned'}"
                }
                return
                
            # Final result
            yield {
                "type": "complete",
                "content": workflow_result.get("workflow", {}),
                "metadata": {
                    "confidence": workflow_result.get("confidence", 0.0),
                    "retrieved_docs": context.get("retrieved_documents", [])
                }
            }
            
        except Exception as e:
            yield {"type": "error", "content": str(e)}
    
    async def get_templates(self) -> List[Dict]:
        """Get available workflow templates"""
        try:
            templates_dir = Path("../n8n_rag_data/templates")
            templates = []
            
            if templates_dir.exists():
                for template_file in templates_dir.glob("*.json"):
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        templates.append({
                            "id": template_file.stem,
                            "name": template_data.get("name", template_file.stem),
                            "description": template_data.get("description", ""),
                            "category": template_data.get("category", "general"),
                            "tags": template_data.get("tags", []),
                            "workflow": template_data
                        })
            
            return templates
        except Exception as e:
            return []
    
    async def submit_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Submit feedback for workflow generation"""
        try:
            await asyncio.to_thread(
                self.feedback_loop.record_generation_result,
                feedback
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_chat_history(self, session_id: str) -> List[Dict]:
        """Get chat history for session"""
        # This would integrate with a chat history storage system
        return self.active_sessions.get(session_id, {}).get("history", [])