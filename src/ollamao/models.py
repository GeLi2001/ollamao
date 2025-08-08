"""Pydantic models for OpenAI-compatible API requests and responses."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# Request models (OpenAI compatible)


class ChatMessage(BaseModel):
    """A single chat message."""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="The role of the message author"
    )
    content: str = Field(..., description="The content of the message")
    name: Optional[str] = Field(
        None, description="Optional name for the message author"
    )


class ChatCompletionRequest(BaseModel):
    """Request for chat completion endpoint."""

    model: str = Field(..., description="Model to use for completion")
    messages: List[ChatMessage] = Field(
        ..., description="List of messages in the conversation"
    )

    # Generation parameters
    temperature: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )
    frequency_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Presence penalty"
    )

    # Response format
    stream: bool = Field(False, description="Whether to stream the response")

    # Additional parameters
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    user: Optional[str] = Field(None, description="User ID for tracking")


# Response models (OpenAI compatible)


class ChatCompletionUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        ..., description="Number of tokens in the completion"
    )
    total_tokens: int = Field(..., description="Total number of tokens")


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""

    index: int = Field(..., description="Index of the choice")
    message: ChatMessage = Field(..., description="The generated message")
    finish_reason: Optional[Literal["stop", "length", "content_filter"]] = Field(
        None, description="Reason the completion finished"
    )


class ChatCompletionResponse(BaseModel):
    """Response from chat completion endpoint."""

    id: str = Field(..., description="Unique ID for the completion")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for completion")
    choices: List[ChatCompletionChoice] = Field(
        ..., description="List of completion choices"
    )
    usage: Optional[ChatCompletionUsage] = Field(
        None, description="Token usage information"
    )


# Streaming response models


class ChatCompletionChunkDelta(BaseModel):
    """Delta content in a streaming chunk."""

    role: Optional[str] = Field(None, description="Role (only in first chunk)")
    content: Optional[str] = Field(None, description="Content delta")


class ChatCompletionChunkChoice(BaseModel):
    """A single choice in a streaming chunk."""

    index: int = Field(..., description="Index of the choice")
    delta: ChatCompletionChunkDelta = Field(..., description="Delta content")
    finish_reason: Optional[Literal["stop", "length", "content_filter"]] = Field(
        None, description="Reason the completion finished"
    )


class ChatCompletionChunk(BaseModel):
    """A chunk in a streaming response."""

    id: str = Field(..., description="Unique ID for the completion")
    object: str = Field("chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for completion")
    choices: List[ChatCompletionChunkChoice] = Field(
        ..., description="List of choice chunks"
    )


# Error response models


class ErrorDetail(BaseModel):
    """Error detail information."""

    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    param: Optional[str] = Field(None, description="Parameter that caused the error")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Error response from the API."""

    error: ErrorDetail = Field(..., description="Error details")


# Internal models for Ollama communication


class OllamaMessage(BaseModel):
    """Message format for Ollama API."""

    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class OllamaRequest(BaseModel):
    """Request format for Ollama API."""

    model: str = Field(..., description="Model name")
    messages: List[OllamaMessage] = Field(..., description="Messages")
    stream: bool = Field(False, description="Whether to stream")
    options: Optional[Dict[str, Any]] = Field(None, description="Model options")


class OllamaResponse(BaseModel):
    """Response format from Ollama API."""

    model: str = Field(..., description="Model name")
    created_at: str = Field(..., description="Creation timestamp")
    message: Optional[OllamaMessage] = Field(None, description="Generated message")
    done: bool = Field(..., description="Whether generation is complete")
    total_duration: Optional[int] = Field(
        None, description="Total duration in nanoseconds"
    )
    load_duration: Optional[int] = Field(None, description="Model load duration")
    prompt_eval_count: Optional[int] = Field(
        None, description="Number of prompt tokens"
    )
    prompt_eval_duration: Optional[int] = Field(
        None, description="Prompt evaluation duration"
    )
    eval_count: Optional[int] = Field(None, description="Number of generated tokens")
    eval_duration: Optional[int] = Field(None, description="Generation duration")


# Health check models


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"] = Field(
        ..., description="Service health status"
    )
    models: List[str] = Field(..., description="Available models")
    version: str = Field(..., description="Service version")


class ModelInfo(BaseModel):
    """Information about a model."""

    name: str = Field(..., description="Model name")
    status: Literal["available", "unavailable"] = Field(..., description="Model status")
    ollama_url: Optional[str] = Field(None, description="Ollama backend URL")


class ModelsResponse(BaseModel):
    """Response listing available models."""

    object: str = Field("list", description="Object type")
    data: List[ModelInfo] = Field(..., description="List of models")
