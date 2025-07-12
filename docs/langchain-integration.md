# LangChain Integration Guide

## Overview

The AI OnCall Bot leverages LangChain to provide:

- **Structured AI responses** with Pydantic output parsers
- **Enhanced retrieval chains** for knowledge base queries
- **LangGraph workflow orchestration** for complex workflows
- **Better prompt management** with ChatPromptTemplate

## Installation

### 1. Install LangChain Dependencies

```bash
# Install the project with LangChain dependencies
poetry install

# Or install LangChain packages manually
pip install langchain langchain-openai langchain-community langchain-chroma langgraph
```

### 2. Environment Configuration

Update your `.env` file with your OpenAI configuration:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=150
OPENAI_TEMPERATURE=0.3

# Existing Slack configuration...
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
```

## Architecture

### Core Components

1.  **LangChain AI Client** (`src/ai/langchain_client.py`)
    -   Structured output with Pydantic models
    -   Better prompt management
    -   Improved error handling

2.  **LangChain Knowledge Manager** (`src/knowledge/langchain_kb_manager.py`)
    -   Advanced retrieval chains
    -   Automatic text chunking
    -   Enhanced search with context

3.  **LangGraph Workflow Engine** (`src/workflows/langgraph_engine.py`)
    -   State-based workflow execution
    -   Complex conditional routing
    -   Better action orchestration

## Key Improvements

### 1. Structured Message Classification

**Before (manual JSON parsing):**

```python
# Manual prompt engineering and JSON parsing
classification = await openai_client.classify_message(message)
# Hope the JSON is valid...
```

**After (structured output):**

```python
# Guaranteed structured output with validation
classification = await langchain_client.classify_message(message)
# Returns validated MessageClassification object
```

### 2. Enhanced Knowledge Retrieval

**Before (basic search + formatting):**

```python
results = knowledge_base.search(query)
response = format_results_manually(results)
```

**After (retrieval chains):**

```python
# Intelligent retrieval with context-aware responses
response = await knowledge_base.search_with_chain(query)
```

### 3. Workflow Orchestration

**Before (simple condition matching):**

```python
if classification.type == "incident":
    execute_incident_workflow()
```

**After (state machine workflows):**

```python
# Complex state-based workflow execution
result = await workflow_engine.execute_workflow(classification, context)
```

## Usage Examples

### 1. Knowledge Query with LangChain

```python
# Enhanced knowledge search with intelligent formatting
user_query = "How do I add a webhook for Slack?"
response = await knowledge_manager.search_with_chain(user_query)

# Returns:
# "Based on the documentation, here are the steps to add a Slack webhook:
#  1. Go to your Slack app settings...
#  2. Navigate to Event Subscriptions...
#  
#  Sources: slack_webhook_setup.md"
```

### 2. Structured Classification

```python
# Get structured classification with confidence and reasoning
classification = await ai_client.classify_message("Server is down!")

# Returns MessageClassification object:
# {
#   "type": "incident",
#   "severity": "critical", 
#   "confidence": 0.95,
#   "reasoning": "Clear indication of system outage"
# }
```

### 3. LangGraph Workflow

```python
# Complex workflow with state management
workflow_result = await workflow_engine.execute_workflow(classification, context)

# Automatically routes through:
# classify → find_workflow → execute_actions → escalate → generate_response
```

## Testing

### Run with LangChain

```bash
# Start the application (LangChain will be used if available)
poetry run python -m src.main

# Test knowledge query
curl -X POST http://localhost:8000/process-message \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I setup webhooks?", "channel_type": "api"}'
```

### Run without LangChain

```bash
# Uninstall LangChain temporarily to test fallback
pip uninstall langchain langchain-openai langchain-community

# Start application (will use original implementations)
poetry run python -m src.main
```

## Benefits

### 1. **Better Reliability**
- Structured outputs reduce parsing errors
- Validation catches malformed responses
- Better error handling and fallbacks

### 2. **Enhanced Functionality** 
- Smarter knowledge retrieval with context
- Complex workflow orchestration
- Better prompt management

### 3. **Future-Proof Architecture**
- Easy to add new LangChain features
- Modular component design
- Graceful degradation

### 4. **Backward Compatibility**
- Existing functionality preserved
- No breaking changes to API
- Smooth migration path

## Migration Notes

### For Developers

1. **No API Changes**: All existing endpoints work the same
2. **Enhanced Responses**: Knowledge queries return better-formatted responses
3. **Better Logging**: More detailed workflow execution logs
4. **Fallback Safety**: Original functionality preserved

### For Operations

1. **Same Deployment**: No deployment process changes
2. **Optional Upgrade**: LangChain installation is optional
3. **Performance**: Similar performance with enhanced capabilities
4. **Monitoring**: Same health checks and metrics

## Troubleshooting

### LangChain Import Errors

```python
# Check if LangChain is properly installed
python -c "import langchain; print('LangChain available')"

# Install missing packages
poetry install
# or
pip install langchain langchain-openai langchain-community
```

### Fallback Behavior

```bash
# Check logs for fallback messages
grep "fallback\|not available" logs/app.log

# Example fallback log:
# "LangChain not available, using fallback workflow execution"
```

### Performance Issues

```python
# Monitor LangChain performance
# Check processing times in response:
# "processing_time_ms": 1250
```

## Next Steps

1. **Enable Vector Store Persistence**: Configure permanent vector storage
2. **Add Custom Tools**: Integrate LangChain tools for external APIs
3. **Enhanced Prompts**: Refine prompts for specific use cases
4. **Memory Integration**: Add conversation memory with LangChain
5. **Multi-Agent Systems**: Explore LangGraph multi-agent capabilities
