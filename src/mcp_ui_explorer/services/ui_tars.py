"""UI-TARS service for element detection and analysis."""

import os
import base64
import re
from typing import Dict, Any, Optional, Union
from openai import OpenAI

from ..config import get_settings
from ..utils.logging import get_logger
from ..utils.coordinates import CoordinateConverter


class UITarsService:
    """Service for interacting with UI-TARS model with multi-provider support."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self._clients: Dict[str, OpenAI] = {}
    
    def _get_client(self, provider: str = None, api_url: str = None, api_key: str = None) -> OpenAI:
        """Get or create OpenAI-compatible client for the specified provider."""
        provider = provider or self.settings.ui_tars.provider
        
        # Use provided values or get from config
        if not api_url or not api_key:
            provider_config = self.settings.ui_tars.get_provider_config()
            api_url = api_url or provider_config.get('api_url', self.settings.ui_tars.api_url)
            api_key = api_key or self.settings.ui_tars.get_effective_api_key()
        
        # For local models, use dummy API key if none provided
        if provider == 'local' and not api_key:
            api_key = "dummy"
        
        # Create cache key
        cache_key = f"{provider}:{api_url}:{bool(api_key)}"
        
        if cache_key not in self._clients:
            self.logger.debug(f"Creating new client for provider: {provider}")
            
            client_kwargs = {
                "base_url": api_url,
                "api_key": api_key or "dummy"
            }
            
            # Add provider-specific configurations
            if provider == "azure":
                provider_config = self.settings.ui_tars.azure_settings
                if "api_version" in provider_config:
                    # For Azure, we might need to handle this differently
                    # depending on the client library version
                    pass
            
            self._clients[cache_key] = OpenAI(**client_kwargs)
        
        return self._clients[cache_key]
    
    async def analyze_image(
        self,
        image_path: str,
        query: str,
        api_url: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use UI-TARS model to identify coordinates of UI elements on screen.
        
        Args:
            image_path: Path to the screenshot image to analyze
            query: Description of what to find on the screen
            api_url: Override API URL (optional)
            model_name: Override model name (optional)
            provider: Override provider (optional)
            
        Returns:
            Dictionary containing the analysis result with normalized coordinates
        """
        # Determine which provider to use
        provider = provider or self.settings.ui_tars.provider
        provider_config = self.settings.ui_tars.get_provider_config()
        
        # Use provided values or fall back to config
        api_url = api_url or provider_config.get('api_url', self.settings.ui_tars.api_url)
        model_name = model_name or provider_config.get('model_name', self.settings.ui_tars.model_name)
        
        # Try primary provider first
        result = await self._try_analyze_with_provider(
            image_path, query, provider, api_url, model_name
        )
        
        # If primary failed and fallback is enabled, try fallback providers
        if not result.get('success') and self.settings.ui_tars.enable_fallback:
            self.logger.warning(f"Primary provider {provider} failed, trying fallbacks...")
            
            for fallback_provider in self.settings.ui_tars.fallback_providers:
                if fallback_provider == provider:
                    continue  # Skip the provider that already failed
                
                self.logger.info(f"Trying fallback provider: {fallback_provider}")
                fallback_config = self.settings.ui_tars.get_provider_config()
                
                # Update config for fallback provider
                if fallback_provider == 'openai':
                    fallback_config = self.settings.ui_tars.openai_settings
                elif fallback_provider == 'anthropic':
                    fallback_config = self.settings.ui_tars.anthropic_settings
                elif fallback_provider == 'local':
                    fallback_config = self.settings.ui_tars.local_settings
                
                fallback_result = await self._try_analyze_with_provider(
                    image_path, query, fallback_provider,
                    fallback_config.get('api_url'),
                    fallback_config.get('model_name')
                )
                
                if fallback_result.get('success'):
                    fallback_result['used_fallback'] = True
                    fallback_result['fallback_provider'] = fallback_provider
                    return fallback_result
        
        return result
    
    async def _try_analyze_with_provider(
        self,
        image_path: str,
        query: str,
        provider: str,
        api_url: str,
        model_name: str
    ) -> Dict[str, Any]:
        """Try to analyze image with a specific provider."""
        try:
            # Check if image file exists
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}",
                    "provider": provider
                }
            
            # Load and encode the image
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get client for this provider
            client = self._get_client(provider, api_url)
            
            # Prepare the prompt based on provider
            system_prompt, user_prompt = self._get_prompts_for_provider(provider, query)
            
            self.logger.debug(f"Analyzing image {image_path} with provider {provider}, query: {query}")
            
            # Prepare messages based on provider capabilities
            messages = self._prepare_messages(provider, system_prompt, user_prompt, image_base64)
            
            # Get provider-specific settings
            provider_config = self._get_provider_settings(provider)
            
            # Make the API call
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=provider_config.get('max_tokens', 150),
                temperature=provider_config.get('temperature', 0.1),
                timeout=self.settings.ui_tars.timeout
            )
            
            # Parse the response
            response_text = response.choices[0].message.content.strip()
            
            result = self._parse_coordinates_response(response_text, query)
            result['provider'] = provider
            result['model_name'] = model_name
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze image with provider {provider}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to analyze image with provider {provider}: {str(e)}",
                "provider": provider
            }
    
    def _get_prompts_for_provider(self, provider: str, query: str) -> tuple[str, str]:
        """Get system and user prompts optimized for the specific provider."""
        if provider == "anthropic":
            system_prompt = """You are a specialized AI assistant for identifying UI elements in screenshots. 
When asked to find an element, respond with the coordinates of the center of the target element.
Use this format: <click>x,y</click> where x,y are normalized coordinates (0-1).
If you cannot find the element, respond with "Element not found"."""
            
            user_prompt = f"Find the {query} in this screenshot and provide its normalized coordinates using the <click>x,y</click> format."
        
        elif provider in ["openai", "azure"]:
            system_prompt = """You are UI-TARS, a specialized model for identifying UI elements in screenshots. 
When asked to find an element, respond with the coordinates of the center of the target element.
You can use any of these formats:
- <click>x,y</click> for normalized coordinates (0-1)
- <|box_start|>(x,y)<|box_end|> for absolute pixel coordinates
- (x,y) for coordinates
If you cannot find the element, respond with "Element not found"."""
            
            user_prompt = f"Find the {query} in this screenshot and provide its normalized coordinates."
        
        else:  # local or custom
            system_prompt = """You are UI-TARS, a specialized model for identifying UI elements in screenshots. 
When asked to find an element, respond with the coordinates of the center of the target element.
You can use any of these formats:
- <click>x,y</click> for normalized coordinates (0-1)
- <|box_start|>(x,y)<|box_end|> for absolute pixel coordinates
- (x,y) for coordinates
If you cannot find the element, respond with "Element not found"."""
            
            user_prompt = f"Find the {query} in this screenshot and provide its normalized coordinates."
        
        return system_prompt, user_prompt
    
    def _prepare_messages(self, provider: str, system_prompt: str, user_prompt: str, image_base64: str) -> list:
        """Prepare messages in the format expected by the provider."""
        if provider == "anthropic":
            # Anthropic uses a different message format
            return [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
        else:
            # OpenAI/Azure/Local format
            return [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
    
    def _get_provider_settings(self, provider: str) -> Dict[str, Any]:
        """Get provider-specific settings."""
        provider_settings = {
            'openai': self.settings.ui_tars.openai_settings,
            'anthropic': self.settings.ui_tars.anthropic_settings,
            'azure': self.settings.ui_tars.azure_settings,
            'local': self.settings.ui_tars.local_settings,
            'custom': self.settings.ui_tars.custom_settings
        }
        
        return provider_settings.get(provider, {})
    
    def _parse_coordinates_response(self, response_text: str, query: str) -> Dict[str, Any]:
        """
        Parse coordinates from UI-TARS response.
        
        Args:
            response_text: Raw response from UI-TARS
            query: Original query for context
            
        Returns:
            Parsed coordinate information
        """
        # Extract coordinates from response - handle multiple formats
        # Format 1: <click>x,y</click>
        coordinate_pattern1 = r'<click>([0-9.]+),([0-9.]+)</click>'
        # Format 2: <|box_start|>(x,y)<|box_end|>
        coordinate_pattern2 = r'<\|box_start\|>\(([0-9.]+),([0-9.]+)\)<\|box_end\|>'
        # Format 3: Just coordinates in parentheses (x,y)
        coordinate_pattern3 = r'\(([0-9.]+),([0-9.]+)\)'
        
        match = re.search(coordinate_pattern1, response_text)
        if not match:
            match = re.search(coordinate_pattern2, response_text)
        if not match:
            match = re.search(coordinate_pattern3, response_text)
        
        if match:
            x, y = float(match.group(1)), float(match.group(2))
            
            # Determine if coordinates are normalized or absolute
            if x <= 1.0 and y <= 1.0:
                # Likely normalized coordinates
                normalized_coords = {"x": x, "y": y}
                
                # Convert to absolute coordinates
                screen_width, screen_height = CoordinateConverter.get_screen_size()
                absolute_coords = {
                    "x": int(x * screen_width),
                    "y": int(y * screen_height)
                }
            else:
                # Likely absolute coordinates
                absolute_coords = {"x": int(x), "y": int(y)}
                
                # Convert to normalized coordinates
                screen_width, screen_height = CoordinateConverter.get_screen_size()
                normalized_coords = {
                    "x": x / screen_width,
                    "y": y / screen_height
                }
            
            return {
                "success": True,
                "found": True,
                "coordinates": {
                    "normalized": normalized_coords,
                    "absolute": absolute_coords
                },
                "response": response_text,
                "query": query
            }
        else:
            # No coordinates found
            return {
                "success": True,
                "found": False,
                "response": response_text,
                "query": query,
                "error": "Could not parse coordinates from response"
            } 