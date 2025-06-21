import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from src.utils.config import config
from src.utils.logging import get_logger
from src.data.models import MessageRequest, MessageResponse, HealthResponse, MessageContext
from src.core.message_processor import MessageProcessor

logger = get_logger(__name__)

# Initialize message processor
message_processor = MessageProcessor()

# Initialize Slack app if credentials are configured
slack_app: AsyncApp | None = None
slack_handler: AsyncSlackRequestHandler | None = None

if config.slack_bot_token and config.slack_signing_secret:
    slack_app = AsyncApp(
        token=config.slack_bot_token,
        signing_secret=config.slack_signing_secret,
        process_before_response=True,
    )
    
    # Set up Slack event handlers
    @slack_app.event("app_mention")
    async def handle_app_mention(event, say, ack):
        """Handle @bot mentions."""
        await ack()
        logger.info("App mention received", user=event["user"], channel=event["channel"])
        
        # Create message context
        context = MessageContext(
            user_id=event["user"],
            channel_id=event["channel"],
            channel_type="slack",
            message_text=event["text"],
            thread_ts=event.get("thread_ts"),
            is_mention=True,
            metadata={"ts": event["ts"], "event_type": "app_mention"}
        )
        
        # Process message
        result = await message_processor.process_message(context)
        
        # Send response
        if result.response_text:
            await say(
                text=result.response_text,
                thread_ts=event.get("ts")  # Reply in thread
            )
    
    @slack_app.event("message")
    async def handle_message(event, say, ack):
        """Handle direct messages to the bot."""
        await ack()
        
        # Skip bot messages and threaded messages that aren't mentions
        if event.get("subtype") == "bot_message" or event.get("bot_id"):
            return
            
        # Only respond to DMs or if bot is mentioned
        if event.get("channel_type") != "im" and "<@" not in event.get("text", ""):
            return
            
        logger.info("Message received", user=event["user"], channel=event["channel"])
        
        # Create message context
        context = MessageContext(
            user_id=event["user"],
            channel_id=event["channel"],
            channel_type="slack",
            message_text=event["text"],
            thread_ts=event.get("thread_ts"),
            is_mention="<@" in event.get("text", ""),
            metadata={"ts": event["ts"], "event_type": "message"}
        )
        
        # Process message
        result = await message_processor.process_message(context)
        
        # Send response
        if result.response_text:
            await say(
                text=result.response_text,
                thread_ts=event.get("ts")  # Reply in thread
            )
    
    slack_handler = AsyncSlackRequestHandler(slack_app)
    logger.info("Slack bot initialized successfully")
else:
    logger.warning("Slack credentials not configured - Slack integration disabled")

# Initialize FastAPI app
app = FastAPI(
    title="AI OnCall Bot",
    description="Multi-channel AI assistant for support and workflow automation",
    version="0.1.0",
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI OnCall Bot - Multi-channel assistant"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Enhanced health check endpoint."""
    return HealthResponse(
        status="healthy", 
        version="0.1.0",
        debug=config.debug,
        openai_configured=bool(config.openai_api_key),
        openai_base_url=config.openai_base_url if config.openai_base_url else None,
        slack_configured=bool(config.slack_bot_token and config.slack_signing_secret),
        timestamp=datetime.now()
    )

@app.post("/process-message", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """Process a message from any channel."""
    try:
        # Create message context
        context = MessageContext(
            user_id=request.user_id,
            channel_id=request.channel_id,
            channel_type=request.channel_type,
            message_text=request.message,
            thread_ts=request.thread_ts,
            is_mention=request.is_mention,
            metadata=request.metadata or {}
        )
        
        # Process the message
        result = await message_processor.process_message(context)
        
        return MessageResponse(
            response_text=result.response_text,
            classification_type=result.classification_type,
            confidence=result.confidence,
            workflow_executed=result.workflow_executed,
            escalation_triggered=result.escalation_triggered,
            processing_time_ms=result.processing_time_ms,
            response_sent=result.response_sent,
            error_occurred=result.error_occurred,
            error_message=result.error_message
        )
        
    except Exception as e:
        logger.error("Error processing message", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

# Slack webhook endpoint
if slack_handler:
    @app.post("/slack/events")
    async def slack_events(request):
        """Handle Slack events."""
        if slack_handler is None:
            raise HTTPException(status_code=503, detail="Slack not configured")
        return await slack_handler.handle(request)

async def main():
    """Main application entry point."""
    logger.info("Starting AI OnCall Bot", config_debug=config.debug)
    
    # Socket Mode for development
    if slack_app is not None and config.slack_socket_mode:
        logger.info("Starting Slack app in Socket Mode")
        await slack_app.start()  # type: ignore
        return
    
    # HTTP mode for production
    logger.info(f"Starting HTTP server on port {config.port}")
    import uvicorn
    config_server = uvicorn.Config(app, host="0.0.0.0", port=config.port)
    server = uvicorn.Server(config_server)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main()) 