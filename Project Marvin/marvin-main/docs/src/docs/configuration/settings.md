# Settings

Marvin makes use of Pydantic's `BaseSettings` for configuration throughout the package.

## Environment Variables
All settings are configurable via environment variables like `MARVIN_<setting name>`.

For example, in an `.env` file or in your shell config file you might have:
```shell
MARVIN_LOG_LEVEL=DEBUG
MARVIN_LLM_MODEL=gpt-4
MARVIN_LLM_TEMPERATURE=0
```

## Runtime Settings
A runtime settings object is accessible via `marvin.settings` and can be used to access or update settings throughout the package.

For example, to access or change the LLM model used by Marvin at runtime:
```python
import marvin

marvin.settings.llm_model
# 'gpt-4'

marvin.settings.llm_model = 'gpt-3.5-turbo'

marvin.settings.llm_model
# 'gpt-3.5-turbo'
```

