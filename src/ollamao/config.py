"""Configuration management for ollamao."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ModelConfig(BaseModel):
    """Configuration for a single Ollama model."""

    port: int = Field(..., description="Port where the Ollama instance is running")
    model: str = Field(..., description="Model name in Ollama")
    quant: Optional[str] = Field(None, description="Quantization level (e.g., Q4_K_M)")
    host: str = Field("localhost", description="Host where Ollama is running")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")


class APIKeyConfig(BaseModel):
    """Configuration for an API key."""

    name: str = Field(..., description="Human-readable name for the key")
    quota: str = Field("unlimited", description="Usage quota (unlimited for now)")
    enabled: bool = Field(True, description="Whether the key is active")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server settings
    host: str = Field("0.0.0.0", description="Host to bind the server to")
    port: int = Field(8000, description="Port to bind the server to")
    reload: bool = Field(False, description="Enable auto-reload for development")

    # Paths
    config_dir: Path = Field(
        Path("config"), description="Directory containing config files"
    )
    models_config_file: str = Field(
        "models.yaml", description="Models configuration file"
    )
    keys_config_file: str = Field(
        "keys.yaml", description="API keys configuration file"
    )

    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field("json", description="Logging format (json or console)")

    # CORS
    cors_origins: list[str] = Field(["*"], description="CORS allowed origins")

    # Development
    debug: bool = Field(False, description="Enable debug mode")

    model_config = {"env_prefix": "OLLAMAO_", "env_file": ".env"}


class ConfigManager:
    """Manages configuration loading and caching."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self._models_cache: Optional[Dict[str, ModelConfig]] = None
        self._keys_cache: Optional[Dict[str, APIKeyConfig]] = None

    @property
    def models_config_path(self) -> Path:
        """Path to the models configuration file."""
        return self.settings.config_dir / self.settings.models_config_file

    @property
    def keys_config_path(self) -> Path:
        """Path to the keys configuration file."""
        return self.settings.config_dir / self.settings.keys_config_file

    def load_models(self, force_reload: bool = False) -> Dict[str, ModelConfig]:
        """Load models configuration from YAML file."""
        if self._models_cache is not None and not force_reload:
            return self._models_cache

        if not self.models_config_path.exists():
            raise FileNotFoundError(
                f"Models config file not found: {self.models_config_path}"
            )

        with open(self.models_config_path, "r") as f:
            data = yaml.safe_load(f)

        models = {}
        for model_name, model_data in data.get("models", {}).items():
            models[model_name] = ModelConfig(**model_data)

        self._models_cache = models
        return models

    def load_keys(self, force_reload: bool = False) -> Dict[str, APIKeyConfig]:
        """Load API keys configuration from YAML file."""
        if self._keys_cache is not None and not force_reload:
            return self._keys_cache

        if not self.keys_config_path.exists():
            raise FileNotFoundError(
                f"Keys config file not found: {self.keys_config_path}"
            )

        with open(self.keys_config_path, "r") as f:
            data = yaml.safe_load(f)

        keys = {}
        for key_name, key_data in data.get("keys", {}).items():
            keys[key_name] = APIKeyConfig(**key_data)

        self._keys_cache = keys
        return keys

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model."""
        models = self.load_models()
        return models.get(model_name)

    def get_api_key_config(self, api_key: str) -> Optional[APIKeyConfig]:
        """Get configuration for a specific API key."""
        keys = self.load_keys()
        return keys.get(api_key)

    def list_available_models(self) -> list[str]:
        """List all available model names."""
        models = self.load_models()
        return list(models.keys())

    def get_ollama_url(self, model_name: str) -> Optional[str]:
        """Get the full Ollama URL for a model."""
        model_config = self.get_model_config(model_name)
        if not model_config:
            return None

        return f"http://{model_config.host}:{model_config.port}"

    def reload_config(self) -> None:
        """Force reload all configuration."""
        self._models_cache = None
        self._keys_cache = None


# Global config manager instance
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    return config_manager


def get_settings() -> Settings:
    """Get application settings."""
    return config_manager.settings
