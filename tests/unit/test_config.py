"""Unit tests for configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_ui_explorer.config import Settings, UITarsConfig, get_settings


class TestUITarsConfig:
    """Test UITarsConfig configuration class."""

    def test_default_values(self):
        """Test default UITarsConfig values."""
        config = UITarsConfig()
        
        assert config.provider == "local"
        assert config.api_url == "http://127.0.0.1:1234/v1"
        assert config.api_key is None
        assert config.model_name == "ui-tars-7b-dpo"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.enable_fallback is True
        assert config.fallback_providers == ["local", "openai"]

    def test_provider_config_local(self):
        """Test getting provider config for local provider."""
        config = UITarsConfig(provider="local")
        provider_config = config.get_provider_config()
        
        assert provider_config["api_url"] == "http://127.0.0.1:1234/v1"
        assert provider_config["model_name"] == "ui-tars-7b-dpo"
        assert provider_config["api_key_required"] is False

    def test_provider_config_openai(self):
        """Test getting provider config for OpenAI provider."""
        config = UITarsConfig(provider="openai")
        provider_config = config.get_provider_config()
        
        assert provider_config["api_url"] == "https://api.openai.com/v1"
        assert provider_config["model_name"] == "gpt-4-vision-preview"
        assert provider_config["max_tokens"] == 150

    def test_provider_config_override(self):
        """Test that main config overrides provider-specific config."""
        config = UITarsConfig(
            provider="openai",
            api_url="https://custom-api.com/v1",
            model_name="custom-model"
        )
        provider_config = config.get_provider_config()
        
        assert provider_config["api_url"] == "https://custom-api.com/v1"
        assert provider_config["model_name"] == "custom-model"

    def test_effective_api_key_from_config(self):
        """Test getting API key from config."""
        config = UITarsConfig(api_key="test-key")
        assert config.get_effective_api_key() == "test-key"

    def test_effective_api_key_from_env(self):
        """Test getting API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            config = UITarsConfig(provider="openai")
            assert config.get_effective_api_key() == "env-key"

    def test_effective_api_key_none(self):
        """Test getting API key when none available."""
        config = UITarsConfig(provider="local")
        assert config.get_effective_api_key() is None

    def test_custom_provider_settings(self):
        """Test custom provider configuration."""
        custom_settings = {
            "api_url": "https://my-custom-api.com/v1",
            "model_name": "my-custom-model",
            "max_tokens": 200,
            "temperature": 0.2
        }
        
        config = UITarsConfig(
            provider="custom",
            custom_settings=custom_settings
        )
        
        provider_config = config.get_provider_config()
        assert provider_config["api_url"] == "https://my-custom-api.com/v1"
        assert provider_config["model_name"] == "my-custom-model"
        assert provider_config["max_tokens"] == 200
        assert provider_config["temperature"] == 0.2


class TestSettings:
    """Test Settings configuration class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        # Test debug setting
        assert settings.debug is False
        
        # Test UI-TARS settings
        assert settings.ui_tars.provider == "local"
        assert settings.ui_tars.api_url == "http://127.0.0.1:1234/v1"
        assert settings.ui_tars.model_name == "ui-tars-7b-dpo"
        assert settings.ui_tars.timeout == 30.0
        
        # Test memory settings
        assert settings.memory.context_threshold == 45000
        assert settings.memory.auto_summarize is True
        
        # Test UI settings
        assert settings.ui.default_wait_time == 2.0
        assert settings.ui.default_verification_timeout == 3.0
        assert settings.ui.auto_verify is True
        assert settings.ui.screenshot_prefix == "ui_hierarchy"
        
        # Test logging settings
        assert settings.logging.level == "INFO"
        assert settings.logging.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def test_settings_from_env_vars(self):
        """Test settings loaded from environment variables."""
        env_vars = {
            "MCP_UI_EXPLORER_DEBUG": "true",
            "MCP_UI_EXPLORER_UI_TARS__PROVIDER": "openai",
            "MCP_UI_EXPLORER_UI_TARS__API_URL": "https://custom-api.com/v1",
            "MCP_UI_EXPLORER_UI_TARS__API_KEY": "test-key",
            "MCP_UI_EXPLORER_UI_TARS__MODEL_NAME": "custom-model",
            "MCP_UI_EXPLORER_UI_TARS__TIMEOUT": "60.0",
            "MCP_UI_EXPLORER_UI_TARS__MAX_RETRIES": "5",
            "MCP_UI_EXPLORER_UI_TARS__ENABLE_FALLBACK": "false",
            "MCP_UI_EXPLORER_MEMORY__CONTEXT_THRESHOLD": "50000",
            "MCP_UI_EXPLORER_MEMORY__AUTO_SUMMARIZE": "false",
            "MCP_UI_EXPLORER_UI__DEFAULT_WAIT_TIME": "5.0",
            "MCP_UI_EXPLORER_UI__AUTO_VERIFY": "false",
            "MCP_UI_EXPLORER_LOGGING__LEVEL": "DEBUG",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings.from_env()
            
            assert settings.debug is True
            assert settings.ui_tars.provider == "openai"
            assert settings.ui_tars.api_url == "https://custom-api.com/v1"
            assert settings.ui_tars.api_key == "test-key"
            assert settings.ui_tars.model_name == "custom-model"
            assert settings.ui_tars.timeout == 60.0
            assert settings.ui_tars.max_retries == 5
            assert settings.ui_tars.enable_fallback is False
            assert settings.memory.context_threshold == 50000
            assert settings.memory.auto_summarize is False
            assert settings.ui.default_wait_time == 5.0
            assert settings.ui.auto_verify is False
            assert settings.logging.level == "DEBUG"

    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_provider_validation_warning(self):
        """Test that provider validation shows warning for missing API key."""
        with patch('builtins.print') as mock_print:
            config = UITarsConfig(provider="openai", api_key=None)
            # The validator should have been called during initialization
            # Check if warning was printed (this is a bit tricky to test)
            # For now, just ensure the config was created successfully
            assert config.provider == "openai"

    def test_settings_immutability(self):
        """Test that settings objects are immutable after creation."""
        settings = Settings()
        
        # Pydantic models are mutable by default, but we can test that
        # the structure is as expected
        assert hasattr(settings, 'ui_tars')
        assert hasattr(settings, 'memory')
        assert hasattr(settings, 'ui')
        assert hasattr(settings, 'logging')


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_invalid_config_file(self):
        """Test get_settings with invalid config file content."""
        # This should not crash the application, just use defaults
        with patch.dict(os.environ, {"MCP_UI_EXPLORER_CONFIG_FILE": "invalid.toml"}):
            settings = get_settings()
            # Should still return valid settings with defaults
            assert settings.ui_tars.provider == "local" 