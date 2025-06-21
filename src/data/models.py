"""Data models for the AI OnCall Bot."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MessageContext(BaseModel):
    """Context for processing messages from different channels."""
    
    user_id: str = Field(..., description="User identifier from the channel")
    channel_id: str = Field(..., description="Channel identifier")
    channel_type: str = Field(..., description="Type of channel (slack, teams, etc.)")
    message_text: str = Field(..., description="The actual message content")
    timestamp: Optional[datetime] = Field(default=None, description="Message timestamp")
    thread_ts: Optional[str] = Field(default=None, description="Thread timestamp for threaded messages")
    is_mention: Optional[bool] = Field(default=False, description="Whether this is a mention of the bot")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional channel-specific metadata")


class ProcessingResult(BaseModel):
    """Result of processing a message."""
    
    message_id: str = Field(..., description="Unique identifier for the processed message")
    channel_type: str = Field(..., description="Type of channel the message came from")
    classification_type: str = Field(..., description="AI classification of the message")
    response_sent: bool = Field(default=False, description="Whether a response was sent")
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    workflow_executed: bool = Field(default=False, description="Whether a workflow was executed")
    workflow_name: str = Field(default="", description="Name of the executed workflow")
    has_context: bool = Field(default=False, description="Whether conversation context was used")
    error_occurred: bool = Field(default=False, description="Whether an error occurred")
    error_message: str = Field(default="", description="Error message if error occurred")
    escalation_triggered: bool = Field(default=False, description="Whether escalation was triggered")
    knowledge_base_used: bool = Field(default=False, description="Whether knowledge base was queried")
    ai_response: Optional[str] = Field(default=None, description="AI-generated response")
    tokens_used: Optional[int] = Field(default=None, description="Number of AI tokens used")


class WorkflowDefinition(BaseModel):
    """Definition of a workflow for processing messages."""
    
    name: str = Field(..., description="Workflow name")
    trigger_conditions: Dict[str, Any] = Field(..., description="Conditions that trigger this workflow")
    actions: list[Dict[str, Any]] = Field(..., description="Actions to execute")
    priority: int = Field(default=1, description="Workflow priority (higher = more important)")
    enabled: bool = Field(default=True, description="Whether this workflow is enabled")


# API Models for direct message processing
class MessageRequest(BaseModel):
    """Request model for message processing API."""
    message: str = Field(..., description="The message text to process", min_length=1)
    user_id: str = Field(default="api-user", description="User ID (for context)")
    channel_type: str = Field(default="api", description="Channel type")
    channel_id: str = Field(default="api-channel", description="Channel ID")
    include_context: bool = Field(default=False, description="Whether to include conversation context")


class MessageResponse(BaseModel):
    """Response model for message processing API."""
    success: bool = Field(..., description="Whether the processing was successful")
    message_id: str = Field(..., description="Unique message identifier")
    classification: Dict[str, Any] = Field(..., description="AI classification result")
    response: Optional[str] = Field(None, description="Generated response")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    workflow_executed: bool = Field(False, description="Whether a workflow was executed")
    workflow_name: str = Field("", description="Name of executed workflow")
    tokens_used: int = Field(0, description="AI tokens consumed")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class HealthResponse(BaseModel):
    """Enhanced health check response model."""
    status: str
    version: str
    debug: bool
    openai_configured: bool
    openai_base_url: Optional[str] = None
    timestamp: datetime 