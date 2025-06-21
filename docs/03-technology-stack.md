# Technology Stack: AI OnCall Bot (Multi-Channel)

## 🛠️ Core Technologies

### Runtime Environment
- **Python 3.11+**
  - **Why**: Modern Python with excellent async support, pattern matching, and performance improvements
  - **Benefits**: Strong typing, extensive ecosystem, great AI/ML library support
  - **Considerations**: Runtime compatibility, dependency management

### Channel Adapter Layer
- **Custom Channel Adapter Interface**
  - Abstract base class for all channel integrations (Slack, Teams, Discord, Email, etc.)
  - Each channel implements its own adapter in `src/channels/<channel>/adapter.py`
  - **Slack**: First supported channel (using `slack-bolt`)
  - **Extensible**: Add new channels by implementing the interface

### Web Framework & API
- **Slack Bolt for Python**
  - **Why**: Official Slack framework with built-in security and event handling
  - **Benefits**: OAuth handling, request verification, Socket Mode support
  - **Alternatives Considered**: Direct Slack SDK (too low-level), FastAPI-only (missing Slack features)

- **FastAPI** (Supporting)
  - **Why**: Modern async framework for health checks and webhook endpoints
  - **Benefits**: Automatic API documentation, excellent async support, type hints
  - **Use Cases**: Health endpoints, metrics API, admin interface

### AI & Machine Learning
- **phidata**
  - **Why**: Specialized AI workflow orchestration with agent-based architecture
  - **Benefits**: Built-in workflow management, tool integration, structured AI patterns
  - **Alternatives Considered**: LangChain (too complex), Direct OpenAI (missing orchestration)

- **OpenAI Python Client**
  - **Why**: Official client for OpenAI API integration
  - **Benefits**: Type safety, automatic retries, streaming support
  - **Features**: Multiple model support, token usage tracking

### Data & Configuration
- **Pydantic v2**
  - **Why**: Modern data validation with excellent performance
  - **Benefits**: Type safety, JSON schema generation, configuration management
  - **Use Cases**: Data models, configuration validation, API schemas

- **PyYAML**
  - **Why**: Standard Python YAML processing library
  - **Benefits**: Workflow configuration, human-readable config files
  - **Security**: Safe loading to prevent code injection

### Testing Framework
- **pytest**
  - **Why**: Most popular Python testing framework with rich ecosystem
  - **Benefits**: Fixture system, parameterized tests, extensive plugin support
  - **Plugins**: pytest-asyncio, pytest-mock, pytest-cov

- **pytest-asyncio**
  - **Why**: Async test support for modern Python applications
  - **Benefits**: Native async/await testing, event loop management

## 📦 Dependency Management

### Core Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
slack-bolt = "^1.18.0"
phidata = "^2.4.0"
openai = "^1.0.0"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
pydantic = "^2.0.0"
pyyaml = "^6.0.0"
```

### Development Dependencies

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-mock = "^3.11.0"
pytest-cov = "^4.1.0"
black = "^23.0.0"
flake8 = "^6.0.0"
mypy = "^1.5.0"
pre-commit = "^3.4.0"
```

### Optional Dependencies

```toml
[tool.poetry.group.monitoring.dependencies]
prometheus-client = "^0.17.0"
structlog = "^23.1.0"

[tool.poetry.group.database.dependencies]
sqlalchemy = "^2.0.0"
alembic = "^1.12.0"
asyncpg = "^0.28.0"  # PostgreSQL async driver
```

## 🗂️ Directory Structure (Excerpt)

```
src/
├── channels/
│   ├── base.py                # ChannelAdapter interface
│   ├── slack/
│   │   └── adapter.py         # SlackAdapter implementation
│   ├── teams/                 # (future) TeamsAdapter
│   └── ...
├── core/
│   ├── message_processor.py   # Channel-agnostic
│   ├── response_builder.py
│   └── context.py
# ...
```

## 🧩 Example: Channel Adapter Interface

```python
# src/channels/base.py
from abc import ABC, abstractmethod

class ChannelAdapter(ABC):
    @abstractmethod
    async def send_message(self, context, message): ...
    @abstractmethod
    async def receive_event(self, request): ...
    # ... other common methods
```

## 🔧 Adding a New Channel

1. Implement the `ChannelAdapter` interface in `src/channels/<new_channel>/adapter.py`.
2. Register the new adapter in the main application entry point.
3. Add configuration and tests for the new channel.

## 📝 Configuration Management

### Environment Configuration
- **python-dotenv**: Environment variable loading
- **pydantic-settings**: Type-safe configuration management

### Configuration Structure

```python
# src/utils/config.py
from pydantic import BaseSettings, Field
from typing import Optional

class SlackConfig(BaseSettings):
    bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    app_token: Optional[str] = Field(None, env="SLACK_APP_TOKEN")
    socket_mode: bool = Field(False, env="SLACK_SOCKET_MODE")

class AIConfig(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_api_base: str = Field("https://api.openai.com/v1", env="OPENAI_API_BASE")
    default_model: str = Field("gpt-3.5-turbo", env="DEFAULT_MODEL")
    max_tokens: int = Field(500, env="MAX_TOKENS")

class AppConfig(BaseSettings):
    slack: SlackConfig = SlackConfig()
    ai: AIConfig = AIConfig()
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

## 🧪 Testing Stack

### Testing Libraries
- **pytest**: Main testing framework
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **pytest-cov**: Coverage reporting
- **httpx**: HTTP client for API testing
- **factory-boy**: Test data generation

### Testing Configuration

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock
from src.bot.slack_handler import SlackHandler
from src.ai.request_classifier import RequestClassifier

@pytest.fixture
async def mock_slack_client():
    client = AsyncMock()
    client.chat_postMessage = AsyncMock(return_value={"ok": True})
    return client

@pytest.fixture
async def mock_openai_client():
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(
        return_value={
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 50}
        }
    )
    return client

@pytest.fixture
def sample_message_context():
    return {
        "user": "U12345",
        "channel": "C12345",
        "text": "I need help with my application",
        "ts": "1234567890.123456"
    }
```

## 🐳 Deployment Technologies

### Containerization
- **Docker**: Application containerization
- **docker-compose**: Local development environment

### Container Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Development Environment

```yaml
# docker-compose.yml
version: '3.8'

services:
  bot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ai_oncall
      POSTGRES_USER: bot_user
      POSTGRES_PASSWORD: bot_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
    
    - name: Run tests
      run: |
        poetry run pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

This technology stack provides a solid foundation for building a scalable, maintainable, and well-tested AI OnCall Bot with modern Python practices and tools. 