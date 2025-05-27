# MCP UI Explorer - AI Provider Configuration Examples

This document shows how to configure different AI providers for UI-TARS functionality.

## Environment Variables

You can configure the AI provider using environment variables:

### Local Models (LM Studio, Ollama, etc.)

```bash
# Default configuration for local models
export MCP_UI_EXPLORER_UI_TARS__PROVIDER="local"
export MCP_UI_EXPLORER_UI_TARS__API_URL="http://127.0.0.1:1234/v1"
export MCP_UI_EXPLORER_UI_TARS__MODEL_NAME="ui-tars-7b-dpo"
# No API key needed for local models
```

### OpenAI

```bash
export MCP_UI_EXPLORER_UI_TARS__PROVIDER="openai"
export MCP_UI_EXPLORER_UI_TARS__API_URL="https://api.openai.com/v1"
export MCP_UI_EXPLORER_UI_TARS__MODEL_NAME="gpt-4-vision-preview"
export OPENAI_API_KEY="your-openai-api-key-here"
# Or alternatively:
export MCP_UI_EXPLORER_UI_TARS__API_KEY="your-openai-api-key-here"
```

### Anthropic Claude

```bash
export MCP_UI_EXPLORER_UI_TARS__PROVIDER="anthropic"
export MCP_UI_EXPLORER_UI_TARS__API_URL="https://api.anthropic.com/v1"
export MCP_UI_EXPLORER_UI_TARS__MODEL_NAME="claude-3-sonnet-20240229"
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
# Or alternatively:
export MCP_UI_EXPLORER_UI_TARS__API_KEY="your-anthropic-api-key-here"
```

### Azure OpenAI

```bash
export MCP_UI_EXPLORER_UI_TARS__PROVIDER="azure"
export MCP_UI_EXPLORER_UI_TARS__API_URL="https://your-resource.openai.azure.com/"
export MCP_UI_EXPLORER_UI_TARS__MODEL_NAME="gpt-4-vision"
export AZURE_OPENAI_API_KEY="your-azure-api-key-here"
# Or alternatively:
export MCP_UI_EXPLORER_UI_TARS__API_KEY="your-azure-api-key-here"
```

### Custom Provider

```bash
export MCP_UI_EXPLORER_UI_TARS__PROVIDER="custom"
export MCP_UI_EXPLORER_UI_TARS__API_URL="https://your-custom-api.com/v1"
export MCP_UI_EXPLORER_UI_TARS__MODEL_NAME="your-custom-model"
export MCP_UI_EXPLORER_UI_TARS__API_KEY="your-custom-api-key"
```

## Configuration File (TOML)

You can also use a configuration file. Create a `config.toml` file:

```toml
[ui_tars]
provider = "openai"  # or "anthropic", "azure", "local", "custom"
api_url = "https://api.openai.com/v1"
model_name = "gpt-4-vision-preview"
api_key = "your-api-key-here"  # Optional if using environment variables
timeout = 30.0
max_retries = 3
enable_fallback = true
fallback_providers = ["local", "openai"]

# Provider-specific settings
[ui_tars.openai_settings]
api_url = "https://api.openai.com/v1"
model_name = "gpt-4-vision-preview"
max_tokens = 150
temperature = 0.1

[ui_tars.anthropic_settings]
api_url = "https://api.anthropic.com/v1"
model_name = "claude-3-sonnet-20240229"
max_tokens = 150
temperature = 0.1

[ui_tars.local_settings]
api_url = "http://127.0.0.1:1234/v1"
model_name = "ui-tars-7b-dpo"
max_tokens = 150
temperature = 0.1
api_key_required = false
```

Then set the config file path:

```bash
export MCP_UI_EXPLORER_CONFIG_FILE="path/to/your/config.toml"
```

## Fallback Configuration

The system supports automatic fallback to other providers if the primary one fails:

```bash
# Enable fallback (default: true)
export MCP_UI_EXPLORER_UI_TARS__ENABLE_FALLBACK="true"

# Set fallback order (will try local first, then openai if local fails)
export MCP_UI_EXPLORER_UI_TARS__FALLBACK_PROVIDERS="local,openai"
```

## Runtime Provider Override

You can also override the provider at runtime when calling the UI-TARS function:

```python
# Use OpenAI for this specific call
result = await ui_explorer.ui_tars_analyze(
    image_path="screenshot.png",
    query="find the login button",
    provider="openai",
    api_key="your-openai-key",
    model_name="gpt-4-vision-preview"
)

# Use local model for this call
result = await ui_explorer.ui_tars_analyze(
    image_path="screenshot.png", 
    query="find the submit button",
    provider="local",
    api_url="http://localhost:1234/v1",
    model_name="ui-tars-7b-dpo"
)
```

## Provider-Specific Notes

### Local Models (LM Studio)
- No API key required
- Make sure LM Studio is running on the specified port
- UI-TARS models work best, but other vision models may work
- Default port is 1234

### OpenAI
- Requires API key
- Best models: `gpt-4-vision-preview`, `gpt-4o`
- Has usage costs per API call
- Generally very reliable

### Anthropic Claude
- Requires API key  
- Best models: `claude-3-sonnet-20240229`, `claude-3-opus-20240229`
- Has usage costs per API call
- Good at following specific coordinate formats

### Azure OpenAI
- Requires API key and proper Azure setup
- Need to specify your Azure resource URL
- Model names may differ from OpenAI (e.g., deployment names)

## Testing Your Configuration

You can test your configuration by running:

```bash
# Test with current configuration
python -c "
from mcp_ui_explorer.config import get_settings
settings = get_settings()
print(f'Provider: {settings.ui_tars.provider}')
print(f'API URL: {settings.ui_tars.api_url}')
print(f'Model: {settings.ui_tars.model_name}')
print(f'API Key set: {bool(settings.ui_tars.get_effective_api_key())}')
"
```

## Security Best Practices

1. **Use environment variables** for API keys, not config files
2. **Never commit API keys** to version control
3. **Use different API keys** for development and production
4. **Monitor API usage** to detect unexpected costs
5. **Rotate API keys** regularly

## Troubleshooting

### Common Issues

1. **"No API key provided"** - Set the appropriate environment variable
2. **"Connection refused"** - Check if local model server is running
3. **"Model not found"** - Verify model name is correct for your provider
4. **"Rate limit exceeded"** - You've hit API limits, wait or upgrade plan
5. **"Invalid API key"** - Check your API key is correct and active

### Debug Mode

Enable debug logging to see detailed provider information:

```bash
export MCP_UI_EXPLORER_DEBUG="true"
export MCP_UI_EXPLORER_LOGGING__LEVEL="DEBUG"
```

This will show which provider is being used, fallback attempts, and detailed error messages. 