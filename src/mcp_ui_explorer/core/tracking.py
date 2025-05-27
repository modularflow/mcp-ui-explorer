"""Tracking utilities for tool usage and step progress."""

import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..utils.logging import get_logger


class ToolUsageTracker:
    """Tracks tool usage statistics and patterns."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.tool_usage_stats: Dict[str, int] = defaultdict(int)
        self.tool_usage_history: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now()
    
    def track_tool_usage(self, tool_name: str) -> Dict[str, Any]:
        """Track tool usage and return current statistics."""
        self.tool_usage_stats[tool_name] += 1
        
        # Add to history
        self.tool_usage_history.append({
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "call_count": self.tool_usage_stats[tool_name]
        })
        
        # Calculate session duration
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        
        # Only show warnings if truly stuck (same tool 5+ times in last 8 calls within short time)
        recent_calls = [entry for entry in self.tool_usage_history[-8:] if entry["tool_name"] == tool_name]
        repetitive_warning = None
        
        if len(recent_calls) >= 5:
            # Check if these calls happened within a short time window (indicating being stuck)
            recent_timestamps = [datetime.fromisoformat(entry["timestamp"]) for entry in recent_calls]
            time_span = (recent_timestamps[-1] - recent_timestamps[0]).total_seconds()
            
            if time_span < 300:  # 5 minutes - likely stuck on same step
                repetitive_warning = f"STUCK DETECTED: '{tool_name}' called {len(recent_calls)} times in {time_span:.1f} seconds. Consider changing approach or documenting current step progress."
        
        return {
            "current_tool": tool_name,
            "current_tool_count": self.tool_usage_stats[tool_name],
            "total_tool_calls": sum(self.tool_usage_stats.values()),
            "session_duration_seconds": round(session_duration, 1),
            "tool_usage_breakdown": dict(self.tool_usage_stats),
            "repetitive_warning": repetitive_warning,
            "recent_history": [entry["tool_name"] for entry in self.tool_usage_history[-5:]]
        }


class ActionLogger:
    """Logs actions for later summarization."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.action_log: List[Dict[str, Any]] = []
        self.estimated_context_size: int = 0
    
    def log_action(self, tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Log an action for later summarization."""
        action_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "arguments": arguments,
            "result_summary": self._summarize_result(result),
            "success": result.get("success", True)
        }
        
        self.action_log.append(action_entry)
        
        # Estimate context size increase
        action_text = json.dumps(action_entry)
        self.estimated_context_size += self._estimate_context_size(action_text)
    
    def _estimate_context_size(self, text: str) -> int:
        """Estimate the context size of text (rough approximation: 4 chars per token)."""
        return len(text) // 4
    
    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Create a brief summary of an action result."""
        if not isinstance(result, dict):
            return str(result)[:200]
        
        # Extract key information for summary
        summary_parts = []
        
        if "success" in result:
            summary_parts.append(f"Success: {result['success']}")
        
        if "error" in result:
            summary_parts.append(f"Error: {result['error'][:100]}")
        
        if "message" in result:
            summary_parts.append(f"Message: {result['message'][:100]}")
        
        if "hierarchy" in result:
            hierarchy_count = len(result["hierarchy"]) if isinstance(result["hierarchy"], list) else 0
            summary_parts.append(f"Found {hierarchy_count} UI elements")
        
        if "coordinates" in result:
            coords = result["coordinates"]
            if isinstance(coords, dict) and "absolute" in coords:
                abs_coords = coords["absolute"]
                summary_parts.append(f"Coordinates: ({abs_coords.get('x', 'N/A')}, {abs_coords.get('y', 'N/A')})")
        
        if "verification_passed" in result:
            summary_parts.append(f"Verification: {'PASSED' if result['verification_passed'] else 'FAILED'}")
        
        return " | ".join(summary_parts) if summary_parts else "Action completed"
    
    def get_actions(self) -> List[Dict[str, Any]]:
        """Get all logged actions."""
        return self.action_log.copy()
    
    def clear_actions(self) -> None:
        """Clear the action log."""
        self.action_log.clear()
        self.estimated_context_size = 0


class StepTracker:
    """Tracks planned steps and progress."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.planned_steps: List[Dict[str, Any]] = []
        self.current_step_index: int = -1
        self.step_start_time: Optional[datetime] = None
        self.step_attempt_count: int = 0
    
    def track_step_progress(self, tool_name: str, step_description: Optional[str] = None) -> Dict[str, Any]:
        """Track progress on planned steps and detect when stuck."""
        now = datetime.now()
        
        # If this is a new step description, advance to next step
        if step_description:
            self.current_step_index += 1
            self.planned_steps.append({
                "step_index": self.current_step_index,
                "description": step_description,
                "start_time": now.isoformat(),
                "tools_used": [],
                "attempts": 0,
                "status": "in_progress"
            })
            self.step_start_time = now
            self.step_attempt_count = 0
        
        # Track tool usage for current step
        if self.current_step_index >= 0 and self.current_step_index < len(self.planned_steps):
            current_step = self.planned_steps[self.current_step_index]
            current_step["tools_used"].append({
                "tool": tool_name,
                "timestamp": now.isoformat()
            })
            current_step["attempts"] += 1
            self.step_attempt_count += 1
            
            # Check if stuck on current step
            step_duration = (now - datetime.fromisoformat(current_step["start_time"])).total_seconds()
            stuck_warning = None
            
            if step_duration > 120 and self.step_attempt_count >= 6:  # 2 minutes, 6+ attempts
                stuck_warning = f"STUCK ON STEP: '{current_step['description']}' for {step_duration:.1f}s with {self.step_attempt_count} attempts. Consider breaking down the step or changing approach."
            
            return {
                "current_step": current_step["description"],
                "step_duration_seconds": round(step_duration, 1),
                "step_attempts": self.step_attempt_count,
                "stuck_warning": stuck_warning,
                "total_steps_planned": len(self.planned_steps)
            }
        
        return {"message": "No current step being tracked"}
    
    def complete_current_step(self, success: bool = True, notes: str = "") -> None:
        """Mark the current step as completed."""
        if self.current_step_index >= 0 and self.current_step_index < len(self.planned_steps):
            current_step = self.planned_steps[self.current_step_index]
            current_step["status"] = "completed" if success else "failed"
            current_step["end_time"] = datetime.now().isoformat()
            current_step["notes"] = notes
            self.step_attempt_count = 0
    
    def get_step_status(self, show_all_steps: bool = False) -> Dict[str, Any]:
        """Get current step status and progress."""
        if not self.planned_steps:
            return {
                "success": True,
                "message": "No steps have been planned yet",
                "current_step": None,
                "total_steps": 0
            }
        
        current_step_info = None
        if self.current_step_index >= 0 and self.current_step_index < len(self.planned_steps):
            current_step = self.planned_steps[self.current_step_index]
            step_duration = (datetime.now() - datetime.fromisoformat(current_step["start_time"])).total_seconds()
            
            current_step_info = {
                "description": current_step["description"],
                "status": current_step["status"],
                "duration_seconds": round(step_duration, 1),
                "attempts": current_step["attempts"],
                "tools_used_count": len(current_step["tools_used"])
            }
        
        result = {
            "success": True,
            "current_step": current_step_info,
            "total_steps": len(self.planned_steps),
            "completed_steps": len([s for s in self.planned_steps if s["status"] == "completed"]),
            "failed_steps": len([s for s in self.planned_steps if s["status"] == "failed"])
        }
        
        if show_all_steps:
            result["all_steps"] = [
                {
                    "index": step["step_index"],
                    "description": step["description"],
                    "status": step["status"],
                    "attempts": step["attempts"],
                    "duration": (
                        (datetime.fromisoformat(step.get("end_time", datetime.now().isoformat())) - 
                         datetime.fromisoformat(step["start_time"])).total_seconds()
                    )
                }
                for step in self.planned_steps
            ]
        
        return result 