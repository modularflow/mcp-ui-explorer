"""Verification service for UI action validation."""

import os
import time
from typing import Dict, Any, Optional

from ..config import get_settings
from ..utils.logging import get_logger
from .ui_tars import UITarsService


class VerificationService:
    """Service for verifying UI actions."""
    
    def __init__(self, ui_tars_service: UITarsService):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.ui_tars_service = ui_tars_service
    
    async def verify_action(
        self,
        action_description: str,
        expected_result: str,
        verification_query: str,
        timeout: float = None,
        comparison_image: Optional[str] = None,
        screenshot_function=None
    ) -> Dict[str, Any]:
        """
        Verify that a UI action had the expected result.
        
        Args:
            action_description: Description of what action was performed
            expected_result: What should have happened
            verification_query: What to look for to verify success
            timeout: How long to wait for changes (seconds)
            comparison_image: Optional before image for comparison
            screenshot_function: Function to take screenshots
        
        Returns:
            Verification result with success status and details
        """
        timeout = timeout or self.settings.ui.default_verification_timeout
        
        try:
            # Wait for the UI to settle after the action
            time.sleep(timeout)
            
            # Take a screenshot to verify the current state
            if screenshot_function:
                image_data, image_path, cursor_pos = await screenshot_function(
                    output_prefix="verification"
                )
            else:
                self.logger.warning("No screenshot function provided for verification")
                return {
                    "success": False,
                    "error": "No screenshot function available for verification"
                }
            
            # Use UI-TARS to check if the expected element/state is present
            verification_result = await self.ui_tars_service.analyze_image(
                image_path=image_path,
                query=verification_query
            )
            
            # Analyze the verification result
            verification_success = False
            verification_details = {}
            
            if verification_result['success']:
                if verification_result.get('found'):
                    verification_success = True
                    verification_details = {
                        "found_element": True,
                        "coordinates": verification_result.get('coordinates'),
                        "ai_response": verification_result.get('response')
                    }
                else:
                    verification_details = {
                        "found_element": False,
                        "ai_response": verification_result.get('response'),
                        "search_query": verification_query
                    }
            else:
                verification_details = {
                    "ai_error": verification_result.get('error', 'Unknown error'),
                    "search_query": verification_query
                }
            
            # Optional: Compare with before image if provided
            comparison_details = None
            if comparison_image and os.path.exists(comparison_image):
                try:
                    # Basic file comparison (could be enhanced with image diff)
                    with open(comparison_image, 'rb') as f1, open(image_path, 'rb') as f2:
                        before_size = len(f1.read())
                        after_size = len(f2.read())
                        
                    comparison_details = {
                        "before_image": comparison_image,
                        "after_image": image_path,
                        "file_size_changed": before_size != after_size,
                        "before_size": before_size,
                        "after_size": after_size
                    }
                except Exception as e:
                    comparison_details = {"comparison_error": str(e)}
            
            return {
                "success": True,
                "verification_passed": verification_success,
                "action_description": action_description,
                "expected_result": expected_result,
                "verification_query": verification_query,
                "verification_details": verification_details,
                "comparison_details": comparison_details,
                "verification_screenshot": image_path,
                "waited_seconds": timeout,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Verification failed: {str(e)}")
            return {
                "success": False,
                "error": f"Verification failed: {str(e)}",
                "action_description": action_description,
                "expected_result": expected_result
            } 