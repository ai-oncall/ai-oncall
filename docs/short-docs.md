## **Project Overview**

The AI OnCall Bot is a **multi-channel AI assistant** for IT support and workflow automation that intelligently classifies incoming messages and executes predefined workflows. **Now enhanced with LangChain integration** for better AI capabilities and structured workflows.

## **Core Functionality**

1. **Message Classification**: Uses **LangChain structured outputs** for reliable message classification into types (incident, knowledge_query, support_request, deployment_help)
2. **Workflow Execution**: **LangGraph state machines** for complex workflow orchestration with fallback to YAML workflows
3. **Knowledge Base Search**: **LangChain retrieval chains** for intelligent document search and response generation
4. **Multi-Channel Support**: Works with Slack (implemented) and Teams (stub)
5. **Response Generation**: **LangChain chat templates** for contextual responses with AI formatting

## **Key Components**

- **FastAPI Server**: REST API with `/process-message` and `/health` endpoints
- **Slack Integration**: Both webhook and Socket Mode support
- **LangChain AI Client**: Structured AI interactions with Pydantic validation
- **LangChain Knowledge Manager**: Enhanced vector search with retrieval chains
- **LangGraph Workflow Engine**: State-based workflow orchestration
- **Fallback Compatibility**: Graceful degradation when LangChain unavailable

## **Usage Flows**

### **1. Knowledge Query Flow (Enhanced with LangChain)**
```
User: "How do I add a webhook for Slack?" 
→ LangChain classifies as "knowledge_query" with structured output
→ LangChain retrieval chain searches ChromaDB intelligently
→ AI formats response with context and source attribution
→ Returns: "📚 Based on the documentation, here are the steps... *Sources: slack_setup.md*"
```

### **2. Incident Response Flow (LangGraph Orchestration)**
```
User: "Server is down!"
→ LangChain classifies as "incident" with "critical" severity + confidence score
→ LangGraph state machine routes through: classify → find_workflow → execute_actions → escalate
→ Escalates to on-call team with intelligent routing
→ Creates high-priority ticket with structured data
→ Returns: "🚨 Incident Acknowledged - Escalated to on-call team..."
```

### **3. Support Request Flow (Structured Processing)**
```
User: "Need help with deployment"
→ LangChain classifies as "support_request" with reasoning
→ LangGraph executes support workflow with state tracking
→ Creates support ticket with enhanced metadata
→ Returns: "🎫 Support ticket created: #12345..."
```

## **Architecture**

- **Message Processor**: Central orchestrator with LangChain integration
- **Channel Adapters**: Platform-specific implementations (Slack, Teams)
- **LangChain AI Client**: Structured AI interactions with Pydantic validation
- **LangChain Knowledge Manager**: Enhanced retrieval chains for intelligent search
- **LangGraph Workflow Engine**: State machine-based workflow orchestration
- **Fallback Systems**: Graceful degradation to original implementations

The system is designed to be **extensible** (new channels/workflows), **resilient** (fallback responses + graceful degradation), **intelligent** (LangChain-powered AI), and **observable** (structured logging).

## **LangChain Enhancements**

### **Key Improvements:**
1. **Structured Outputs**: Pydantic models ensure reliable AI responses
2. **Retrieval Chains**: Intelligent knowledge base search with context
3. **State Machines**: Complex workflow orchestration with LangGraph
4. **Better Prompts**: ChatPromptTemplate for consistent AI interactions
5. **Graceful Fallback**: Maintains compatibility when LangChain unavailable

### **Installation:**
```bash
# Install with LangChain support
poetry install

# Or install manually
pip install langchain langchain-openai langchain-community langgraph
```

### **Benefits:**
- 🎯 **More Reliable**: Structured outputs reduce parsing errors
- 🧠 **Smarter Responses**: Enhanced retrieval chains with context
- 🔄 **Better Workflows**: State-based orchestration with LangGraph  
- 🛡️ **Backward Compatible**: Fallback to original implementations
- 🚀 **Future-Ready**: Easy integration of new LangChain features