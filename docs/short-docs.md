## **Project Overview**

The AI OnCall Bot is a **multi-channel AI assistant** for IT support and workflow automation that intelligently classifies incoming messages and executes predefined workflows.

## **Core Functionality**

1. **Message Classification**: Uses OpenAI to classify messages into types (incident, knowledge_query, support_request, deployment_help)
2. **Workflow Execution**: Matches classifications to predefined workflows in `flow.yaml`
3. **Knowledge Base Search**: Uses ChromaDB for vector-based document search
4. **Multi-Channel Support**: Works with Slack (implemented) and Teams (stub)
5. **Response Generation**: Creates contextual responses using AI and templates

## **Key Components**

- **FastAPI Server**: REST API with `/process-message` and `/health` endpoints
- **Slack Integration**: Both webhook and Socket Mode support
- **ChromaDB**: Vector database for knowledge base documents
- **OpenAI Client**: AI-powered classification and response generation
- **Workflow Engine**: YAML-configured action execution

## **Usage Flows**

### **1. Knowledge Query Flow**
```
User: "How do I add a webhook for Slack?" 
→ AI classifies as "knowledge_query"
→ Searches ChromaDB for relevant docs
→ AI formats response with found information
→ Returns: "📚 Found relevant information: [formatted results]"
```

### **2. Incident Response Flow**
```
User: "Server is down!"
→ AI classifies as "incident" with "critical" severity
→ Executes incident_response workflow
→ Escalates to on-call team
→ Creates high-priority ticket
→ Returns: "🚨 Incident Acknowledged - Escalated to on-call team..."
```

### **3. Support Request Flow**
```
User: "Need help with deployment"
→ AI classifies as "support_request"
→ Creates support ticket
→ Returns: "🎫 Support ticket created: #12345..."
```

## **Architecture**

- **Message Processor**: Central orchestrator
- **Channel Adapters**: Platform-specific implementations
- **AI Client**: OpenAI integration with fallback mocks
- **Knowledge Manager**: ChromaDB operations
- **Workflow Engine**: YAML-driven automation

The system is designed to be **extensible** (new channels/workflows), **resilient** (fallback responses), and **observable** (structured logging).