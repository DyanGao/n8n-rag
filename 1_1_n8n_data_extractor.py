"""
n8n RAG System - Phase 1: Data Extraction and Preparation
Main script to extract all n8n documentation and prepare for vector indexing
"""

import json
import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
from pathlib import Path
from tqdm import tqdm
from chunking_utils import IntelligentChunker, create_intelligent_node_chunks


@dataclass
class NodeDocument:
    """Structure for node documentation"""
    node_type: str
    display_name: str
    description: str
    category: str
    package: str
    is_trigger: bool
    is_ai_tool: bool
    properties: Dict[str, Any]
    examples: List[Dict[str, Any]]
    connections: Dict[str, Any]
    documentation: str
    embedding_text: str
    metadata: Dict[str, Any]
    chunk_id: str
    
class N8nDataExtractor:
    """Extract and prepare n8n documentation for RAG system"""
    
    def __init__(
        self, 
        output_dir: str = "./n8n_rag_data",
        chunk_size: int = 800,
        chunk_overlap: int = 100
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.nodes_dir = self.output_dir / "nodes"
        self.templates_dir = self.output_dir / "templates"
        self.chunks_dir = self.output_dir / "chunks"
        self.metadata_dir = self.output_dir / "metadata"
        
        for dir_path in [self.nodes_dir, self.templates_dir, self.chunks_dir, self.metadata_dir]:
            dir_path.mkdir(exist_ok=True)
            
        self.extracted_nodes = []
        self.extracted_templates = []
        self.chunks = []
        
        # Initialize intelligent chunker
        self.chunker = IntelligentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
    def generate_chunk_id(self, content: str, prefix: str = "") -> str:
        """Generate unique ID for content chunk"""
        # Include prefix in hash to ensure uniqueness across chunk types
        combined_content = f"{prefix}_{content}"
        hash_obj = hashlib.md5(combined_content.encode())
        return f"{prefix}_{hash_obj.hexdigest()[:12]}"
    
    def get_all_n8n_nodes(self) -> List[Dict[str, Any]]:
        """Return comprehensive catalog of 400+ n8n nodes"""
        return [
            # === TRIGGER NODES ===
            {
                "nodeType": "n8n-nodes-base.webhook",
                "displayName": "Webhook",
                "description": "Starts a workflow when an HTTP request is received",
                "category": "trigger",
                "package": "n8n-nodes-base",
                "isTrigger": True,
                "isAITool": True,
                "properties": {
                    "httpMethod": {"type": "options", "options": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"], "default": "GET"},
                    "path": {"type": "string", "required": True, "description": "The path for the webhook URL"},
                    "responseMode": {"type": "options", "options": ["onReceived", "lastNode"], "default": "onReceived"}
                },
                "documentation": "Webhook node creates a unique URL that can receive HTTP requests to trigger workflows. Perfect for integrating with external services, APIs, and automation triggers.",
                "examples": [
                    {"title": "Simple webhook", "config": {"httpMethod": "POST", "path": "webhook"}},
                    {"title": "API endpoint", "config": {"httpMethod": "GET", "path": "api/data"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.scheduleTrigger",
                "displayName": "Schedule Trigger",
                "description": "Triggers workflow execution at specified intervals",
                "category": "trigger",
                "package": "n8n-nodes-base",
                "isTrigger": True,
                "isAITool": True,
                "properties": {
                    "rule": {"type": "object", "description": "Cron rule for scheduling"},
                    "triggerAt": {"type": "dateTime", "description": "Specific time to trigger"}
                },
                "documentation": "Schedule workflows to run automatically at specific times or intervals. Supports cron expressions for complex scheduling patterns.",
                "examples": [
                    {"title": "Daily at 9 AM", "config": {"rule": {"hour": 9, "minute": 0}}},
                    {"title": "Every 5 minutes", "config": {"rule": {"minute": "*/5"}}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.emailReadImap",
                "displayName": "Email Trigger (IMAP)",
                "description": "Triggers when new emails are received via IMAP",
                "category": "trigger",
                "package": "n8n-nodes-base",
                "isTrigger": True,
                "isAITool": True,
                "properties": {
                    "host": {"type": "string", "required": True},
                    "port": {"type": "number", "default": 993},
                    "user": {"type": "string", "required": True},
                    "password": {"type": "string", "required": True},
                    "ssl": {"type": "boolean", "default": True}
                },
                "documentation": "Monitor email inboxes and trigger workflows when new emails arrive. Supports filtering and processing of email content.",
                "examples": [
                    {"title": "Gmail monitoring", "config": {"host": "imap.gmail.com", "port": 993, "ssl": True}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.telegramTrigger",
                "displayName": "Telegram Trigger",
                "description": "Triggers workflow when Telegram events occur (messages, callbacks, reactions)",
                "category": "trigger",
                "package": "n8n-nodes-base",
                "isTrigger": True,
                "isAITool": True,
                "properties": {
                    "updates": {
                        "type": "multiOptions",
                        "options": ["message", "edited_message", "channel_post", "callback_query", "inline_query", "message_reaction"],
                        "default": ["message"],
                        "description": "Types of updates to receive"
                    },
                    "downloadImages": {
                        "type": "boolean",
                        "default": False,
                        "description": "Download images sent to the bot"
                    },
                    "downloadFiles": {
                        "type": "boolean", 
                        "default": False,
                        "description": "Download files sent to the bot"
                    },
                    "imageSize": {
                        "type": "options",
                        "options": ["small", "medium", "large"],
                        "default": "large",
                        "description": "Size of images to download"
                    }
                },
                "documentation": "Webhook-based Telegram trigger that responds to bot events including messages, callback queries from inline keyboards, inline queries, message reactions, and channel posts. Supports automatic file/image downloads with configurable sizes.",
                "examples": [
                    {"title": "Message trigger", "config": {"updates": ["message"], "downloadImages": True, "imageSize": "medium"}},
                    {"title": "Callback query trigger", "config": {"updates": ["callback_query"]}},
                    {"title": "Message reactions", "config": {"updates": ["message_reaction"]}}
                ]
            },

            # === COMMUNICATION NODES ===
            {
                "nodeType": "n8n-nodes-base.telegram",
                "displayName": "Telegram",
                "description": "Interact with Telegram to send messages, manage chats, handle callbacks, and work with files",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {
                        "type": "options", 
                        "options": ["chat", "callback", "file", "message"], 
                        "default": "message",
                        "description": "The resource to operate on"
                    },
                    "operation": {
                        "type": "options", 
                        "options": ["send", "edit", "delete", "pin", "get", "getAll", "answerQuery", "downloadFile"], 
                        "default": "send",
                        "description": "Operation to perform"
                    },
                    "chatId": {
                        "type": "string", 
                        "required": True, 
                        "description": "Chat ID, channel username (@channelusername), or user ID"
                    },
                    "messageType": {
                        "type": "options",
                        "options": ["text", "animation", "audio", "document", "photo", "sticker", "video", "voice", "location", "contact"],
                        "default": "text",
                        "description": "Type of message to send"
                    },
                    "text": {
                        "type": "string", 
                        "description": "Message text content"
                    },
                    "parseMode": {
                        "type": "options", 
                        "options": ["None", "Markdown", "MarkdownV2", "HTML"], 
                        "default": "Markdown",
                        "description": "Parse mode for formatting text"
                    },
                    "disableNotification": {
                        "type": "boolean", 
                        "default": False,
                        "description": "Send message silently"
                    },
                    "disableWebPagePreview": {
                        "type": "boolean",
                        "default": False,
                        "description": "Disable web page preview for links"
                    },
                    "replyToMessageId": {
                        "type": "number",
                        "description": "Message ID to reply to"
                    },
                    "fileId": {
                        "type": "string",
                        "description": "File ID for file operations"
                    },
                    "caption": {
                        "type": "string",
                        "description": "Caption for media files"
                    },
                    "queryId": {
                        "type": "string", 
                        "description": "Callback query ID to answer"
                    },
                    "answerText": {
                        "type": "string",
                        "description": "Text to show to user (callback answer)"
                    },
                    "showAlert": {
                        "type": "boolean",
                        "default": False,
                        "description": "Show alert instead of notification"
                    }
                },
                "documentation": "Comprehensive Telegram integration supporting message operations (send, edit, delete, pin text/media messages), chat operations (get chat info, administrators, members), callback operations (answer inline keyboard queries), and file operations (get/download files). Supports all message types including animations, audio, documents, photos, stickers, videos, voice messages, locations, and contacts.",
                "examples": [
                    {"title": "Send text message", "config": {"resource": "message", "operation": "send", "messageType": "text", "chatId": "@channel", "text": "Hello from n8n!", "parseMode": "Markdown"}},
                    {"title": "Send photo with caption", "config": {"resource": "message", "operation": "send", "messageType": "photo", "chatId": "123456789", "caption": "Check out this photo!", "disableNotification": True}},
                    {"title": "Answer callback query", "config": {"resource": "callback", "operation": "answerQuery", "queryId": "callback_query_id", "answerText": "Button clicked!", "showAlert": False}},
                    {"title": "Get chat info", "config": {"resource": "chat", "operation": "get", "chatId": "@mychannel"}},
                    {"title": "Download file", "config": {"resource": "file", "operation": "get", "fileId": "BAADBAADrwADBREAAYdaEKS-zYdaAg"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.discord",
                "displayName": "Discord",
                "description": "Send messages and manage Discord servers",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["message", "member"], "default": "message"},
                    "operation": {"type": "options", "options": ["send", "edit", "delete"], "default": "send"},
                    "webhookUrl": {"type": "string", "description": "Discord webhook URL"},
                    "content": {"type": "string", "description": "Message content"},
                    "username": {"type": "string", "description": "Custom username"},
                    "embeds": {"type": "collection", "description": "Rich embeds"}
                },
                "documentation": "Send messages to Discord channels via webhooks or bot API. Supports rich embeds, mentions, and file attachments.",
                "examples": [
                    {"title": "Webhook message", "config": {"resource": "message", "operation": "send", "content": "Hello Discord!"}},
                    {"title": "Rich embed", "config": {"embeds": [{"title": "Alert", "description": "System notification", "color": 16711680}]}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.slack",
                "displayName": "Slack",
                "description": "Send messages and manage Slack workspaces",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["message", "channel", "user"], "default": "message"},
                    "operation": {"type": "options", "options": ["post", "update", "delete", "get"], "default": "post"},
                    "channel": {"type": "string", "required": True, "description": "Channel name or ID"},
                    "text": {"type": "string", "description": "Message text"},
                    "username": {"type": "string", "description": "Bot username"},
                    "linkNames": {"type": "boolean", "default": True}
                },
                "documentation": "Send messages to Slack channels, DMs, and manage workspace. Supports mentions, attachments, and interactive components.",
                "examples": [
                    {"title": "Channel message", "config": {"resource": "message", "operation": "post", "channel": "#general", "text": "Hello team!"}},
                    {"title": "Direct message", "config": {"channel": "@user", "text": "Private notification"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.microsoftTeams",
                "displayName": "Microsoft Teams",
                "description": "Send messages to Microsoft Teams channels",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["message"], "default": "message"},
                    "operation": {"type": "options", "options": ["send"], "default": "send"},
                    "webhookUrl": {"type": "string", "required": True},
                    "message": {"type": "string", "required": True}
                },
                "documentation": "Send notifications and messages to Microsoft Teams channels using webhooks.",
                "examples": [
                    {"title": "Team notification", "config": {"message": "Deployment complete!"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.whatsApp",
                "displayName": "WhatsApp Business",
                "description": "Send WhatsApp messages via WhatsApp Business API",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["message"], "default": "message"},
                    "operation": {"type": "options", "options": ["send"], "default": "send"},
                    "to": {"type": "string", "required": True, "description": "Recipient phone number"},
                    "message": {"type": "string", "required": True, "description": "Message text"}
                },
                "documentation": "Send WhatsApp messages using the WhatsApp Business API for customer communication.",
                "examples": [
                    {"title": "Send message", "config": {"to": "+1234567890", "message": "Hello from n8n!"}}
                ]
            },

            # === EMAIL NODES ===
            {
                "nodeType": "n8n-nodes-base.emailSend",
                "displayName": "Send Email",
                "description": "Send emails via SMTP",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "fromEmail": {"type": "string", "required": True},
                    "toEmail": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "text": {"type": "string", "description": "Plain text content"},
                    "html": {"type": "string", "description": "HTML content"},
                    "attachments": {"type": "collection", "description": "File attachments"}
                },
                "documentation": "Send emails with attachments and HTML content via SMTP servers.",
                "examples": [
                    {"title": "Simple email", "config": {"subject": "Alert", "text": "System notification"}},
                    {"title": "HTML email", "config": {"subject": "Report", "html": "<h1>Daily Report</h1>"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.gmail",
                "displayName": "Gmail",
                "description": "Send emails through Gmail, read Gmail messages, and manage Gmail labels using Google API authentication",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["message", "label"], "default": "message"},
                    "operation": {"type": "options", "options": ["send", "get", "getAll", "delete"], "default": "send"},
                    "to": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "message": {"type": "string", "required": True}
                },
                "documentation": "Gmail integration for sending emails through your Gmail account, reading Gmail messages, and managing Gmail labels. Requires Google OAuth authentication. Use this specifically for Gmail accounts rather than generic SMTP email sending.",
                "examples": [
                    {"title": "Send email via Gmail", "config": {"resource": "message", "operation": "send", "to": "user@example.com", "subject": "Reddit Posts Update", "message": "Here are the latest posts from Reddit"}},
                    {"title": "Send Gmail with Reddit data", "config": {"resource": "message", "operation": "send", "to": "admin@company.com", "subject": "Daily Reddit Summary", "message": "{{ $json.title }} - {{ $json.url }}"}},
                    {"title": "Email notification through Gmail", "config": {"resource": "message", "operation": "send", "to": "team@company.com", "subject": "Workflow Alert", "message": "Automated notification sent via Gmail"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.outlook",
                "displayName": "Microsoft Outlook",
                "description": "Send and manage emails via Microsoft Outlook",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["message", "folder"], "default": "message"},
                    "operation": {"type": "options", "options": ["send", "get", "getAll"], "default": "send"},
                    "to": {"type": "string", "required": True},
                    "subject": {"type": "string", "required": True},
                    "bodyContent": {"type": "string", "required": True}
                },
                "documentation": "Send and receive emails through Microsoft Outlook using Microsoft Graph API.",
                "examples": [
                    {"title": "Send email", "config": {"operation": "send", "to": "colleague@company.com", "subject": "Meeting", "bodyContent": "Let's schedule a meeting."}}
                ]
            },

            # === DATABASE NODES ===
            {
                "nodeType": "n8n-nodes-base.postgres",
                "displayName": "Postgres",
                "description": "Execute queries and manage PostgreSQL databases",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["executeQuery", "insert", "update", "delete"], "default": "executeQuery"},
                    "query": {"type": "string", "description": "SQL query to execute"},
                    "table": {"type": "string", "description": "Table name"},
                    "columns": {"type": "string", "description": "Column names"},
                    "values": {"type": "string", "description": "Values to insert/update"}
                },
                "documentation": "Connect to PostgreSQL databases to execute queries, insert records, update data, and manage database operations.",
                "examples": [
                    {"title": "Select query", "config": {"operation": "executeQuery", "query": "SELECT * FROM users WHERE active = true"}},
                    {"title": "Insert record", "config": {"operation": "insert", "table": "users", "columns": "name,email", "values": "John,john@example.com"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.mysql",
                "displayName": "MySQL",
                "description": "Execute queries and manage MySQL databases",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["executeQuery", "insert", "update", "delete"], "default": "executeQuery"},
                    "query": {"type": "string", "description": "SQL query to execute"},
                    "table": {"type": "string", "description": "Table name"}
                },
                "documentation": "Connect to MySQL databases for data operations, queries, and database management tasks.",
                "examples": [
                    {"title": "Query data", "config": {"operation": "executeQuery", "query": "SELECT COUNT(*) FROM orders WHERE status = 'completed'"}},
                    {"title": "Update record", "config": {"operation": "update", "query": "UPDATE users SET last_login = NOW() WHERE id = ?"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.mongodb",
                "displayName": "MongoDB",
                "description": "Interact with MongoDB databases and collections",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["find", "findOneAndUpdate", "insert", "update", "delete"], "default": "find"},
                    "collection": {"type": "string", "required": True, "description": "Collection name"},
                    "query": {"type": "json", "description": "MongoDB query"},
                    "fields": {"type": "json", "description": "Fields to return"}
                },
                "documentation": "Perform CRUD operations on MongoDB collections, execute queries, and manage document databases.",
                "examples": [
                    {"title": "Find documents", "config": {"operation": "find", "collection": "users", "query": "{\"active\": true}"}},
                    {"title": "Insert document", "config": {"operation": "insert", "collection": "orders", "query": "{\"product\": \"laptop\", \"price\": 999}"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.redis",
                "displayName": "Redis",
                "description": "Interact with Redis key-value store",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["get", "set", "delete", "incr", "exists"], "default": "get"},
                    "key": {"type": "string", "required": True, "description": "Redis key"},
                    "value": {"type": "string", "description": "Value to set"},
                    "ttl": {"type": "number", "description": "Time to live in seconds"}
                },
                "documentation": "Store and retrieve data from Redis cache, manage sessions, and implement caching strategies.",
                "examples": [
                    {"title": "Cache data", "config": {"operation": "set", "key": "user:123", "value": "John Doe", "ttl": 3600}},
                    {"title": "Get cached value", "config": {"operation": "get", "key": "user:123"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.supabase",
                "displayName": "Supabase",
                "description": "Interact with Supabase database and services",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["row"], "default": "row"},
                    "operation": {"type": "options", "options": ["create", "delete", "get", "getAll", "update"], "default": "get"},
                    "table": {"type": "string", "required": True, "description": "Table name"},
                    "filterType": {"type": "options", "options": ["manual", "json"], "default": "manual"}
                },
                "documentation": "Manage Supabase database operations including CRUD operations on tables and real-time subscriptions.",
                "examples": [
                    {"title": "Insert row", "config": {"operation": "create", "table": "profiles", "filterType": "manual"}},
                    {"title": "Get all rows", "config": {"operation": "getAll", "table": "posts"}}
                ]
            },

            # === FILE & STORAGE NODES ===
            {
                "nodeType": "n8n-nodes-base.googleDrive",
                "displayName": "Google Drive",
                "description": "Upload, download, and manage files in Google Drive",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["file", "folder"], "default": "file"},
                    "operation": {"type": "options", "options": ["upload", "download", "delete", "share"], "default": "upload"},
                    "name": {"type": "string", "description": "File name"},
                    "parents": {"type": "collection", "description": "Parent folder IDs"}
                },
                "documentation": "Manage Google Drive files and folders, upload documents, share files, and organize cloud storage.",
                "examples": [
                    {"title": "Upload file", "config": {"resource": "file", "operation": "upload", "name": "report.pdf"}},
                    {"title": "Create folder", "config": {"resource": "folder", "operation": "create", "name": "Monthly Reports"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.googleSheets",
                "displayName": "Google Sheets",
                "description": "Read from and write to Google Sheets spreadsheets",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["spreadsheet", "sheet"], "default": "sheet"},
                    "operation": {"type": "options", "options": ["append", "clear", "create", "delete", "read", "update"], "default": "append"},
                    "spreadsheetId": {"type": "string", "required": True},
                    "range": {"type": "string", "description": "A1 notation range"},
                    "values": {"type": "collection", "description": "Values to write"}
                },
                "documentation": "Integrate with Google Sheets to read data, append rows, update cells, and manage spreadsheet operations.",
                "examples": [
                    {"title": "Append row", "config": {"operation": "append", "range": "Sheet1!A:C", "values": [["John", "Doe", "john@example.com"]]}},
                    {"title": "Read range", "config": {"operation": "read", "range": "Sheet1!A1:C10"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.googleCalendar",
                "displayName": "Google Calendar",
                "description": "Create, update, and manage Google Calendar events and calendars",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["calendar", "event"], "default": "event"},
                    "operation": {"type": "options", "options": ["create", "delete", "get", "getAll", "update"], "default": "create"},
                    "calendarId": {"type": "string", "description": "Calendar ID"},
                    "summary": {"type": "string", "description": "Event title"},
                    "start": {"type": "dateTime", "description": "Start date and time"},
                    "end": {"type": "dateTime", "description": "End date and time"},
                    "description": {"type": "string", "description": "Event description"},
                    "location": {"type": "string", "description": "Event location"}
                },
                "documentation": "Manage Google Calendar events, create meetings, schedule appointments, and integrate calendar functionality into workflows.",
                "examples": [
                    {"title": "Create event", "config": {"resource": "event", "operation": "create", "summary": "Team Meeting", "start": "2024-01-15T10:00:00", "end": "2024-01-15T11:00:00"}},
                    {"title": "List events", "config": {"resource": "event", "operation": "getAll", "calendarId": "primary"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.googleDocs",
                "displayName": "Google Docs",
                "description": "Create, read, and update Google Docs documents",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["document"], "default": "document"},
                    "operation": {"type": "options", "options": ["create", "get", "update"], "default": "create"},
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Document content"},
                    "documentId": {"type": "string", "description": "Document ID"},
                    "folderId": {"type": "string", "description": "Parent folder ID"}
                },
                "documentation": "Create and manage Google Docs documents, insert content, and collaborate on documents programmatically.",
                "examples": [
                    {"title": "Create document", "config": {"resource": "document", "operation": "create", "title": "Project Report", "content": "This is the content"}},
                    {"title": "Update document", "config": {"resource": "document", "operation": "update", "documentId": "doc123", "content": "Updated content"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.googleForms",
                "displayName": "Google Forms",
                "description": "Create forms and retrieve responses from Google Forms",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["form", "response"], "default": "form"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll"], "default": "get"},
                    "formId": {"type": "string", "description": "Form ID"},
                    "title": {"type": "string", "description": "Form title"},
                    "description": {"type": "string", "description": "Form description"}
                },
                "documentation": "Manage Google Forms, collect responses, and integrate form data into automated workflows.",
                "examples": [
                    {"title": "Get responses", "config": {"resource": "response", "operation": "getAll", "formId": "form123"}},
                    {"title": "Create form", "config": {"resource": "form", "operation": "create", "title": "Feedback Form", "description": "Please provide your feedback"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.googleAnalytics",
                "displayName": "Google Analytics",
                "description": "Retrieve Google Analytics data and reports",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["report", "userActivity"], "default": "report"},
                    "operation": {"type": "options", "options": ["get"], "default": "get"},
                    "viewId": {"type": "string", "required": True, "description": "Analytics view ID"},
                    "startDate": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "endDate": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "metrics": {"type": "string", "description": "Metrics to retrieve"},
                    "dimensions": {"type": "string", "description": "Dimensions to group by"}
                },
                "documentation": "Access Google Analytics data, generate reports, and integrate website analytics into your workflows.",
                "examples": [
                    {"title": "Get page views", "config": {"resource": "report", "operation": "get", "viewId": "12345", "startDate": "2024-01-01", "endDate": "2024-01-31", "metrics": "ga:pageviews"}},
                    {"title": "Get user data", "config": {"resource": "report", "operation": "get", "metrics": "ga:users,ga:sessions", "dimensions": "ga:country"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.googleCloud",
                "displayName": "Google Cloud",
                "description": "Interact with Google Cloud Platform services",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["storage", "function", "firestore"], "default": "storage"},
                    "operation": {"type": "options", "options": ["upload", "download", "delete", "invoke"], "default": "upload"},
                    "bucketName": {"type": "string", "description": "Cloud Storage bucket name"},
                    "fileName": {"type": "string", "description": "File name"},
                    "functionName": {"type": "string", "description": "Cloud Function name"},
                    "collection": {"type": "string", "description": "Firestore collection"}
                },
                "documentation": "Integrate with Google Cloud services including Cloud Storage, Cloud Functions, and Firestore for scalable cloud operations.",
                "examples": [
                    {"title": "Upload to storage", "config": {"resource": "storage", "operation": "upload", "bucketName": "my-bucket", "fileName": "data.json"}},
                    {"title": "Invoke function", "config": {"resource": "function", "operation": "invoke", "functionName": "process-data"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.dropbox",
                "displayName": "Dropbox",
                "description": "Upload, download, and manage Dropbox files",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["file", "folder"], "default": "file"},
                    "operation": {"type": "options", "options": ["upload", "download", "delete", "search"], "default": "upload"},
                    "path": {"type": "string", "required": True, "description": "File path in Dropbox"}
                },
                "documentation": "Manage Dropbox files and folders, sync documents, and integrate cloud storage workflows.",
                "examples": [
                    {"title": "Upload file", "config": {"operation": "upload", "path": "/documents/report.pdf"}},
                    {"title": "Download file", "config": {"operation": "download", "path": "/backup/data.json"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.awsS3",
                "displayName": "AWS S3",
                "description": "Upload, download, and manage files in Amazon S3",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["file", "folder"], "default": "file"},
                    "operation": {"type": "options", "options": ["upload", "download", "delete", "getAll"], "default": "upload"},
                    "bucketName": {"type": "string", "required": True},
                    "fileKey": {"type": "string", "required": True, "description": "S3 object key"}
                },
                "documentation": "Integrate with Amazon S3 for file storage, backup operations, and cloud file management.",
                "examples": [
                    {"title": "Upload to S3", "config": {"operation": "upload", "bucketName": "my-bucket", "fileKey": "uploads/image.jpg"}},
                    {"title": "List objects", "config": {"operation": "getAll", "bucketName": "my-bucket"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.awsLambda",
                "displayName": "AWS Lambda",
                "description": "Invoke AWS Lambda functions and manage serverless operations",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["invoke"], "default": "invoke"},
                    "functionName": {"type": "string", "required": True, "description": "Lambda function name"},
                    "invocationType": {"type": "options", "options": ["RequestResponse", "Event", "DryRun"], "default": "RequestResponse"},
                    "payload": {"type": "json", "description": "Function payload"},
                    "qualifier": {"type": "string", "description": "Function version or alias"}
                },
                "documentation": "Invoke AWS Lambda functions for serverless computing, process events, and integrate with other AWS services.",
                "examples": [
                    {"title": "Invoke function", "config": {"operation": "invoke", "functionName": "my-function", "payload": {"key": "value"}}},
                    {"title": "Async invoke", "config": {"operation": "invoke", "functionName": "process-data", "invocationType": "Event"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.awsSes",
                "displayName": "AWS SES",
                "description": "Send emails using Amazon Simple Email Service",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["email"], "default": "email"},
                    "operation": {"type": "options", "options": ["send"], "default": "send"},
                    "fromEmail": {"type": "string", "required": True, "description": "Sender email address"},
                    "toEmail": {"type": "string", "required": True, "description": "Recipient email address"},
                    "subject": {"type": "string", "required": True, "description": "Email subject"},
                    "body": {"type": "string", "required": True, "description": "Email body"},
                    "isBodyHtml": {"type": "boolean", "default": False, "description": "Body contains HTML"}
                },
                "documentation": "Send transactional emails, marketing emails, and notifications using Amazon Simple Email Service with high deliverability.",
                "examples": [
                    {"title": "Send text email", "config": {"operation": "send", "fromEmail": "sender@domain.com", "toEmail": "recipient@domain.com", "subject": "Hello", "body": "Hello World!"}},
                    {"title": "Send HTML email", "config": {"operation": "send", "subject": "Newsletter", "body": "<h1>Welcome!</h1>", "isBodyHtml": True}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.awsSns",
                "displayName": "AWS SNS",
                "description": "Send push notifications and SMS using Amazon Simple Notification Service",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["sms", "topic"], "default": "sms"},
                    "operation": {"type": "options", "options": ["send", "publish"], "default": "send"},
                    "phoneNumber": {"type": "string", "description": "Phone number for SMS"},
                    "message": {"type": "string", "required": True, "description": "Message content"},
                    "topicArn": {"type": "string", "description": "SNS topic ARN"},
                    "subject": {"type": "string", "description": "Message subject"}
                },
                "documentation": "Send SMS messages, push notifications, and publish messages to SNS topics for distributed messaging.",
                "examples": [
                    {"title": "Send SMS", "config": {"resource": "sms", "operation": "send", "phoneNumber": "+1234567890", "message": "Hello from n8n!"}},
                    {"title": "Publish to topic", "config": {"resource": "topic", "operation": "publish", "topicArn": "arn:aws:sns:region:account:topic", "message": "Alert", "subject": "System Alert"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.awsDynamodb",
                "displayName": "AWS DynamoDB",
                "description": "Perform CRUD operations on Amazon DynamoDB NoSQL database",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["scan", "query", "get", "put", "update", "delete"], "default": "get"},
                    "tableName": {"type": "string", "required": True, "description": "DynamoDB table name"},
                    "key": {"type": "json", "description": "Item key"},
                    "item": {"type": "json", "description": "Item data"},
                    "filterExpression": {"type": "string", "description": "Filter expression"},
                    "projectionExpression": {"type": "string", "description": "Attributes to retrieve"}
                },
                "documentation": "Interact with Amazon DynamoDB NoSQL database for high-performance applications requiring fast, predictable performance.",
                "examples": [
                    {"title": "Get item", "config": {"operation": "get", "tableName": "Users", "key": {"id": {"S": "123"}}}},
                    {"title": "Put item", "config": {"operation": "put", "tableName": "Users", "item": {"id": {"S": "123"}, "name": {"S": "John"}}}}
                ]
            },

            # === CORE & UTILITY NODES ===
            {
                "nodeType": "n8n-nodes-base.json",
                "displayName": "JSON",
                "description": "Process, parse, transform, and manipulate JSON data",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["parse", "stringify", "transform", "extract"], "default": "parse"},
                    "path": {"type": "string", "description": "JSONPath expression for data extraction"},
                    "data": {"type": "json", "description": "JSON data to process"},
                    "prettify": {"type": "boolean", "default": False, "description": "Format JSON with indentation"}
                },
                "documentation": "Essential for processing JSON API responses, transforming data structures, extracting specific fields, and preparing data for other nodes.",
                "examples": [
                    {"title": "Parse JSON string", "config": {"operation": "parse", "data": "{\"name\": \"John\", \"age\": 30}"}},
                    {"title": "Extract field", "config": {"operation": "extract", "path": "$.data[*].name"}},
                    {"title": "Transform structure", "config": {"operation": "transform", "prettify": True}}
                ],
                "embedding_text": "Node: JSON\nType: n8n-nodes-base.json\nCategory: transform\nDescription: Process, parse, transform, and manipulate JSON data\nUse case: Parse JSON, extract data, transform structures\nUse for: JSON processing, API response handling, data transformation\nKey properties: operation, path, data",
                "metadata": {
                    "node_type": "n8n-nodes-base.json",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.xml",
                "displayName": "XML",
                "description": "Parse, generate, and transform XML documents",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["parse", "generate", "transform"], "default": "parse"},
                    "xmlData": {"type": "string", "description": "XML data to process"},
                    "rootElement": {"type": "string", "description": "Root element for XML generation"},
                    "encoding": {"type": "options", "options": ["UTF-8", "UTF-16", "ISO-8859-1"], "default": "UTF-8"}
                },
                "documentation": "Process XML from APIs, SOAP services, RSS feeds, and legacy systems. Convert between XML and JSON formats.",
                "examples": [
                    {"title": "Parse XML", "config": {"operation": "parse", "xmlData": "<root><item>value</item></root>"}},
                    {"title": "Generate XML", "config": {"operation": "generate", "rootElement": "data"}}
                ],
                "embedding_text": "Node: XML\nType: n8n-nodes-base.xml\nCategory: transform\nDescription: Parse, generate, and transform XML documents\nUse case: XML processing, SOAP integration\nUse for: XML parsing, RSS feeds, legacy systems\nKey properties: operation, xmlData, rootElement",
                "metadata": {
                    "node_type": "n8n-nodes-base.xml",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.csv",
                "displayName": "CSV",
                "description": "Read, write, and transform CSV (Comma-Separated Values) files",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["read", "write", "transform"], "default": "read"},
                    "delimiter": {"type": "string", "default": ",", "description": "Field delimiter"},
                    "headers": {"type": "boolean", "default": True, "description": "First row contains headers"},
                    "encoding": {"type": "options", "options": ["UTF-8", "UTF-16", "ISO-8859-1"], "default": "UTF-8"}
                },
                "documentation": "Handle CSV data import/export, process spreadsheet data, convert between CSV and JSON formats for data migration.",
                "examples": [
                    {"title": "Read CSV", "config": {"operation": "read", "headers": True, "delimiter": ","}},
                    {"title": "Convert to CSV", "config": {"operation": "write", "headers": True}}
                ],
                "embedding_text": "Node: CSV\nType: n8n-nodes-base.csv\nCategory: transform\nDescription: Read, write, and transform CSV files\nUse case: Data import/export, spreadsheet processing\nUse for: CSV processing, data migration, file handling\nKey properties: operation, delimiter, headers",
                "metadata": {
                    "node_type": "n8n-nodes-base.csv",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.if",
                "displayName": "IF",
                "description": "Route workflow execution based on conditional logic",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "conditions": {
                        "type": "collection",
                        "description": "Conditions to evaluate",
                        "options": [
                            {"name": "boolean", "type": "boolean"},
                            {"name": "dateTime", "type": "dateTime"},
                            {"name": "number", "type": "number"},
                            {"name": "string", "type": "string"}
                        ]
                    },
                    "combineOperation": {"type": "options", "options": ["AND", "OR"], "default": "AND"}
                },
                "documentation": "Essential for workflow branching logic, conditional processing, data validation, and error handling paths.",
                "examples": [
                    {"title": "Check number", "config": {"conditions": {"number": {"value1": "{{$json.count}}", "operation": "larger", "value2": 10}}}},
                    {"title": "String contains", "config": {"conditions": {"string": {"value1": "{{$json.status}}", "operation": "contains", "value2": "success"}}}}
                ],
                "embedding_text": "Node: IF\nType: n8n-nodes-base.if\nCategory: transform\nDescription: Route workflow execution based on conditional logic\nUse case: Workflow branching, conditional processing\nUse for: Logic conditions, data validation, routing\nKey properties: conditions, combineOperation",
                "metadata": {
                    "node_type": "n8n-nodes-base.if",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 2
                }
            },
            {
                "nodeType": "n8n-nodes-base.switch",
                "displayName": "Switch",
                "description": "Route data to different paths based on multiple conditions",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "mode": {"type": "options", "options": ["expression", "rules"], "default": "rules"},
                    "rules": {
                        "type": "fixedCollection",
                        "description": "Rules for routing data"
                    },
                    "fallbackOutput": {"type": "number", "default": 3, "description": "Output to use when no rules match"}
                },
                "documentation": "Advanced conditional routing with multiple output paths. Perfect for complex workflow branching and multi-path data processing.",
                "examples": [
                    {"title": "Route by status", "config": {"mode": "rules", "rules": {"values": [{"conditions": {"string": {"value1": "{{$json.status}}", "operation": "equal", "value2": "active"}}}]}}},
                    {"title": "Route by number range", "config": {"mode": "rules", "fallbackOutput": 2}}
                ],
                "embedding_text": "Node: Switch\nType: n8n-nodes-base.switch\nCategory: transform\nDescription: Route data to different paths based on multiple conditions\nUse case: Multi-path routing, complex branching\nUse for: Advanced routing, conditional logic, workflow paths\nKey properties: mode, rules, fallbackOutput",
                "metadata": {
                    "node_type": "n8n-nodes-base.switch",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 3
                }
            },
            {
                "nodeType": "n8n-nodes-base.merge",
                "displayName": "Merge",
                "description": "Combine data from multiple workflow branches",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "mode": {"type": "options", "options": ["append", "pass-through", "wait"], "default": "append"},
                    "mergeByFields": {"type": "string", "description": "Fields to merge by"},
                    "clashHandling": {"type": "options", "options": ["addSuffix", "preferInput1", "preferInput2"], "default": "addSuffix"}
                },
                "documentation": "Combine data from parallel workflow branches, merge API responses, synchronize data streams for unified processing.",
                "examples": [
                    {"title": "Append all data", "config": {"mode": "append"}},
                    {"title": "Wait for all", "config": {"mode": "wait"}},
                    {"title": "Merge by ID", "config": {"mode": "append", "mergeByFields": "id"}}
                ],
                "embedding_text": "Node: Merge\nType: n8n-nodes-base.merge\nCategory: transform\nDescription: Combine data from multiple workflow branches\nUse case: Data merging, branch synchronization\nUse for: Merge branches, combine data, synchronize flows\nKey properties: mode, mergeByFields, clashHandling",
                "metadata": {
                    "node_type": "n8n-nodes-base.merge",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 3
                }
            },
            {
                "nodeType": "n8n-nodes-base.set",
                "displayName": "Set",
                "description": "Set values, add fields, transform data structure",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "keepOnlySet": {"type": "boolean", "default": False, "description": "Keep only set values"},
                    "values": {
                        "type": "fixedCollection",
                        "description": "Values to set",
                        "options": [
                            {"name": "boolean", "type": "boolean"},
                            {"name": "number", "type": "number"},
                            {"name": "string", "type": "string"}
                        ]
                    },
                    "options": {"type": "collection", "description": "Additional options"}
                },
                "documentation": "Transform data, add calculated fields, prepare data for APIs, clean and structure data for downstream processing.",
                "examples": [
                    {"title": "Add timestamp", "config": {"values": {"string": [{"name": "timestamp", "value": "{{$now}}"}]}}},
                    {"title": "Calculate field", "config": {"values": {"number": [{"name": "total", "value": "{{$json.price * $json.quantity}}"}]}}},
                    {"title": "Clean data", "config": {"keepOnlySet": True, "values": {"string": [{"name": "clean_name", "value": "{{$json.name.toLowerCase()}}"}]}}}
                ],
                "embedding_text": "Node: Set\nType: n8n-nodes-base.set\nCategory: transform\nDescription: Set values, add fields, transform data structure\nUse case: Data transformation, field addition\nUse for: Set values, transform data, add fields\nKey properties: keepOnlySet, values, options",
                "metadata": {
                    "node_type": "n8n-nodes-base.set",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 3
                }
            },
            {
                "nodeType": "n8n-nodes-base.functionItem",
                "displayName": "Function Item",
                "description": "Run custom JavaScript code on each item separately",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "functionCode": {"type": "string", "description": "JavaScript function code", "typeOptions": {"editor": "code"}},
                    "mode": {"type": "options", "options": ["runOnceForEachItem", "runOnceForAllItems"], "default": "runOnceForEachItem"}
                },
                "documentation": "Execute custom JavaScript logic on individual data items. Perfect for complex transformations, calculations, and custom business logic.",
                "examples": [
                    {"title": "Transform item", "config": {"functionCode": "item.fullName = `${item.firstName} ${item.lastName}`;\nreturn item;"}},
                    {"title": "Calculate field", "config": {"functionCode": "item.discount = item.price > 100 ? item.price * 0.1 : 0;\nreturn item;"}}
                ],
                "embedding_text": "Node: Function Item\nType: n8n-nodes-base.functionItem\nCategory: transform\nDescription: Run custom JavaScript code on each item separately\nUse case: Custom logic, item processing\nUse for: JavaScript code, custom transformations, item logic\nKey properties: functionCode, mode",
                "metadata": {
                    "node_type": "n8n-nodes-base.functionItem",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 2
                }
            },
            {
                "nodeType": "n8n-nodes-base.function",
                "displayName": "Function",
                "description": "Run custom JavaScript code on all items at once",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "functionCode": {"type": "string", "description": "JavaScript function code", "typeOptions": {"editor": "code"}},
                    "mode": {"type": "options", "options": ["code", "runOnceForAllItems"], "default": "code"}
                },
                "documentation": "Execute custom JavaScript code on entire dataset. Advanced data processing, aggregations, complex transformations, and custom algorithms.",
                "examples": [
                    {"title": "Aggregate data", "config": {"functionCode": "const total = items.reduce((sum, item) => sum + item.json.amount, 0);\nreturn [{json: {total}}];"}},
                    {"title": "Custom processing", "config": {"functionCode": "return items.filter(item => item.json.status === 'active').map(item => ({json: item.json}));"}}
                ],
                "embedding_text": "Node: Function\nType: n8n-nodes-base.function\nCategory: transform\nDescription: Run custom JavaScript code on all items at once\nUse case: Custom logic, bulk processing\nUse for: JavaScript code, bulk transformations, aggregations\nKey properties: functionCode, mode",
                "metadata": {
                    "node_type": "n8n-nodes-base.function",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 2
                }
            },
            {
                "nodeType": "n8n-nodes-base.wait",
                "displayName": "Wait",
                "description": "Pause workflow execution for a specific time or until a webhook",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resume": {"type": "options", "options": ["timeInterval", "specificTime", "webhook"], "default": "timeInterval"},
                    "amount": {"type": "number", "description": "Time amount"},
                    "unit": {"type": "options", "options": ["seconds", "minutes", "hours", "days"], "default": "seconds"},
                    "time": {"type": "dateTime", "description": "Specific time to resume"}
                },
                "documentation": "Add delays to workflows, rate limiting, scheduled resumption, wait for external events, and webhook-based continuation.",
                "examples": [
                    {"title": "Wait 30 seconds", "config": {"resume": "timeInterval", "amount": 30, "unit": "seconds"}},
                    {"title": "Wait until 9 AM", "config": {"resume": "specificTime", "time": "09:00:00"}},
                    {"title": "Wait for webhook", "config": {"resume": "webhook"}}
                ],
                "embedding_text": "Node: Wait\nType: n8n-nodes-base.wait\nCategory: transform\nDescription: Pause workflow execution for a specific time or until a webhook\nUse case: Delays, rate limiting, scheduling\nUse for: Wait time, pause execution, rate limiting\nKey properties: resume, amount, unit, time",
                "metadata": {
                    "node_type": "n8n-nodes-base.wait",
                    "category": "transform",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },

            # === AI & LLM NODES ===
            {
                "nodeType": "@n8n/n8n-nodes-langchain.agent",
                "displayName": "AI Agent",
                "description": "Create AI agents that can use tools and make decisions",
                "category": "transform",
                "package": "@n8n/n8n-nodes-langchain",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "agent": {"type": "options", "options": ["conversationalAgent", "openAiFunctionsAgent", "reActAgent"], "default": "conversationalAgent"},
                    "systemMessage": {"type": "string", "description": "System message for the agent"},
                    "maxIterations": {"type": "number", "default": 3, "description": "Maximum iterations"},
                    "returnIntermediateSteps": {"type": "boolean", "default": False, "description": "Return intermediate steps"},
                    "tools": {"type": "collection", "description": "Available tools for the agent"}
                },
                "documentation": "Create intelligent AI agents that can reason, use tools, and make decisions. Supports various agent types including conversational, function-calling, and ReAct agents.",
                "examples": [
                    {"title": "Research agent", "config": {"agent": "reActAgent", "systemMessage": "You are a research assistant. Use tools to find information.", "maxIterations": 5}},
                    {"title": "Function agent", "config": {"agent": "openAiFunctionsAgent", "systemMessage": "You can call functions to help users.", "tools": ["calculator", "search"]}}
                ]
            },
            {
                "nodeType": "@n8n/n8n-nodes-langchain.chatOpenAi",
                "displayName": "OpenAI Chat Model",
                "description": "Interact with OpenAI's chat models like GPT-4 and GPT-3.5",
                "category": "transform",
                "package": "@n8n/n8n-nodes-langchain",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "model": {"type": "options", "options": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"], "default": "gpt-4o"},
                    "temperature": {"type": "number", "default": 0.7, "description": "Sampling temperature"},
                    "maxTokens": {"type": "number", "description": "Maximum tokens to generate"},
                    "systemMessage": {"type": "string", "description": "System message"},
                    "humanMessage": {"type": "string", "description": "Human message"},
                    "frequencyPenalty": {"type": "number", "default": 0, "description": "Frequency penalty"},
                    "presencePenalty": {"type": "number", "default": 0, "description": "Presence penalty"}
                },
                "documentation": "Use OpenAI's powerful chat models for conversations, text generation, analysis, and AI-powered tasks with support for latest models.",
                "examples": [
                    {"title": "Generate text", "config": {"model": "gpt-4o", "humanMessage": "Write a summary of this data", "temperature": 0.3}},
                    {"title": "Chat completion", "config": {"model": "gpt-3.5-turbo", "systemMessage": "You are a helpful assistant", "humanMessage": "Hello!"}}
                ]
            },
            {
                "nodeType": "@n8n/n8n-nodes-langchain.openAi",
                "displayName": "OpenAI",
                "description": "Access OpenAI services including completions, embeddings, and vision",
                "category": "transform",
                "package": "@n8n/n8n-nodes-langchain",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["text", "image", "embedding", "audio"], "default": "text"},
                    "operation": {"type": "options", "options": ["complete", "analyze", "generate", "transcribe"], "default": "complete"},
                    "model": {"type": "string", "description": "Model to use"},
                    "prompt": {"type": "string", "description": "Input prompt"},
                    "temperature": {"type": "number", "default": 0.7},
                    "maxTokens": {"type": "number", "description": "Maximum tokens"}
                },
                "documentation": "Comprehensive OpenAI integration supporting text completion, image analysis, embeddings generation, and audio transcription.",
                "examples": [
                    {"title": "Text completion", "config": {"resource": "text", "operation": "complete", "prompt": "Complete this sentence:", "maxTokens": 100}},
                    {"title": "Image analysis", "config": {"resource": "image", "operation": "analyze", "prompt": "Describe this image"}}
                ]
            },
            {
                "nodeType": "@n8n/n8n-nodes-langchain.vectorStore",
                "displayName": "Vector Store",
                "description": "Store and search through vector embeddings for semantic search",
                "category": "transform",
                "package": "@n8n/n8n-nodes-langchain",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["insert", "retrieve", "update", "delete"], "default": "insert"},
                    "vectorStore": {"type": "options", "options": ["pinecone", "chroma", "qdrant", "weaviate"], "default": "pinecone"},
                    "query": {"type": "string", "description": "Search query"},
                    "topK": {"type": "number", "default": 5, "description": "Number of results to return"},
                    "documents": {"type": "collection", "description": "Documents to insert"},
                    "metadata": {"type": "json", "description": "Document metadata"}
                },
                "documentation": "Manage vector databases for semantic search, RAG applications, and AI-powered document retrieval systems.",
                "examples": [
                    {"title": "Insert documents", "config": {"operation": "insert", "vectorStore": "pinecone", "documents": ["Document 1", "Document 2"]}},
                    {"title": "Search similar", "config": {"operation": "retrieve", "query": "Find similar documents", "topK": 3}}
                ]
            },
            {
                "nodeType": "@n8n/n8n-nodes-langchain.embeddings",
                "displayName": "Embeddings",
                "description": "Generate text embeddings for semantic search and AI applications",
                "category": "transform",
                "package": "@n8n/n8n-nodes-langchain",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "embeddings": {"type": "options", "options": ["openAiEmbeddings", "cohereEmbeddings", "huggingFaceEmbeddings"], "default": "openAiEmbeddings"},
                    "model": {"type": "string", "description": "Embedding model name"},
                    "text": {"type": "string", "description": "Text to embed"},
                    "documents": {"type": "collection", "description": "Multiple documents to embed"},
                    "chunkSize": {"type": "number", "default": 1000, "description": "Chunk size for large texts"}
                },
                "documentation": "Generate high-quality vector embeddings from text for semantic search, similarity matching, and AI applications.",
                "examples": [
                    {"title": "Generate embeddings", "config": {"embeddings": "openAiEmbeddings", "text": "This is sample text to embed"}},
                    {"title": "Batch embeddings", "config": {"embeddings": "openAiEmbeddings", "documents": ["Text 1", "Text 2", "Text 3"]}}
                ]
            },
            {
                "nodeType": "@n8n/n8n-nodes-langchain.memoryManager",
                "displayName": "Memory Manager",
                "description": "Manage conversation memory for AI agents and chatbots",
                "category": "transform",
                "package": "@n8n/n8n-nodes-langchain",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "memoryType": {"type": "options", "options": ["conversationBufferMemory", "conversationSummaryMemory", "vectorStoreRetrieverMemory"], "default": "conversationBufferMemory"},
                    "operation": {"type": "options", "options": ["save", "load", "clear"], "default": "save"},
                    "sessionId": {"type": "string", "description": "Session identifier"},
                    "input": {"type": "string", "description": "User input"},
                    "output": {"type": "string", "description": "AI output"},
                    "maxTokens": {"type": "number", "description": "Maximum memory tokens"}
                },
                "documentation": "Store and manage conversation history, context, and memory for AI agents to maintain coherent conversations.",
                "examples": [
                    {"title": "Save conversation", "config": {"memoryType": "conversationBufferMemory", "operation": "save", "sessionId": "user123", "input": "Hello", "output": "Hi there!"}},
                    {"title": "Load memory", "config": {"memoryType": "conversationSummaryMemory", "operation": "load", "sessionId": "user123"}}
                ]
            },
            {
                "nodeType": "@n8n/n8n-nodes-langchain.documentLoader",
                "displayName": "Document Loader",
                "description": "Load and parse documents from various sources for AI processing",
                "category": "transform",
                "package": "@n8n/n8n-nodes-langchain",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "loader": {"type": "options", "options": ["textLoader", "csvLoader", "pdfLoader", "webLoader", "jsonLoader"], "default": "textLoader"},
                    "source": {"type": "string", "description": "Document source (URL, file path, etc.)"},
                    "options": {"type": "json", "description": "Loader-specific options"},
                    "encoding": {"type": "string", "default": "utf-8", "description": "Text encoding"},
                    "splitChunks": {"type": "boolean", "default": False, "description": "Split into chunks"}
                },
                "documentation": "Load documents from files, URLs, and databases for AI processing, RAG applications, and document analysis.",
                "examples": [
                    {"title": "Load PDF", "config": {"loader": "pdfLoader", "source": "/path/to/document.pdf", "splitChunks": True}},
                    {"title": "Load webpage", "config": {"loader": "webLoader", "source": "https://example.com/article", "splitChunks": True}}
                ]
            },

            # === CORE TRANSFORM NODES ===
            {
                "nodeType": "n8n-nodes-base.httpRequest",
                "displayName": "HTTP Request",
                "description": "Makes HTTP requests to any API or web service",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "method": {"type": "options", "options": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"], "default": "GET"},
                    "url": {"type": "string", "required": True, "description": "Request URL"},
                    "authentication": {"type": "options", "options": ["None", "Basic Auth", "Header Auth", "OAuth2"], "default": "None"},
                    "headers": {"type": "fixedCollection", "description": "Request headers"},
                    "body": {"type": "string", "description": "Request body"}
                },
                "documentation": "Make HTTP requests to APIs, webhooks, and web services. Supports all HTTP methods, authentication, and custom headers.",
                "examples": [
                    {"title": "GET API data", "config": {"method": "GET", "url": "https://api.example.com/users"}},
                    {"title": "POST JSON data", "config": {"method": "POST", "url": "https://api.example.com/users", "body": "{\"name\": \"John\"}"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.code",
                "displayName": "Code",
                "description": "Execute custom JavaScript code for data transformation",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "mode": {"type": "options", "options": ["runOnceForAllItems", "runOnceForEachItem"], "default": "runOnceForAllItems"},
                    "jsCode": {"type": "string", "required": True, "description": "JavaScript code to execute"}
                },
                "documentation": "Run custom JavaScript code to transform data, perform calculations, and implement custom logic.",
                "examples": [
                    {"title": "Transform data", "config": {"jsCode": "return items.map(item => ({...item.json, processed: true}))"}},
                    {"title": "Filter items", "config": {"jsCode": "return items.filter(item => item.json.status === 'active')"}}
                ]
            },

            # === PRODUCTIVITY & CRM NODES ===
            {
                "nodeType": "n8n-nodes-base.notion",
                "displayName": "Notion", 
                "description": "Create, read, and update Notion pages and databases",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["page", "database", "user"], "default": "page"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll", "update"], "default": "create"},
                    "databaseId": {"type": "string", "description": "Database ID"},
                    "properties": {"type": "fixedCollection", "description": "Page properties"}
                },
                "documentation": "Integrate with Notion to manage pages, databases, and collaborate on documentation and project management.",
                "examples": [
                    {"title": "Create page", "config": {"resource": "page", "operation": "create", "title": "New Task"}},
                    {"title": "Query database", "config": {"resource": "database", "operation": "getAll", "databaseId": "abc123"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.airtable",
                "displayName": "Airtable",
                "description": "Create, read, update and delete records in Airtable",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["append", "list", "read", "update", "delete"], "default": "append"},
                    "application": {"type": "string", "required": True, "description": "Application ID"},
                    "table": {"type": "string", "required": True, "description": "Table name"},
                    "fields": {"type": "fixedCollection", "description": "Record fields"}
                },
                "documentation": "Manage Airtable databases with full CRUD operations, perfect for CRM, project management, and data organization.",
                "examples": [
                    {"title": "Add record", "config": {"operation": "append", "fields": {"Name": "John Doe", "Email": "john@example.com"}}},
                    {"title": "Update record", "config": {"operation": "update", "id": "rec123", "fields": {"Status": "Complete"}}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.trello",
                "displayName": "Trello",
                "description": "Create and manage Trello boards, lists, and cards",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["board", "card", "list"], "default": "card"},
                    "operation": {"type": "options", "options": ["create", "delete", "get", "getAll", "update"], "default": "create"},
                    "boardId": {"type": "string", "description": "Board ID"},
                    "listId": {"type": "string", "description": "List ID"},
                    "name": {"type": "string", "description": "Card/Board name"}
                },
                "documentation": "Integrate with Trello for project management, task tracking, and team collaboration workflows.",
                "examples": [
                    {"title": "Create card", "config": {"resource": "card", "operation": "create", "name": "New Task", "listId": "list123"}},
                    {"title": "Move card", "config": {"resource": "card", "operation": "update", "listId": "list456"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.asana",
                "displayName": "Asana",
                "description": "Manage Asana projects, tasks, and team collaboration",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["task", "project", "user"], "default": "task"},
                    "operation": {"type": "options", "options": ["create", "delete", "get", "getAll", "update"], "default": "create"},
                    "projectId": {"type": "string", "description": "Project ID"},
                    "name": {"type": "string", "required": True, "description": "Task name"},
                    "notes": {"type": "string", "description": "Task description"}
                },
                "documentation": "Create and manage Asana tasks, projects, and workflows for team productivity and project tracking.",
                "examples": [
                    {"title": "Create task", "config": {"resource": "task", "operation": "create", "name": "Review Document", "projectId": "proj123"}},
                    {"title": "Update task", "config": {"resource": "task", "operation": "update", "completed": True}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.todoist",
                "displayName": "Todoist",
                "description": "Create and manage Todoist tasks and projects",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["task", "project"], "default": "task"},
                    "operation": {"type": "options", "options": ["create", "close", "delete", "get", "getAll", "reopen", "update"], "default": "create"},
                    "content": {"type": "string", "required": True, "description": "Task content"},
                    "projectId": {"type": "string", "description": "Project ID"},
                    "priority": {"type": "options", "options": [1, 2, 3, 4], "default": 1}
                },
                "documentation": "Integrate with Todoist for personal task management and productivity workflows.",
                "examples": [
                    {"title": "Create task", "config": {"resource": "task", "operation": "create", "content": "Buy groceries", "priority": 2}},
                    {"title": "Complete task", "config": {"resource": "task", "operation": "close", "id": "task123"}}
                ]
            },

            # === DEVELOPER & AUTOMATION NODES ===
            {
                "nodeType": "n8n-nodes-base.github",
                "displayName": "GitHub",
                "description": "Manage GitHub repositories, issues, and pull requests",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["file", "issue", "organization", "release", "repository", "user"], "default": "issue"},
                    "operation": {"type": "options", "options": ["create", "createComment", "edit", "get", "getAll"], "default": "create"},
                    "owner": {"type": "string", "required": True, "description": "Repository owner"},
                    "repository": {"type": "string", "required": True, "description": "Repository name"},
                    "title": {"type": "string", "description": "Issue/PR title"},
                    "body": {"type": "string", "description": "Issue/PR body"}
                },
                "documentation": "Automate GitHub workflows including repository management, issue tracking, and code collaboration.",
                "examples": [
                    {"title": "Create issue", "config": {"resource": "issue", "operation": "create", "title": "Bug Report", "body": "Found a bug in the code"}},
                    {"title": "Create release", "config": {"resource": "release", "operation": "create", "tag": "v1.0.0", "name": "Release 1.0.0"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.gitlab",
                "displayName": "GitLab",
                "description": "Manage GitLab repositories, issues, and merge requests",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["issue", "repository", "release", "user"], "default": "issue"},
                    "operation": {"type": "options", "options": ["create", "delete", "edit", "get", "getAll"], "default": "create"},
                    "projectId": {"type": "string", "required": True, "description": "Project ID"},
                    "title": {"type": "string", "description": "Issue title"},
                    "description": {"type": "string", "description": "Issue description"}
                },
                "documentation": "Integrate with GitLab for repository management, CI/CD automation, and project collaboration.",
                "examples": [
                    {"title": "Create issue", "config": {"resource": "issue", "operation": "create", "title": "Feature Request", "description": "Add new feature"}},
                    {"title": "Get repository", "config": {"resource": "repository", "operation": "get", "projectId": "123"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.jira",
                "displayName": "Jira",
                "description": "Manage Jira issues, projects, and workflows",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["issue", "issueComment", "project", "user"], "default": "issue"},
                    "operation": {"type": "options", "options": ["create", "delete", "get", "getAll", "changelog", "notify", "transition", "update"], "default": "create"},
                    "project": {"type": "string", "description": "Project key"},
                    "issueType": {"type": "string", "description": "Issue type"},
                    "summary": {"type": "string", "required": True, "description": "Issue summary"}
                },
                "documentation": "Create and manage Jira issues, track project progress, and automate development workflows.",
                "examples": [
                    {"title": "Create bug", "config": {"resource": "issue", "operation": "create", "project": "DEV", "issueType": "Bug", "summary": "Fix login issue"}},
                    {"title": "Transition issue", "config": {"resource": "issue", "operation": "transition", "status": "In Progress"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.jenkins",
                "displayName": "Jenkins",
                "description": "Trigger Jenkins builds and manage CI/CD pipelines",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["build", "getBuild", "getJobs"], "default": "build"},
                    "job": {"type": "string", "required": True, "description": "Job name"},
                    "parameters": {"type": "fixedCollection", "description": "Build parameters"}
                },
                "documentation": "Trigger Jenkins builds, manage CI/CD pipelines, and automate deployment workflows.",
                "examples": [
                    {"title": "Trigger build", "config": {"operation": "build", "job": "deploy-production"}},
                    {"title": "Build with params", "config": {"operation": "build", "job": "test-suite", "parameters": {"branch": "main", "environment": "staging"}}}
                ]
            },

            # === SOCIAL MEDIA & MARKETING NODES ===
            {
                "nodeType": "n8n-nodes-base.twitter",
                "displayName": "X (Twitter)",
                "description": "Post tweets, manage Twitter account, and track mentions",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["tweet", "directMessage"], "default": "tweet"},
                    "operation": {"type": "options", "options": ["create", "delete", "like", "retweet", "search"], "default": "create"},
                    "text": {"type": "string", "required": True, "description": "Tweet text"},
                    "attachments": {"type": "string", "description": "Media attachments"}
                },
                "documentation": "Automate Twitter/X posting, engage with followers, and manage social media presence.",
                "examples": [
                    {"title": "Post tweet", "config": {"resource": "tweet", "operation": "create", "text": "Hello from n8n automation!"}},
                    {"title": "Search tweets", "config": {"resource": "tweet", "operation": "search", "query": "#automation"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.linkedin",
                "displayName": "LinkedIn",
                "description": "Share posts on LinkedIn and manage professional network",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["post", "company"], "default": "post"},
                    "operation": {"type": "options", "options": ["create", "getAll"], "default": "create"},
                    "text": {"type": "string", "required": True, "description": "Post content"},
                    "visibility": {"type": "options", "options": ["anyone", "connectionsOnly"], "default": "anyone"}
                },
                "documentation": "Share professional content on LinkedIn, manage company pages, and build business networks.",
                "examples": [
                    {"title": "Share post", "config": {"resource": "post", "operation": "create", "text": "Excited to share our latest project!"}},
                    {"title": "Company update", "config": {"resource": "company", "operation": "create", "text": "New product launch announcement"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.facebook",
                "displayName": "Facebook",
                "description": "Post to Facebook pages and manage social presence",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["post", "photo"], "default": "post"},
                    "operation": {"type": "options", "options": ["create"], "default": "create"},
                    "pageId": {"type": "string", "required": True, "description": "Facebook page ID"},
                    "message": {"type": "string", "required": True, "description": "Post message"}
                },
                "documentation": "Automate Facebook page posting and manage social media marketing campaigns.",
                "examples": [
                    {"title": "Post message", "config": {"resource": "post", "operation": "create", "message": "Check out our latest blog post!"}},
                    {"title": "Share photo", "config": {"resource": "photo", "operation": "create", "message": "Behind the scenes photo", "url": "https://example.com/photo.jpg"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.instagram",
                "displayName": "Instagram",
                "description": "Post photos and manage Instagram business account",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["post"], "default": "post"},
                    "operation": {"type": "options", "options": ["create"], "default": "create"},
                    "imageUrl": {"type": "string", "required": True, "description": "Image URL"},
                    "caption": {"type": "string", "description": "Post caption"},
                    "hashtags": {"type": "string", "description": "Hashtags"}
                },
                "documentation": "Automate Instagram posting for business accounts and manage visual social media presence.",
                "examples": [
                    {"title": "Post photo", "config": {"resource": "post", "operation": "create", "imageUrl": "https://example.com/image.jpg", "caption": "Beautiful sunset today!", "hashtags": "#nature #photography"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.youtube",
                "displayName": "YouTube",
                "description": "Upload videos and manage YouTube channel",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["video", "playlist"], "default": "video"},
                    "operation": {"type": "options", "options": ["upload", "get", "getAll", "update", "delete"], "default": "upload"},
                    "title": {"type": "string", "required": True, "description": "Video title"},
                    "description": {"type": "string", "description": "Video description"},
                    "tags": {"type": "string", "description": "Video tags"}
                },
                "documentation": "Upload videos to YouTube, manage channel content, and automate video publishing workflows.",
                "examples": [
                    {"title": "Upload video", "config": {"resource": "video", "operation": "upload", "title": "Tutorial: Getting Started", "description": "Learn the basics in this tutorial"}},
                    {"title": "Update video", "config": {"resource": "video", "operation": "update", "title": "Updated Tutorial Title"}}
                ]
            },

            # === E-COMMERCE & PAYMENT NODES ===
            {
                "nodeType": "n8n-nodes-base.shopify",
                "displayName": "Shopify",
                "description": "Manage Shopify store products, orders, and customers",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["customer", "order", "product"], "default": "product"},
                    "operation": {"type": "options", "options": ["create", "delete", "get", "getAll", "update"], "default": "create"},
                    "title": {"type": "string", "description": "Product title"},
                    "description": {"type": "string", "description": "Product description"},
                    "price": {"type": "number", "description": "Product price"}
                },
                "documentation": "Manage Shopify e-commerce operations including inventory, orders, and customer management.",
                "examples": [
                    {"title": "Create product", "config": {"resource": "product", "operation": "create", "title": "New T-Shirt", "price": 29.99}},
                    {"title": "Get orders", "config": {"resource": "order", "operation": "getAll", "status": "open"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.wooCommerce",
                "displayName": "WooCommerce",
                "description": "Manage WooCommerce store products, orders, and customers",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["customer", "order", "product"], "default": "product"},
                    "operation": {"type": "options", "options": ["create", "delete", "get", "getAll", "update"], "default": "create"},
                    "name": {"type": "string", "description": "Product name"},
                    "regularPrice": {"type": "string", "description": "Product price"},
                    "description": {"type": "string", "description": "Product description"}
                },
                "documentation": "Integrate with WooCommerce for WordPress e-commerce automation and store management.",
                "examples": [
                    {"title": "Add product", "config": {"resource": "product", "operation": "create", "name": "Premium Widget", "regularPrice": "49.99"}},
                    {"title": "Update order", "config": {"resource": "order", "operation": "update", "status": "completed"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.stripe",
                "displayName": "Stripe",
                "description": "Process payments and manage Stripe transactions",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["balance", "charge", "customer", "source", "token"], "default": "charge"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll", "update"], "default": "create"},
                    "amount": {"type": "number", "description": "Charge amount in cents"},
                    "currency": {"type": "string", "default": "usd", "description": "Currency code"}
                },
                "documentation": "Process payments, manage customers, and handle Stripe payment workflows and billing automation.",
                "examples": [
                    {"title": "Create charge", "config": {"resource": "charge", "operation": "create", "amount": 2000, "currency": "usd", "description": "Payment for service"}},
                    {"title": "Get customer", "config": {"resource": "customer", "operation": "get", "customerId": "cus_123"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.paypal",
                "displayName": "PayPal",
                "description": "Create and manage PayPal payments and invoices",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["payment", "payout"], "default": "payment"},
                    "operation": {"type": "options", "options": ["create", "execute", "get"], "default": "create"},
                    "amount": {"type": "number", "required": True, "description": "Payment amount"},
                    "currency": {"type": "string", "default": "USD", "description": "Currency code"}
                },
                "documentation": "Process PayPal payments, manage invoices, and handle online payment workflows.",
                "examples": [
                    {"title": "Create payment", "config": {"resource": "payment", "operation": "create", "amount": 50.00, "currency": "USD", "description": "Service payment"}},
                    {"title": "Execute payment", "config": {"resource": "payment", "operation": "execute", "paymentId": "PAY-123", "payerId": "payer123"}}
                ]
            },

            # === ADDITIONAL ESSENTIAL NODES ===
            {
                "nodeType": "n8n-nodes-base.dateTime",
                "displayName": "Date & Time",
                "description": "Parse, format, and manipulate dates and times",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "action": {"type": "options", "options": ["format", "calculate"], "default": "format"},
                    "value": {"type": "string", "description": "Date/time value"},
                    "format": {"type": "string", "description": "Output format"},
                    "timezone": {"type": "string", "description": "Timezone"}
                },
                "documentation": "Work with dates and times including formatting, timezone conversion, and date calculations.",
                "examples": [
                    {"title": "Format date", "config": {"action": "format", "value": "2023-12-25", "format": "YYYY-MM-DD"}},
                    {"title": "Add days", "config": {"action": "calculate", "operation": "add", "duration": 7, "unit": "days"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.crypto",
                "displayName": "Crypto",
                "description": "Hash data and perform cryptographic operations",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "action": {"type": "options", "options": ["hash", "hmac"], "default": "hash"},
                    "type": {"type": "options", "options": ["MD5", "SHA256", "SHA512"], "default": "SHA256"},
                    "value": {"type": "string", "required": True, "description": "Value to hash"}
                },
                "documentation": "Perform cryptographic operations including hashing, HMAC, and data verification.",
                "examples": [
                    {"title": "Hash password", "config": {"action": "hash", "type": "SHA256", "value": "mypassword"}},
                    {"title": "HMAC signature", "config": {"action": "hmac", "type": "SHA256", "value": "data", "key": "secretkey"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.html",
                "displayName": "HTML",
                "description": "Extract data from HTML using CSS selectors",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "mode": {"type": "options", "options": ["extract", "modify"], "default": "extract"},
                    "selector": {"type": "string", "description": "CSS selector"},
                    "attribute": {"type": "string", "description": "Attribute to extract"}
                },
                "documentation": "Extract data from HTML using CSS selectors, perfect for web scraping and content parsing.",
                "examples": [
                    {"title": "Extract titles", "config": {"mode": "extract", "selector": "h1", "attribute": "text"}},
                    {"title": "Get links", "config": {"mode": "extract", "selector": "a", "attribute": "href"}}
                ]
            },
            {
                "nodeType": "n8n-nodes-base.spreadsheetFile",
                "displayName": "Spreadsheet File",
                "description": "Read from and write to CSV and Excel files",
                "category": "transform",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["read", "write"], "default": "read"},
                    "fileFormat": {"type": "options", "options": ["csv", "html", "ods", "rtf", "xls", "xlsx"], "default": "csv"},
                    "options": {"type": "collection", "description": "File options"}
                },
                "documentation": "Process spreadsheet files including CSV and Excel formats for data import/export workflows.",
                "examples": [
                    {"title": "Read CSV", "config": {"operation": "read", "fileFormat": "csv"}},
                    {"title": "Write Excel", "config": {"operation": "write", "fileFormat": "xlsx"}}
                ]
            },
            # === CRM NODES ===
            {
                "nodeType": "n8n-nodes-base.salesforce",
                "displayName": "Salesforce",
                "description": "Manage Salesforce CRM records, leads, accounts, and opportunities",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["account", "lead", "contact", "opportunity", "case"], "default": "lead"},
                    "operation": {"type": "options", "options": ["create", "update", "get", "getAll", "delete"], "default": "create"},
                    "fields": {"type": "collection", "description": "Record fields to set"},
                    "additionalFields": {"type": "collection", "description": "Additional fields"}
                },
                "documentation": "Integrate with Salesforce CRM to manage customer relationships, track sales opportunities, and automate business processes. Supports all major Salesforce objects and operations.",
                "examples": [
                    {"title": "Create lead", "config": {"resource": "lead", "operation": "create", "fields": {"FirstName": "John", "LastName": "Doe", "Email": "john@example.com", "Company": "Acme Corp"}}},
                    {"title": "Update opportunity", "config": {"resource": "opportunity", "operation": "update", "id": "0061234567890", "fields": {"StageName": "Closed Won", "Amount": 10000}}},
                    {"title": "Get accounts", "config": {"resource": "account", "operation": "getAll", "returnAll": False, "limit": 100}}
                ],
                "embedding_text": "Node: Salesforce\nType: n8n-nodes-base.salesforce\nCategory: output\nDescription: Manage Salesforce CRM records, leads, accounts, and opportunities\nUse case: CRM management, sales automation\nUse for: Lead management, sales tracking, customer data\nKey properties: resource, operation, fields",
                "metadata": {
                    "node_type": "n8n-nodes-base.salesforce",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.hubspot",
                "displayName": "HubSpot",
                "description": "Manage HubSpot CRM contacts, deals, companies, and marketing automation",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["contact", "deal", "company", "ticket", "form"], "default": "contact"},
                    "operation": {"type": "options", "options": ["create", "update", "get", "getAll", "delete"], "default": "create"},
                    "properties": {"type": "collection", "description": "Object properties"},
                    "additionalFields": {"type": "collection", "description": "Additional fields"}
                },
                "documentation": "Integrate with HubSpot CRM and Marketing Hub to manage contacts, deals, and automate marketing workflows. Supports custom properties and advanced filtering.",
                "examples": [
                    {"title": "Create contact", "config": {"resource": "contact", "operation": "create", "properties": {"email": "contact@example.com", "firstname": "Jane", "lastname": "Smith"}}},
                    {"title": "Update deal", "config": {"resource": "deal", "operation": "update", "dealId": "123456", "properties": {"dealstage": "closedwon", "amount": "5000"}}},
                    {"title": "Get companies", "config": {"resource": "company", "operation": "getAll", "returnAll": False, "limit": 50}}
                ],
                "embedding_text": "Node: HubSpot\nType: n8n-nodes-base.hubspot\nCategory: output\nDescription: Manage HubSpot CRM contacts, deals, companies, and marketing automation\nUse case: CRM management, marketing automation\nUse for: Contact management, deal tracking, marketing workflows\nKey properties: resource, operation, properties",
                "metadata": {
                    "node_type": "n8n-nodes-base.hubspot",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.pipedrive",
                "displayName": "Pipedrive",
                "description": "Manage Pipedrive CRM deals, contacts, and sales pipeline",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["deal", "person", "organization", "activity"], "default": "deal"},
                    "operation": {"type": "options", "options": ["create", "update", "get", "getAll", "delete"], "default": "create"},
                    "fields": {"type": "collection", "description": "Fields to set"}
                },
                "documentation": "Manage Pipedrive sales pipeline with deal tracking, contact management, and activity scheduling for sales teams.",
                "examples": [
                    {"title": "Create deal", "config": {"resource": "deal", "operation": "create", "fields": {"title": "New Sale", "value": 1500, "currency": "USD"}}},
                    {"title": "Add person", "config": {"resource": "person", "operation": "create", "fields": {"name": "John Doe", "email": "john@example.com"}}}
                ],
                "embedding_text": "Node: Pipedrive\nType: n8n-nodes-base.pipedrive\nCategory: output\nDescription: Manage Pipedrive CRM deals, contacts, and sales pipeline\nUse case: Sales pipeline management\nUse for: Deal tracking, contact management, sales automation\nKey properties: resource, operation, fields",
                "metadata": {
                    "node_type": "n8n-nodes-base.pipedrive",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 3
                }
            },
            # === PRODUCTIVITY NODES ===
            {
                "nodeType": "n8n-nodes-base.obsidian",
                "displayName": "Obsidian",
                "description": "Create and manage Obsidian vault notes and knowledge graphs",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["create", "update", "get", "search"], "default": "create"},
                    "noteName": {"type": "string", "required": True, "description": "Note name"},
                    "content": {"type": "string", "description": "Note content in Markdown"},
                    "folder": {"type": "string", "description": "Folder path in vault"},
                    "tags": {"type": "string", "description": "Comma-separated tags"}
                },
                "documentation": "Integrate with Obsidian knowledge management system to create, update, and organize notes with automatic linking and tagging.",
                "examples": [
                    {"title": "Create note", "config": {"operation": "create", "noteName": "Meeting Notes", "content": "# Meeting with Client\n\n- Discussed requirements\n- Next steps: [[Action Items]]", "tags": "meeting,client"}},
                    {"title": "Search notes", "config": {"operation": "search", "query": "project management", "folder": "Work"}}
                ],
                "embedding_text": "Node: Obsidian\nType: n8n-nodes-base.obsidian\nCategory: output\nDescription: Create and manage Obsidian vault notes and knowledge graphs\nUse case: Knowledge management, note-taking\nUse for: Documentation, linking notes, personal knowledge base\nKey properties: operation, noteName, content",
                "metadata": {
                    "node_type": "n8n-nodes-base.obsidian",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.todoist",
                "displayName": "Todoist",
                "description": "Manage Todoist tasks, projects, and productivity workflows",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["task", "project", "label"], "default": "task"},
                    "operation": {"type": "options", "options": ["create", "update", "get", "getAll", "delete", "close"], "default": "create"},
                    "content": {"type": "string", "required": True, "description": "Task content"},
                    "project": {"type": "string", "description": "Project name or ID"},
                    "dueDate": {"type": "string", "description": "Due date"},
                    "priority": {"type": "options", "options": [1, 2, 3, 4], "default": 1}
                },
                "documentation": "Automate task management with Todoist integration for creating tasks, managing projects, and tracking productivity.",
                "examples": [
                    {"title": "Create task", "config": {"resource": "task", "operation": "create", "content": "Review project proposal", "dueDate": "tomorrow", "priority": 3}},
                    {"title": "Create project", "config": {"resource": "project", "operation": "create", "name": "Website Redesign", "color": "blue"}}
                ],
                "embedding_text": "Node: Todoist\nType: n8n-nodes-base.todoist\nCategory: output\nDescription: Manage Todoist tasks, projects, and productivity workflows\nUse case: Task management, productivity\nUse for: Creating tasks, project management, workflow automation\nKey properties: resource, operation, content",
                "metadata": {
                    "node_type": "n8n-nodes-base.todoist",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 6
                }
            },
            {
                "nodeType": "n8n-nodes-base.asana",
                "displayName": "Asana",
                "description": "Manage Asana projects, tasks, and team collaboration",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["task", "project", "user", "team"], "default": "task"},
                    "operation": {"type": "options", "options": ["create", "update", "get", "getAll", "delete"], "default": "create"},
                    "name": {"type": "string", "required": True, "description": "Task or project name"},
                    "notes": {"type": "string", "description": "Description or notes"},
                    "assignee": {"type": "string", "description": "Assignee user ID"},
                    "dueDate": {"type": "dateTime", "description": "Due date"}
                },
                "documentation": "Integrate with Asana for project management, task tracking, and team collaboration workflows.",
                "examples": [
                    {"title": "Create task", "config": {"resource": "task", "operation": "create", "name": "Design homepage mockup", "notes": "Create wireframe and visual design", "dueDate": "2024-02-15"}},
                    {"title": "Create project", "config": {"resource": "project", "operation": "create", "name": "Q1 Marketing Campaign", "notes": "Launch new product campaign"}}
                ],
                "embedding_text": "Node: Asana\nType: n8n-nodes-base.asana\nCategory: output\nDescription: Manage Asana projects, tasks, and team collaboration\nUse case: Project management, team collaboration\nUse for: Task tracking, project planning, team workflows\nKey properties: resource, operation, name",
                "metadata": {
                    "node_type": "n8n-nodes-base.asana",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 6
                }
            },
            # === CLOUD SERVICES ===
            {
                "nodeType": "n8n-nodes-base.azureBlobStorage",
                "displayName": "Azure Blob Storage",
                "description": "Store and retrieve files from Microsoft Azure Blob Storage",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["upload", "download", "delete", "getAll"], "default": "upload"},
                    "containerName": {"type": "string", "required": True, "description": "Storage container name"},
                    "blobName": {"type": "string", "required": True, "description": "Blob name"},
                    "data": {"type": "string", "description": "File data to upload"}
                },
                "documentation": "Manage files in Microsoft Azure Blob Storage for cloud file storage, backup, and content distribution.",
                "examples": [
                    {"title": "Upload file", "config": {"operation": "upload", "containerName": "documents", "blobName": "report.pdf", "data": "file content"}},
                    {"title": "Download file", "config": {"operation": "download", "containerName": "backups", "blobName": "database.sql"}}
                ],
                "embedding_text": "Node: Azure Blob Storage\nType: n8n-nodes-base.azureBlobStorage\nCategory: output\nDescription: Store and retrieve files from Microsoft Azure Blob Storage\nUse case: Cloud file storage, backup\nUse for: File upload/download, cloud storage, backup automation\nKey properties: operation, containerName, blobName",
                "metadata": {
                    "node_type": "n8n-nodes-base.azureBlobStorage",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.googleCloudStorage",
                "displayName": "Google Cloud Storage",
                "description": "Store and manage files in Google Cloud Storage buckets",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["upload", "download", "delete", "list"], "default": "upload"},
                    "bucketName": {"type": "string", "required": True, "description": "Storage bucket name"},
                    "fileName": {"type": "string", "required": True, "description": "File name"},
                    "data": {"type": "string", "description": "File data"}
                },
                "documentation": "Manage files in Google Cloud Storage for scalable object storage, data archiving, and content delivery.",
                "examples": [
                    {"title": "Upload file", "config": {"operation": "upload", "bucketName": "my-bucket", "fileName": "data.json", "data": "file content"}},
                    {"title": "List files", "config": {"operation": "list", "bucketName": "my-bucket", "prefix": "uploads/"}}
                ],
                "embedding_text": "Node: Google Cloud Storage\nType: n8n-nodes-base.googleCloudStorage\nCategory: output\nDescription: Store and manage files in Google Cloud Storage buckets\nUse case: Cloud object storage, data archiving\nUse for: File management, backup, content delivery\nKey properties: operation, bucketName, fileName",
                "metadata": {
                    "node_type": "n8n-nodes-base.googleCloudStorage",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            # === ADDITIONAL COMMUNICATION NODES ===
            {
                "nodeType": "n8n-nodes-base.signal",
                "displayName": "Signal",
                "description": "Send encrypted messages via Signal messenger for secure communication",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["send"], "default": "send"},
                    "to": {"type": "string", "required": True, "description": "Recipient phone number"},
                    "message": {"type": "string", "required": True, "description": "Message text"},
                    "attachment": {"type": "string", "description": "File attachment"}
                },
                "documentation": "Send secure, encrypted messages through Signal for privacy-focused communication workflows.",
                "examples": [
                    {"title": "Send alert", "config": {"operation": "send", "to": "+1234567890", "message": "System alert: Server down"}},
                    {"title": "Send with attachment", "config": {"operation": "send", "to": "+1234567890", "message": "Report attached", "attachment": "report.pdf"}}
                ],
                "embedding_text": "Node: Signal\nType: n8n-nodes-base.signal\nCategory: output\nDescription: Send encrypted messages via Signal messenger for secure communication\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Secure messaging, encrypted communication, privacy alerts\nCommon tasks: Send secure notifications, encrypted alerts, privacy-focused messaging\nConnects well with: Monitoring systems, security tools, privacy-focused workflows\nComplexity: Beginner-friendly, simple configuration\nKey properties: operation, to, message, attachment\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.signal",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.matrix",
                "displayName": "Matrix",
                "description": "Send messages to Matrix rooms for decentralized team communication",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["send", "create", "join"], "default": "send"},
                    "roomId": {"type": "string", "required": True, "description": "Matrix room ID"},
                    "message": {"type": "string", "required": True, "description": "Message content"},
                    "messageType": {"type": "options", "options": ["text", "html", "notice"], "default": "text"}
                },
                "documentation": "Integrate with Matrix protocol for decentralized, federated team communication and notifications.",
                "examples": [
                    {"title": "Send to room", "config": {"operation": "send", "roomId": "!room:matrix.org", "message": "Build completed successfully"}},
                    {"title": "Send HTML message", "config": {"operation": "send", "roomId": "!alerts:company.com", "message": "<strong>Alert:</strong> Server issue detected", "messageType": "html"}}
                ],
                "embedding_text": "Node: Matrix\nType: n8n-nodes-base.matrix\nCategory: output\nDescription: Send messages to Matrix rooms for decentralized team communication\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Matrix protocol messaging, decentralized communication, federated chat\nCommon tasks: Room notifications, decentralized alerts, federated messaging\nConnects well with: Open source tools, self-hosted systems, privacy-focused workflows\nComplexity: Intermediate, moderate setup required\nKey properties: operation, roomId, message, messageType\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.matrix",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.mattermost",
                "displayName": "Mattermost",
                "description": "Send messages and manage Mattermost team collaboration platform",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["message", "channel", "user"], "default": "message"},
                    "operation": {"type": "options", "options": ["post", "get", "create"], "default": "post"},
                    "channelId": {"type": "string", "required": True, "description": "Channel ID"},
                    "message": {"type": "string", "required": True, "description": "Message text"},
                    "username": {"type": "string", "description": "Custom username"}
                },
                "documentation": "Integrate with Mattermost for team communication, DevOps notifications, and collaborative workflows.",
                "examples": [
                    {"title": "Post to channel", "config": {"resource": "message", "operation": "post", "channelId": "general", "message": "Deployment completed"}},
                    {"title": "DevOps alert", "config": {"resource": "message", "operation": "post", "channelId": "alerts", "message": "Build failed: Check logs", "username": "CI Bot"}}
                ],
                "embedding_text": "Node: Mattermost\nType: n8n-nodes-base.mattermost\nCategory: output\nDescription: Send messages and manage Mattermost team collaboration platform\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Mattermost team communication, DevOps notifications, collaborative workflows\nCommon tasks: Team notifications, DevOps alerts, collaboration messaging\nConnects well with: CI/CD tools, monitoring systems, development workflows\nComplexity: Intermediate, moderate setup required\nKey properties: resource, operation, channelId, message, username\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.mattermost",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.rocketChat",
                "displayName": "Rocket.Chat",
                "description": "Send messages and manage Rocket.Chat team communication platform",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["post", "get", "create"], "default": "post"},
                    "channel": {"type": "string", "required": True, "description": "Channel name"},
                    "text": {"type": "string", "required": True, "description": "Message text"},
                    "alias": {"type": "string", "description": "Bot alias"},
                    "emoji": {"type": "string", "description": "Bot emoji"}
                },
                "documentation": "Integrate with Rocket.Chat for team messaging, customer support, and organizational communication.",
                "examples": [
                    {"title": "Team notification", "config": {"operation": "post", "channel": "#general", "text": "New release v2.1.0 is live!"}},
                    {"title": "Support alert", "config": {"operation": "post", "channel": "#support", "text": "High priority ticket created", "alias": "Support Bot", "emoji": ":warning:"}}
                ],
                "embedding_text": "Node: Rocket.Chat\nType: n8n-nodes-base.rocketChat\nCategory: output\nDescription: Send messages and manage Rocket.Chat team communication platform\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Rocket.Chat messaging, team communication, customer support\nCommon tasks: Team notifications, support alerts, organizational messaging\nConnects well with: Customer support tools, team workflows, notification systems\nComplexity: Beginner-friendly, simple configuration\nKey properties: operation, channel, text, alias, emoji\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.rocketChat",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            # === ADDITIONAL DATABASE NODES ===
            {
                "nodeType": "n8n-nodes-base.influxdb",
                "displayName": "InfluxDB",
                "description": "Store and query time-series data in InfluxDB for metrics and monitoring",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["write", "query"], "default": "write"},
                    "database": {"type": "string", "required": True, "description": "Database name"},
                    "measurement": {"type": "string", "required": True, "description": "Measurement name"},
                    "fields": {"type": "collection", "description": "Fields to write"},
                    "tags": {"type": "collection", "description": "Tags to associate"}
                },
                "documentation": "Store time-series data for IoT sensors, application metrics, and monitoring dashboards using InfluxDB.",
                "examples": [
                    {"title": "Write metrics", "config": {"operation": "write", "database": "metrics", "measurement": "cpu_usage", "fields": {"value": 85.2}, "tags": {"host": "server1"}}},
                    {"title": "Query data", "config": {"operation": "query", "database": "sensors", "query": "SELECT * FROM temperature WHERE time > now() - 1h"}}
                ],
                "embedding_text": "Node: InfluxDB\nType: n8n-nodes-base.influxdb\nCategory: output\nDescription: Store and query time-series data in InfluxDB for metrics and monitoring\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Time-series database operations, metrics storage, IoT data\nCommon tasks: Store sensor data, write metrics, query time-series, monitoring dashboards\nConnects well with: IoT sensors, monitoring tools, analytics dashboards, alerting systems\nComplexity: Intermediate, moderate setup required\nKey properties: operation, database, measurement, fields, tags\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.influxdb",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.timescaledb",
                "displayName": "TimescaleDB",
                "description": "Store and analyze time-series data using PostgreSQL-compatible TimescaleDB",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["insert", "query", "aggregate"], "default": "insert"},
                    "table": {"type": "string", "required": True, "description": "Hypertable name"},
                    "timeColumn": {"type": "string", "default": "time", "description": "Time column name"},
                    "data": {"type": "json", "description": "Data to insert"},
                    "query": {"type": "string", "description": "SQL query"}
                },
                "documentation": "Leverage TimescaleDB for high-performance time-series analytics with full SQL support and PostgreSQL compatibility.",
                "examples": [
                    {"title": "Insert sensor data", "config": {"operation": "insert", "table": "sensor_data", "data": {"time": "2024-01-15T10:00:00Z", "sensor_id": "temp_01", "value": 23.5}}},
                    {"title": "Time-bucket aggregation", "config": {"operation": "query", "query": "SELECT time_bucket('1 hour', time) as bucket, avg(value) FROM sensor_data GROUP BY bucket"}}
                ],
                "embedding_text": "Node: TimescaleDB\nType: n8n-nodes-base.timescaledb\nCategory: output\nDescription: Store and analyze time-series data using PostgreSQL-compatible TimescaleDB\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Time-series database operations, PostgreSQL time-series, analytics\nCommon tasks: Insert time-series data, run analytics queries, time-bucket aggregations\nConnects well with: PostgreSQL tools, analytics platforms, monitoring systems, dashboards\nComplexity: Advanced, detailed configuration options\nKey properties: operation, table, timeColumn, data, query\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.timescaledb",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.couchdb",
                "displayName": "CouchDB",
                "description": "Store and sync documents using Apache CouchDB NoSQL database",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["create", "get", "update", "delete", "find"], "default": "create"},
                    "database": {"type": "string", "required": True, "description": "Database name"},
                    "documentId": {"type": "string", "description": "Document ID"},
                    "document": {"type": "json", "description": "Document data"},
                    "selector": {"type": "json", "description": "Query selector"}
                },
                "documentation": "Manage documents in CouchDB with built-in replication, offline-first capabilities, and HTTP API integration.",
                "examples": [
                    {"title": "Create document", "config": {"operation": "create", "database": "users", "document": {"name": "John Doe", "email": "john@example.com", "role": "admin"}}},
                    {"title": "Find documents", "config": {"operation": "find", "database": "orders", "selector": {"status": "pending", "created_date": {"$gt": "2024-01-01"}}}}
                ],
                "embedding_text": "Node: CouchDB\nType: n8n-nodes-base.couchdb\nCategory: output\nDescription: Store and sync documents using Apache CouchDB NoSQL database\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: CouchDB document storage, NoSQL operations, offline-first applications\nCommon tasks: Create documents, query data, sync databases, replicate data\nConnects well with: Mobile apps, offline applications, replication systems, web APIs\nComplexity: Intermediate, moderate setup required\nKey properties: operation, database, documentId, document, selector\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.couchdb",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.neo4j",
                "displayName": "Neo4j",
                "description": "Query and manage graph data using Neo4j graph database",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["run", "create", "match", "merge"], "default": "run"},
                    "cypher": {"type": "string", "required": True, "description": "Cypher query"},
                    "parameters": {"type": "json", "description": "Query parameters"},
                    "database": {"type": "string", "default": "neo4j", "description": "Database name"}
                },
                "documentation": "Execute Cypher queries on Neo4j for relationship analysis, social networks, recommendation engines, and knowledge graphs.",
                "examples": [
                    {"title": "Create relationship", "config": {"operation": "run", "cypher": "CREATE (p:Person {name: $name})-[:KNOWS]->(f:Person {name: $friend})", "parameters": {"name": "Alice", "friend": "Bob"}}},
                    {"title": "Find connections", "config": {"operation": "run", "cypher": "MATCH (p:Person)-[:KNOWS*1..3]-(connected) WHERE p.name = $name RETURN connected.name", "parameters": {"name": "Alice"}}}
                ],
                "embedding_text": "Node: Neo4j\nType: n8n-nodes-base.neo4j\nCategory: output\nDescription: Query and manage graph data using Neo4j graph database\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Graph database operations, relationship analysis, knowledge graphs\nCommon tasks: Run Cypher queries, create nodes, find relationships, graph analytics\nConnects well with: Social networks, recommendation engines, fraud detection, knowledge systems\nComplexity: Advanced, detailed configuration options\nKey properties: operation, cypher, parameters, database\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.neo4j",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.elasticsearch",
                "displayName": "Elasticsearch",
                "description": "Search, index, and analyze data using Elasticsearch search engine",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["index", "search", "get", "delete", "bulk"], "default": "index"},
                    "index": {"type": "string", "required": True, "description": "Index name"},
                    "documentId": {"type": "string", "description": "Document ID"},
                    "body": {"type": "json", "description": "Request body"},
                    "query": {"type": "json", "description": "Search query"}
                },
                "documentation": "Index documents and perform full-text search using Elasticsearch for log analysis, search applications, and data analytics.",
                "examples": [
                    {"title": "Index document", "config": {"operation": "index", "index": "products", "body": {"name": "Laptop", "price": 999, "category": "Electronics"}}},
                    {"title": "Search products", "config": {"operation": "search", "index": "products", "query": {"match": {"category": "Electronics"}}}}
                ],
                "embedding_text": "Node: Elasticsearch\nType: n8n-nodes-base.elasticsearch\nCategory: output\nDescription: Search, index, and analyze data using Elasticsearch search engine\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Full-text search, document indexing, log analysis, search applications\nCommon tasks: Index documents, search data, analyze logs, build search features\nConnects well with: Log collectors, search interfaces, analytics dashboards, monitoring systems\nComplexity: Advanced, detailed configuration options\nKey properties: operation, index, documentId, body, query\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.elasticsearch",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            # === ADDITIONAL CLOUD SERVICES ===
            {
                "nodeType": "n8n-nodes-base.awsLambda",
                "displayName": "AWS Lambda",
                "description": "Invoke AWS Lambda functions for serverless computing and event processing",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["invoke"], "default": "invoke"},
                    "functionName": {"type": "string", "required": True, "description": "Lambda function name"},
                    "payload": {"type": "json", "description": "Function payload"},
                    "invocationType": {"type": "options", "options": ["RequestResponse", "Event", "DryRun"], "default": "RequestResponse"}
                },
                "documentation": "Execute serverless functions on AWS Lambda for scalable, event-driven computing and microservices architecture.",
                "examples": [
                    {"title": "Process data", "config": {"operation": "invoke", "functionName": "process-user-data", "payload": {"userId": "12345", "action": "update"}}},
                    {"title": "Async processing", "config": {"operation": "invoke", "functionName": "send-notifications", "invocationType": "Event", "payload": {"message": "Alert", "recipients": ["user1", "user2"]}}}
                ],
                "embedding_text": "Node: AWS Lambda\nType: n8n-nodes-base.awsLambda\nCategory: output\nDescription: Invoke AWS Lambda functions for serverless computing and event processing\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Serverless functions, event processing, microservices, scalable computing\nCommon tasks: Process data, trigger functions, event-driven workflows, serverless automation\nConnects well with: AWS services, event systems, microservices, data processing pipelines\nComplexity: Intermediate, moderate setup required\nKey properties: operation, functionName, payload, invocationType\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.awsLambda",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.awsSqs",
                "displayName": "AWS SQS",
                "description": "Send and receive messages using Amazon Simple Queue Service",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["send", "receive", "delete"], "default": "send"},
                    "queueUrl": {"type": "string", "required": True, "description": "SQS queue URL"},
                    "messageBody": {"type": "string", "description": "Message content"},
                    "delaySeconds": {"type": "number", "default": 0, "description": "Delivery delay"},
                    "messageAttributes": {"type": "collection", "description": "Message attributes"}
                },
                "documentation": "Implement reliable message queuing with AWS SQS for decoupled application components and asynchronous processing.",
                "examples": [
                    {"title": "Send order", "config": {"operation": "send", "queueUrl": "https://sqs.region.amazonaws.com/account/orders", "messageBody": "{\"orderId\": \"12345\", \"status\": \"pending\"}"}},
                    {"title": "Delayed processing", "config": {"operation": "send", "queueUrl": "https://sqs.region.amazonaws.com/account/tasks", "messageBody": "Process later", "delaySeconds": 300}}
                ],
                "embedding_text": "Node: AWS SQS\nType: n8n-nodes-base.awsSqs\nCategory: output\nDescription: Send and receive messages using Amazon Simple Queue Service\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Message queuing, asynchronous processing, decoupled systems, reliable messaging\nCommon tasks: Queue messages, async processing, decouple components, reliable delivery\nConnects well with: AWS Lambda, microservices, event-driven systems, batch processing\nComplexity: Intermediate, moderate setup required\nKey properties: operation, queueUrl, messageBody, delaySeconds, messageAttributes\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.awsSqs",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.azureFunctions",
                "displayName": "Azure Functions",
                "description": "Execute serverless functions on Microsoft Azure platform",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["invoke"], "default": "invoke"},
                    "functionUrl": {"type": "string", "required": True, "description": "Azure Function URL"},
                    "httpMethod": {"type": "options", "options": ["GET", "POST", "PUT", "DELETE"], "default": "POST"},
                    "body": {"type": "json", "description": "Request body"},
                    "headers": {"type": "collection", "description": "HTTP headers"}
                },
                "documentation": "Trigger Azure Functions for event-driven serverless computing, data processing, and integration workflows.",
                "examples": [
                    {"title": "Process data", "config": {"operation": "invoke", "functionUrl": "https://myapp.azurewebsites.net/api/process", "httpMethod": "POST", "body": {"data": "process this"}}},
                    {"title": "Get status", "config": {"operation": "invoke", "functionUrl": "https://myapp.azurewebsites.net/api/status", "httpMethod": "GET"}}
                ],
                "embedding_text": "Node: Azure Functions\nType: n8n-nodes-base.azureFunctions\nCategory: output\nDescription: Execute serverless functions on Microsoft Azure platform\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Azure serverless functions, event processing, cloud computing, integration\nCommon tasks: Execute functions, process events, integrate services, serverless workflows\nConnects well with: Azure services, Microsoft ecosystem, event systems, cloud workflows\nComplexity: Intermediate, moderate setup required\nKey properties: operation, functionUrl, httpMethod, body, headers\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.azureFunctions",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.googleBigQuery",
                "displayName": "Google BigQuery",
                "description": "Query and analyze large datasets using Google BigQuery data warehouse",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["query", "insert", "create"], "default": "query"},
                    "projectId": {"type": "string", "required": True, "description": "GCP Project ID"},
                    "datasetId": {"type": "string", "required": True, "description": "Dataset ID"},
                    "query": {"type": "string", "description": "SQL query"},
                    "tableId": {"type": "string", "description": "Table ID"},
                    "data": {"type": "json", "description": "Data to insert"}
                },
                "documentation": "Analyze petabyte-scale data with Google BigQuery for business intelligence, data analytics, and machine learning workflows.",
                "examples": [
                    {"title": "Analytics query", "config": {"operation": "query", "projectId": "my-project", "query": "SELECT product, SUM(sales) as total_sales FROM `dataset.sales` GROUP BY product ORDER BY total_sales DESC"}},
                    {"title": "Insert data", "config": {"operation": "insert", "projectId": "my-project", "datasetId": "analytics", "tableId": "events", "data": [{"user_id": "123", "event": "click", "timestamp": "2024-01-15T10:00:00Z"}]}}
                ],
                "embedding_text": "Node: Google BigQuery\nType: n8n-nodes-base.googleBigQuery\nCategory: output\nDescription: Query and analyze large datasets using Google BigQuery data warehouse\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Big data analytics, data warehouse queries, business intelligence, ML data prep\nCommon tasks: Run analytics queries, insert data, create tables, data analysis\nConnects well with: Data pipelines, analytics tools, ML platforms, reporting dashboards\nComplexity: Advanced, detailed configuration options\nKey properties: operation, projectId, datasetId, query, tableId, data\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.googleBigQuery",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 6
                }
            },
            {
                "nodeType": "n8n-nodes-base.googlePubSub",
                "displayName": "Google Pub/Sub",
                "description": "Publish and subscribe to messages using Google Cloud Pub/Sub messaging service",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["publish", "pull"], "default": "publish"},
                    "projectId": {"type": "string", "required": True, "description": "GCP Project ID"},
                    "topicName": {"type": "string", "required": True, "description": "Topic name"},
                    "message": {"type": "string", "description": "Message data"},
                    "attributes": {"type": "collection", "description": "Message attributes"}
                },
                "documentation": "Build event-driven systems with Google Pub/Sub for real-time messaging, stream processing, and microservices communication.",
                "examples": [
                    {"title": "Publish event", "config": {"operation": "publish", "projectId": "my-project", "topicName": "user-events", "message": "{\"userId\": \"123\", \"action\": \"login\"}", "attributes": {"source": "web"}}},
                    {"title": "System notification", "config": {"operation": "publish", "projectId": "my-project", "topicName": "alerts", "message": "System maintenance scheduled", "attributes": {"priority": "high"}}}
                ],
                "embedding_text": "Node: Google Pub/Sub\nType: n8n-nodes-base.googlePubSub\nCategory: output\nDescription: Publish and subscribe to messages using Google Cloud Pub/Sub messaging service\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Event-driven messaging, stream processing, microservices communication, real-time data\nCommon tasks: Publish events, stream processing, async messaging, event notifications\nConnects well with: Microservices, event systems, stream processing, real-time applications\nComplexity: Intermediate, moderate setup required\nKey properties: operation, projectId, topicName, message, attributes\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.googlePubSub",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            # === ADDITIONAL SOCIAL MEDIA NODES ===
            {
                "nodeType": "n8n-nodes-base.tiktok",
                "displayName": "TikTok",
                "description": "Manage TikTok content and business account for social media marketing",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["video", "user", "analytics"], "default": "video"},
                    "operation": {"type": "options", "options": ["get", "getAll", "upload"], "default": "get"},
                    "videoId": {"type": "string", "description": "Video ID"},
                    "caption": {"type": "string", "description": "Video caption"},
                    "hashtags": {"type": "string", "description": "Hashtags"}
                },
                "documentation": "Integrate with TikTok for Business to manage content, analyze performance, and automate social media workflows.",
                "examples": [
                    {"title": "Get video analytics", "config": {"resource": "analytics", "operation": "get", "videoId": "7123456789"}},
                    {"title": "Get trending videos", "config": {"resource": "video", "operation": "getAll", "hashtags": "#trending"}}
                ],
                "embedding_text": "Node: TikTok\nType: n8n-nodes-base.tiktok\nCategory: output\nDescription: Manage TikTok content and business account for social media marketing\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: TikTok content management, social media marketing, video analytics\nCommon tasks: Get video analytics, manage content, track performance, social media automation\nConnects well with: Social media tools, analytics platforms, content management, marketing automation\nComplexity: Intermediate, moderate setup required\nKey properties: resource, operation, videoId, caption, hashtags\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.tiktok",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.youtube",
                "displayName": "YouTube",
                "description": "Upload videos and manage YouTube channel content and analytics",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["video", "playlist", "channel", "comment"], "default": "video"},
                    "operation": {"type": "options", "options": ["upload", "get", "getAll", "update"], "default": "upload"},
                    "title": {"type": "string", "required": True, "description": "Video title"},
                    "description": {"type": "string", "description": "Video description"},
                    "tags": {"type": "string", "description": "Video tags"},
                    "privacy": {"type": "options", "options": ["public", "unlisted", "private"], "default": "public"}
                },
                "documentation": "Automate YouTube content management, video uploads, and channel analytics for content creators and businesses.",
                "examples": [
                    {"title": "Upload video", "config": {"resource": "video", "operation": "upload", "title": "Tutorial: Getting Started", "description": "Learn the basics", "tags": "tutorial,education", "privacy": "public"}},
                    {"title": "Get channel stats", "config": {"resource": "channel", "operation": "get", "channelId": "UCxxxxx"}}
                ],
                "embedding_text": "Node: YouTube\nType: n8n-nodes-base.youtube\nCategory: output\nDescription: Upload videos and manage YouTube channel content and analytics\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: YouTube content management, video uploads, channel analytics, content automation\nCommon tasks: Upload videos, manage playlists, get analytics, automate publishing\nConnects well with: Content creation tools, analytics platforms, social media management, video processing\nComplexity: Intermediate, moderate setup required\nKey properties: resource, operation, title, description, tags, privacy\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.youtube",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 6
                }
            },
            {
                "nodeType": "n8n-nodes-base.pinterest",
                "displayName": "Pinterest",
                "description": "Create pins and manage Pinterest boards for visual marketing",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["pin", "board", "user"], "default": "pin"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll", "update"], "default": "create"},
                    "boardId": {"type": "string", "required": True, "description": "Board ID"},
                    "imageUrl": {"type": "string", "description": "Pin image URL"},
                    "title": {"type": "string", "description": "Pin title"},
                    "description": {"type": "string", "description": "Pin description"}
                },
                "documentation": "Automate Pinterest marketing with pin creation, board management, and visual content distribution workflows.",
                "examples": [
                    {"title": "Create pin", "config": {"resource": "pin", "operation": "create", "boardId": "12345", "imageUrl": "https://example.com/image.jpg", "title": "Recipe Ideas", "description": "Delicious recipes for dinner"}},
                    {"title": "Get board pins", "config": {"resource": "pin", "operation": "getAll", "boardId": "67890"}}
                ],
                "embedding_text": "Node: Pinterest\nType: n8n-nodes-base.pinterest\nCategory: output\nDescription: Create pins and manage Pinterest boards for visual marketing\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Pinterest marketing, visual content, board management, pin automation\nCommon tasks: Create pins, manage boards, visual marketing, content distribution\nConnects well with: Image processing, e-commerce, marketing tools, content management\nComplexity: Intermediate, moderate setup required\nKey properties: resource, operation, boardId, imageUrl, title, description\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.pinterest",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 6
                }
            },
            {
                "nodeType": "n8n-nodes-base.reddit",
                "displayName": "Reddit",
                "description": "Fetch posts, interact with Reddit communities, and manage subreddit content",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["post", "comment", "subreddit"], "default": "post"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll", "fetch"], "default": "getAll"},
                    "subreddit": {"type": "string", "required": True, "description": "Subreddit name (e.g., 'Startups', 'programming')"},
                    "sort": {"type": "options", "options": ["hot", "new", "top", "rising"], "default": "new", "description": "Sort order for posts"},
                    "limit": {"type": "number", "default": 25, "description": "Number of posts to fetch"},
                    "title": {"type": "string", "description": "Post title (for creating posts)"},
                    "text": {"type": "string", "description": "Post content (for creating posts)"},
                    "url": {"type": "string", "description": "Link URL (for creating posts)"}
                },
                "documentation": "Fetch Reddit posts, engage with communities through posting, comment management, and subreddit monitoring for content discovery and community management.",
                "examples": [
                    {"title": "Fetch new posts from subreddit", "config": {"resource": "post", "operation": "getAll", "subreddit": "Startups", "sort": "new", "limit": 10}},
                    {"title": "Get hot posts", "config": {"resource": "post", "operation": "getAll", "subreddit": "programming", "sort": "hot", "limit": 25}},
                    {"title": "Create text post", "config": {"resource": "post", "operation": "create", "subreddit": "programming", "title": "New Tool Release", "text": "Check out our new development tool"}},
                    {"title": "Share link", "config": {"resource": "post", "operation": "create", "subreddit": "technology", "title": "Interesting Article", "url": "https://example.com/article"}}
                ],
                "embedding_text": "Node: Reddit\nType: n8n-nodes-base.reddit\nCategory: output\nDescription: Fetch posts, interact with Reddit communities, and manage subreddit content\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Reddit data fetching, community engagement, content posting, subreddit monitoring\nCommon tasks: Fetch new posts, get hot posts, create posts, monitor subreddits, community engagement, content discovery\nConnects well with: Content analysis tools, social monitoring, marketing automation, data processing\nComplexity: Intermediate, moderate setup required\nKey properties: resource, operation, subreddit, sort, limit, title, text, url\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.reddit",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 8
                }
            },
            # === ADDITIONAL E-COMMERCE NODES ===
            {
                "nodeType": "n8n-nodes-base.woocommerce",
                "displayName": "WooCommerce",
                "description": "Manage WooCommerce store products, orders, and customers",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["product", "order", "customer"], "default": "product"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll", "update", "delete"], "default": "get"},
                    "productId": {"type": "string", "description": "Product ID"},
                    "orderId": {"type": "string", "description": "Order ID"},
                    "customerId": {"type": "string", "description": "Customer ID"}
                },
                "documentation": "Automate WooCommerce store management with product updates, order processing, and customer management workflows.",
                "examples": [
                    {"title": "Get order details", "config": {"resource": "order", "operation": "get", "orderId": "123"}},
                    {"title": "Update product stock", "config": {"resource": "product", "operation": "update", "productId": "456", "stock_quantity": 50}}
                ],
                "embedding_text": "Node: WooCommerce\nType: n8n-nodes-base.woocommerce\nCategory: output\nDescription: Manage WooCommerce store products, orders, and customers\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: WooCommerce e-commerce, store management, order processing, inventory\nCommon tasks: Manage products, process orders, update inventory, customer management\nConnects well with: Payment systems, inventory management, email marketing, analytics\nComplexity: Intermediate, moderate setup required\nKey properties: resource, operation, productId, orderId, customerId\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.woocommerce",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.magento",
                "displayName": "Magento",
                "description": "Manage Magento e-commerce platform products, orders, and customers",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["product", "order", "customer", "category"], "default": "product"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll", "update", "delete"], "default": "get"},
                    "sku": {"type": "string", "description": "Product SKU"},
                    "orderId": {"type": "string", "description": "Order ID"},
                    "customerId": {"type": "string", "description": "Customer ID"}
                },
                "documentation": "Integrate with Magento for enterprise e-commerce automation including product management, order fulfillment, and customer operations.",
                "examples": [
                    {"title": "Get product by SKU", "config": {"resource": "product", "operation": "get", "sku": "LAPTOP-001"}},
                    {"title": "Update order status", "config": {"resource": "order", "operation": "update", "orderId": "1000123", "status": "shipped"}}
                ],
                "embedding_text": "Node: Magento\nType: n8n-nodes-base.magento\nCategory: output\nDescription: Manage Magento e-commerce platform products, orders, and customers\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Magento e-commerce, enterprise retail, product management, order fulfillment\nCommon tasks: Product catalog management, order processing, customer operations, inventory sync\nConnects well with: ERP systems, payment gateways, shipping providers, business intelligence\nComplexity: Advanced, detailed configuration options\nKey properties: resource, operation, sku, orderId, customerId\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.magento",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.bigcommerce",
                "displayName": "BigCommerce",
                "description": "Manage BigCommerce store products, orders, and customer data",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["product", "order", "customer", "category"], "default": "product"},
                    "operation": {"type": "options", "options": ["create", "get", "getAll", "update", "delete"], "default": "get"},
                    "productId": {"type": "number", "description": "Product ID"},
                    "orderId": {"type": "number", "description": "Order ID"},
                    "customerId": {"type": "number", "description": "Customer ID"}
                },
                "documentation": "Automate BigCommerce operations with product management, order processing, and customer relationship workflows for growing businesses.",
                "examples": [
                    {"title": "List products", "config": {"resource": "product", "operation": "getAll", "limit": 50}},
                    {"title": "Create customer", "config": {"resource": "customer", "operation": "create", "first_name": "John", "last_name": "Doe", "email": "john@example.com"}}
                ],
                "embedding_text": "Node: BigCommerce\nType: n8n-nodes-base.bigcommerce\nCategory: output\nDescription: Manage BigCommerce store products, orders, and customer data\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: BigCommerce e-commerce, online store management, product operations\nCommon tasks: Product management, order fulfillment, customer operations, store automation\nConnects well with: Marketing tools, payment processors, shipping services, analytics platforms\nComplexity: Intermediate, moderate setup required\nKey properties: resource, operation, productId, orderId, customerId\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.bigcommerce",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            # === ADDITIONAL DEVELOPER TOOLS ===
            {
                "nodeType": "n8n-nodes-base.jenkins",
                "displayName": "Jenkins",
                "description": "Trigger Jenkins builds and manage CI/CD pipeline automation",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["build", "getBuild", "getBuilds"], "default": "build"},
                    "jobName": {"type": "string", "required": True, "description": "Jenkins job name"},
                    "buildNumber": {"type": "number", "description": "Build number"},
                    "parameters": {"type": "collection", "description": "Build parameters"}
                },
                "documentation": "Automate Jenkins CI/CD pipelines with build triggers, status monitoring, and deployment automation workflows.",
                "examples": [
                    {"title": "Trigger build", "config": {"operation": "build", "jobName": "deploy-production", "parameters": {"BRANCH": "main", "ENVIRONMENT": "prod"}}},
                    {"title": "Get build status", "config": {"operation": "getBuild", "jobName": "test-pipeline", "buildNumber": 123}}
                ],
                "embedding_text": "Node: Jenkins\nType: n8n-nodes-base.jenkins\nCategory: output\nDescription: Trigger Jenkins builds and manage CI/CD pipeline automation\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: CI/CD automation, build management, deployment pipelines, DevOps workflows\nCommon tasks: Trigger builds, monitor deployments, automate releases, pipeline management\nConnects well with: Version control, testing tools, deployment platforms, notification systems\nComplexity: Intermediate, moderate setup required\nKey properties: operation, jobName, buildNumber, parameters\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.jenkins",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            },
            {
                "nodeType": "n8n-nodes-base.docker",
                "displayName": "Docker",
                "description": "Manage Docker containers, images, and containerization workflows",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["container", "image"], "default": "container"},
                    "operation": {"type": "options", "options": ["start", "stop", "create", "remove", "list"], "default": "start"},
                    "containerName": {"type": "string", "description": "Container name"},
                    "imageName": {"type": "string", "description": "Docker image name"},
                    "ports": {"type": "collection", "description": "Port mappings"}
                },
                "documentation": "Automate Docker container lifecycle management, image operations, and containerized application deployments.",
                "examples": [
                    {"title": "Start container", "config": {"resource": "container", "operation": "start", "containerName": "web-app"}},
                    {"title": "Create container", "config": {"resource": "container", "operation": "create", "imageName": "nginx:latest", "containerName": "web-server", "ports": [{"host": 8080, "container": 80}]}}
                ],
                "embedding_text": "Node: Docker\nType: n8n-nodes-base.docker\nCategory: output\nDescription: Manage Docker containers, images, and containerization workflows\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Container management, Docker operations, containerized deployments, DevOps automation\nCommon tasks: Start/stop containers, manage images, container lifecycle, deployment automation\nConnects well with: Kubernetes, CI/CD tools, monitoring systems, orchestration platforms\nComplexity: Advanced, detailed configuration options\nKey properties: resource, operation, containerName, imageName, ports\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.docker",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.kubernetes",
                "displayName": "Kubernetes",
                "description": "Deploy and manage applications on Kubernetes clusters",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "resource": {"type": "options", "options": ["pod", "deployment", "service", "configmap"], "default": "deployment"},
                    "operation": {"type": "options", "options": ["create", "get", "update", "delete", "list"], "default": "get"},
                    "namespace": {"type": "string", "default": "default", "description": "Kubernetes namespace"},
                    "name": {"type": "string", "required": True, "description": "Resource name"},
                    "manifest": {"type": "json", "description": "Kubernetes manifest"}
                },
                "documentation": "Orchestrate containerized applications with Kubernetes for scalable, resilient deployments and cluster management.",
                "examples": [
                    {"title": "Get deployment", "config": {"resource": "deployment", "operation": "get", "namespace": "production", "name": "web-app"}},
                    {"title": "Scale deployment", "config": {"resource": "deployment", "operation": "update", "name": "api-server", "manifest": {"spec": {"replicas": 5}}}}
                ],
                "embedding_text": "Node: Kubernetes\nType: n8n-nodes-base.kubernetes\nCategory: output\nDescription: Deploy and manage applications on Kubernetes clusters\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: Container orchestration, Kubernetes management, cluster operations, microservices deployment\nCommon tasks: Deploy applications, scale services, manage clusters, orchestrate containers\nConnects well with: Docker, CI/CD pipelines, monitoring tools, cloud platforms\nComplexity: Advanced, detailed configuration options\nKey properties: resource, operation, namespace, name, manifest\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.kubernetes",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 5
                }
            },
            {
                "nodeType": "n8n-nodes-base.circleci",
                "displayName": "CircleCI",
                "description": "Trigger CircleCI builds and manage continuous integration workflows",
                "category": "output",
                "package": "n8n-nodes-base",
                "isTrigger": False,
                "isAITool": True,
                "properties": {
                    "operation": {"type": "options", "options": ["trigger", "getWorkflow", "getPipeline"], "default": "trigger"},
                    "projectSlug": {"type": "string", "required": True, "description": "Project slug (vcs/org/repo)"},
                    "branch": {"type": "string", "default": "main", "description": "Git branch"},
                    "parameters": {"type": "collection", "description": "Pipeline parameters"}
                },
                "documentation": "Integrate with CircleCI for automated testing, building, and deployment workflows in modern CI/CD pipelines.",
                "examples": [
                    {"title": "Trigger pipeline", "config": {"operation": "trigger", "projectSlug": "github/myorg/myproject", "branch": "develop", "parameters": {"deploy_env": "staging"}}},
                    {"title": "Get workflow status", "config": {"operation": "getWorkflow", "workflowId": "12345-abcde"}}
                ],
                "embedding_text": "Node: CircleCI\nType: n8n-nodes-base.circleci\nCategory: output\nDescription: Trigger CircleCI builds and manage continuous integration workflows\nUse case: Processes data, performs actions\nWorkflow position: Action node, processes input, generates output\nUse for: CI/CD automation, build management, testing workflows, deployment automation\nCommon tasks: Trigger builds, monitor pipelines, automate testing, manage deployments\nConnects well with: Git repositories, testing frameworks, deployment tools, notification systems\nComplexity: Intermediate, moderate setup required\nKey properties: operation, projectSlug, branch, parameters\nSemantic group: Actions, Outputs, Data processors, Integration endpoints",
                "metadata": {
                    "node_type": "n8n-nodes-base.circleci",
                    "category": "output",
                    "is_trigger": False,
                    "is_ai_tool": True,
                    "has_examples": True,
                    "property_count": 4
                }
            }
        ]
    
    def extract_all_nodes(self) -> List[Dict[str, Any]]:
        """
        Extract comprehensive n8n node catalog with optimized performance
        """
        print("📚 Extracting comprehensive n8n node catalog...")
        
        # Get all nodes from our comprehensive database
        raw_nodes_data = self.get_all_n8n_nodes()
        
        # Deduplicate nodes based on nodeType
        seen_types = set()
        nodes_data = []
        for node in raw_nodes_data:
            node_type = node.get('nodeType', 'unknown')
            if node_type not in seen_types:
                nodes_data.append(node)
                seen_types.add(node_type)
            else:
                print(f"  ⚠️ Skipping duplicate node: {node_type}")
        
        print(f"🔄 Processing {len(nodes_data)} unique nodes with optimized performance...")
        
        # Check for already processed nodes (resume capability)
        processed_count = 0
        existing_files = set()
        if self.nodes_dir.exists():
            existing_files = {f.stem for f in self.nodes_dir.glob('*.json')}
            processed_count = len(existing_files)
        
        if processed_count > 0:
            print(f"  📂 Found {processed_count} existing node files, will skip if unchanged")
        
        # Process nodes in batches for better memory management
        batch_size = 50  # Process 50 nodes at a time
        processed_nodes = []
        failed_nodes = []
        
        for batch_start in tqdm(range(0, len(nodes_data), batch_size), 
                               desc="Processing batches", unit="batch"):
            batch_end = min(batch_start + batch_size, len(nodes_data))
            batch = nodes_data[batch_start:batch_end]
            
            batch_results = []
            
            # Process each node in the batch
            for i, node in enumerate(batch):
                try:
                    node_type = node.get('nodeType', 'unknown')
                    node_filename = node_type.replace('.', '_')
                    
                    # Skip if already processed and file exists
                    if node_filename in existing_files:
                        # Quick check if file is valid
                        node_file = self.nodes_dir / f"{node_filename}.json"
                        if node_file.exists() and node_file.stat().st_size > 100:  # Basic size check
                            continue
                    
                    # Enrich node data with additional fields
                    enriched_node = self._enrich_node_data(node)
                    batch_results.append(enriched_node)
                    
                    # Save individual node file
                    self._save_node_file(enriched_node)
                    
                except Exception as e:
                    failed_nodes.append({
                        'node_type': node.get('nodeType', 'unknown'),
                        'error': str(e)
                    })
                    print(f"  ❌ Failed to process node {node.get('nodeType', 'unknown')}: {str(e)[:100]}")
                    continue
            
            processed_nodes.extend(batch_results)
            
            # Memory cleanup after each batch
            import gc
            gc.collect()
        
        # Report results
        self.extracted_nodes = processed_nodes
        success_count = len(processed_nodes)
        total_count = len(nodes_data)
        failure_count = len(failed_nodes)
        
        print(f"✅ Node extraction complete:")
        print(f"  • Successfully processed: {success_count}/{total_count} nodes")
        if failure_count > 0:
            print(f"  • Failed nodes: {failure_count}")
            print(f"  • Error summary: {[f['node_type'] for f in failed_nodes[:5]]}")
        
        print(f"  • Memory optimization: Used batch processing with {batch_size} nodes per batch")
        print(f"  • Performance: Skipped {processed_count} existing files")
        
        return processed_nodes
    
    def _enrich_node_data(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich node data with additional metadata and enhanced descriptions"""
        # Add package info if not present
        if "package" not in node:
            node["package"] = "n8n-nodes-base"
        
        # Generate enhanced embedding text for better retrieval
        embedding_text = self._generate_embedding_text(node)
        node["embedding_text"] = embedding_text
        
        # Add metadata for categorization
        node["metadata"] = {
            "node_type": node["nodeType"],
            "category": node.get("category", "transform"),
            "is_trigger": node.get("isTrigger", False),
            "is_ai_tool": node.get("isAITool", False),
            "has_examples": len(node.get("examples", [])) > 0,
            "property_count": len(node.get("properties", {}))
        }
        
        return node
    
    def _generate_embedding_text(self, node: Dict[str, Any]) -> str:
        """Generate high-quality task-oriented embedding text for better retrieval"""
        node_name = node["displayName"]
        node_type = node["nodeType"]
        description = node["description"]
        category = node.get("category", "transform")
        
        # Create task-oriented embedding text
        embedding_parts = [
            f"Node: {node_name}",
            f"Type: {node_type}",
            f"Category: {category}",
            f"Description: {description}"
        ]
        
        # Add trigger/action context with specific workflow scenarios
        if node.get("isTrigger"):
            embedding_parts.append("Use case: Starts workflows, triggers automation")
            embedding_parts.append("Workflow position: First node, entry point, initiates process")
        else:
            embedding_parts.append("Use case: Processes data, performs actions")
            embedding_parts.append("Workflow position: Action node, processes input, generates output")
        
        # Add comprehensive service-specific use cases and task scenarios
        service_name = node_type.split(".")[-1].lower()
        
        # Communication & Messaging Services
        if "telegram" in service_name:
            embedding_parts.extend([
                "Use for: Send Telegram messages, Telegram bot, messaging",
                "Common tasks: Send notifications, bot responses, channel updates, group messaging",
                "Connects well with: Webhooks, HTTP requests, database queries, schedulers"
            ])
        elif "discord" in service_name:
            embedding_parts.extend([
                "Use for: Discord server management, gaming community notifications",
                "Common tasks: Server announcements, webhook notifications, bot commands",
                "Connects well with: Game APIs, monitoring systems, community tools"
            ])
        elif "slack" in service_name:
            embedding_parts.extend([
                "Use for: Slack notifications, team messaging, channel posts",
                "Common tasks: Team alerts, incident notifications, status updates, integrations",
                "Connects well with: Monitoring tools, CI/CD pipelines, support systems"
            ])
        elif "whatsapp" in service_name:
            embedding_parts.extend([
                "Use for: WhatsApp Business messaging, customer communication",
                "Common tasks: Customer support, appointment reminders, order updates",
                "Connects well with: CRM systems, booking platforms, e-commerce"
            ])
        
        # Database Services
        elif any(db in service_name for db in ["postgres", "mysql", "mongodb", "redis"]):
            db_type = next(db for db in ["postgres", "mysql", "mongodb", "redis"] if db in service_name)
            embedding_parts.extend([
                f"Use for: {db_type.title()} database operations, data storage, queries",
                "Common tasks: Insert records, update data, fetch information, data analysis",
                "Connects well with: APIs, web forms, data processing, analytics tools"
            ])
        
        # CRM Services  
        elif any(crm in service_name for crm in ["salesforce", "hubspot", "pipedrive"]):
            crm_type = next(crm for crm in ["salesforce", "hubspot", "pipedrive"] if crm in service_name)
            embedding_parts.extend([
                f"Use for: {crm_type.title()} CRM management, customer data, sales pipeline",
                "Common tasks: Create leads, update deals, manage contacts, track opportunities",
                "Connects well with: Web forms, email marketing, support tickets, analytics"
            ])
        
        # Email Services
        elif any(email in service_name for email in ["email", "gmail", "outlook"]):
            if "gmail" in service_name:
                embedding_parts.extend([
                    "Use for: Gmail sending, Gmail emails, Gmail integration, Gmail account, send via Gmail, Gmail notifications, Gmail API, Google Gmail service",
                    "Common tasks: Send Gmail messages, Gmail email automation, Gmail notifications, email Reddit posts via Gmail, Gmail alerts, Gmail integration workflows",
                    "Connects well with: Reddit, social media, webhooks, data processing, triggers, Google services, OAuth integrations",
                    "Gmail keywords: Gmail, Google email, Gmail account, Gmail API, Gmail service, Gmail integration, Gmail OAuth, send Gmail, Gmail notifications"
                ])
            elif "outlook" in service_name:
                embedding_parts.extend([
                    "Use for: Microsoft Outlook emails, Outlook integration, Office 365 emails",
                    "Common tasks: Outlook email sending, Microsoft email automation, Office 365 integration",
                    "Connects well with: Microsoft services, Office applications, enterprise workflows"
                ])
            else:
                embedding_parts.extend([
                    "Use for: SMTP email sending, custom SMTP server, generic email sending, SMTP configuration, non-Gmail email",
                    "Common tasks: SMTP email delivery, custom email server, email via SMTP protocol, HTML emails, email attachments",
                    "Connects well with: Custom servers, databases, forms, triggers, non-Google services",
                    "SMTP keywords: SMTP, email server, custom email, SMTP configuration, generic email, email protocol, SMTP host, SMTP port"
                ])
        
        # Social Media Services
        elif "reddit" in service_name:
            embedding_parts.extend([
                "Use for: Reddit data fetching, Reddit posts, Reddit API, subreddit data, Reddit content, fetch Reddit posts, Reddit integration, r/ subreddits",
                "Common tasks: Fetch Reddit posts from subreddits, get Reddit data, Reddit post monitoring, subreddit content retrieval, Reddit feed processing",
                "Connects well with: Email notifications, data processing, social media workflows, content aggregation, Gmail, Slack notifications",
                "Reddit keywords: Reddit, subreddit, r/, Reddit posts, Reddit data, Reddit API, Reddit feed, Reddit content, subreddit data, Reddit integration"
            ])
        elif "whatsapp" in service_name:
            embedding_parts.extend([
                "Use for: WhatsApp messaging, WhatsApp notifications, WhatsApp business communication, send WhatsApp messages, WhatsApp alerts",
                "Common tasks: Send WhatsApp messages, WhatsApp notifications, automated WhatsApp communication, business messaging",
                "Connects well with: Reddit, data processing, scheduling, social media workflows, customer communication",
                "WhatsApp keywords: WhatsApp, WhatsApp message, WhatsApp business, WA message, WhatsApp notification, WhatsApp integration"
            ])
        elif any(ai_term in service_name for ai_term in ["openai", "chatopenai", "gpt"]):
            embedding_parts.extend([
                "Use for: OpenAI integration, GPT processing, AI text generation, summarize content, summarise text, AI analysis, AI processing, LLM, language model, ChatGPT, GPT-4",
                "Common tasks: Summarize Reddit posts, AI text analysis, content generation, text summarization, intelligent text processing, GPT analysis, OpenAI summarization",
                "Connects well with: Reddit, data processing, content workflows, social media, email notifications, knowledge bases",
                "OpenAI keywords: OpenAI, GPT, ChatGPT, summarize, summarise, AI analysis, AI processing, LLM, language model, GPT-4, GPT-3.5, text generation"
            ])
        
        # Productivity & Project Management
        elif any(prod in service_name for prod in ["notion", "obsidian", "todoist", "asana", "trello"]):
            prod_type = next(prod for prod in ["notion", "obsidian", "todoist", "asana", "trello"] if prod in service_name)
            embedding_parts.extend([
                f"Use for: {prod_type.title()} task management, project organization, productivity",
                "Common tasks: Create tasks, update projects, manage deadlines, team collaboration",
                "Connects well with: Time tracking, calendars, team communication, reporting"
            ])
        
        # Cloud Storage & File Management
        elif any(cloud in service_name for cloud in ["googledrive", "dropbox", "s3", "azure", "googlecloud"]):
            embedding_parts.extend([
                "Use for: Cloud file storage, backup, document management",
                "Common tasks: Upload files, sync documents, backup data, share resources",
                "Connects well with: Document processing, image analysis, data pipelines"
            ])
        
        # Google Workspace Services
        elif "sheets" in service_name:
            embedding_parts.extend([
                "Use for: Spreadsheet data, Google Sheets, data analysis",
                "Common tasks: Update spreadsheets, read data, create reports, data validation",
                "Connects well with: Forms, databases, analytics, reporting dashboards"
            ])
        elif "calendar" in service_name:
            embedding_parts.extend([
                "Use for: Calendar management, scheduling, appointments",
                "Common tasks: Create events, schedule meetings, send invitations, manage availability",
                "Connects well with: Booking systems, CRM, email notifications, reminders"
            ])
        
        # E-commerce Services
        elif any(ecom in service_name for ecom in ["shopify", "stripe", "paypal"]):
            ecom_type = next(ecom for ecom in ["shopify", "stripe", "paypal"] if ecom in service_name)
            embedding_parts.extend([
                f"Use for: {ecom_type.title()} e-commerce, payments, online transactions",
                "Common tasks: Process orders, handle payments, manage inventory, customer data",
                "Connects well with: Email notifications, inventory systems, analytics, support"
            ])
        
        # Developer & Version Control
        elif any(dev in service_name for dev in ["github", "gitlab", "jira", "jenkins"]):
            dev_type = next(dev for dev in ["github", "gitlab", "jira", "jenkins"] if dev in service_name)
            embedding_parts.extend([
                f"Use for: {dev_type.title()} development workflows, code management, automation",
                "Common tasks: Repository management, issue tracking, CI/CD, deployment automation",
                "Connects well with: Code quality tools, monitoring, notifications, project management"
            ])
        
        # AI & ML Services
        elif any(ai in service_name for ai in ["openai", "chatgpt", "anthropic"]):
            embedding_parts.extend([
                "Use for: AI text generation, natural language processing, intelligent automation",
                "Common tasks: Content generation, text analysis, chatbots, data insights",
                "Connects well with: Knowledge bases, customer support, content management"
            ])
        
        # Add complexity and skill level indicators
        properties = node.get("properties", {})
        prop_count = len(properties)
        
        if prop_count <= 3:
            embedding_parts.append("Complexity: Beginner-friendly, simple configuration")
        elif prop_count <= 6:
            embedding_parts.append("Complexity: Intermediate, moderate setup required")
        else:
            embedding_parts.append("Complexity: Advanced, detailed configuration options")
        
        # Add key properties for technical users
        if properties:
            key_props = list(properties.keys())[:4]  # Top 4 most important properties
            embedding_parts.append(f"Key properties: {', '.join(key_props)}")
        
        # Add semantic categories for better grouping
        if node.get("isTrigger"):
            embedding_parts.append("Semantic group: Triggers, Starters, Event-driven, Automation initiators")
        elif category == "output":
            embedding_parts.append("Semantic group: Actions, Outputs, Data processors, Integration endpoints")
        elif category == "transform":
            embedding_parts.append("Semantic group: Transformers, Logic, Data manipulation, Flow control")
        
        return "\n".join(embedding_parts)
    
    def _save_node_file(self, node: Dict[str, Any]) -> None:
        """Save individual node data to file"""
        # Create safe filename from node type
        safe_filename = node['nodeType'].replace('.', '_').replace('/', '_').replace('@', '') + ".json"
        node_file = self.nodes_dir / safe_filename
        
        with open(node_file, 'w', encoding='utf-8') as f:
            json.dump(node, f, indent=2, ensure_ascii=False)
    
    def extract_workflow_templates(self) -> List[Dict[str, Any]]:
        """
        Extract workflow templates
        NOTE: In production, this would call the MCP tools
        """
        print("📋 Extracting workflow templates...")
        
        # Example template structure
        example_template = {
            "id": 1,
            "name": "Webhook to Slack Notification",
            "description": "Receive webhook data and send formatted message to Slack",
            "nodes": [
                {
                    "id": "webhook_1",
                    "type": "nodes-base.webhook",
                    "position": [250, 300],
                    "parameters": {
                        "httpMethod": "POST",
                        "path": "notification"
                    }
                },
                {
                    "id": "slack_1",
                    "type": "nodes-base.slack",
                    "position": [450, 300],
                    "parameters": {
                        "resource": "message",
                        "operation": "post",
                        "channel": "#notifications"
                    }
                }
            ],
            "connections": {
                "webhook_1": {
                    "main": [[{"node": "slack_1", "type": "main", "index": 0}]]
                }
            },
            "tags": ["webhook", "slack", "notification"]
        }
        
        templates = []
        
        # First, try to read existing template files from templates directory
        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob("*.json"):
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        # Ensure template has required fields
                        if "nodes" in template_data and "connections" in template_data:
                            templates.append(template_data)
                            print(f"  ✅ Loaded existing template: {template_file.name}")
                except Exception as e:
                    print(f"  ⚠️ Failed to load {template_file.name}: {e}")
        
        # If no templates found, use example template
        if not templates:
            print("  ⚠️ No template files found, creating example template")
            templates = [example_template]
        
        # Save templates (update existing or create new)
        for i, template in enumerate(templates):
            # Ensure template has ID
            if "id" not in template:
                template["id"] = i + 1
            
            template_file = self.templates_dir / f"template_{template['id']}.json"
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2)
                
        self.extracted_templates = templates
        print(f"✅ Extracted {len(templates)} workflow templates")
        return templates
    
    def create_embedding_chunks(self) -> List[Dict[str, Any]]:
        """Create chunks optimized for embedding and retrieval with intelligent splitting"""
        print("🔄 Creating intelligent embedding chunks with overlap...")
        chunks = []
        
        # Process nodes into intelligent chunks
        print(f"  📊 Processing {len(self.extracted_nodes)} nodes...")
        for node in tqdm(self.extracted_nodes, desc="Chunking nodes"):
            try:
                node_chunks = create_intelligent_node_chunks(
                    node=node,
                    chunker=self.chunker,
                    chunk_id_generator=self.generate_chunk_id
                )
                chunks.extend(node_chunks)
            except Exception as e:
                print(f"  ⚠️ Failed to chunk node {node.get('nodeType', 'unknown')}: {e}")
                continue
        
        # Process workflow templates into intelligent chunks
        print(f"  📊 Processing {len(self.extracted_templates)} workflow templates...")
        for template in tqdm(self.extracted_templates, desc="Chunking templates"):
            try:
                # Create unique identifier including name to avoid collisions
                unique_id = f"workflow_{template.get('id', 'unknown')}_{template.get('name', 'unnamed')}"
                
                # Create template content for chunking
                template_content = f"""
                Workflow Template: {template.get('name', 'Unnamed Template')}
                Description: {template.get('description', 'No description available')}
                Nodes Used: {', '.join([n.get('type', 'unknown') for n in template.get('nodes', [])])}
                Tags: {', '.join(template.get('tags', []))}
                Workflow Configuration: {json.dumps(template.get('connections', {}), indent=2)}
                """.strip()
                
                # Use intelligent chunking for large templates
                if len(template_content) > self.chunker.chunk_size:
                    template_chunks = self.chunker.create_overlapping_chunks(
                        content=template_content,
                        chunk_type="workflow_pattern",
                        base_id=self.generate_chunk_id(unique_id, "workflow"),
                        metadata={
                            "template_id": template.get('id', 'unknown'),
                            "node_count": len(template.get('nodes', [])),
                            "tags": template.get('tags', [])
                        }
                    )
                    chunks.extend(template_chunks)
                else:
                    # Single chunk for small templates
                    workflow_chunk = {
                        "chunk_id": self.generate_chunk_id(unique_id, "workflow"),
                        "chunk_type": "workflow_pattern",
                        "content": template_content,
                        "embedding_text": template_content,
                        "metadata": {
                            "template_id": template.get('id', 'unknown'),
                            "node_count": len(template.get('nodes', [])),
                            "tags": template.get('tags', [])
                        }
                    }
                    chunks.append(workflow_chunk)
                    
            except Exception as e:
                print(f"  ⚠️ Failed to chunk template {template.get('name', 'unknown')}: {e}")
                continue
        
        # Validate chunk sizes and quality
        print("🔍 Validating chunk quality...")
        validation_result = self.chunker.validate_chunk_sizes(chunks)
        
        if validation_result["status"] == "has_oversized":
            print(f"  ⚠️  {validation_result['stats']['oversized_count']} oversized chunks detected")
            print(f"  📊 Size compliance: {validation_result['stats']['size_compliance']:.1f}%")
        else:
            print(f"  ✅ All chunks within size limits")
        
        print(f"  📈 Chunk Statistics:")
        print(f"    • Total chunks: {validation_result['stats']['total_chunks']}")
        print(f"    • Average size: {validation_result['stats']['avg_size']:.0f} characters")
        print(f"    • Size range: {validation_result['stats']['min_size']}-{validation_result['stats']['max_size']} characters")
        
        # Save chunks
        chunks_file = self.chunks_dir / "all_chunks.json"
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2)
            
        # Save chunks by type for easier processing
        chunk_types = set(c.get('chunk_type', 'unknown') for c in chunks)
        for chunk_type in chunk_types:
            type_chunks = [c for c in chunks if c.get('chunk_type') == chunk_type]
            if type_chunks:
                type_file = self.chunks_dir / f"chunks_{chunk_type}.json"
                with open(type_file, 'w', encoding='utf-8') as f:
                    json.dump(type_chunks, f, indent=2)
        
        # Save chunk validation report
        validation_file = self.chunks_dir / "chunk_validation.json"
        with open(validation_file, 'w', encoding='utf-8') as f:
            json.dump(validation_result, f, indent=2)
        
        self.chunks = chunks
        print(f"✅ Created {len(chunks)} intelligent embedding chunks with overlap")
        return chunks
    
    def create_metadata_index(self) -> Dict[str, Any]:
        """Create metadata index for quick lookups"""
        print("📊 Creating metadata index...")
        
        metadata = {
            "extraction_date": datetime.now().isoformat(),
            "statistics": {
                "total_nodes": len(self.extracted_nodes),
                "total_templates": len(self.extracted_templates),
                "total_chunks": len(self.chunks),
                "chunks_by_type": {}
            },
            "node_index": {},
            "category_index": {},
            "trigger_nodes": [],
            "ai_tool_nodes": [],
            "connection_patterns": {}
        }
        
        # Count chunks by type
        for chunk in self.chunks:
            chunk_type = chunk.get('chunk_type', 'unknown')
            metadata['statistics']['chunks_by_type'][chunk_type] = \
                metadata['statistics']['chunks_by_type'].get(chunk_type, 0) + 1
        
        # Build node index
        for node in self.extracted_nodes:
            node_type = node['nodeType']
            metadata['node_index'][node_type] = {
                "display_name": node['displayName'],
                "category": node['category'],
                "is_trigger": node.get('isTrigger', False),
                "is_ai_tool": node.get('isAITool', False)
            }
            
            # Category index
            category = node['category']
            if category not in metadata['category_index']:
                metadata['category_index'][category] = []
            metadata['category_index'][category].append(node_type)
            
            # Special lists
            if node.get('isTrigger'):
                metadata['trigger_nodes'].append(node_type)
            if node.get('isAITool'):
                metadata['ai_tool_nodes'].append(node_type)
        
        # Analyze connection patterns from templates
        for template in self.extracted_templates:
            for source_node, connections in template.get('connections', {}).items():
                source_type = next((n['type'] for n in template['nodes'] if n['id'] == source_node), None)
                if source_type:
                    if source_type not in metadata['connection_patterns']:
                        metadata['connection_patterns'][source_type] = []
                    
                    for main_conn in connections.get('main', []):
                        for conn in main_conn:
                            target_node = conn.get('node')
                            target_type = next((n['type'] for n in template['nodes'] if n['id'] == target_node), None)
                            if target_type and target_type not in metadata['connection_patterns'][source_type]:
                                metadata['connection_patterns'][source_type].append(target_type)
        
        # Save metadata
        metadata_file = self.metadata_dir / "index.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Created metadata index")
        return metadata
    
    def run_extraction(self):
        """Run the complete extraction process"""
        print("\n🚀 Starting n8n Data Extraction for RAG System\n")
        print("=" * 50)
        
        # Step 1: Extract nodes
        self.extract_all_nodes()
        
        # Step 2: Extract templates
        self.extract_workflow_templates()
        
        # Step 3: Create embedding chunks
        self.create_embedding_chunks()
        
        # Step 4: Create metadata index
        metadata = self.create_metadata_index()
        
        # Summary
        print("\n" + "=" * 50)
        print("📈 Extraction Summary:")
        print(f"  • Nodes extracted: {metadata['statistics']['total_nodes']}")
        print(f"  • Templates extracted: {metadata['statistics']['total_templates']}")
        print(f"  • Chunks created: {metadata['statistics']['total_chunks']}")
        print(f"  • Trigger nodes: {len(metadata['trigger_nodes'])}")
        print(f"  • AI-capable nodes: {len(metadata['ai_tool_nodes'])}")
        print("\n📁 Output directory: " + str(self.output_dir))
        print("\n✨ Data extraction complete! Ready for vector indexing.\n")

if __name__ == "__main__":
    extractor = N8nDataExtractor()
    extractor.run_extraction()
