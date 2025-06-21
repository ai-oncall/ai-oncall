# Phase 1: Foundation Setup

## 🎯 Phase Overview

This phase establishes the basic project structure, development environment, and foundational components needed for the AI OnCall Bot. We'll set up the repository structure, configure development tools, and create the basic application skeleton.

**Duration**: 3-4 days  
**Dependencies**: None  
**Prerequisites**: Python 3.11+, Git, Docker (optional)

## 📋 Phase Objectives

### Primary Goals
- [ ] Set up project structure and directory layout
- [ ] Configure dependency management with Poetry
- [ ] Implement basic configuration management
- [ ] Set up development tools (linting, formatting, type checking)
- [ ] Create basic logging infrastructure
- [ ] Set up testing framework and initial tests
- [ ] Configure Git hooks and CI/CD pipeline
- [ ] Create basic health check endpoints

### Success Criteria
- Project structure matches architectural design
- All development tools are configured and working
- Basic tests are passing with >90% coverage
- Code quality checks are passing
- Development environment is reproducible

## 🗂️ Directory Structure to Create

```
ai-oncall/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Application entry point
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── slack_handler.py       # Basic Slack event handlers
│   │   ├── message_processor.py   # Message preprocessing
│   │   └── response_builder.py    # Response formatting
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── openai_client.py       # OpenAI client wrapper
│   │   ├── request_classifier.py  # Basic classification
│   │   └── context_manager.py     # Context management
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── flow_parser.py         # YAML parser
│   │   ├── flow_executor.py       # Basic execution
│   │   └── flow_validator.py      # Validation
│   ├── data/
│   │   ├── __init__.py
│   │   ├── models.py              # Pydantic models
│   │   ├── storage.py             # Data persistence
│   │   └── analytics.py           # Basic analytics
│   └── utils/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── logging.py             # Logging setup
│       ├── exceptions.py          # Custom exceptions
│       └── validators.py          # Input validation
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest configuration
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_logging.py
│   │   └── test_models.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_health.py
│   └── fixtures/
│       ├── __init__.py
│       ├── sample_data.json
│       └── test_config.yaml
├── config/
│   ├── flow.yaml                  # Sample workflow
│   ├── settings.yaml              # App settings
│   ├── logging.yaml               # Logging config
│   └── environments/
│       ├── dev.yaml
│       ├── staging.yaml
│       └── prod.yaml
├── scripts/
│   ├── setup.py                   # Setup script
│   ├── run_tests.py               # Test runner
│   └── lint.py                    # Code quality checks
├── docs/                          # Already created
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore patterns
├── .pre-commit-config.yaml        # Pre-commit hooks
├── pyproject.toml                 # Project configuration
├── pytest.ini                    # Pytest configuration
├── Dockerfile                     # Container configuration
├── docker-compose.yml             # Development environment
└── README.md                      # Project documentation
```

## 🛠️ Implementation Tasks

### Task 1: Project Structure Setup

**Files to Create**:
- `pyproject.toml` - Project configuration and dependencies
- `.gitignore` - Git ignore patterns
- `.env.example` - Environment variable template
- `README.md` - Project documentation

**Implementation**:

```toml
# pyproject.toml
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "ai-oncall-bot"
version = "0.1.0"
description = "AI-powered Slack bot for intelligent request handling"
authors = ["Your Team <team@example.com>"]
readme = "README.md"
packages = [{include = "src"}]

[tool.poetry.dependencies]
python = "^3.11"
slack-bolt = "^1.18.0"
phidata = "^2.4.0"
openai = "^1.0.0"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.0.0"
pyyaml = "^6.0.1"
structlog = "^23.2.0"
python-dotenv = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-mock = "^3.12.0"
pytest-cov = "^4.1.0"
black = "^23.11.0"
flake8 = "^6.1.0"
mypy = "^1.7.0"
isort = "^5.12.0"
pre-commit = "^3.5.0"
httpx = "^0.25.0"

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "--cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=90"
asyncio_mode = "auto"
```

### Task 2: Configuration Management

**Files to Create**:
- `src/utils/config.py` - Configuration classes
- `config/settings.yaml` - Default settings
- `config/environments/dev.yaml` - Development configuration

**Configuration Structure**:

```python
# src/utils/config.py
from pydantic import BaseSettings, Field
from typing import Optional, Dict, Any
import yaml
from pathlib import Path

class SlackConfig(BaseSettings):
    """Slack configuration settings."""
    bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    app_token: Optional[str] = Field(None, env="SLACK_APP_TOKEN")
    socket_mode: bool = Field(False, env="SLACK_SOCKET_MODE")

class AIConfig(BaseSettings):
    """AI configuration settings."""
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_api_base: str = Field("https://api.openai.com/v1", env="OPENAI_API_BASE")
    default_model: str = Field("gpt-3.5-turbo", env="DEFAULT_MODEL")
    max_tokens: int = Field(500, env="MAX_TOKENS")
    temperature: float = Field(0.7, env="AI_TEMPERATURE")

class WorkflowConfig(BaseSettings):
    """Workflow configuration settings."""
    config_path: str = Field("./config/workflows/", env="WORKFLOW_CONFIG_PATH")
    reload_interval: int = Field(300, env="WORKFLOW_RELOAD_INTERVAL")
    default_workflow: str = Field("general", env="DEFAULT_WORKFLOW")

class AppConfig(BaseSettings):
    """Main application configuration."""
    slack: SlackConfig = SlackConfig()
    ai: AIConfig = AIConfig()
    workflow: WorkflowConfig = WorkflowConfig()
    
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    port: int = Field(8000, env="PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def load_config(config_file: Optional[str] = None) -> AppConfig:
    """Load configuration from file and environment variables."""
    if config_file and Path(config_file).exists():
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        # Override with environment variables
        return AppConfig(**config_data)
    return AppConfig()

# Global configuration instance
config = load_config()
```

### Task 3: Logging Infrastructure

**Files to Create**:
- `src/utils/logging.py` - Logging configuration
- `config/logging.yaml` - Logging settings

**Logging Implementation**:

```python
# src/utils/logging.py
import structlog
import logging
import sys
from typing import Dict, Any
from .config import config

def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.log_level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not config.debug 
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)

# Initialize logging
configure_logging()
logger = get_logger(__name__)
```

### Task 4: Basic Data Models

**Files to Create**:
- `src/data/models.py` - Core data models

**Data Models**:

```python
# src/data/models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    """Types of messages."""
    MESSAGE = "message"
    APP_MENTION = "app_mention"
    REACTION_ADDED = "reaction_added"

class Intent(str, Enum):
    """Request intent categories."""
    SUPPORT = "support"
    INFORMATION = "information"
    ACTION = "action"
    GENERAL = "general"

class Urgency(str, Enum):
    """Request urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MessageContext(BaseModel):
    """Context information for a Slack message."""
    user_id: str = Field(..., description="Slack user ID")
    channel_id: str = Field(..., description="Slack channel ID")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp")
    message_text: str = Field(..., description="Message text content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: MessageType = Field(default=MessageType.MESSAGE)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RequestClassification(BaseModel):
    """Classification result for a request."""
    intent: Intent = Field(..., description="Detected intent")
    urgency: Urgency = Field(..., description="Urgency level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    entities: List[str] = Field(default_factory=list, description="Extracted entities")
    workflow_id: str = Field(..., description="Assigned workflow ID")

class ConversationSession(BaseModel):
    """Represents a conversation session."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="Slack user ID")
    channel_id: str = Field(..., description="Slack channel ID")
    messages: List[MessageContext] = Field(default_factory=list)
    current_workflow: Optional[str] = Field(None, description="Active workflow")
    status: str = Field(default="active", description="Session status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WorkflowResult(BaseModel):
    """Result of workflow execution."""
    workflow_id: str = Field(..., description="Workflow identifier")
    status: str = Field(..., description="Execution status")
    response_text: str = Field(..., description="Generated response")
    actions_taken: List[str] = Field(default_factory=list)
    next_steps: Optional[List[str]] = Field(None)
    escalation_required: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Task 5: Basic Application Structure

**Files to Create**:
- `src/main.py` - Application entry point
- `src/bot/slack_handler.py` - Basic Slack handler
- `src/utils/exceptions.py` - Custom exceptions

**Application Entry Point**:

```python
# src/main.py
import asyncio
from fastapi import FastAPI
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

from src.utils.config import config
from src.utils.logging import get_logger
from src.bot.slack_handler import SlackHandler

logger = get_logger(__name__)

# Initialize Slack app
slack_app = AsyncApp(
    token=config.slack.bot_token,
    signing_secret=config.slack.signing_secret,
    process_before_response=True,
)

# Initialize FastAPI app
api_app = FastAPI(
    title="AI OnCall Bot",
    description="Intelligent Slack bot for request handling",
    version="0.1.0",
)

# Initialize Slack handler
slack_handler = SlackHandler(slack_app)
app_handler = AsyncSlackRequestHandler(slack_app)

@api_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}

@api_app.post("/slack/events")
async def slack_events(request):
    """Handle Slack events."""
    return await app_handler.handle(request)

async def main():
    """Main application entry point."""
    logger.info("Starting AI OnCall Bot", config=config.dict())
    
    if config.slack.socket_mode:
        # Use Socket Mode for development
        await slack_app.start()
    else:
        # Use HTTP mode for production
        import uvicorn
        uvicorn.run(api_app, host="0.0.0.0", port=config.port)

if __name__ == "__main__":
    asyncio.run(main())
```

### Task 6: Testing Framework Setup

**Files to Create**:
- `tests/conftest.py` - Pytest configuration
- `tests/unit/test_config.py` - Configuration tests
- `tests/unit/test_models.py` - Model tests

**Test Configuration**:

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.utils.config import AppConfig
from src.data.models import MessageContext, MessageType


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return AppConfig(
        slack={
            "bot_token": "xoxb-test-token",
            "signing_secret": "test-signing-secret",
            "socket_mode": True,
        },
        ai={
            "openai_api_key": "sk-test-key",
            "default_model": "gpt-3.5-turbo",
        },
        debug=True,
    )

@pytest.fixture
def sample_message_context():
    """Sample message context for testing."""
    return MessageContext(
        user_id="U12345678",
        channel_id="C87654321",
        message_text="I need help with my application",
        message_type=MessageType.MESSAGE,
    )

@pytest.fixture
async def mock_slack_client():
    """Mock Slack client for testing."""
    client = AsyncMock()
    client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "123456789.123"})
    client.users_info = AsyncMock(return_value={"ok": True, "user": {"name": "testuser"}})
    return client

@pytest.fixture
async def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test AI response"))],
            usage=MagicMock(total_tokens=50)
        )
    )
    return client
```

### Task 7: Development Tools Setup

**Files to Create**:
- `.pre-commit-config.yaml` - Pre-commit hooks
- `scripts/setup.py` - Development setup script
- `scripts/lint.py` - Code quality checks

**Pre-commit Configuration**:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-PyYAML]
        exclude: ^tests/

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
```

## 🧪 Testing Requirements

### Unit Tests to Implement

1. **Configuration Tests** (`tests/unit/test_config.py`)
   - Test configuration loading from environment
   - Test configuration validation
   - Test default values

2. **Model Tests** (`tests/unit/test_models.py`)
   - Test Pydantic model validation
   - Test model serialization/deserialization
   - Test enum values

3. **Logging Tests** (`tests/unit/test_logging.py`)
   - Test logger configuration
   - Test structured logging output
   - Test log level filtering

### Integration Tests

1. **Health Check Test** (`tests/integration/test_health.py`)
   - Test health endpoint availability
   - Test API response format

### Coverage Requirements
- Minimum 90% code coverage
- All public functions must have tests
- All error conditions must be tested

## 🚀 Deployment Setup

### Docker Configuration

**Files to Create**:
- `Dockerfile` - Container configuration
- `docker-compose.yml` - Development environment
- `.dockerignore` - Docker ignore patterns

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "src.main"]
```

## 📝 Validation Checklist

### Code Quality
- [ ] All code passes linting (flake8)
- [ ] All code is formatted (black)
- [ ] All imports are sorted (isort)
- [ ] Type hints are complete (mypy)
- [ ] Pre-commit hooks are working

### Testing
- [ ] All tests pass
- [ ] Code coverage >= 90%
- [ ] Integration tests work
- [ ] Mock objects are properly configured

### Configuration
- [ ] Environment variables are documented
- [ ] Configuration validation works
- [ ] Default values are sensible
- [ ] Configuration can be loaded from files

### Documentation
- [ ] README.md is complete
- [ ] API documentation is generated
- [ ] Code has docstrings
- [ ] Configuration is documented

### Infrastructure
- [ ] Docker container builds successfully
- [ ] Health check endpoint works
- [ ] Application starts without errors
- [ ] Logging works correctly

## 🔄 Next Steps

After completing Phase 1, you should have:
1. A solid project foundation with all tools configured
2. Basic application structure in place
3. Configuration management working
4. Testing framework set up
5. Development environment ready

**Ready for Phase 2**: Slack Integration - implementing the Slack bot functionality. 