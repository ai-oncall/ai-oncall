# 🏗️ Architecture & Technology Stack

## 🔄 System Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Multi-Channel │    │   AI OnCall     │    │    LangChain      │
│   (Slack, Teams,│───▶│      Bot        │───▶│   Orchestrator  │
│   Discord, API) │    │ (LangGraph)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ Knowledge Base  │
                       │(ChromaDB/FAISS) │
                       │   (Vector DB)   │
                       └─────────────────┘
```

### Message Flow
1. **User sends message** → Slack/Teams/API
2. **Bot processes** → Classifies intent with LangChain
3. **Searches knowledge** → LangChain vector search
4. **Generates response** → LangChain with context from KB
5. **Sends reply** → Back to original channel

## 🛠️ Technology Stack

### **Core Platform**
- **Python 3.11+** - Runtime environment
- **FastAPI** - Web framework and API endpoints
- **Slack Bolt** - Slack integration
- **WebSocket** - Real-time communication

### **AI & Knowledge**
- **LangChain** - Core AI orchestration framework
- **LangGraph** - For building stateful, multi-step applications
- **OpenAI GPT** - Language understanding and generation
- **ChromaDB** - Vector database for document search

### **Data & Config**
- **Pydantic** - Data validation and models
- **YAML** - Configuration files
- **Environment Variables** - Secrets management

### **Testing & Development**
- **pytest** - Testing framework
- **Poetry** - Dependency management
- **Docker** - Containerization