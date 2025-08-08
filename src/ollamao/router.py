"""FastAPI router with OpenAI-compatible endpoints."""

import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from .auth import APIKeyConfig, api_key_auth, get_request_id
from .config import get_config_manager
from .logging import request_logger
from .models import (
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ModelInfo,
    ModelsResponse,
)
from .ollama_client import OllamaError, get_ollama_client

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    config_manager = get_config_manager()
    available_models = config_manager.list_available_models()

    return HealthResponse(status="healthy", models=available_models, version="0.1.0")


@router.get("/v1/models", response_model=ModelsResponse)
async def list_models(
    current_user: APIKeyConfig = Depends(api_key_auth.get_current_user),
):
    """List available models (OpenAI compatible)."""
    config_manager = get_config_manager()
    models = config_manager.load_models()

    model_data = []
    for model_name, model_config in models.items():
        ollama_url = config_manager.get_ollama_url(model_name)
        model_data.append(
            ModelInfo(
                name=model_name,
                status="available",  # TODO: Check actual status
                ollama_url=ollama_url,
            )
        )

    return ModelsResponse(data=model_data)


@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    chat_request: ChatCompletionRequest,
    current_user: APIKeyConfig = Depends(api_key_auth.get_current_user),
):
    """OpenAI-compatible chat completions endpoint."""
    request_id = get_request_id(request)

    # Start request logging
    log_context = request_logger.log_request_start(
        request_id=request_id,
        method="POST",
        path="/v1/chat/completions",
        model=chat_request.model,
        api_key=current_user.name,
    )

    try:
        ollama_client = await get_ollama_client()

        if chat_request.stream:
            return StreamingResponse(
                _stream_chat_completion(
                    ollama_client, chat_request, request_id, log_context
                ),
                media_type="text/plain",
                headers={"X-Request-ID": request_id},
            )
        else:
            return await _non_stream_chat_completion(
                ollama_client, chat_request, request_id, log_context
            )

    except OllamaError as e:
        request_logger.log_request_complete(log_context, status_code=503, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message=str(e), type="service_unavailable", code="ollama_error"
                )
            ).model_dump(),
        )
    except Exception as e:
        request_logger.log_request_complete(log_context, status_code=500, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message="Internal server error",
                    type="internal_error",
                    code="server_error",
                )
            ).model_dump(),
        )


async def _non_stream_chat_completion(
    ollama_client,
    chat_request: ChatCompletionRequest,
    request_id: str,
    log_context: dict,
) -> ChatCompletionResponse:
    """Handle non-streaming chat completion."""
    # Convert OpenAI format to Ollama format
    ollama_messages = [
        {"role": msg.role, "content": msg.content} for msg in chat_request.messages
    ]

    # Prepare kwargs for Ollama
    kwargs = {}
    if chat_request.temperature is not None:
        kwargs["temperature"] = chat_request.temperature
    if chat_request.max_tokens is not None:
        kwargs["max_tokens"] = chat_request.max_tokens

    # Get single response from Ollama
    response_generator = ollama_client.chat_completion(
        model=chat_request.model, messages=ollama_messages, stream=False, **kwargs
    )

    ollama_response = None
    async for chunk in response_generator:
        ollama_response = chunk
        break  # Should only be one response for non-streaming

    if not ollama_response:
        raise OllamaError("No response received from Ollama")

    # Extract token counts
    prompt_tokens = ollama_response.get("prompt_eval_count", 0)
    completion_tokens = ollama_response.get("eval_count", 0)

    # Convert Ollama response to OpenAI format
    openai_response = ChatCompletionResponse(
        id=f"chatcmpl-{request_id}",
        created=int(time.time()),
        model=chat_request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(
                    role="assistant",
                    content=ollama_response.get("message", {}).get("content", ""),
                ),
                finish_reason="stop" if ollama_response.get("done", False) else None,
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )

    # Log completion
    request_logger.log_request_complete(
        log_context,
        status_code=200,
        tokens_prompt=prompt_tokens,
        tokens_response=completion_tokens,
    )

    return openai_response


async def _stream_chat_completion(
    ollama_client,
    chat_request: ChatCompletionRequest,
    request_id: str,
    log_context: dict,
) -> AsyncGenerator[str, None]:
    """Handle streaming chat completion."""
    completion_id = f"chatcmpl-{request_id}"
    created_time = int(time.time())

    # Convert OpenAI format to Ollama format
    ollama_messages = [
        {"role": msg.role, "content": msg.content} for msg in chat_request.messages
    ]

    # Prepare kwargs for Ollama
    kwargs = {}
    if chat_request.temperature is not None:
        kwargs["temperature"] = chat_request.temperature
    if chat_request.max_tokens is not None:
        kwargs["max_tokens"] = chat_request.max_tokens

    try:
        first_chunk = True
        prompt_tokens = 0
        completion_tokens = 0

        async for ollama_chunk in ollama_client.chat_completion(
            model=chat_request.model, messages=ollama_messages, stream=True, **kwargs
        ):
            # Extract token counts when available
            if "prompt_eval_count" in ollama_chunk:
                prompt_tokens = ollama_chunk["prompt_eval_count"]
            if "eval_count" in ollama_chunk:
                completion_tokens = ollama_chunk["eval_count"]

            # Create OpenAI-compatible chunk
            if first_chunk:
                # First chunk includes role
                delta = ChatCompletionChunkDelta(role="assistant", content="")
                first_chunk = False
            else:
                # Subsequent chunks have content
                content = ollama_chunk.get("message", {}).get("content", "")
                delta = ChatCompletionChunkDelta(content=content)

            chunk = ChatCompletionChunk(
                id=completion_id,
                created=created_time,
                model=chat_request.model,
                choices=[
                    ChatCompletionChunkChoice(
                        index=0,
                        delta=delta,
                        finish_reason=(
                            "stop" if ollama_chunk.get("done", False) else None
                        ),
                    )
                ],
            )

            # Format as SSE (Server-Sent Events)
            yield f"data: {chunk.model_dump_json()}\n\n"

            # Send final chunk if done
            if ollama_chunk.get("done", False):
                final_chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=created_time,
                    model=chat_request.model,
                    choices=[
                        ChatCompletionChunkChoice(
                            index=0,
                            delta=ChatCompletionChunkDelta(),
                            finish_reason="stop",
                        )
                    ],
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                break

        # Log completion
        request_logger.log_request_complete(
            log_context,
            status_code=200,
            tokens_prompt=prompt_tokens,
            tokens_response=completion_tokens,
        )

    except Exception as e:
        # Log error and send error chunk
        request_logger.log_request_complete(log_context, status_code=500, error=str(e))

        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error",
                "code": "streaming_error",
            }
        }
        yield f"data: {error_chunk}\n\n"
        yield "data: [DONE]\n\n"
