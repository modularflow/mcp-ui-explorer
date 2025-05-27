"""Memory service for session summarization and context management."""

from datetime import datetime
from typing import Dict, Any, Optional, List

from ..config import get_settings
from ..utils.logging import get_logger
from ..core.tracking import ActionLogger


class MemoryService:
    """Service for managing memory and session summarization."""
    
    def __init__(self, action_logger: ActionLogger):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.action_logger = action_logger
        self.summary_count: int = 0
        self.last_summary_id: Optional[str] = None
    
    async def check_and_create_summary(self) -> Optional[Dict[str, Any]]:
        """Check if context is approaching limit and create summary if needed."""
        if not self.settings.memory.auto_summarize:
            return None
            
        if self.action_logger.estimated_context_size < self.settings.memory.context_threshold:
            return None
        
        return await self._create_summary()
    
    async def create_summary(self, force_summary: bool = False) -> Dict[str, Any]:
        """Create a memory summary of the current session."""
        if not force_summary and self.action_logger.estimated_context_size < self.settings.memory.context_threshold:
            return {
                "success": True,
                "summary_created": False,
                "message": f"Context size ({self.action_logger.estimated_context_size}) below threshold ({self.settings.memory.context_threshold}). Use force_summary=true to create anyway.",
                "current_context_size": self.action_logger.estimated_context_size,
                "context_threshold": self.settings.memory.context_threshold,
                "actions_logged": len(self.action_logger.get_actions())
            }
        
        actions = self.action_logger.get_actions()
        if not actions:
            return {
                "success": True,
                "summary_created": False,
                "message": "No actions to summarize",
                "current_context_size": self.action_logger.estimated_context_size
            }
        
        try:
            summary_result = await self._create_summary()
            
            if summary_result:
                return {
                    "success": True,
                    "summary_created": True,
                    "summary_id": summary_result["summary_id"],
                    "actions_summarized": summary_result["actions_summarized"],
                    "context_reset": True,
                    "message": f"Created summary '{summary_result['summary_id']}' with {summary_result['actions_summarized']} actions",
                    "memory_entity": summary_result["summary_entity"],
                    "memory_relations": summary_result["relations"],
                    "previous_summary": self.last_summary_id
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create summary",
                    "current_context_size": self.action_logger.estimated_context_size
                }
                
        except Exception as e:
            self.logger.error(f"Error creating memory summary: {str(e)}")
            return {
                "success": False,
                "error": f"Error creating memory summary: {str(e)}",
                "current_context_size": self.action_logger.estimated_context_size
            }
    
    async def _create_summary(self) -> Optional[Dict[str, Any]]:
        """Create summary of recent actions."""
        actions = self.action_logger.get_actions()
        if not actions:
            return None
        
        # Create summary of recent actions
        summary_id = f"UI_Session_Summary_{self.summary_count + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Analyze the action log for patterns and outcomes
        successful_actions = [action for action in actions if action.get("success", True)]
        failed_actions = [action for action in actions if not action.get("success", True)]
        
        # Group actions by tool type
        tool_usage_summary = {}
        for action in actions:
            tool = action["tool_name"]
            if tool not in tool_usage_summary:
                tool_usage_summary[tool] = {"count": 0, "successes": 0, "failures": 0}
            tool_usage_summary[tool]["count"] += 1
            if action.get("success", True):
                tool_usage_summary[tool]["successes"] += 1
            else:
                tool_usage_summary[tool]["failures"] += 1
        
        # Create comprehensive summary
        session_duration = (datetime.now() - datetime.fromisoformat(actions[0]["timestamp"])).total_seconds()
        
        summary_observations = [
            f"Session Duration: {session_duration:.1f} seconds ({session_duration/60:.1f} minutes)",
            f"Total Actions: {len(actions)}",
            f"Successful Actions: {len(successful_actions)}",
            f"Failed Actions: {len(failed_actions)}",
            f"Success Rate: {(len(successful_actions)/len(actions)*100):.1f}%" if actions else "No actions",
            "",
            "Tool Usage Summary:",
        ]
        
        for tool, stats in tool_usage_summary.items():
            success_rate = (stats["successes"] / stats["count"] * 100) if stats["count"] > 0 else 0
            summary_observations.append(f"  {tool}: {stats['count']} calls, {success_rate:.1f}% success rate")
        
        summary_observations.extend([
            "",
            "Key Actions Taken:",
        ])
        
        # Add most recent significant actions
        recent_actions = actions[-20:]  # Last 20 actions
        for action in recent_actions:
            timestamp = action["timestamp"].split("T")[1][:8]  # Just time part
            summary_observations.append(f"  {timestamp} - {action['tool_name']}: {action['result_summary']}")
        
        if failed_actions:
            summary_observations.extend([
                "",
                "Notable Failures:",
            ])
            for action in failed_actions[-5:]:  # Last 5 failures
                timestamp = action["timestamp"].split("T")[1][:8]
                summary_observations.append(f"  {timestamp} - {action['tool_name']}: {action['result_summary']}")
        
        # Create memory entity
        summary_entity = {
            "name": summary_id,
            "entityType": "Session_Summary",
            "observations": summary_observations
        }
        
        # Create relation to previous summary if exists
        relations = []
        if self.last_summary_id:
            relations.append({
                "from": self.last_summary_id,
                "to": summary_id,
                "relationType": "FOLLOWED_BY"
            })
        
        # Store count before clearing
        actions_count = len(actions)
        
        # Update tracking variables
        self.summary_count += 1
        self.last_summary_id = summary_id
        
        # Reset for next session segment
        self.action_logger.clear_actions()
        
        return {
            "summary_created": True,
            "summary_id": summary_id,
            "summary_entity": summary_entity,
            "relations": relations,
            "actions_summarized": actions_count,
            "context_reset": True
        } 