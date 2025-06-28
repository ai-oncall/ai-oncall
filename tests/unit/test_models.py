"""Tests for data models."""
from datetime import datetime
from src.data.models import MessageContext, ProcessingResult, WorkflowDefinition


class TestMessageContext:
    """Tests for MessageContext model."""

    def test_message_context_creation(self):
        """Test MessageContext can be created with required fields."""
        context = MessageContext(
            user_id="user123",
            channel_id="channel456",
            channel_type="slack",
            message_text="Test message"
        )
        
        assert context.user_id == "user123"
        assert context.channel_id == "channel456"
        assert context.channel_type == "slack"
        assert context.message_text == "Test message"
        assert context.thread_ts is None
        assert context.timestamp is None  # Updated to match new model
        assert context.is_mention is False
        assert isinstance(context.metadata, dict)

    def test_message_context_with_optional_fields(self):
        """Test MessageContext with optional fields."""
        metadata = {"source": "api", "priority": "high"}
        timestamp = datetime.now()
        
        context = MessageContext(
            user_id="user123",
            channel_id="channel456",
            channel_type="teams",
            message_text="Test message",
            timestamp=timestamp,
            thread_ts="1234567890.123",
            is_mention=True,
            metadata=metadata
        )
        
        assert context.thread_ts == "1234567890.123"
        assert context.timestamp == timestamp
        assert context.is_mention is True
        assert context.metadata == metadata
        assert context.channel_type == "teams"

    def test_message_context_different_channels(self):
        """Test MessageContext works with different channel types."""
        slack_context = MessageContext(
            user_id="slack_user",
            channel_id="slack_channel",
            channel_type="slack",
            message_text="Slack message"
        )
        
        teams_context = MessageContext(
            user_id="teams_user",
            channel_id="teams_channel",
            channel_type="teams",
            message_text="Teams message"
        )
        
        assert slack_context.channel_type == "slack"
        assert teams_context.channel_type == "teams"

    def test_message_context_mention_detection(self):
        """Test mention detection in MessageContext."""
        mention_context = MessageContext(
            user_id="user123",
            channel_id="channel456",
            channel_type="slack",
            message_text="<@UBOT123> help me",
            is_mention=True
        )
        
        assert mention_context.is_mention is True
        assert "<@UBOT123>" in mention_context.message_text


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_processing_result_creation(self):
        """Test ProcessingResult with required fields."""
        result = ProcessingResult(
            response="I can help you with that request.",
            classification="support_request"
        )
        
        assert result.response == "I can help you with that request."
        assert result.classification == "support_request"
        assert result.confidence == 0.0
        assert result.workflow_executed is False
        assert result.error_occurred is False

    def test_processing_result_with_workflow(self):
        """Test ProcessingResult with workflow execution."""
        result = ProcessingResult(
            response="Incident acknowledged",
            classification="incident",
            confidence=0.9,
            workflow_executed=True,
            workflow_name="incident_response",
            escalation_triggered=True,
            ai_response="Incident acknowledged",
            tokens_used=150
        )
        
        assert result.workflow_executed is True
        assert result.workflow_name == "incident_response"
        assert result.escalation_triggered is True
        assert result.ai_response == "Incident acknowledged"
        assert result.tokens_used == 150
        assert result.confidence == 0.9

    def test_processing_result_with_error(self):
        """Test ProcessingResult with error state."""
        result = ProcessingResult(
            response="I apologize, but I encountered an error processing your request.",
            classification="error",
            error_occurred=True,
            error_message="AI API unavailable"
        )
        
        assert result.error_occurred is True
        assert result.error_message == "AI API unavailable"
        assert result.classification == "error"

    def test_processing_result_knowledge_base(self):
        """Test ProcessingResult with knowledge base usage."""
        result = ProcessingResult(
            response="Here's the information from our knowledge base...",
            classification="knowledge_query",
            workflow_executed=True,
            workflow_name="knowledge_base_lookup",
            knowledge_base_used=True
        )
        
        assert result.knowledge_base_used is True
        assert result.workflow_name == "knowledge_base_lookup"


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition model."""

    def test_workflow_definition_creation(self):
        """Test WorkflowDefinition creation."""
        workflow = WorkflowDefinition(
            name="test_workflow",
            trigger_conditions={"type": "support_request"},
            actions=[{"type": "create_ticket"}]
        )
        
        assert workflow.name == "test_workflow"
        assert workflow.trigger_conditions == {"type": "support_request"}
        assert workflow.actions == [{"type": "create_ticket"}]
        assert workflow.priority == 1  # default
        assert workflow.enabled is True  # default

    def test_workflow_definition_with_priority(self):
        """Test WorkflowDefinition with custom priority."""
        workflow = WorkflowDefinition(
            name="high_priority_workflow",
            trigger_conditions={"type": "incident", "severity": "critical"},
            actions=[
                {"type": "escalate", "level": "urgent"}, 
                {"type": "create_ticket", "priority": "high"}
            ],
            priority=10,
            enabled=True
        )
        
        assert workflow.priority == 10
        assert len(workflow.actions) == 2
        assert workflow.actions[0]["type"] == "escalate"

    def test_workflow_definition_disabled(self):
        """Test WorkflowDefinition when disabled."""
        workflow = WorkflowDefinition(
            name="disabled_workflow",
            trigger_conditions={"type": "test"},
            actions=[{"type": "log"}],
            enabled=False
        )
        
        assert workflow.enabled is False 