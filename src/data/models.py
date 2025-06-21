from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class MessageContext(BaseModel):
    user_id: str
    channel_id: str
    channel_type: str  # e.g., 'slack', 'teams', 'discord', 'email'
    thread_ts: Optional[str] = None
    message_text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict) 