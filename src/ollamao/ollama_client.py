"""HTTP client for communicating with Ollama backends."""

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from fastapi import HTTPException

from .config import ModelConfig, get_config_manager
from .logging import model_logger


class OllamaError(Exception):
    """Base exception for Ollama client errors."""

    pass


class OllamaConnectionError(OllamaError):
    """Raised when unable to connect to Ollama."""

    pass


class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested model is not available."""

    pass


class OllamaClient:
    """HTTP client for communicating with Ollama backends."""

    def __init__(self):
        self.config_manager = get_config_manager()
        self.http_client = httpx.AsyncClient()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.aclose()

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a chat completion request to Ollama.

        Args:
            model: Model name to use
            messages: List of chat messages
            stream: Whether to stream the response
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to Ollama

        Yields:
            Response chunks if streaming, single response if not

        Raises:
            OllamaError: If the request fails
        """
        model_config = self.config_manager.get_model_config(model)
        if not model_config:
            available_models = self.config_manager.list_available_models()
            model_logger.log_model_not_found(model, available_models)
            raise OllamaModelNotFoundError(
                f"Model '{model}' not found. Available models: {available_models}"
            )

        ollama_url = self.config_manager.get_ollama_url(model)
        endpoint = f"{ollama_url}/api/chat"

        # Build the request payload
        payload = {
            "model": model_config.model,
            "messages": messages,
            "stream": stream,
        }

        # Add optional parameters
        if temperature is not None:
            payload["options"] = {"temperature": temperature}
        if max_tokens is not None:
            payload.setdefault("options", {})["num_predict"] = max_tokens

        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in payload:
                payload[key] = value

        model_logger.log_ollama_request(model, endpoint)
        start_time = time.time()

        try:
            async with self.http_client.stream(
                "POST",
                endpoint,
                json=payload,
                timeout=model_config.timeout,
            ) as response:
                response.raise_for_status()

                if stream:
                    async for chunk in self._process_streaming_response(
                        response, model, start_time
                    ):
                        yield chunk
                else:
                    content = await response.aread()
                    data = json.loads(content)

                    latency_ms = int((time.time() - start_time) * 1000)
                    model_logger.log_ollama_response(
                        model, response.status_code, latency_ms
                    )

                    yield data

        except httpx.TimeoutException as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Timeout connecting to Ollama for model {model}"
            model_logger.log_ollama_response(model, 0, latency_ms, error=error_msg)
            raise OllamaConnectionError(error_msg) from e

        except httpx.ConnectError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Failed to connect to Ollama for model {model}"
            model_logger.log_ollama_response(model, 0, latency_ms, error=error_msg)
            raise OllamaConnectionError(error_msg) from e

        except httpx.HTTPStatusError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = (
                f"Ollama returned status {e.response.status_code} for model {model}"
            )
            model_logger.log_ollama_response(
                model, e.response.status_code, latency_ms, error=error_msg
            )
            raise OllamaError(error_msg) from e

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Unexpected error with Ollama for model {model}: {str(e)}"
            model_logger.log_ollama_response(model, 0, latency_ms, error=error_msg)
            raise OllamaError(error_msg) from e

    async def _process_streaming_response(
        self, response: httpx.Response, model: str, start_time: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a streaming response from Ollama."""
        try:
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        yield data

                        # Log completion when we receive the final chunk
                        if data.get("done", False):
                            latency_ms = int((time.time() - start_time) * 1000)
                            model_logger.log_ollama_response(
                                model, response.status_code, latency_ms
                            )

                    except json.JSONDecodeError as e:
                        # Skip malformed JSON lines
                        continue

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error processing streaming response: {str(e)}"
            model_logger.log_ollama_response(
                model, response.status_code, latency_ms, error=error_msg
            )
            raise OllamaError(error_msg) from e

    async def list_models(self, model_name: str) -> List[Dict[str, Any]]:
        """
        List available models from a specific Ollama instance.

        Args:
            model_name: Name of the model configuration to check

        Returns:
            List of available models from that Ollama instance

        Raises:
            OllamaError: If the request fails
        """
        model_config = self.config_manager.get_model_config(model_name)
        if not model_config:
            raise OllamaModelNotFoundError(
                f"Model configuration '{model_name}' not found"
            )

        ollama_url = self.config_manager.get_ollama_url(model_name)
        endpoint = f"{ollama_url}/api/tags"

        try:
            response = await self.http_client.get(
                endpoint, timeout=model_config.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])

        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Failed to connect to Ollama: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"Ollama returned status {e.response.status_code}") from e

    async def health_check(self, model_name: str) -> bool:
        """
        Check if an Ollama instance is healthy.

        Args:
            model_name: Name of the model configuration to check

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.list_models(model_name)
            return True
        except Exception:
            return False


# Global Ollama client instance
ollama_client = OllamaClient()


async def get_ollama_client() -> OllamaClient:
    """Get the global Ollama client instance."""
    return ollama_client
