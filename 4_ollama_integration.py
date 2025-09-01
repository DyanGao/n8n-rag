"""
Phase 4: Ollama Integration for n8n Workflow Generation
Works without the full RAG pipeline for basic workflow generation
"""

import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re
import time

# Vector DB imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

class OllamaWorkflowGenerator:
    """Generate n8n workflows using Ollama"""
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model_name: str = "deepseek-r1:14b",  
        temperature: float = 0.1,
        max_tokens: int = 4096
    ):
        self.ollama_host = ollama_host
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Test connection and auto-detect available models
        self._test_connection()
        
        # Initialize vector database connection
        self.vector_client = None
        if CHROMADB_AVAILABLE:
            try:
                self.vector_client = chromadb.PersistentClient(
                    path="n8n_vector_db",
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )
            except Exception as e:
                print(f"⚠️ Vector database not available: {e}")
                self.vector_client = None
    
    def _test_connection(self):
        """Test Ollama connection and auto-detect models"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                if self.model_name in model_names:
                    print(f"✅ Connected to Ollama with {self.model_name}")
                elif model_names:
                    print(f"⚠️ Model {self.model_name} not found.")
                    print(f"   Available models: {', '.join(model_names[:5])}")
                    
                    # Auto-select a good model
                    preferred_models = ["deepseek-r1:14b", "llama3.2:latest", "llama3.2", "llama3:latest", "llama3", "qwen2.5:latest"]
                    for preferred in preferred_models:
                        if preferred in model_names:
                            self.model_name = preferred
                            print(f"   Auto-selected: {self.model_name}")
                            break
                    else:
                        # Use first available
                        self.model_name = model_names[0]
                        print(f"   Using first available: {self.model_name}")
                else:
                    print(f"⚠️ No models found in Ollama.")
                    print("   Please pull a model first: ollama pull llama3.2:latest")
            else:
                print(f"❌ Failed to connect to Ollama (status: {response.status_code})")
        except requests.exceptions.ConnectionError:
            print(f"❌ Ollama not running at {self.ollama_host}")
            print("   Please start Ollama with: ollama serve")
        except Exception as e:
            print(f"❌ Ollama connection error: {e}")
    
    def get_relevant_context(self, query: str, n_results: int = 10) -> Dict[str, Any]:
        """Get relevant context from vector database with service-aware ranking"""
        context = {"retrieved_documents": [], "node_types": {}}
        
        if not self.vector_client:
            return context
        
        try:
            # Detect explicit service mentions in query
            service_mentions = self._detect_service_mentions(query.lower())
            
            # Query the n8n_nodes collection for relevant context
            collection = self.vector_client.get_collection(name="n8n_nodes")
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results * 2,  # Get more results for ranking
                include=['documents', 'metadatas', 'distances']
            )
            
            # Rank results with service-aware scoring
            scored_results = self._rank_results_by_service_relevance(
                results, service_mentions, query.lower()
            )
            
            # Take top n_results after ranking
            scored_results = scored_results[:n_results]
            
            # Extract node types and context
            node_types = {}
            for result_data in scored_results:
                doc = result_data['document']
                metadata = result_data['metadata']
                
                # Extract node type information with priority
                if metadata:
                    node_type = metadata.get('node_type', '')
                    
                    # Enhanced service extraction
                    if node_type:
                        service_key = self._extract_service_key(node_type, service_mentions)
                        if service_key:
                            # Prioritize explicitly mentioned services
                            if service_key in service_mentions:
                                node_types[service_key] = node_type
                            elif service_key not in node_types:
                                node_types[service_key] = node_type
                
                # Store document for context
                context["retrieved_documents"].append({
                    "content": doc,
                    "metadata": metadata,
                    "relevance_score": result_data['score']
                })
            
            context["node_types"] = node_types
            context["detected_services"] = service_mentions
            return context
            
        except Exception as e:
            print(f"⚠️ Error retrieving context: {e}")
            return context
    
    def _detect_service_mentions(self, query: str) -> List[str]:
        """Detect explicit service mentions in the query"""
        service_patterns = {
            'gmail': ['gmail', 'google mail', 'gmail account', 'gmail api'],
            'whatsapp': ['whatsapp', 'whats app', 'whatsapp message', 'whatsapp business', 'wa message'],
            'telegram': ['telegram', 'telegram bot', 'telegram message'],
            'slack': ['slack', 'slack channel', 'slack notification'],
            'discord': ['discord', 'discord bot', 'discord message'],
            'reddit': ['reddit', 'reddit post', 'reddit posts', 'reddit subreddit', 'subreddit', 'r/', '/r/', 'reddit data', 'reddit feed', 'reddit api', 'from reddit', 'reddit content'],
            'twitter': ['twitter', 'tweet', 'x.com'],
            'linkedin': ['linkedin', 'linkedin post'],
            'facebook': ['facebook', 'fb'],
            'instagram': ['instagram', 'insta'],
            'youtube': ['youtube', 'youtube video'],
            'postgres': ['postgres', 'postgresql', 'pg'],
            'mysql': ['mysql'],
            'mongodb': ['mongodb', 'mongo'],
            'salesforce': ['salesforce', 'sfdc'],
            'hubspot': ['hubspot'],
            'notion': ['notion'],
            'trello': ['trello'],
            'asana': ['asana'],
            'jira': ['jira'],
            'github': ['github', 'git'],
            'aws': ['aws', 'amazon web services'],
            'outlook': ['outlook', 'microsoft outlook', 'office 365'],
            'smtp': ['smtp', 'email server', 'mail server'],
            'webhook': ['webhook', 'http trigger'],
            'openai': ['openai', 'open ai', 'gpt', 'chatgpt', 'summarize', 'summarise', 'ai summary', 'ai analysis', 'ai processing', 'llm', 'language model'],
            'openai_assistant': ['assistant', 'create assistant', 'openai assistant', 'ai assistant']
        }
        
        detected_services = []
        for service, patterns in service_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    detected_services.append(service)
                    break
                    
        return detected_services
    
    def _extract_service_key(self, node_type: str, service_mentions: List[str]) -> str:
        """Extract service key from node type with priority for mentioned services"""
        if not node_type:
            return ""
            
        # Direct mapping for common services
        service_mapping = {
            'gmail': 'gmail',
            'whatsapp': 'whatsapp',  
            'telegram': 'telegram',
            'slack': 'slack',
            'discord': 'discord',
            'reddit': 'reddit',
            'emailsend': 'smtp',  
            'webhook': 'webhook',
            'postgres': 'postgres',
            'mysql': 'mysql',
            'mongodb': 'mongodb',
            'salesforce': 'salesforce',
            'hubspot': 'hubspot',
            'outlook': 'outlook',
            'openai': 'openai',  
            'openai_assistant': 'openai_assistant',  
            'gpt': 'openai'  
        }
        
        node_lower = node_type.lower()
        
        # Check for explicit service mentions first
        for service in service_mentions:
            if service in node_lower:
                return service
                
        # Check mapping
        for key, mapped_service in service_mapping.items():
            if key in node_lower:
                return mapped_service
                
        # Extract from node type pattern
        if '.' in node_type:
            service_name = node_type.split('.')[-1]
        else:
            service_name = node_type
            
        return service_name.lower()
    
    def _rank_results_by_service_relevance(
        self, 
        results: Dict, 
        service_mentions: List[str], 
        query: str
    ) -> List[Dict]:
        """Rank results by service relevance with scoring"""
        if not results['documents'] or not results['documents'][0]:
            return []
            
        scored_results = []
        
        for i in range(len(results['documents'][0])):
            document = results['documents'][0][i]
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            # Base score (lower distance = higher relevance)
            base_score = 1.0 / (1.0 + distance)
            
            # Service mention bonus
            service_bonus = 0.0
            if metadata and metadata.get('node_type'):
                node_type = metadata['node_type'].lower()
                
                # Strong bonus for exact service matches
                for service in service_mentions:
                    if service in node_type:
                        if service == 'gmail' and 'gmail' in node_type:
                            service_bonus += 0.5  # Strong Gmail preference
                        elif service == 'reddit' and 'reddit' in node_type:
                            service_bonus += 0.5  # Strong Reddit preference over httpRequest
                        elif service == 'whatsapp' and 'whatsapp' in node_type:
                            service_bonus += 0.5  # Strong WhatsApp preference
                        elif service == 'openai' and 'openai' in node_type:
                            service_bonus += 0.5  # Strong OpenAI preference for standalone openAI node
                        elif service == 'smtp' and 'emailsend' in node_type:
                            service_bonus += 0.2  # Moderate SMTP preference
                        else:
                            service_bonus += 0.3
                            
                # Penalize generic nodes when specific service is detected
                if service_mentions:
                    if 'reddit' in service_mentions and 'httprequest' in node_type.lower():
                        service_bonus -= 0.3  # Penalize httpRequest when Reddit is mentioned
                    elif 'gmail' in service_mentions and 'emailsend' in node_type.lower():
                        service_bonus -= 0.3  # Penalize emailSend when Gmail is mentioned
                            
                # Content relevance bonus
                if document:
                    doc_lower = document.lower()
                    for service in service_mentions:
                        if service in doc_lower:
                            service_bonus += 0.1
            
            final_score = base_score + service_bonus
            
            scored_results.append({
                'document': document,
                'metadata': metadata,
                'distance': distance,
                'score': final_score,
                'service_bonus': service_bonus
            })
        
        # Sort by final score (highest first)
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        return scored_results
    
    def _get_node_type_version(self, node_type: str) -> float:
        """Get the correct typeVersion for each node type based on n8n 1.108.1"""
        type_versions = {
            # n8n-nodes-base nodes
            "n8n-nodes-base.scheduleTrigger": 1.2,
            "n8n-nodes-base.webhook": 1.1,
            "n8n-nodes-base.httpRequest": 4.2,
            "n8n-nodes-base.code": 2,
            "n8n-nodes-base.emailSend": 2.1,
            "n8n-nodes-base.gmail": 2.1,
            "n8n-nodes-base.slack": 2.1,
            "n8n-nodes-base.reddit": 1,
            "n8n-nodes-base.whatsApp": 1.1,
            "@n8n/n8n-nodes-langchain.openAi": 1,
            "n8n-nodes-base.set": 3.3,
            "n8n-nodes-base.if": 2,
            "n8n-nodes-base.merge": 2.1,
            "n8n-nodes-base.function": 1.1,
            
            # @n8n/n8n-nodes-langchain nodes  
            "@n8n/n8n-nodes-langchain.openAi": 1.8,
            "@n8n/n8n-nodes-langchain.chatOpenAi": 1.8,
            "@n8n/n8n-nodes-langchain.agent": 1.6,
            "@n8n/n8n-nodes-langchain.embeddings": 1.3,
            "@n8n/n8n-nodes-langchain.vectorStore": 1.3,
            "@n8n/n8n-nodes-langchain.documentLoader": 1.2,
            "@n8n/n8n-nodes-langchain.memoryManager": 1.4
        }
        
        return type_versions.get(node_type, 1.0)  
    
    def _fix_workflow_type_versions(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Fix typeVersion for all nodes in the workflow"""
        if "nodes" in workflow:
            for node in workflow["nodes"]:
                if "type" in node:
                    correct_version = self._get_node_type_version(node["type"])
                    node["typeVersion"] = correct_version
        return workflow

    def generate_workflow(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate workflow using RAG context and Ollama"""
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info("🤖 Generating workflow using RAG + LLM...")
        
        # Get relevant context if none provided
        if context is None:
            context = self.get_relevant_context(user_query)
        
        # Fallback to Ollama with timeout
        system_prompt = self._get_system_prompt()
        prompt = self._create_prompt(user_query, context)
        
        # Prepare request - prevent DeepSeek from extensive thinking
        stop_sequences = ["Human:", "Assistant:", "<think>", "</think>"]
        
        # Use effective settings for DeepSeek to get direct JSON output
        if "deepseek" in self.model_name.lower():
            temperature = 0.1  # Small amount of randomness
            
            request_data = {
                "model": self.model_name,
                "prompt": prompt,  
                "system": f"{system_prompt}\n\nIMPORTANT: Respond ONLY with valid n8n workflow JSON. No explanations, no thinking, just the JSON object starting with {{ and ending with }}.",
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "num_predict": 3000,  
                    "stop": ["Human:", "User:", "\n\n---", "```", "\n\nUser:", "\n\nHuman:"],
                    "top_p": 0.9,  
                    "repeat_penalty": 1.1,
                    "num_ctx": 8192,  
                    "seed": 42
                }
            }
        else:
            temperature = self.temperature
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "num_predict": 1024,
                    "stop": stop_sequences + ["\n\nHuman:", "\n\n---", "```\n\n"],
                    "top_p": 0.1,
                    "repeat_penalty": 1.2,
                    "top_k": 40,
                    "num_ctx": 1024
                }
            }
        
        if stream:
            return self._generate_streaming(request_data)
        else:
            return self._generate_complete(request_data)
    
    def _get_system_prompt(self) -> str:
        if "deepseek" in self.model_name.lower():
            return """You are an n8n workflow generator. Your response must be ONLY valid JSON - nothing else.

CRITICAL REQUIREMENTS:
- First character must be { 
- Last character must be }
- NO explanations before or after JSON
- Generate complete n8n workflow with nodes, connections, and proper UUIDs
- NEVER use cronExpression, cron, or old scheduling formats
- ALWAYS use rule.interval structure for Schedule Triggers
- For OpenAI chat operations use @n8n/n8n-nodes-langchain.chatOpenAi
- For ALL OpenAI operations use @n8n/n8n-nodes-langchain.openAi ONLY

VALID N8N NODE TYPES (use these exactly):
- n8n-nodes-base.webhook (for receiving HTTP requests)
- n8n-nodes-base.scheduleTrigger (for cron/schedule)
- n8n-nodes-base.httpRequest (for API calls)
- n8n-nodes-base.reddit (for Reddit posts)
- n8n-nodes-base.slack (for Slack messages)
- n8n-nodes-base.emailSend (for sending emails)
- n8n-nodes-base.gmail (for Gmail operations)
- n8n-nodes-base.code (for JavaScript code)
- n8n-nodes-base.set (for setting data)
- n8n-nodes-base.if (for conditions)
- @n8n/n8n-nodes-langchain.openAi (for ALL OpenAI operations)


REDDIT NODE PARAMETERS (MANDATORY format):
{
  "parameters": {
    "resource": "post",
    "operation": "getAll",
    "subreddit": "n8n",
    "sort": "new",
    "limit": 10
  }
}

OPENAI ASSISTANT NODE PARAMETERS (MANDATORY format):
{
  "parameters": {
    "resource": "assistant",
    "operation": "create",
    "modelId": {
      "__rl": true,
      "mode": "list",
      "value": ""
    },
    "options": {}
  },
  "type": "@n8n/n8n-nodes-langchain.openAi",
  "credentials": {
    "openAiApi": {
      "id": "credential_id",
      "name": "OpenAi account"
    }
  }
}

MANDATORY SCHEDULE TRIGGER FORMAT (NEVER use cronExpression):
{
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "weeks",
          "triggerAtDay": [1],
          "triggerAtHour": 7,
          "triggerAtMinute": 0
        }
      ]
    }
  },
  "type": "n8n-nodes-base.scheduleTrigger"
}

WORKFLOW STRUCTURE:
{
  "name": "Workflow Name",
  "nodes": [
    {
      "parameters": {},
      "id": "uuid-string",
      "name": "Node Name",
      "type": "n8n-nodes-base.nodetype", 
      "typeVersion": "varies_by_node",
      "position": [x, y]
    }
  ],
  "connections": {
    "Node Name": {
      "main": [[{"node": "Next Node", "type": "main", "index": 0}]]
    }
  }
}"""
        else:
            return """You are an expert n8n workflow generator. Generate ONLY valid JSON.

CRITICAL: 
- Start response with { immediately - NO thinking, NO text before JSON  
- Create working n8n workflows with proper connections
- Use real node types and parameters
- NEVER use cronExpression - ALWAYS use rule.interval for Schedule Triggers
- Schedule format: {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 7}]}}
- Reddit format: {"resource": "post", "operation": "getAll", "subreddit": "name", "sort": "new", "limit": 10}"""

    def _get_workflow_patterns(self):
        return """WORKFLOW PATTERNS:

Pattern 1: SCHEDULED TASKS
Request keywords: daily, hourly, every, schedule, periodic, cron, recurring
Structure: scheduleTrigger -> action nodes -> output
Example: "daily report" = scheduleTrigger -> httpRequest/database -> emailSend

SCHEDULE TRIGGER PARAMETERS:
Use rule.interval array format (NOT cron expressions):

FORBIDDEN: Do NOT use: cronExpression, cron, or any cron-style formats

REQUIRED Schedule Trigger Parameters:
Daily 9 AM: {
  "rule": {
    "interval": [{"field": "days", "triggerAtHour": 9, "triggerAtMinute": 0}]
  }
}

Weekly Monday 8 AM: {
  "rule": {
    "interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 8, "triggerAtMinute": 0}]
  }
}

Weekly Sunday 7 AM: {
  "rule": {
    "interval": [{"field": "weeks", "triggerAtDay": [0], "triggerAtHour": 7, "triggerAtMinute": 0}]
  }
}
(triggerAtDay: [0]=Sunday, [1]=Monday, [2]=Tuesday, etc.)

Hourly: {
  "rule": {
    "interval": [{"field": "hours", "hoursInterval": 2}]
  }
}

Minutes: {
  "rule": {
    "interval": [{"field": "minutes", "minutesInterval": 30}]
  }
}

Pattern 2: WEBHOOK/API ENDPOINTS  
Request keywords: webhook, endpoint, receive, API, POST, GET
Structure: webhook -> process -> respond/store
Example: "receive data" = webhook -> code/transform -> database/response

Pattern 3: DATA PROCESSING
Request keywords: transform, convert, process, filter, modify
Structure: trigger -> fetch -> code/function -> output
Example: "process CSV" = trigger -> readFile -> code -> writeFile

Pattern 4: INTEGRATIONS  
Request keywords: send to, post to, notify, alert, sync
Structure: trigger -> fetch/process -> integration node
Example: "send to Slack" = trigger -> process -> slack

Pattern 6: REDDIT WORKFLOWS
Request keywords: reddit, subreddit, r/, reddit posts, fetch reddit
Structure: trigger -> reddit -> process -> output
Reddit parameters MUST include: resource, operation, subreddit, sort, limit
Example: "fetch reddit posts" = scheduleTrigger -> reddit(resource: post, operation: getAll) -> process -> notify

Pattern 5: AI/AUTOMATION
Request keywords: AI, GPT, automate, intelligent, analyze
Structure: trigger -> data -> openAi/agent -> output
Example: "AI analysis" = trigger -> httpRequest -> openAi -> output

COMMON NODE TYPES:

TRIGGERS (start workflows):
- n8n-nodes-base.scheduleTrigger - for scheduled/periodic tasks
- n8n-nodes-base.webhook - for receiving external data
- n8n-nodes-base.emailReadImap - for email triggers
- n8n-nodes-base.rssFeedRead - for RSS feeds
- n8n-nodes-base.githubTrigger - for GitHub events

DATA SOURCES:
- n8n-nodes-base.httpRequest - for API calls (GET/POST/PUT/DELETE)
- n8n-nodes-base.postgres - for PostgreSQL queries
- n8n-nodes-base.mysql - for MySQL queries
- n8n-nodes-base.mongodb - for MongoDB operations
- n8n-nodes-base.googleSheets - for spreadsheet data
- n8n-nodes-base.readBinaryFiles - for file reading

PROCESSING:
- n8n-nodes-base.code - for JavaScript transformations
- n8n-nodes-base.function - for data manipulation
- n8n-nodes-base.if - for conditional logic
- n8n-nodes-base.switch - for multiple conditions
- n8n-nodes-base.merge - for combining data
- n8n-nodes-base.itemLists - for list operations
- n8n-nodes-base.set - for setting values

OUTPUTS:
- n8n-nodes-base.telegram - for Telegram messages
- n8n-nodes-base.slack - for Slack notifications
- n8n-nodes-base.discord - for Discord messages
- n8n-nodes-base.emailSend - for sending emails
- n8n-nodes-base.writeBinaryFile - for file writing
- n8n-nodes-base.respondToWebhook - for webhook responses

AI/ML:
- @n8n/n8n-nodes-langchain.openAi - for ALL OpenAI operations (chat, assistant, etc.)

CONNECTION RULES:
1. Each node connects to the next in sequence
2. Trigger nodes start the flow
3. Use this exact structure:

"connections": {
  "first_node_id": {
    "main": [[{"node": "second_node_id", "type": "main", "index": 0}]]
  },
  "second_node_id": {
    "main": [[{"node": "third_node_id", "type": "main", "index": 0}]]
  }
}

PARAMETER EXAMPLES:

scheduleTrigger (daily at specific time):
"parameters": {
  "rule": {
    "interval": [{"field": "hours", "hoursInterval": 7}]
  }
}

scheduleTrigger (every N minutes):
"parameters": {
  "rule": {
    "interval": [{"field": "minutes", "minutesInterval": 30}]
  }
}

webhook:
"parameters": {
  "httpMethod": "POST",
  "path": "webhook-endpoint"
}

httpRequest (GET):
"parameters": {
  "method": "GET",
  "url": "https://api.example.com/data"
}

httpRequest (POST with auth):
"parameters": {
  "method": "POST",
  "url": "https://api.example.com/create",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {"name": "key", "value": "value"}
    ]
  }
}

telegram:
"parameters": {
  "operation": "sendMessage",
  "chatId": "CHAT_ID",
  "text": "={{$json.message}}"
}

slack:
"parameters": {
  "operation": "post",
  "channel": "#general",
  "text": "Notification text"
}

emailSend:
"parameters": {
  "toEmail": "recipient@example.com",
  "subject": "Subject",
  "text": "Email body",
  "fromEmail": "sender@example.com"
}

openAi (ALL OpenAI operations - use @n8n/n8n-nodes-langchain.openAi ONLY):
For Chat/Summarization:
"parameters": {
  "operation": "message",
  "model": "gpt-3.5-turbo",
  "messages": {
    "messageType": "multipleMessages",
    "values": [
      {"role": "system", "content": "You are a helpful assistant"},
      {"role": "user", "content": "{{ $json.input }}"}
    ]
  }
}

For Assistant Creation:
"parameters": {
  "resource": "assistant",
  "operation": "create",
  "modelId": {
    "__rl": true,
    "mode": "list",
    "value": ""
  }
}

code (transform data):
"parameters": {
  "jsCode": "return items.map(item => ({json: {result: item.json.value * 2}}))"
}

postgres:
"parameters": {
  "operation": "executeQuery",
  "query": "SELECT * FROM table WHERE condition = true"
}

COMPLETE WORKFLOW STRUCTURE:
{
  "name": "Descriptive Workflow Name",
  "nodes": [
    {
      "id": "unique_id_1",
      "name": "Human Readable Name",
      "type": "n8n-nodes-base.nodeType",
      "typeVersion": 1,
      "position": [250, 300],
      "parameters": {...}
    },
    {
      "id": "unique_id_2",
      "name": "Next Step Name",
      "type": "n8n-nodes-base.nodeType",
      "typeVersion": 1,
      "position": [450, 300],
      "parameters": {...}
    }
  ],
  "connections": {
    "unique_id_1": {
      "main": [[{"node": "unique_id_2", "type": "main", "index": 0}]]
    }
  },
  "settings": {
    "executionOrder": "v1"
  }
}

DECISION LOGIC:
- If "daily" or "schedule" -> use scheduleTrigger
- If "webhook" or "receive" -> use webhook
- If "API" or "fetch" -> use httpRequest
- If "transform" or "process" -> use code
- If "Slack" -> use slack
- If "Telegram" -> use telegram
- If "email" -> use emailSend
- If "database" or "SQL" -> use postgres/mysql
- If "AI" or "GPT" -> use openAi
- If "if" or "condition" -> use if
- If "merge" or "combine" -> use merge

CRITICAL: 
- For Telegram messaging use ONLY "n8n-nodes-base.telegram" 
- NEVER use "telegramSendMessage" or similar made-up types

ALWAYS:
1. Start with appropriate trigger
2. Connect nodes sequentially
3. End with appropriate output
4. Use descriptive node names
5. Position nodes left-to-right: [250,300], [450,300], [650,300], [850,300]

OUTPUT ONLY VALID JSON - NO EXPLANATIONS."""
    
    def _create_prompt(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Create enhanced prompt with pattern detection and RAG context"""
        import json
    
        query_lower = user_query.lower()
    
        # Detect workflow pattern
        pattern_hints = []
    
        # Enhanced scheduling patterns with comprehensive time extraction
        if any(word in query_lower for word in ['daily', 'weekly', 'monthly', 'hourly', 'schedule', 'every', 'periodic', 'cron', 'recurring', 'am', 'pm', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            pattern_hints.append("PATTERN: Scheduled workflow - use n8n-nodes-base.scheduleTrigger as first node")
            
            # Extract specific times and frequencies
            import re
            time_pattern = r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)'
            time_match = re.search(time_pattern, query_lower)
            
            # Default values
            hour = 9
            minute = 0
            day_of_week = None
            
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                period = time_match.group(3).lower()
                
                # Convert to 24-hour format
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
            
            # Detect day of week for weekly schedules
            day_mapping = {
                'sunday': 0, 'monday': 1, 'tuesday': 2, 'wednesday': 3,
                'thursday': 4, 'friday': 5, 'saturday': 6
            }
            
            for day_name, day_num in day_mapping.items():
                if day_name in query_lower:
                    day_of_week = day_num
                    break
            
            # Generate appropriate cron expression
            if 'weekly' in query_lower or day_of_week is not None:
                if day_of_week is None:
                    day_of_week = 1  # Default to Monday
                pattern_hints.append(f"SCHEDULE: Weekly on {list(day_mapping.keys())[day_of_week]} at {hour:02d}:{minute:02d} - use cron: '{minute} {hour} * * {day_of_week}'")
            elif 'monthly' in query_lower:
                pattern_hints.append(f"SCHEDULE: Monthly at {hour:02d}:{minute:02d} - use cron: '{minute} {hour} 1 * *'")
            elif 'hourly' in query_lower:
                pattern_hints.append(f"SCHEDULE: Hourly - use cron: '0 * * * *'")
            elif 'daily' in query_lower or time_match:
                pattern_hints.append(f"SCHEDULE: Daily at {hour:02d}:{minute:02d} - use cron: '{minute} {hour} * * *'")
            else:
                pattern_hints.append("SCHEDULE: Scheduled execution - use appropriate cron expression")
        
        # Webhook patterns
        if any(word in query_lower for word in ['webhook', 'endpoint', 'receive', 'listen', 'incoming']):
            pattern_hints.append("PATTERN: Webhook receiver - use n8n-nodes-base.webhook as first node")
    
        # API patterns - but check for specific services first
        if any(word in query_lower for word in ['api', 'fetch', 'get', 'post', 'rest', 'http']):
            # Only suggest httpRequest if no specific service is mentioned
            specific_services = ['reddit', 'gmail', 'slack', 'telegram', 'notion', 'trello', 'asana', 'github']
            has_specific_service = any(service in query_lower for service in specific_services)
            if not has_specific_service:
                pattern_hints.append("ACTION: Generic API call - use n8n-nodes-base.httpRequest node")
    
        # Service-specific patterns with smart detection
        if 'notion' in query_lower:
            pattern_hints.append("SERVICE: Notion - use n8n-nodes-base.notion node")
        if 'slack' in query_lower:
            pattern_hints.append("SERVICE: Slack - use n8n-nodes-base.slack node")
        
        # Smart email detection
        if 'gmail' in query_lower:
            pattern_hints.append("SERVICE: Gmail - use n8n-nodes-base.gmail node (NOT emailSend)")
        elif 'outlook' in query_lower:
            pattern_hints.append("SERVICE: Outlook - use n8n-nodes-base.outlook node")
        elif any(word in query_lower for word in ['smtp', 'email server', 'mail server']):
            pattern_hints.append("SERVICE: SMTP Email - use n8n-nodes-base.emailSend node")
        elif 'email' in query_lower:
            # Generic email - check context for specific service
            if context and context.get('detected_services'):
                if 'gmail' in context['detected_services']:
                    pattern_hints.append("SERVICE: Gmail detected - use n8n-nodes-base.gmail node")
                elif 'outlook' in context['detected_services']:
                    pattern_hints.append("SERVICE: Outlook detected - use n8n-nodes-base.outlook node")
                else:
                    pattern_hints.append("SERVICE: Generic Email - use n8n-nodes-base.emailSend node")
            else:
                pattern_hints.append("SERVICE: Generic Email - use n8n-nodes-base.emailSend node")
        
        # Smart Reddit detection  
        if any(reddit_term in query_lower for reddit_term in ['reddit', 'r/', '/r/', 'subreddit']):
            pattern_hints.append("SERVICE: Reddit - use n8n-nodes-base.reddit node (NOT httpRequest)")
            pattern_hints.append("REDDIT: For subreddits like 'r/n8n', use subreddit parameter without 'r/' prefix")
        
        # Smart AI/OpenAI detection - ALWAYS use standalone openAi node
        if any(ai_term in query_lower for ai_term in ['assistant', 'create assistant', 'openai assistant', 'ai assistant', 'summarize', 'summarise', 'ai summary', 'gpt', 'chatgpt', 'ai analysis', 'ai processing', 'llm', 'openai']):
            pattern_hints.append("SERVICE: OpenAI - use @n8n/n8n-nodes-langchain.openAi node ONLY (standalone node)")
            pattern_hints.append("SERVICE: OpenAI Chat - use @n8n/n8n-nodes-langchain.chatOpenAi for conversational operations")
            pattern_hints.append("AI: For ALL OpenAI operations (chat, assistant, summarization), use the standalone openAi node")
        
        # Generic API detection - but deprioritize if specific service detected
        elif any(word in query_lower for word in ['api', 'fetch', 'get', 'post', 'rest', 'http']):
            if context and context.get('detected_services'):
                if 'reddit' in context['detected_services']:
                    pattern_hints.append("SERVICE: Reddit API detected - use n8n-nodes-base.reddit node")
                else:
                    pattern_hints.append("ACTION: Generic API call - use n8n-nodes-base.httpRequest node")
            else:
                pattern_hints.append("ACTION: Generic API call - use n8n-nodes-base.httpRequest node")
                
        if 'telegram' in query_lower:
            pattern_hints.append("SERVICE: Telegram - use ONLY n8n-nodes-base.telegram node for sending messages")
            pattern_hints.append("SERVICE: Telegram trigger - use n8n-nodes-base.telegramTrigger node for receiving messages")
            pattern_hints.append("CRITICAL: NEVER use telegramSendMessage - this node type does not exist!")
        if any(word in query_lower for word in ['postgres', 'postgresql']):
            pattern_hints.append("SERVICE: PostgreSQL - use n8n-nodes-base.postgres node")
        if 'mysql' in query_lower:
            pattern_hints.append("SERVICE: MySQL - use n8n-nodes-base.mysql node")

        # Processing patterns
        if any(word in query_lower for word in ['transform', 'process', 'convert', 'modify', 'filter']):
            pattern_hints.append("PROCESSING: Data transformation - include code node")

        # AI patterns
        if any(word in query_lower for word in ['ai', 'gpt', 'chatgpt', 'openai', 'intelligent']):
            pattern_hints.append("AI: OpenAI integration - include openAi node")

        hints = "\n".join(pattern_hints) if pattern_hints else "Analyze request and choose appropriate nodes"
        
        # Add comprehensive context information if available
        context_info = ""
        if context:
            # Add detected services with priority
            detected_services = context.get("detected_services", [])
            if detected_services:
                context_info += f"\nDETECTED SERVICES IN QUERY: {', '.join(detected_services)}\n"
                context_info += "PRIORITY: Use node types that match detected services EXACTLY!\n\n"
            
            # Add node type mappings with priority indication
            node_types = context.get("node_types", {})
            if node_types:
                context_info += "AVAILABLE NODE TYPES (prioritized by relevance):\n"
                # Sort by detected services first
                sorted_services = sorted(node_types.items(), 
                                       key=lambda x: x[0] not in detected_services)
                for service, node_type in sorted_services:
                    priority_marker = "⭐ PRIORITY" if service in detected_services else ""
                    context_info += f"  - {service.upper()}: {node_type} {priority_marker}\n"
                context_info += "\n"
            
            # Add documentation context
            if context.get("retrieved_documents"):
                docs = context.get("retrieved_documents", [])[:3]  # Limit to top 3
                context_info += "RELEVANT DOCUMENTATION FROM KNOWLEDGE BASE:\n"
                for i, doc in enumerate(docs, 1):
                    if isinstance(doc, dict):
                        content = doc.get("content", "")
                        metadata = doc.get("metadata", {})
                        node_type = metadata.get("node_type", "")
                        chunk_type = metadata.get("chunk_type", "")
                        
                        if node_type and content:
                            context_info += f"Node {i} ({node_type} - {chunk_type}):\n{content[:300]}...\n\n"
                    else:
                        context_info += f"Doc {i}: {str(doc)[:200]}...\n\n"
                context_info += "USE THIS DOCUMENTATION TO ENSURE CORRECT NODE TYPES AND PARAMETERS.\n"

        return f"""REQUEST: {user_query}

{hints}
{context_info}

EXAMPLE VALID WORKFLOW:
{{
  "name": "Webhook to Slack",
  "nodes": [
    {{
      "parameters": {{"httpMethod": "POST", "path": "/webhook"}},
      "id": "abc-123",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [240, 300]
    }},
    {{
      "parameters": {{"channel": "#general", "text": "{{{{ $json.message }}}}"}},
      "id": "def-456",
      "name": "Slack",
      "type": "n8n-nodes-base.slack", 
      "typeVersion": 1,
      "position": [460, 300]
    }}
  ],
  "connections": {{
    "Webhook": {{"main": [[{{"node": "Slack", "type": "main", "index": 0}}]]}}
  }}
}}

YOUR WORKFLOW JSON (start immediately with opening brace):"""
    
    def _generate_complete(self, request_data: Dict) -> Dict[str, Any]:
        """Generate complete response (non-streaming)"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("🤖 Generating workflow...")
            print(f"🔧 Using model: {self.model_name}")
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=request_data,
                timeout=120  # Increased timeout for DeepSeek
            )
            
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "")
                
                print(f"📝 Raw response length: {len(raw_response)}")
                if len(raw_response) > 0:
                    print(f"📄 Response preview: {raw_response[:100]}...")
                else:
                    print("⚠️ Empty response from Ollama")
                
                workflow_json = self._extract_json(raw_response)
                
                # Apply fixes to the workflow
                if workflow_json:
                    workflow_json = self.fix_common_issues(workflow_json)
                    workflow_json = self._validate_and_fix_workflow_execution(workflow_json)
                
                return {
                    "success": workflow_json is not None,
                    "workflow": workflow_json,
                    "confidence": 0.8 if workflow_json is not None else 0.0,
                    "raw_response": raw_response,
                    "model": self.model_name,
                    "generated_at": datetime.now().isoformat(),
                    "error": "Empty response" if len(raw_response) == 0 else None
                }
            else:
                error_msg = f"Ollama error {response.status_code}: {response.text}"
                print(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "workflow": None,
                    "confidence": 0.0,
                    "raw_response": ""
                }
                
        except requests.exceptions.ConnectionError as e:
            error_msg = "Could not connect to Ollama. Please ensure Ollama is running."
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "workflow": None,
                "confidence": 0.0,
                "raw_response": ""
            }
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout after 120s: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "workflow": None,
                "confidence": 0.0,
                "raw_response": ""
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "workflow": None,
                "confidence": 0.0,
                "raw_response": ""
            }
    
    def _generate_streaming(self, request_data: Dict) -> Dict[str, Any]:
        """Generate with streaming response"""
        try:
            print("🤖 Generating workflow (streaming)...")
            full_response = ""
            
            with requests.post(
                f"{self.ollama_host}/api/generate",
                json=request_data,
                stream=True,
                timeout=60
            ) as response:
                
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        full_response += token
                        
                        # Print token for visual feedback
                        print(token, end="", flush=True)
                        
                        if chunk.get("done", False):
                            break
            
            print()  
            
            workflow_json = self._extract_json(full_response)
            
            # Apply fixes to the workflow
            if workflow_json:
                workflow_json = self.fix_common_issues(workflow_json)
                workflow_json = self._validate_and_fix_workflow_execution(workflow_json)
            
            return {
                "success": workflow_json is not None,
                "workflow": workflow_json,
                "raw_response": full_response,
                "model": self.model_name,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workflow": None
            }
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from LLM response, aggressively removing thinking content"""
        if not text:
            return None
            
        # Store original for debugging
        original_text = text
        text = text.strip()
        
        
        # AGGRESSIVE thinking removal for DeepSeek
        # Remove <think>...</think> sections
        if "<think>" in text:
            think_pattern = r'<think>.*?</think>'
            text = re.sub(think_pattern, '', text, flags=re.DOTALL)
            text = text.strip()
        
        # Remove any remaining thinking indicators
        thinking_phrases = [
            r'Let me think.*?(?=\{)',
            r'I need to.*?(?=\{)',
            r'First.*?(?=\{)',
            r'Alright.*?(?=\{)',
            r'.*thinking.*?(?=\{)',
            r'.*analysis.*?(?=\{)'
        ]
        
        for phrase_pattern in thinking_phrases:
            text = re.sub(phrase_pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
            text = text.strip()
        
        # Remove everything before the first {
        if '{' in text:
            text = text[text.index('{'):]
        
        # Remove everything after the last }
        if '}' in text:
            text = text[:text.rindex('}') + 1]
        
        # Remove markdown code blocks if present
        if "```json" in text:
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                text = json_match.group(1).strip()
        elif "```" in text:
            json_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                text = json_match.group(1).strip()
        
        # Try to parse the cleaned JSON
        try:
            workflow = json.loads(text)
            if isinstance(workflow, dict) and "nodes" in workflow:
                workflow = self._fix_workflow_type_versions(workflow)
                return workflow
        except json.JSONDecodeError:
            pass
        
        # If direct parsing fails, try to find JSON patterns
        json_patterns = [
            r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}',  # Balanced braces
            r'\{[\s\S]*\}',  # Everything between first { and last }
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                # Try the longest match first
                for match in sorted(matches, key=len, reverse=True):
                    try:
                        clean_json = match.strip()
                        workflow = json.loads(clean_json)
                        
                        if isinstance(workflow, dict) and "nodes" in workflow:
                            workflow = self._fix_workflow_type_versions(workflow)
                            return workflow
                            
                    except json.JSONDecodeError:
                        continue
            
        return None
    
    def validate_workflow(self, workflow: Dict) -> Tuple[bool, List[str]]:
        """Validate generated workflow"""
        errors = []
        
        if not workflow:
            return False, ["No workflow generated"]
        
        # Check required fields
        if "nodes" not in workflow:
            errors.append("Missing 'nodes' field")
        if "connections" not in workflow:
            errors.append("Missing 'connections' field")
        
        # Validate nodes
        if "nodes" in workflow and workflow["nodes"]:
            node_ids = set()
            for i, node in enumerate(workflow["nodes"]):
                # Check required node fields
                required_fields = ["id", "name", "type"]
                for field in required_fields:
                    if field not in node:
                        errors.append(f"Node {i}: missing '{field}' field")
                
                # Check for duplicate IDs
                if "id" in node:
                    if node["id"] in node_ids:
                        errors.append(f"Duplicate node ID: {node['id']}")
                    node_ids.add(node["id"])
        else:
            errors.append("No nodes found in workflow")
        
        return len(errors) == 0, errors
    
    def fix_common_issues(self, workflow: Dict) -> Dict:
        """Fix common issues in generated workflows"""
        if not workflow:
            return workflow
        
        # Add default name if missing
        if "name" not in workflow:
            workflow["name"] = "Generated Workflow"
        
        # Add settings if missing
        if "settings" not in workflow:
            workflow["settings"] = {"executionOrder": "v1"}
        
        # Add connections if missing
        if "connections" not in workflow:
            workflow["connections"] = {}
        
        # Add n8n workflow metadata
        if "pinData" not in workflow:
            workflow["pinData"] = {}
        if "active" not in workflow:
            workflow["active"] = False
        if "tags" not in workflow:
            workflow["tags"] = []
        
        # Fix nodes
        if "nodes" in workflow:
            import uuid
            for i, node in enumerate(workflow["nodes"]):
                # Add name if missing (CRITICAL FIX)
                if "name" not in node or not node["name"]:
                    # Generate a default name based on node type
                    node_type = node.get("type", "").split(".")[-1] if "." in node.get("type", "") else "Node"
                    type_name_map = {
                        "webhook": "Webhook Trigger",
                        "scheduleTrigger": "Schedule Trigger", 
                        "httpRequest": "HTTP Request",
                        "code": "Code",
                        "slack": "Slack",
                        "emailSend": "Send Email",
                        "telegram": "Telegram Message"
                    }
                    node["name"] = type_name_map.get(node_type, f"Node {i+1}")
                
                # Generate UUID-style ID if missing or simple
                if "id" not in node or len(node["id"]) < 10:
                    node["id"] = str(uuid.uuid4())
                
                # Add typeVersion if missing
                if "typeVersion" not in node:
                    node["typeVersion"] = 1
                
                # Add position if missing
                if "position" not in node:
                    node["position"] = [250 + (i * 200), 300]  # Spread nodes horizontally
                
                # Add parameters if missing or enhance existing ones
                if "parameters" not in node:
                    node["parameters"] = {}
                
                # Add node-specific fields
                node_type = node.get("type", "")
                if "webhook" in node_type:
                    # Add webhookId for webhook nodes
                    if "webhookId" not in node:
                        node["webhookId"] = str(uuid.uuid4())
                    # Ensure webhook parameters have options
                    if "parameters" in node and "options" not in node["parameters"]:
                        node["parameters"]["options"] = {}
                elif "slack" in node_type:
                    # Add Slack-specific parameter structure
                    if "parameters" in node:
                        if "otherOptions" not in node["parameters"]:
                            node["parameters"]["otherOptions"] = {}
                        if "attachments" not in node["parameters"]:
                            node["parameters"]["attachments"] = []
                
                # Fix specific node parameter issues
                self._fix_node_parameters(node, node_type)
                
                # Add better default parameters based on node type
                if "@n8n/n8n-nodes-langchain.openAi" == node_type or "openai" in node_type.lower():
                    # OpenAI node - detect operation type from context
                    if not node["parameters"].get("operation"):
                        # Default to message operation for chat/summarization
                        node["parameters"].update({
                            "operation": "message",
                            "model": "gpt-3.5-turbo",
                            "messages": {
                                "messageType": "multipleMessages",
                                "values": [
                                    {
                                        "role": "system",
                                        "content": "You are a helpful assistant that summarizes content."
                                    },
                                    {
                                        "role": "user",
                                        "content": "{{ $json.input || 'Please process this data' }}"
                                    }
                                ]
                            }
                        })
                    # Add credentials if missing
                    if "credentials" not in node:
                        node["credentials"] = {
                            "openAiApi": {
                                "id": "openai_credentials_id",
                                "name": "OpenAi account"
                            }
                        }
                
                elif "emailSend" in node_type:
                    if not node["parameters"].get("toEmail"):
                        node["parameters"].update({
                            "toEmail": "{{ $json.email || 'recipient@example.com' }}",
                            "subject": "{{ $json.subject || 'Automated Email' }}",
                            "text": "{{ $json.message || 'This is an automated message' }}",
                            "fromEmail": "noreply@example.com"
                        })
                elif "scheduleTrigger" in node_type:
                    if not node["parameters"].get("rule"):
                        node["parameters"]["rule"] = {
                            "interval": [{"field": "hours", "hoursInterval": 24}]
                        }
                elif "webhook" in node_type:
                    if not node["parameters"].get("path"):
                        node["parameters"].update({
                            "httpMethod": "POST",
                            "path": "webhook-endpoint",
                            "responseMode": "responseNode"
                        })
                elif "code" in node_type:
                    if not node["parameters"].get("jsCode"):
                        node["parameters"]["jsCode"] = "// Process the input data\\nreturn items;"
                
                # Fix node type prefix (but skip LangChain nodes)
                if "type" in node and not node["type"].startswith("n8n-nodes-") and not node["type"].startswith("@n8n/"):
                    if not node["type"].startswith("nodes-base."):
                        node["type"] = f"n8n-nodes-base.{node['type']}"
                    else:
                        node["type"] = f"n8n-{node['type']}"
        
        # AUTO-CONNECT NODES if connections are empty
        if "connections" not in workflow or not workflow["connections"]:
            workflow["connections"] = {}
        
            nodes = workflow.get("nodes", [])
            if len(nodes) > 1:
                # Connect nodes in sequence using NODE NAMES (not IDs)
                for i in range(len(nodes) - 1):
                    current_node_name = nodes[i]["name"]
                    next_node_name = nodes[i + 1]["name"]
                
                    workflow["connections"][current_node_name] = {
                        "main": [[{"node": next_node_name, "type": "main", "index": 0}]]
                    }
        return workflow
    
    def _fix_node_parameters(self, node: Dict[str, Any], node_type: str):
        """Fix common parameter issues for specific node types"""
        params = node.get("parameters", {})
        
        # Schedule Trigger fixes
        if "scheduletrigger" in node_type.lower():
            # Remove cronExpression if rule exists (they conflict)
            if "rule" in params and "cronExpression" in params:
                del params["cronExpression"]
            
            # Ensure proper rule structure for schedule trigger
            if "rule" not in params:
                # Default to daily at 9 AM
                params["rule"] = {
                    "interval": [{
                        "field": "hours",
                        "hoursInterval": 24
                    }]
                }
            
            # Add triggerOn for better control
            if "triggerOn" not in params:
                params["triggerOn"] = "multipleIntervals"
        
        # Reddit node fixes  
        elif "reddit" in node_type.lower():
            # Fix parameter structure for Reddit API
            if "subreddits" in params:
                # Reddit node expects different structure
                subreddits = params.pop("subreddits", [])
                params.update({
                    "resource": "post",
                    "operation": "getAll",
                    "subreddit": subreddits[0] if subreddits else "popular",
                    "sort": "hot",
                    "limit": params.get("limit", 10)
                })
        
        # OpenAI/LangChain node fixes
        elif any(x in node_type.lower() for x in ["openai", "langchain"]):
            # Fix node type for LangChain OpenAI
            if "langchain" in node_type and "openai" in node_type:
                node["type"] = "@n8n/n8n-nodes-langchain.openAi"
                node["typeVersion"] = 1.3
            
            # Ensure proper message structure
            if "messages" not in params:
                params["messages"] = {
                    "values": [{
                        "role": "user", 
                        "content": "{{ $json }}"
                    }]
                }
        
        # Gmail node fixes
        elif "gmail" in node_type.lower():
            # Gmail requires specific operation and resource
            params.update({
                "resource": "message",
                "operation": "send"
            })
            
            # Fix email structure
            if "to" in params:
                params["toList"] = params.pop("to")
            if "message" in params:
                params["message"] = params.get("message", "")
                params["useHtml"] = False
                
        # HTTP Request node fixes  
        elif "httprequest" in node_type.lower():
            # Ensure proper HTTP method
            if "method" not in params:
                params["method"] = "GET"
            if "url" not in params:
                params["url"] = "https://api.example.com"
                
        # Code node fixes
        elif "code" in node_type.lower():
            if "jsCode" not in params:
                params["jsCode"] = "// Process the input data\nreturn items;"
                
        # Update node parameters
        node["parameters"] = params
        
    def _validate_and_fix_workflow_execution(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Additional validation and fixes for workflow execution issues"""
        if not workflow or "nodes" not in workflow:
            return workflow
            
        # Fix common execution blocking issues
        for node in workflow["nodes"]:
            node_type = node.get("type", "")
            params = node.get("parameters", {})
            
            # Add credentials placeholders for nodes that require them
            if any(service in node_type.lower() for service in ["gmail", "slack", "telegram", "openai", "discord"]):
                if "credentials" not in node:
                    cred_name = self._get_credential_name(node_type)
                    if cred_name:
                        node["credentials"] = {
                            cred_name: {
                                "id": "placeholder_credential_id",
                                "name": f"{cred_name.title()} account"
                            }
                        }
            
            # Ensure webhook nodes have proper configuration
            if "webhook" in node_type.lower():
                if "webhookId" not in node:
                    import uuid
                    node["webhookId"] = str(uuid.uuid4())
                if "httpMethod" not in params:
                    params["httpMethod"] = "GET"
                if "path" not in params:
                    params["path"] = "webhook"
                
            # Add disabled flag for problematic nodes during development
            if any(x in node_type.lower() for x in ["email", "slack", "telegram"]):
                node["disabled"] = True  # Disable external service calls by default
                
        return workflow
    
    def _get_credential_name(self, node_type: str) -> str:
        """Get the credential name for a node type"""
        credential_map = {
            "gmail": "gmailOAuth2",
            "slack": "slackOAuth2Api", 
            "telegram": "telegramApi",
            "openai": "openAiApi",
            "discord": "discordOAuth2Api"
        }
        
        for service, cred in credential_map.items():
            if service in node_type.lower():
                return cred
        return ""

class SimpleN8nGenerator:
    """Simple n8n workflow generator without RAG"""
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model_name: str = "deepseek-r1:14b"  
    ):
        print("🚀 Initializing Simple n8n Generator...")
        self.generator = OllamaWorkflowGenerator(ollama_host, model_name)
        
        # Output directory
        self.output_dir = Path("./generated_workflows")
        self.output_dir.mkdir(exist_ok=True)
        print("✅ Generator ready!")
    
    def generate_workflow(
        self,
        user_query: str,
        stream: bool = False,
        save_to_file: bool = True,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """Generate workflow from user query"""
        
        start_time = time.time()
        
        if verbose:
            print(f"\n🎯 Generating workflow for: {user_query}")
        
        # Generate workflow
        generation_result = self.generator.generate_workflow(user_query, stream=stream)
        
        if generation_result["success"] and generation_result["workflow"]:
            # Fix and validate
            workflow = self.generator.fix_common_issues(generation_result["workflow"])
            workflow = self.generator._validate_and_fix_workflow_execution(workflow)
            is_valid, errors = self.generator.validate_workflow(workflow)
            
            if verbose:
                if is_valid:
                    print("✅ Workflow validation passed!")
                else:
                    print(f"⚠️ Validation issues: {len(errors)}")
                    for error in errors[:3]:
                        print(f"   - {error}")
            
            # Save to file
            filepath = None
            if save_to_file and workflow:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"workflow_{timestamp}.json"
                filepath = self.output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(workflow, f, indent=2)
                
                if verbose:
                    print(f"💾 Saved to: {filepath}")
            
            return {
                "success": True,
                "workflow": workflow,
                "is_valid": is_valid,
                "validation_errors": errors,
                "generation_time": time.time() - start_time,
                "output_file": str(filepath) if filepath else None
            }
        else:
            return {
                "success": False,
                "error": generation_result.get("error", "Generation failed"),
                "generation_time": time.time() - start_time
            }

def test_generator():
    """Test the generator"""
    try:
        generator = SimpleN8nGenerator()
        
        test_queries = [
            "Create a simple webhook",
            "Build a workflow that sends an email notification",
            "Make an HTTP request to an API"
        ]
        
        for query in test_queries:
            print(f"\n{'='*50}")
            result = generator.generate_workflow(query, verbose=True)
            
            if result["success"]:
                workflow = result["workflow"]
                print(f"✅ Success!")
                print(f"   Nodes: {len(workflow.get('nodes', []))}")
                print(f"   Valid: {result.get('is_valid', False)}")
                if result.get('output_file'):
                    print(f"   File: {result['output_file']}")
            else:
                print(f"❌ Failed: {result.get('error')}")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def interactive_mode():
    """Interactive mode"""
    try:
        generator = SimpleN8nGenerator()
        
        print("\n" + "="*50)
        print("🤖 Simple n8n Workflow Generator")
        print("="*50)
        print("Type 'exit' to quit\n")
        
        while True:
            try:
                query = input("📝 Describe your workflow: ").strip()
                
                if query.lower() == 'exit':
                    print("👋 Goodbye!")
                    break
                elif not query:
                    continue
                
                result = generator.generate_workflow(query, stream=True)
                
                if result["success"]:
                    print(f"\n✅ Success! File: {result.get('output_file')}")
                    
                    workflow = result["workflow"]
                    nodes = workflow.get('nodes', [])
                    if nodes:
                        node_names = [n.get('name', 'Unnamed') for n in nodes]
                        print(f"📋 Nodes: {', '.join(node_names)}")
                else:
                    print(f"\n❌ Failed: {result.get('error')}")
                
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Failed to start: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_generator()
        elif sys.argv[1] == "interactive":
            interactive_mode()
        else:
            # Single query
            query = " ".join(sys.argv[1:])
            generator = SimpleN8nGenerator()
            result = generator.generate_workflow(query)
            if result["success"]:
                print(f"✅ Generated: {result.get('output_file')}")
            else:
                print(f"❌ Failed: {result.get('error')}")
    else:
        interactive_mode()
