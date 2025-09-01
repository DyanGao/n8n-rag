"""
Phase 5: Feedback Loop System for n8n RAG
Learns from successful/failed generations to improve retrieval
"""

import json
import sqlite3
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import numpy as np
from collections import defaultdict

class FeedbackLoop:
    """Tracks generation success and updates retrieval weights"""
    
    def __init__(self, db_path: str = "./n8n_rag_feedback.db"):
        self.db_path = db_path
        self._init_database()
        
        # Weight adjustments
        self.success_weight_boost = 0.1
        self.failure_weight_penalty = 0.05
        
        # Cache for performance
        self.node_success_rates = {}
        self.pattern_effectiveness = {}
        
    def _init_database(self):
        """Initialize feedback database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Generation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                intent TEXT,
                complexity TEXT,
                required_nodes TEXT,
                retrieved_chunks TEXT,
                generated_workflow TEXT,
                success BOOLEAN,
                validation_errors TEXT,
                user_feedback INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Node effectiveness table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_effectiveness (
                node_type TEXT PRIMARY KEY,
                total_uses INTEGER DEFAULT 0,
                successful_uses INTEGER DEFAULT 0,
                avg_relevance_score REAL DEFAULT 0.5,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Pattern success table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_success (
                pattern_id TEXT PRIMARY KEY,
                pattern_description TEXT,
                total_uses INTEGER DEFAULT 0,
                successful_uses INTEGER DEFAULT 0,
                effectiveness_score REAL DEFAULT 0.5,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Query intent mappings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intent_mappings (
                query_pattern TEXT,
                detected_intent TEXT,
                actual_intent TEXT,
                correction_count INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_generation(
        self,
        query: str,
        context: Dict[str, Any],
        workflow: Optional[Dict],
        success: bool,
        validation_errors: List[str] = None,
        user_feedback: Optional[int] = None
    ):
        """Record a generation attempt for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Prepare data
        required_nodes = json.dumps(context.get("required_nodes", []))
        retrieved_chunks = json.dumps({
            "nodes": len(context.get("node_documentation", [])),
            "patterns": len(context.get("workflow_patterns", [])),
            "examples": len(context.get("examples", []))
        })
        
        # Insert generation record
        cursor.execute("""
            INSERT INTO generation_history 
            (query, intent, complexity, required_nodes, retrieved_chunks, 
             generated_workflow, success, validation_errors, user_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query,
            context.get("intent", "unknown"),
            context.get("complexity", "unknown"),
            required_nodes,
            retrieved_chunks,
            json.dumps(workflow) if workflow else None,
            success,
            json.dumps(validation_errors) if validation_errors else None,
            user_feedback
        ))
        
        # Update node effectiveness
        if success and workflow:
            self._update_node_effectiveness(context, success=True)
        elif not success:
            self._update_node_effectiveness(context, success=False)
        
        # Update pattern effectiveness
        self._update_pattern_effectiveness(context, success)
        
        conn.commit()
        conn.close()
        
        # Clear cache to force refresh
        self.node_success_rates = {}
        self.pattern_effectiveness = {}
    
    def _update_node_effectiveness(self, context: Dict, success: bool):
        """Update node effectiveness scores"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        nodes = context.get("required_nodes", [])
        
        for node_type in nodes:
            # Check if node exists in table
            cursor.execute(
                "SELECT total_uses, successful_uses FROM node_effectiveness WHERE node_type = ?",
                (node_type,)
            )
            result = cursor.fetchone()
            
            if result:
                total_uses, successful_uses = result
                total_uses += 1
                if success:
                    successful_uses += 1
                
                # Update effectiveness
                cursor.execute("""
                    UPDATE node_effectiveness 
                    SET total_uses = ?, successful_uses = ?, 
                        avg_relevance_score = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE node_type = ?
                """, (
                    total_uses,
                    successful_uses,
                    successful_uses / total_uses if total_uses > 0 else 0,
                    node_type
                ))
            else:
                # Insert new node
                cursor.execute("""
                    INSERT INTO node_effectiveness 
                    (node_type, total_uses, successful_uses, avg_relevance_score)
                    VALUES (?, 1, ?, ?)
                """, (
                    node_type,
                    1 if success else 0,
                    1.0 if success else 0.0
                ))
        
        conn.commit()
        conn.close()
    
    def _update_pattern_effectiveness(self, context: Dict, success: bool):
        """Update pattern effectiveness scores"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        patterns = context.get("workflow_patterns", [])
        
        for pattern in patterns:
            pattern_id = pattern.get("pattern", "unknown")
            
            cursor.execute(
                "SELECT total_uses, successful_uses FROM pattern_success WHERE pattern_id = ?",
                (pattern_id,)
            )
            result = cursor.fetchone()
            
            if result:
                total_uses, successful_uses = result
                total_uses += 1
                if success:
                    successful_uses += 1
                
                effectiveness = successful_uses / total_uses if total_uses > 0 else 0
                
                cursor.execute("""
                    UPDATE pattern_success 
                    SET total_uses = ?, successful_uses = ?, 
                        effectiveness_score = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE pattern_id = ?
                """, (total_uses, successful_uses, effectiveness, pattern_id))
            else:
                cursor.execute("""
                    INSERT INTO pattern_success 
                    (pattern_id, pattern_description, total_uses, successful_uses, effectiveness_score)
                    VALUES (?, ?, 1, ?, ?)
                """, (
                    pattern_id,
                    pattern.get("description", ""),
                    1 if success else 0,
                    1.0 if success else 0.0
                ))
        
        conn.commit()
        conn.close()
    
    def get_node_weights(self) -> Dict[str, float]:
        """Get learned weights for nodes"""
        if not self.node_success_rates:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT node_type, avg_relevance_score 
                FROM node_effectiveness
                WHERE total_uses > 0
            """)
            
            self.node_success_rates = {
                row[0]: row[1] for row in cursor.fetchall()
            }
            
            conn.close()
        
        return self.node_success_rates
    
    def get_pattern_weights(self) -> Dict[str, float]:
        """Get learned weights for patterns"""
        if not self.pattern_effectiveness:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pattern_id, effectiveness_score 
                FROM pattern_success
                WHERE total_uses > 0
            """)
            
            self.pattern_effectiveness = {
                row[0]: row[1] for row in cursor.fetchall()
            }
            
            conn.close()
        
        return self.pattern_effectiveness
    
    def suggest_improvements(self, intent: str) -> Dict[str, Any]:
        """Suggest improvements based on historical data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get successful patterns for this intent
        cursor.execute("""
            SELECT required_nodes, COUNT(*) as success_count
            FROM generation_history
            WHERE intent = ? AND success = 1
            GROUP BY required_nodes
            ORDER BY success_count DESC
            LIMIT 5
        """, (intent,))
        
        successful_patterns = cursor.fetchall()
        
        # Get common errors for this intent
        cursor.execute("""
            SELECT validation_errors, COUNT(*) as error_count
            FROM generation_history
            WHERE intent = ? AND success = 0 AND validation_errors IS NOT NULL
            GROUP BY validation_errors
            ORDER BY error_count DESC
            LIMIT 5
        """, (intent,))
        
        common_errors = cursor.fetchall()
        
        conn.close()
        
        return {
            "intent": intent,
            "successful_node_combinations": [
                json.loads(pattern[0]) for pattern in successful_patterns
            ],
            "common_errors": [
                json.loads(error[0]) for error in common_errors if error[0]
            ],
            "recommendations": self._generate_recommendations(intent, successful_patterns)
        }
    
    def _generate_recommendations(self, intent: str, patterns: List) -> List[str]:
        """Generate recommendations based on patterns"""
        recommendations = []
        
        if patterns:
            most_successful = json.loads(patterns[0][0])
            recommendations.append(
                f"For {intent} workflows, consider using: {', '.join(most_successful)}"
            )
        
        # Add more specific recommendations based on intent
        intent_tips = {
            "webhook_trigger": "Always include proper HTTP method and path parameters",
            "api_integration": "Don't forget authentication configuration",
            "data_transformation": "Code nodes are effective for complex transformations",
            "ai_automation": "Ensure AI agent has necessary tools configured",
            "notification": "Verify channel/recipient configuration"
        }
        
        if intent in intent_tips:
            recommendations.append(intent_tips[intent])
        
        return recommendations
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get overall system analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall success rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM generation_history
        """)
        total, successful = cursor.fetchone()
        
        # Success by intent
        cursor.execute("""
            SELECT 
                intent,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM generation_history
            GROUP BY intent
        """)
        intent_stats = cursor.fetchall()
        
        # Most effective nodes
        cursor.execute("""
            SELECT node_type, avg_relevance_score
            FROM node_effectiveness
            WHERE total_uses > 5
            ORDER BY avg_relevance_score DESC
            LIMIT 10
        """)
        top_nodes = cursor.fetchall()
        
        # Most common validation errors
        cursor.execute("""
            SELECT validation_errors, COUNT(*) as count
            FROM generation_history
            WHERE validation_errors IS NOT NULL
            GROUP BY validation_errors
            ORDER BY count DESC
            LIMIT 5
        """)
        common_errors = cursor.fetchall()
        
        conn.close()
        
        return {
            "overall_success_rate": (successful / total * 100) if total > 0 else 0,
            "total_generations": total,
            "successful_generations": successful,
            "success_by_intent": {
                row[0]: (row[2] / row[1] * 100) if row[1] > 0 else 0
                for row in intent_stats
            },
            "top_performing_nodes": [
                {"node": row[0], "score": row[1]} for row in top_nodes
            ],
            "common_validation_errors": [
                json.loads(row[0]) if row[0] else [] for row in common_errors[:3]
            ]
        }

class EnhancedN8nRetriever:
    """Enhanced retriever with feedback-based weight adjustment"""
    
    def __init__(self, base_retriever, feedback_loop: FeedbackLoop):
        self.base_retriever = base_retriever
        self.feedback_loop = feedback_loop
    
    def retrieve_with_learning(
        self,
        query: str,
        k_per_stage: int = 5
    ) -> Dict[str, Any]:
        """Retrieve with learned weights applied"""
        
        # Get base retrieval
        context = self.base_retriever.retrieve_for_generation(query, k_per_stage)
        
        # Apply learned weights
        node_weights = self.feedback_loop.get_node_weights()
        pattern_weights = self.feedback_loop.get_pattern_weights()
        
        # Re-rank nodes based on historical success
        if context.get("node_documentation"):
            for node_doc in context["node_documentation"]:
                node_type = node_doc.get("node_type", "")
                if node_type in node_weights:
                    # Boost or penalize based on historical performance
                    weight = node_weights[node_type]
                    node_doc["adjusted_relevance"] = weight
        
        # Re-rank patterns
        if context.get("workflow_patterns"):
            for pattern in context["workflow_patterns"]:
                pattern_id = pattern.get("pattern", "")
                if pattern_id in pattern_weights:
                    pattern["relevance"] *= pattern_weights[pattern_id]
            
            # Sort by adjusted relevance
            context["workflow_patterns"].sort(
                key=lambda x: x.get("relevance", 0),
                reverse=True
            )
        
        # Add improvement suggestions
        intent = context.get("intent", "unknown")
        suggestions = self.feedback_loop.suggest_improvements(intent)
        context["improvement_suggestions"] = suggestions
        
        return context

def integrate_feedback_loop(rag_system):
    """Integrate feedback loop into existing RAG system"""
    
    # Initialize feedback loop
    feedback_loop = FeedbackLoop()
    
    # Wrap the generate_workflow method
    original_generate = rag_system.generate_workflow
    
    def generate_with_feedback(*args, **kwargs):
        # Generate workflow
        result = original_generate(*args, **kwargs)
        
        # Record feedback
        if "query" in result and "context" in result:
            feedback_loop.record_generation(
                query=result["query"],
                context=result["context"],
                workflow=result.get("workflow"),
                success=result.get("success", False),
                validation_errors=result.get("validation_errors", [])
            )
        
        return result
    
    # Replace method
    rag_system.generate_workflow = generate_with_feedback
    
    # Add analytics method
    rag_system.get_analytics = feedback_loop.get_analytics
    
    # Add feedback recording method
    rag_system.record_user_feedback = lambda gen_id, rating: feedback_loop.record_user_feedback(gen_id, rating)
    
    return rag_system

# Usage Example
if __name__ == "__main__":
    # Initialize feedback system
    feedback = FeedbackLoop()
    
    # Get analytics
    analytics = feedback.get_analytics()
    print("System Analytics:")
    print(f"  Success Rate: {analytics['overall_success_rate']:.1f}%")
    print(f"  Total Generations: {analytics['total_generations']}")
    
    # Get improvement suggestions
    suggestions = feedback.suggest_improvements("webhook_trigger")
    print("\nImprovement Suggestions:")
    for rec in suggestions['recommendations']:
        print(f"  - {rec}")
