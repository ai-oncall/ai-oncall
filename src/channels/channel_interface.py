from abc import ABC, abstractmethod
from typing import Any, Dict
from src.data.models import MessageContext

class ChannelAdapter(ABC):
    @abstractmethod
    async def send_message(self, context: MessageContext, message: str) -> Dict[str, Any]:
        """Send a message to the channel."""
        pass

    @abstractmethod
    async def receive_event(self, request: Any) -> Dict[str, Any]:
        """Receive and normalize an event from the channel."""
        pass

    @abstractmethod
    def get_channel_type(self) -> str:
        """Return the channel type identifier (e.g., 'slack', 'teams')."""
        pass 