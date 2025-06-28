# 🏗️ Architecture & Technology Stack

## 🔄 System Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Multi-Channel │    │   AI OnCall     │    │    OpenAI       │
│   (Slack, Teams,│───▶│      Bot        │───▶│   GPT Models    │
│   Discord, API) │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   ChromaDB      │
                       │ Knowledge Base  │
                       │   (Vector DB)   │
                       └─────────────────┘
```

### Message Flow
1. **User sends message** → Slack/Teams/API
2. **Bot processes** → Classifies intent with OpenAI
3. **Searches knowledge** → ChromaDB vector search
4. **Generates response** → OpenAI with context
5. **Sends reply** → Back to original channel

## 🛠️ Technology Stack

### **Core Platform**
- **Python 3.11+** - Runtime environment
- **FastAPI** - Web framework and API endpoints
- **Slack Bolt** - Slack integration
- **WebSocket** - Real-time communication

### **AI & Knowledge**
- **OpenAI GPT** - Language understanding and generation
- **ChromaDB** - Vector database for document search
- **Phidata** - AI workflow orchestration

### **Data & Config**
- **Pydantic** - Data validation and models
- **YAML** - Configuration files
- **Environment Variables** - Secrets management

### **Testing & Development**
- **pytest** - Testing framework
- **Poetry** - Dependency management
- **Docker** - Containerization 