"""Configuration settings for MCP UI Explorer."""

import os
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from functools import lru_cache


class UITarsConfig(BaseModel):
    """Configuration for UI-TARS integration with multiple AI provider support."""
    
    model_config = ConfigDict(
        env_prefix="MCP_UI_EXPLORER_UI_TARS__",
        env_nested_delimiter="__",
        case_sensitive=False
    )
    
    # Provider selection
    provider: Literal["openai", "anthropic", "azure", "local", "custom"] = Field(
        default="local", 
        description="AI provider to use (openai, anthropic, azure, local, custom)"
    )
    
    # Common settings
    api_url: str = Field(
        default="http://127.0.0.1:1234/v1", 
        description="Base URL for the AI API"
    )
    api_key: Optional[str] = Field(
        default=None, 
        description="API key for authentication (not needed for local models)"
    )
    model_name: str = Field(
        default="ui-tars-7b-dpo", 
        description="Name of the model to use"
    )
    timeout: float = Field(
        default=30.0, 
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3, 
        description="Maximum number of retry attempts"
    )
    
    # Provider-specific settings
    openai_settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_url": "https://api.openai.com/v1",
            "model_name": "gpt-4-vision-preview",
            "max_tokens": 150,
            "temperature": 0.1
        },
        description="OpenAI-specific configuration"
    )
    
    anthropic_settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_url": "https://api.anthropic.com/v1",
            "model_name": "claude-3-sonnet-20240229",
            "max_tokens": 150,
            "temperature": 0.1
        },
        description="Anthropic-specific configuration"
    )
    
    azure_settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_url": "https://your-resource.openai.azure.com/",
            "api_version": "2024-02-15-preview",
            "deployment_name": "gpt-4-vision",
            "max_tokens": 150,
            "temperature": 0.1
        },
        description="Azure OpenAI-specific configuration"
    )
    
    local_settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_url": "http://127.0.0.1:1234/v1",
            "model_name": "ui-tars-7b-dpo",
            "max_tokens": 150,
            "temperature": 0.1,
            "api_key_required": False
        },
        description="Local model configuration (LM Studio, Ollama, etc.)"
    )
    
    custom_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom provider configuration"
    )
    
    # Fallback configuration
    enable_fallback: bool = Field(
        default=True,
        description="Enable fallback to other providers if primary fails"
    )
    
    fallback_providers: list[str] = Field(
        default_factory=lambda: ["local", "openai"],
        description="List of fallback providers in order of preference"
    )
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key_for_provider(cls, v, info):
        """Validate that API key is provided for cloud providers."""
        if info.data and 'provider' in info.data:
            provider = info.data['provider']
            if provider in ['openai', 'anthropic', 'azure'] and not v:
                # Check environment variables for API keys
                env_keys = {
                    'openai': 'OPENAI_API_KEY',
                    'anthropic': 'ANTHROPIC_API_KEY', 
                    'azure': 'AZURE_OPENAI_API_KEY'
                }
                env_key = os.getenv(env_keys.get(provider, ''))
                if not env_key:
                    print(f"Warning: No API key provided for {provider}. Set {env_keys.get(provider)} environment variable or provide api_key in config.")
        return v
    
    def get_provider_config(self) -> Dict[str, Any]:
        """Get the configuration for the current provider."""
        provider_configs = {
            'openai': self.openai_settings,
            'anthropic': self.anthropic_settings,
            'azure': self.azure_settings,
            'local': self.local_settings,
            'custom': self.custom_settings
        }
        
        config = provider_configs.get(self.provider, {}).copy()
        
        # Override with main settings if provided
        if self.api_url != "http://127.0.0.1:1234/v1":  # If not default
            config['api_url'] = self.api_url
        if self.model_name != "ui-tars-7b-dpo":  # If not default
            config['model_name'] = self.model_name
        if self.api_key:
            config['api_key'] = self.api_key
            
        return config
    
    def get_effective_api_key(self) -> Optional[str]:
        """Get the effective API key from config or environment."""
        if self.api_key:
            return self.api_key
            
        # Check environment variables
        env_keys = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'azure': 'AZURE_OPENAI_API_KEY'
        }
        
        env_key_name = env_keys.get(self.provider)
        if env_key_name:
            return os.getenv(env_key_name)
            
        return None


class MemoryConfig(BaseModel):
    """Configuration for memory management."""
    
    context_threshold: int = Field(default=45000, description="Context size threshold for auto-summarization")
    auto_summarize: bool = Field(default=True, description="Enable automatic summarization")


class UIConfig(BaseModel):
    """Configuration for UI interaction."""
    
    default_wait_time: float = Field(default=2.0, description="Default wait time before actions")
    default_verification_timeout: float = Field(default=3.0, description="Default verification timeout")
    auto_verify: bool = Field(default=True, description="Enable automatic verification by default")
    screenshot_prefix: str = Field(default="ui_hierarchy", description="Default screenshot filename prefix")


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )


class Settings(BaseModel):
    """Main settings class for MCP UI Explorer."""
    
    model_config = ConfigDict(
        env_prefix="MCP_UI_EXPLORER_",
        env_nested_delimiter="__",
        case_sensitive=False
    )
    
    # Environment
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Component configurations
    ui_tars: UITarsConfig = Field(default_factory=UITarsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        return cls(
            debug=os.getenv("MCP_UI_EXPLORER_DEBUG", "false").lower() == "true",
            ui_tars=UITarsConfig(
                provider=os.getenv("MCP_UI_EXPLORER_UI_TARS__PROVIDER", "local"),
                api_url=os.getenv("MCP_UI_EXPLORER_UI_TARS__API_URL", "http://127.0.0.1:1234/v1"),
                api_key=os.getenv("MCP_UI_EXPLORER_UI_TARS__API_KEY"),
                model_name=os.getenv("MCP_UI_EXPLORER_UI_TARS__MODEL_NAME", "ui-tars-7b-dpo"),
                timeout=float(os.getenv("MCP_UI_EXPLORER_UI_TARS__TIMEOUT", "30.0")),
                max_retries=int(os.getenv("MCP_UI_EXPLORER_UI_TARS__MAX_RETRIES", "3")),
                enable_fallback=os.getenv("MCP_UI_EXPLORER_UI_TARS__ENABLE_FALLBACK", "true").lower() == "true",
            ),
            memory=MemoryConfig(
                context_threshold=int(os.getenv("MCP_UI_EXPLORER_MEMORY__CONTEXT_THRESHOLD", "45000")),
                auto_summarize=os.getenv("MCP_UI_EXPLORER_MEMORY__AUTO_SUMMARIZE", "true").lower() == "true",
            ),
            ui=UIConfig(
                default_wait_time=float(os.getenv("MCP_UI_EXPLORER_UI__DEFAULT_WAIT_TIME", "2.0")),
                default_verification_timeout=float(os.getenv("MCP_UI_EXPLORER_UI__DEFAULT_VERIFICATION_TIMEOUT", "3.0")),
                auto_verify=os.getenv("MCP_UI_EXPLORER_UI__AUTO_VERIFY", "true").lower() == "true",
                screenshot_prefix=os.getenv("MCP_UI_EXPLORER_UI__SCREENSHOT_PREFIX", "ui_hierarchy"),
            ),
            logging=LoggingConfig(
                level=os.getenv("MCP_UI_EXPLORER_LOGGING__LEVEL", "INFO"),
                format=os.getenv(
                    "MCP_UI_EXPLORER_LOGGING__FORMAT", 
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                ),
            ),
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings.from_env() 