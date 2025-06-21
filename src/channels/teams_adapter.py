"""Teams channel adapter implementation."""
from typing import Dict, Any
from src.channels.channel_interface import ChannelAdapter
from src.data.models import MessageContext
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TeamsAdapter(ChannelAdapter):
    """Teams-specific implementation of the channel adapter."""
    
    def __init__(self):
        """Initialize the Teams adapter."""
        logger.info("Initializing Teams adapter")
    
    async def send_message(self, context: MessageContext, message: str) -> Dict[str, Any]:
        """Send a message to Teams."""
        logger.info("Sending message to Teams", channel_id=context.channel_id)
        
        # Mock Teams API call for testing
        return {
            "success": True,
            "id": "teams-msg-123",
            "conversationId": context.channel_id,
            "message": message
        }
    
    async def receive_event(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming Teams event."""
        logger.info("Processing Teams event", event_type=request.get("type"))
        
        # Parse Teams event into MessageContext
        parsed_context = self._parse_teams_event(request)
        
        return {
            "parsed_context": parsed_context,
            "is_thread_reply": bool(request.get("replyToId")),
            "event_type": request.get("type")
        }
    
    def get_channel_type(self) -> str:
        """Return the channel type."""
        return "teams"
    
    def _parse_teams_event(self, event: Dict[str, Any]) -> MessageContext:
        """Parse Teams event into MessageContext."""
        return MessageContext(
            user_id=event.get("from", {}).get("id", "unknown"),
            channel_id=event.get("conversation", {}).get("id", "unknown"),
            channel_type="teams",
            message_text=event.get("text", ""),
            thread_ts=event.get("replyToId"),
            is_mention="@" in event.get("text", ""),
            metadata={
                "id": event.get("id"),
                "timestamp": event.get("timestamp"),
                "event_type": event.get("type"),
                "raw_event": event
            }
        ) 