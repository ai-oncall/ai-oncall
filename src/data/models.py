"""Data models for the AI OnCall Bot."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MessageContext(BaseModel):
    """Context for processing messages from different channels."""

    message_id: str = Field(..., description="Unique message identifier")
    user_id: str = Field(..., description="User identifier from the channel")
    channel_id: str = Field(..., description="Channel identifier")
    channel_type: str = Field(..., description="Type of channel (slack, teams, etc.)")
    message_text: str = Field(..., description="The actual message content")
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp")
    thread_ts: Optional[str] = Field(
        default=None, description="Thread timestamp for threaded messages"
    )
    is_mention: Optional[bool] = Field(
        default=False, description="Whether this is a mention of the bot"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional channel-specific metadata"
    )


class ProcessingResult(BaseModel):
    """Result of processing a message through a workflow."""

    # Required fields
    response: str = Field(..., description="The response to send back")

    # Classification
    classification: Optional[str] = Field(
        default=None,
        description="The message type (knowledge_query, incident, support_request)",
    )
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score of classification"
    )

    # Workflow info
    workflow_id: str = Field(
        default="unknown", description="ID of the executed workflow"
    )
    workflow_executed: bool = Field(
        default=False, description="Whether a workflow was executed"
    )
    knowledge_base_used: bool = Field(
        default=False, description="Whether knowledge base was queried"
    )
    escalation_triggered: bool = Field(
        default=False, description="Whether escalation was triggered"
    )

    # Error handling
    error: Optional[str] = Field(default=None, description="Error message if any")
    error_occurred: bool = Field(default=False, description="Whether an error occurred")

    # Metrics
    tokens_used: Optional[int] = Field(
        default=None, description="Number of AI tokens used"
    )
    latency_ms: Optional[int] = Field(
        default=None, description="Processing time in milliseconds"
    )

    @property
    def has_error(self) -> bool:
        """Whether there was an error during processing."""
        return self.error_occurred or bool(self.error)


class WorkflowDefinition(BaseModel):
    """Definition of a workflow for processing messages."""

    name: str = Field(..., description="Workflow name")
    trigger_conditions: Dict[str, Any] = Field(
        ..., description="Conditions that trigger this workflow"
    )
    actions: list[Dict[str, Any]] = Field(..., description="Actions to execute")
    priority: int = Field(
        default=1, description="Workflow priority (higher = more important)"
    )
    enabled: bool = Field(default=True, description="Whether this workflow is enabled")


# API Models for direct message processing
class MessageRequest(BaseModel):
    """Request model for message processing API."""

    message: str = Field(..., description="The message text to process", min_length=1)
    user_id: str = Field(default="api-user", description="User ID (for context)")
    channel_type: str = Field(default="api", description="Channel type")
    channel_id: str = Field(default="api-channel", description="Channel ID")
    thread_ts: Optional[str] = Field(default=None, description="Thread timestamp")
    is_mention: bool = Field(default=False, description="Whether this is a mention")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )
    include_context: bool = Field(
        default=False, description="Whether to include conversation context"
    )


class MessageResponse(BaseModel):
    """Response model for message processing API."""

    response_text: Optional[str] = Field(None, description="Generated response text")
    classification_type: str = Field(..., description="AI classification type")
    confidence: float = Field(default=0.0, description="Classification confidence")
    workflow_executed: bool = Field(
        False, description="Whether a workflow was executed"
    )
    escalation_triggered: bool = Field(
        False, description="Whether escalation was triggered"
    )
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    response_sent: bool = Field(False, description="Whether response was sent")
    error_occurred: bool = Field(False, description="Whether an error occurred")
    error_message: Optional[str] = Field(
        None, description="Error message if processing failed"
    )


class HealthResponse(BaseModel):
    """Enhanced health check response model."""

    status: str
    version: str
    debug: bool
    openai_configured: bool
    openai_base_url: Optional[str] = None
    slack_configured: bool = False
    knowledge_base_initialized: bool = False
    timestamp: datetime
