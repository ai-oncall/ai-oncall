import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from src.utils.config import config
from src.utils.logging import get_logger
from src.data.models import MessageRequest, MessageResponse, HealthResponse, MessageContext
from src.core.message_processor import MessageProcessor

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI OnCall Bot",
    description="Multi-channel AI assistant for support and workflow automation",
    version="0.1.0",
)

# Initialize message processor
message_processor = MessageProcessor()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Enhanced health check endpoint."""
    return HealthResponse(
        status="healthy", 
        version="0.1.0",
        debug=config.debug,
        openai_configured=bool(config.openai_api_key),
        openai_base_url=config.openai_base_url if config.openai_base_url else None,
        timestamp=datetime.now()
    )

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI OnCall Bot - Multi-channel assistant"}

@app.post("/process-message", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    """Process a message through the AI system and return the response."""
    logger.info("Processing message via API", 
                user_id=request.user_id, 
                channel_type=request.channel_type,
                message_length=len(request.message))
    
    try:
        # Create message context from request
        context = MessageContext(
            user_id=request.user_id,
            channel_id=request.channel_id,
            channel_type=request.channel_type,
            message_text=request.message,
            timestamp=datetime.now()
        )
        
        # Process the message using API-specific method
        result = await message_processor.process_api_message(context)
        
        # Parse classification from result
        classification = {
            "type": result.classification_type,
            "confidence": 0.8,  # Default confidence
            "workflow_executed": result.workflow_executed,
            "workflow_name": result.workflow_name
        }
        
        # Return response
        return MessageResponse(
            success=not result.error_occurred,
            message_id=result.message_id,
            classification=classification,
            response=result.ai_response,
            processing_time_ms=result.processing_time_ms,
            workflow_executed=result.workflow_executed,
            workflow_name=result.workflow_name,
            tokens_used=result.tokens_used or 0,
            error_message=result.error_message if result.error_occurred else None
        )
        
    except Exception as e:
        logger.error("API message processing failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Message processing failed: {str(e)}"
        )

def main():
    """Main application entry point."""
    logger.info("Starting AI OnCall Bot", config=config.model_dump())
    
    # Start the FastAPI server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.port)

if __name__ == "__main__":
    main() 