"""Main application entry point."""
import asyncio
import uuid
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from src.utils.config import config
from src.utils.logging import get_logger
from src.data.models import MessageRequest, MessageResponse, HealthResponse, MessageContext
from src.core.message_processor import MessageProcessor
from src.channels.slack_adapter import SlackAdapter

logger = get_logger(__name__)

# Knowledge base initialization
try:
    from src.knowledge.kb_manager import KnowledgeBaseManager
    knowledge_base = KnowledgeBaseManager()
    
    # Load documents from knowledge-base folder at startup
    try:
        files_processed = knowledge_base.bulk_add_from_directory("knowledge-base")
        if files_processed > 0:
            logger.info("Knowledge base initialized successfully", 
                       files_processed=files_processed,
                       collection_info=knowledge_base.get_collection_info())
        else:
            logger.warning("No documents found in knowledge-base folder")
    except Exception as e:
        logger.error("Failed to initialize knowledge base", error=str(e))
        knowledge_base = None
        
except ImportError:
    logger.warning("ChromaDB not available, knowledge base disabled")
    knowledge_base = None

# Initialize message processor
message_processor = MessageProcessor()

# Initialize Slack app if credentials are configured
slack_app: AsyncApp | None = None
slack_handler: AsyncSlackRequestHandler | None = None
slack_adapter: SlackAdapter | None = None

if config.slack_bot_token:
    logger.info("Initializing Slack app", 
                socket_mode=config.slack_socket_mode,
                channel_id=config.slack_channel_id)
    
    slack_app = AsyncApp(
        token=config.slack_bot_token,
        signing_secret=config.slack_signing_secret if config.slack_signing_secret else None,
        process_before_response=True
    )
    
    if not config.slack_socket_mode:
        slack_handler = AsyncSlackRequestHandler(slack_app)
    
    slack_adapter = SlackAdapter()
else:
    logger.warning("Slack credentials not configured, Slack integration will be disabled")

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
    """Process an incoming message from any channel."""
    start_time = datetime.now()
    logger.info("Processing message request", channel_type=request.channel_type)
    
    context = MessageContext(
        user_id=request.user_id,
        channel_id=request.channel_id,
        channel_type=request.channel_type,
        message_text=request.message,
        thread_ts=request.thread_ts,
        is_mention=request.is_mention,
        timestamp=datetime.now()
    )
    
    try:
        result = await message_processor.process_message(context)
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return MessageResponse(
            response_text=result.response,
            classification_type=result.classification,
            confidence=result.confidence,
            workflow_executed=result.workflow_executed,
            escalation_triggered=result.escalation_triggered,
            processing_time_ms=processing_time,
            response_sent=True,
            error_occurred=False,
            error_message=None
        )
    except Exception as e:
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.exception("Error processing message")
        
        return MessageResponse(
            response_text=f"Error processing message: {str(e)}",
            classification_type="error",
            confidence=0.0,
            workflow_executed=False,
            escalation_triggered=False,
            processing_time_ms=processing_time,
            response_sent=False,
            error_occurred=True,
            error_message=str(e)
        )

# Slack webhook endpoint
if slack_handler:
    @app.post("/slack/events")
    async def handle_slack_events(request: Request):
        """Handle incoming Slack events."""
        if slack_handler is not None:
            return await slack_handler.handle(request)
        else:
            raise HTTPException(status_code=503, detail="Slack handler not available")

async def main():
    """Main application entry point."""
    logger.info("Starting AI OnCall Bot", config_debug=config.debug)

    tasks = []
    
    # Start Slack Socket Mode if enabled
    if slack_adapter and config.slack_socket_mode:
        if not config.slack_app_token:
            logger.error("Socket Mode enabled but SLACK_APP_TOKEN is missing")
            raise ValueError("SLACK_APP_TOKEN is required for Socket Mode")
            
        logger.info("Starting Slack Socket Mode listener in background task")
        tasks.append(asyncio.create_task(slack_adapter.start_socket_mode(message_processor)))
    elif slack_adapter:
        logger.info("Running in HTTP webhook mode")

    # Start FastAPI server
    config_server = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=config.port,
        log_level=config.log_level.lower()
    )
    server = uvicorn.Server(config_server)
    tasks.append(asyncio.create_task(server.serve()))

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.exception("Error in main execution", error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(main())