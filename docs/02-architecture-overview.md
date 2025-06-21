# Architecture Overview: AI OnCall Bot (Multi-Channel)

## 🏗️ System Architecture

The AI OnCall Bot is designed as a modular, event-driven, and channel-agnostic system. It supports multiple communication platforms (Slack, Teams, Discord, Email, etc.) through a unified Channel Adapter interface, ensuring that all core logic is decoupled from any specific channel.

```
┌──────────────────────────────────────────────────────────────┐
│                        AI OnCall Bot                         │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Channel     │  │     AI      │  │  Workflow   │          │
│  │ Adapter(s)  │  │ Processing  │  │   Engine    │          │
│  │ (Slack,...) │  │   Engine    │  │             │          │
│  └──────────────┘  └─────────────┘  └─────────────┘          │
│         │                 │                 │               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │    Data     │  │   Shared    │  │  External   │          │
│  │   Layer     │  │ Utils       │  │ Services    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└──────────────────────────────────────────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────┐         ┌──────▼──────┐        ┌────▼─────┐
│ Slack  │         │   OpenAI    │        │   YAML   │
│ Teams  │         │    Proxy    │        │  Config  │
│ ...    │         └─────────────┘        └──────────┘
└────────┘
```

## 🔧 Core Components

### 1. Channel Adapter Layer (`src/channels/`)

**Purpose**: Abstracts all channel-specific logic behind a common interface. Each supported platform (Slack, Teams, etc.) implements the `ChannelAdapter` interface.

**Key Modules**:
- `base.py`: Defines the `ChannelAdapter` interface
- `slack/adapter.py`: Slack implementation
- `teams/adapter.py`: Teams implementation (future)
- ...

**Responsibilities**:
- Receive and normalize events/messages from each channel
- Convert channel-specific payloads to a unified context model
- Send responses back to the originating channel
- Handle authentication and security for each channel

**Key Interactions**:
```python
ChannelEvent → ChannelAdapter → CoreBotLogic → ChannelAdapter → ChannelResponse
```

### 2. Core Bot Logic (`src/core/`)

**Purpose**: Channel-agnostic message processing, AI integration, workflow execution, and response generation.

**Key Modules**:
- `message_processor.py`: Message parsing and preprocessing
- `response_builder.py`: Response formatting
- `context.py`: Conversation context management

**Responsibilities**:
- Process normalized events from any channel
- Classify requests, manage context, and execute workflows
- Generate responses in a channel-agnostic format

### 3. AI Processing Engine (`src/ai/`)

**Purpose**: Core intelligence using OpenAI and phi data lib for request understanding and response generation.

**Key Modules**:
- `openai_client.py`: OpenAI API integration
- `request_classifier.py`: Intent classification
- `context_manager.py`: Conversation context
- `agents/`: Specialized AI agents

### 4. Workflow Engine (`src/workflow/`)

**Purpose**: Executes YAML-defined business logic and decision trees.

**Key Modules**:
- `flow_parser.py`: YAML workflow parsing
- `flow_executor.py`: Workflow execution
- `flow_validator.py`: Validation

### 5. Data Layer (`src/data/`)

**Purpose**: Data persistence, models, and analytics.

**Key Modules**:
- `models.py`: Unified data models (with channel/source info)
- `storage.py`: Data persistence
- `analytics.py`: Usage tracking

### 6. Shared Utils (`src/utils/`)

**Purpose**: Common utilities and cross-cutting concerns.

**Key Modules**:
- `config.py`: Configuration management
- `logging.py`: Logging
- `exceptions.py`: Exception handling
- `validators.py`: Input validation

## 🔄 Data Flow (Channel-Agnostic)

```
1. Channel Event (Slack, Teams, etc.)
   ↓
2. Channel Adapter (normalizes event)
   ↓
3. Core Bot Logic (processes message)
   ↓
4. AI Processing & Workflow Engine
   ↓
5. Response Builder (formats response)
   ↓
6. Channel Adapter (sends response)
   ↓
7. User (in original channel)
```

## 📊 Data Models

### Unified Context Example
```python
class MessageContext(BaseModel):
    user_id: str
    channel_id: str
    channel_type: str  # e.g., 'slack', 'teams', 'discord', 'email'
    thread_ts: Optional[str]
    message_text: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

## 🔧 Configuration Architecture

- Each channel adapter can have its own configuration section.
- Core configuration is channel-agnostic.

## 🔐 Security Architecture

- Each channel adapter is responsible for its own authentication and request validation.
- Core logic enforces channel-agnostic security policies (rate limiting, audit logging, etc.)

## 📈 Scalability Considerations

- Channel adapters can be added or removed independently.
- Core logic and AI processing scale horizontally, regardless of channel.

## 🔍 Monitoring and Observability

- Metrics and logs include channel/source information for analytics and troubleshooting.

## 🧩 Adding a New Channel

1. Implement the `ChannelAdapter` interface in `src/channels/<new_channel>/adapter.py`.
2. Register the new adapter in the main application entry point.
3. Add configuration and tests for the new channel.
4. Update documentation and user guides as needed.
