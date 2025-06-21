"""Slack channel adapter implementation."""
from typing import Dict, Any
from src.channels.channel_interface import ChannelAdapter
from src.data.models import MessageContext
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SlackAdapter(ChannelAdapter):
    """Slack-specific implementation of the channel adapter."""
    
    def __init__(self):
        """Initialize the Slack adapter."""
        # In production, this would initialize the Slack Bolt app
        logger.info("Initializing Slack adapter")
    
    async def send_message(self, context: MessageContext, message: str) -> Dict[str, Any]:
        """Send a message to Slack."""
        logger.info("Sending message to Slack", channel_id=context.channel_id)
        
        # Mock Slack API call for testing
        # In production, this would use the Slack Bolt client
        return {
            "ok": True,
            "ts": "1234567890.123",
            "channel": context.channel_id,
            "message": message
        }
    
    async def receive_event(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming Slack event."""
        logger.info("Processing Slack event", event_type=request.get("type"))
        
        # Parse Slack event into MessageContext
        parsed_context = self._parse_slack_event(request)
        
        return {
            "parsed_context": parsed_context,
            "is_thread_reply": bool(request.get("thread_ts")),
            "event_type": request.get("type")
        }
    
    def get_channel_type(self) -> str:
        """Return the channel type."""
        return "slack"
    
    def _parse_slack_event(self, event: Dict[str, Any]) -> MessageContext:
        """Parse Slack event into MessageContext."""
        return MessageContext(
            user_id=event.get("user", "unknown"),
            channel_id=event.get("channel", "unknown"),
            channel_type="slack",
            message_text=self._clean_slack_message(event.get("text", "")),
            thread_ts=event.get("thread_ts"),
            is_mention=event.get("type") == "app_mention" or "<@" in event.get("text", ""),
            metadata={
                "ts": event.get("ts"),
                "event_type": event.get("type"),
                "raw_event": event
            }
        )
    
    def _clean_slack_message(self, text: str) -> str:
        """Clean Slack message text (remove mentions, formatting, etc.)."""
        import re
        
        # Remove bot mentions
        text = re.sub(r'<@U\w+>', '', text)
        
        # Remove channel mentions  
        text = re.sub(r'<#C\w+\|[\w-]+>', '', text)
        
        # Remove URLs
        text = re.sub(r'<http[^>]+>', '', text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip() 