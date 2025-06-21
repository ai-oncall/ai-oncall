"""Slack channel adapter implementation."""
import asyncio
import re
from datetime import datetime
from typing import Dict, Any
from slack_bolt.app.async_app import AsyncApp
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from src.channels.channel_interface import ChannelAdapter
from src.data.models import MessageContext
from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SlackAdapter(ChannelAdapter):
    """Slack-specific implementation of the channel adapter."""
    
    def __init__(self):
        """Initialize Slack adapter with necessary client."""
        if not config.slack_bot_token:
            raise ValueError("Slack bot token is required")
            
        self.app = AsyncApp(
            token=config.slack_bot_token,
            signing_secret=config.slack_signing_secret if config.slack_signing_secret else None
        )
        self.bot_id = None
        logger.info("Slack adapter initialized",
                   socket_mode=config.slack_socket_mode,
                   channel_id=config.slack_channel_id)
    
    async def _get_bot_id(self):
        """Get the bot's user ID from Slack."""
        if not self.bot_id:
            try:
                auth_result = await self.app.client.auth_test()
                self.bot_id = auth_result["user_id"]
                logger.info("Retrieved bot ID", bot_id=self.bot_id)
            except Exception as e:
                logger.error("Failed to get bot ID", error=str(e))
        return self.bot_id
    
    async def send_message(self, context: MessageContext, message: str) -> Dict[str, Any]:
        """Send a message to Slack channel, optionally in a thread."""
        try:
            logger.info("Attempting to send message to Slack",
                       channel_id=context.channel_id,
                       thread_ts=context.thread_ts,
                       message_length=len(message))
            
            response = await self.app.client.chat_postMessage(
                channel=context.channel_id,
                text=message,
                thread_ts=context.thread_ts if context.thread_ts else None
            )
            logger.info("Message sent successfully to Slack",
                       channel_id=context.channel_id,
                       timestamp=response.get("ts"),
                       thread_ts=context.thread_ts)
            return response
        except Exception as e:
            logger.exception("Error sending message to Slack",
                           channel_id=context.channel_id,
                           error=str(e))
            raise
    
    async def receive_event(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming Slack events."""
        try:
            event_type = request.get("type")
            logger.info("Received Slack event", 
                       event_type=event_type,
                       request_id=request.get("event_id"))
            
            if event_type == "url_verification":
                logger.info("Handling URL verification challenge")
                return {"challenge": request["challenge"]}
            
            if event_type == "event_callback":
                event = request["event"]
                if event["type"] == "message" and not event.get("subtype"):
                    logger.info("Processing message event",
                              channel=event.get("channel"),
                              user=event.get("user"),
                              thread_ts=event.get("thread_ts"))
                    return await self._handle_message_event(event)
            
            return {}
        except Exception as e:
            logger.exception("Error processing Slack event",
                           event_type=event_type,
                           error=str(e))
            raise
    
    async def start_socket_mode(self, message_processor):
        """Start Socket Mode client if configured."""
        if not config.slack_app_token:
            logger.warning("Slack app token not configured, Socket Mode disabled")
            return
        
        # Get bot ID first
        await self._get_bot_id()
        
        async def process_socket_event(client: SocketModeClient, req: SocketModeRequest):
            try:
                if req.type == "events_api":
                    # Log raw event for debugging
                    if config.debug:
                        logger.debug("Raw socket mode event", payload=req.payload)
                    
                    # Acknowledge the request immediately
                    await client.send_socket_mode_response(
                        SocketModeResponse(envelope_id=req.envelope_id)
                    )
                    
                    # Process the event
                    event = req.payload["event"]
                    if event["type"] == "message" and not event.get("subtype"):
                        # Ignore messages from the bot itself
                        if event.get("user") == self.bot_id:
                            logger.debug("Ignoring message from bot itself", 
                                       bot_id=self.bot_id,
                                       user_id=event.get("user"))
                            return
                            
                        logger.info("Received message via Socket Mode",
                                  channel=event.get("channel"),
                                  user=event.get("user"),
                                  text=event.get("text", "")[:50],
                                  thread_ts=event.get("thread_ts"))
                        
                        context = self._parse_slack_event(event)
                        try:
                            result = await message_processor.process_message(context)
                            if result and result.response:
                                logger.info("Sending response via Socket Mode",
                                          channel=context.channel_id,
                                          thread_ts=context.thread_ts,
                                          response_length=len(result.response))
                                await self.send_message(context, result.response)
                        except Exception as e:
                            logger.exception("Error processing socket mode message",
                                           channel=context.channel_id,
                                           error=str(e))
            except Exception as e:
                logger.exception("Error in socket mode event handler", error=str(e))
        
        logger.info("Starting Slack Socket Mode client", 
                   app_token=f"{config.slack_app_token[:5]}...{config.slack_app_token[-5:]}")
                   
        # Create the Socket Mode client
        client = SocketModeClient(
            app_token=config.slack_app_token,
            web_client=self.app.client
        )
        
        # Add event listener
        client.socket_mode_request_listeners.append(process_socket_event)
        
        try:
            # Connect and maintain the connection
            await client.connect()
            logger.info("Slack Socket Mode client connected successfully")
            
            # Keep the connection alive with periodic checks
            while True:
                try:
                    is_connected = await client.is_connected()
                    if not is_connected:
                        logger.warning("Socket Mode disconnected, attempting to reconnect")
                        await client.connect()
                    await asyncio.sleep(30)  # Check connection every 30 seconds
                except Exception as e:
                    logger.error("Error in Socket Mode connection maintenance",
                               error=str(e))
                    await asyncio.sleep(5)  # Wait before retry
        except Exception as e:
            logger.exception("Fatal error in Socket Mode connection", error=str(e))
            raise
    
    def get_channel_type(self) -> str:
        """Return channel type identifier."""
        return "slack"
    
    def _parse_slack_event(self, event: Dict[str, Any]) -> MessageContext:
        """Convert Slack event to MessageContext."""
        logger.debug("Parsing Slack event",
                    event_type=event.get("type"),
                    user=event.get("user"),
                    channel=event.get("channel"))
        
        return MessageContext(
            user_id=event["user"],
            channel_id=event["channel"],
            channel_type="slack",
            message_text=event["text"],
            thread_ts=event.get("thread_ts", event.get("ts")),
            is_mention=self._is_bot_mention(event["text"]),
            timestamp=datetime.fromtimestamp(float(event["ts"]))
        )
    
    def _is_bot_mention(self, text: str) -> bool:
        """Check if the message mentions the bot."""
        # Clean up Slack's <@USER_ID> format
        return bool(re.search(r'<@[A-Z0-9]+>', text))