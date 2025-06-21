import asyncio
from fastapi import FastAPI
from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI OnCall Bot",
    description="Multi-channel AI assistant for support and workflow automation",
    version="0.1.0",
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "version": "0.1.0",
        "debug": config.debug
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AI OnCall Bot - Multi-channel assistant"}

def main():
    """Main application entry point."""
    logger.info("Starting AI OnCall Bot", config=config.model_dump())
    
    # Start the FastAPI server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.port)

if __name__ == "__main__":
    main() 