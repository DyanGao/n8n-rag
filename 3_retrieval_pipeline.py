"""
Phase 3: Advanced Retrieval Pipeline for n8n RAG System
Intelligent query processing and context assembly for LLM generation
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer

class WorkflowIntent(Enum):
    """Types of workflow intents"""
    WEBHOOK_TRIGGER = "webhook_trigger"
    API_INTEGRATION = "api_integration"
    DATA_TRANSFORMATION = "data_transformation"
    DATABASE_OPERATION = "database_operation"
    AI_AUTOMATION = "ai_automation"
    NOTIFICATION = "notification"
    FILE_PROCESSING = "file_processing"
    SCHEDULING = "scheduling"
    ERROR_HANDLING = "error_handling"
    MULTI_STEP_WORKFLOW = "multi_step_workflow"

@dataclass
class QueryAnalysis:
    """Analysis of user query"""
    original_query: str
    cleaned_query: str
    intent: WorkflowIntent
    entities: Dict[str, List[str]]
    required_nodes: List[str]
    workflow_complexity: str  
    
class N8nQueryProcessor:
    """Process and analyze user queries for n8n workflows"""
    
    def __init__(self):
        # Keywords for intent detection
        self.intent_keywords = {
            WorkflowIntent.WEBHOOK_TRIGGER: [
                "webhook", "trigger", "receive", "endpoint", "listen", "http post", "incoming"
            ],
            WorkflowIntent.API_INTEGRATION: [
                "api", "rest", "http", "request", "fetch", "get", "post", "external", "service"
            ],
            WorkflowIntent.DATA_TRANSFORMATION: [
                "transform", "convert", "process", "modify", "format", "parse", "extract", "filter"
            ],
            WorkflowIntent.DATABASE_OPERATION: [
                "database", "db", "sql", "postgres", "mysql", "mongodb", "query", "insert", "update"
            ],
            WorkflowIntent.AI_AUTOMATION: [
                "ai", "gpt", "openai", "llm", "artificial intelligence", "ml", "summarize", "summarise", "analyze", "analyse", "generate text", "completion"
            ],
            WorkflowIntent.NOTIFICATION: [
                "notify", "alert", "email", "slack", "discord", "telegram", "send", "message"
            ],
            WorkflowIntent.FILE_PROCESSING: [
                "file", "csv", "excel", "pdf", "upload", "download", "read", "write", "storage"
            ],
            WorkflowIntent.SCHEDULING: [
                "schedule", "cron", "timer", "interval", "daily", "weekly", "periodic", "recurring"
            ],
            WorkflowIntent.ERROR_HANDLING: [
                "error", "retry", "fail", "exception", "handle", "catch", "fallback", "recovery"
            ]
        }
        
        # Node type mappings
        self.intent_to_nodes = {
            WorkflowIntent.WEBHOOK_TRIGGER: ["n8n-nodes-base.webhook"],
            WorkflowIntent.API_INTEGRATION: ["n8n-nodes-base.httpRequest"],
            WorkflowIntent.DATA_TRANSFORMATION: ["n8n-nodes-base.code", "n8n-nodes-base.function", "n8n-nodes-base.itemLists"],
            WorkflowIntent.DATABASE_OPERATION: ["n8n-nodes-base.postgres", "n8n-nodes-base.mysql", "n8n-nodes-base.mongodb"],
            WorkflowIntent.AI_AUTOMATION: ["@n8n/n8n-nodes-langchain.openAi"],
            WorkflowIntent.NOTIFICATION: ["n8n-nodes-base.slack", "n8n-nodes-base.emailSend", "n8n-nodes-base.discord"],
            WorkflowIntent.FILE_PROCESSING: ["n8n-nodes-base.readBinaryFiles", "n8n-nodes-base.spreadsheetFile"],
            WorkflowIntent.SCHEDULING: ["n8n-nodes-base.scheduleTrigger", "n8n-nodes-base.cron"],
            WorkflowIntent.ERROR_HANDLING: ["n8n-nodes-base.errorTrigger", "n8n-nodes-base.stopAndError"]
        }
        
        # Common workflow patterns
        self.workflow_patterns = {
            "webhook_to_slack": ["webhook", "slack"],
            "api_to_database": ["httpRequest", "code", "postgres"],
            "scheduled_report": ["scheduleTrigger", "postgres", "emailSend"],
            "ai_chatbot": ["webhook", "agent", "httpRequest"],
            "data_sync": ["httpRequest", "code", "httpRequest"],
            "error_notification": ["errorTrigger", "slack"]
        }
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze user query to understand workflow requirements"""
        
        # Clean query
        cleaned_query = query.lower().strip()
        
        # Detect intent
        intent = self._detect_intent(cleaned_query)
        
        # Extract entities
        entities = self._extract_entities(cleaned_query)
        
        # Determine required nodes
        required_nodes = self._identify_required_nodes(cleaned_query, intent, entities)
        
        # Assess complexity
        complexity = self._assess_complexity(required_nodes, entities)
        
        return QueryAnalysis(
            original_query=query,
            cleaned_query=cleaned_query,
            intent=intent,
            entities=entities,
            required_nodes=required_nodes,
            workflow_complexity=complexity
        )
    
    def _detect_intent(self, query: str) -> WorkflowIntent:
        """Detect primary intent from query"""
        intent_scores = {}
        
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            # Return intent with highest score
            return max(intent_scores, key=intent_scores.get)
        
        # Default to multi-step if no clear intent
        return WorkflowIntent.MULTI_STEP_WORKFLOW
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query"""
        entities = {
            "triggers": [],
            "actions": [],
            "services": [],
            "data_types": [],
            "conditions": []
        }
        
        # Triggers
        trigger_words = ["when", "on", "trigger", "receive", "schedule", "every"]
        for word in trigger_words:
            if word in query:
                entities["triggers"].append(word)
        
        # Services (common integrations)
        services = ["slack", "email", "discord", "telegram", "google", "github", 
                   "gitlab", "jira", "notion", "airtable", "salesforce", "hubspot"]
        for service in services:
            if service in query:
                entities["services"].append(service)
        
        # Actions
        action_words = ["send", "create", "update", "delete", "fetch", "transform", 
                       "notify", "store", "process", "analyze", "generate"]
        for action in action_words:
            if action in query:
                entities["actions"].append(action)
        
        # Data types
        data_types = ["json", "csv", "xml", "pdf", "image", "file", "data", "message", "email"]
        for dtype in data_types:
            if dtype in query:
                entities["data_types"].append(dtype)
        
        # Conditions
        condition_words = ["if", "when", "filter", "contains", "equals", "greater", "less"]
        for condition in condition_words:
            if condition in query:
                entities["conditions"].append(condition)
        
        return entities
    
    def _identify_required_nodes(
        self, 
        query: str, 
        intent: WorkflowIntent, 
        entities: Dict[str, List[str]]
    ) -> List[str]:
        """Identify required n8n nodes based on analysis"""
        required_nodes = []
        
        # Add nodes based on intent
        if intent in self.intent_to_nodes:
            required_nodes.extend(self.intent_to_nodes[intent])
        
        # Add nodes based on services mentioned
        service_to_node = {
            "slack": "n8n-nodes-base.slack",
            "email": "n8n-nodes-base.emailSend",
            "discord": "n8n-nodes-base.discord",
            "telegram": "n8n-nodes-base.telegram",
            "google": "n8n-nodes-base.googleSheets",
            "github": "n8n-nodes-base.github",
            "postgres": "n8n-nodes-base.postgres",
            "mysql": "n8n-nodes-base.mysql",
            "mongodb": "n8n-nodes-base.mongodb",
            "openai": "@n8n/n8n-nodes-langchain.openAi",
            "gpt": "@n8n/n8n-nodes-langchain.openAi", 
            "chatgpt": "@n8n/n8n-nodes-langchain.chatOpenAi",
            "summarize": "@n8n/n8n-nodes-langchain.openAi",
            "summarise": "@n8n/n8n-nodes-langchain.openAi",
            "analyze": "@n8n/n8n-nodes-langchain.openAi",
            "completion": "@n8n/n8n-nodes-langchain.openAi",
            "ai_agent": "@n8n/n8n-nodes-langchain.chatOpenAi",
            "conversational_ai": "@n8n/n8n-nodes-langchain.chatOpenAi",
            "langchain": "@n8n/n8n-nodes-langchain.chatOpenAi",
            "intelligent_agent": "@n8n/n8n-nodes-langchain.agent",
            "reasoning_agent": "@n8n/n8n-nodes-langchain.agent"
        }
        
        for service in entities.get("services", []):
            if service in service_to_node:
                node = service_to_node[service]
                if node not in required_nodes:
                    required_nodes.append(node)
        
        # Always add code node for complex transformations
        if entities.get("conditions") or "transform" in entities.get("actions", []):
            if "n8n-nodes-base.code" not in required_nodes:
                required_nodes.append("n8n-nodes-base.code")
        
        # Add trigger if needed
        if entities.get("triggers") and not any("Trigger" in node for node in required_nodes):
            if "schedule" in query or "every" in query:
                required_nodes.insert(0, "n8n-nodes-base.scheduleTrigger")
            else:
                required_nodes.insert(0, "n8n-nodes-base.webhook")
        
        return required_nodes
    
    def _assess_complexity(self, required_nodes: List[str], entities: Dict) -> str:
        """Assess workflow complexity"""
        node_count = len(required_nodes)
        has_conditions = bool(entities.get("conditions"))
        service_count = len(entities.get("services", []))
        
        if node_count <= 2 and not has_conditions:
            return "simple"
        elif node_count <= 4 or (node_count <= 3 and has_conditions):
            return "moderate"
        else:
            return "complex"
    
    def expand_query(self, analysis: QueryAnalysis) -> List[str]:
        """Expand query with synonyms and related terms"""
        expanded_queries = [analysis.cleaned_query]
        
        # Add intent-based expansions
        if analysis.intent == WorkflowIntent.WEBHOOK_TRIGGER:
            expanded_queries.append("webhook receiver http endpoint trigger")
        elif analysis.intent == WorkflowIntent.API_INTEGRATION:
            expanded_queries.append("http request api call rest service")
        elif analysis.intent == WorkflowIntent.DATA_TRANSFORMATION:
            expanded_queries.append("transform data javascript code function")
        elif analysis.intent == WorkflowIntent.AI_AUTOMATION:
            expanded_queries.append("ai agent llm automation gpt openai")
        elif analysis.intent == WorkflowIntent.NOTIFICATION:
            expanded_queries.append("send notification message alert")
        
        # Add node-specific queries
        for node in analysis.required_nodes:
            node_name = node.split(".")[-1]
            expanded_queries.append(f"{node_name} node configuration example")
        
        return expanded_queries

class N8nContextAssembler:
    """Assemble context for LLM from retrieved documents"""
    
    def __init__(self, metadata_dir: str = "./n8n_rag_data/metadata"):
        self.metadata_dir = Path(metadata_dir)
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata index"""
        metadata_file = self.metadata_dir / "index.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
    
    def assemble_context(
        self,
        query_analysis: QueryAnalysis,
        retrieved_chunks: Dict[str, List[Dict]],
        max_context_length: int = 4000
    ) -> Dict[str, Any]:
        """Assemble structured context for LLM"""
        
        context = {
            "query": query_analysis.original_query,
            "intent": query_analysis.intent.value,
            "complexity": query_analysis.workflow_complexity,
            "required_nodes": query_analysis.required_nodes,
            "node_documentation": [],
            "workflow_patterns": [],
            "examples": [],
            "validation_rules": [],
            "prompt": ""
        }
        
        # Add node documentation
        for node_type in query_analysis.required_nodes:
            node_docs = self._get_node_documentation(node_type, retrieved_chunks)
            if node_docs:
                context["node_documentation"].append(node_docs)
        
        # Add relevant workflow patterns
        patterns = self._get_workflow_patterns(query_analysis, retrieved_chunks)
        context["workflow_patterns"] = patterns
        
        # Add examples
        examples = self._get_relevant_examples(query_analysis, retrieved_chunks)
        context["examples"] = examples
        
        # Add validation rules
        context["validation_rules"] = self._get_validation_rules(query_analysis.required_nodes)
        
        # Create structured prompt
        context["prompt"] = self._create_structured_prompt(context)
        
        return context
    
    def _get_node_documentation(self, node_type: str, retrieved_chunks: Dict) -> Dict:
        """Get documentation for specific node"""
        node_doc = {
            "node_type": node_type,
            "properties": {},
            "description": "",
            "configuration": {}
        }
        
        # Find relevant chunks
        for chunk in retrieved_chunks.get("nodes", []):
            if node_type in chunk.get("content", ""):
                # Extract relevant information
                node_doc["description"] = chunk.get("content", "")[:500]
                
                # Extract properties if available
                metadata = chunk.get("metadata", {})
                if metadata.get("node_type") == node_type:
                    node_doc["properties"] = metadata
                    break
        
        return node_doc
    
    def _get_workflow_patterns(self, analysis: QueryAnalysis, retrieved_chunks: Dict) -> List[Dict]:
        """Get relevant workflow patterns"""
        patterns = []
        
        # Check templates
        for template in retrieved_chunks.get("templates", []):
            relevance_score = template.get("relevance_score", 0)
            if relevance_score > 0.7:
                patterns.append({
                    "pattern": template.get("metadata", {}).get("template_id", "unknown"),
                    "description": template.get("content", "")[:300],
                    "relevance": relevance_score
                })
        
        return patterns[:3]  # Top 3 patterns
    
    def _get_relevant_examples(self, analysis: QueryAnalysis, retrieved_chunks: Dict) -> List[Dict]:
        """Get relevant examples"""
        examples = []
        
        # Get task configurations
        for task in retrieved_chunks.get("tasks", []):
            if task.get("relevance_score", 0) > 0.6:
                examples.append({
                    "type": "task_configuration",
                    "content": task.get("content", "")[:400]
                })
        
        return examples[:2]  # Top 2 examples
    
    def _get_validation_rules(self, required_nodes: List[str]) -> List[str]:
        """Get validation rules for workflow"""
        rules = [
            "Workflow must have at least one trigger node",
            "All node connections must be valid",
            "Node IDs must be unique",
            "Position arrays must have [x, y] coordinates"
        ]
        
        # Add node-specific rules
        if any("Trigger" in node for node in required_nodes):
            rules.append("Only one trigger node per workflow")
        
        if "nodes-base.webhook" in required_nodes:
            rules.append("Webhook must have httpMethod and path parameters")
        
        if "nodes-base.code" in required_nodes:
            rules.append("Code node must have valid JavaScript in jsCode parameter")
        
        return rules
    
    def _create_structured_prompt(self, context: Dict) -> str:
        """Create structured prompt for LLM"""
        prompt = f"""Generate an n8n workflow JSON for the following request:

USER REQUEST: {context['query']}

WORKFLOW REQUIREMENTS:
- Intent: {context['intent']}
- Complexity: {context['complexity']}
- Required Nodes: {', '.join(context['required_nodes'])}

NODE DOCUMENTATION:
"""
        
        for node_doc in context['node_documentation']:
            prompt += f"\n{node_doc['node_type']}:\n{node_doc['description']}\n"
        
        if context['workflow_patterns']:
            prompt += "\nRELEVANT PATTERNS:\n"
            for pattern in context['workflow_patterns']:
                prompt += f"- {pattern['description']}\n"
        
        if context['examples']:
            prompt += "\nEXAMPLES:\n"
            for example in context['examples']:
                prompt += f"{example['content']}\n"
        
        prompt += f"""
VALIDATION RULES:
{chr(10).join('- ' + rule for rule in context['validation_rules'])}

INSTRUCTIONS:
1. Create a complete n8n workflow JSON
2. Include all required nodes with proper configuration
3. Set up correct connections between nodes
4. Use appropriate node IDs and positions
5. Ensure the workflow follows n8n JSON schema

Generate the workflow JSON:
"""
        
        return prompt

class AdvancedN8nRetriever:
    """Advanced retrieval system with query processing and context assembly"""
    
    def __init__(
        self,
        db_dir: str = "./n8n_vector_db",
        data_dir: str = "./n8n_rag_data"
    ):
        self.db_dir = Path(db_dir)
        self.data_dir = Path(data_dir)
        
        # Initialize components
        self.query_processor = N8nQueryProcessor()
        self.context_assembler = N8nContextAssembler(str(self.data_dir / "metadata"))
        
        # Initialize embedding model
        print("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Connect to ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=str(self.db_dir))
        self._load_collections()
    
    def _load_collections(self):
        """Load ChromaDB collections"""
        self.collections = {}
        collection_names = ["n8n_nodes", "n8n_templates", "n8n_tasks", "n8n_connections"]
        
        for name in collection_names:
            try:
                self.collections[name] = self.chroma_client.get_collection(name)
            except:
                print(f"⚠️ Collection {name} not found")
    
    def retrieve_for_generation(
        self,
        query: str,
        k_per_stage: int = 5,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Complete retrieval pipeline for workflow generation
        """
        if verbose:
            print(f"\n🔍 Processing query: {query}")
        
        # Step 1: Analyze query
        analysis = self.query_processor.analyze_query(query)
        
        if verbose:
            print(f"📊 Analysis:")
            print(f"  - Intent: {analysis.intent.value}")
            print(f"  - Complexity: {analysis.workflow_complexity}")
            print(f"  - Required nodes: {analysis.required_nodes}")
        
        # Step 2: Expand query
        expanded_queries = self.query_processor.expand_query(analysis)
        
        # Step 3: Multi-stage retrieval
        retrieved_chunks = self._multi_stage_retrieval(
            expanded_queries,
            analysis,
            k_per_stage
        )
        
        if verbose:
            print(f"📚 Retrieved:")
            for key, chunks in retrieved_chunks.items():
                print(f"  - {key}: {len(chunks)} chunks")
        
        # Step 4: Assemble context
        context = self.context_assembler.assemble_context(
            analysis,
            retrieved_chunks
        )
        
        if verbose:
            print(f"📝 Context assembled:")
            print(f"  - Node docs: {len(context['node_documentation'])}")
            print(f"  - Patterns: {len(context['workflow_patterns'])}")
            print(f"  - Examples: {len(context['examples'])}")
            print(f"  - Prompt length: {len(context['prompt'])} chars")
        
        return context
    
    def _multi_stage_retrieval(
        self,
        queries: List[str],
        analysis: QueryAnalysis,
        k_per_stage: int
    ) -> Dict[str, List[Dict]]:
        """Enhanced multi-stage retrieval"""
        
        results = {
            "nodes": [],
            "templates": [],
            "tasks": [],
            "connections": []
        }
        
        # Create embeddings for all queries
        query_embeddings = self.embedding_model.encode(queries)
        
        # Stage 1: Node retrieval (prioritize required nodes)
        if "n8n_nodes" in self.collections:
            node_results = []
            for embedding in query_embeddings[:2]:  # Use first 2 expanded queries
                res = self.collections["n8n_nodes"].query(
                    query_embeddings=[embedding.tolist()],
                    n_results=k_per_stage
                )
                node_results.extend(self._format_results(res))
            
            # Deduplicate and sort by relevance
            seen = set()
            for result in sorted(node_results, key=lambda x: x['relevance_score'], reverse=True):
                content_hash = hash(result['content'][:100])
                if content_hash not in seen:
                    seen.add(content_hash)
                    results["nodes"].append(result)
                    if len(results["nodes"]) >= k_per_stage:
                        break
        
        # Stage 2: Template retrieval
        if "n8n_templates" in self.collections:
            template_res = self.collections["n8n_templates"].query(
                query_embeddings=[query_embeddings[0].tolist()],
                n_results=min(k_per_stage, 3)
            )
            results["templates"] = self._format_results(template_res)
        
        # Stage 3: Task retrieval
        if "n8n_tasks" in self.collections:
            task_res = self.collections["n8n_tasks"].query(
                query_embeddings=[query_embeddings[0].tolist()],
                n_results=min(k_per_stage, 3)
            )
            results["tasks"] = self._format_results(task_res)
        
        # Stage 4: Connection patterns
        if "n8n_connections" in self.collections:
            conn_res = self.collections["n8n_connections"].query(
                query_embeddings=[query_embeddings[0].tolist()],
                n_results=min(k_per_stage, 2)
            )
            results["connections"] = self._format_results(conn_res)
        
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
                    "relevance_score": 1 - (distance / 2)  # Normalize to 0-1
                })
        
        return formatted
    
    def retrieve_context(self, query_analysis):
        """Main retrieval method called by RAG service"""
        try:
            # Use the existing retrieve_for_generation method
            context = self.retrieve_for_generation(
                query_analysis.original_query,
                k_per_stage=5,
                verbose=False
            )
            
            # Format for RAG service compatibility
            return {
                "retrieved_documents": [
                    doc.get("content", "") for doc in 
                    context.get("node_documentation", []) + 
                    context.get("workflow_patterns", []) + 
                    context.get("examples", [])
                ],
                "confidence": 0.8,  # Default confidence
                "node_documentation": context.get("node_documentation", []),
                "workflow_patterns": context.get("workflow_patterns", []),
                "examples": context.get("examples", []),
                "prompt": context.get("prompt", "")
            }
        except Exception as e:
            print(f"⚠️ Retrieval failed: {e}")
            return {
                "retrieved_documents": [],
                "confidence": 0.0,
                "node_documentation": [],
                "workflow_patterns": [],
                "examples": [],
                "prompt": ""
            }

def test_retrieval_pipeline():
    """Test the advanced retrieval pipeline"""
    retriever = AdvancedN8nRetriever()
    
    test_queries = [
        "create a webhook that receives data and sends a slack notification",
        "fetch data from an API every hour and store in postgres database",
        "build an AI chatbot that responds to webhooks",
        "transform CSV data and send email with results"
    ]
    
    for query in test_queries:
        print("\n" + "="*60)
        context = retriever.retrieve_for_generation(query, verbose=True)
        print("\n📋 Generated Prompt Preview:")
        print(context["prompt"][:500] + "...")
        print("="*60)

if __name__ == "__main__":
    test_retrieval_pipeline()
